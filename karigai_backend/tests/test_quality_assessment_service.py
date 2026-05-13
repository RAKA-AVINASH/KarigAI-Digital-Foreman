"""Tests for Quality Assessment Service"""

import pytest
from io import BytesIO
from PIL import Image
from app.services.quality_assessment_service import QualityAssessmentService
from app.core.vision_engine import ImageData, ImageFormat, ProductType


def create_test_image() -> ImageData:
    img = Image.new('RGB', (800, 600), color='orange')
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return ImageData(image_bytes=img_bytes.read(), width=800, height=600, format=ImageFormat.JPEG, file_size=1000)


def test_service_initialization():
    service = QualityAssessmentService()
    assert service is not None
    assert service.quality_standards is not None


def test_quality_standards_structure():
    service = QualityAssessmentService()
    standards = service.quality_standards
    assert "saffron" in standards
    assert "walnut" in standards
    assert "textile" in standards


@pytest.mark.asyncio
async def test_assess_quality_saffron():
    service = QualityAssessmentService()
    image = create_test_image()
    result = await service.assess_quality(image, ProductType.SAFFRON)
    
    assert result.grade in ["A", "B", "C", "D"]
    assert result.score >= 0
    assert result.confidence_score > 0
    assert "₹" in result.price_range


def test_calculate_grade():
    service = QualityAssessmentService()
    assert service._calculate_grade(95) == "A"
    assert service._calculate_grade(80) == "B"
    assert service._calculate_grade(65) == "C"
    assert service._calculate_grade(50) == "D"


def test_get_market_standard():
    service = QualityAssessmentService()
    assert "Premium" in service._get_market_standard("A")
    assert "Good" in service._get_market_standard("B")
