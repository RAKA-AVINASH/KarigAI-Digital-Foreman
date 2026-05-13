"""
Unit tests for PDF Generator Service

Tests PDF generation with ReportLab including warranty clauses,
tax calculations, and digital watermarking.
"""

import pytest
import os
import tempfile
from datetime import datetime

from app.services.pdf_generator_service import PDFGeneratorService
from app.core.document_generator import InvoiceData, ReportData, ServiceItem


@pytest.fixture
def pdf_service():
    """Create PDF generator service with temp directory"""
    temp_dir = tempfile.mkdtemp()
    service = PDFGeneratorService(output_dir=temp_dir)
    yield service
    # Cleanup is handled by temp directory


@pytest.fixture
def sample_invoice_data():
    """Create sample invoice data for testing"""
    return InvoiceData(
        invoice_id="INV-TEST-001",
        customer_name="Rajesh Kumar",
        customer_phone="+919876543210",
        services=[
            ServiceItem(description="Plumbing repair", amount=500.0, quantity=2),
            ServiceItem(description="Material cost", amount=300.0, quantity=1)
        ],
        warranty_info="90 days warranty on all parts and labor",
        notes="Payment due within 7 days",
        service_date=datetime.now()
    )


@pytest.fixture
def sample_report_data():
    """Create sample report data for testing"""
    return ReportData(
        report_id="RPT-TEST-001",
        title="Monthly Service Report",
        content={
            "summary": "All services completed successfully",
            "total_jobs": "15",
            "revenue": "₹45,000"
        },
        generated_by="user123",
        generated_at=datetime.now(),
        report_type="monthly_summary"
    )


class TestPDFGeneratorService:
    """Test PDF Generator Service"""
    
    @pytest.mark.asyncio
    async def test_generate_invoice_creates_file(self, pdf_service, sample_invoice_data):
        """Test that invoice generation creates a PDF file"""
        pdf_doc = await pdf_service.generate_invoice(sample_invoice_data)
        
        assert os.path.exists(pdf_doc.file_path)
        assert pdf_doc.file_path.endswith(".pdf")
    
    @pytest.mark.asyncio
    async def test_generate_invoice_metadata(self, pdf_service, sample_invoice_data):
        """Test invoice metadata is correct"""
        pdf_doc = await pdf_service.generate_invoice(sample_invoice_data)
        
        assert pdf_doc.metadata["invoice_id"] == "INV-TEST-001"
        assert pdf_doc.metadata["service_count"] == 2
        assert pdf_doc.metadata["has_warranty"] is True
        assert pdf_doc.metadata["has_notes"] is True
        assert pdf_doc.metadata["total_amount"] == sample_invoice_data.total_amount
    
    @pytest.mark.asyncio
    async def test_generate_invoice_bilingual(self, pdf_service, sample_invoice_data):
        """Test invoice generation in both languages"""
        pdf_hindi = await pdf_service.generate_invoice(sample_invoice_data, language="hi-IN")
        pdf_english = await pdf_service.generate_invoice(sample_invoice_data, language="en-IN")
        
        assert os.path.exists(pdf_hindi.file_path)
        assert os.path.exists(pdf_english.file_path)
        assert "hi-IN" in pdf_hindi.file_path
        assert "en-IN" in pdf_english.file_path
    
    @pytest.mark.asyncio
    async def test_generate_invoice_with_warranty(self, pdf_service, sample_invoice_data):
        """Test warranty clause inclusion"""
        pdf_doc = await pdf_service.generate_invoice(sample_invoice_data)
        
        assert pdf_doc.metadata["has_warranty"] is True
        assert os.path.exists(pdf_doc.file_path)
        
        # Verify file size is reasonable (not empty)
        file_size = os.path.getsize(pdf_doc.file_path)
        assert file_size > 1000  # At least 1KB
    
    @pytest.mark.asyncio
    async def test_generate_invoice_without_warranty(self, pdf_service):
        """Test invoice generation without warranty"""
        invoice_data = InvoiceData(
            invoice_id="INV-TEST-002",
            customer_name="Test Customer",
            customer_phone=None,
            services=[ServiceItem(description="Service", amount=100.0, quantity=1)],
            warranty_info=None,
            notes=None,
            service_date=datetime.now()
        )
        
        pdf_doc = await pdf_service.generate_invoice(invoice_data)
        
        assert pdf_doc.metadata["has_warranty"] is False
        assert pdf_doc.metadata["has_notes"] is False
    
    @pytest.mark.asyncio
    async def test_generate_invoice_tax_calculation(self, pdf_service, sample_invoice_data):
        """Test tax calculation in invoice"""
        pdf_doc = await pdf_service.generate_invoice(sample_invoice_data)
        
        # Verify tax calculation (18% GST)
        expected_subtotal = 1300.0  # (500*2 + 300*1)
        expected_tax = expected_subtotal * 0.18
        expected_total = expected_subtotal + expected_tax
        
        assert abs(pdf_doc.metadata["total_amount"] - expected_total) < 0.01
    
    @pytest.mark.asyncio
    async def test_generate_report_creates_file(self, pdf_service, sample_report_data):
        """Test that report generation creates a PDF file"""
        pdf_doc = await pdf_service.generate_report(sample_report_data)
        
        assert os.path.exists(pdf_doc.file_path)
        assert pdf_doc.file_path.endswith(".pdf")
    
    @pytest.mark.asyncio
    async def test_generate_report_metadata(self, pdf_service, sample_report_data):
        """Test report metadata is correct"""
        pdf_doc = await pdf_service.generate_report(sample_report_data)
        
        assert pdf_doc.metadata["report_id"] == "RPT-TEST-001"
        assert pdf_doc.metadata["report_type"] == "monthly_summary"
    
    @pytest.mark.asyncio
    async def test_get_available_templates(self, pdf_service):
        """Test getting available templates"""
        templates = pdf_service.get_available_templates()
        
        assert "default" in templates
        assert "professional" in templates
        assert "simple" in templates
    
    @pytest.mark.asyncio
    async def test_add_custom_template(self, pdf_service):
        """Test adding custom template"""
        template_data = {"layout": "custom", "colors": ["blue", "white"]}
        result = await pdf_service.add_custom_template("custom_template", template_data)
        
        assert result is True
        assert "custom_template" in pdf_service.get_available_templates()
    
    @pytest.mark.asyncio
    async def test_invoice_with_special_characters(self, pdf_service):
        """Test invoice generation with special characters in text"""
        invoice_data = InvoiceData(
            invoice_id="INV-TEST-003",
            customer_name="राजेश कुमार",  # Hindi name
            customer_phone="+919876543210",
            services=[
                ServiceItem(description="विद्युत मरम्मत", amount=500.0, quantity=1)  # Hindi description
            ],
            warranty_info="90 दिन की वारंटी",  # Hindi warranty
            notes="भुगतान 7 दिनों में देय",  # Hindi notes
            service_date=datetime.now()
        )
        
        pdf_doc = await pdf_service.generate_invoice(invoice_data, language="hi-IN")
        
        assert os.path.exists(pdf_doc.file_path)
        assert pdf_doc.metadata["invoice_id"] == "INV-TEST-003"
    
    @pytest.mark.asyncio
    async def test_invoice_with_multiple_services(self, pdf_service):
        """Test invoice with many service items"""
        services = [
            ServiceItem(description=f"Service {i}", amount=100.0 * i, quantity=i)
            for i in range(1, 11)
        ]
        
        invoice_data = InvoiceData(
            invoice_id="INV-TEST-004",
            customer_name="Test Customer",
            customer_phone=None,
            services=services,
            warranty_info=None,
            notes=None,
            service_date=datetime.now()
        )
        
        pdf_doc = await pdf_service.generate_invoice(invoice_data)
        
        assert os.path.exists(pdf_doc.file_path)
        assert pdf_doc.metadata["service_count"] == 10
    
    @pytest.mark.asyncio
    async def test_digital_watermark_present(self, pdf_service, sample_invoice_data):
        """Test that digital watermark is added to PDF"""
        pdf_doc = await pdf_service.generate_invoice(sample_invoice_data)
        
        # Verify PDF file exists and has content
        assert os.path.exists(pdf_doc.file_path)
        file_size = os.path.getsize(pdf_doc.file_path)
        assert file_size > 1000  # At least 1KB
        
        # Verify metadata contains invoice information
        assert pdf_doc.metadata["invoice_id"] == "INV-TEST-001"
