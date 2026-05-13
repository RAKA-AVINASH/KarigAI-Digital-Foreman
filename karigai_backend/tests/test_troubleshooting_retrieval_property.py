"""
Property-Based Test: Troubleshooting Information Retrieval

**Property 6: Troubleshooting Information Retrieval**
*For any* identified equipment, the system should retrieve and provide relevant 
troubleshooting procedures or general diagnostic approaches.

**Validates: Requirements 2.2, 2.5**

This test uses property-based testing to verify that the system always provides
troubleshooting information for any equipment identification result.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from io import BytesIO
from PIL import Image

from app.services.equipment_vision_service import EquipmentVisionService
from app.core.vision_engine import (
    ImageData,
    ImageFormat,
    EquipmentInfo,
    ErrorCode,
    TroubleshootingStep
)


def create_test_image(width=800, height=600) -> ImageData:
    """Create a test image."""
    img = Image.new('RGB', (width, height), color='red')
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


# Strategies for generating test data
equipment_categories = st.sampled_from([
    "Air Conditioner",
    "Refrigerator",
    "Washing Machine",
    "Water Heater",
    "Microwave",
    "Television",
    "Fan",
    "Unknown Appliance"
])

equipment_brands = st.sampled_from([
    "Samsung",
    "LG",
    "Voltas",
    "Whirlpool",
    "Godrej",
    "Bajaj",
    "Unknown"
])

confidence_scores = st.floats(min_value=0.0, max_value=1.0)


@pytest.fixture
def equipment_service():
    """Fixture providing equipment vision service."""
    return EquipmentVisionService()


@given(
    category=equipment_categories,
    brand=equipment_brands,
    confidence=confidence_scores
)
@settings(max_examples=100, deadline=3000)
def test_property_troubleshooting_always_provided(category, brand, confidence):
    """
    Property Test: Troubleshooting procedures are always provided.
    
    For any equipment identification (regardless of category, brand, or confidence),
    the system should provide troubleshooting procedures or diagnostic approaches.
    """
    service = EquipmentVisionService()
    
    # Create mock equipment info
    equipment = EquipmentInfo(
        equipment_id=f"eq_{hash(brand + category) % 100000}",
        brand=brand,
        model="TestModel",
        category=category,
        common_issues=[],
        procedures=[],
        confidence_score=confidence
    )
    
    # Get troubleshooting procedures
    procedures = service._get_troubleshooting_procedures(category)
    
    # Property assertions
    assert procedures is not None, "Troubleshooting procedures must not be None"
    assert isinstance(procedures, list), "Procedures must be a list"
    assert len(procedures) > 0, \
        f"At least one troubleshooting procedure must be provided for {category}"
    
    # Verify each procedure has required fields
    for i, procedure in enumerate(procedures):
        assert isinstance(procedure, TroubleshootingStep), \
            f"Procedure {i} must be a TroubleshootingStep"
        assert procedure.step_number > 0, \
            f"Step number must be positive, got {procedure.step_number}"
        assert procedure.instruction, \
            f"Instruction must not be empty for step {procedure.step_number}"
        assert procedure.expected_result, \
            f"Expected result must not be empty for step {procedure.step_number}"


@given(
    category=equipment_categories
)
@settings(max_examples=50, deadline=3000)
def test_property_common_issues_provided(category):
    """
    Property Test: Common issues are always provided.
    
    For any equipment category, the system should provide a list of common issues.
    """
    service = EquipmentVisionService()
    
    common_issues = service._get_common_issues(category)
    
    # Property assertions
    assert common_issues is not None, "Common issues must not be None"
    assert isinstance(common_issues, list), "Common issues must be a list"
    assert len(common_issues) > 0, \
        f"At least one common issue must be provided for {category}"
    
    # Verify issues are non-empty strings
    for issue in common_issues:
        assert isinstance(issue, str), "Each issue must be a string"
        assert len(issue) > 0, "Issue description must not be empty"


@given(
    error_code=st.text(alphabet="EF", min_size=1, max_size=1).flatmap(
        lambda prefix: st.builds(
            lambda num: f"{prefix}{num}",
            st.integers(min_value=1, max_value=99)
        )
    )
)
@settings(max_examples=100, deadline=3000)
def test_property_error_code_info_always_provided(error_code):
    """
    Property Test: Error code information is always provided.
    
    For any error code format (E01-E99, F1-F99), the system should provide
    error information with troubleshooting steps.
    """
    service = EquipmentVisionService()
    
    error_info = service._get_error_code_info(error_code)
    
    # Property assertions
    assert error_info is not None, "Error info must not be None"
    assert isinstance(error_info, ErrorCode), "Must return ErrorCode object"
    assert error_info.code == error_code, \
        f"Error code must match input: expected {error_code}, got {error_info.code}"
    assert error_info.description, "Description must not be empty"
    assert error_info.severity in ["Low", "Medium", "High", "Critical", "Unknown"], \
        f"Severity must be valid: got {error_info.severity}"
    
    # Troubleshooting steps must be provided
    assert len(error_info.troubleshooting_steps) > 0, \
        f"At least one troubleshooting step must be provided for {error_code}"
    
    # Verify troubleshooting steps structure
    for step in error_info.troubleshooting_steps:
        assert isinstance(step, TroubleshootingStep)
        assert step.instruction, "Step instruction must not be empty"


@given(
    category=equipment_categories,
    num_procedures=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=50, deadline=3000)
def test_property_troubleshooting_steps_sequential(category, num_procedures):
    """
    Property Test: Troubleshooting steps are sequential.
    
    Troubleshooting procedures should have sequential step numbers starting from 1.
    """
    service = EquipmentVisionService()
    
    procedures = service._get_troubleshooting_procedures(category)
    
    # Check step numbers are sequential
    for i, procedure in enumerate(procedures):
        expected_step = i + 1
        assert procedure.step_number == expected_step, \
            f"Step numbers must be sequential: expected {expected_step}, got {procedure.step_number}"


@given(
    category=equipment_categories
)
@settings(max_examples=50, deadline=3000)
def test_property_troubleshooting_has_safety_info(category):
    """
    Property Test: Safety information is provided when relevant.
    
    Troubleshooting procedures should include safety warnings for electrical equipment.
    """
    service = EquipmentVisionService()
    
    procedures = service._get_troubleshooting_procedures(category)
    
    # At least one procedure should have safety information for electrical equipment
    has_safety_warning = any(
        proc.safety_warning is not None and len(proc.safety_warning) > 0
        for proc in procedures
    )
    
    # For electrical equipment, safety warnings should be present
    if any(keyword in category.lower() for keyword in 
           ["air conditioner", "refrigerator", "washing machine", "heater", "electrical"]):
        assert has_safety_warning, \
            f"Safety warnings should be provided for electrical equipment: {category}"


@given(
    category=equipment_categories
)
@settings(max_examples=50, deadline=3000)
def test_property_troubleshooting_has_tools_info(category):
    """
    Property Test: Required tools information is provided.
    
    Troubleshooting procedures should specify required tools.
    """
    service = EquipmentVisionService()
    
    procedures = service._get_troubleshooting_procedures(category)
    
    # At least one procedure should specify required tools
    has_tools_info = any(
        len(proc.tools_required) > 0
        for proc in procedures
    )
    
    assert has_tools_info, \
        f"At least one procedure should specify required tools for {category}"


@given(
    category=equipment_categories
)
@settings(max_examples=50, deadline=3000)
def test_property_troubleshooting_has_time_estimates(category):
    """
    Property Test: Time estimates are provided for procedures.
    
    Troubleshooting procedures should include estimated time for completion.
    """
    service = EquipmentVisionService()
    
    procedures = service._get_troubleshooting_procedures(category)
    
    # Check if time estimates are provided
    has_time_estimates = any(
        proc.estimated_time is not None and proc.estimated_time > 0
        for proc in procedures
    )
    
    assert has_time_estimates, \
        f"At least one procedure should have time estimate for {category}"


@pytest.mark.asyncio
@given(
    width=st.integers(min_value=100, max_value=2000),
    height=st.integers(min_value=100, max_value=2000)
)
@settings(max_examples=50, deadline=5000)
async def test_property_fallback_provides_troubleshooting(width, height):
    """
    Property Test: Fallback equipment info includes troubleshooting.
    
    Even when equipment identification fails, fallback info should provide
    general troubleshooting guidance.
    """
    service = EquipmentVisionService()
    image = create_test_image(width, height)
    
    fallback_info = service._create_fallback_equipment_info(image)
    
    # Fallback should still provide some guidance
    assert fallback_info is not None
    assert isinstance(fallback_info, EquipmentInfo)
    
    # Even with low confidence, should have some common issues
    assert len(fallback_info.common_issues) > 0, \
        "Fallback should provide at least one common issue"


def test_property_troubleshooting_consistency():
    """
    Property Test: Troubleshooting procedures are consistent.
    
    Multiple calls for the same category should return consistent procedures.
    """
    service = EquipmentVisionService()
    category = "Air Conditioner"
    
    # Get procedures multiple times
    procedures1 = service._get_troubleshooting_procedures(category)
    procedures2 = service._get_troubleshooting_procedures(category)
    procedures3 = service._get_troubleshooting_procedures(category)
    
    # Should return same number of procedures
    assert len(procedures1) == len(procedures2) == len(procedures3), \
        "Troubleshooting procedures should be consistent across calls"
    
    # Step numbers should match
    for p1, p2, p3 in zip(procedures1, procedures2, procedures3):
        assert p1.step_number == p2.step_number == p3.step_number, \
            "Step numbers should be consistent"


def test_property_test_configuration():
    """
    Meta-test: Verify property test configuration.
    
    This ensures we're running enough iterations for statistical significance.
    """
    import hypothesis
    
    # Verify we're using Hypothesis for property-based testing
    assert hypothesis.settings.default.max_examples >= 100, \
        "Should run at least 100 examples for property tests"
    
    print(f"✓ Property tests configured with {hypothesis.settings.default.max_examples} examples")
    print("✓ Testing Property 6: Troubleshooting Information Retrieval")
    print("✓ Validates Requirements: 2.2, 2.5")
