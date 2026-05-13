"""Tests for Trend Analysis Service"""

import pytest
from io import BytesIO
from PIL import Image
from app.services.trend_analysis_service import TrendAnalysisService
from app.core.vision_engine import ImageData, ImageFormat, PatternAnalysis


def create_test_image() -> ImageData:
    img = Image.new('RGB', (800, 600), color='purple')
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return ImageData(image_bytes=img_bytes.read(), width=800, height=600, format=ImageFormat.JPEG, file_size=1000)


def test_service_initialization():
    service = TrendAnalysisService()
    assert service is not None
    assert service.market_trends is not None


def test_market_trends_structure():
    service = TrendAnalysisService()
    trends = service.market_trends
    assert "color_palettes" in trends
    assert "style_trends" in trends
    assert "target_markets" in trends


@pytest.mark.asyncio
async def test_analyze_pattern():
    service = TrendAnalysisService()
    image = create_test_image()
    result = await service.analyze_pattern(image)
    
    assert isinstance(result, PatternAnalysis)
    assert len(result.modern_variations) > 0
    assert "pricing" in result.market_trends
    assert result.confidence_score > 0


def test_generate_modern_variations():
    service = TrendAnalysisService()
    base_pattern = PatternAnalysis(
        pattern_type="Traditional",
        elements=["Motif"],
        colors=["Red"],
        confidence_score=0.8
    )
    
    variations = service._generate_modern_variations(base_pattern)
    assert isinstance(variations, list)
    assert len(variations) > 0


def test_calculate_pricing_recommendations():
    service = TrendAnalysisService()
    base_pattern = PatternAnalysis(pattern_type="Test", elements=[], colors=[], confidence_score=0.8)
    market_trends = {"popularity_score": 80}
    
    pricing = service._calculate_pricing_recommendations(base_pattern, market_trends)
    assert "base_price" in pricing
    assert "recommended_price" in pricing
    assert "₹" in pricing["base_price"]


def test_generate_visual_mockups_metadata():
    service = TrendAnalysisService()
    pattern = PatternAnalysis(
        pattern_type="Traditional",
        elements=["Element1", "Element2"],
        colors=["Red", "Gold"],
        confidence_score=0.8
    )
    
    metadata = service.generate_visual_mockups_metadata(pattern)
    assert "original_elements" in metadata
    assert "suggested_colors" in metadata
    assert "style_guidelines" in metadata
    assert len(metadata["mockup_variations"]) > 0


def test_create_marketing_materials_suggestions():
    service = TrendAnalysisService()
    pattern = PatternAnalysis(pattern_type="Test", elements=[], colors=[], confidence_score=0.8)
    
    suggestions = service.create_marketing_materials_suggestions(pattern)
    assert isinstance(suggestions, list)
    assert len(suggestions) > 0
    assert "platform" in suggestions[0]
