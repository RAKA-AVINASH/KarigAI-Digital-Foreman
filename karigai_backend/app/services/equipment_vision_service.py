"""
Equipment Vision Service

This service implements equipment identification and error code recognition
using OpenAI GPT-4V or Google Vision API.
"""

import os
import json
from typing import List, Optional, Dict, Any
import base64

from app.core.vision_engine import (
    VisionEngine,
    ImageData,
    EquipmentInfo,
    ErrorCode,
    TroubleshootingStep,
    PatternAnalysis,
    QualityAssessment,
    ProductType,
    InventoryItem,
    VisionProcessingError
)


class EquipmentVisionService(VisionEngine):
    """
    Equipment identification service using OpenAI GPT-4V.
    
    This service identifies equipment from images, detects error codes,
    and provides troubleshooting guidance.
    """
    
    def __init__(self, api_key: Optional[str] = None, use_google_vision: bool = False):
        """
        Initialize equipment vision service.
        
        Args:
            api_key: OpenAI or Google Cloud API key
            use_google_vision: If True, use Google Vision API instead of OpenAI
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.use_google_vision = use_google_vision
        
        if use_google_vision:
            self.google_api_key = api_key or os.getenv("GOOGLE_CLOUD_API_KEY")
        
        # Equipment database for common Indian brands
        self.equipment_database = self._load_equipment_database()
    
    def _load_equipment_database(self) -> Dict[str, Any]:
        """Load equipment database with common Indian brands and models."""
        return {
            "air_conditioners": {
                "brands": ["Samsung", "LG", "Voltas", "Daikin", "Blue Star", "Hitachi"],
                "common_issues": [
                    "Not cooling properly",
                    "Water leakage",
                    "Strange noise",
                    "Remote not working",
                    "Compressor not starting"
                ]
            },
            "refrigerators": {
                "brands": ["Samsung", "LG", "Whirlpool", "Godrej", "Haier"],
                "common_issues": [
                    "Not cooling",
                    "Ice formation",
                    "Water leakage",
                    "Door not closing",
                    "Strange noise"
                ]
            },
            "washing_machines": {
                "brands": ["Samsung", "LG", "Whirlpool", "IFB", "Bosch"],
                "common_issues": [
                    "Not spinning",
                    "Water not draining",
                    "Door not opening",
                    "Excessive vibration",
                    "Not starting"
                ]
            },
            "water_heaters": {
                "brands": ["Bajaj", "Racold", "AO Smith", "Havells", "V-Guard"],
                "common_issues": [
                    "Not heating",
                    "Water leakage",
                    "Thermostat issue",
                    "Element failure",
                    "Safety valve problem"
                ]
            }
        }
    
    async def identify_equipment(self, image: ImageData) -> EquipmentInfo:
        """
        Identify equipment from image using GPT-4V or Google Vision.
        
        Args:
            image: ImageData object containing equipment photo
            
        Returns:
            EquipmentInfo with identification results
        """
        try:
            if self.use_google_vision:
                return await self._identify_with_google_vision(image)
            else:
                return await self._identify_with_gpt4v(image)
        except Exception as e:
            raise VisionProcessingError(
                f"Equipment identification failed: {str(e)}",
                error_code="EQUIPMENT_ID_FAILED",
                original_error=e
            )
    
    async def _identify_with_gpt4v(self, image: ImageData) -> EquipmentInfo:
        """Identify equipment using OpenAI GPT-4V."""
        try:
            import openai
            
            if not self.api_key:
                raise VisionProcessingError("OpenAI API key not configured")
            
            client = openai.OpenAI(api_key=self.api_key)
            
            # Convert image to base64
            base64_image = image.to_base64()
            
            # Create prompt for equipment identification
            prompt = """Analyze this image and identify the equipment shown. Provide:
1. Equipment type/category (e.g., Air Conditioner, Refrigerator, Washing Machine)
2. Brand name if visible
3. Model number if visible
4. Common issues for this type of equipment
5. Confidence level (0-100%)

Respond in JSON format:
{
    "category": "equipment category",
    "brand": "brand name or Unknown",
    "model": "model number or Unknown",
    "common_issues": ["issue1", "issue2", "issue3"],
    "confidence": 85
}"""
            
            response = client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{image.format.value};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            
            # Parse response
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            # Get troubleshooting procedures from database
            procedures = self._get_troubleshooting_procedures(result["category"])
            
            return EquipmentInfo(
                equipment_id=f"eq_{hash(result['brand'] + result['model']) % 100000}",
                brand=result.get("brand", "Unknown"),
                model=result.get("model", "Unknown"),
                category=result.get("category", "Unknown"),
                common_issues=result.get("common_issues", []),
                procedures=procedures,
                confidence_score=result.get("confidence", 80) / 100.0,
                manual_url=None,
                warranty_info=None
            )
            
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return self._create_fallback_equipment_info(image)
        except Exception as e:
            raise VisionProcessingError(
                f"GPT-4V identification failed: {str(e)}",
                original_error=e
            )
    
    async def _identify_with_google_vision(self, image: ImageData) -> EquipmentInfo:
        """Identify equipment using Google Vision API."""
        try:
            from google.cloud import vision
            
            if not self.google_api_key:
                raise VisionProcessingError("Google Cloud API key not configured")
            
            client = vision.ImageAnnotatorClient()
            
            # Create vision image
            vision_image = vision.Image(content=image.image_bytes)
            
            # Perform label detection
            response = client.label_detection(image=vision_image)
            labels = response.label_annotations
            
            # Perform text detection for brand/model
            text_response = client.text_detection(image=vision_image)
            texts = text_response.text_annotations
            
            # Extract equipment information from labels
            category = "Unknown"
            confidence = 0.5
            
            for label in labels[:5]:  # Check top 5 labels
                if any(keyword in label.description.lower() for keyword in 
                       ["air conditioner", "refrigerator", "washing machine", "heater"]):
                    category = label.description
                    confidence = label.score
                    break
            
            # Extract brand and model from text
            brand = "Unknown"
            model = "Unknown"
            if texts:
                full_text = texts[0].description
                # Simple heuristic to extract brand/model
                words = full_text.split()
                for word in words:
                    if word.upper() in ["SAMSUNG", "LG", "VOLTAS", "DAIKIN", "WHIRLPOOL"]:
                        brand = word.capitalize()
                        break
            
            procedures = self._get_troubleshooting_procedures(category)
            common_issues = self._get_common_issues(category)
            
            return EquipmentInfo(
                equipment_id=f"eq_{hash(brand + model) % 100000}",
                brand=brand,
                model=model,
                category=category,
                common_issues=common_issues,
                procedures=procedures,
                confidence_score=confidence
            )
            
        except Exception as e:
            raise VisionProcessingError(
                f"Google Vision identification failed: {str(e)}",
                original_error=e
            )
    
    def _create_fallback_equipment_info(self, image: ImageData) -> EquipmentInfo:
        """Create fallback equipment info when AI fails."""
        return EquipmentInfo(
            equipment_id="eq_unknown",
            brand="Unknown",
            model="Unknown",
            category="Appliance",
            common_issues=["Unable to identify specific issues"],
            procedures=[],
            confidence_score=0.3
        )
    
    def _get_troubleshooting_procedures(self, category: str) -> List[TroubleshootingStep]:
        """Get troubleshooting procedures for equipment category."""
        # Generic troubleshooting steps
        return [
            TroubleshootingStep(
                step_number=1,
                instruction="Check power supply and ensure the unit is plugged in",
                expected_result="Power indicator should light up",
                safety_warning="Ensure hands are dry before touching electrical connections",
                tools_required=["Multimeter"],
                estimated_time=5
            ),
            TroubleshootingStep(
                step_number=2,
                instruction="Inspect for visible damage or loose connections",
                expected_result="All connections should be secure and intact",
                tools_required=["Screwdriver", "Flashlight"],
                estimated_time=10
            ),
            TroubleshootingStep(
                step_number=3,
                instruction="Check circuit breaker and reset if tripped",
                expected_result="Circuit breaker should be in ON position",
                safety_warning="Turn off main power before checking breaker",
                estimated_time=5
            )
        ]
    
    def _get_common_issues(self, category: str) -> List[str]:
        """Get common issues for equipment category."""
        category_lower = category.lower()
        
        for eq_type, data in self.equipment_database.items():
            if any(keyword in category_lower for keyword in eq_type.split("_")):
                return data["common_issues"]
        
        return ["General malfunction", "Power issues", "Performance degradation"]
    
    async def detect_error_codes(self, image: ImageData) -> List[ErrorCode]:
        """
        Detect error codes from equipment displays using OCR.
        
        Args:
            image: ImageData containing error code display
            
        Returns:
            List of detected error codes with troubleshooting
        """
        try:
            # Extract text from image
            text = await self.extract_text(image, "en")
            
            # Parse error codes (format: E01, E02, F1, F2, etc.)
            import re
            error_pattern = r'[EF]\d{1,3}'
            matches = re.findall(error_pattern, text.upper())
            
            error_codes = []
            for code in matches:
                error_info = self._get_error_code_info(code)
                error_codes.append(error_info)
            
            return error_codes
            
        except Exception as e:
            raise VisionProcessingError(
                f"Error code detection failed: {str(e)}",
                original_error=e
            )
    
    def _get_error_code_info(self, code: str) -> ErrorCode:
        """Get error code information from database."""
        # Error code database (simplified)
        error_database = {
            "E01": {
                "description": "Temperature sensor error",
                "severity": "High",
                "causes": ["Sensor disconnected", "Sensor failure", "Wiring issue"],
                "parts": ["Temperature sensor"]
            },
            "E02": {
                "description": "Pressure sensor error",
                "severity": "High",
                "causes": ["Sensor malfunction", "Refrigerant leak"],
                "parts": ["Pressure sensor"]
            },
            "F1": {
                "description": "Communication error",
                "severity": "Medium",
                "causes": ["Loose connection", "Control board issue"],
                "parts": ["Control board"]
            }
        }
        
        info = error_database.get(code, {
            "description": f"Error code {code}",
            "severity": "Unknown",
            "causes": ["Unknown cause"],
            "parts": []
        })
        
        return ErrorCode(
            code=code,
            description=info["description"],
            severity=info["severity"],
            troubleshooting_steps=[
                TroubleshootingStep(
                    step_number=1,
                    instruction=f"Check connections related to {info['description']}",
                    expected_result="Connections should be secure",
                    tools_required=["Screwdriver"],
                    estimated_time=10
                ),
                TroubleshootingStep(
                    step_number=2,
                    instruction="Reset the system and check if error persists",
                    expected_result="Error code should clear if issue is resolved",
                    estimated_time=5
                )
            ],
            common_causes=info.get("causes", []),
            parts_needed=info.get("parts", [])
        )
    
    # Implement remaining abstract methods with basic functionality
    
    async def analyze_pattern(self, image: ImageData) -> PatternAnalysis:
        """Basic pattern analysis (to be enhanced in task 3.9)."""
        return PatternAnalysis(
            pattern_type="Not implemented",
            confidence_score=0.0
        )
    
    async def assess_quality(self, image: ImageData, product_type: ProductType) -> QualityAssessment:
        """Basic quality assessment (to be enhanced in task 3.12)."""
        return QualityAssessment(
            grade="N/A",
            score=0.0,
            confidence_score=0.0
        )
    
    async def extract_text(self, image: ImageData, language_code: str) -> str:
        """Extract text using OCR."""
        try:
            if self.use_google_vision:
                return await self._extract_text_google(image, language_code)
            else:
                return await self._extract_text_openai(image)
        except Exception as e:
            raise VisionProcessingError(
                f"Text extraction failed: {str(e)}",
                original_error=e
            )
    
    async def _extract_text_openai(self, image: ImageData) -> str:
        """Extract text using OpenAI GPT-4V."""
        try:
            import openai
            
            if not self.api_key:
                return "OCR not available - API key not configured"
            
            client = openai.OpenAI(api_key=self.api_key)
            base64_image = image.to_base64()
            
            response = client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract all visible text from this image. Return only the text, nothing else."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{image.format.value};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Text extraction failed: {str(e)}"
    
    async def _extract_text_google(self, image: ImageData, language_code: str) -> str:
        """Extract text using Google Vision API."""
        try:
            from google.cloud import vision
            
            client = vision.ImageAnnotatorClient()
            vision_image = vision.Image(content=image.image_bytes)
            
            response = client.text_detection(image=vision_image)
            texts = response.text_annotations
            
            if texts:
                return texts[0].description
            return ""
            
        except Exception as e:
            return f"Text extraction failed: {str(e)}"
    
    async def count_inventory(self, image: ImageData) -> List[InventoryItem]:
        """Basic inventory counting (to be enhanced in task 3.6)."""
        return []
    
    async def preprocess_image(self, image: ImageData, **kwargs) -> ImageData:
        """Basic image preprocessing."""
        # For now, just return the image with preprocessed flag
        return ImageData(
            image_bytes=image.image_bytes,
            width=image.width,
            height=image.height,
            format=image.format,
            file_path=image.file_path,
            file_size=image.file_size,
            preprocessed=True,
            metadata=image.metadata
        )
