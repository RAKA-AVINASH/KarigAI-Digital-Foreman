"""Tests for Plant Disease Service"""

import pytest
from io import BytesIO
from PIL import Image
from app.services.plant_disease_service import PlantDiseaseService
from app.core.vision_engine import ImageData, ImageFormat, ProductType


def create_test_image() -> ImageData:
    img = Image.new('RGB', (800, 600), color='green')
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return ImageData(
        image_bytes=img_bytes.read(),
        width=800, height=600,
        format=ImageFormat.JPEG,
        file_size=1000
    )


def test_service_initialization():
    service = PlantDiseaseService()
    assert service is not None
    assert service.disease_database is not None


def test_disease_database_structure():
    service = PlantDiseaseService()
    db = service.disease_database
    assert "fungal" in db
    assert "bacterial" in db
    assert "viral" in db


def test_get_treatments():
    service = PlantDiseaseService()
    treatments = service._get_treatments("powdery mildew")
    assert isinstance(treatments, list)
    assert len(treatments) > 0


@pytest.mark.asyncio
async def test_assess_quality_without_api():
    service = PlantDiseaseService(api_key=None)
    image = create_test_image()
    result = await service.assess_quality(image, ProductType.AGRICULTURAL)
    assert result is not None
    assert result.grade in ["A", "B", "C", "N/A"]
