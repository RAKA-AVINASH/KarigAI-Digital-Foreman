"""Tests for Pattern Analysis Service"""

import pytest
from io import BytesIO
from PIL import Image
from app.services.pattern_analysis_service import PatternAnalysisService
from app.core.vision_engine import ImageData, ImageFormat


def create_test_image() -> ImageData:
    img = Image.new('RGB', (800, 600), color='red')
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return ImageData(image_bytes=img_bytes.read(), width=800, height=600, format=ImageFormat.JPEG, file_size=1000)


@pytest.mark.asyncio
async def test_analyze_pattern():
    service = PatternAnalysisService()
    image = create_test_image()
    result = await service.analyze_pattern(image)
    assert result.pattern_type != ""
    assert len(result.elements) > 0
    assert len(result.colors) > 0
    assert len(result.modern_variations) > 0
    assert result.confidence_score > 0
