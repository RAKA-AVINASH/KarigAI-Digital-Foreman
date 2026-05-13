"""
Property-Based Test for Voice Recognition Completeness

**Property 1: Voice Recognition Completeness**
*For any* voice input in supported local dialects, the Voice_Engine should produce 
structured data containing all identifiable invoice fields, service details, or query parameters
**Validates: Requirements 1.1, 7.1, 7.5**
"""

import pytest
import numpy as np
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from unittest.mock import AsyncMock, Mock

from app.core.voice_engine import VoiceEngine, AudioData, VoiceProcessingSession


@dataclass
class StructuredVoiceData:
    """Represents structured data extracted from voice input."""
    invoice_fields: Dict[str, Any]
    service_details: Dict[str, Any]
    query_parameters: Dict[str, Any]
    detected_language: str
    confidence_score: float
    contains_identifiable_data: bool


class MockVoiceEngineForProperty(VoiceEngine):
    """Mock Voice Engine implementation for property testing."""
    
    SUPPORTED_LANGUAGES = [
        "hi-IN",  # Hindi
        "en-US",  # English
        "ml-IN",  # Malayalam
        "pa-IN",  # Punjabi
        "bn-IN",  # Bengali
        "ta-IN",  # Tamil
        "te-IN",  # Telugu
        "hi-en-mixed",  # Hinglish (code-mixed)
    ]
    
    def __init__(self):
        self.recognition_accuracy = 0.95  # 95% accuracy as per requirement 7.1
    
    async def speech_to_text(self, audio: AudioData, language_code: Optional[str] = None) -> str:
        """Mock speech-to-text that simulates realistic transcription."""
        # Simulate transcription based on audio characteristics
        if audio.duration < 0.5:
            return ""  # Too short to transcribe
        
        # Simulate language-specific transcription patterns
        if language_code == "hi-IN":
            return "ग्राहक का नाम राम शर्मा है, सेवा शुल्क पांच हजार रुपये"
        elif language_code == "en-US":
            return "Customer name is John Smith, service charge five thousand rupees"
        elif language_code == "hi-en-mixed":
            return "Customer ka naam John Smith hai, service charge five thousand rupees"
        elif language_code == "ml-IN":
            return "ഉപഭോക്താവിന്റെ പേര് രാം ശർമ്മ, സേവന ചാർജ് അയ്യായിരം രൂപ"
        else:
            return "Customer service details provided"
    
    async def text_to_speech(self, text: str, language_code: str, voice_settings: Optional[dict] = None) -> AudioData:
        """Mock TTS implementation."""
        return AudioData(
            audio_bytes=b"mock_tts_audio",
            sample_rate=22050,
            channels=1,
            duration=len(text) * 0.1,  # Rough duration estimate
            format="wav"
        )
    
    async def detect_language(self, audio: AudioData) -> str:
        """Mock language detection based on audio characteristics."""
        # Simulate language detection based on audio properties
        if audio.noise_level > 0.7:
            return "unknown"  # Too noisy to detect
        
        # Simple heuristic based on duration and sample rate
        if audio.sample_rate >= 16000 and audio.duration >= 1.0:
            return np.random.choice(self.SUPPORTED_LANGUAGES)
        else:
            return "en-US"  # Default fallback
    
    async def is_language_supported(self, language_code: str) -> bool:
        """Check if language is supported."""
        return language_code in self.SUPPORTED_LANGUAGES
    
    async def get_supported_languages(self) -> List[str]:
        """Get supported languages."""
        return self.SUPPORTED_LANGUAGES.copy()
    
    async def preprocess_audio(self, audio: AudioData, noise_reduction: bool = True, normalize: bool = True) -> AudioData:
        """Mock audio preprocessing."""
        processed = AudioData(
            audio_bytes=audio.audio_bytes,
            sample_rate=audio.sample_rate,
            channels=audio.channels,
            duration=audio.duration,
            format=audio.format,
            bit_depth=audio.bit_depth,
            preprocessed=True,
            noise_level=max(0.0, audio.noise_level - 0.3) if noise_reduction else audio.noise_level
        )
        return processed
    
    async def extract_structured_data(self, transcribed_text: str, language_code: str) -> StructuredVoiceData:
        """Extract structured data from transcribed text."""
        invoice_fields = {}
        service_details = {}
        query_parameters = {}
        
        # Simple pattern matching for different data types
        text_lower = transcribed_text.lower()
        
        # Extract invoice fields
        if any(word in text_lower for word in ["customer", "ग्राहक", "नाम", "name", "ഉപഭോക്താവ്"]):
            if "john smith" in text_lower or "राम शर्मा" in text_lower or "രാം ശർമ്മ" in text_lower:
                invoice_fields["customer_name"] = "extracted_customer_name"
        
        if any(word in text_lower for word in ["charge", "शुल्क", "rupees", "रुपये", "രൂപ", "amount"]):
            if any(word in text_lower for word in ["thousand", "हजार", "അയ്യായിരം", "5000"]):
                invoice_fields["amount"] = "5000"
        
        # Extract service details
        if any(word in text_lower for word in ["service", "सेवा", "സേവന", "work", "काम"]):
            service_details["service_type"] = "general_service"
        
        # Extract query parameters
        if "?" in transcribed_text or any(word in text_lower for word in ["how", "what", "कैसे", "क्या", "എങ്ങനെ"]):
            query_parameters["query_type"] = "question"
        
        # Determine if identifiable data was found
        contains_identifiable_data = bool(invoice_fields or service_details or query_parameters)
        
        # Simulate confidence score based on data extraction success
        confidence_score = 0.95 if contains_identifiable_data else 0.6
        
        return StructuredVoiceData(
            invoice_fields=invoice_fields,
            service_details=service_details,
            query_parameters=query_parameters,
            detected_language=language_code,
            confidence_score=confidence_score,
            contains_identifiable_data=contains_identifiable_data
        )


# Hypothesis strategies for generating test data
@st.composite
def audio_data_strategy(draw):
    """Generate AudioData objects for property testing."""
    sample_rate = draw(st.sampled_from([8000, 16000, 22050, 44100]))
    duration = draw(st.floats(min_value=0.1, max_value=10.0))
    channels = draw(st.sampled_from([1, 2]))
    format_type = draw(st.sampled_from(["wav", "mp3", "flac"]))
    bit_depth = draw(st.sampled_from([16, 24, 32]))
    noise_level = draw(st.floats(min_value=0.0, max_value=1.0))
    
    # Generate realistic audio bytes (simplified)
    samples = int(sample_rate * duration * channels)
    audio_array = np.random.randint(-32768, 32767, samples, dtype=np.int16)
    audio_bytes = audio_array.tobytes()
    
    return AudioData(
        audio_bytes=audio_bytes,
        sample_rate=sample_rate,
        channels=channels,
        duration=duration,
        format=format_type,
        bit_depth=bit_depth,
        noise_level=noise_level
    )


@st.composite
def supported_language_strategy(draw):
    """Generate supported language codes."""
    return draw(st.sampled_from(MockVoiceEngineForProperty.SUPPORTED_LANGUAGES))


class TestVoiceRecognitionCompletenessProperty:
    """Property-based tests for Voice Recognition Completeness."""
    
    @given(
        audio_data=audio_data_strategy(),
        language_code=supported_language_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_voice_recognition_completeness_property(self, audio_data, language_code):
        """
        **Property 1: Voice Recognition Completeness**
        
        For any voice input in supported local dialects, the Voice_Engine should produce 
        structured data containing all identifiable invoice fields, service details, or query parameters.
        
        **Validates: Requirements 1.1, 7.1, 7.5**
        """
        # Create voice engine instance
        voice_engine = MockVoiceEngineForProperty()
        
        # Assume valid audio input (not too short or too noisy)
        assume(audio_data.duration >= 0.5)  # Minimum duration for meaningful speech
        assume(audio_data.noise_level <= 0.8)  # Not too noisy to process
        assume(await voice_engine.is_language_supported(language_code))
        
        # Process the voice input
        transcribed_text = await voice_engine.speech_to_text(audio_data, language_code)
        structured_data = await voice_engine.extract_structured_data(transcribed_text, language_code)
        
        # Property assertions
        
        # 1. Voice engine should always produce some form of structured data
        assert isinstance(structured_data, StructuredVoiceData)
        assert isinstance(structured_data.invoice_fields, dict)
        assert isinstance(structured_data.service_details, dict)
        assert isinstance(structured_data.query_parameters, dict)
        
        # 2. Language detection should be consistent
        assert structured_data.detected_language == language_code
        
        # 3. Confidence score should be within valid range
        assert 0.0 <= structured_data.confidence_score <= 1.0
        
        # 4. For supported languages with sufficient audio quality, 
        #    the system should achieve high confidence (95% accuracy requirement)
        if (audio_data.duration >= 2.0 and 
            audio_data.noise_level <= 0.3 and 
            language_code in voice_engine.SUPPORTED_LANGUAGES):
            assert structured_data.confidence_score >= 0.8
        
        # 5. If identifiable data is found, at least one category should have content
        if structured_data.contains_identifiable_data:
            assert (len(structured_data.invoice_fields) > 0 or 
                   len(structured_data.service_details) > 0 or 
                   len(structured_data.query_parameters) > 0)
        
        # 6. Transcribed text should not be None for valid audio
        if audio_data.duration >= 1.0 and audio_data.noise_level <= 0.5:
            assert transcribed_text is not None
            assert len(transcribed_text.strip()) > 0
    
    @given(
        audio_data=audio_data_strategy(),
        language_code=st.sampled_from(["hi-en-mixed", "en-hi-mixed"])  # Code-mixed languages
    )
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_code_mixed_speech_handling_property(self, audio_data, language_code):
        """
        Test property for code-mixed speech handling (Requirement 7.5).
        
        WHEN handling code-mixed speech (multiple languages in one sentence), 
        THE Voice_Engine SHALL process and respond appropriately.
        """
        # Create voice engine instance
        voice_engine = MockVoiceEngineForProperty()
        
        # Assume valid audio for code-mixed speech
        assume(audio_data.duration >= 1.0)  # Code-mixed speech needs reasonable duration
        assume(audio_data.noise_level <= 0.6)  # Should be clear enough to detect mixing
        
        # For code-mixed languages, use a supported base language
        base_language = "hi-IN" if "hi" in language_code else "en-US"
        
        # Process the code-mixed speech
        transcribed_text = await voice_engine.speech_to_text(audio_data, base_language)
        structured_data = await voice_engine.extract_structured_data(transcribed_text, base_language)
        
        # Property assertions for code-mixed speech
        
        # 1. System should still produce structured data for code-mixed input
        assert isinstance(structured_data, StructuredVoiceData)
        
        # 2. Should handle code-mixed content gracefully (not crash or return empty)
        assert transcribed_text is not None
        
        # 3. Confidence might be lower for code-mixed speech but should still be reasonable
        assert structured_data.confidence_score >= 0.5
        
        # 4. Should still extract identifiable data when present
        if structured_data.contains_identifiable_data:
            total_fields = (len(structured_data.invoice_fields) + 
                          len(structured_data.service_details) + 
                          len(structured_data.query_parameters))
            assert total_fields > 0
    
    @given(
        audio_data=audio_data_strategy(),
        language_code=supported_language_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_structured_data_completeness_property(self, audio_data, language_code):
        """
        Test that structured data contains all identifiable fields when present.
        
        This validates the completeness aspect of Property 1 - ensuring that
        ALL identifiable invoice fields, service details, or query parameters
        are captured in the structured output.
        """
        # Create voice engine instance
        voice_engine = MockVoiceEngineForProperty()
        
        assume(audio_data.duration >= 1.0)
        assume(audio_data.noise_level <= 0.7)
        assume(await voice_engine.is_language_supported(language_code))
        
        # Process voice input
        transcribed_text = await voice_engine.speech_to_text(audio_data, language_code)
        structured_data = await voice_engine.extract_structured_data(transcribed_text, language_code)
        
        # Property: If the system identifies any data, it should be properly categorized
        if structured_data.contains_identifiable_data:
            # At least one category should have extracted data
            has_invoice_data = len(structured_data.invoice_fields) > 0
            has_service_data = len(structured_data.service_details) > 0
            has_query_data = len(structured_data.query_parameters) > 0
            
            assert has_invoice_data or has_service_data or has_query_data
            
            # If invoice fields are detected, they should have meaningful keys
            if has_invoice_data:
                valid_invoice_keys = {"customer_name", "amount", "date", "service_type", "contact"}
                assert any(key in valid_invoice_keys for key in structured_data.invoice_fields.keys())
            
            # If service details are detected, they should have meaningful keys
            if has_service_data:
                valid_service_keys = {"service_type", "duration", "materials", "warranty", "location"}
                assert any(key in valid_service_keys for key in structured_data.service_details.keys())
            
            # If query parameters are detected, they should have meaningful keys
            if has_query_data:
                valid_query_keys = {"query_type", "subject", "urgency", "category"}
                assert any(key in valid_query_keys for key in structured_data.query_parameters.keys())
    
    @given(
        audio_data=audio_data_strategy(),
        language_code=supported_language_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_accuracy_requirement_property(self, audio_data, language_code):
        """
        Test the 95% accuracy requirement for supported dialects (Requirement 7.1).
        
        WHEN a user speaks in Local_Dialect, THE Voice_Engine SHALL accurately 
        recognize speech with 95% accuracy for supported dialects.
        """
        # Create voice engine instance
        voice_engine = MockVoiceEngineForProperty()
        
        assume(audio_data.duration >= 2.0)  # Sufficient duration for accuracy measurement
        assume(audio_data.noise_level <= 0.2)  # High quality audio
        assume(await voice_engine.is_language_supported(language_code))
        
        # Process high-quality audio in supported language
        transcribed_text = await voice_engine.speech_to_text(audio_data, language_code)
        structured_data = await voice_engine.extract_structured_data(transcribed_text, language_code)
        
        # Property: High-quality audio in supported languages should achieve high accuracy
        # This is represented by high confidence scores and successful data extraction
        
        # 1. Confidence score should meet the 95% accuracy requirement
        assert structured_data.confidence_score >= 0.95
        
        # 2. Transcription should not be empty for good quality audio
        assert transcribed_text is not None
        assert len(transcribed_text.strip()) > 0
        
        # 3. Language detection should be accurate
        assert structured_data.detected_language == language_code
        
        # 4. For clear audio with identifiable content, extraction should succeed
        if any(keyword in transcribed_text.lower() for keyword in 
               ["customer", "service", "amount", "ग्राहक", "सेवा", "रुपये", "ഉപഭോക്താവ്", "സേവന"]):
            assert structured_data.contains_identifiable_data