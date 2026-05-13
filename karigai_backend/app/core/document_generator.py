"""
Document Generator Interface and Base Classes

This module provides the abstract interface for document generation
and base implementations for PDF generation with bilingual support.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass


@dataclass
class ServiceItem:
    """Represents a service item in an invoice"""
    description: str
    amount: float
    quantity: int = 1
    
    @property
    def total(self) -> float:
        """Calculate total amount for this service item"""
        return self.amount * self.quantity


@dataclass
class InvoiceData:
    """Data model for invoice generation"""
    invoice_id: str
    customer_name: str
    customer_phone: Optional[str]
    services: List[ServiceItem]
    warranty_info: Optional[str]
    notes: Optional[str]
    service_date: datetime
    user_name: Optional[str] = None
    user_phone: Optional[str] = None
    user_address: Optional[str] = None
    
    @property
    def subtotal(self) -> float:
        """Calculate subtotal of all services"""
        return sum(item.total for item in self.services)
    
    @property
    def tax_amount(self) -> float:
        """Calculate tax amount (18% GST)"""
        return self.subtotal * 0.18
    
    @property
    def total_amount(self) -> float:
        """Calculate total amount including tax"""
        return self.subtotal + self.tax_amount


@dataclass
class ReportData:
    """Data model for report generation"""
    report_id: str
    title: str
    content: Dict[str, Any]
    generated_by: str
    generated_at: datetime
    report_type: str
    metadata: Optional[Dict[str, Any]] = None


class PDFDocument:
    """Represents a generated PDF document"""
    
    def __init__(self, file_path: str, metadata: Optional[Dict[str, Any]] = None):
        self.file_path = file_path
        self.metadata = metadata or {}
        self.created_at = datetime.now()
    
    def __repr__(self) -> str:
        return f"PDFDocument(file_path='{self.file_path}')"


class DocumentGenerator(ABC):
    """Abstract base class for document generation"""
    
    @abstractmethod
    async def generate_invoice(
        self, 
        data: InvoiceData, 
        template: str = "default",
        language: str = "hi-IN"
    ) -> PDFDocument:
        """
        Generate an invoice PDF document
        
        Args:
            data: Invoice data to generate document from
            template: Template identifier to use
            language: Language code (hi-IN for Hindi, en-IN for English)
            
        Returns:
            PDFDocument object with file path and metadata
        """
        pass
    
    @abstractmethod
    async def generate_report(
        self, 
        data: ReportData, 
        template: str = "default",
        language: str = "hi-IN"
    ) -> PDFDocument:
        """
        Generate a report PDF document
        
        Args:
            data: Report data to generate document from
            template: Template identifier to use
            language: Language code
            
        Returns:
            PDFDocument object with file path and metadata
        """
        pass
    
    @abstractmethod
    def get_available_templates(self) -> List[str]:
        """
        Get list of available template identifiers
        
        Returns:
            List of template names
        """
        pass
    
    @abstractmethod
    async def add_custom_template(
        self, 
        template_id: str, 
        template_data: Dict[str, Any]
    ) -> bool:
        """
        Add a custom template to the generator
        
        Args:
            template_id: Unique identifier for the template
            template_data: Template configuration and layout data
            
        Returns:
            True if template was added successfully
        """
        pass


class InvoiceTemplate:
    """Base class for invoice templates with bilingual support"""
    
    # English translations
    EN_TRANSLATIONS = {
        "invoice": "INVOICE",
        "invoice_no": "Invoice No",
        "date": "Date",
        "customer_details": "Customer Details",
        "name": "Name",
        "phone": "Phone",
        "service_details": "Service Details",
        "description": "Description",
        "quantity": "Qty",
        "rate": "Rate",
        "amount": "Amount",
        "subtotal": "Subtotal",
        "tax": "Tax (GST 18%)",
        "total": "Total Amount",
        "warranty": "Warranty Information",
        "notes": "Notes",
        "service_provider": "Service Provider",
        "thank_you": "Thank you for your business!",
        "currency": "₹"
    }
    
    # Hindi translations
    HI_TRANSLATIONS = {
        "invoice": "बिल",
        "invoice_no": "बिल नंबर",
        "date": "तारीख",
        "customer_details": "ग्राहक विवरण",
        "name": "नाम",
        "phone": "फोन",
        "service_details": "सेवा विवरण",
        "description": "विवरण",
        "quantity": "मात्रा",
        "rate": "दर",
        "amount": "राशि",
        "subtotal": "उप-योग",
        "tax": "कर (जीएसटी 18%)",
        "total": "कुल राशि",
        "warranty": "वारंटी जानकारी",
        "notes": "टिप्पणी",
        "service_provider": "सेवा प्रदाता",
        "thank_you": "आपके व्यवसाय के लिए धन्यवाद!",
        "currency": "₹"
    }
    
    @classmethod
    def get_translations(cls, language: str) -> Dict[str, str]:
        """Get translations for specified language"""
        if language.startswith("hi"):
            return cls.HI_TRANSLATIONS
        return cls.EN_TRANSLATIONS
    
    @classmethod
    def format_currency(cls, amount: float) -> str:
        """Format currency amount in Indian format"""
        return f"₹{amount:,.2f}"
    
    @classmethod
    def format_date(cls, date: datetime, language: str) -> str:
        """Format date according to language preference"""
        if language.startswith("hi"):
            return date.strftime("%d/%m/%Y")
        return date.strftime("%d %B %Y")
