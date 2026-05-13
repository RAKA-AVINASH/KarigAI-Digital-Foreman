"""
Property-Based Test: WhatsApp Integration Reliability

**Property 4: WhatsApp Integration Reliability**
**Validates: Requirements 1.4**

For any generated invoice document, the WhatsApp integration should 
successfully deliver the PDF when requested.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
import tempfile
import os

from app.services.whatsapp_service import (
    WhatsAppService,
    DeliveryStatus,
    DeliveryMethod
)


# Strategy for generating phone numbers
@st.composite
def phone_number_strategy(draw):
    """Generate valid Indian phone numbers"""
    # Indian mobile numbers: +91 followed by 10 digits starting with 6-9
    first_digit = draw(st.integers(min_value=6, max_value=9))
    remaining_digits = draw(st.integers(min_value=0, max_value=999999999))
    
    phone = f"+91{first_digit}{remaining_digits:09d}"
    return phone


# Strategy for generating email addresses
@st.composite
def email_strategy(draw):
    """Generate valid email addresses"""
    username = draw(st.text(min_size=3, max_size=20, alphabet=st.characters(
        whitelist_categories=('Ll', 'Nd'),
        blacklist_characters='@.'
    )))
    domain = draw(st.sampled_from(['gmail.com', 'yahoo.com', 'example.com', 'test.com']))
    
    return f"{username}@{domain}"


# Strategy for generating messages
@st.composite
def message_strategy(draw):
    """Generate delivery messages"""
    templates = [
        "Your invoice is ready",
        "Document attached",
        "Please find your invoice",
        "Invoice for your service",
        "Payment receipt"
    ]
    
    return draw(st.sampled_from(templates))


def create_test_document():
    """Create a test document file"""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False)
    temp_file.write("Test invoice document content")
    temp_file.close()
    return temp_file.name


@pytest.mark.asyncio
class TestWhatsAppIntegrationReliabilityProperty:
    """
    Property-Based Tests for WhatsApp Integration Reliability
    
    **Feature: karigai, Property 4**
    **Validates: Requirements 1.4**
    """
    
    @given(
        phone=phone_number_strategy(),
        message=message_strategy()
    )
    @settings(
        max_examples=50, 
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_delivery_always_succeeds_with_fallback(
        self, 
        phone: str, 
        message: str
    ):
        """
        Property: For any phone number and message, document delivery should 
        succeed either via WhatsApp or fallback methods
        """
        test_document = create_test_document()
        try:
            service = WhatsAppService()
            
            result = await service.send_document(
                recipient_phone=phone,
                document_path=test_document,
                message=message
            )
            
            # Delivery should always succeed (via WhatsApp or fallback)
            assert result.success is True, \
                f"Delivery failed for {phone}: {result.message}"
            
            # Should have a delivery ID
            assert result.delivery_id is not None, \
                "Delivery ID not generated"
            
            # Should have a timestamp
            assert result.timestamp is not None, \
                "Timestamp not recorded"
        finally:
            if os.path.exists(test_document):
                os.unlink(test_document)
    
    @given(
        phone=phone_number_strategy(),
        email=email_strategy()
    )
    @settings(
        max_examples=50, 
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_fallback_email_always_available(
        self,
        phone: str,
        email: str
    ):
        """
        Property: When email fallback is provided, delivery should succeed 
        even if WhatsApp fails
        """
        test_document = create_test_document()
        try:
            service = WhatsAppService()  # No WhatsApp credentials
            
            result = await service.send_document(
                recipient_phone=phone,
                document_path=test_document,
                fallback_email=email
            )
            
            # Should succeed via fallback
            assert result.success is True, \
                f"Delivery failed even with fallback email: {result.message}"
            
            # Should use fallback method
            assert result.method in [DeliveryMethod.EMAIL, DeliveryMethod.DIRECT_DOWNLOAD], \
                f"Expected fallback method, got {result.method}"
        finally:
            if os.path.exists(test_document):
                os.unlink(test_document)
    
    @given(phone=phone_number_strategy())
    @settings(
        max_examples=30, 
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_retry_mechanism_improves_reliability(
        self,
        phone: str
    ):
        """
        Property: Retry mechanism should improve delivery reliability
        """
        test_document = create_test_document()
        try:
            service = WhatsAppService(max_retries=3)
            
            result = await service.send_document_with_retry(
                recipient_phone=phone,
                document_path=test_document
            )
            
            # Should eventually succeed
            assert result.success is True, \
                f"Delivery failed after retries: {result.message}"
            
            # Retry count should be tracked
            assert result.retry_count >= 0, \
                "Retry count not tracked"
            
            # Should not exceed max retries
            assert result.retry_count <= service.max_retries, \
                f"Retry count {result.retry_count} exceeds max {service.max_retries}"
        finally:
            if os.path.exists(test_document):
                os.unlink(test_document)
    
    @given(phone=phone_number_strategy())
    @settings(
        max_examples=30, 
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_delivery_result_always_complete(
        self,
        phone: str
    ):
        """
        Property: Delivery result should always contain complete information
        """
        test_document = create_test_document()
        try:
            service = WhatsAppService()
            
            result = await service.send_document(
                recipient_phone=phone,
                document_path=test_document
            )
            
            # Result should have all required fields
            assert result.success is not None, "Success status missing"
            assert result.method is not None, "Delivery method missing"
            assert result.status is not None, "Delivery status missing"
            assert result.message is not None, "Message missing"
            assert len(result.message) > 0, "Message is empty"
        finally:
            if os.path.exists(test_document):
                os.unlink(test_document)
