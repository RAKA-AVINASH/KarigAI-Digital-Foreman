"""
Translation and Localization Service

This service provides language register transformation, colloquial to formal
business language conversion, and technical content translation.
"""

from typing import Dict, List, Optional
from enum import Enum


class LanguageRegister(Enum):
    """Language register types"""
    COLLOQUIAL = "colloquial"
    FORMAL = "formal"
    TECHNICAL = "technical"
    BUSINESS = "business"


class TranslationService:
    """
    Service for translation and localization
    
    Provides:
    - Language register transformation
    - Colloquial to formal business language conversion
    - Technical content translation with accuracy preservation
    - Code-mixed speech processing
    """
    
    def __init__(self):
        """Initialize the translation service"""
        self.supported_languages = [
            "hi-IN",  # Hindi
            "en-IN",  # English (India)
            "ml-IN",  # Malayalam
            "pa-IN",  # Punjabi
            "bn-IN",  # Bengali
            "ta-IN",  # Tamil
            "te-IN",  # Telugu
            "mr-IN",  # Marathi
            "gu-IN",  # Gujarati
        ]
        
        # Colloquial to formal mappings (simplified examples)
        self.register_mappings = {
            "hi-IN": {
                "kya": "क्या",
                "hai": "है",
                "thik": "ठीक",
                "kaam": "काम",
                "paisa": "रुपये",
            },
            "en-IN": {
                "gonna": "going to",
                "wanna": "want to",
                "gotta": "have to",
                "yeah": "yes",
                "nope": "no",
            }
        }
        
        # Technical terms that should be preserved
        self.technical_terms = {
            "voltage", "circuit", "ampere", "watt", "ohm",
            "pipe", "valve", "pressure", "flow", "leak",
            "motor", "compressor", "refrigerant", "thermostat",
            "error code", "diagnostic", "troubleshoot"
        }
    
    def transform_register(
        self,
        text: str,
        source_register: LanguageRegister,
        target_register: LanguageRegister,
        language: str = "en-IN"
    ) -> str:
        """
        Transform text from one language register to another
        
        Args:
            text: Input text
            source_register: Source language register
            target_register: Target language register
            language: Language code
            
        Returns:
            Transformed text
        """
        if source_register == target_register:
            return text
        
        # Colloquial to formal transformation
        if source_register == LanguageRegister.COLLOQUIAL and target_register == LanguageRegister.FORMAL:
            return self._colloquial_to_formal(text, language)
        
        # Colloquial to business transformation
        if source_register == LanguageRegister.COLLOQUIAL and target_register == LanguageRegister.BUSINESS:
            formal_text = self._colloquial_to_formal(text, language)
            return self._formal_to_business(formal_text, language)
        
        # Technical preservation
        if target_register == LanguageRegister.TECHNICAL:
            return self._preserve_technical_terms(text)
        
        return text
    
    def translate_with_register(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        target_register: LanguageRegister = LanguageRegister.FORMAL
    ) -> str:
        """
        Translate text while maintaining appropriate register
        
        Args:
            text: Input text
            source_lang: Source language code
            target_lang: Target language code
            target_register: Desired register in target language
            
        Returns:
            Translated text
        """
        # In production, this would use a translation API
        # For now, we'll simulate the translation
        
        if source_lang == target_lang:
            return text
        
        # Simulate translation (in production, use Google Translate API or similar)
        translated = self._simulate_translation(text, source_lang, target_lang)
        
        # Apply register transformation
        if target_register != LanguageRegister.COLLOQUIAL:
            translated = self.transform_register(
                translated,
                LanguageRegister.COLLOQUIAL,
                target_register,
                target_lang
            )
        
        return translated
    
    def process_code_mixed_speech(
        self,
        text: str,
        primary_language: str,
        secondary_language: str
    ) -> Dict[str, any]:
        """
        Process code-mixed speech (multiple languages in one sentence)
        
        Args:
            text: Input text with mixed languages
            primary_language: Primary language code
            secondary_language: Secondary language code
            
        Returns:
            Dictionary with processed text and language segments
        """
        # Detect language segments
        segments = self._detect_language_segments(text, primary_language, secondary_language)
        
        # Process each segment
        processed_segments = []
        for segment in segments:
            processed_text = segment["text"]
            if segment["language"] != primary_language:
                # Translate to primary language
                processed_text = self.translate_with_register(
                    segment["text"],
                    segment["language"],
                    primary_language
                )
            processed_segments.append({
                "original": segment["text"],
                "processed": processed_text,
                "language": segment["language"]
            })
        
        # Combine processed segments
        combined_text = " ".join([seg["processed"] for seg in processed_segments])
        
        return {
            "original_text": text,
            "processed_text": combined_text,
            "segments": processed_segments,
            "primary_language": primary_language
        }
    
    def is_language_supported(self, language_code: str) -> bool:
        """Check if a language is supported"""
        return language_code in self.supported_languages
    
    def _colloquial_to_formal(self, text: str, language: str) -> str:
        """Convert colloquial language to formal"""
        if language not in self.register_mappings:
            return text
        
        formal_text = text
        mappings = self.register_mappings[language]
        
        for colloquial, formal in mappings.items():
            # Simple word replacement (in production, use NLP)
            formal_text = formal_text.replace(colloquial, formal)
        
        return formal_text
    
    def _formal_to_business(self, text: str, language: str) -> str:
        """Convert formal language to business language"""
        # Add business-appropriate phrases
        business_prefixes = {
            "en-IN": "Dear Sir/Madam, ",
            "hi-IN": "आदरणीय महोदय/महोदया, "
        }
        
        prefix = business_prefixes.get(language, "")
        return f"{prefix}{text}"
    
    def _preserve_technical_terms(self, text: str) -> str:
        """Preserve technical terms during translation"""
        # Mark technical terms for preservation
        preserved_text = text
        for term in self.technical_terms:
            if term.lower() in text.lower():
                # In production, mark these for the translation API
                preserved_text = preserved_text.replace(term, f"[TECH]{term}[/TECH]")
        
        return preserved_text
    
    def _simulate_translation(self, text: str, source_lang: str, target_lang: str) -> str:
        """Simulate translation (placeholder for actual translation API)"""
        # In production, this would call Google Translate API, Azure Translator, etc.
        # For now, return the original text with a marker
        return f"[Translated from {source_lang} to {target_lang}] {text}"
    
    def _detect_language_segments(
        self,
        text: str,
        primary_language: str,
        secondary_language: str
    ) -> List[Dict[str, str]]:
        """Detect language segments in code-mixed text"""
        # Simplified language detection (in production, use langdetect or similar)
        # For now, split by common code-mixing patterns
        
        words = text.split()
        segments = []
        current_segment = {"text": "", "language": primary_language}
        
        for word in words:
            # Simple heuristic: if word contains non-ASCII, it's likely primary language
            if any(ord(char) > 127 for char in word):
                if current_segment["language"] != primary_language:
                    if current_segment["text"]:
                        segments.append(current_segment)
                    current_segment = {"text": word, "language": primary_language}
                else:
                    current_segment["text"] += " " + word
            else:
                if current_segment["language"] != secondary_language:
                    if current_segment["text"]:
                        segments.append(current_segment)
                    current_segment = {"text": word, "language": secondary_language}
                else:
                    current_segment["text"] += " " + word
        
        if current_segment["text"]:
            segments.append(current_segment)
        
        return segments
