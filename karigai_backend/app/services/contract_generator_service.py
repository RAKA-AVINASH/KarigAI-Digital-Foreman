"""
Contract Generator Service

This module implements the contract safeguard system for verbal agreements,
converting them into formal Work Order Agreements with digital signatures.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass
import uuid
import json
import hashlib

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, 
    Spacer, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

from app.core.document_generator import PDFDocument


@dataclass
class ContractTerms:
    """Extracted contract terms from verbal agreement"""
    amount: float
    scope_of_work: str
    timeline: str
    party_a_name: str
    party_a_contact: Optional[str]
    party_b_name: str
    party_b_contact: Optional[str]
    payment_terms: Optional[str] = None
    materials_included: Optional[bool] = None
    additional_terms: Optional[List[str]] = None


@dataclass
class DigitalSignature:
    """Digital signature data"""
    signer_name: str
    signer_contact: str
    signature_timestamp: datetime
    signature_hash: str
    location_data: Optional[Dict[str, Any]] = None


class ContractGeneratorService:
    """
    Service for generating formal Work Order Agreements from verbal agreements
    
    Features:
    - Contract term extraction from transcribed conversations
    - Bilingual agreement generation (English/Hindi)
    - Digital signature capability
    - Secure storage with timestamp and location data
    """
    
    def __init__(self, output_dir: str = "contracts"):
        """
        Initialize contract generator service
        
        Args:
            output_dir: Directory to save generated contracts
        """
        self.output_dir = output_dir
        import os
        os.makedirs(output_dir, exist_ok=True)
    
    def extract_contract_terms(
        self,
        transcription: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ContractTerms:
        """
        Extract key contract terms from transcribed verbal agreement
        
        Args:
            transcription: Transcribed conversation text
            context: Additional context (user profiles, etc.)
            
        Returns:
            ContractTerms object with extracted information
        """
        # In a real implementation, this would use NLP/LLM to extract terms
        # For now, we'll use a simple keyword-based extraction
        
        # Extract amount (look for currency patterns)
        amount = self._extract_amount(transcription)
        
        # Extract scope of work
        scope = self._extract_scope(transcription)
        
        # Extract timeline
        timeline = self._extract_timeline(transcription)
        
        # Extract party names from context or transcription
        party_a = context.get("party_a_name", "Party A") if context else "Party A"
        party_b = context.get("party_b_name", "Party B") if context else "Party B"
        
        party_a_contact = context.get("party_a_contact") if context else None
        party_b_contact = context.get("party_b_contact") if context else None
        
        # Extract payment terms
        payment_terms = self._extract_payment_terms(transcription)
        
        # Extract materials information
        materials_included = "material" in transcription.lower()
        
        return ContractTerms(
            amount=amount,
            scope_of_work=scope,
            timeline=timeline,
            party_a_name=party_a,
            party_a_contact=party_a_contact,
            party_b_name=party_b,
            party_b_contact=party_b_contact,
            payment_terms=payment_terms,
            materials_included=materials_included
        )
    
    async def generate_work_order_agreement(
        self,
        terms: ContractTerms,
        language: str = "hi-IN",
        contract_id: Optional[str] = None
    ) -> PDFDocument:
        """
        Generate formal Work Order Agreement PDF
        
        Args:
            terms: Contract terms to include
            language: Language code (hi-IN for Hindi, en-IN for English)
            contract_id: Optional contract ID (generated if not provided)
            
        Returns:
            PDFDocument object with file path and metadata
        """
        if not contract_id:
            contract_id = f"WOA-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        
        # Get translations
        trans = self._get_translations(language)
        
        # Create file path
        file_name = f"{contract_id}_{language}.pdf"
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
            'ContractTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'ContractHeading',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#333333'),
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        )
        
        body_style = ParagraphStyle(
            'ContractBody',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            alignment=TA_JUSTIFY,
            spaceAfter=8
        )
        
        # Title
        title = Paragraph(trans['title'], title_style)
        elements.append(title)
        elements.append(Spacer(1, 20))
        
        # Contract ID and Date
        contract_info = [
            [trans['contract_id'], contract_id],
            [trans['date'], datetime.now().strftime("%d %B %Y")]
        ]
        
        info_table = Table(contract_info, colWidths=[2*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1a1a1a')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 20))
        
        # Parties
        parties_heading = Paragraph(trans['parties'], heading_style)
        elements.append(parties_heading)
        
        party_a_text = f"{trans['party_a']}: {terms.party_a_name}"
        if terms.party_a_contact:
            party_a_text += f" ({terms.party_a_contact})"
        
        party_b_text = f"{trans['party_b']}: {terms.party_b_name}"
        if terms.party_b_contact:
            party_b_text += f" ({terms.party_b_contact})"
        
        elements.append(Paragraph(party_a_text, body_style))
        elements.append(Paragraph(party_b_text, body_style))
        elements.append(Spacer(1, 15))
        
        # Scope of Work
        scope_heading = Paragraph(trans['scope'], heading_style)
        elements.append(scope_heading)
        elements.append(Paragraph(terms.scope_of_work, body_style))
        elements.append(Spacer(1, 15))
        
        # Financial Terms
        financial_heading = Paragraph(trans['financial'], heading_style)
        elements.append(financial_heading)
        
        amount_text = f"{trans['amount']}: ₹{terms.amount:,.2f}"
        elements.append(Paragraph(amount_text, body_style))
        
        if terms.payment_terms:
            payment_text = f"{trans['payment_terms']}: {terms.payment_terms}"
            elements.append(Paragraph(payment_text, body_style))
        
        if terms.materials_included is not None:
            materials_text = f"{trans['materials']}: {trans['yes'] if terms.materials_included else trans['no']}"
            elements.append(Paragraph(materials_text, body_style))
        
        elements.append(Spacer(1, 15))
        
        # Timeline
        timeline_heading = Paragraph(trans['timeline'], heading_style)
        elements.append(timeline_heading)
        elements.append(Paragraph(terms.timeline, body_style))
        elements.append(Spacer(1, 15))
        
        # Additional Terms
        if terms.additional_terms:
            additional_heading = Paragraph(trans['additional_terms'], heading_style)
            elements.append(additional_heading)
            
            for term in terms.additional_terms:
                elements.append(Paragraph(f"• {term}", body_style))
            
            elements.append(Spacer(1, 15))
        
        # Legal Disclaimer
        disclaimer_heading = Paragraph(trans['disclaimer'], heading_style)
        elements.append(disclaimer_heading)
        elements.append(Paragraph(trans['disclaimer_text'], body_style))
        elements.append(Spacer(1, 30))
        
        # Signature Section
        signature_heading = Paragraph(trans['signatures'], heading_style)
        elements.append(signature_heading)
        elements.append(Spacer(1, 20))
        
        signature_data = [
            [trans['party_a_signature'], trans['party_b_signature']],
            ['', ''],
            ['_' * 30, '_' * 30],
            [terms.party_a_name, terms.party_b_name],
            [trans['date'] + ': __________', trans['date'] + ': __________']
        ]
        
        signature_table = Table(signature_data, colWidths=[3*inch, 3*inch])
        signature_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(signature_table)
        
        # Build PDF
        doc.build(elements)
        
        # Create metadata
        metadata = {
            "contract_id": contract_id,
            "language": language,
            "amount": terms.amount,
            "party_a": terms.party_a_name,
            "party_b": terms.party_b_name,
            "generated_at": datetime.now().isoformat()
        }
        
        return PDFDocument(file_path=file_path, metadata=metadata)
    
    def create_digital_signature(
        self,
        signer_name: str,
        signer_contact: str,
        contract_id: str,
        location_data: Optional[Dict[str, Any]] = None
    ) -> DigitalSignature:
        """
        Create a digital signature for a contract
        
        Args:
            signer_name: Name of the signer
            signer_contact: Contact information
            contract_id: Contract being signed
            location_data: Optional GPS/location data
            
        Returns:
            DigitalSignature object
        """
        timestamp = datetime.now()
        
        # Create signature hash
        signature_string = f"{signer_name}:{signer_contact}:{contract_id}:{timestamp.isoformat()}"
        signature_hash = hashlib.sha256(signature_string.encode()).hexdigest()
        
        return DigitalSignature(
            signer_name=signer_name,
            signer_contact=signer_contact,
            signature_timestamp=timestamp,
            signature_hash=signature_hash,
            location_data=location_data
        )
    
    def store_contract_securely(
        self,
        contract_id: str,
        pdf_path: str,
        signatures: List[DigitalSignature],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Store contract with signatures and metadata securely
        
        Args:
            contract_id: Contract identifier
            pdf_path: Path to PDF file
            signatures: List of digital signatures
            metadata: Additional metadata
            
        Returns:
            Storage confirmation with details
        """
        storage_record = {
            "contract_id": contract_id,
            "pdf_path": pdf_path,
            "signatures": [
                {
                    "signer_name": sig.signer_name,
                    "signer_contact": sig.signer_contact,
                    "timestamp": sig.signature_timestamp.isoformat(),
                    "signature_hash": sig.signature_hash,
                    "location": sig.location_data
                }
                for sig in signatures
            ],
            "metadata": metadata,
            "stored_at": datetime.now().isoformat()
        }
        
        # In a real implementation, this would store in a database
        # For now, we'll save as JSON
        storage_file = f"{self.output_dir}/{contract_id}_storage.json"
        with open(storage_file, 'w') as f:
            json.dump(storage_record, f, indent=2)
        
        return storage_record
    
    def _extract_amount(self, text: str) -> float:
        """Extract monetary amount from text"""
        import re
        # Look for patterns like "₹1000", "Rs 1000", "1000 rupees"
        patterns = [
            r'₹\s*(\d+(?:,\d+)*(?:\.\d+)?)',
            r'[Rr]s\.?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
            r'(\d+(?:,\d+)*(?:\.\d+)?)\s*rupees?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                amount_str = match.group(1).replace(',', '')
                return float(amount_str)
        
        return 0.0
    
    def _extract_scope(self, text: str) -> str:
        """Extract scope of work from text"""
        # Simple extraction - in real implementation, use NLP
        keywords = ["work", "repair", "install", "build", "construct", "service"]
        sentences = text.split('.')
        
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in keywords):
                return sentence.strip()
        
        return "Work as discussed and agreed upon"
    
    def _extract_timeline(self, text: str) -> str:
        """Extract timeline from text"""
        import re
        # Look for time patterns
        patterns = [
            r'(\d+)\s*days?',
            r'(\d+)\s*weeks?',
            r'(\d+)\s*months?',
            r'by\s+(\w+\s+\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return "As mutually agreed"
    
    def _extract_payment_terms(self, text: str) -> Optional[str]:
        """Extract payment terms from text"""
        keywords = ["advance", "payment", "installment", "credit"]
        sentences = text.split('.')
        
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in keywords):
                return sentence.strip()
        
        return None
    
    def _get_translations(self, language: str) -> Dict[str, str]:
        """Get translations for contract generation"""
        if language.startswith("hi"):
            return {
                "title": "कार्य आदेश समझौता",
                "contract_id": "अनुबंध संख्या",
                "date": "तारीख",
                "parties": "पक्षकार",
                "party_a": "पक्ष अ (सेवा प्रदाता)",
                "party_b": "पक्ष ब (ग्राहक)",
                "scope": "कार्य का दायरा",
                "financial": "वित्तीय शर्तें",
                "amount": "कुल राशि",
                "payment_terms": "भुगतान की शर्तें",
                "materials": "सामग्री शामिल",
                "yes": "हाँ",
                "no": "नहीं",
                "timeline": "समय सीमा",
                "additional_terms": "अतिरिक्त शर्तें",
                "disclaimer": "कानूनी अस्वीकरण",
                "disclaimer_text": "यह समझौता दोनों पक्षों के बीच मौखिक समझौते का औपचारिक दस्तावेज है। दोनों पक्ष इसमें उल्लिखित शर्तों से सहमत हैं।",
                "signatures": "हस्ताक्षर",
                "party_a_signature": "पक्ष अ का हस्ताक्षर",
                "party_b_signature": "पक्ष ब का हस्ताक्षर"
            }
        else:
            return {
                "title": "WORK ORDER AGREEMENT",
                "contract_id": "Contract No",
                "date": "Date",
                "parties": "Parties to the Agreement",
                "party_a": "Party A (Service Provider)",
                "party_b": "Party B (Client)",
                "scope": "Scope of Work",
                "financial": "Financial Terms",
                "amount": "Total Amount",
                "payment_terms": "Payment Terms",
                "materials": "Materials Included",
                "yes": "Yes",
                "no": "No",
                "timeline": "Timeline",
                "additional_terms": "Additional Terms",
                "disclaimer": "Legal Disclaimer",
                "disclaimer_text": "This agreement formalizes the verbal understanding between both parties. Both parties agree to the terms outlined herein.",
                "signatures": "Signatures",
                "party_a_signature": "Party A Signature",
                "party_b_signature": "Party B Signature"
            }
