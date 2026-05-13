"""
Tests for Equipment Vision Service

This module tests the equipment identification and error code detection service.
"""

import pytest
from io import BytesIO
from PIL import Image

from app.services.equipment_vision_service import EquipmentVisionService
from app.core.vision_engine import (
    ImageData,
    ImageFormat,
    EquipmentInfo,
    ErrorCode,
    VisionProcessingError
)


def create_test_image(width=800, height=600) -> ImageData:
    """Create a test image."""
    img = Image.new('RGB', (width, height), color='blue')
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    image_data = img_bytes.read()
    
    return ImageData(
        image_bytes=image_data,
        width=width,
        height=height,
        format=ImageFormat.JPEG,
        file_size=len(image_data)
    )


@pytest.fixture
def equipment_service():
    """Fixture providing equipment vision service without API key."""
    return EquipmentVisionService(api_key=None)


def test_equipment_service_initialization():
    """Test equipment service initialization."""
    service = EquipmentVisionService()
    
    assert service is not None
    assert service.equipment_database is not None
    assert "air_conditioners" in service.equipment_database
    assert "refrigerators" in service.equipment_database


def test_equipment_database_structure(equipment_service):
    """Test equipment database has correct structure."""
    db = equipment_service.equipment_database
    
    # Check air conditioners
    assert "brands" in db["air_conditioners"]
    assert "common_issues" in db["air_conditioners"]
    assert len(db["air_conditioners"]["brands"]) > 0
    assert len(db["air_conditioners"]["common_issues"]) > 0
    
    # Verify Indian brands are included
    ac_brands = db["air_conditioners"]["brands"]
    assert "Voltas" in ac_brands or "Blue Star" in ac_brands


def test_get_common_issues(equipment_service):
    """Test getting common issues for equipment category."""
    issues = equipment_service._get_common_issues("Air Conditioner")
    
    assert isinstance(issues, list)
    assert len(issues) > 0
    assert any("cooling" in issue.lower() for issue in issues)


def test_get_troubleshooting_procedures(equipment_service):
    """Test getting troubleshooting procedures."""
    procedures = equipment_service._get_troubleshooting_procedures("Air Conditioner")
    
    assert isinstance(procedures, list)
    assert len(procedures) > 0
    
    # Check first procedure structure
    first_step = procedures[0]
    assert first_step.step_number == 1
    assert first_step.instruction != ""
    assert first_step.expected_result != ""


def test_get_error_code_info(equipment_service):
    """Test getting error code information."""
    error_info = equipment_service._get_error_code_info("E01")
    
    assert isinstance(error_info, ErrorCode)
    assert error_info.code == "E01"
    assert error_info.description != ""
    assert error_info.severity in ["Low", "Medium", "High", "Critical", "Unknown"]
    assert len(error_info.troubleshooting_steps) > 0


def test_get_error_code_info_unknown(equipment_service):
    """Test getting info for unknown error code."""
    error_info = equipment_service._get_error_code_info("E99")
    
    assert isinstance(error_info, ErrorCode)
    assert error_info.code == "E99"
    assert "E99" in error_info.description


@pytest.mark.asyncio
async def test_create_fallback_equipment_info(equipment_service):
    """Test fallback equipment info creation."""
    image = create_test_image()
    
    result = equipment_service._create_fallback_equipment_info(image)
    
    assert isinstance(result, EquipmentInfo)
    assert result.equipment_id == "eq_unknown"
    assert result.brand == "Unknown"
    assert result.confidence_score < 0.5


@pytest.mark.asyncio
async def test_preprocess_image(equipment_service):
    """Test image preprocessing."""
    image = create_test_image()
    
    result = await equipment_service.preprocess_image(image)
    
    assert isinstance(result, ImageData)
    assert result.preprocessed is True
    assert result.width == image.width
    assert result.height == image.height


@pytest.mark.asyncio
async def test_identify_equipment_without_api_key(equipment_service):
    """Test equipment identification without API key (should use fallback)."""
    image = create_test_image()
    
    # Without API key, should raise error or use fallback
    try:
        result = await equipment_service.identify_equipment(image)
        # If it doesn't raise error, check it's a fallback result
        assert result.confidence_score < 0.5 or result.brand == "Unknown"
    except VisionProcessingError as e:
        # Expected when no API key is configured
        assert "API key" in str(e) or "failed" in str(e).lower()


@pytest.mark.asyncio
async def test_detect_error_codes_with_text(equipment_service):
    """Test error code detection with mock text extraction."""
    image = create_test_image()
    
    # This will try to extract text and parse error codes
    # Without API, it should handle gracefully
    try:
        result = await equipment_service.detect_error_codes(image)
        assert isinstance(result, list)
    except VisionProcessingError:
        # Expected without API key
        pass


@pytest.mark.asyncio
async def test_extract_text_without_api_key(equipment_service):
    """Test text extraction without API key."""
    image = create_test_image()
    
    result = await equipment_service.extract_text(image, "en")
    
    # Should return error message or empty string
    assert isinstance(result, str)
    assert "not available" in result.lower() or "not configured" in result.lower() or result == ""


@pytest.mark.asyncio
async def test_analyze_pattern_not_implemented(equipment_service):
    """Test pattern analysis (not yet implemented)."""
    image = create_test_image()
    
    result = await equipment_service.analyze_pattern(image)
    
    assert result.pattern_type == "Not implemented"
    assert result.confidence_score == 0.0


@pytest.mark.asyncio
async def test_assess_quality_not_implemented(equipment_service):
    """Test quality assessment (not yet implemented)."""
    from app.core.vision_engine import ProductType
    
    image = create_test_image()
    
    result = await equipment_service.assess_quality(image, ProductType.SAFFRON)
    
    assert result.grade == "N/A"
    assert result.score == 0.0


@pytest.mark.asyncio
async def test_count_inventory_not_implemented(equipment_service):
    """Test inventory counting (not yet implemented)."""
    image = create_test_image()
    
    result = await equipment_service.count_inventory(image)
    
    assert isinstance(result, list)
    assert len(result) == 0


def test_equipment_service_with_google_vision_flag():
    """Test service initialization with Google Vision flag."""
    service = EquipmentVisionService(use_google_vision=True)
    
    assert service.use_google_vision is True


@pytest.mark.asyncio
async def test_vision_processing_session(equipment_service):
    """Test complete vision processing session."""
    image = create_test_image()
    
    session = await equipment_service.create_session("test_user", image)
    
    assert session.session_id is not None
    assert session.user_id == "test_user"
    assert session.input_image == image
    
    # Process session for equipment identification
    try:
        result = await equipment_service.process_vision_session(
            session,
            analysis_type="equipment_identification",
            preprocess=True
        )
        
        assert result.analysis_type == "equipment_identification"
        assert result.processing_time is not None
    except VisionProcessingError:
        # Expected without API key
        pass


def test_error_code_pattern_matching():
    """Test error code pattern matching logic."""
    import re
    
    test_texts = [
        "Error E01 detected",
        "Code: F1",
        "E02 and E03 errors",
        "No errors here"
    ]
    
    error_pattern = r'[EF]\d{1,3}'
    
    matches1 = re.findall(error_pattern, test_texts[0].upper())
    assert "E01" in matches1
    
    matches2 = re.findall(error_pattern, test_texts[1].upper())
    assert "F1" in matches2
    
    matches3 = re.findall(error_pattern, test_texts[2].upper())
    assert len(matches3) == 2
    
    matches4 = re.findall(error_pattern, test_texts[3].upper())
    assert len(matches4) == 0
