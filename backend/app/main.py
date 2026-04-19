import os
from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from . import models, schemas, crud
from .database import engine, get_db, run_sqlite_migrations
from .security import create_access_token, get_current_user, hash_password, verify_password
from .alpaca_stream import active_connections, start_alpaca_stream, stop_alpaca_stream
from .stock_selector import get_algorithmic_portfolio
from .tavily_research import get_company_research
from .llm_service import (
    FINANCIAL_UNAVAILABLE,
    generate_financial_rationale,
    generate_theme_overlap_rationale,
    parse_user_interests,
)
from .interests_util import interest_tags, normalize_risk
from .cache_service import get_cached_value, set_cached_value


def _financial_cache_fresh(updated_at: datetime | None, ttl_hours: float) -> bool:
    if updated_at is None:
        return False
    now = datetime.now(timezone.utc)
    ts = updated_at
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return now - ts < timedelta(hours=ttl_hours)

# Create the database tables and apply SQLite migrations
models.Base.metadata.create_all(bind=engine)
run_sqlite_migrations()

@asynccontextmanager
async def lifespan(app: FastAPI):
    from pathlib import Path
    import dotenv
    # Explicitly load root-level .env regardless of where uvicorn is launched from
    _root_env = Path(__file__).resolve().parents[2] / ".env"
    dotenv.load_dotenv(dotenv_path=_root_env, override=True)
    # Start the Alpaca stream in the background
    await start_alpaca_stream()
    yield
    # Clean shutdown — cancel the stream task before the event loop closes
    await stop_alpaca_stream()

app = FastAPI(title="Theme-Trader API", description="Hackathon Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Welcome to the Theme-Trader Backend"}


# --- Authentication ---


@app.post("/auth/register", response_model=schemas.AuthResponse)
def auth_register(body: schemas.RegisterRequest, db: Session = Depends(get_db)):
    if crud.get_user_by_username(db, username=body.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    ph = hash_password(body.password)
    user = crud.create_user(
        db=db,
        username=body.username,
        risk_tolerance=body.risk_tolerance,
        interests=body.interests,
        password_hash=ph,
    )
    token = create_access_token(user_id=user.id, username=user.username)
    return schemas.AuthResponse(
        access_token=token,
        user=schemas.UserPublic.model_validate(user),
    )


@app.post("/auth/login", response_model=schemas.AuthResponse)
def auth_login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username=body.username)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    token = create_access_token(user_id=user.id, username=user.username)
    return schemas.AuthResponse(
        access_token=token,
        user=schemas.UserPublic.model_validate(user),
    )


@app.get("/users/me", response_model=schemas.UserPublic)
def read_me(current: models.UserProfile = Depends(get_current_user)):
    return schemas.UserPublic.model_validate(current)


@app.get("/users/me/portfolios/", response_model=List[schemas.Portfolio])
def get_my_portfolios(
    db: Session = Depends(get_db),
    current: models.UserProfile = Depends(get_current_user),
):
    return crud.get_portfolios_for_user(db, user_id=current.id)


# --- Interest Parsing Endpoint ---

class ParseInterestsRequest(BaseModel):
    raw_text: str

@app.post("/api/parse-interests")
async def parse_interests(body: ParseInterestsRequest):
    """
    Sends the user's free-text description to the LLM and returns structured
    interests and an inferred investment goal.
    """
    result = await parse_user_interests(body.raw_text)
    return result

# --- Assessment & Research Pipeline Endpoint ---

@app.post("/api/assess", response_model=schemas.Portfolio)
async def run_assessment(
    db: Session = Depends(get_db),
    current: models.UserProfile = Depends(get_current_user),
):
    """
    Core pipeline: Authenticated user; algorithmic selection, Tavily research, LLM rationale, new portfolio.
    """
    user = current

    fin_ttl = float(os.getenv("FINANCIAL_RATIONALE_TTL_HOURS", "72"))
    risk_norm = normalize_risk(user.risk_tolerance)
    tags = interest_tags(user.interests or "")

    # 1. Select portfolio algorithmically, personalised by user interests
    raw_portfolio = await get_algorithmic_portfolio(user.risk_tolerance, interests=user.interests or "")

    # Create the portfolio in DB
    portfolio_name = f"{user.risk_tolerance.capitalize()} Risk Theme Portfolio"
    db_portfolio = crud.create_portfolio(db=db, user_id=user.id, name=portfolio_name)

    for asset_data in raw_portfolio:
        ticker = asset_data["ticker"]
        category = asset_data["category"]
        company_name = asset_data.get("company_name") or ticker

        cached = crud.get_ticker_financial_cache(db, ticker, risk_norm, category)
        research = ""
        financial_text = ""
        used_financial_cache = (
            cached
            and cached.financial_rationale
            and _financial_cache_fresh(cached.financial_updated_at, fin_ttl)
            and FINANCIAL_UNAVAILABLE.lower() not in cached.financial_rationale.lower()
        )

        if used_financial_cache:
            financial_text = cached.financial_rationale
            if cached.company_name:
                company_name = cached.company_name
        else:
            cache_key_tavily = f"tavily:{ticker}"
            research = get_cached_value(db, cache_key_tavily)
            if not research:
                research = get_company_research(ticker, category)
                if research and not research.startswith("Error") and not research.startswith("Could not"):
                    set_cached_value(db, cache_key_tavily, research, ttl_hours=24)

            financial_text = await generate_financial_rationale(
                ticker=ticker,
                category=category,
                quantitative_data=asset_data,
                qualitative_research=research or "",
                risk_tolerance=user.risk_tolerance,
            )
            if financial_text and FINANCIAL_UNAVAILABLE.lower() not in financial_text.lower():
                crud.upsert_ticker_financial_cache(
                    db=db,
                    ticker=ticker,
                    risk_tolerance=risk_norm,
                    category=category,
                    company_name=company_name,
                    financial_rationale=financial_text,
                    updated_at=datetime.now(timezone.utc),
                )

        theme_text = await generate_theme_overlap_rationale(
            ticker=ticker,
            category=category,
            interest_tags=tags,
            company_name=company_name,
            financial_rationale=financial_text,
            risk_tolerance=user.risk_tolerance,
        )

        crud.add_asset_to_portfolio(
            db=db,
            portfolio_id=db_portfolio.id,
            ticker=ticker,
            category=category,
            name=company_name,
            theme_rationale=theme_text,
            financial_rationale=financial_text,
        )
        
    # Return the newly hydrated portfolio
    db.refresh(db_portfolio)
    return db_portfolio

# --- Basic CRUD Endpoints ---

@app.post("/users/", response_model=schemas.UserProfile)
def create_user(user: schemas.UserProfileCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    ph = None
    if user.password:
        if len(user.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        ph = hash_password(user.password)
    return crud.create_user(
        db=db,
        username=user.username,
        risk_tolerance=user.risk_tolerance,
        interests=user.interests,
        password_hash=ph,
    )

@app.get("/users/{user_id}", response_model=schemas.UserProfile)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.get("/users/{user_id}/portfolios/", response_model=List[schemas.Portfolio])
def get_portfolios_for_user(user_id: int, db: Session = Depends(get_db)):
    user = crud.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return crud.get_portfolios_for_user(db, user_id=user_id)

@app.post("/users/{user_id}/portfolios/", response_model=schemas.Portfolio)
def create_portfolio_for_user(user_id: int, portfolio: schemas.PortfolioCreate, db: Session = Depends(get_db)):
    return crud.create_portfolio(db=db, user_id=user_id, name=portfolio.name)

# --- Market Data Endpoints ---

@app.get("/api/expected-return")
async def get_expected_return(tickers: str):
    """
    Returns the annualised 1-year CAGR for each ticker based on the past 252
    trading days of daily closes from yfinance.

    Formula: CAGR = (P_last / P_first) ^ (252 / n_days) - 1
    Returned as a percentage, e.g. 12.3 means +12.3 % per year.

    Example: /api/expected-return?tickers=AAPL,NVDA,SPY
    """
    import yfinance as yf
    import math

    symbols = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if not symbols:
        return {}

    result = {}
    for sym in symbols:
        try:
            hist = yf.Ticker(sym).history(period="1y", interval="1d")
            closes = hist["Close"].dropna()
            if len(closes) < 2:
                continue
            n_days = len(closes)
            cagr = (float(closes.iloc[-1]) / float(closes.iloc[0])) ** (252 / n_days) - 1
            if not math.isnan(cagr) and not math.isinf(cagr):
                result[sym] = round(cagr * 100, 2)  # as percentage
        except Exception:
            pass

    return result


@app.get("/api/prev-close")
async def get_prev_close(tickers: str):
    """
    Returns the previous trading day's closing price for a comma-separated list
    of tickers. Uses yfinance's fast_info so only one network call per symbol.
    Example: /api/prev-close?tickers=AAPL,NVDA,SPY
    """
    import yfinance as yf
    import math

    symbols = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if not symbols:
        return {}

    result = {}
    for sym in symbols:
        try:
            tk = yf.Ticker(sym)
            pc = tk.fast_info.get("previousClose") or tk.fast_info.get("previous_close")
            if pc is not None and not math.isnan(float(pc)):
                result[sym] = round(float(pc), 4)
            else:
                # fallback: last close from 5-day daily history
                hist = tk.history(period="5d", interval="1d")
                if not hist.empty:
                    result[sym] = round(float(hist["Close"].iloc[-1]), 4)
        except Exception:
            pass

    return result


# --- Historical Bars Endpoint ---

@app.get("/api/bars/{ticker}")
async def get_bars(ticker: str):
    """
    Returns minute-level OHLCV bars for the most recent trading session.
    Uses yfinance so no Alpaca credentials are required.
    Falls back to daily bars if intraday data is unavailable.
    """
    import yfinance as yf
    import math

    sym = ticker.upper()
    try:
        tk = yf.Ticker(sym)
        # "1d" period with "1m" interval gives today's intraday bars (or the
        # last trading day's bars when the market is closed).
        hist = tk.history(period="1d", interval="1m")

        if hist.empty:
            # Fallback: 5-day daily closes so the chart always has something
            hist = tk.history(period="5d", interval="1d")
            if hist.empty:
                return {"ticker": sym, "bars": [], "source": "none"}
            bars = [
                {
                    "time": int(row.Index.timestamp()),
                    "value": round(float(row.Close), 4),
                }
                for row in hist.itertuples()
                if not math.isnan(row.Close)
            ]
            return {"ticker": sym, "bars": bars, "source": "daily"}

        bars = [
            {
                "time": int(row.Index.timestamp()),
                "value": round(float(row.Close), 4),
            }
            for row in hist.itertuples()
            if not math.isnan(row.Close)
        ]
        return {"ticker": sym, "bars": bars, "source": "intraday"}

    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch bars for {sym}: {exc}")


# --- Realtime WebSocket Endpoint ---

@app.websocket("/ws/prices")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)
