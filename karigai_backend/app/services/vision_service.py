from sqlalchemy.orm import Session
from fastapi import UploadFile
from typing import Optional, List
import time
import io
from PIL import Image

from app.schemas.vision import (
    EquipmentIdentificationResponse, 
    VisionAnalysisResponse,
    EquipmentInfo,
    ErrorCode,
    PatternAnalysis,
    QualityAssessment,
    TroubleshootingStep,
    InventoryCountResponse,
    InventoryItem
)
from app.core.vision_engine import (
    VisionEngine,
    ImageData,
    ImageFormat,
    ProductType,
    VisionProcessingError
)


class VisionService:
    """
    Vision service that orchestrates vision processing operations.
    This service acts as a facade for the VisionEngine interface.
    """
    
    def __init__(self, db: Session, vision_engine: Optional[VisionEngine] = None):
        self.db = db
        self.vision_engine = vision_engine
    
    async def _upload_file_to_image_data(self, image_file: UploadFile) -> ImageData:
        """Convert UploadFile to ImageData object."""
        # Read image bytes
        image_bytes = await image_file.read()
        
        # Open image to get dimensions
        image = Image.open(io.BytesIO(image_bytes))
        width, height = image.size
        
        # Determine format
        format_map = {
            'image/jpeg': ImageFormat.JPEG,
            'image/png': ImageFormat.PNG,
            'image/webp': ImageFormat.WEBP,
            'image/bmp': ImageFormat.BMP,
            'image/tiff': ImageFormat.TIFF
        }
        image_format = format_map.get(image_file.content_type, ImageFormat.JPEG)
        
        return ImageData(
            image_bytes=image_bytes,
            width=width,
            height=height,
            format=image_format,
            file_path=image_file.filename,
            file_size=len(image_bytes)
        )
    
    async def identify_equipment(
        self, 
        image_file: UploadFile, 
        user_id: Optional[str] = None
    ) -> EquipmentIdentificationResponse:
        """Identify equipment from image"""
        start_time = time.time()
        
        # Convert upload file to ImageData
        image_data = await self._upload_file_to_image_data(image_file)
        
        if self.vision_engine:
            # Use actual vision engine if available
            try:
                equipment_info_obj = await self.vision_engine.identify_equipment(image_data)
                error_codes_obj = await self.vision_engine.detect_error_codes(image_data)
                
                # Convert to Pydantic models
                equipment_info = EquipmentInfo(**equipment_info_obj.__dict__)
                error_codes = [ErrorCode(**ec.__dict__) for ec in error_codes_obj]
                
            except VisionProcessingError as e:
                # Fallback to placeholder on error
                equipment_info = self._get_placeholder_equipment()
                error_codes = self._get_placeholder_error_codes()
        else:
            # Placeholder implementation when no engine is configured
            equipment_info = self._get_placeholder_equipment()
            error_codes = self._get_placeholder_error_codes()
        
        processing_time = time.time() - start_time
        
        return EquipmentIdentificationResponse(
            equipment_info=equipment_info,
            error_codes=error_codes,
            troubleshooting_available=True,
            processing_time=processing_time
        )
    
    def _get_placeholder_equipment(self) -> EquipmentInfo:
        """Get placeholder equipment info for testing."""
        return EquipmentInfo(
            equipment_id="eq_001",
            brand="Samsung",
            model="AC-2024",
            category="Air Conditioner",
            common_issues=["Not cooling", "Strange noise", "Water leakage"],
            procedures=[
                TroubleshootingStep(
                    step_number=1,
                    instruction="Check power supply and connections",
                    expected_result="Unit should power on with indicator lights",
                    safety_warning="Ensure power is off before checking connections",
                    tools_required=["Multimeter", "Screwdriver"],
                    estimated_time=10
                )
            ],
            confidence_score=0.92,
            manual_url="https://example.com/manual",
            warranty_info="2 years manufacturer warranty"
        )
    
    def _get_placeholder_error_codes(self) -> List[ErrorCode]:
        """Get placeholder error codes for testing."""
        return [
            ErrorCode(
                code="E01",
                description="Temperature sensor error",
                severity="High",
                troubleshooting_steps=[
                    TroubleshootingStep(
                        step_number=1,
                        instruction="Check sensor connections",
                        expected_result="Connections should be secure and clean",
                        tools_required=["Screwdriver"],
                        estimated_time=5
                    ),
                    TroubleshootingStep(
                        step_number=2,
                        instruction="Replace temperature sensor if faulty",
                        expected_result="Error code should clear after replacement",
                        safety_warning="Disconnect power before replacing sensor",
                        tools_required=["Replacement sensor", "Screwdriver"],
                        estimated_time=15
                    )
                ],
                common_causes=["Loose connection", "Sensor failure", "Wiring damage"],
                parts_needed=["Temperature sensor"]
            )
        ]
    
    async def detect_error_codes(
        self, 
        image_file: UploadFile, 
        user_id: Optional[str] = None
    ) -> List[ErrorCode]:
        """Detect error codes from image"""
        image_data = await self._upload_file_to_image_data(image_file)
        
        if self.vision_engine:
            try:
                error_codes_obj = await self.vision_engine.detect_error_codes(image_data)
                return [ErrorCode(**ec.__dict__) for ec in error_codes_obj]
            except VisionProcessingError:
                pass
        
        # Placeholder implementation
        return self._get_placeholder_error_codes()
    
    async def analyze_pattern(
        self, 
        image_file: UploadFile, 
        user_id: Optional[str] = None
    ) -> VisionAnalysisResponse:
        """Analyze traditional patterns"""
        start_time = time.time()
        image_data = await self._upload_file_to_image_data(image_file)
        
        if self.vision_engine:
            try:
                pattern_obj = await self.vision_engine.analyze_pattern(image_data)
                pattern_analysis = PatternAnalysis(**pattern_obj.__dict__)
            except VisionProcessingError:
                pattern_analysis = self._get_placeholder_pattern()
        else:
            pattern_analysis = self._get_placeholder_pattern()
        
        processing_time = time.time() - start_time
        
        return VisionAnalysisResponse(
            analysis_type="pattern_analysis",
            result=pattern_analysis.model_dump(),
            confidence_score=pattern_analysis.confidence_score,
            processing_time=processing_time,
            suggestions=pattern_analysis.modern_variations
        )
    
    def _get_placeholder_pattern(self) -> PatternAnalysis:
        """Get placeholder pattern analysis for testing."""
        return PatternAnalysis(
            pattern_type="Traditional Paisley",
            elements=["Curved motifs", "Floral patterns", "Geometric borders"],
            colors=["Red", "Gold", "Green", "Blue"],
            style_period="Mughal Era",
            cultural_origin="North India",
            modern_variations=[
                "Modern geometric variation with simplified curves",
                "Minimalist interpretation with single color palette",
                "Contemporary fusion with abstract elements"
            ],
            market_trends={
                "popularity": "High",
                "price_range": "₹2000-5000 per meter",
                "target_market": "Urban millennials, Export market"
            },
            confidence_score=0.88
        )
    
    async def assess_quality(
        self, 
        image_file: UploadFile, 
        product_type: str,
        user_id: Optional[str] = None
    ) -> QualityAssessment:
        """Assess product quality"""
        image_data = await self._upload_file_to_image_data(image_file)
        
        # Map string to ProductType enum
        product_type_map = {
            'saffron': ProductType.SAFFRON,
            'walnut': ProductType.WALNUT,
            'textile': ProductType.TEXTILE,
            'handicraft': ProductType.HANDICRAFT,
            'agricultural': ProductType.AGRICULTURAL,
            'electronic': ProductType.ELECTRONIC
        }
        product_enum = product_type_map.get(product_type.lower(), ProductType.AGRICULTURAL)
        
        if self.vision_engine:
            try:
                quality_obj = await self.vision_engine.assess_quality(image_data, product_enum)
                return QualityAssessment(**quality_obj.__dict__)
            except VisionProcessingError:
                pass
        
        # Placeholder implementation
        return QualityAssessment(
            grade="A",
            score=85.5,
            defects=[],
            price_range="₹500-700 per kg",
            market_standard="Premium quality",
            improvement_suggestions=[
                "Maintain consistent color",
                "Ensure uniform size"
            ],
            confidence_score=0.87
        )
    
    async def extract_text(
        self, 
        image_file: UploadFile, 
        language_code: str,
        user_id: Optional[str] = None
    ) -> str:
        """Extract text using OCR"""
        image_data = await self._upload_file_to_image_data(image_file)
        
        if self.vision_engine:
            try:
                return await self.vision_engine.extract_text(image_data, language_code)
            except VisionProcessingError:
                pass
        
        # Placeholder implementation
        return "Extracted text from image (placeholder)"
    
    async def count_inventory(
        self,
        image_file: UploadFile,
        user_id: Optional[str] = None
    ) -> InventoryCountResponse:
        """Count inventory items from image"""
        start_time = time.time()
        image_data = await self._upload_file_to_image_data(image_file)
        
        if self.vision_engine:
            try:
                items_obj = await self.vision_engine.count_inventory(image_data)
                items = [InventoryItem(**item.__dict__) for item in items_obj]
            except VisionProcessingError:
                items = self._get_placeholder_inventory()
        else:
            items = self._get_placeholder_inventory()
        
        processing_time = time.time() - start_time
        total_items = sum(item.quantity for item in items)
        avg_confidence = sum(item.confidence_score for item in items) / len(items) if items else 0.0
        
        return InventoryCountResponse(
            items=items,
            total_items=total_items,
            processing_time=processing_time,
            confidence_score=avg_confidence
        )
    
    def _get_placeholder_inventory(self) -> List[InventoryItem]:
        """Get placeholder inventory items for testing."""
        return [
            InventoryItem(
                item_id="item_001",
                name="Motor Oil 5W-30",
                brand="Castrol",
                category="Automotive",
                quantity=12,
                location="Shelf A, Row 2",
                confidence_score=0.92
            ),
            InventoryItem(
                item_id="item_002",
                name="Air Filter",
                brand="Bosch",
                category="Automotive",
                quantity=8,
                location="Shelf A, Row 3",
                confidence_score=0.88
            )
        ]