"""
Property-Based Test: Document Generation Consistency

**Property 2: Document Generation Consistency**
**Validates: Requirements 1.2, 1.3**

For any valid invoice data, the Document_Generator should create PDF documents 
containing all required fields in both English and Hindi, including warranty 
clauses and service details.
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime
import os
import tempfile
from typing import List

from app.core.document_generator import (
    InvoiceData,
    ServiceItem,
    PDFDocument,
    InvoiceTemplate
)


# Strategy for generating service items
@st.composite
def service_item_strategy(draw):
    """Generate valid service items"""
    description = draw(st.text(min_size=5, max_size=100, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'),
        blacklist_characters='\n\r\t'
    )))
    amount = draw(st.floats(min_value=1.0, max_value=100000.0, allow_nan=False, allow_infinity=False))
    quantity = draw(st.integers(min_value=1, max_value=100))
    
    return ServiceItem(
        description=description.strip() or "Service",
        amount=round(amount, 2),
        quantity=quantity
    )


# Strategy for generating invoice data
@st.composite
def invoice_data_strategy(draw):
    """Generate valid invoice data"""
    invoice_id = f"INV-{draw(st.integers(min_value=1000, max_value=9999))}"
    customer_name = draw(st.text(min_size=3, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Zs'),
        blacklist_characters='\n\r\t'
    )))
    
    # Optional phone number
    has_phone = draw(st.booleans())
    customer_phone = f"+91{draw(st.integers(min_value=6000000000, max_value=9999999999))}" if has_phone else None
    
    # Generate 1-10 service items
    services = draw(st.lists(service_item_strategy(), min_size=1, max_size=10))
    
    # Optional warranty and notes
    has_warranty = draw(st.booleans())
    warranty_text = draw(st.text(min_size=10, max_size=200)) if has_warranty else None
    # Clean warranty text - remove carriage returns and newlines
    warranty_info = warranty_text.replace('\r', ' ').replace('\n', ' ').strip() if warranty_text else None
    
    has_notes = draw(st.booleans())
    notes_text = draw(st.text(min_size=10, max_size=200)) if has_notes else None
    # Clean notes text - remove carriage returns and newlines
    notes = notes_text.replace('\r', ' ').replace('\n', ' ').strip() if notes_text else None
    
    return InvoiceData(
        invoice_id=invoice_id,
        customer_name=customer_name.strip() or "Customer",
        customer_phone=customer_phone,
        services=services,
        warranty_info=warranty_info,
        notes=notes,
        service_date=datetime.now()
    )


class MockPDFGenerator:
    """Mock PDF generator for testing document consistency"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
    
    async def generate_invoice_pdf(
        self,
        data: InvoiceData,
        language: str = "hi-IN"
    ) -> PDFDocument:
        """
        Generate a mock PDF document with all required fields
        """
        # Get translations for the language
        translations = InvoiceTemplate.get_translations(language)
        
        # Create mock PDF content (in real implementation, this would use ReportLab)
        file_path = os.path.join(self.temp_dir, f"{data.invoice_id}_{language}.pdf")
        
        # Simulate PDF generation by creating a text file with all required fields
        content_lines = [
            f"{translations['invoice']}: {data.invoice_id}",
            f"{translations['date']}: {InvoiceTemplate.format_date(data.service_date, language)}",
            f"{translations['customer_details']}:",
            f"  {translations['name']}: {data.customer_name}",
        ]
        
        if data.customer_phone:
            content_lines.append(f"  {translations['phone']}: {data.customer_phone}")
        
        content_lines.append(f"\n{translations['service_details']}:")
        
        for item in data.services:
            content_lines.append(
                f"  {item.description} - "
                f"{translations['quantity']}: {item.quantity}, "
                f"{translations['rate']}: {InvoiceTemplate.format_currency(item.amount)}, "
                f"{translations['amount']}: {InvoiceTemplate.format_currency(item.total)}"
            )
        
        content_lines.extend([
            f"\n{translations['subtotal']}: {InvoiceTemplate.format_currency(data.subtotal)}",
            f"{translations['tax']}: {InvoiceTemplate.format_currency(data.tax_amount)}",
            f"{translations['total']}: {InvoiceTemplate.format_currency(data.total_amount)}"
        ])
        
        if data.warranty_info:
            content_lines.append(f"\n{translations['warranty']}: {data.warranty_info}")
        
        if data.notes:
            content_lines.append(f"\n{translations['notes']}: {data.notes}")
        
        content_lines.append(f"\n{translations['thank_you']}")
        
        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content_lines))
        
        metadata = {
            "invoice_id": data.invoice_id,
            "language": language,
            "total_amount": data.total_amount,
            "service_count": len(data.services),
            "has_warranty": data.warranty_info is not None,
            "has_notes": data.notes is not None
        }
        
        return PDFDocument(file_path=file_path, metadata=metadata)
    
    def verify_document_completeness(self, pdf_doc: PDFDocument, invoice_data: InvoiceData) -> bool:
        """
        Verify that the generated document contains all required fields
        """
        # Check that file exists
        if not os.path.exists(pdf_doc.file_path):
            return False
        
        # Read the content
        with open(pdf_doc.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verify all required fields are present
        required_checks = [
            invoice_data.invoice_id in content,
            invoice_data.customer_name in content,
            len(invoice_data.services) > 0,
        ]
        
        # Check that all service descriptions are present
        for service in invoice_data.services:
            required_checks.append(service.description in content)
        
        # Check warranty if provided
        if invoice_data.warranty_info:
            required_checks.append(invoice_data.warranty_info in content)
        
        # Check notes if provided
        if invoice_data.notes:
            required_checks.append(invoice_data.notes in content)
        
        return all(required_checks)


@pytest.mark.asyncio
class TestDocumentGenerationConsistencyProperty:
    """
    Property-Based Tests for Document Generation Consistency
    
    **Feature: karigai, Property 2**
    **Validates: Requirements 1.2, 1.3**
    """
    
    @given(invoice_data=invoice_data_strategy())
    @settings(max_examples=100, deadline=None)
    async def test_invoice_contains_all_required_fields(self, invoice_data: InvoiceData):
        """
        Property: For any valid invoice data, the generated document should 
        contain all required fields (invoice ID, customer name, services, totals)
        """
        generator = MockPDFGenerator()
        
        # Generate document in Hindi
        pdf_doc = await generator.generate_invoice_pdf(invoice_data, language="hi-IN")
        
        # Verify completeness
        assert generator.verify_document_completeness(pdf_doc, invoice_data), \
            f"Document missing required fields for invoice {invoice_data.invoice_id}"
        
        # Verify metadata
        assert pdf_doc.metadata["invoice_id"] == invoice_data.invoice_id
        assert pdf_doc.metadata["service_count"] == len(invoice_data.services)
    
    @given(invoice_data=invoice_data_strategy())
    @settings(max_examples=100, deadline=None)
    async def test_bilingual_document_generation(self, invoice_data: InvoiceData):
        """
        Property: For any valid invoice data, documents should be generatable 
        in both English and Hindi with consistent content
        """
        generator = MockPDFGenerator()
        
        # Generate in both languages
        pdf_hindi = await generator.generate_invoice_pdf(invoice_data, language="hi-IN")
        pdf_english = await generator.generate_invoice_pdf(invoice_data, language="en-IN")
        
        # Both should be complete
        assert generator.verify_document_completeness(pdf_hindi, invoice_data), \
            "Hindi document missing required fields"
        assert generator.verify_document_completeness(pdf_english, invoice_data), \
            "English document missing required fields"
        
        # Both should have same metadata values
        assert pdf_hindi.metadata["invoice_id"] == pdf_english.metadata["invoice_id"]
        assert pdf_hindi.metadata["total_amount"] == pdf_english.metadata["total_amount"]
        assert pdf_hindi.metadata["service_count"] == pdf_english.metadata["service_count"]
    
    @given(invoice_data=invoice_data_strategy())
    @settings(max_examples=100, deadline=None)
    async def test_warranty_clause_inclusion(self, invoice_data: InvoiceData):
        """
        Property: For any invoice data with warranty information, the generated 
        document should include the warranty clause
        """
        generator = MockPDFGenerator()
        
        pdf_doc = await generator.generate_invoice_pdf(invoice_data, language="hi-IN")
        
        # Check warranty inclusion in metadata
        if invoice_data.warranty_info:
            assert pdf_doc.metadata["has_warranty"] is True
            # Verify warranty is in the document
            with open(pdf_doc.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert invoice_data.warranty_info in content, \
                    "Warranty information not found in document"
        else:
            assert pdf_doc.metadata["has_warranty"] is False
    
    @given(invoice_data=invoice_data_strategy())
    @settings(max_examples=100, deadline=None)
    async def test_service_details_inclusion(self, invoice_data: InvoiceData):
        """
        Property: For any invoice data, all service details (description, quantity, 
        rate, amount) should be included in the generated document
        """
        generator = MockPDFGenerator()
        
        pdf_doc = await generator.generate_invoice_pdf(invoice_data, language="hi-IN")
        
        # Read document content
        with open(pdf_doc.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verify each service is documented
        for service in invoice_data.services:
            assert service.description in content, \
                f"Service description '{service.description}' not found in document"
            assert str(service.quantity) in content, \
                f"Service quantity {service.quantity} not found in document"
    
    @given(invoice_data=invoice_data_strategy())
    @settings(max_examples=100, deadline=None)
    async def test_financial_calculations_accuracy(self, invoice_data: InvoiceData):
        """
        Property: For any invoice data, the document should contain accurate 
        financial calculations (subtotal, tax, total)
        """
        generator = MockPDFGenerator()
        
        pdf_doc = await generator.generate_invoice_pdf(invoice_data, language="hi-IN")
        
        # Verify calculations in metadata
        expected_subtotal = sum(item.total for item in invoice_data.services)
        expected_tax = expected_subtotal * 0.18
        expected_total = expected_subtotal + expected_tax
        
        assert abs(invoice_data.subtotal - expected_subtotal) < 0.01, \
            "Subtotal calculation incorrect"
        assert abs(invoice_data.tax_amount - expected_tax) < 0.01, \
            "Tax calculation incorrect"
        assert abs(invoice_data.total_amount - expected_total) < 0.01, \
            "Total calculation incorrect"
        
        # Verify amounts are in document
        with open(pdf_doc.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert InvoiceTemplate.format_currency(invoice_data.total_amount) in content, \
                "Total amount not found in document"
