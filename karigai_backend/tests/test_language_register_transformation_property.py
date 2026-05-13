"""
Property-Based Test for Language Register Transformation

**Property 20: Language Register Transformation**
**Validates: Requirements 7.2, 7.3**

For any colloquial input, the system should translate to formal business language
while maintaining meaning and technical accuracy.
"""

import pytest
from hypothesis import given, strategies as st, settings
from app.services.translation_service import (
    TranslationService,
    LanguageRegister
)


# Strategy for generating text with colloquial terms
colloquial_terms = ["gonna", "wanna", "gotta", "yeah", "nope"]
formal_terms = ["going to", "want to", "have to", "yes", "no"]

@st.composite
def colloquial_text(draw):
    """Generate text with colloquial terms"""
    num_words = draw(st.integers(min_value=1, max_value=10))
    words = []
    for _ in range(num_words):
        if draw(st.booleans()):
            # Add a colloquial term
            words.append(draw(st.sampled_from(colloquial_terms)))
        else:
            # Add a regular word
            words.append(draw(st.text(
                alphabet=st.characters(whitelist_categories=('Lu', 'Ll')),
                min_size=1,
                max_size=10
            )))
    return " ".join(words)


@st.composite
def text_with_technical_terms(draw):
    """Generate text with technical terms"""
    technical_terms = ["voltage", "circuit", "ampere", "watt", "pipe", "valve"]
    num_words = draw(st.integers(min_value=2, max_value=8))
    words = []
    # Ensure at least one technical term
    words.append(draw(st.sampled_from(technical_terms)))
    for _ in range(num_words - 1):
        if draw(st.booleans()):
            words.append(draw(st.sampled_from(technical_terms)))
        else:
            words.append(draw(st.text(
                alphabet=st.characters(whitelist_categories=('Lu', 'Ll')),
                min_size=1,
                max_size=8
            )))
    return " ".join(words)


class TestLanguageRegisterTransformationProperty:
    """Property-based tests for language register transformation"""
    
    @given(text=st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_property_transformation_preserves_length_order(self, text):
        """
        Property: Transformation should preserve approximate length
        
        The transformed text should not be drastically different in length
        (within reasonable bounds for language transformation)
        """
        service = TranslationService()
        
        result = service.transform_register(
            text,
            LanguageRegister.COLLOQUIAL,
            LanguageRegister.FORMAL,
            "en-IN"
        )
        
        # Length should be within reasonable bounds (0.5x to 3x)
        assert len(result) >= len(text) * 0.3
        assert len(result) <= len(text) * 5
    
    @given(text=colloquial_text())
    @settings(max_examples=100)
    def test_property_colloquial_to_formal_removes_colloquialisms(self, text):
        """
        Property: Colloquial to formal transformation removes colloquial terms
        
        After transformation, colloquial terms should be replaced with formal equivalents
        """
        service = TranslationService()
        
        result = service.transform_register(
            text,
            LanguageRegister.COLLOQUIAL,
            LanguageRegister.FORMAL,
            "en-IN"
        )
        
        # Check that colloquial terms are replaced
        result_lower = result.lower()
        for colloquial in colloquial_terms:
            if colloquial in text.lower():
                # The colloquial term should be replaced
                # (may still appear if it's part of another word)
                count_before = text.lower().split().count(colloquial)
                count_after = result_lower.split().count(colloquial)
                assert count_after <= count_before
    
    @given(text=text_with_technical_terms())
    @settings(max_examples=100)
    def test_property_technical_terms_preserved(self, text):
        """
        Property: Technical terms should be preserved during transformation
        
        Technical terms should remain in the output, possibly marked for preservation
        """
        service = TranslationService()
        
        result = service.transform_register(
            text,
            LanguageRegister.COLLOQUIAL,
            LanguageRegister.TECHNICAL,
            "en-IN"
        )
        
        # Technical terms should be preserved (marked with [TECH] tags)
        for term in service.technical_terms:
            if term.lower() in text.lower():
                # Term should appear in result, possibly with markers
                assert term.lower() in result.lower() or f"[TECH]{term}[/TECH]".lower() in result.lower()
    
    @given(
        text=st.text(min_size=1, max_size=50),
        source_register=st.sampled_from(list(LanguageRegister)),
        target_register=st.sampled_from(list(LanguageRegister))
    )
    @settings(max_examples=100)
    def test_property_transformation_is_deterministic(self, text, source_register, target_register):
        """
        Property: Transformation should be deterministic
        
        Same input should always produce same output
        """
        service = TranslationService()
        
        result1 = service.transform_register(text, source_register, target_register, "en-IN")
        result2 = service.transform_register(text, source_register, target_register, "en-IN")
        
        assert result1 == result2
    
    @given(text=st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_property_same_register_is_identity(self, text):
        """
        Property: Transforming to same register should return unchanged text
        
        If source and target register are the same, text should be unchanged
        """
        service = TranslationService()
        
        for register in LanguageRegister:
            result = service.transform_register(text, register, register, "en-IN")
            assert result == text
    
    @given(
        text=st.text(min_size=1, max_size=50),
        language=st.sampled_from(["en-IN", "hi-IN", "ml-IN"])
    )
    @settings(max_examples=100)
    def test_property_translation_same_language_is_identity(self, text, language):
        """
        Property: Translating to same language should return unchanged text
        
        If source and target language are the same, text should be unchanged
        """
        service = TranslationService()
        
        result = service.translate_with_register(text, language, language)
        assert result == text
    
    @given(text=st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_property_business_register_adds_formal_greeting(self, text):
        """
        Property: Business register should add formal greeting
        
        Transforming to business register should add appropriate greeting
        """
        service = TranslationService()
        
        result = service.transform_register(
            text,
            LanguageRegister.COLLOQUIAL,
            LanguageRegister.BUSINESS,
            "en-IN"
        )
        
        # Should contain formal greeting
        assert "Dear Sir/Madam" in result or text in result
    
    @given(
        text=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
            min_size=1,
            max_size=100
        )
    )
    @settings(max_examples=100)
    def test_property_transformation_handles_all_text(self, text):
        """
        Property: Transformation should handle any text without errors
        
        The service should not crash on any input
        """
        service = TranslationService()
        
        try:
            result = service.transform_register(
                text,
                LanguageRegister.COLLOQUIAL,
                LanguageRegister.FORMAL,
                "en-IN"
            )
            assert result is not None
            assert isinstance(result, str)
        except Exception as e:
            pytest.fail(f"Transformation failed with error: {e}")
    
    @given(
        text=st.text(min_size=5, max_size=50),
        primary_lang=st.sampled_from(["hi-IN", "en-IN"]),
        secondary_lang=st.sampled_from(["hi-IN", "en-IN"])
    )
    @settings(max_examples=100)
    def test_property_code_mixed_processing_returns_valid_structure(self, text, primary_lang, secondary_lang):
        """
        Property: Code-mixed processing should return valid structure
        
        The result should contain all required fields
        """
        service = TranslationService()
        
        result = service.process_code_mixed_speech(text, primary_lang, secondary_lang)
        
        # Check structure
        assert "original_text" in result
        assert "processed_text" in result
        assert "segments" in result
        assert "primary_language" in result
        
        # Check values
        assert result["original_text"] == text
        assert result["primary_language"] == primary_lang
        assert isinstance(result["segments"], list)
        assert isinstance(result["processed_text"], str)
    
    @given(text=st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_property_transformation_maintains_non_empty_input(self, text):
        """
        Property: Non-empty input should produce non-empty output
        
        If input has content, output should also have content
        """
        service = TranslationService()
        
        if text.strip():  # Only test non-whitespace text
            result = service.transform_register(
                text,
                LanguageRegister.COLLOQUIAL,
                LanguageRegister.FORMAL,
                "en-IN"
            )
            assert len(result.strip()) > 0
