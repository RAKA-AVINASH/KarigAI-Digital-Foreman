from sqlalchemy import Column, String, DateTime, Text, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class VoiceSession(Base):
    __tablename__ = "voice_sessions"
    
    session_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    audio_file_path = Column(String, nullable=True)
    transcribed_text = Column(Text, nullable=True)
    language_detected = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="voice_sessions")