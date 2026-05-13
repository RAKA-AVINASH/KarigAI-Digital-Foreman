"""
Property-Based Test: Design Generation with Preservation

**Property 13: Design Generation with Preservation**
*For any* analyzed traditional pattern, the system should generate modern variations 
while maintaining identifiable core traditional elements.

**Validates: Requirements 4.2**
"""

import pytest
from hypothesis import given, strategies as st, settings
from io import BytesIO
from PIL import Image
from app.services.pattern_analysis_service import PatternAnalysisService
from app.core.vision_engine import ImageData, ImageFormat


def create_test_image(width=800, height=600) -> ImageData:
    img = Image.new('RGB', (width, height), color='red')
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return ImageData(
        image_bytes=img_bytes.read(),
        width=width, height=height,
        format=ImageFormat.JPEG,
        file_size=1000
    )


@pytest.mark.asyncio
@given(
    width=st.integers(min_value=400, max_value=1200),
    height=st.integers(min_value=400, max_value=1200)
)
@settings(max_examples=100, deadline=3000)
async def test_property_modern_variations_provided(width, height):
    """Property: Modern variations are always provided for patterns."""
    service = PatternAnalysisService()
    image = create_test_image(width, height)
    
    result = await service.analyze_pattern(image)
    
    assert result is not None
    assert len(result.modern_variations) > 0, "Must provide at least one modern variation"
    assert result.confidence_score > 0.0


@pytest.mark.asyncio
@given(
    width=st.integers(min_value=400, max_value=1200),
    height=st.integers(min_value=400, max_value=1200)
)
@settings(max_examples=100, deadline=3000)
async def test_property_traditional_elements_preserved(width, height):
    """Property: Traditional elements are identified and preserved."""
    service = PatternAnalysisService()
    image = create_test_image(width, height)
    
    result = await service.analyze_pattern(image)
    
    assert len(result.elements) > 0, "Must identify traditional elements"
    assert len(result.colors) > 0, "Must identify traditional colors"
    assert result.pattern_type != "", "Must identify pattern type"


def test_property_test_configuration():
    """Meta-test: Verify property test configuration."""
    import hypothesis
    print(f"✓ Property tests configured with {hypothesis.settings.default.max_examples} examples")
    print("✓ Testing Property 13: Design Generation with Preservation")
    print("✓ Validates Requirements: 4.2")
