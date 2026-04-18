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
from .llm_service import generate_investment_rationale, parse_user_interests
from .cache_service import get_cached_value, set_cached_value

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
        
    # 1. Select portfolio algorithmically, personalised by user interests
    raw_portfolio = await get_algorithmic_portfolio(user.risk_tolerance, interests=user.interests or "")
    
    # Create the portfolio in DB
    portfolio_name = f"{user.risk_tolerance.capitalize()} Risk Theme Portfolio"
    db_portfolio = crud.create_portfolio(db=db, user_id=user.id, name=portfolio_name)
    
    # Process each asset: fetch research, generate rationale, and save
    # Note: Running these sequentially for simplicity, but could be gathered concurrently with asyncio.gather
    for asset_data in raw_portfolio:
        ticker = asset_data["ticker"]
        category = asset_data["category"]
        
        # 2. Get Qualitative Research (with Caching)
        cache_key_tavily = f"tavily:{ticker}"
        research = get_cached_value(db, cache_key_tavily)
        if not research:
            research = get_company_research(ticker, category)
            if research and not research.startswith("Error") and not research.startswith("Could not"):
                set_cached_value(db, cache_key_tavily, research, ttl_hours=24)
        
        # 3. Generate LLM Pitch (with Caching — keyed by ticker + risk + interests)
        interests_slug = (user.interests or "")[:50]  # cap length for key safety
        cache_key_llm = f"llm:rationale:{ticker}:{user.risk_tolerance}:{interests_slug}"
        rationale = get_cached_value(db, cache_key_llm)
        if not rationale:
            rationale = await generate_investment_rationale(
                ticker=ticker, 
                category=category, 
                quantitative_data=asset_data, 
                qualitative_research=research, 
                risk_tolerance=user.risk_tolerance,
                interests=user.interests or "",
            )
            if rationale and "temporarily unavailable" not in rationale.lower():
                set_cached_value(db, cache_key_llm, rationale, ttl_hours=24)
        
        # 4. Save to Database
        crud.add_asset_to_portfolio(
            db=db, 
            portfolio_id=db_portfolio.id, 
            ticker=ticker, 
            category=category, 
            rationale=rationale
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
