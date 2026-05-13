from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class VoiceProcessRequest(BaseModel):
    text: str = Field(..., description="Text to convert to speech")
    language_code: Optional[str] = Field("hi-IN", description="Language code")
    user_id: Optional[str] = Field(None, description="User ID")


class VoiceProcessResponse(BaseModel):
    session_id: str
    transcribed_text: str
    language_detected: str
    confidence_score: float
    processing_time: float
    created_at: datetime
    
    class Config:
        from_attributes = True