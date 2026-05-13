"""
Unit tests for Translation Service
"""

import pytest
from app.services.translation_service import (
    TranslationService,
    LanguageRegister
)


@pytest.fixture
def translation_service():
    """Create a translation service instance"""
    return TranslationService()


class TestTranslationService:
    """Test suite for Translation Service"""
    
    def test_supported_languages(self, translation_service):
        """Test that common Indian languages are supported"""
        assert translation_service.is_language_supported("hi-IN")
        assert translation_service.is_language_supported("en-IN")
        assert translation_service.is_language_supported("ml-IN")
        assert not translation_service.is_language_supported("fr-FR")
    
    def test_colloquial_to_formal_english(self, translation_service):
        """Test colloquial to formal transformation in English"""
        text = "yeah I gonna fix it"
        result = translation_service.transform_register(
            text,
            LanguageRegister.COLLOQUIAL,
            LanguageRegister.FORMAL,
            "en-IN"
        )
        
        assert "going to" in result
        assert "yes" in result
        assert "gonna" not in result
    
    def test_colloquial_to_business_english(self, translation_service):
        """Test colloquial to business transformation"""
        text = "yeah I can help"
        result = translation_service.transform_register(
            text,
            LanguageRegister.COLLOQUIAL,
            LanguageRegister.BUSINESS,
            "en-IN"
        )
        
        assert "Dear Sir/Madam" in result
        assert "yes" in result
    
    def test_same_register_returns_unchanged(self, translation_service):
        """Test that same register transformation returns unchanged text"""
        text = "This is formal text"
        result = translation_service.transform_register(
            text,
            LanguageRegister.FORMAL,
            LanguageRegister.FORMAL,
            "en-IN"
        )
        
        assert result == text
    
    def test_technical_terms_preservation(self, translation_service):
        """Test that technical terms are preserved"""
        text = "Check the voltage and circuit"
        result = translation_service.transform_register(
            text,
            LanguageRegister.COLLOQUIAL,
            LanguageRegister.TECHNICAL,
            "en-IN"
        )
        
        assert "[TECH]voltage[/TECH]" in result
        assert "[TECH]circuit[/TECH]" in result
    
    def test_translate_same_language(self, translation_service):
        """Test translation with same source and target language"""
        text = "Hello world"
        result = translation_service.translate_with_register(
            text,
            "en-IN",
            "en-IN"
        )
        
        assert result == text
    
    def test_translate_with_register(self, translation_service):
        """Test translation with register transformation"""
        text = "gonna help you"
        result = translation_service.translate_with_register(
            text,
            "en-IN",
            "hi-IN",
            LanguageRegister.FORMAL
        )
        
        # Should be translated and formalized
        assert result is not None
        assert len(result) > 0
    
    def test_code_mixed_speech_processing(self, translation_service):
        """Test processing of code-mixed speech"""
        text = "Main gonna market जाऊंगा"
        result = translation_service.process_code_mixed_speech(
            text,
            "hi-IN",
            "en-IN"
        )
        
        assert result["original_text"] == text
        assert result["processed_text"] is not None
        assert result["primary_language"] == "hi-IN"
        assert len(result["segments"]) > 0
    
    def test_code_mixed_segments_detection(self, translation_service):
        """Test that code-mixed segments are detected"""
        text = "I am going बाजार to buy सब्जी"
        result = translation_service.process_code_mixed_speech(
            text,
            "hi-IN",
            "en-IN"
        )
        
        segments = result["segments"]
        assert len(segments) > 1
        # Should detect both English and Hindi segments
        languages = [seg["language"] for seg in segments]
        assert "hi-IN" in languages
        assert "en-IN" in languages
    
    def test_empty_text_handling(self, translation_service):
        """Test handling of empty text"""
        result = translation_service.transform_register(
            "",
            LanguageRegister.COLLOQUIAL,
            LanguageRegister.FORMAL,
            "en-IN"
        )
        
        assert result == ""
    
    def test_unsupported_language_handling(self, translation_service):
        """Test handling of unsupported language"""
        text = "Hello"
        # Should still process even if language not in mappings
        result = translation_service.transform_register(
            text,
            LanguageRegister.COLLOQUIAL,
            LanguageRegister.FORMAL,
            "unsupported-lang"
        )
        
        assert result == text  # Returns unchanged
    
    def test_multiple_technical_terms(self, translation_service):
        """Test preservation of multiple technical terms"""
        text = "Check voltage, circuit, and ampere readings"
        result = translation_service.transform_register(
            text,
            LanguageRegister.COLLOQUIAL,
            LanguageRegister.TECHNICAL,
            "en-IN"
        )
        
        assert "[TECH]voltage[/TECH]" in result
        assert "[TECH]circuit[/TECH]" in result
        assert "[TECH]ampere[/TECH]" in result
    
    def test_register_mappings_exist(self, translation_service):
        """Test that register mappings are defined"""
        assert "hi-IN" in translation_service.register_mappings
        assert "en-IN" in translation_service.register_mappings
        assert len(translation_service.register_mappings["en-IN"]) > 0
    
    def test_technical_terms_list_exists(self, translation_service):
        """Test that technical terms list is defined"""
        assert len(translation_service.technical_terms) > 0
        assert "voltage" in translation_service.technical_terms
        assert "circuit" in translation_service.technical_terms
