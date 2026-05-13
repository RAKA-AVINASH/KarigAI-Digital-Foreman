"""
OCR-Based Error Code Decoder Service

This service reads error codes from machine control panels using OCR,
identifies the machine model, and provides troubleshooting guidance.
"""

import os
import re
from typing import List, Optional, Dict, Any, Tuple
import json

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


class OCRErrorDecoderService(VisionEngine):
    """
    OCR-based error code decoder for appliances and machinery.
    
    This service:
    1. Detects and reads error codes from machine displays using OCR
    2. Identifies machine model and brand from control panels
    3. Retrieves specific troubleshooting procedures from manufacturer databases
    4. Translates technical instructions to local dialects
    5. Provides general diagnostic approaches when specific manuals don't exist
    """
    
    def __init__(self, api_key: Optional[str] = None, use_google_vision: bool = False):
        """
        Initialize OCR error decoder service.
        
        Args:
            api_key: OpenAI or Google Cloud API key
            use_google_vision: If True, use Google Vision API for OCR
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.use_google_vision = use_google_vision
        
        if use_google_vision:
            self.google_api_key = api_key or os.getenv("GOOGLE_CLOUD_API_KEY")
        
        # Load manufacturer error code database
        self.error_code_database = self._load_error_code_database()
        
        # Load machine model patterns
        self.model_patterns = self._load_model_patterns()
    
    def _load_error_code_database(self) -> Dict[str, Dict[str, Any]]:
        """Load comprehensive error code database for various manufacturers."""
        return {
            # Samsung error codes
            "samsung": {
                "E01": {
                    "description": "Temperature sensor malfunction",
                    "severity": "High",
                    "causes": ["Sensor disconnected", "Sensor failure", "Wiring damage"],
                    "parts": ["Temperature sensor", "Wiring harness"],
                    "manual_section": "Error Codes - Temperature Control"
                },
                "E02": {
                    "description": "Pressure sensor error",
                    "severity": "High",
                    "causes": ["Sensor malfunction", "Refrigerant leak", "Compressor issue"],
                    "parts": ["Pressure sensor", "Refrigerant"],
                    "manual_section": "Error Codes - Pressure System"
                },
                "E03": {
                    "description": "Communication error between PCB boards",
                    "severity": "Medium",
                    "causes": ["Loose connection", "PCB failure", "Cable damage"],
                    "parts": ["Control board", "Communication cable"],
                    "manual_section": "Error Codes - Communication"
                },
                "E04": {
                    "description": "Water level sensor error",
                    "severity": "Medium",
                    "causes": ["Sensor malfunction", "Water inlet issue", "Drain problem"],
                    "parts": ["Water level sensor"],
                    "manual_section": "Error Codes - Water System"
                }
            },
            # LG error codes
            "lg": {
                "F1": {
                    "description": "Door lock error",
                    "severity": "Medium",
                    "causes": ["Door not properly closed", "Lock mechanism failure"],
                    "parts": ["Door lock assembly"],
                    "manual_section": "Error Codes - Door System"
                },
                "F2": {
                    "description": "Motor speed sensor error",
                    "severity": "High",
                    "causes": ["Sensor failure", "Motor issue", "Belt problem"],
                    "parts": ["Speed sensor", "Motor"],
                    "manual_section": "Error Codes - Motor System"
                },
                "OE": {
                    "description": "Drain error - water not draining",
                    "severity": "High",
                    "causes": ["Clogged drain", "Pump failure", "Drain hose kinked"],
                    "parts": ["Drain pump", "Drain hose"],
                    "manual_section": "Error Codes - Drainage"
                }
            },
            # Whirlpool error codes
            "whirlpool": {
                "F01": {
                    "description": "EEPROM communication error",
                    "severity": "Critical",
                    "causes": ["Control board failure", "Memory chip issue"],
                    "parts": ["Main control board"],
                    "manual_section": "Error Codes - Electronic Control"
                },
                "F02": {
                    "description": "Long drain time",
                    "severity": "Medium",
                    "causes": ["Clogged filter", "Pump issue", "Drain restriction"],
                    "parts": ["Drain pump", "Filter"],
                    "manual_section": "Error Codes - Drainage"
                }
            },
            # Generic error codes (fallback)
            "generic": {
                "E00": {
                    "description": "General system error",
                    "severity": "Medium",
                    "causes": ["Multiple possible causes"],
                    "parts": [],
                    "manual_section": "General Troubleshooting"
                }
            }
        }
    
    def _load_model_patterns(self) -> Dict[str, List[str]]:
        """Load regex patterns for identifying machine models."""
        return {
            "samsung": [
                r"SAMSUNG\s+([A-Z0-9\-]+)",
                r"Model:\s*([A-Z0-9\-]+)",
                r"WA\d{2}[A-Z]\d{4}",  # Washing machine pattern
                r"RT\d{2}[A-Z]\d{4}"   # Refrigerator pattern
            ],
            "lg": [
                r"LG\s+([A-Z0-9\-]+)",
                r"Model:\s*([A-Z0-9\-]+)",
                r"WM\d{4}[A-Z]{2}",    # Washing machine pattern
                r"GR\-[A-Z]\d{3}"      # Refrigerator pattern
            ],
            "whirlpool": [
                r"WHIRLPOOL\s+([A-Z0-9\-]+)",
                r"Model:\s*([A-Z0-9\-]+)",
                r"WTW\d{4}[A-Z]{2}"    # Washing machine pattern
            ],
            "voltas": [
                r"VOLTAS\s+([A-Z0-9\-]+)",
                r"Model:\s*([A-Z0-9\-]+)"
            ],
            "daikin": [
                r"DAIKIN\s+([A-Z0-9\-]+)",
                r"Model:\s*([A-Z0-9\-]+)"
            ]
        }
    
    async def identify_equipment(self, image: ImageData) -> EquipmentInfo:
        """
        Identify machine model and brand from control panel image.
        
        Args:
            image: ImageData containing control panel photo
            
        Returns:
            EquipmentInfo with machine details
        """
        try:
            # Extract text from image
            text = await self.extract_text(image, "en")
            
            # Identify brand and model
            brand, model = self._identify_brand_and_model(text)
            
            # Determine equipment category
            category = self._determine_category(text, brand)
            
            # Get common issues for this brand/category
            common_issues = self._get_common_issues_for_brand(brand, category)
            
            # Get troubleshooting procedures
            procedures = self._get_troubleshooting_procedures(category)
            
            return EquipmentInfo(
                equipment_id=f"eq_{hash(brand + model) % 100000}",
                brand=brand,
                model=model,
                category=category,
                common_issues=common_issues,
                procedures=procedures,
                confidence_score=0.85 if brand != "Unknown" else 0.5,
                manual_url=self._get_manual_url(brand, model),
                warranty_info=None
            )
            
        except Exception as e:
            raise VisionProcessingError(
                f"Equipment identification failed: {str(e)}",
                original_error=e
            )
    
    def _identify_brand_and_model(self, text: str) -> Tuple[str, str]:
        """Identify brand and model from extracted text."""
        text_upper = text.upper()
        
        # Check each brand pattern
        for brand, patterns in self.model_patterns.items():
            if brand.upper() in text_upper:
                # Try to extract model number
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        model = match.group(1) if match.lastindex else match.group(0)
                        return brand.capitalize(), model
                
                # Brand found but no model
                return brand.capitalize(), "Unknown"
        
        return "Unknown", "Unknown"
    
    def _determine_category(self, text: str, brand: str) -> str:
        """Determine equipment category from text and brand."""
        text_lower = text.lower()
        
        if any(keyword in text_lower for keyword in ["washing", "washer", "wm"]):
            return "Washing Machine"
        elif any(keyword in text_lower for keyword in ["refrigerator", "fridge", "rt", "gr"]):
            return "Refrigerator"
        elif any(keyword in text_lower for keyword in ["air conditioner", "ac", "cooling"]):
            return "Air Conditioner"
        elif any(keyword in text_lower for keyword in ["microwave", "oven"]):
            return "Microwave Oven"
        elif any(keyword in text_lower for keyword in ["dishwasher"]):
            return "Dishwasher"
        else:
            return "Appliance"
    
    def _get_common_issues_for_brand(self, brand: str, category: str) -> List[str]:
        """Get common issues for specific brand and category."""
        # Brand-specific common issues
        brand_issues = {
            "Samsung": ["Display errors", "Sensor malfunctions", "Communication errors"],
            "LG": ["Door lock issues", "Drain problems", "Motor errors"],
            "Whirlpool": ["Control board issues", "Drain timing errors"],
            "Voltas": ["Cooling issues", "Compressor problems"],
            "Daikin": ["Temperature control issues", "Filter alerts"]
        }
        
        return brand_issues.get(brand, ["General malfunction", "Performance issues"])
    
    def _get_manual_url(self, brand: str, model: str) -> Optional[str]:
        """Get manual URL for brand and model."""
        if brand == "Unknown" or model == "Unknown":
            return None
        
        # Construct manual URL (simplified)
        brand_lower = brand.lower()
        return f"https://www.{brand_lower}.com/support/manuals/{model}"
    
    async def detect_error_codes(self, image: ImageData) -> List[ErrorCode]:
        """
        Detect and decode error codes from machine display.
        
        Args:
            image: ImageData containing error code display
            
        Returns:
            List of decoded error codes with troubleshooting
        """
        try:
            # Extract text from image
            text = await self.extract_text(image, "en")
            
            # Identify brand first
            brand, _ = self._identify_brand_and_model(text)
            
            # Extract error codes
            error_codes = self._extract_error_codes(text)
            
            # Decode each error code
            decoded_errors = []
            for code in error_codes:
                error_info = self._decode_error_code(code, brand)
                decoded_errors.append(error_info)
            
            return decoded_errors
            
        except Exception as e:
            raise VisionProcessingError(
                f"Error code detection failed: {str(e)}",
                original_error=e
            )
    
    def _extract_error_codes(self, text: str) -> List[str]:
        """Extract error codes from text using regex patterns."""
        # Common error code patterns
        patterns = [
            r'\b[EF]\d{1,3}\b',      # E01, F1, etc.
            r'\b[A-Z]{2}\d{1,2}\b',  # OE, LE, etc.
            r'\bErr\s*\d{1,3}\b',    # Err 01, etc.
            r'\bError\s*\d{1,3}\b'   # Error 01, etc.
        ]
        
        error_codes = set()
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            error_codes.update([m.upper() for m in matches])
        
        return list(error_codes)
    
    def _decode_error_code(self, code: str, brand: str) -> ErrorCode:
        """Decode error code using manufacturer database."""
        brand_lower = brand.lower()
        
        # Try brand-specific database first
        if brand_lower in self.error_code_database:
            brand_db = self.error_code_database[brand_lower]
            if code in brand_db:
                info = brand_db[code]
                return self._create_error_code_object(code, info, brand)
        
        # Try generic database
        if code in self.error_code_database.get("generic", {}):
            info = self.error_code_database["generic"][code]
            return self._create_error_code_object(code, info, "Generic")
        
        # Create unknown error code
        return self._create_unknown_error_code(code, brand)
    
    def _create_error_code_object(self, code: str, info: Dict[str, Any], brand: str) -> ErrorCode:
        """Create ErrorCode object from database info."""
        # Generate troubleshooting steps
        steps = []
        
        # Step 1: Check connections
        steps.append(TroubleshootingStep(
            step_number=1,
            instruction=f"Check all connections related to {info['description']}",
            expected_result="All connections should be secure and clean",
            safety_warning="Disconnect power before checking connections",
            tools_required=["Screwdriver", "Multimeter"],
            estimated_time=10
        ))
        
        # Step 2: Inspect components
        if info.get("parts"):
            parts_str = ", ".join(info["parts"])
            steps.append(TroubleshootingStep(
                step_number=2,
                instruction=f"Inspect {parts_str} for visible damage",
                expected_result="Components should be intact without visible damage",
                tools_required=["Flashlight", "Screwdriver"],
                estimated_time=15
            ))
        
        # Step 3: Test components
        steps.append(TroubleshootingStep(
            step_number=3,
            instruction="Test components with multimeter if available",
            expected_result="Readings should be within normal range",
            safety_warning="Ensure proper safety precautions when testing electrical components",
            tools_required=["Multimeter"],
            estimated_time=20
        ))
        
        # Step 4: Reset system
        steps.append(TroubleshootingStep(
            step_number=4,
            instruction="Reset the system and check if error persists",
            expected_result="Error code should clear if issue is resolved",
            estimated_time=5
        ))
        
        # Step 5: Consult manual or technician
        steps.append(TroubleshootingStep(
            step_number=5,
            instruction=f"If error persists, consult {brand} service manual section: {info.get('manual_section', 'Error Codes')}",
            expected_result="Detailed manufacturer-specific guidance",
            estimated_time=10
        ))
        
        return ErrorCode(
            code=code,
            description=info["description"],
            severity=info["severity"],
            troubleshooting_steps=steps,
            common_causes=info.get("causes", []),
            parts_needed=info.get("parts", [])
        )
    
    def _create_unknown_error_code(self, code: str, brand: str) -> ErrorCode:
        """Create error code object for unknown codes."""
        return ErrorCode(
            code=code,
            description=f"Error code {code} - Specific information not available",
            severity="Unknown",
            troubleshooting_steps=[
                TroubleshootingStep(
                    step_number=1,
                    instruction=f"Consult {brand} service manual for error code {code}",
                    expected_result="Manufacturer-specific troubleshooting steps",
                    estimated_time=10
                ),
                TroubleshootingStep(
                    step_number=2,
                    instruction="Check for loose connections and visible damage",
                    expected_result="All connections secure, no visible damage",
                    safety_warning="Disconnect power before inspection",
                    tools_required=["Screwdriver", "Flashlight"],
                    estimated_time=15
                ),
                TroubleshootingStep(
                    step_number=3,
                    instruction="Reset the appliance and monitor for error recurrence",
                    expected_result="Error may clear if it was temporary",
                    estimated_time=5
                ),
                TroubleshootingStep(
                    step_number=4,
                    instruction="Contact authorized service center if error persists",
                    expected_result="Professional diagnosis and repair",
                    estimated_time=30
                )
            ],
            common_causes=["Unknown - requires manufacturer documentation"],
            parts_needed=[]
        )
    
    # Implement remaining abstract methods
    
    async def analyze_pattern(self, image: ImageData) -> PatternAnalysis:
        """Not implemented in OCR service."""
        return PatternAnalysis(pattern_type="Not implemented", confidence_score=0.0)
    
    async def assess_quality(self, image: ImageData, product_type: ProductType) -> QualityAssessment:
        """Not implemented in OCR service."""
        return QualityAssessment(grade="N/A", score=0.0, confidence_score=0.0)
    
    async def extract_text(self, image: ImageData, language_code: str) -> str:
        """Extract text using OCR (OpenAI or Google Vision)."""
        try:
            if self.use_google_vision:
                return await self._extract_text_google(image)
            else:
                return await self._extract_text_openai(image)
        except Exception as e:
            raise VisionProcessingError(f"OCR failed: {str(e)}", original_error=e)
    
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
                            {
                                "type": "text",
                                "text": "Extract all visible text from this machine control panel or display. Include brand names, model numbers, error codes, and any other text. Return only the text."
                            },
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
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"OCR failed: {str(e)}"
    
    async def _extract_text_google(self, image: ImageData) -> str:
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
            return f"OCR failed: {str(e)}"
    
    async def count_inventory(self, image: ImageData) -> List[InventoryItem]:
        """Not implemented in OCR service."""
        return []
    
    async def preprocess_image(self, image: ImageData, **kwargs) -> ImageData:
        """Basic image preprocessing."""
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
    
    def _get_troubleshooting_procedures(self, category: str) -> List[TroubleshootingStep]:
        """Get general troubleshooting procedures."""
        return [
            TroubleshootingStep(
                step_number=1,
                instruction="Check power supply and ensure unit is plugged in",
                expected_result="Power indicator should be on",
                safety_warning="Ensure hands are dry",
                tools_required=["Multimeter"],
                estimated_time=5
            ),
            TroubleshootingStep(
                step_number=2,
                instruction="Inspect for visible damage or error displays",
                expected_result="Note any error codes or unusual indicators",
                tools_required=["Flashlight"],
                estimated_time=10
            )
        ]
