from sqlalchemy import Column, Float, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String, nullable=True)
    interests = Column(String)  # Comma-separated list for simplicity in hackathon
    risk_tolerance = Column(String)  # "Low", "Medium", "High"
    
    portfolios = relationship("Portfolio", back_populates="user")

class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"))
    name = Column(String)
    
    user = relationship("UserProfile", back_populates="portfolios")
    assets = relationship("Asset", back_populates="portfolio")

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    ticker = Column(String, index=True)
    name = Column(String)
    category = Column(String)  # e.g., "ETF", "Blue Chip", "IPO", "Rising Star"
    rationale = Column(String)  # Legacy combined copy for older clients
    theme_rationale = Column(String, nullable=True)
    financial_rationale = Column(String, nullable=True)
    beta = Column(Float, nullable=True)    # Market beta from yfinance
    weight = Column(Float, nullable=True)  # Beta-derived portfolio weight (sums to 1.0)

    portfolio = relationship("Portfolio", back_populates="assets")


class TickerFinancialCache(Base):
    """Financial thesis keyed by ticker + risk + category (shared across users)."""

    __tablename__ = "ticker_financial_cache"
    __table_args__ = (
        UniqueConstraint("ticker", "risk_tolerance", "category", name="uq_ticker_financial_key"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String, index=True)
    risk_tolerance = Column(String)
    category = Column(String)
    company_name = Column(String, default="")
    financial_rationale = Column(String, default="")
    financial_updated_at = Column(DateTime(timezone=True), nullable=True)


class CacheEntry(Base):
    __tablename__ = "cache_entries"
    
    key = Column(String, primary_key=True, index=True)
    value = Column(String)
    expires_at = Column(String) # Storing as ISO formatted string for simplicity across sqlite/postgres
