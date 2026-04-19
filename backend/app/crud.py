from datetime import datetime

from sqlalchemy import desc
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


def get_ticker_financial_cache(
    db: Session, ticker: str, risk_tolerance: str, category: str
) -> models.TickerFinancialCache | None:
    return (
        db.query(models.TickerFinancialCache)
        .filter(
            models.TickerFinancialCache.ticker == ticker.upper(),
            models.TickerFinancialCache.risk_tolerance == risk_tolerance,
            models.TickerFinancialCache.category == category,
        )
        .first()
    )


def upsert_ticker_financial_cache(
    db: Session,
    ticker: str,
    risk_tolerance: str,
    category: str,
    company_name: str,
    financial_rationale: str,
    updated_at: datetime,
) -> models.TickerFinancialCache:
    row = get_ticker_financial_cache(db, ticker, risk_tolerance, category)
    if row:
        row.company_name = company_name
        row.financial_rationale = financial_rationale
        row.financial_updated_at = updated_at
    else:
        row = models.TickerFinancialCache(
            ticker=ticker.upper(),
            risk_tolerance=risk_tolerance,
            category=category,
            company_name=company_name,
            financial_rationale=financial_rationale,
            financial_updated_at=updated_at,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _combined_rationale(theme: str | None, financial: str | None) -> str:
    t = (theme or "").strip()
    f = (financial or "").strip()
    if t and f:
        return f"{t}\n\n{f}"
    return t or f


def add_asset_to_portfolio(
    db: Session,
    portfolio_id: int,
    ticker: str,
    category: str,
    rationale: str = "",
    name: str = "",
    theme_rationale: str | None = None,
    financial_rationale: str | None = None,
):
    combined = rationale if rationale else _combined_rationale(theme_rationale, financial_rationale)
    db_asset = models.Asset(
        portfolio_id=portfolio_id,
        ticker=ticker,
        name=name,
        category=category,
        rationale=combined,
        theme_rationale=theme_rationale,
        financial_rationale=financial_rationale,
    )
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset


def get_landing_example_assets(db: Session) -> list[models.Asset]:
    """
    One holding per category (ETF, Blue Chip, Rising Star, IPO) from the portfolio
    that owns the most recently inserted asset—mirrors what users see on the dashboard.
    """
    latest = db.query(models.Asset).order_by(desc(models.Asset.id)).first()
    if not latest:
        return []

    assets = (
        db.query(models.Asset)
        .filter(models.Asset.portfolio_id == latest.portfolio_id)
        .order_by(models.Asset.id)
        .all()
    )
    order = ["ETF", "Blue Chip", "Rising Star", "IPO"]
    by_cat: dict[str, models.Asset] = {}
    for a in assets:
        if a.category in order and a.category not in by_cat:
            by_cat[a.category] = a

    return [by_cat[c] for c in order if c in by_cat]
