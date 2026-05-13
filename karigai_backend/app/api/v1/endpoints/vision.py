from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.schemas.vision import (
    VisionAnalysisResponse, 
    EquipmentIdentificationResponse,
    InventoryCountResponse
)
from app.services.vision_service import VisionService

router = APIRouter()


@router.post("/identify-equipment", response_model=EquipmentIdentificationResponse)
async def identify_equipment(
    image_file: UploadFile = File(...),
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Identify equipment from image"""
    vision_service = VisionService(db)
    
    try:
        result = await vision_service.identify_equipment(image_file, user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect-error-codes")
async def detect_error_codes(
    image_file: UploadFile = File(...),
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Detect error codes from image"""
    vision_service = VisionService(db)
    
    try:
        result = await vision_service.detect_error_codes(image_file, user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-pattern", response_model=VisionAnalysisResponse)
async def analyze_pattern(
    image_file: UploadFile = File(...),
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Analyze traditional patterns from image"""
    vision_service = VisionService(db)
    
    try:
        result = await vision_service.analyze_pattern(image_file, user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assess-quality")
async def assess_quality(
    product_type: str,
    image_file: UploadFile = File(...),
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Assess product quality from image"""
    vision_service = VisionService(db)
    
    try:
        result = await vision_service.assess_quality(image_file, product_type, user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-text")
async def extract_text(
    image_file: UploadFile = File(...),
    language_code: str = "hi-IN",
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Extract text from image using OCR"""
    vision_service = VisionService(db)
    
    try:
        result = await vision_service.extract_text(image_file, language_code, user_id)
        return {"extracted_text": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/count-inventory", response_model=InventoryCountResponse)
async def count_inventory(
    image_file: UploadFile = File(...),
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Count inventory items from image"""
    vision_service = VisionService(db)
    
    try:
        result = await vision_service.count_inventory(image_file, user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
