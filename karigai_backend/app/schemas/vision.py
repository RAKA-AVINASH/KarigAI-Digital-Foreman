from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class TroubleshootingStep(BaseModel):
    step_number: int
    instruction: str
    expected_result: str
    safety_warning: Optional[str] = None
    tools_required: List[str] = []
    estimated_time: Optional[int] = None


class ErrorCode(BaseModel):
    code: str
    description: str
    severity: str
    troubleshooting_steps: List[TroubleshootingStep] = []
    common_causes: List[str] = []
    parts_needed: List[str] = []


class EquipmentInfo(BaseModel):
    equipment_id: str
    brand: str
    model: str
    category: str
    common_issues: List[str] = []
    procedures: List[TroubleshootingStep] = []
    confidence_score: float
    manual_url: Optional[str] = None
    warranty_info: Optional[str] = None


class PatternAnalysis(BaseModel):
    pattern_type: str
    elements: List[str] = []
    colors: List[str] = []
    style_period: Optional[str] = None
    cultural_origin: Optional[str] = None
    modern_variations: List[str] = []
    market_trends: Dict[str, Any] = {}
    confidence_score: float


class QualityDefect(BaseModel):
    defect_type: str
    severity: str
    location: Optional[str] = None
    description: str = ""
    impact_on_grade: float = 0.0


class QualityAssessment(BaseModel):
    grade: str
    score: float
    defects: List[QualityDefect] = []
    price_range: str = ""
    market_standard: str = ""
    improvement_suggestions: List[str] = []
    confidence_score: float = 0.0


class InventoryItem(BaseModel):
    item_id: str
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    quantity: int = 0
    location: Optional[str] = None
    confidence_score: float = 0.0


class EquipmentIdentificationResponse(BaseModel):
    equipment_info: EquipmentInfo
    error_codes: List[ErrorCode]
    troubleshooting_available: bool
    processing_time: float


class VisionAnalysisResponse(BaseModel):
    analysis_type: str
    result: Dict[str, Any]
    confidence_score: float
    processing_time: float
    suggestions: List[str] = []


class InventoryCountResponse(BaseModel):
    items: List[InventoryItem]
    total_items: int
    processing_time: float
    confidence_score: float