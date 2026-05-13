"""
Document Service

This module provides document generation and management services.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from app.core.document_generator import (
    DocumentGenerator,
    InvoiceData,
    ReportData,
    ServiceItem,
    PDFDocument
)
from app.models.document import Document
from app.schemas.document import (
    InvoiceCreateRequest,
    DocumentCreateRequest,
    DocumentResponse
)
from sqlalchemy.orm import Session


class DocumentService:
    """Service for managing document generation and storage"""
    
    def __init__(self, generator: DocumentGenerator):
        """
        Initialize document service
        
        Args:
            generator: Document generator implementation to use
        """
        self.generator = generator
    
    async def create_invoice(
        self,
        request: InvoiceCreateRequest,
        db: Session
    ) -> DocumentResponse:
        """
        Create an invoice document
        
        Args:
            request: Invoice creation request
            db: Database session
            
        Returns:
            Document response with file path and metadata
        """
        # Generate unique invoice ID
        invoice_id = f"INV-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        
        # Convert request to InvoiceData
        invoice_data = InvoiceData(
            invoice_id=invoice_id,
            customer_name=request.customer_name,
            customer_phone=request.customer_phone,
            services=[
                ServiceItem(
                    description=item.description,
                    amount=item.amount,
                    quantity=item.quantity
                )
                for item in request.services
            ],
            warranty_info=request.warranty_info,
            notes=request.notes,
            service_date=datetime.now()
        )
        
        # Generate PDF document
        pdf_doc = await self.generator.generate_invoice(
            data=invoice_data,
            template=request.template,
            language=request.language
        )
        
        # Create document record in database
        document = Document(
            document_id=str(uuid.uuid4()),
            user_id=request.user_id,
            document_type="invoice",
            file_path=pdf_doc.file_path,
            metadata=str(pdf_doc.metadata)
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Return response
        return DocumentResponse(
            document_id=document.document_id,
            user_id=document.user_id,
            document_type=document.document_type,
            file_path=document.file_path,
            download_url=f"/api/v1/documents/{document.document_id}/download",
            metadata=pdf_doc.metadata,
            created_at=document.created_at
        )
    
    async def create_report(
        self,
        request: DocumentCreateRequest,
        db: Session
    ) -> DocumentResponse:
        """
        Create a report document
        
        Args:
            request: Document creation request
            db: Database session
            
        Returns:
            Document response with file path and metadata
        """
        # Generate unique report ID
        report_id = f"RPT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        
        # Convert request to ReportData
        report_data = ReportData(
            report_id=report_id,
            title=request.title,
            content=request.content,
            generated_by=request.user_id,
            generated_at=datetime.now(),
            report_type=request.document_type
        )
        
        # Generate PDF document
        pdf_doc = await self.generator.generate_report(
            data=report_data,
            template=request.template,
            language=request.language
        )
        
        # Create document record in database
        document = Document(
            document_id=str(uuid.uuid4()),
            user_id=request.user_id,
            document_type=request.document_type,
            file_path=pdf_doc.file_path,
            metadata=str(pdf_doc.metadata)
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Return response
        return DocumentResponse(
            document_id=document.document_id,
            user_id=document.user_id,
            document_type=document.document_type,
            file_path=document.file_path,
            download_url=f"/api/v1/documents/{document.document_id}/download",
            metadata=pdf_doc.metadata,
            created_at=document.created_at
        )
    
    def get_available_templates(self) -> list[str]:
        """Get list of available document templates"""
        return self.generator.get_available_templates()
    
    async def add_custom_template(
        self,
        template_id: str,
        template_data: Dict[str, Any]
    ) -> bool:
        """Add a custom document template"""
        return await self.generator.add_custom_template(template_id, template_data)
