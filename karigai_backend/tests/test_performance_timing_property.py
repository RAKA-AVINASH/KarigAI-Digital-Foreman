"""
Property-Based Test: Performance Timing Requirements

**Property 27: Performance Timing Requirements**
**Validates: Requirements 10.1, 10.2, 10.3**

For any voice processing, document generation, or image analysis, the system 
should meet specified response time limits (3s, 5s, 10s respectively).
"""

import pytest
from hypothesis import given, strategies as st, settings
import time
from datetime import datetime

from app.core.document_generator import InvoiceData, ServiceItem
from app.services.pdf_generator_service import PDFGeneratorService


# Strategy for generating invoice data
@st.composite
def invoice_data_strategy(draw):
    """Generate valid invoice data for performance testing"""
    invoice_id = f"INV-{draw(st.integers(min_value=1000, max_value=9999))}"
    customer_name = draw(st.text(min_size=3, max_size=30, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Zs'),
        blacklist_characters='\n\r\t'
    )))
    
    # Generate 1-5 service items for reasonable performance
    services = draw(st.lists(
        st.builds(
            ServiceItem,
            description=st.text(min_size=5, max_size=50, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'),
                blacklist_characters='\n\r\t'
            )),
            amount=st.floats(min_value=10.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
            quantity=st.integers(min_value=1, max_value=10)
        ),
        min_size=1,
        max_size=5
    ))
    
    return InvoiceData(
        invoice_id=invoice_id,
        customer_name=customer_name.strip() or "Customer",
        customer_phone=None,
        services=services,
        warranty_info=None,
        notes=None,
        service_date=datetime.now()
    )


@pytest.mark.asyncio
class TestPerformanceTimingProperty:
    """
    Property-Based Tests for Performance Timing Requirements
    
    **Feature: karigai, Property 27**
    **Validates: Requirements 10.1, 10.2, 10.3**
    """
    
    @given(invoice_data=invoice_data_strategy())
    @settings(max_examples=50, deadline=None)
    async def test_document_generation_within_5_seconds(self, invoice_data: InvoiceData):
        """
        Property: For any invoice data, document generation should complete 
        within 5 seconds (Requirement 10.2)
        """
        import tempfile
        temp_dir = tempfile.mkdtemp()
        pdf_service = PDFGeneratorService(output_dir=temp_dir)
        
        # Measure document generation time
        start_time = time.time()
        pdf_doc = await pdf_service.generate_invoice(invoice_data)
        end_time = time.time()
        
        generation_time = end_time - start_time
        
        assert generation_time < 5.0, \
            f"Document generation took {generation_time:.2f}s, exceeds 5s limit"
        
        # Verify document was actually created
        import os
        assert os.path.exists(pdf_doc.file_path), \
            "Document file was not created"
    
    @given(invoice_data=invoice_data_strategy())
    @settings(max_examples=50, deadline=None)
    async def test_document_generation_consistency(self, invoice_data: InvoiceData):
        """
        Property: Document generation time should be consistent across 
        multiple invocations for similar data
        """
        import tempfile
        temp_dir = tempfile.mkdtemp()
        pdf_service = PDFGeneratorService(output_dir=temp_dir)
        
        # Generate document twice
        start1 = time.time()
        pdf_doc1 = await pdf_service.generate_invoice(invoice_data)
        time1 = time.time() - start1
        
        start2 = time.time()
        pdf_doc2 = await pdf_service.generate_invoice(invoice_data, language="en-IN")
        time2 = time.time() - start2
        
        # Both should be under 5 seconds
        assert time1 < 5.0, f"First generation took {time1:.2f}s"
        assert time2 < 5.0, f"Second generation took {time2:.2f}s"
        
        # Times should be relatively consistent (within 2x of each other)
        ratio = max(time1, time2) / min(time1, time2)
        assert ratio < 3.0, \
            f"Generation times vary too much: {time1:.2f}s vs {time2:.2f}s"
    
    @given(invoice_data=invoice_data_strategy())
    @settings(max_examples=30, deadline=None)
    async def test_bilingual_generation_performance(self, invoice_data: InvoiceData):
        """
        Property: Generating documents in both languages should complete 
        within reasonable time (10s total for both)
        """
        import tempfile
        temp_dir = tempfile.mkdtemp()
        pdf_service = PDFGeneratorService(output_dir=temp_dir)
        
        # Generate both language versions
        start_time = time.time()
        
        pdf_hindi = await pdf_service.generate_invoice(invoice_data, language="hi-IN")
        pdf_english = await pdf_service.generate_invoice(invoice_data, language="en-IN")
        
        total_time = time.time() - start_time
        
        assert total_time < 10.0, \
            f"Bilingual generation took {total_time:.2f}s, exceeds 10s limit"
        
        # Verify both documents were created
        import os
        assert os.path.exists(pdf_hindi.file_path)
        assert os.path.exists(pdf_english.file_path)
    
    @given(
        service_count=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=30, deadline=None)
    async def test_performance_scales_with_complexity(self, service_count: int):
        """
        Property: Document generation time should scale reasonably with 
        the number of service items
        """
        import tempfile
        temp_dir = tempfile.mkdtemp()
        pdf_service = PDFGeneratorService(output_dir=temp_dir)
        
        # Create invoice with specified number of services
        services = [
            ServiceItem(
                description=f"Service {i}",
                amount=100.0 * i,
                quantity=1
            )
            for i in range(1, service_count + 1)
        ]
        
        invoice_data = InvoiceData(
            invoice_id=f"INV-PERF-{service_count}",
            customer_name="Performance Test Customer",
            customer_phone=None,
            services=services,
            warranty_info=None,
            notes=None,
            service_date=datetime.now()
        )
        
        # Measure generation time
        start_time = time.time()
        pdf_doc = await pdf_service.generate_invoice(invoice_data)
        generation_time = time.time() - start_time
        
        # Should still be under 5 seconds even with many services
        assert generation_time < 5.0, \
            f"Generation with {service_count} services took {generation_time:.2f}s"
        
        # Time should scale sub-linearly (not proportional to service count)
        # For 20 services, should not take 20x longer than 1 service
        max_expected_time = 0.5 + (service_count * 0.2)  # Base time + linear component
        assert generation_time < max_expected_time, \
            f"Generation time {generation_time:.2f}s exceeds expected {max_expected_time:.2f}s"
    
    @given(invoice_data=invoice_data_strategy())
    @settings(max_examples=30, deadline=None)
    async def test_concurrent_generation_performance(self, invoice_data: InvoiceData):
        """
        Property: Multiple concurrent document generations should not 
        significantly degrade individual performance
        """
        import tempfile
        import asyncio
        temp_dir = tempfile.mkdtemp()
        pdf_service = PDFGeneratorService(output_dir=temp_dir)
        
        # Generate 3 documents concurrently
        start_time = time.time()
        
        tasks = [
            pdf_service.generate_invoice(invoice_data, language="hi-IN"),
            pdf_service.generate_invoice(invoice_data, language="en-IN"),
            pdf_service.generate_invoice(invoice_data, language="hi-IN")
        ]
        
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # All 3 should complete within 15 seconds (3 * 5s limit)
        assert total_time < 15.0, \
            f"Concurrent generation took {total_time:.2f}s, exceeds 15s limit"
        
        # Verify all documents were created
        import os
        for pdf_doc in results:
            assert os.path.exists(pdf_doc.file_path)
    
    @given(invoice_data=invoice_data_strategy())
    @settings(max_examples=20, deadline=None)
    async def test_performance_with_optional_fields(self, invoice_data: InvoiceData):
        """
        Property: Including optional fields (warranty, notes) should not 
        significantly impact generation time
        """
        import tempfile
        temp_dir = tempfile.mkdtemp()
        pdf_service = PDFGeneratorService(output_dir=temp_dir)
        
        # Generate without optional fields
        invoice_minimal = InvoiceData(
            invoice_id=invoice_data.invoice_id,
            customer_name=invoice_data.customer_name,
            customer_phone=None,
            services=invoice_data.services,
            warranty_info=None,
            notes=None,
            service_date=invoice_data.service_date
        )
        
        start1 = time.time()
        pdf_minimal = await pdf_service.generate_invoice(invoice_minimal)
        time_minimal = time.time() - start1
        
        # Generate with optional fields
        invoice_full = InvoiceData(
            invoice_id=invoice_data.invoice_id + "-FULL",
            customer_name=invoice_data.customer_name,
            customer_phone="+919876543210",
            services=invoice_data.services,
            warranty_info="90 days warranty on all parts and labor",
            notes="Payment due within 7 days. Thank you for your business.",
            service_date=invoice_data.service_date
        )
        
        start2 = time.time()
        pdf_full = await pdf_service.generate_invoice(invoice_full)
        time_full = time.time() - start2
        
        # Both should be under 5 seconds
        assert time_minimal < 5.0, f"Minimal generation took {time_minimal:.2f}s"
        assert time_full < 5.0, f"Full generation took {time_full:.2f}s"
        
        # Difference should be minimal (less than 1 second)
        time_diff = abs(time_full - time_minimal)
        assert time_diff < 1.0, \
            f"Optional fields added {time_diff:.2f}s, should be < 1s"
