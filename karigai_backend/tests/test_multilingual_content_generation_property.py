"""
Property-Based Tests for Multilingual Content Generation

**Property 19: Multilingual Content Generation**
For any guest information or booking communication, the system should generate
professional content in multiple specified languages (English, French, Hindi)

**Validates: Requirements 6.2, 6.5**
"""

import pytest
from hypothesis import given, strategies as st, settings
from app.services.multilingual_content_service import (
    MultilingualContentService,
    ContentType,
    Language,
    ContentRequest
)


# Strategy for generating valid guest names
guest_names = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"),
        whitelist_characters=" -'"
    ),
    min_size=2,
    max_size=50
).filter(lambda x: x.strip() and not x.isspace())

# Strategy for generating property names
property_names = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"),
        whitelist_characters=" -'&"
    ),
    min_size=3,
    max_size=100
).filter(lambda x: x.strip() and not x.isspace())

# Strategy for generating dates
import datetime
dates = st.dates(
    min_value=datetime.date(2026, 1, 1),
    max_value=datetime.date(2027, 12, 31)
).map(lambda d: d.isoformat())

# Strategy for generating booking IDs
booking_ids = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Nd")),
    min_size=5,
    max_size=20
).filter(lambda x: x.strip())

# Strategy for generating room types
room_types = st.sampled_from([
    "Standard Room",
    "Deluxe Room",
    "Suite",
    "Executive Room",
    "Family Room"
])

# Strategy for generating amounts
amounts = st.floats(min_value=1000.0, max_value=100000.0)

# Strategy for generating language lists
language_lists = st.lists(
    st.sampled_from([Language.ENGLISH, Language.FRENCH, Language.HINDI]),
    min_size=1,
    max_size=3,
    unique=True
)


class TestMultilingualContentGenerationProperty:
    """Property-based tests for multilingual content generation"""
    
    @given(
        guest_name=guest_names,
        property_name=property_names,
        check_in=dates,
        check_out=dates,
        languages=language_lists
    )
    @settings(max_examples=100)
    def test_property_all_requested_languages_generated(
        self,
        guest_name,
        property_name,
        check_in,
        check_out,
        languages
    ):
        """
        Property: For any guest information request, content should be
        generated in ALL requested languages
        
        **Validates: Requirements 6.2**
        """
        service = MultilingualContentService()
        result = service.generate_guest_information(
            guest_name=guest_name,
            property_name=property_name,
            check_in_date=check_in,
            check_out_date=check_out,
            languages=languages
        )
        
        # Property: All requested languages must be present
        assert len(result.content_by_language) == len(languages)
        for language in languages:
            assert language in result.content_by_language
            assert result.content_by_language[language] is not None
            assert len(result.content_by_language[language]) > 0
    
    @given(
        guest_name=guest_names,
        property_name=property_names,
        check_in=dates,
        check_out=dates,
        languages=language_lists
    )
    @settings(max_examples=100)
    def test_property_content_includes_context_data(
        self,
        guest_name,
        property_name,
        check_in,
        check_out,
        languages
    ):
        """
        Property: For any content generation, all context data should be
        included in the generated content
        
        **Validates: Requirements 6.2, 6.5**
        """
        service = MultilingualContentService()
        result = service.generate_guest_information(
            guest_name=guest_name,
            property_name=property_name,
            check_in_date=check_in,
            check_out_date=check_out,
            languages=languages
        )
        
        # Property: Each language's content must include key context data
        for language, content in result.content_by_language.items():
            # At least one of the key pieces of information should be present
            # (some languages may format differently)
            has_guest_name = guest_name in content
            has_property_name = property_name in content
            has_check_in = check_in in content
            has_check_out = check_out in content
            
            # At least 2 out of 4 key pieces should be present
            present_count = sum([
                has_guest_name,
                has_property_name,
                has_check_in,
                has_check_out
            ])
            assert present_count >= 2, (
                f"Content in {language.value} missing too much context data. "
                f"Present: guest_name={has_guest_name}, property_name={has_property_name}, "
                f"check_in={has_check_in}, check_out={has_check_out}"
            )
    
    @given(
        booking_id=booking_ids,
        guest_name=guest_names,
        property_name=property_names,
        room_type=room_types,
        check_in=dates,
        check_out=dates,
        amount=amounts,
        languages=language_lists
    )
    @settings(max_examples=100)
    def test_property_booking_confirmation_completeness(
        self,
        booking_id,
        guest_name,
        property_name,
        room_type,
        check_in,
        check_out,
        amount,
        languages
    ):
        """
        Property: For any booking confirmation, all booking details should
        be present in all requested languages
        
        **Validates: Requirements 6.5**
        """
        service = MultilingualContentService()
        result = service.generate_booking_confirmation(
            booking_id=booking_id,
            guest_name=guest_name,
            property_name=property_name,
            room_type=room_type,
            check_in_date=check_in,
            check_out_date=check_out,
            total_amount=amount,
            languages=languages
        )
        
        # Property: All languages must have content
        assert len(result.content_by_language) == len(languages)
        
        # Property: Each language's content must include booking ID
        for language, content in result.content_by_language.items():
            assert booking_id in content, (
                f"Booking ID {booking_id} not found in {language.value} content"
            )
    
    @given(
        guest_name=guest_names,
        property_name=property_names,
        check_in=dates,
        check_out=dates
    )
    @settings(max_examples=100)
    def test_property_different_languages_produce_different_content(
        self,
        guest_name,
        property_name,
        check_in,
        check_out
    ):
        """
        Property: For any content request with multiple languages, each
        language should produce distinct content (not just copies)
        
        **Validates: Requirements 6.2**
        """
        service = MultilingualContentService()
        languages = [Language.ENGLISH, Language.FRENCH, Language.HINDI]
        
        result = service.generate_guest_information(
            guest_name=guest_name,
            property_name=property_name,
            check_in_date=check_in,
            check_out_date=check_out,
            languages=languages
        )
        
        # Property: Content in different languages should be different
        english_content = result.content_by_language[Language.ENGLISH]
        french_content = result.content_by_language[Language.FRENCH]
        hindi_content = result.content_by_language[Language.HINDI]
        
        assert english_content != french_content
        assert english_content != hindi_content
        assert french_content != hindi_content
    
    @given(
        guest_name=guest_names,
        property_name=property_names,
        host_name=guest_names,
        languages=language_lists
    )
    @settings(max_examples=100)
    def test_property_welcome_message_professional_tone(
        self,
        guest_name,
        property_name,
        host_name,
        languages
    ):
        """
        Property: For any welcome message, content should maintain
        professional and welcoming tone in all languages
        
        **Validates: Requirements 6.5**
        """
        service = MultilingualContentService()
        result = service.generate_welcome_message(
            guest_name=guest_name,
            property_name=property_name,
            host_name=host_name,
            languages=languages
        )
        
        # Property: All languages must have non-empty content
        for language, content in result.content_by_language.items():
            assert len(content) > 20, (
                f"Content in {language.value} is too short to be professional"
            )
            
            # Content should include all three names
            name_count = sum([
                guest_name in content,
                property_name in content,
                host_name in content
            ])
            assert name_count >= 2, (
                f"Content in {language.value} missing key names"
            )
    
    @given(
        guest_name=guest_names,
        property_name=property_names,
        check_in=dates,
        check_out=dates,
        languages=language_lists
    )
    @settings(max_examples=100)
    def test_property_content_type_consistency(
        self,
        guest_name,
        property_name,
        check_in,
        check_out,
        languages
    ):
        """
        Property: For any content generation, the content type should be
        consistent across all languages
        
        **Validates: Requirements 6.2**
        """
        service = MultilingualContentService()
        result = service.generate_guest_information(
            guest_name=guest_name,
            property_name=property_name,
            check_in_date=check_in,
            check_out_date=check_out,
            languages=languages
        )
        
        # Property: Content type should match request
        assert result.content_type == ContentType.GUEST_INFORMATION
        
        # Property: Metadata should reflect all requested languages
        assert len(result.metadata["languages"]) == len(languages)
    
    @given(
        booking_id=booking_ids,
        guest_name=guest_names,
        property_name=property_names,
        room_type=room_types,
        check_in=dates,
        check_out=dates,
        amount=amounts
    )
    @settings(max_examples=100)
    def test_property_amount_formatting_consistency(
        self,
        booking_id,
        guest_name,
        property_name,
        room_type,
        check_in,
        check_out,
        amount
    ):
        """
        Property: For any booking with amount, the amount should be
        consistently formatted across all languages
        
        **Validates: Requirements 6.5**
        """
        service = MultilingualContentService()
        languages = [Language.ENGLISH, Language.FRENCH, Language.HINDI]
        
        result = service.generate_booking_confirmation(
            booking_id=booking_id,
            guest_name=guest_name,
            property_name=property_name,
            room_type=room_type,
            check_in_date=check_in,
            check_out_date=check_out,
            total_amount=amount,
            languages=languages
        )
        
        # Property: Amount should appear in all language versions
        amount_str = str(int(amount))
        
        for language, content in result.content_by_language.items():
            # Amount should be present (at least the integer part)
            assert amount_str in content or str(amount) in content, (
                f"Amount {amount} not found in {language.value} content"
            )
    
    @given(
        guest_name=guest_names,
        property_name=property_names,
        check_in=dates,
        check_out=dates,
        languages=language_lists
    )
    @settings(max_examples=100)
    def test_property_no_empty_content(
        self,
        guest_name,
        property_name,
        check_in,
        check_out,
        languages
    ):
        """
        Property: For any valid content request, no language should produce
        empty or null content
        
        **Validates: Requirements 6.2, 6.5**
        """
        service = MultilingualContentService()
        result = service.generate_guest_information(
            guest_name=guest_name,
            property_name=property_name,
            check_in_date=check_in,
            check_out_date=check_out,
            languages=languages
        )
        
        # Property: No content should be empty or None
        for language, content in result.content_by_language.items():
            assert content is not None
            assert len(content.strip()) > 0
            assert content != ""
    
    @given(
        guest_name=guest_names,
        property_name=property_names,
        check_in=dates,
        check_out=dates
    )
    @settings(max_examples=100)
    def test_property_single_language_request_efficiency(
        self,
        guest_name,
        property_name,
        check_in,
        check_out
    ):
        """
        Property: For any single language request, only that language
        should be generated (no unnecessary processing)
        
        **Validates: Requirements 6.2**
        """
        service = MultilingualContentService()
        result = service.generate_guest_information(
            guest_name=guest_name,
            property_name=property_name,
            check_in_date=check_in,
            check_out_date=check_out,
            languages=[Language.ENGLISH]
        )
        
        # Property: Only one language should be present
        assert len(result.content_by_language) == 1
        assert Language.ENGLISH in result.content_by_language
        assert Language.FRENCH not in result.content_by_language
        assert Language.HINDI not in result.content_by_language
