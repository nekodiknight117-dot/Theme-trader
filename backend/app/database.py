import os
from sqlalchemy import create_engine, text
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


def run_sqlite_migrations() -> None:
    """Add columns to existing SQLite DBs (SQLAlchemy create_all does not alter tables)."""
    if not DATABASE_URL.startswith("sqlite"):
        return
    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(user_profiles)")).fetchall()
        cols = {r[1] for r in rows}
        if "password_hash" not in cols:
            conn.execute(text("ALTER TABLE user_profiles ADD COLUMN password_hash VARCHAR"))
            conn.commit()

        rows = conn.execute(text("PRAGMA table_info(assets)")).fetchall()
        cols = {r[1] for r in rows}
        if "theme_rationale" not in cols:
            conn.execute(text("ALTER TABLE assets ADD COLUMN theme_rationale VARCHAR"))
            conn.commit()
        if "financial_rationale" not in cols:
            conn.execute(text("ALTER TABLE assets ADD COLUMN financial_rationale VARCHAR"))
            conn.commit()
        if "beta" not in cols:
            conn.execute(text("ALTER TABLE assets ADD COLUMN beta REAL"))
            conn.commit()
        if "weight" not in cols:
            conn.execute(text("ALTER TABLE assets ADD COLUMN weight REAL"))
            conn.commit()

Base = declarative_base()

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
