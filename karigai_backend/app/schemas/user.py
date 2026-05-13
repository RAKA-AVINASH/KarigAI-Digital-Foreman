from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class UserBase(BaseModel):
    phone_number: str = Field(..., description="User's phone number")
    primary_language: str = Field(default="hi-IN", description="Primary language code")
    trade_type: Optional[str] = Field(None, description="User's trade/profession")
    location_data: Optional[Dict[str, Any]] = Field(None, description="Location information")


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    primary_language: Optional[str] = None
    trade_type: Optional[str] = None
    location_data: Optional[Dict[str, Any]] = None


class UserResponse(UserBase):
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True