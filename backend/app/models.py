from sqlalchemy import Column, Integer, String, ForeignKey
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
    rationale = Column(String) # AI generated reason to invest
    
    portfolio = relationship("Portfolio", back_populates="assets")

class CacheEntry(Base):
    __tablename__ = "cache_entries"
    
    key = Column(String, primary_key=True, index=True)
    value = Column(String)
    expires_at = Column(String) # Storing as ISO formatted string for simplicity across sqlite/postgres
