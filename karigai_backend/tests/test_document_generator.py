"""
Unit tests for Document Generator Interface

Tests the document generator interface, data models, and template functionality.
"""

import pytest
from datetime import datetime
from typing import List, Dict, Any

from app.core.document_generator import (
    DocumentGenerator,
    InvoiceData,
    ReportData,
    ServiceItem,
    PDFDocument,
    InvoiceTemplate
)


class MockDocumentGenerator(DocumentGenerator):
    """Mock implementation of DocumentGenerator for testing"""
    
    def __init__(self):
        self.templates = ["default", "professional", "simple"]
        self.custom_templates = {}
    
    async def generate_invoice(
        self, 
        data: InvoiceData, 
        template: str = "default",
        language: str = "hi-IN"
    ) -> PDFDocument:
        """Mock invoice generation"""
        file_path = f"/tmp/invoice_{data.invoice_id}.pdf"
        metadata = {
            "invoice_id": data.invoice_id,
            "template": template,
            "language": language,
            "total_amount": data.total_amount
        }
        return PDFDocument(file_path=file_path, metadata=metadata)
    
    async def generate_report(
        self, 
        data: ReportData, 
        template: str = "default",
        language: str = "hi-IN"
    ) -> PDFDocument:
        """Mock report generation"""
        file_path = f"/tmp/report_{data.report_id}.pdf"
        metadata = {
            "report_id": data.report_id,
            "template": template,
            "language": language,
            "report_type": data.report_type
        }
        return PDFDocument(file_path=file_path, metadata=metadata)
    
    def get_available_templates(self) -> List[str]:
        """Return available templates"""
        return self.templates + list(self.custom_templates.keys())
    
    async def add_custom_template(
        self, 
        template_id: str, 
        template_data: Dict[str, Any]
    ) -> bool:
        """Add custom template"""
        self.custom_templates[template_id] = template_data
        return True


class TestServiceItem:
    """Test ServiceItem data model"""
    
    def test_service_item_creation(self):
        """Test creating a service item"""
        item = ServiceItem(
            description="Plumbing repair",
            amount=500.0,
            quantity=2
        )
        
        assert item.description == "Plumbing repair"
        assert item.amount == 500.0
        assert item.quantity == 2
    
    def test_service_item_total_calculation(self):
        """Test total calculation for service item"""
        item = ServiceItem(
            description="Electrical work",
            amount=750.0,
            quantity=3
        )
        
        assert item.total == 2250.0
    
    def test_service_item_default_quantity(self):
        """Test default quantity is 1"""
        item = ServiceItem(
            description="Consultation",
            amount=200.0
        )
        
        assert item.quantity == 1
        assert item.total == 200.0


class TestInvoiceData:
    """Test InvoiceData model"""
    
    def test_invoice_data_creation(self):
        """Test creating invoice data"""
        services = [
            ServiceItem(description="Service 1", amount=100.0, quantity=2),
            ServiceItem(description="Service 2", amount=150.0, quantity=1)
        ]
        
        invoice = InvoiceData(
            invoice_id="INV-001",
            customer_name="Rajesh Kumar",
            customer_phone="+919876543210",
            services=services,
            warranty_info="90 days warranty",
            notes="Payment due in 7 days",
            service_date=datetime.now()
        )
        
        assert invoice.invoice_id == "INV-001"
        assert invoice.customer_name == "Rajesh Kumar"
        assert len(invoice.services) == 2
    
    def test_invoice_subtotal_calculation(self):
        """Test subtotal calculation"""
        services = [
            ServiceItem(description="Service 1", amount=100.0, quantity=2),
            ServiceItem(description="Service 2", amount=150.0, quantity=1)
        ]
        
        invoice = InvoiceData(
            invoice_id="INV-002",
            customer_name="Test Customer",
            customer_phone=None,
            services=services,
            warranty_info=None,
            notes=None,
            service_date=datetime.now()
        )
        
        assert invoice.subtotal == 350.0
    
    def test_invoice_tax_calculation(self):
        """Test tax calculation (18% GST)"""
        services = [
            ServiceItem(description="Service", amount=1000.0, quantity=1)
        ]
        
        invoice = InvoiceData(
            invoice_id="INV-003",
            customer_name="Test Customer",
            customer_phone=None,
            services=services,
            warranty_info=None,
            notes=None,
            service_date=datetime.now()
        )
        
        assert invoice.tax_amount == 180.0
    
    def test_invoice_total_calculation(self):
        """Test total amount calculation"""
        services = [
            ServiceItem(description="Service", amount=1000.0, quantity=1)
        ]
        
        invoice = InvoiceData(
            invoice_id="INV-004",
            customer_name="Test Customer",
            customer_phone=None,
            services=services,
            warranty_info=None,
            notes=None,
            service_date=datetime.now()
        )
        
        assert invoice.total_amount == 1180.0


class TestReportData:
    """Test ReportData model"""
    
    def test_report_data_creation(self):
        """Test creating report data"""
        report = ReportData(
            report_id="RPT-001",
            title="Monthly Service Report",
            content={"summary": "All services completed"},
            generated_by="user123",
            generated_at=datetime.now(),
            report_type="monthly_summary"
        )
        
        assert report.report_id == "RPT-001"
        assert report.title == "Monthly Service Report"
        assert report.report_type == "monthly_summary"


class TestPDFDocument:
    """Test PDFDocument class"""
    
    def test_pdf_document_creation(self):
        """Test creating PDF document"""
        doc = PDFDocument(
            file_path="/tmp/test.pdf",
            metadata={"invoice_id": "INV-001"}
        )
        
        assert doc.file_path == "/tmp/test.pdf"
        assert doc.metadata["invoice_id"] == "INV-001"
        assert doc.created_at is not None


class TestInvoiceTemplate:
    """Test InvoiceTemplate translations"""
    
    def test_english_translations(self):
        """Test English translations"""
        translations = InvoiceTemplate.get_translations("en-IN")
        
        assert translations["invoice"] == "INVOICE"
        assert translations["customer_details"] == "Customer Details"
        assert translations["total"] == "Total Amount"
    
    def test_hindi_translations(self):
        """Test Hindi translations"""
        translations = InvoiceTemplate.get_translations("hi-IN")
        
        assert translations["invoice"] == "बिल"
        assert translations["customer_details"] == "ग्राहक विवरण"
        assert translations["total"] == "कुल राशि"
    
    def test_currency_formatting(self):
        """Test currency formatting"""
        formatted = InvoiceTemplate.format_currency(1234.56)
        assert formatted == "₹1,234.56"
        
        formatted = InvoiceTemplate.format_currency(1000000.00)
        assert formatted == "₹1,000,000.00"
    
    def test_date_formatting_english(self):
        """Test date formatting for English"""
        date = datetime(2024, 1, 15)
        formatted = InvoiceTemplate.format_date(date, "en-IN")
        assert formatted == "15 January 2024"
    
    def test_date_formatting_hindi(self):
        """Test date formatting for Hindi"""
        date = datetime(2024, 1, 15)
        formatted = InvoiceTemplate.format_date(date, "hi-IN")
        assert formatted == "15/01/2024"


@pytest.mark.asyncio
class TestDocumentGenerator:
    """Test DocumentGenerator interface"""
    
    async def test_generate_invoice(self):
        """Test invoice generation"""
        generator = MockDocumentGenerator()
        
        services = [
            ServiceItem(description="Repair work", amount=500.0, quantity=1)
        ]
        
        invoice_data = InvoiceData(
            invoice_id="INV-TEST-001",
            customer_name="Test Customer",
            customer_phone="+919876543210",
            services=services,
            warranty_info="30 days",
            notes="Test invoice",
            service_date=datetime.now()
        )
        
        pdf_doc = await generator.generate_invoice(invoice_data)
        
        assert pdf_doc.file_path.endswith(".pdf")
        assert pdf_doc.metadata["invoice_id"] == "INV-TEST-001"
    
    async def test_generate_report(self):
        """Test report generation"""
        generator = MockDocumentGenerator()
        
        report_data = ReportData(
            report_id="RPT-TEST-001",
            title="Test Report",
            content={"data": "test"},
            generated_by="user123",
            generated_at=datetime.now(),
            report_type="test"
        )
        
        pdf_doc = await generator.generate_report(report_data)
        
        assert pdf_doc.file_path.endswith(".pdf")
        assert pdf_doc.metadata["report_id"] == "RPT-TEST-001"
    
    async def test_get_available_templates(self):
        """Test getting available templates"""
        generator = MockDocumentGenerator()
        
        templates = generator.get_available_templates()
        
        assert "default" in templates
        assert "professional" in templates
        assert "simple" in templates
    
    async def test_add_custom_template(self):
        """Test adding custom template"""
        generator = MockDocumentGenerator()
        
        template_data = {"layout": "custom", "colors": ["blue", "white"]}
        result = await generator.add_custom_template("custom_template", template_data)
        
        assert result is True
        assert "custom_template" in generator.get_available_templates()
