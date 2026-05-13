"""
Tests for Multilingual Content Generation Service
"""

import pytest
from app.services.multilingual_content_service import (
    MultilingualContentService,
    ContentType,
    Language,
    ContentRequest,
    GeneratedContent
)


class TestMultilingualContentService:
    """Test suite for MultilingualContentService"""
    
    @pytest.fixture
    def service(self):
        """Create service instance"""
        return MultilingualContentService()
    
    def test_initialization(self, service):
        """Test service initialization"""
        assert service is not None
        assert service.content_templates is not None
        assert service.cultural_guidelines is not None
    
    def test_get_supported_languages(self, service):
        """Test getting supported languages"""
        languages = service.get_supported_languages()
        
        assert len(languages) == 3
        assert "en" in languages
        assert "fr" in languages
        assert "hi" in languages
    
    def test_get_supported_content_types(self, service):
        """Test getting supported content types"""
        content_types = service.get_supported_content_types()
        
        assert len(content_types) >= 3
        assert "guest_information" in content_types
        assert "booking_confirmation" in content_types
        assert "welcome_message" in content_types
    
    def test_generate_guest_information_english(self, service):
        """Test generating guest information in English"""
        result = service.generate_guest_information(
            guest_name="John Smith",
            property_name="Mountain View Homestay",
            check_in_date="2026-03-15",
            check_out_date="2026-03-20",
            languages=[Language.ENGLISH]
        )
        
        assert isinstance(result, GeneratedContent)
        assert result.content_type == ContentType.GUEST_INFORMATION
        assert Language.ENGLISH in result.content_by_language
        
        content = result.content_by_language[Language.ENGLISH]
        assert "John Smith" in content
        assert "Mountain View Homestay" in content
        assert "2026-03-15" in content
        assert "2026-03-20" in content
    
    def test_generate_guest_information_french(self, service):
        """Test generating guest information in French"""
        result = service.generate_guest_information(
            guest_name="Marie Dubois",
            property_name="Maison de Montagne",
            check_in_date="2026-04-10",
            check_out_date="2026-04-15",
            languages=[Language.FRENCH]
        )
        
        assert Language.FRENCH in result.content_by_language
        
        content = result.content_by_language[Language.FRENCH]
        assert "Marie Dubois" in content
        assert "Maison de Montagne" in content
        assert "Bienvenue" in content
    
    def test_generate_guest_information_hindi(self, service):
        """Test generating guest information in Hindi"""
        result = service.generate_guest_information(
            guest_name="राज कुमार",
            property_name="पहाड़ी होमस्टे",
            check_in_date="2026-05-01",
            check_out_date="2026-05-05",
            languages=[Language.HINDI]
        )
        
        assert Language.HINDI in result.content_by_language
        
        content = result.content_by_language[Language.HINDI]
        assert "राज कुमार" in content
        assert "पहाड़ी होमस्टे" in content
        assert "स्वागत" in content
    
    def test_generate_guest_information_multiple_languages(self, service):
        """Test generating guest information in multiple languages"""
        result = service.generate_guest_information(
            guest_name="Alex Johnson",
            property_name="Lake View Resort",
            check_in_date="2026-06-01",
            check_out_date="2026-06-10",
            languages=[Language.ENGLISH, Language.FRENCH, Language.HINDI]
        )
        
        assert len(result.content_by_language) == 3
        assert Language.ENGLISH in result.content_by_language
        assert Language.FRENCH in result.content_by_language
        assert Language.HINDI in result.content_by_language
        
        # Verify all languages contain guest name
        for content in result.content_by_language.values():
            assert "Alex Johnson" in content or "Lake View Resort" in content
    
    def test_generate_booking_confirmation_english(self, service):
        """Test generating booking confirmation in English"""
        result = service.generate_booking_confirmation(
            booking_id="BK12345",
            guest_name="Sarah Williams",
            property_name="Sunset Villa",
            room_type="Deluxe Room",
            check_in_date="2026-07-15",
            check_out_date="2026-07-20",
            total_amount=15000.00,
            languages=[Language.ENGLISH]
        )
        
        assert result.content_type == ContentType.BOOKING_CONFIRMATION
        
        content = result.content_by_language[Language.ENGLISH]
        assert "BK12345" in content
        assert "Sarah Williams" in content
        assert "Sunset Villa" in content
        assert "Deluxe Room" in content
        assert "15000" in content
    
    def test_generate_booking_confirmation_french(self, service):
        """Test generating booking confirmation in French"""
        result = service.generate_booking_confirmation(
            booking_id="BK67890",
            guest_name="Pierre Martin",
            property_name="Villa Soleil",
            room_type="Chambre Standard",
            check_in_date="2026-08-01",
            check_out_date="2026-08-05",
            total_amount=12000.00,
            languages=[Language.FRENCH]
        )
        
        content = result.content_by_language[Language.FRENCH]
        assert "BK67890" in content
        assert "Pierre Martin" in content
        assert "Confirmation" in content or "réservation" in content
    
    def test_generate_booking_confirmation_hindi(self, service):
        """Test generating booking confirmation in Hindi"""
        result = service.generate_booking_confirmation(
            booking_id="BK11111",
            guest_name="अमित शर्मा",
            property_name="गंगा व्यू होटल",
            room_type="स्टैंडर्ड रूम",
            check_in_date="2026-09-10",
            check_out_date="2026-09-15",
            total_amount=10000.00,
            languages=[Language.HINDI]
        )
        
        content = result.content_by_language[Language.HINDI]
        assert "BK11111" in content
        assert "अमित शर्मा" in content
        assert "पुष्टिकरण" in content
    
    def test_generate_welcome_message_english(self, service):
        """Test generating welcome message in English"""
        result = service.generate_welcome_message(
            guest_name="David Brown",
            property_name="Riverside Cottage",
            host_name="Ramesh Kumar",
            languages=[Language.ENGLISH]
        )
        
        assert result.content_type == ContentType.WELCOME_MESSAGE
        
        content = result.content_by_language[Language.ENGLISH]
        assert "David Brown" in content
        assert "Riverside Cottage" in content
        assert "Ramesh Kumar" in content
        assert "Welcome" in content
    
    def test_generate_welcome_message_with_cultural_preferences(self, service):
        """Test generating welcome message with cultural preferences"""
        result = service.generate_welcome_message(
            guest_name="Emma Wilson",
            property_name="Heritage Home",
            host_name="Priya Sharma",
            languages=[Language.ENGLISH],
            cultural_preferences={"formality": "formal"}
        )
        
        content = result.content_by_language[Language.ENGLISH]
        assert "Emma Wilson" in content
        assert "Heritage Home" in content
    
    def test_generate_content_with_request_object(self, service):
        """Test generating content using ContentRequest object"""
        request = ContentRequest(
            content_type=ContentType.GUEST_INFORMATION,
            languages=[Language.ENGLISH, Language.HINDI],
            context={
                "guest_name": "Test Guest",
                "property_name": "Test Property",
                "check_in_date": "2026-10-01",
                "check_out_date": "2026-10-05"
            }
        )
        
        result = service.generate_content(request)
        
        assert isinstance(result, GeneratedContent)
        assert len(result.content_by_language) == 2
        assert result.metadata["languages"] == ["en", "hi"]
    
    def test_generate_content_missing_context_key(self, service):
        """Test generating content with missing context key"""
        request = ContentRequest(
            content_type=ContentType.GUEST_INFORMATION,
            languages=[Language.ENGLISH],
            context={
                "guest_name": "Test Guest"
                # Missing other required keys
            }
        )
        
        result = service.generate_content(request)
        
        # Should handle missing keys gracefully
        content = result.content_by_language[Language.ENGLISH]
        assert "Error" in content or "missing" in content.lower()
    
    def test_metadata_includes_context_keys(self, service):
        """Test that metadata includes context keys"""
        result = service.generate_guest_information(
            guest_name="Test User",
            property_name="Test Place",
            check_in_date="2026-11-01",
            check_out_date="2026-11-05",
            languages=[Language.ENGLISH]
        )
        
        assert "context_keys" in result.metadata
        assert "guest_name" in result.metadata["context_keys"]
        assert "property_name" in result.metadata["context_keys"]
    
    def test_all_languages_generate_different_content(self, service):
        """Test that different languages generate different content"""
        result = service.generate_guest_information(
            guest_name="Test Guest",
            property_name="Test Property",
            check_in_date="2026-12-01",
            check_out_date="2026-12-05",
            languages=[Language.ENGLISH, Language.FRENCH, Language.HINDI]
        )
        
        english_content = result.content_by_language[Language.ENGLISH]
        french_content = result.content_by_language[Language.FRENCH]
        hindi_content = result.content_by_language[Language.HINDI]
        
        # Content should be different for each language
        assert english_content != french_content
        assert english_content != hindi_content
        assert french_content != hindi_content
    
    def test_booking_confirmation_includes_all_details(self, service):
        """Test that booking confirmation includes all required details"""
        result = service.generate_booking_confirmation(
            booking_id="BK99999",
            guest_name="Complete Test",
            property_name="Full Details Hotel",
            room_type="Suite",
            check_in_date="2027-01-01",
            check_out_date="2027-01-10",
            total_amount=25000.00,
            languages=[Language.ENGLISH]
        )
        
        content = result.content_by_language[Language.ENGLISH]
        
        # Verify all details are present
        assert "BK99999" in content
        assert "Complete Test" in content
        assert "Full Details Hotel" in content
        assert "Suite" in content
        assert "2027-01-01" in content
        assert "2027-01-10" in content
        assert "25000" in content
    
    def test_professional_tone_in_all_languages(self, service):
        """Test that content maintains professional tone"""
        result = service.generate_booking_confirmation(
            booking_id="BK00001",
            guest_name="Professional Guest",
            property_name="Business Hotel",
            room_type="Executive Room",
            check_in_date="2027-02-01",
            check_out_date="2027-02-05",
            total_amount=20000.00,
            languages=[Language.ENGLISH, Language.FRENCH, Language.HINDI]
        )
        
        # Check for professional language markers
        english_content = result.content_by_language[Language.ENGLISH]
        assert any(word in english_content.lower() for word in ["confirmation", "booking", "details"])
        
        french_content = result.content_by_language[Language.FRENCH]
        assert any(word in french_content for word in ["Confirmation", "réservation"])
        
        hindi_content = result.content_by_language[Language.HINDI]
        assert "पुष्टिकरण" in hindi_content or "बुकिंग" in hindi_content
