"""
Tests for Material OCR Service

This module tests the material instruction translation service for product labels.
"""

import pytest
from io import BytesIO
from PIL import Image

from app.services.material_ocr_service import MaterialOCRService
from app.core.vision_engine import ImageData, ImageFormat


def create_test_image(width=800, height=600) -> ImageData:
    """Create a test image."""
    img = Image.new('RGB', (width, height), color='white')
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
def material_service():
    """Fixture providing material OCR service."""
    return MaterialOCRService(api_key=None)


def test_material_service_initialization():
    """Test material OCR service initialization."""
    service = MaterialOCRService()
    
    assert service is not None
    assert service.safety_keywords is not None


def test_safety_keywords_database_structure(material_service):
    """Test safety keywords database has correct structure."""
    keywords = material_service.safety_keywords
    
    assert "english" in keywords
    assert "hindi" in keywords
    assert "symbols" in keywords
    assert isinstance(keywords["english"], list)
    assert len(keywords["english"]) > 0


@pytest.mark.asyncio
async def test_extract_text_basic(material_service):
    """Test basic text extraction from product labels."""
    image = create_test_image()
    
    result = await material_service.extract_text(image, "en")
    
    assert isinstance(result, str)
    assert len(result) > 0


def test_translate_instructions_basic(material_service):
    """Test basic instruction translation."""
    text = """
    Instructions:
    1. Mix with water
    2. Apply evenly
    WARNING: Keep away from children
    """
    
    result = material_service.translate_instructions(text, "en", "hi")
    
    assert "original_text" in result
    assert "translated_steps" in result
    assert "safety_warnings" in result
    assert "language" in result
    assert result["language"] == "hi"
    assert isinstance(result["translated_steps"], list)


def test_extract_safety_warnings_with_warnings(material_service):
    """Test extracting safety warnings when present."""
    text = """
    Product Instructions
    WARNING: Avoid contact with skin
    DANGER: Flammable material
    Keep away from children
    """
    
    warnings = material_service._extract_safety_warnings(text)
    
    assert isinstance(warnings, list)
    assert len(warnings) > 0
    assert any("WARNING" in w.upper() for w in warnings)


def test_extract_safety_warnings_no_warnings(material_service):
    """Test extracting safety warnings when none present."""
    text = "Simple product instructions for normal use"
    
    warnings = material_service._extract_safety_warnings(text)
    
    assert isinstance(warnings, list)
    assert len(warnings) == 0


def test_break_into_steps_numbered(material_service):
    """Test breaking numbered instructions into steps."""
    text = """
    1. First step
    2. Second step
    3. Third step
    """
    
    steps = material_service._break_into_steps(text)
    
    assert isinstance(steps, list)
    assert len(steps) == 3


def test_break_into_steps_bulleted(material_service):
    """Test breaking bulleted instructions into steps."""
    text = """
    - First step
    - Second step
    - Third step
    """
    
    steps = material_service._break_into_steps(text)
    
    assert isinstance(steps, list)
    assert len(steps) == 3


def test_break_into_steps_no_structure(material_service):
    """Test breaking unstructured text into steps."""
    text = "Just some random text without any structure"
    
    steps = material_service._break_into_steps(text)
    
    assert isinstance(steps, list)
    assert len(steps) > 0  # Should return default step


def test_highlight_safety_info_with_warnings(material_service):
    """Test highlighting safety information when warnings present."""
    text = """
    Product Instructions
    WARNING: Avoid contact with skin
    Apply carefully
    """
    
    result = material_service.highlight_safety_info(text)
    
    assert "has_safety_warnings" in result
    assert result["has_safety_warnings"] is True
    assert "warnings" in result
    assert "severity" in result
    assert "highlighted_text" in result
    assert len(result["warnings"]) > 0


def test_highlight_safety_info_no_warnings(material_service):
    """Test highlighting safety information when no warnings."""
    text = "Simple instructions for normal use"
    
    result = material_service.highlight_safety_info(text)
    
    assert result["has_safety_warnings"] is False
    assert len(result["warnings"]) == 0


def test_highlight_safety_info_severity_high(material_service):
    """Test severity assessment for high-risk warnings."""
    text = "DANGER: Toxic material. FLAMMABLE substance."
    
    result = material_service.highlight_safety_info(text)
    
    assert result["severity"] == "HIGH"


def test_highlight_safety_info_severity_medium(material_service):
    """Test severity assessment for medium-risk warnings."""
    text = "CAUTION: Handle with care"
    
    result = material_service.highlight_safety_info(text)
    
    assert result["severity"] == "MEDIUM"


def test_add_highlights(material_service):
    """Test adding visual highlights to warnings."""
    text = "WARNING: Keep away from fire"
    warnings = ["WARNING: Keep away from fire"]
    
    highlighted = material_service._add_highlights(text, warnings)
    
    assert "⚠️" in highlighted
    assert "WARNING" in highlighted


def test_generate_audio_instructions_basic(material_service):
    """Test generating audio instruction metadata."""
    steps = ["Step 1: Mix ingredients", "Step 2: Apply mixture"]
    
    result = material_service.generate_audio_instructions(steps, "hi")
    
    assert "steps" in result
    assert "language" in result
    assert "voice_settings" in result
    assert "audio_format" in result
    assert "estimated_duration" in result
    assert result["language"] == "hi"
    assert result["steps"] == steps


def test_generate_audio_instructions_voice_settings(material_service):
    """Test audio instruction voice settings structure."""
    steps = ["Step 1"]
    
    result = material_service.generate_audio_instructions(steps, "en")
    
    voice_settings = result["voice_settings"]
    assert "speed" in voice_settings
    assert "emphasis" in voice_settings
    assert "pause_between_steps" in voice_settings
    assert voice_settings["speed"] == "slow"


def test_generate_audio_instructions_duration_calculation(material_service):
    """Test audio duration estimation."""
    steps = ["Step 1", "Step 2", "Step 3"]
    
    result = material_service.generate_audio_instructions(steps, "en")
    
    # Should estimate based on number of steps
    assert result["estimated_duration"] == len(steps) * 10


def test_translate_instructions_includes_audio_flag(material_service):
    """Test that translation result includes audio availability flag."""
    text = "1. Mix ingredients"
    
    result = material_service.translate_instructions(text, "en", "hi")
    
    assert "audio_available" in result
    assert result["audio_available"] is True


@pytest.mark.asyncio
async def test_preprocess_image(material_service):
    """Test image preprocessing."""
    image = create_test_image()
    
    result = await material_service.preprocess_image(image)
    
    assert isinstance(result, ImageData)
    assert result.preprocessed is True


def test_safety_keywords_english_coverage(material_service):
    """Test English safety keywords coverage."""
    keywords = material_service.safety_keywords["english"]
    
    # Should include common safety terms
    assert "WARNING" in keywords
    assert "DANGER" in keywords
    assert "CAUTION" in keywords


def test_safety_keywords_hindi_present(material_service):
    """Test Hindi safety keywords are present."""
    keywords = material_service.safety_keywords["hindi"]
    
    assert isinstance(keywords, list)
    assert len(keywords) > 0


def test_safety_keywords_symbols_present(material_service):
    """Test safety symbols are present."""
    symbols = material_service.safety_keywords["symbols"]
    
    assert isinstance(symbols, list)
    assert len(symbols) > 0
    assert "⚠️" in symbols
