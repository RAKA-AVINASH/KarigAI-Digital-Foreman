"""Material OCR Service for product label reading and translation."""

import os
from typing import List, Optional, Dict, Any
from app.core.vision_engine import (
    VisionEngine, ImageData, EquipmentInfo, ErrorCode, PatternAnalysis,
    QualityAssessment, ProductType, InventoryItem
)


class MaterialOCRService(VisionEngine):
    """Material instruction translation service for product labels."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.safety_keywords = self._load_safety_keywords()
    
    def _load_safety_keywords(self) -> Dict[str, List[str]]:
        """Load safety warning keywords in multiple languages."""
        return {
            "english": ["WARNING", "CAUTION", "DANGER", "FLAMMABLE", "TOXIC", "KEEP AWAY"],
            "hindi": ["चेतावनी", "सावधान", "खतरा"],
            "symbols": ["⚠️", "🔥", "☠️", "⚡"]
        }
    
    async def extract_text(self, image: ImageData, language_code: str) -> str:
        """Extract text from product labels using OCR."""
        # Simulated OCR extraction
        return """
        Product: Construction Cement
        Instructions:
        1. Mix with water in 1:4 ratio
        2. Apply within 30 minutes
        3. Allow 24 hours for curing
        WARNING: Avoid contact with skin
        Keep away from children
        """
    
    def translate_instructions(
        self,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> Dict[str, Any]:
        """Translate instructions to local dialect."""
        # Detect safety warnings
        safety_warnings = self._extract_safety_warnings(text)
        
        # Break into steps
        steps = self._break_into_steps(text)
        
        # Simulated translation
        translated_steps = [
            f"चरण {i+1}: {step}" for i, step in enumerate(steps)
        ]
        
        return {
            "original_text": text,
            "translated_steps": translated_steps,
            "safety_warnings": safety_warnings,
            "language": target_lang,
            "audio_available": True
        }
    
    def _extract_safety_warnings(self, text: str) -> List[str]:
        """Extract safety warnings from text."""
        warnings = []
        
        for line in text.split('\n'):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            line_upper = line_stripped.upper()
            # Check if line starts with or contains a safety keyword
            for keyword in self.safety_keywords["english"]:
                if keyword in line_upper:
                    # Only add if not already in warnings
                    if line_stripped not in warnings:
                        warnings.append(line_stripped)
                    break  # Don't check other keywords for this line
        
        return warnings
    
    def _break_into_steps(self, text: str) -> List[str]:
        """Break instructions into sequential steps."""
        steps = []
        
        for line in text.split('\n'):
            line = line.strip()
            # Look for numbered steps or bullet points
            if any(line.startswith(str(i)) for i in range(1, 10)):
                steps.append(line)
            elif line.startswith('-') or line.startswith('•'):
                steps.append(line[1:].strip())
        
        return steps if steps else ["Follow product instructions"]
    
    def highlight_safety_info(self, text: str) -> Dict[str, Any]:
        """Highlight critical safety information."""
        safety_warnings = self._extract_safety_warnings(text)
        
        return {
            "has_safety_warnings": len(safety_warnings) > 0,
            "warnings": safety_warnings,
            "severity": "HIGH" if any(
                keyword in text.upper() 
                for keyword in ["DANGER", "TOXIC", "FLAMMABLE"]
            ) else "MEDIUM",
            "highlighted_text": self._add_highlights(text, safety_warnings)
        }
    
    def _add_highlights(self, text: str, warnings: List[str]) -> str:
        """Add visual highlights to safety warnings."""
        highlighted = text
        for warning in warnings:
            highlighted = highlighted.replace(warning, f"⚠️ {warning} ⚠️")
        return highlighted
    
    def generate_audio_instructions(
        self,
        steps: List[str],
        language: str
    ) -> Dict[str, Any]:
        """Generate metadata for audio instruction generation."""
        return {
            "steps": steps,
            "language": language,
            "voice_settings": {
                "speed": "slow",
                "emphasis": "safety_warnings",
                "pause_between_steps": 2.0
            },
            "audio_format": "mp3",
            "estimated_duration": len(steps) * 10  # seconds
        }
    
    # Implement remaining abstract methods
    async def identify_equipment(self, image: ImageData) -> EquipmentInfo:
        return EquipmentInfo(equipment_id="n/a", brand="N/A", model="N/A", category="N/A", confidence_score=0.0)
    
    async def detect_error_codes(self, image: ImageData) -> List[ErrorCode]:
        return []
    
    async def analyze_pattern(self, image: ImageData) -> PatternAnalysis:
        return PatternAnalysis(pattern_type="Not implemented", confidence_score=0.0)
    
    async def assess_quality(self, image: ImageData, product_type: ProductType) -> QualityAssessment:
        return QualityAssessment(grade="N/A", score=0.0, confidence_score=0.0)
    
    async def count_inventory(self, image: ImageData) -> List[InventoryItem]:
        return []
    
    async def preprocess_image(self, image: ImageData, **kwargs) -> ImageData:
        return ImageData(
            image_bytes=image.image_bytes, width=image.width, height=image.height,
            format=image.format, preprocessed=True
        )
