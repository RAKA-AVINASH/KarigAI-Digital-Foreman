"""
Plant Disease Detection Service

This service provides crop disease diagnosis with treatment recommendations.
"""

import os
from typing import List, Optional, Dict, Any
import json

from app.core.vision_engine import (
    VisionEngine, ImageData, EquipmentInfo, ErrorCode, PatternAnalysis,
    QualityAssessment, ProductType, InventoryItem, VisionProcessingError
)


class PlantDiseaseService(VisionEngine):
    """Crop disease detection and treatment recommendation service."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.disease_database = self._load_disease_database()
    
    def _load_disease_database(self) -> Dict[str, Any]:
        """Load disease database with treatments."""
        return {
            "fungal": {
                "powdery_mildew": {
                    "symptoms": ["White powdery coating", "Leaf curling"],
                    "treatments": ["Neem oil spray", "Sulfur fungicide", "Baking soda solution"],
                    "urgency": "Medium"
                },
                "leaf_blight": {
                    "symptoms": ["Brown spots", "Leaf yellowing"],
                    "treatments": ["Copper fungicide", "Remove infected leaves"],
                    "urgency": "High"
                }
            },
            "bacterial": {
                "bacterial_spot": {
                    "symptoms": ["Dark spots with yellow halo"],
                    "treatments": ["Copper spray", "Remove infected plants"],
                    "urgency": "High"
                }
            },
            "viral": {
                "mosaic_virus": {
                    "symptoms": ["Mottled leaves", "Stunted growth"],
                    "treatments": ["Remove infected plants", "Control aphids"],
                    "urgency": "Critical"
                }
            }
        }
    
    async def assess_quality(self, image: ImageData, product_type: ProductType) -> QualityAssessment:
        """Assess plant health and disease severity."""
        try:
            if not self.api_key:
                return self._create_fallback_assessment()
            
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            base64_image = image.to_base64()
            
            prompt = """Analyze this plant image for disease. Provide:
1. Plant species (if identifiable)
2. Disease name (if present)
3. Severity (0-100)
4. Symptoms observed
5. Confidence level

JSON format:
{
    "plant": "species",
    "disease": "disease name or Healthy",
    "severity": number,
    "symptoms": ["symptom1"],
    "confidence": number
}"""
            
            response = client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/{image.format.value};base64,{base64_image}"
                        }}
                    ]
                }],
                max_tokens=500
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Get treatment recommendations
            treatments = self._get_treatments(result.get("disease", "Unknown"))
            
            grade = "A" if result["severity"] < 20 else "B" if result["severity"] < 50 else "C"
            
            return QualityAssessment(
                grade=grade,
                score=100 - result["severity"],
                defects=[],
                price_range="",
                market_standard=result.get("plant", "Unknown plant"),
                improvement_suggestions=treatments,
                confidence_score=result.get("confidence", 70) / 100.0
            )
            
        except Exception as e:
            return self._create_fallback_assessment()
    
    def _get_treatments(self, disease_name: str) -> List[str]:
        """Get treatment recommendations for disease."""
        disease_lower = disease_name.lower()
        
        for category, diseases in self.disease_database.items():
            for disease_key, disease_data in diseases.items():
                if disease_key in disease_lower or disease_lower in disease_key:
                    return disease_data["treatments"]
        
        return ["Consult agricultural expert", "Remove affected parts"]
    
    def _create_fallback_assessment(self) -> QualityAssessment:
        """Create fallback assessment."""
        return QualityAssessment(
            grade="N/A",
            score=0.0,
            improvement_suggestions=["Image analysis not available"],
            confidence_score=0.0
        )
    
    # Implement remaining abstract methods
    async def identify_equipment(self, image: ImageData) -> EquipmentInfo:
        return EquipmentInfo(equipment_id="n/a", brand="N/A", model="N/A", category="N/A", confidence_score=0.0)
    
    async def detect_error_codes(self, image: ImageData) -> List[ErrorCode]:
        return []
    
    async def analyze_pattern(self, image: ImageData) -> PatternAnalysis:
        return PatternAnalysis(pattern_type="Not implemented", confidence_score=0.0)
    
    async def extract_text(self, image: ImageData, language_code: str) -> str:
        return ""
    
    async def count_inventory(self, image: ImageData) -> List[InventoryItem]:
        return []
    
    async def preprocess_image(self, image: ImageData, **kwargs) -> ImageData:
        return ImageData(
            image_bytes=image.image_bytes, width=image.width, height=image.height,
            format=image.format, preprocessed=True
        )
