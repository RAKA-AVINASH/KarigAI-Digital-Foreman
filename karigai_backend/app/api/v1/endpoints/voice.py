from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.schemas.voice import VoiceProcessRequest, VoiceProcessResponse
from app.services.voice_service import VoiceService

router = APIRouter()


@router.post("/speech-to-text", response_model=VoiceProcessResponse)
async def speech_to_text(
    audio_file: UploadFile = File(...),
    user_id: str = None,
    language_code: str = "hi-IN",
    db: Session = Depends(get_db)
):
    """Convert speech to text"""
    voice_service = VoiceService(db)
    
    try:
        result = await voice_service.speech_to_text(
            audio_file=audio_file,
            user_id=user_id,
            language_code=language_code
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/text-to-speech")
async def text_to_speech(
    request: VoiceProcessRequest,
    db: Session = Depends(get_db)
):
    """Convert text to speech"""
    voice_service = VoiceService(db)
    
    try:
        audio_file = await voice_service.text_to_speech(
            text=request.text,
            language_code=request.language_code or "hi-IN"
        )
        return {"audio_url": audio_file}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect-language")
async def detect_language(
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Detect language from audio"""
    voice_service = VoiceService(db)
    
    try:
        language = await voice_service.detect_language(audio_file)
        return {"detected_language": language}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/supported-languages")
async def get_supported_languages():
    """Get list of supported languages"""
    from app.core.config import settings
    return {"supported_languages": settings.SUPPORTED_LANGUAGES}