import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load DATABASE_URL from environment or fallback to local SQLite for development
# In production, this would be loaded via python-dotenv, but we'll default it here for now
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./theme_trader.db")

# create_engine needs connect_args={"check_same_thread": False} only for SQLite
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL, connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
