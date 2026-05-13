"""
Tests for Inventory Vision Service

This module tests the inventory snapshot management service.
"""

import pytest
from io import BytesIO
from PIL import Image

from app.services.inventory_vision_service import InventoryVisionService
from app.core.vision_engine import (
    ImageData,
    ImageFormat,
    InventoryItem
)


def create_test_image(width=800, height=600) -> ImageData:
    """Create a test image."""
    img = Image.new('RGB', (width, height), color='gray')
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
def inventory_service():
    """Fixture providing inventory vision service."""
    return InventoryVisionService(api_key=None)


def test_inventory_service_initialization():
    """Test inventory service initialization."""
    service = InventoryVisionService()
    
    assert service is not None
    assert service.product_database is not None
    assert "automotive" in service.product_database
    assert "hardware" in service.product_database


def test_product_database_structure(inventory_service):
    """Test product database has correct structure."""
    db = inventory_service.product_database
    
    # Check automotive products
    assert "motor_oil" in db["automotive"]
    assert "brands" in db["automotive"]["motor_oil"]
    assert "reorder_threshold" in db["automotive"]["motor_oil"]
    
    # Check hardware products
    assert "screws" in db["hardware"]
    assert "reorder_threshold" in db["hardware"]["screws"]


def test_get_reorder_threshold_automotive(inventory_service):
    """Test getting reorder threshold for automotive items."""
    threshold = inventory_service._get_reorder_threshold("Motor Oil 5W-30", "automotive")
    
    assert isinstance(threshold, int)
    assert threshold > 0


def test_get_reorder_threshold_unknown(inventory_service):
    """Test getting reorder threshold for unknown items."""
    threshold = inventory_service._get_reorder_threshold("Unknown Item", "unknown")
    
    assert isinstance(threshold, int)
    assert threshold == 5  # Default threshold


def test_create_fallback_inventory(inventory_service):
    """Test fallback inventory creation."""
    items = inventory_service._create_fallback_inventory()
    
    assert isinstance(items, list)
    assert len(items) > 0
    assert isinstance(items[0], InventoryItem)
    assert items[0].confidence_score < 0.5


def test_generate_restocking_list_empty():
    """Test generating restocking list with empty inventory."""
    service = InventoryVisionService()
    current_inventory = []
    
    restocking_list = service.generate_restocking_list(current_inventory)
    
    assert isinstance(restocking_list, list)
    assert len(restocking_list) == 0


def test_generate_restocking_list_below_threshold():
    """Test generating restocking list for items below threshold."""
    service = InventoryVisionService()
    
    current_inventory = [
        InventoryItem(
            item_id="item_001",
            name="Motor Oil",
            brand="Castrol",
            category="automotive",
            quantity=2,  # Below threshold of 5
            confidence_score=0.9
        ),
        InventoryItem(
            item_id="item_002",
            name="Air Filter",
            brand="Bosch",
            category="automotive",
            quantity=10,  # Above threshold
            confidence_score=0.9
        )
    ]
    
    restocking_list = service.generate_restocking_list(current_inventory)
    
    assert isinstance(restocking_list, list)
    assert len(restocking_list) >= 1
    
    # Check first item needs restocking
    first_item = restocking_list[0]
    assert first_item["name"] == "Motor Oil"
    assert first_item["current_quantity"] == 2
    assert first_item["suggested_quantity"] > 0
    assert first_item["priority"] in ["High", "Medium", "Low"]


def test_generate_restocking_list_with_usage_patterns():
    """Test generating restocking list with historical usage."""
    service = InventoryVisionService()
    
    current_inventory = [
        InventoryItem(
            item_id="item_001",
            name="Motor Oil",
            category="automotive",
            quantity=3,
            confidence_score=0.9
        )
    ]
    
    historical_usage = {
        "Motor Oil": 20  # 20 units per month
    }
    
    restocking_list = service.generate_restocking_list(current_inventory, historical_usage)
    
    assert len(restocking_list) >= 1
    first_item = restocking_list[0]
    # Suggested quantity should be based on usage (20 * 2 = 40)
    assert first_item["suggested_quantity"] >= 20


def test_generate_restocking_list_priority_sorting():
    """Test that restocking list is sorted by priority."""
    service = InventoryVisionService()
    
    current_inventory = [
        InventoryItem(
            item_id="item_001",
            name="Item Low Priority",
            category="general",
            quantity=4,  # Just below threshold
            confidence_score=0.9
        ),
        InventoryItem(
            item_id="item_002",
            name="Item High Priority",
            category="general",
            quantity=0,  # Out of stock
            confidence_score=0.9
        ),
        InventoryItem(
            item_id="item_003",
            name="Item Medium Priority",
            category="general",
            quantity=2,  # Below half threshold
            confidence_score=0.9
        )
    ]
    
    restocking_list = service.generate_restocking_list(current_inventory)
    
    # Should be sorted: High, Medium, Low
    assert restocking_list[0]["priority"] == "High"
    assert restocking_list[0]["name"] == "Item High Priority"


def test_categorize_products():
    """Test product categorization."""
    service = InventoryVisionService()
    
    items = [
        InventoryItem(
            item_id="item_001",
            name="Motor Oil",
            category="automotive",
            quantity=10,
            confidence_score=0.9
        ),
        InventoryItem(
            item_id="item_002",
            name="Screws",
            category="hardware",
            quantity=50,
            confidence_score=0.9
        ),
        InventoryItem(
            item_id="item_003",
            name="Air Filter",
            category="automotive",
            quantity=5,
            confidence_score=0.9
        )
    ]
    
    categorized = service.categorize_products(items)
    
    assert isinstance(categorized, dict)
    assert "automotive" in categorized
    assert "hardware" in categorized
    assert len(categorized["automotive"]) == 2
    assert len(categorized["hardware"]) == 1


def test_categorize_products_uncategorized():
    """Test categorization with uncategorized items."""
    service = InventoryVisionService()
    
    items = [
        InventoryItem(
            item_id="item_001",
            name="Unknown Item",
            category=None,
            quantity=5,
            confidence_score=0.5
        )
    ]
    
    categorized = service.categorize_products(items)
    
    assert "uncategorized" in categorized
    assert len(categorized["uncategorized"]) == 1


@pytest.mark.asyncio
async def test_count_inventory_without_api_key(inventory_service):
    """Test inventory counting without API key."""
    image = create_test_image()
    
    # Without API key, should raise error or use fallback
    try:
        result = await inventory_service.count_inventory(image)
        # If it doesn't raise error, check it's a fallback result
        assert isinstance(result, list)
        if len(result) > 0:
            assert result[0].confidence_score < 0.5
    except Exception as e:
        # Expected when no API key is configured
        assert "API key" in str(e) or "not configured" in str(e)


@pytest.mark.asyncio
async def test_preprocess_image(inventory_service):
    """Test image preprocessing."""
    image = create_test_image()
    
    result = await inventory_service.preprocess_image(image)
    
    assert isinstance(result, ImageData)
    assert result.preprocessed is True
    assert result.width == image.width


@pytest.mark.asyncio
async def test_identify_equipment_not_implemented(inventory_service):
    """Test that equipment identification is not implemented."""
    image = create_test_image()
    
    result = await inventory_service.identify_equipment(image)
    
    assert result.equipment_id == "not_implemented"
    assert result.confidence_score == 0.0


@pytest.mark.asyncio
async def test_detect_error_codes_not_implemented(inventory_service):
    """Test that error code detection is not implemented."""
    image = create_test_image()
    
    result = await inventory_service.detect_error_codes(image)
    
    assert isinstance(result, list)
    assert len(result) == 0


def test_inventory_service_with_google_vision_flag():
    """Test service initialization with Google Vision flag."""
    service = InventoryVisionService(use_google_vision=True)
    
    assert service.use_google_vision is True


def test_restocking_list_structure():
    """Test restocking list has correct structure."""
    service = InventoryVisionService()
    
    current_inventory = [
        InventoryItem(
            item_id="item_001",
            name="Test Item",
            brand="Test Brand",
            category="test",
            quantity=1,
            confidence_score=0.9
        )
    ]
    
    restocking_list = service.generate_restocking_list(current_inventory)
    
    assert len(restocking_list) > 0
    item = restocking_list[0]
    
    # Check all required fields
    assert "item_id" in item
    assert "name" in item
    assert "brand" in item
    assert "category" in item
    assert "current_quantity" in item
    assert "reorder_threshold" in item
    assert "suggested_quantity" in item
    assert "priority" in item
