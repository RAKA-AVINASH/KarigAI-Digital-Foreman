from sqlalchemy import Column, String, DateTime, Text, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class LearningProgress(Base):
    __tablename__ = "learning_progress"
    
    progress_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    course_id = Column(String, nullable=False)
    completion_percentage = Column(Float, default=0.0)
    last_accessed = Column(DateTime(timezone=True), nullable=True)
    quiz_scores = Column(Text, nullable=True)  # JSON string
    
    # Relationships
    user = relationship("User", back_populates="learning_progress")