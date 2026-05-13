from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.schemas.document import DocumentCreateRequest, DocumentResponse, InvoiceCreateRequest
from app.services.document_service import DocumentService

router = APIRouter()


@router.post("/invoice", response_model=DocumentResponse)
async def create_invoice(
    request: InvoiceCreateRequest,
    db: Session = Depends(get_db)
):
    """Generate invoice document"""
    document_service = DocumentService(db)
    
    try:
        result = await document_service.create_invoice(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=DocumentResponse)
async def create_document(
    request: DocumentCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a generic document"""
    document_service = DocumentService(db)
    
    try:
        result = await document_service.create_document(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}", response_model=List[DocumentResponse])
async def get_user_documents(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get all documents for a user"""
    document_service = DocumentService(db)
    
    try:
        documents = await document_service.get_user_documents(user_id)
        return documents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    """Get document by ID"""
    document_service = DocumentService(db)
    
    try:
        document = await document_service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return document
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{document_id}/share")
async def share_document(
    document_id: str,
    phone_number: str,
    db: Session = Depends(get_db)
):
    """Share document via WhatsApp"""
    document_service = DocumentService(db)
    
    try:
        result = await document_service.share_document(document_id, phone_number)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/available")
async def get_available_templates():
    """Get list of available document templates"""
    document_service = DocumentService(None)
    templates = await document_service.get_available_templates()
    return {"templates": templates}