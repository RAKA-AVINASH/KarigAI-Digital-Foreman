from sqlalchemy import Column, String, DateTime, Text, Integer
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True, index=True)
    phone_number = Column(String, unique=True, nullable=False, index=True)
    primary_language = Column(String, nullable=False, default="hi-IN")
    trade_type = Column(String, nullable=True)
    location_data = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    voice_sessions = relationship("VoiceSession", back_populates="user")
    documents = relationship("Document", back_populates="user")
    learning_progress = relationship("LearningProgress", back_populates="user")