from pydantic import BaseModel, Field
from typing import List, Optional


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str = Field(min_length=6)
    risk_tolerance: str
    interests: str = ""


class UserPublic(BaseModel):
    id: int
    username: str
    risk_tolerance: str
    interests: str = ""

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class AssetBase(BaseModel):
    ticker: str
    category: str
    rationale: Optional[str] = None
    weight: Optional[float] = None
    projected_cagr: Optional[float] = None

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
    """Optional password: if set (min 6 chars), user can log in via /auth/login."""

    password: Optional[str] = None

class UserProfile(UserProfileBase):
    id: int
    portfolios: List[Portfolio] = []
    class Config:
        from_attributes = True
