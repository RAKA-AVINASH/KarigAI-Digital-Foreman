from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ServiceItem(BaseModel):
    description: str
    amount: float
    quantity: int = 1


class InvoiceCreateRequest(BaseModel):
    user_id: str
    customer_name: str
    customer_phone: Optional[str] = None
    services: List[ServiceItem]
    warranty_info: Optional[str] = None
    notes: Optional[str] = None
    template: str = "default"
    language: str = "hi-IN"


class DocumentCreateRequest(BaseModel):
    user_id: str
    document_type: str
    title: str
    content: Dict[str, Any]
    template: str = "default"
    language: str = "hi-IN"


class DocumentResponse(BaseModel):
    document_id: str
    user_id: str
    document_type: str
    file_path: str
    download_url: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True