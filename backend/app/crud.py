from sqlalchemy.orm import Session
from . import models

def get_user(db: Session, user_id: int):
    return db.query(models.UserProfile).filter(models.UserProfile.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.UserProfile).filter(models.UserProfile.username == username).first()

def create_user(
    db: Session,
    username: str,
    risk_tolerance: str,
    interests: str = "",
    password_hash: str | None = None,
):
    db_user = models.UserProfile(
        username=username,
        risk_tolerance=risk_tolerance,
        interests=interests,
        password_hash=password_hash,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_portfolio(db: Session, user_id: int, name: str):
    db_portfolio = models.Portfolio(user_id=user_id, name=name)
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio

def get_portfolios_for_user(db: Session, user_id: int):
    return db.query(models.Portfolio).filter(models.Portfolio.user_id == user_id).all()

def add_asset_to_portfolio(db: Session, portfolio_id: int, ticker: str, category: str, rationale: str = "", name: str = ""):
    db_asset = models.Asset(portfolio_id=portfolio_id, ticker=ticker, name=name, category=category, rationale=rationale)
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset
