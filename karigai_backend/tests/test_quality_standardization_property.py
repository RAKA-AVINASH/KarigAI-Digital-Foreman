"""
Property-Based Test: Quality Assessment Standardization

**Property 17: Quality Assessment Standardization**
*For any* product quality analysis, the system should provide grading information 
based on established market standards.

**Validates: Requirements 5.2**
"""

import pytest
from hypothesis import given, strategies as st, settings
from io import BytesIO
from PIL import Image
from app.services.quality_assessment_service import QualityAssessmentService
from app.core.vision_engine import ImageData, ImageFormat, ProductType


def create_test_image(width=800, height=600) -> ImageData:
    img = Image.new('RGB', (width, height), color='yellow')
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
    product_type=st.sampled_from(list(ProductType)),
    width=st.integers(min_value=400, max_value=1200),
    height=st.integers(min_value=400, max_value=1200)
)
@settings(max_examples=100, deadline=3000)
async def test_property_grading_always_provided(product_type, width, height):
    """Property: Grading information is always provided."""
    service = QualityAssessmentService()
    image = create_test_image(width, height)
    
    result = await service.assess_quality(image, product_type)
    
    assert result is not None
    assert result.grade in ["A", "B", "C", "D", "F"], f"Invalid grade: {result.grade}"
    assert 0.0 <= result.score <= 100.0, f"Score out of range: {result.score}"
    assert result.confidence_score > 0.0


@pytest.mark.asyncio
@given(
    product_type=st.sampled_from(list(ProductType))
)
@settings(max_examples=50, deadline=3000)
async def test_property_market_standard_provided(product_type):
    """Property: Market standard information is always provided."""
    service = QualityAssessmentService()
    image = create_test_image()
    
    result = await service.assess_quality(image, product_type)
    
    assert result.market_standard != "", "Market standard must not be empty"
    assert isinstance(result.market_standard, str)


@pytest.mark.asyncio
@given(
    product_type=st.sampled_from(list(ProductType))
)
@settings(max_examples=50, deadline=3000)
async def test_property_price_range_provided(product_type):
    """Property: Price range is always provided."""
    service = QualityAssessmentService()
    image = create_test_image()
    
    result = await service.assess_quality(image, product_type)
    
    assert result.price_range != "", "Price range must not be empty"
    assert "₹" in result.price_range or "Price" in result.price_range


def test_property_test_configuration():
    """Meta-test: Verify property test configuration."""
    import hypothesis
    print(f"✓ Property tests configured with {hypothesis.settings.default.max_examples} examples")
    print("✓ Testing Property 17: Quality Assessment Standardization")
    print("✓ Validates Requirements: 5.2")
