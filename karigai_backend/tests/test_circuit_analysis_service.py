"""Tests for Circuit Analysis Service"""

import pytest
from io import BytesIO
from PIL import Image
from app.services.circuit_analysis_service import CircuitAnalysisService
from app.core.vision_engine import ImageData, ImageFormat


def create_test_image() -> ImageData:
    img = Image.new('RGB', (800, 600), color='blue')
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return ImageData(image_bytes=img_bytes.read(), width=800, height=600, format=ImageFormat.JPEG, file_size=1000)


@pytest.mark.asyncio
async def test_identify_equipment():
    service = CircuitAnalysisService()
    image = create_test_image()
    result = await service.identify_equipment(image)
    assert result.category == "Electronics"
    assert len(result.procedures) > 0
