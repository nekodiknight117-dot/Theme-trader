import asyncio
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from . import models, schemas, crud
from .database import engine, get_db
from .alpaca_stream import active_connections, start_alpaca_stream
from .stock_selector import get_algorithmic_portfolio
from .tavily_research import get_company_research
from .llm_service import generate_investment_rationale
from .cache_service import get_cached_value, set_cached_value

# Create the database tables
models.Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    import dotenv
    dotenv.load_dotenv()
    # Start the Alpaca stream in the background
    asyncio.create_task(start_alpaca_stream())
    yield

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

# --- Assessment & Research Pipeline Endpoint ---

@app.post("/api/assess", response_model=schemas.Portfolio)
async def run_assessment(user_id: int, db: Session = Depends(get_db)):
    """
    Core pipeline: Takes a user, uses algorithmic stock selection based on their risk tolerance,
    pulls qualitative research from Tavily, synthesizes it via LLM, and creates a portfolio.
    """
    user = crud.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # 1. Select basic portfolio mix algorithmically
    raw_portfolio = get_algorithmic_portfolio(user.risk_tolerance)
    
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
        
        # 3. Generate LLM Pitch (with Caching)
        cache_key_llm = f"llm:rationale:{ticker}:{user.risk_tolerance}"
        rationale = get_cached_value(db, cache_key_llm)
        if not rationale:
            rationale = await generate_investment_rationale(
                ticker=ticker, 
                category=category, 
                quantitative_data=asset_data, 
                qualitative_research=research, 
                risk_tolerance=user.risk_tolerance
            )
            if rationale and not rationale.startswith("System was unable"):
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
    return crud.create_user(db=db, username=user.username, risk_tolerance=user.risk_tolerance, interests=user.interests)

@app.get("/users/{user_id}", response_model=schemas.UserProfile)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

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
