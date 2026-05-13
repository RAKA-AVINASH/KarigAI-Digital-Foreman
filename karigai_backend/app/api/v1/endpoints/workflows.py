"""
End-to-end workflow orchestration endpoints.
Combines multiple services to provide complete user journeys.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_service_container, ServiceContainer
from app.core.error_handlers import VoiceProcessingError, VisionProcessingError, DocumentGenerationError

router = APIRouter()


class VoiceToInvoiceRequest(BaseModel):
    """Request for voice-to-invoice workflow"""
    user_id: str
    language_code: str = "hi-IN"
    customer_phone: Optional[str] = None


class VoiceToInvoiceResponse(BaseModel):
    """Response for voice-to-invoice workflow"""
    transcribed_text: str
    invoice_id: str
    document_url: str
    whatsapp_sent: bool
    confidence_score: float


class EquipmentTroubleshootingRequest(BaseModel):
    """Request for equipment troubleshooting workflow"""
    user_id: str
    language_code: str = "hi-IN"


class EquipmentTroubleshootingResponse(BaseModel):
    """Response for equipment troubleshooting workflow"""
    equipment_info: dict
    troubleshooting_steps: List[str]
    audio_guidance_url: Optional[str]
    confidence_score: float


class LearningRecommendationRequest(BaseModel):
    """Request for learning recommendation workflow"""
    user_id: str
    query_history: List[str]
    language_code: str = "hi-IN"


@router.post("/voice-to-invoice", response_model=VoiceToInvoiceResponse)
async def voice_to_invoice_workflow(
    audio_file: UploadFile = File(...),
    user_id: str = None,
    language_code: str = "hi-IN",
    customer_phone: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Complete workflow: Voice input → Invoice generation → WhatsApp delivery
    
    This workflow demonstrates end-to-end integration of:
    1. Voice recognition service
    2. Document generation service
    3. WhatsApp integration service
    """
    container = get_service_container(db)
    
    try:
        # Step 1: Convert speech to text
        voice_service = container.get_voice_service()
        voice_result = await voice_service.speech_to_text(
            audio_file=audio_file,
            user_id=user_id,
            language_code=language_code
        )
        
        if voice_result.confidence_score < 0.8:
            raise VoiceProcessingError(
                "Low confidence in voice recognition",
                details={"confidence": voice_result.confidence_score}
            )
        
        # Step 2: Extract invoice data from transcribed text
        # (In production, this would use NLP to extract structured data)
        invoice_data = {
            "user_id": user_id,
            "customer_name": "Customer",  # Would be extracted from voice
            "items": [],  # Would be extracted from voice
            "total_amount": 0.0,  # Would be calculated
            "language": language_code
        }
        
        # Step 3: Generate invoice document
        document_service = container.get_document_service()
        from app.schemas.document import InvoiceCreateRequest
        invoice_request = InvoiceCreateRequest(**invoice_data)
        document = await document_service.create_invoice(invoice_request)
        
        # Step 4: Send via WhatsApp if phone number provided
        whatsapp_sent = False
        if customer_phone:
            whatsapp_service = container.get_whatsapp_service()
            try:
                await whatsapp_service.send_document(
                    phone_number=customer_phone,
                    document_url=document.file_url,
                    message="आपका बिल तैयार है। (Your invoice is ready.)"
                )
                whatsapp_sent = True
            except Exception as e:
                # Log but don't fail the workflow
                pass
        
        return VoiceToInvoiceResponse(
            transcribed_text=voice_result.transcribed_text,
            invoice_id=document.document_id,
            document_url=document.file_url,
            whatsapp_sent=whatsapp_sent,
            confidence_score=voice_result.confidence_score
        )
        
    except VoiceProcessingError:
        raise
    except DocumentGenerationError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")


@router.post("/equipment-troubleshooting", response_model=EquipmentTroubleshootingResponse)
async def equipment_troubleshooting_workflow(
    image_file: UploadFile = File(...),
    user_id: str = None,
    language_code: str = "hi-IN",
    db: Session = Depends(get_db)
):
    """
    Complete workflow: Equipment image → Identification → Troubleshooting → Voice guidance
    
    This workflow demonstrates end-to-end integration of:
    1. Vision recognition service
    2. Equipment database lookup
    3. Translation service
    4. Text-to-speech service
    """
    container = get_service_container(db)
    
    try:
        # Step 1: Identify equipment from image
        vision_service = container.get_vision_service()
        equipment_result = await vision_service.identify_equipment(image_file, user_id)
        
        if equipment_result.confidence_score < 0.7:
            raise VisionProcessingError(
                "Unable to identify equipment clearly",
                details={"confidence": equipment_result.confidence_score}
            )
        
        # Step 2: Get troubleshooting steps
        # (In production, this would query a knowledge base)
        troubleshooting_steps = [
            "Check power connection",
            "Verify error code on display",
            "Test voltage at main terminals"
        ]
        
        # Step 3: Translate to local dialect if needed
        if language_code != "en-US":
            translation_service = container.get_translation_service()
            translated_steps = []
            for step in troubleshooting_steps:
                translated = await translation_service.translate(
                    text=step,
                    target_language=language_code
                )
                translated_steps.append(translated)
            troubleshooting_steps = translated_steps
        
        # Step 4: Generate audio guidance
        voice_service = container.get_voice_service()
        guidance_text = " । ".join(troubleshooting_steps)
        audio_result = await voice_service.text_to_speech(
            text=guidance_text,
            language_code=language_code
        )
        
        return EquipmentTroubleshootingResponse(
            equipment_info={
                "brand": equipment_result.brand,
                "model": equipment_result.model,
                "category": equipment_result.category
            },
            troubleshooting_steps=troubleshooting_steps,
            audio_guidance_url=audio_result.get("audio_url"),
            confidence_score=equipment_result.confidence_score
        )
        
    except VisionProcessingError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")


@router.post("/learning-recommendation")
async def learning_recommendation_workflow(
    request: LearningRecommendationRequest,
    db: Session = Depends(get_db)
):
    """
    Complete workflow: Query history → Gap analysis → Course recommendation → Offline sync
    
    This workflow demonstrates end-to-end integration of:
    1. Learning service
    2. User profile analysis
    3. Content personalization
    4. Offline content management
    """
    container = get_service_container(db)
    
    try:
        # Step 1: Get personalized recommendations
        learning_service = container.get_learning_service()
        recommendations = await learning_service.get_recommendations(request.user_id)
        
        # Step 2: Prepare offline content
        offline_manager = container.get_offline_manager()
        offline_courses = []
        for course in recommendations[:3]:  # Top 3 recommendations
            offline_data = await offline_manager.prepare_offline_content(
                content_type="course",
                content_id=course.course_id,
                user_id=request.user_id
            )
            offline_courses.append(offline_data)
        
        # Step 3: Track recommendation event
        user_service = container.get_user_service()
        await user_service.log_activity(
            user_id=request.user_id,
            activity_type="learning_recommendation",
            metadata={"course_count": len(recommendations)}
        )
        
        return {
            "recommendations": recommendations,
            "offline_ready": offline_courses,
            "total_count": len(recommendations)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")


@router.post("/sync-offline-data")
async def sync_offline_data_workflow(
    user_id: str,
    offline_data: dict,
    db: Session = Depends(get_db)
):
    """
    Complete workflow: Offline data → Validation → Sync → Conflict resolution
    
    This workflow demonstrates end-to-end integration of:
    1. Sync service
    2. Data validation
    3. Conflict resolution
    4. Storage management
    """
    container = get_service_container(db)
    
    try:
        # Step 1: Validate offline data
        sync_service = container.get_sync_service()
        validation_result = await sync_service.validate_offline_data(offline_data)
        
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid offline data: {validation_result.errors}"
            )
        
        # Step 2: Sync data with conflict resolution
        sync_result = await sync_service.sync_user_data(
            user_id=user_id,
            offline_data=offline_data
        )
        
        # Step 3: Update storage priorities
        storage_manager = container.get_storage_manager()
        await storage_manager.update_usage_patterns(
            user_id=user_id,
            synced_items=sync_result.synced_items
        )
        
        return {
            "synced_count": sync_result.synced_count,
            "conflicts_resolved": sync_result.conflicts_resolved,
            "failed_items": sync_result.failed_items
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync workflow failed: {str(e)}")
