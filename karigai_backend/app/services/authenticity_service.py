"""
Authenticity Certification Service

This module implements the authenticity certification system for handmade products,
providing Digital Story Cards with QR codes and blockchain-based verification.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass
import uuid
import hashlib
import json
import qrcode
from io import BytesIO
import base64

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, 
    Spacer, Image as RLImage
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from app.core.document_generator import PDFDocument


@dataclass
class ProductionRecord:
    """Record of product production process"""
    product_id: str
    product_name: str
    product_category: str
    craftsman_name: str
    craftsman_contact: str
    location: str
    production_start: datetime
    production_end: datetime
    video_documentation: Optional[str] = None  # Path to video file
    images: Optional[List[str]] = None  # Paths to image files
    materials_used: Optional[List[str]] = None
    techniques: Optional[List[str]] = None
    description: Optional[str] = None


@dataclass
class AuthenticityRecord:
    """Blockchain-style authenticity record"""
    record_id: str
    product_id: str
    timestamp: datetime
    record_hash: str
    previous_hash: Optional[str]
    data: Dict[str, Any]


class AuthenticityService:
    """
    Service for creating authenticity certificates for handmade products
    
    Features:
    - Timestamped video documentation
    - Digital Story Card generation with QR codes
    - Blockchain-based immutable records
    - Buyer verification system
    """
    
    def __init__(self, output_dir: str = "authenticity_certificates"):
        """
        Initialize authenticity service
        
        Args:
            output_dir: Directory to save certificates and records
        """
        self.output_dir = output_dir
        self.blockchain_file = f"{output_dir}/blockchain.json"
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize blockchain if it doesn't exist
        if not os.path.exists(self.blockchain_file):
            self._initialize_blockchain()
    
    def create_production_record(
        self,
        product_name: str,
        product_category: str,
        craftsman_name: str,
        craftsman_contact: str,
        location: str,
        video_path: Optional[str] = None,
        images: Optional[List[str]] = None,
        materials: Optional[List[str]] = None,
        techniques: Optional[List[str]] = None,
        description: Optional[str] = None
    ) -> ProductionRecord:
        """
        Create a production record for a product
        
        Args:
            product_name: Name of the product
            product_category: Category (e.g., "Pashmina", "Saffron", "Handicraft")
            craftsman_name: Name of the craftsman
            craftsman_contact: Contact information
            location: Production location
            video_path: Path to production video
            images: List of image paths
            materials: Materials used
            techniques: Techniques employed
            description: Product description
            
        Returns:
            ProductionRecord object
        """
        product_id = f"PROD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        
        return ProductionRecord(
            product_id=product_id,
            product_name=product_name,
            product_category=product_category,
            craftsman_name=craftsman_name,
            craftsman_contact=craftsman_contact,
            location=location,
            production_start=datetime.now(),
            production_end=datetime.now(),
            video_documentation=video_path,
            images=images or [],
            materials_used=materials or [],
            techniques=techniques or [],
            description=description
        )
    
    async def generate_digital_story_card(
        self,
        production_record: ProductionRecord,
        language: str = "en-IN"
    ) -> PDFDocument:
        """
        Generate Digital Story Card with QR code
        
        Args:
            production_record: Production record to create card for
            language: Language code
            
        Returns:
            PDFDocument object with file path and metadata
        """
        # Create blockchain record first
        auth_record = self._add_to_blockchain(production_record)
        
        # Generate QR code for verification
        verification_url = f"https://karigai.app/verify/{production_record.product_id}"
        qr_image = self._generate_qr_code(verification_url)
        
        # Get translations
        trans = self._get_translations(language)
        
        # Create file path
        file_name = f"story_card_{production_record.product_id}.pdf"
        file_path = f"{self.output_dir}/{file_name}"
        
        # Create PDF document
        doc = SimpleDocTemplate(
            file_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Container for PDF elements
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'StoryCardTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'StoryCardHeading',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#333333'),
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        )
        
        body_style = ParagraphStyle(
            'StoryCardBody',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            spaceAfter=8
        )
        
        # Title
        title = Paragraph(trans['title'], title_style)
        elements.append(title)
        elements.append(Spacer(1, 10))
        
        # Subtitle
        subtitle = Paragraph(trans['subtitle'], ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER,
            spaceAfter=20
        ))
        elements.append(subtitle)
        elements.append(Spacer(1, 20))
        
        # Product Information
        product_heading = Paragraph(trans['product_info'], heading_style)
        elements.append(product_heading)
        
        product_data = [
            [trans['product_name'], production_record.product_name],
            [trans['category'], production_record.product_category],
            [trans['product_id'], production_record.product_id]
        ]
        
        product_table = Table(product_data, colWidths=[2*inch, 3.5*inch])
        product_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1a1a1a')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(product_table)
        elements.append(Spacer(1, 15))
        
        # Craftsman Information
        craftsman_heading = Paragraph(trans['craftsman_info'], heading_style)
        elements.append(craftsman_heading)
        
        craftsman_data = [
            [trans['craftsman_name'], production_record.craftsman_name],
            [trans['location'], production_record.location],
            [trans['contact'], production_record.craftsman_contact]
        ]
        
        craftsman_table = Table(craftsman_data, colWidths=[2*inch, 3.5*inch])
        craftsman_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1a1a1a')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(craftsman_table)
        elements.append(Spacer(1, 15))
        
        # Production Details
        if production_record.description:
            description_heading = Paragraph(trans['description'], heading_style)
            elements.append(description_heading)
            elements.append(Paragraph(production_record.description, body_style))
            elements.append(Spacer(1, 15))
        
        # Materials and Techniques
        if production_record.materials_used:
            materials_heading = Paragraph(trans['materials'], heading_style)
            elements.append(materials_heading)
            materials_text = ", ".join(production_record.materials_used)
            elements.append(Paragraph(materials_text, body_style))
            elements.append(Spacer(1, 15))
        
        if production_record.techniques:
            techniques_heading = Paragraph(trans['techniques'], heading_style)
            elements.append(techniques_heading)
            techniques_text = ", ".join(production_record.techniques)
            elements.append(Paragraph(techniques_text, body_style))
            elements.append(Spacer(1, 15))
        
        # Production Timeline
        timeline_heading = Paragraph(trans['timeline'], heading_style)
        elements.append(timeline_heading)
        
        timeline_data = [
            [trans['started'], production_record.production_start.strftime("%d %B %Y")],
            [trans['completed'], production_record.production_end.strftime("%d %B %Y")]
        ]
        
        timeline_table = Table(timeline_data, colWidths=[2*inch, 3.5*inch])
        timeline_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1a1a1a')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(timeline_table)
        elements.append(Spacer(1, 20))
        
        # QR Code for Verification
        verification_heading = Paragraph(trans['verification'], heading_style)
        elements.append(verification_heading)
        
        verify_text = Paragraph(trans['verify_text'], body_style)
        elements.append(verify_text)
        elements.append(Spacer(1, 10))
        
        # Add QR code image
        qr_img = RLImage(qr_image, width=2*inch, height=2*inch)
        elements.append(qr_img)
        elements.append(Spacer(1, 10))
        
        # Verification URL
        url_text = Paragraph(f"<font size=8>{verification_url}</font>", ParagraphStyle(
            'URL',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER
        ))
        elements.append(url_text)
        elements.append(Spacer(1, 20))
        
        # Authenticity Statement
        authenticity_text = Paragraph(trans['authenticity_statement'], ParagraphStyle(
            'Authenticity',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#1a1a1a'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        elements.append(authenticity_text)
        
        # Build PDF
        doc.build(elements)
        
        # Create metadata
        metadata = {
            "product_id": production_record.product_id,
            "product_name": production_record.product_name,
            "craftsman": production_record.craftsman_name,
            "location": production_record.location,
            "blockchain_hash": auth_record.record_hash,
            "verification_url": verification_url,
            "generated_at": datetime.now().isoformat()
        }
        
        return PDFDocument(file_path=file_path, metadata=metadata)
    
    def verify_product_authenticity(
        self,
        product_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Verify product authenticity using blockchain records
        
        Args:
            product_id: Product ID to verify
            
        Returns:
            Verification result with product history
        """
        # Load blockchain
        blockchain = self._load_blockchain()
        
        # Find all records for this product
        product_records = [
            record for record in blockchain
            if record.get("data", {}).get("product_id") == product_id
        ]
        
        if not product_records:
            return None
        
        # Verify blockchain integrity
        is_valid = self._verify_blockchain_integrity(blockchain)
        
        # Get latest record
        latest_record = product_records[-1]
        
        return {
            "product_id": product_id,
            "is_authentic": is_valid,
            "record_count": len(product_records),
            "latest_record": latest_record,
            "verification_timestamp": datetime.now().isoformat()
        }
    
    def _add_to_blockchain(self, production_record: ProductionRecord) -> AuthenticityRecord:
        """Add production record to blockchain"""
        # Load existing blockchain
        blockchain = self._load_blockchain()
        
        # Get previous hash
        previous_hash = blockchain[-1]["record_hash"] if blockchain else "0"
        
        # Create record data
        record_data = {
            "product_id": production_record.product_id,
            "product_name": production_record.product_name,
            "craftsman": production_record.craftsman_name,
            "location": production_record.location,
            "production_start": production_record.production_start.isoformat(),
            "production_end": production_record.production_end.isoformat()
        }
        
        # Generate record hash
        record_id = str(uuid.uuid4())
        timestamp = datetime.now()
        hash_string = f"{record_id}:{timestamp.isoformat()}:{previous_hash}:{json.dumps(record_data)}"
        record_hash = hashlib.sha256(hash_string.encode()).hexdigest()
        
        # Create authenticity record
        auth_record = AuthenticityRecord(
            record_id=record_id,
            product_id=production_record.product_id,
            timestamp=timestamp,
            record_hash=record_hash,
            previous_hash=previous_hash,
            data=record_data
        )
        
        # Add to blockchain
        blockchain.append({
            "record_id": auth_record.record_id,
            "product_id": auth_record.product_id,
            "timestamp": auth_record.timestamp.isoformat(),
            "record_hash": auth_record.record_hash,
            "previous_hash": auth_record.previous_hash,
            "data": auth_record.data
        })
        
        # Save blockchain
        self._save_blockchain(blockchain)
        
        return auth_record
    
    def _generate_qr_code(self, data: str) -> BytesIO:
        """Generate QR code image"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to BytesIO
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return img_buffer
    
    def _initialize_blockchain(self):
        """Initialize empty blockchain"""
        genesis_block = {
            "record_id": "genesis",
            "product_id": "genesis",
            "timestamp": datetime.now().isoformat(),
            "record_hash": hashlib.sha256(b"genesis_block").hexdigest(),
            "previous_hash": "0",
            "data": {"type": "genesis"}
        }
        
        self._save_blockchain([genesis_block])
    
    def _load_blockchain(self) -> List[Dict[str, Any]]:
        """Load blockchain from file"""
        try:
            with open(self.blockchain_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._initialize_blockchain()
            with open(self.blockchain_file, 'r') as f:
                return json.load(f)
    
    def _save_blockchain(self, blockchain: List[Dict[str, Any]]):
        """Save blockchain to file"""
        with open(self.blockchain_file, 'w') as f:
            json.dump(blockchain, f, indent=2)
    
    def _verify_blockchain_integrity(self, blockchain: List[Dict[str, Any]]) -> bool:
        """Verify blockchain integrity"""
        for i in range(1, len(blockchain)):
            current = blockchain[i]
            previous = blockchain[i-1]
            
            # Verify previous hash matches
            if current["previous_hash"] != previous["record_hash"]:
                return False
        
        return True
    
    def _get_translations(self, language: str) -> Dict[str, str]:
        """Get translations for story card"""
        if language.startswith("hi"):
            return {
                "title": "डिजिटल स्टोरी कार्ड",
                "subtitle": "प्रामाणिकता का प्रमाण पत्र",
                "product_info": "उत्पाद जानकारी",
                "product_name": "उत्पाद का नाम",
                "category": "श्रेणी",
                "product_id": "उत्पाद आईडी",
                "craftsman_info": "कारीगर जानकारी",
                "craftsman_name": "कारीगर का नाम",
                "location": "स्थान",
                "contact": "संपर्क",
                "description": "विवरण",
                "materials": "उपयोग की गई सामग्री",
                "techniques": "तकनीकें",
                "timeline": "उत्पादन समयरेखा",
                "started": "शुरू किया",
                "completed": "पूर्ण किया",
                "verification": "प्रामाणिकता सत्यापन",
                "verify_text": "इस उत्पाद की प्रामाणिकता सत्यापित करने के लिए QR कोड स्कैन करें:",
                "authenticity_statement": "यह प्रमाणित करता है कि यह उत्पाद प्रामाणिक है और ऊपर उल्लिखित कारीगर द्वारा बनाया गया है।"
            }
        else:
            return {
                "title": "DIGITAL STORY CARD",
                "subtitle": "Certificate of Authenticity",
                "product_info": "Product Information",
                "product_name": "Product Name",
                "category": "Category",
                "product_id": "Product ID",
                "craftsman_info": "Craftsman Information",
                "craftsman_name": "Craftsman Name",
                "location": "Location",
                "contact": "Contact",
                "description": "Description",
                "materials": "Materials Used",
                "techniques": "Techniques",
                "timeline": "Production Timeline",
                "started": "Started",
                "completed": "Completed",
                "verification": "Authenticity Verification",
                "verify_text": "Scan the QR code to verify the authenticity of this product:",
                "authenticity_statement": "This certifies that this product is authentic and handmade by the craftsman mentioned above."
            }
