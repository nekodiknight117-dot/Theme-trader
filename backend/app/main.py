import asyncio
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from . import models, schemas, crud
from .database import engine, get_db
from .alpaca_stream import active_connections, start_alpaca_stream

# Create the database tables
models.Base.metadata.create_all(bind=engine)

# Lifecycle manager for FastAPI to start background tasks (like Alpaca stream)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load env variables here if python-dotenv is added later
    import dotenv
    dotenv.load_dotenv()
    
    # Start the Alpaca stream in the background
    asyncio.create_task(start_alpaca_stream())
    yield
    # Cleanup on shutdown

app = FastAPI(title="Theme-Trader API", description="Hackathon Backend", lifespan=lifespan)

# Allow CORS for the frontend to connect
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
            # Keep the connection alive, waiting for client messages if any
            data = await websocket.receive_text()
            # We can parse client messages here to change which tickers we subscribe to in the future
    except WebSocketDisconnect:
        active_connections.remove(websocket)
