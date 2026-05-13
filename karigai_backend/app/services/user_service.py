from sqlalchemy.orm import Session
from typing import Optional
import uuid

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, db: Session):
        self.db = db
    
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user"""
        user = User(
            user_id=str(uuid.uuid4()),
            phone_number=user_data.phone_number,
            primary_language=user_data.primary_language,
            trade_type=user_data.trade_type,
            location_data=str(user_data.location_data) if user_data.location_data else None
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter(User.user_id == user_id).first()
    
    async def get_user_by_phone(self, phone_number: str) -> Optional[User]:
        """Get user by phone number"""
        return self.db.query(User).filter(User.phone_number == phone_number).first()
    
    async def update_user(self, user_id: str, user_data: UserUpdate) -> Optional[User]:
        """Update user information"""
        user = await self.get_user(user_id)
        if not user:
            return None
        
        update_data = user_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field == "location_data" and value:
                value = str(value)
            setattr(user, field, value)
        
        self.db.commit()
        self.db.refresh(user)
        return user