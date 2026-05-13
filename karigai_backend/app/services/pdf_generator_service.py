"""
PDF Generator Service using ReportLab

This module implements PDF generation for invoices and reports with
bilingual support, automatic warranty clauses, and digital watermarking.
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, 
    Spacer, Image, PageBreak
)
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from app.core.document_generator import (
    DocumentGenerator,
    InvoiceData,
    ReportData,
    PDFDocument,
    InvoiceTemplate
)


class PDFGeneratorService(DocumentGenerator):
    """
    PDF generation service using ReportLab
    
    Implements bilingual invoice and report generation with:
    - Automatic warranty clause inclusion
    - Service detail formatting
    - Tax calculation and compliance
    - Digital watermarking
    """
    
    def __init__(self, output_dir: str = "generated_documents"):
        """
        Initialize PDF generator service
        
        Args:
            output_dir: Directory to save generated PDFs
        """
        self.output_dir = output_dir
        self.templates = ["default", "professional", "simple"]
        self.custom_templates = {}
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    async def generate_invoice(
        self, 
        data: InvoiceData, 
        template: str = "default",
        language: str = "hi-IN"
    ) -> PDFDocument:
        """
        Generate an invoice PDF document
        
        Args:
            data: Invoice data to generate document from
            template: Template identifier to use
            language: Language code (hi-IN for Hindi, en-IN for English)
            
        Returns:
            PDFDocument object with file path and metadata
        """
        # Get translations
        trans = InvoiceTemplate.get_translations(language)
        
        # Create file path
        file_name = f"{data.invoice_id}_{language}.pdf"
        file_path = os.path.join(self.output_dir, file_name)
        
        # Create PDF document
        doc = SimpleDocTemplate(
            file_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Container for PDF elements
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#333333'),
            spaceAfter=12,
            spaceBefore=12
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666')
        )
        
        # Title
        title = Paragraph(trans['invoice'], title_style)
        elements.append(title)
        elements.append(Spacer(1, 12))
        
        # Invoice details
        invoice_info = [
            [trans['invoice_no'], data.invoice_id],
            [trans['date'], InvoiceTemplate.format_date(data.service_date, language)]
        ]
        
        invoice_table = Table(invoice_info, colWidths=[2*inch, 3*inch])
        invoice_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1a1a1a')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(invoice_table)
        elements.append(Spacer(1, 20))
        
        # Customer details
        customer_heading = Paragraph(trans['customer_details'], heading_style)
        elements.append(customer_heading)
        
        customer_info = [[trans['name'], data.customer_name]]
        if data.customer_phone:
            customer_info.append([trans['phone'], data.customer_phone])
        
        customer_table = Table(customer_info, colWidths=[2*inch, 3*inch])
        customer_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1a1a1a')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(customer_table)
        elements.append(Spacer(1, 20))
        
        # Service details
        service_heading = Paragraph(trans['service_details'], heading_style)
        elements.append(service_heading)
        
        # Service table
        service_data = [[
            trans['description'],
            trans['quantity'],
            trans['rate'],
            trans['amount']
        ]]
        
        for item in data.services:
            service_data.append([
                item.description,
                str(item.quantity),
                InvoiceTemplate.format_currency(item.amount),
                InvoiceTemplate.format_currency(item.total)
            ])
        
        service_table = Table(service_data, colWidths=[3*inch, 0.8*inch, 1.2*inch, 1.2*inch])
        service_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1a1a1a')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#666666')),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(service_table)
        elements.append(Spacer(1, 20))
        
        # Financial summary
        summary_data = [
            [trans['subtotal'], InvoiceTemplate.format_currency(data.subtotal)],
            [trans['tax'], InvoiceTemplate.format_currency(data.tax_amount)],
            [trans['total'], InvoiceTemplate.format_currency(data.total_amount)]
        ]
        
        summary_table = Table(summary_data, colWidths=[4*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1a1a1a')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#1a1a1a')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 20))
        
        # Warranty information
        if data.warranty_info:
            warranty_heading = Paragraph(trans['warranty'], heading_style)
            elements.append(warranty_heading)
            
            # Clean warranty text
            warranty_text = data.warranty_info.replace('\r', ' ').replace('\n', ' ').strip()
            warranty_para = Paragraph(warranty_text, normal_style)
            elements.append(warranty_para)
            elements.append(Spacer(1, 12))
        
        # Notes
        if data.notes:
            notes_heading = Paragraph(trans['notes'], heading_style)
            elements.append(notes_heading)
            
            # Clean notes text
            notes_text = data.notes.replace('\r', ' ').replace('\n', ' ').strip()
            notes_para = Paragraph(notes_text, normal_style)
            elements.append(notes_para)
            elements.append(Spacer(1, 12))
        
        # Thank you message
        elements.append(Spacer(1, 20))
        thank_you = Paragraph(trans['thank_you'], ParagraphStyle(
            'ThankYou',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#1a1a1a'),
            alignment=TA_CENTER
        ))
        elements.append(thank_you)
        
        # Build PDF
        doc.build(elements, onFirstPage=self._add_watermark, onLaterPages=self._add_watermark)
        
        # Create metadata
        metadata = {
            "invoice_id": data.invoice_id,
            "language": language,
            "template": template,
            "total_amount": data.total_amount,
            "service_count": len(data.services),
            "has_warranty": data.warranty_info is not None,
            "has_notes": data.notes is not None,
            "generated_at": datetime.now().isoformat()
        }
        
        return PDFDocument(file_path=file_path, metadata=metadata)
    
    async def generate_report(
        self, 
        data: ReportData, 
        template: str = "default",
        language: str = "hi-IN"
    ) -> PDFDocument:
        """
        Generate a report PDF document
        
        Args:
            data: Report data to generate document from
            template: Template identifier to use
            language: Language code
            
        Returns:
            PDFDocument object with file path and metadata
        """
        # Create file path
        file_name = f"{data.report_id}_{language}.pdf"
        file_path = os.path.join(self.output_dir, file_name)
        
        # Create PDF document
        doc = SimpleDocTemplate(
            file_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Container for PDF elements
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        # Title
        title = Paragraph(data.title, title_style)
        elements.append(title)
        elements.append(Spacer(1, 12))
        
        # Report metadata
        meta_info = [
            ["Report ID", data.report_id],
            ["Generated By", data.generated_by],
            ["Generated At", data.generated_at.strftime("%d %B %Y %H:%M")]
        ]
        
        meta_table = Table(meta_info, colWidths=[2*inch, 3*inch])
        meta_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1a1a1a')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 20))
        
        # Report content
        for key, value in data.content.items():
            heading = Paragraph(str(key).replace('_', ' ').title(), styles['Heading2'])
            elements.append(heading)
            
            content_text = str(value)
            content_para = Paragraph(content_text, styles['Normal'])
            elements.append(content_para)
            elements.append(Spacer(1, 12))
        
        # Build PDF
        doc.build(elements, onFirstPage=self._add_watermark, onLaterPages=self._add_watermark)
        
        # Create metadata
        metadata = {
            "report_id": data.report_id,
            "language": language,
            "template": template,
            "report_type": data.report_type,
            "generated_at": datetime.now().isoformat()
        }
        
        return PDFDocument(file_path=file_path, metadata=metadata)
    
    def get_available_templates(self) -> List[str]:
        """Get list of available template identifiers"""
        return self.templates + list(self.custom_templates.keys())
    
    async def add_custom_template(
        self, 
        template_id: str, 
        template_data: Dict[str, Any]
    ) -> bool:
        """
        Add a custom template to the generator
        
        Args:
            template_id: Unique identifier for the template
            template_data: Template configuration and layout data
            
        Returns:
            True if template was added successfully
        """
        self.custom_templates[template_id] = template_data
        return True
    
    def _add_watermark(self, canvas_obj, doc):
        """
        Add digital watermark to PDF pages
        
        Args:
            canvas_obj: ReportLab canvas object
            doc: Document object
        """
        canvas_obj.saveState()
        
        # Add watermark text
        canvas_obj.setFont('Helvetica', 8)
        canvas_obj.setFillColor(colors.HexColor('#cccccc'))
        
        # Bottom center watermark
        watermark_text = f"Generated by KarigAI - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        canvas_obj.drawCentredString(
            A4[0] / 2,
            20,
            watermark_text
        )
        
        canvas_obj.restoreState()
