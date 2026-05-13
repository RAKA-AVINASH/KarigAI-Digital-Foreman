"""
Tests for Vision Engine Interface

This module tests the vision engine abstract interface and data models.
"""

import pytest
from app.core.vision_engine import (
    VisionEngine,
    ImageData,
    ImageFormat,
    ProductType,
    EquipmentInfo,
    ErrorCode,
    PatternAnalysis,
    QualityAssessment,
    TroubleshootingStep,
    InventoryItem,
    VisionProcessingSession,
    VisionProcessingError
)


class MockVisionEngine(VisionEngine):
    """Mock implementation of VisionEngine for testing."""
    
    async def identify_equipment(self, image: ImageData) -> EquipmentInfo:
        return EquipmentInfo(
            equipment_id="test_eq_001",
            brand="TestBrand",
            model="TestModel",
            category="TestCategory",
            common_issues=["Issue 1", "Issue 2"],
            procedures=[],
            confidence_score=0.95
        )
    
    async def detect_error_codes(self, image: ImageData) -> list:
        return [
            ErrorCode(
                code="E01",
                description="Test error",
                severity="High",
                troubleshooting_steps=[],
                common_causes=["Cause 1"],
                parts_needed=[]
            )
        ]
    
    async def analyze_pattern(self, image: ImageData) -> PatternAnalysis:
        return PatternAnalysis(
            pattern_type="Test Pattern",
            elements=["Element 1"],
            colors=["Red", "Blue"],
            confidence_score=0.90
        )
    
    async def assess_quality(self, image: ImageData, product_type: ProductType) -> QualityAssessment:
        return QualityAssessment(
            grade="A",
            score=90.0,
            defects=[],
            price_range="₹100-200",
            market_standard="Premium",
            confidence_score=0.88
        )
    
    async def extract_text(self, image: ImageData, language_code: str) -> str:
        return "Test extracted text"
    
    async def count_inventory(self, image: ImageData) -> list:
        return [
            InventoryItem(
                item_id="item_001",
                name="Test Item",
                quantity=5,
                confidence_score=0.92
            )
        ]
    
    async def preprocess_image(self, image: ImageData, **kwargs) -> ImageData:
        # Return a copy with preprocessed flag set
        return ImageData(
            image_bytes=image.image_bytes,
            width=image.width,
            height=image.height,
            format=image.format,
            preprocessed=True
        )


@pytest.fixture
def mock_engine():
    """Fixture providing a mock vision engine."""
    return MockVisionEngine()


@pytest.fixture
def sample_image():
    """Fixture providing sample image data."""
    return ImageData(
        image_bytes=b"fake_image_data",
        width=800,
        height=600,
        format=ImageFormat.JPEG
    )


@pytest.mark.asyncio
async def test_identify_equipment(mock_engine, sample_image):
    """Test equipment identification."""
    result = await mock_engine.identify_equipment(sample_image)
    
    assert isinstance(result, EquipmentInfo)
    assert result.equipment_id == "test_eq_001"
    assert result.brand == "TestBrand"
    assert result.confidence_score == 0.95


@pytest.mark.asyncio
async def test_detect_error_codes(mock_engine, sample_image):
    """Test error code detection."""
    result = await mock_engine.detect_error_codes(sample_image)
    
    assert isinstance(result, list)
    assert len(result) > 0
    assert result[0].code == "E01"
    assert result[0].severity == "High"


@pytest.mark.asyncio
async def test_analyze_pattern(mock_engine, sample_image):
    """Test pattern analysis."""
    result = await mock_engine.analyze_pattern(sample_image)
    
    assert isinstance(result, PatternAnalysis)
    assert result.pattern_type == "Test Pattern"
    assert "Red" in result.colors
    assert result.confidence_score == 0.90


@pytest.mark.asyncio
async def test_assess_quality(mock_engine, sample_image):
    """Test quality assessment."""
    result = await mock_engine.assess_quality(sample_image, ProductType.SAFFRON)
    
    assert isinstance(result, QualityAssessment)
    assert result.grade == "A"
    assert result.score == 90.0
    assert result.confidence_score == 0.88


@pytest.mark.asyncio
async def test_extract_text(mock_engine, sample_image):
    """Test text extraction."""
    result = await mock_engine.extract_text(sample_image, "en")
    
    assert isinstance(result, str)
    assert result == "Test extracted text"


@pytest.mark.asyncio
async def test_count_inventory(mock_engine, sample_image):
    """Test inventory counting."""
    result = await mock_engine.count_inventory(sample_image)
    
    assert isinstance(result, list)
    assert len(result) > 0
    assert result[0].name == "Test Item"
    assert result[0].quantity == 5


@pytest.mark.asyncio
async def test_preprocess_image(mock_engine, sample_image):
    """Test image preprocessing."""
    result = await mock_engine.preprocess_image(sample_image)
    
    assert isinstance(result, ImageData)
    assert result.preprocessed is True
    assert result.width == sample_image.width
    assert result.height == sample_image.height


@pytest.mark.asyncio
async def test_create_session(mock_engine, sample_image):
    """Test session creation."""
    session = await mock_engine.create_session("user_123", sample_image)
    
    assert isinstance(session, VisionProcessingSession)
    assert session.user_id == "user_123"
    assert session.input_image == sample_image
    assert session.session_id is not None


@pytest.mark.asyncio
async def test_process_vision_session_equipment(mock_engine, sample_image):
    """Test complete vision session processing for equipment identification."""
    session = await mock_engine.create_session("user_123", sample_image)
    
    result = await mock_engine.process_vision_session(
        session,
        analysis_type="equipment_identification",
        preprocess=True
    )
    
    assert result.analysis_type == "equipment_identification"
    assert result.processed_image is not None
    assert result.processed_image.preprocessed is True
    assert isinstance(result.results, EquipmentInfo)
    assert result.confidence_score == 0.95
    assert result.processing_time is not None


@pytest.mark.asyncio
async def test_process_vision_session_pattern(mock_engine, sample_image):
    """Test complete vision session processing for pattern analysis."""
    session = await mock_engine.create_session("user_123", sample_image)
    
    result = await mock_engine.process_vision_session(
        session,
        analysis_type="pattern_analysis",
        preprocess=False
    )
    
    assert result.analysis_type == "pattern_analysis"
    assert result.processed_image is None  # No preprocessing
    assert isinstance(result.results, PatternAnalysis)
    assert result.confidence_score == 0.90


@pytest.mark.asyncio
async def test_process_vision_session_quality(mock_engine, sample_image):
    """Test complete vision session processing for quality assessment."""
    session = await mock_engine.create_session("user_123", sample_image)
    
    result = await mock_engine.process_vision_session(
        session,
        analysis_type="quality_assessment",
        preprocess=True,
        product_type=ProductType.TEXTILE
    )
    
    assert result.analysis_type == "quality_assessment"
    assert isinstance(result.results, QualityAssessment)
    assert result.confidence_score == 0.88


def test_image_data_to_base64(sample_image):
    """Test ImageData base64 conversion."""
    base64_str = sample_image.to_base64()
    
    assert isinstance(base64_str, str)
    assert len(base64_str) > 0


def test_image_data_from_base64():
    """Test ImageData creation from base64."""
    import base64
    
    test_bytes = b"test_image_data"
    base64_str = base64.b64encode(test_bytes).decode('utf-8')
    
    image = ImageData.from_base64(base64_str, 100, 100, ImageFormat.PNG)
    
    assert image.width == 100
    assert image.height == 100
    assert image.format == ImageFormat.PNG
    assert image.image_bytes == test_bytes


def test_troubleshooting_step_creation():
    """Test TroubleshootingStep data model."""
    step = TroubleshootingStep(
        step_number=1,
        instruction="Test instruction",
        expected_result="Test result",
        safety_warning="Be careful",
        tools_required=["Screwdriver"],
        estimated_time=10
    )
    
    assert step.step_number == 1
    assert step.instruction == "Test instruction"
    assert "Screwdriver" in step.tools_required
    assert step.estimated_time == 10


def test_error_code_creation():
    """Test ErrorCode data model."""
    error = ErrorCode(
        code="E01",
        description="Test error",
        severity="High",
        troubleshooting_steps=[],
        common_causes=["Cause 1", "Cause 2"],
        parts_needed=["Part A"]
    )
    
    assert error.code == "E01"
    assert error.severity == "High"
    assert len(error.common_causes) == 2
    assert "Part A" in error.parts_needed


def test_vision_processing_error():
    """Test VisionProcessingError exception."""
    error = VisionProcessingError(
        message="Test error message",
        error_code="ERR_001",
        original_error=ValueError("Original error")
    )
    
    assert error.message == "Test error message"
    assert error.error_code == "ERR_001"
    assert isinstance(error.original_error, ValueError)
