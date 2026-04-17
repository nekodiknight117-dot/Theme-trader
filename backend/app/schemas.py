from pydantic import BaseModel
from typing import List, Optional

class AssetBase(BaseModel):
    ticker: str
    category: str
    rationale: Optional[str] = None

class AssetCreate(AssetBase):
    pass

class Asset(AssetBase):
    id: int
    portfolio_id: int
    class Config:
        from_attributes = True

class PortfolioBase(BaseModel):
    name: str

class PortfolioCreate(PortfolioBase):
    pass

class Portfolio(PortfolioBase):
    id: int
    user_id: int
    assets: List[Asset] = []
    class Config:
        from_attributes = True

class UserProfileBase(BaseModel):
    username: str
    risk_tolerance: str
    interests: str = ""

class UserProfileCreate(UserProfileBase):
    pass

class UserProfile(UserProfileBase):
    id: int
    portfolios: List[Portfolio] = []
    class Config:
        orm_mode = True
