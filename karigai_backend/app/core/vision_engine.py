"""
Vision Engine Abstract Interface

This module defines the abstract interface for computer vision and image analysis engines,
providing a contract for equipment identification, pattern analysis, quality assessment,
and OCR capabilities.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import base64


class ImageFormat(Enum):
    """Supported image formats."""
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    BMP = "bmp"
    TIFF = "tiff"


class ProductType(Enum):
    """Types of products for quality assessment."""
    SAFFRON = "saffron"
    WALNUT = "walnut"
    TEXTILE = "textile"
    HANDICRAFT = "handicraft"
    AGRICULTURAL = "agricultural"
    ELECTRONIC = "electronic"


@dataclass
class ImageData:
    """
    Represents image data with metadata for vision processing.
    
    Attributes:
        image_bytes: Raw image data as bytes
        width: Image width in pixels
        height: Image height in pixels
        format: Image format (jpeg, png, etc.)
        file_path: Optional path to the image file
        file_size: Size of image file in bytes
        preprocessed: Whether image has been preprocessed
        metadata: Additional image metadata (EXIF, etc.)
    """
    image_bytes: bytes
    width: int
    height: int
    format: ImageFormat
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    preprocessed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_base64(self) -> str:
        """Convert image bytes to base64 string."""
        return base64.b64encode(self.image_bytes).decode('utf-8')
    
    @classmethod
    def from_base64(cls, base64_str: str, width: int, height: int, 
                    format: ImageFormat) -> 'ImageData':
        """Create ImageData from base64 string."""
        image_bytes = base64.b64decode(base64_str)
        return cls(
            image_bytes=image_bytes,
            width=width,
            height=height,
            format=format,
            file_size=len(image_bytes)
        )


@dataclass
class TroubleshootingStep:
    """
    Represents a single troubleshooting step.
    
    Attributes:
        step_number: Sequential step number
        instruction: Instruction text
        expected_result: What should happen after this step
        safety_warning: Optional safety warning
        tools_required: List of tools needed for this step
        estimated_time: Estimated time in minutes
    """
    step_number: int
    instruction: str
    expected_result: str
    safety_warning: Optional[str] = None
    tools_required: List[str] = field(default_factory=list)
    estimated_time: Optional[int] = None


@dataclass
class ErrorCode:
    """
    Represents an equipment error code with troubleshooting information.
    
    Attributes:
        code: Error code identifier
        description: Human-readable error description
        severity: Error severity level (Low, Medium, High, Critical)
        troubleshooting_steps: List of steps to resolve the error
        common_causes: List of common causes for this error
        parts_needed: Parts that might need replacement
    """
    code: str
    description: str
    severity: str
    troubleshooting_steps: List[TroubleshootingStep] = field(default_factory=list)
    common_causes: List[str] = field(default_factory=list)
    parts_needed: List[str] = field(default_factory=list)


@dataclass
class EquipmentInfo:
    """
    Represents identified equipment information.
    
    Attributes:
        equipment_id: Unique identifier for equipment type
        brand: Equipment brand/manufacturer
        model: Equipment model number
        category: Equipment category (AC, refrigerator, etc.)
        common_issues: List of common issues for this equipment
        procedures: Available troubleshooting procedures
        confidence_score: Confidence of identification (0.0 to 1.0)
        manual_url: Optional URL to equipment manual
        warranty_info: Optional warranty information
    """
    equipment_id: str
    brand: str
    model: str
    category: str
    common_issues: List[str] = field(default_factory=list)
    procedures: List[TroubleshootingStep] = field(default_factory=list)
    confidence_score: float = 0.0
    manual_url: Optional[str] = None
    warranty_info: Optional[str] = None


@dataclass
class PatternAnalysis:
    """
    Represents analysis of traditional patterns and designs.
    
    Attributes:
        pattern_type: Type of pattern identified
        elements: Design elements and motifs found
        colors: Color palette extracted from pattern
        style_period: Historical style period if applicable
        cultural_origin: Cultural origin of the pattern
        modern_variations: Suggested modern variations
        market_trends: Current market trends for similar patterns
        confidence_score: Confidence of analysis (0.0 to 1.0)
    """
    pattern_type: str
    elements: List[str] = field(default_factory=list)
    colors: List[str] = field(default_factory=list)
    style_period: Optional[str] = None
    cultural_origin: Optional[str] = None
    modern_variations: List[str] = field(default_factory=list)
    market_trends: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 0.0


@dataclass
class QualityDefect:
    """
    Represents a quality defect found in product assessment.
    
    Attributes:
        defect_type: Type of defect
        severity: Severity level (Minor, Moderate, Major, Critical)
        location: Location of defect in image
        description: Detailed description
        impact_on_grade: How much this affects quality grade
    """
    defect_type: str
    severity: str
    location: Optional[str] = None
    description: str = ""
    impact_on_grade: float = 0.0


@dataclass
class QualityAssessment:
    """
    Represents quality assessment results for products.
    
    Attributes:
        grade: Quality grade (A, B, C, etc.)
        score: Numerical quality score (0-100)
        defects: List of defects found
        price_range: Suggested price range
        market_standard: How it compares to market standards
        improvement_suggestions: Suggestions for quality improvement
        confidence_score: Confidence of assessment (0.0 to 1.0)
    """
    grade: str
    score: float
    defects: List[QualityDefect] = field(default_factory=list)
    price_range: str = ""
    market_standard: str = ""
    improvement_suggestions: List[str] = field(default_factory=list)
    confidence_score: float = 0.0


@dataclass
class InventoryItem:
    """
    Represents an item identified in inventory snapshot.
    
    Attributes:
        item_id: Unique identifier for item type
        name: Item name
        brand: Item brand
        category: Item category
        quantity: Detected quantity
        location: Location in image/shelf
        confidence_score: Confidence of identification
    """
    item_id: str
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    quantity: int = 0
    location: Optional[str] = None
    confidence_score: float = 0.0


@dataclass
class VisionProcessingSession:
    """
    Represents a vision processing session with metadata and results.
    
    Attributes:
        session_id: Unique identifier for the session
        user_id: ID of the user who initiated the session
        input_image: Original image input
        processed_image: Image after preprocessing (if applicable)
        analysis_type: Type of analysis performed
        results: Analysis results
        confidence_score: Overall confidence score
        processing_time: Time taken for processing in seconds
        created_at: Timestamp when session was created
        metadata: Additional session metadata
    """
    session_id: str
    user_id: Optional[str]
    input_image: ImageData
    processed_image: Optional[ImageData] = None
    analysis_type: Optional[str] = None
    results: Optional[Any] = None
    confidence_score: Optional[float] = None
    processing_time: Optional[float] = None
    created_at: datetime = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class VisionEngine(ABC):
    """
    Abstract base class for computer vision and image analysis engines.
    
    This interface defines the contract for implementing vision processing
    capabilities including equipment identification, pattern analysis,
    quality assessment, and OCR.
    """
    
    @abstractmethod
    async def identify_equipment(self, image: ImageData) -> EquipmentInfo:
        """
        Identify equipment from image.
        
        Args:
            image: ImageData object containing equipment photo
            
        Returns:
            EquipmentInfo object with identification results
            
        Raises:
            VisionProcessingError: If equipment identification fails
        """
        pass
    
    @abstractmethod
    async def detect_error_codes(self, image: ImageData) -> List[ErrorCode]:
        """
        Detect and read error codes from equipment displays.
        
        Args:
            image: ImageData object containing error code display
            
        Returns:
            List of ErrorCode objects detected
            
        Raises:
            VisionProcessingError: If error code detection fails
        """
        pass
    
    @abstractmethod
    async def analyze_pattern(self, image: ImageData) -> PatternAnalysis:
        """
        Analyze traditional patterns and designs.
        
        Args:
            image: ImageData object containing pattern/design
            
        Returns:
            PatternAnalysis object with analysis results
            
        Raises:
            VisionProcessingError: If pattern analysis fails
        """
        pass
    
    @abstractmethod
    async def assess_quality(self, image: ImageData, product_type: ProductType) -> QualityAssessment:
        """
        Assess product quality from image.
        
        Args:
            image: ImageData object containing product photo
            product_type: Type of product being assessed
            
        Returns:
            QualityAssessment object with grading results
            
        Raises:
            VisionProcessingError: If quality assessment fails
        """
        pass
    
    @abstractmethod
    async def extract_text(self, image: ImageData, language_code: str) -> str:
        """
        Extract text from image using OCR.
        
        Args:
            image: ImageData object containing text
            language_code: Language code for OCR (e.g., 'hi', 'en')
            
        Returns:
            Extracted text string
            
        Raises:
            VisionProcessingError: If text extraction fails
        """
        pass
    
    @abstractmethod
    async def count_inventory(self, image: ImageData) -> List[InventoryItem]:
        """
        Count and identify items in inventory snapshot.
        
        Args:
            image: ImageData object containing inventory/shelf photo
            
        Returns:
            List of InventoryItem objects with counts
            
        Raises:
            VisionProcessingError: If inventory counting fails
        """
        pass
    
    @abstractmethod
    async def preprocess_image(self, image: ImageData,
                              enhance_contrast: bool = True,
                              denoise: bool = True,
                              resize: Optional[tuple] = None) -> ImageData:
        """
        Preprocess image for better analysis quality.
        
        Args:
            image: Input ImageData object
            enhance_contrast: Whether to enhance image contrast
            denoise: Whether to apply denoising
            resize: Optional target size (width, height)
            
        Returns:
            Preprocessed ImageData object
            
        Raises:
            VisionProcessingError: If preprocessing fails
        """
        pass
    
    async def create_session(self, user_id: Optional[str],
                           image: ImageData) -> VisionProcessingSession:
        """
        Create a new vision processing session.
        
        Args:
            user_id: Optional user identifier
            image: Input image data
            
        Returns:
            VisionProcessingSession object
        """
        import uuid
        
        session_id = str(uuid.uuid4())
        return VisionProcessingSession(
            session_id=session_id,
            user_id=user_id,
            input_image=image
        )
    
    async def process_vision_session(self, session: VisionProcessingSession,
                                    analysis_type: str,
                                    preprocess: bool = True,
                                    **kwargs) -> VisionProcessingSession:
        """
        Process a complete vision session with preprocessing and analysis.
        
        Args:
            session: VisionProcessingSession to process
            analysis_type: Type of analysis to perform
            preprocess: Whether to preprocess image
            **kwargs: Additional arguments for specific analysis types
            
        Returns:
            Updated VisionProcessingSession with results
        """
        import time
        
        start_time = time.time()
        session.analysis_type = analysis_type
        
        try:
            # Preprocess image if requested
            if preprocess:
                session.processed_image = await self.preprocess_image(session.input_image)
                image_to_process = session.processed_image
            else:
                image_to_process = session.input_image
            
            # Perform analysis based on type
            if analysis_type == "equipment_identification":
                session.results = await self.identify_equipment(image_to_process)
                session.confidence_score = session.results.confidence_score
                
            elif analysis_type == "error_code_detection":
                session.results = await self.detect_error_codes(image_to_process)
                session.confidence_score = 0.9 if session.results else 0.0
                
            elif analysis_type == "pattern_analysis":
                session.results = await self.analyze_pattern(image_to_process)
                session.confidence_score = session.results.confidence_score
                
            elif analysis_type == "quality_assessment":
                product_type = kwargs.get('product_type', ProductType.AGRICULTURAL)
                session.results = await self.assess_quality(image_to_process, product_type)
                session.confidence_score = session.results.confidence_score
                
            elif analysis_type == "text_extraction":
                language_code = kwargs.get('language_code', 'en')
                session.results = await self.extract_text(image_to_process, language_code)
                session.confidence_score = 0.85  # Default for OCR
                
            elif analysis_type == "inventory_counting":
                session.results = await self.count_inventory(image_to_process)
                session.confidence_score = 0.8 if session.results else 0.0
                
            else:
                raise VisionProcessingError(f"Unknown analysis type: {analysis_type}")
            
        except Exception as e:
            session.metadata['error'] = str(e)
            raise
        finally:
            session.processing_time = time.time() - start_time
        
        return session


class VisionProcessingError(Exception):
    """Exception raised for vision processing errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None,
                 original_error: Optional[Exception] = None):
        self.message = message
        self.error_code = error_code
        self.original_error = original_error
        super().__init__(self.message)
