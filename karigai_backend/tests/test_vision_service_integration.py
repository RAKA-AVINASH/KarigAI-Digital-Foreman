"""
Integration tests for Vision Service

This module tests the vision service integration with the API endpoints.
"""

import pytest
from fastapi import UploadFile
from io import BytesIO
from PIL import Image
from sqlalchemy.orm import Session

from app.services.vision_service import VisionService
from app.schemas.vision import (
    EquipmentIdentificationResponse,
    VisionAnalysisResponse,
    QualityAssessment,
    InventoryCountResponse
)


def create_test_image() -> BytesIO:
    """Create a test image in memory."""
    img = Image.new('RGB', (800, 600), color='red')
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return img_bytes


def create_upload_file(filename: str = "test.jpg") -> UploadFile:
    """Create a mock UploadFile for testing."""
    img_bytes = create_test_image()
    
    class MockUploadFile:
        def __init__(self, file_bytes, filename, content_type):
            self.file = file_bytes
            self.filename = filename
            self.content_type = content_type
        
        async def read(self):
            return self.file.read()
    
    return MockUploadFile(img_bytes, filename, "image/jpeg")


@pytest.fixture
def mock_db():
    """Mock database session."""
    class MockDB:
        pass
    return MockDB()


@pytest.mark.asyncio
async def test_vision_service_identify_equipment(mock_db):
    """Test equipment identification through vision service."""
    service = VisionService(mock_db)
    upload_file = create_upload_file()
    
    result = await service.identify_equipment(upload_file, user_id="test_user")
    
    assert isinstance(result, EquipmentIdentificationResponse)
    assert result.equipment_info is not None
    assert result.equipment_info.brand == "Samsung"
    assert result.equipment_info.confidence_score > 0.0
    assert len(result.error_codes) > 0
    assert result.troubleshooting_available is True
    assert result.processing_time > 0.0


@pytest.mark.asyncio
async def test_vision_service_detect_error_codes(mock_db):
    """Test error code detection through vision service."""
    service = VisionService(mock_db)
    upload_file = create_upload_file()
    
    result = await service.detect_error_codes(upload_file, user_id="test_user")
    
    assert isinstance(result, list)
    assert len(result) > 0
    assert result[0].code == "E01"
    assert result[0].severity == "High"
    assert len(result[0].troubleshooting_steps) > 0


@pytest.mark.asyncio
async def test_vision_service_analyze_pattern(mock_db):
    """Test pattern analysis through vision service."""
    service = VisionService(mock_db)
    upload_file = create_upload_file()
    
    result = await service.analyze_pattern(upload_file, user_id="test_user")
    
    assert isinstance(result, VisionAnalysisResponse)
    assert result.analysis_type == "pattern_analysis"
    assert result.confidence_score > 0.0
    assert len(result.suggestions) > 0
    assert result.processing_time > 0.0


@pytest.mark.asyncio
async def test_vision_service_assess_quality(mock_db):
    """Test quality assessment through vision service."""
    service = VisionService(mock_db)
    upload_file = create_upload_file()
    
    result = await service.assess_quality(upload_file, "saffron", user_id="test_user")
    
    assert isinstance(result, QualityAssessment)
    assert result.grade == "A"
    assert result.score > 0.0
    assert result.confidence_score > 0.0
    assert result.price_range != ""


@pytest.mark.asyncio
async def test_vision_service_extract_text(mock_db):
    """Test text extraction through vision service."""
    service = VisionService(mock_db)
    upload_file = create_upload_file()
    
    result = await service.extract_text(upload_file, "en", user_id="test_user")
    
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_vision_service_count_inventory(mock_db):
    """Test inventory counting through vision service."""
    service = VisionService(mock_db)
    upload_file = create_upload_file()
    
    result = await service.count_inventory(upload_file, user_id="test_user")
    
    assert isinstance(result, InventoryCountResponse)
    assert len(result.items) > 0
    assert result.total_items > 0
    assert result.confidence_score > 0.0
    assert result.processing_time > 0.0
    
    # Verify item details
    first_item = result.items[0]
    assert first_item.name != ""
    assert first_item.quantity > 0
    assert first_item.confidence_score > 0.0


@pytest.mark.asyncio
async def test_vision_service_with_different_image_formats(mock_db):
    """Test vision service with different image formats."""
    service = VisionService(mock_db)
    
    # Test with PNG
    img = Image.new('RGB', (800, 600), color='blue')
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    class MockUploadFile:
        def __init__(self, file_bytes, filename, content_type):
            self.file = file_bytes
            self.filename = filename
            self.content_type = content_type
        
        async def read(self):
            return self.file.read()
    
    upload_file = MockUploadFile(img_bytes, "test.png", "image/png")
    
    result = await service.identify_equipment(upload_file, user_id="test_user")
    
    assert isinstance(result, EquipmentIdentificationResponse)
    assert result.equipment_info is not None
