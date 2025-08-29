from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics import renderPDF
from datetime import datetime
from typing import Optional
import os
from io import BytesIO
import tempfile

from ..models.invoice import Invoice
from ..schemas.invoice import CompanyInfo


class InvoicePDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Setup custom styles for the invoice"""
        # Company name style
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=5,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        ))
        
        # Company info style
        self.styles.add(ParagraphStyle(
            name='CompanyInfo',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#7f8c8d'),
            spaceAfter=3,
            alignment=TA_LEFT
        ))
        
        # Invoice title style
        self.styles.add(ParagraphStyle(
            name='InvoiceTitle',
            parent=self.styles['Heading1'],
            fontSize=28,
            textColor=colors.HexColor('#e74c3c'),
            spaceAfter=10,
            alignment=TA_RIGHT,
            fontName='Helvetica-Bold'
        ))
        
        # Invoice details style
        self.styles.add(ParagraphStyle(
            name='InvoiceDetails',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=3,
            alignment=TA_RIGHT,
            fontName='Helvetica-Bold'
        ))
        
        # Client info style
        self.styles.add(ParagraphStyle(
            name='ClientInfo',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=3,
            alignment=TA_LEFT
        ))
        
        # Table header style
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.white,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Total amount style
        self.styles.add(ParagraphStyle(
            name='TotalAmount',
            parent=self.styles['Normal'],
            fontSize=16,
            textColor=colors.HexColor('#27ae60'),
            alignment=TA_RIGHT,
            fontName='Helvetica-Bold'
        ))

    def generate_invoice_pdf(self, invoice: Invoice, company_info: CompanyInfo, output_path: str) -> str:
        """Generate a professional invoice PDF"""
        
        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Build the PDF content
        story = []
        
        # Header section
        story.extend(self._create_header(company_info, invoice))
        story.append(Spacer(1, 0.5*inch))
        
        # Client information
        story.extend(self._create_client_info(invoice))
        story.append(Spacer(1, 0.3*inch))
        
        # Invoice items table
        story.extend(self._create_items_table(invoice))
        story.append(Spacer(1, 0.3*inch))
        
        # Payment information and totals
        story.extend(self._create_payment_section(invoice))
        story.append(Spacer(1, 0.3*inch))
        
        # Footer
        story.extend(self._create_footer(invoice, company_info))
        
        # Build PDF
        doc.build(story)
        return output_path

    def _create_header(self, company_info: CompanyInfo, invoice: Invoice) -> list:
        """Create the header section with company info and invoice details"""
        elements = []
        
        # Create a table for header layout
        header_data = []
        
        # Left side - Company info
        company_col = [
            Paragraph(company_info.name, self.styles['CompanyName']),
            Paragraph(f"<b>Dirección:</b> {company_info.address}", self.styles['CompanyInfo']),
            Paragraph(f"<b>Teléfono:</b> {company_info.phone}", self.styles['CompanyInfo']),
            Paragraph(f"<b>Email:</b> {company_info.email}", self.styles['CompanyInfo']),
            Paragraph(f"<b>NIT:</b> {company_info.nit}", self.styles['CompanyInfo'])
        ]
        
        # Right side - Invoice details
        invoice_col = [
            Paragraph("FACTURA", self.styles['InvoiceTitle']),
            Paragraph(f"<b>No. Factura:</b> {invoice.invoice_number}", self.styles['InvoiceDetails']),
            Paragraph(f"<b>No. Pedido:</b> {invoice.order.order_number}", self.styles['InvoiceDetails']),
            Paragraph(f"<b>Fecha Emisión:</b> {invoice.issue_date.strftime('%d/%m/%Y')}", self.styles['InvoiceDetails']),
            Paragraph(f"<b>Fecha Vencimiento:</b> {invoice.due_date.strftime('%d/%m/%Y') if invoice.due_date else 'N/A'}", self.styles['InvoiceDetails'])
        ]
        
        header_data.append([company_col, invoice_col])
        
        header_table = Table(header_data, colWidths=[8*cm, 8*cm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        
        elements.append(header_table)
        
        # Add a decorative line
        elements.append(Spacer(1, 0.2*inch))
        line_table = Table([['', '']], colWidths=[16*cm])
        line_table.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, -1), 2, colors.HexColor('#e74c3c')),
        ]))
        elements.append(line_table)
        
        return elements

    def _create_client_info(self, invoice: Invoice) -> list:
        """Create client information section"""
        elements = []
        
        client = invoice.order.client
        
        # Client info header
        elements.append(Paragraph("<b>FACTURAR A:</b>", self.styles['Heading3']))
        
        # Client details
        client_info = [
            f"<b>Cliente:</b> {client.name}",
            f"<b>Email:</b> {client.email or 'N/A'}",
            f"<b>Teléfono:</b> {client.phone or 'N/A'}",
            f"<b>NIT:</b> {client.nit or 'C/F'}",
            f"<b>Dirección:</b> {client.address or 'N/A'}"
        ]
        
        for info in client_info:
            elements.append(Paragraph(info, self.styles['ClientInfo']))
        
        return elements

    def _create_items_table(self, invoice: Invoice) -> list:
        """Create the items table"""
        elements = []
        
        # Table headers
        headers = ['Producto', 'SKU', 'Cantidad', 'Precio Unit.', 'Total']
        
        # Table data
        data = [headers]
        
        for item in invoice.order.items:
            row = [
                Paragraph(f"<b>{item.product.name}</b><br/>{item.product.description or ''}", self.styles['Normal']),
                item.product.sku or 'N/A',
                f"{item.quantity:,}",
                f"Q {item.unit_price:,.2f}",
                f"Q {item.total_price:,.2f}"
            ]
            data.append(row)
        
        # Create table
        table = Table(data, colWidths=[6*cm, 2.5*cm, 2*cm, 2.5*cm, 3*cm])
        
        # Style the table
        table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            
            # Data styling
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            
            # Borders
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        
        elements.append(table)
        return elements

    def _create_payment_section(self, invoice: Invoice) -> list:
        """Create payment and totals section"""
        elements = []
        
        # Create totals table
        totals_data = [
            ['Subtotal:', f"Q {invoice.subtotal:,.2f}"],
            ['Descuento:', f"Q {invoice.discount_amount:,.2f}"],
            ['IVA ({:.0%}):'.format(invoice.tax_rate), f"Q {invoice.tax_amount:,.2f}"],
            ['', ''],  # Separator row
            ['TOTAL:', f"Q {invoice.total_amount:,.2f}"]
        ]
        
        totals_table = Table(totals_data, colWidths=[10*cm, 4*cm])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 3), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, 3), 11),
            ('FONTNAME', (0, 4), (-1, 4), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 4), (-1, 4), 14),
            ('TEXTCOLOR', (0, 4), (-1, 4), colors.HexColor('#27ae60')),
            ('LINEABOVE', (0, 4), (-1, 4), 2, colors.HexColor('#27ae60')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(totals_table)
        
        # Payment status
        elements.append(Spacer(1, 0.2*inch))
        
        status_color = {
            'paid': colors.HexColor('#27ae60'),
            'issued': colors.HexColor('#f39c12'),
            'overdue': colors.HexColor('#e74c3c'),
            'draft': colors.HexColor('#95a5a6')
        }.get(invoice.status.value, colors.black)
        
        status_style = ParagraphStyle(
            name='PaymentStatus',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=status_color,
            alignment=TA_RIGHT,
            fontName='Helvetica-Bold'
        )
        
        status_text = {
            'paid': 'PAGADO',
            'issued': 'PENDIENTE DE PAGO',
            'overdue': 'VENCIDO',
            'draft': 'BORRADOR'
        }.get(invoice.status.value, invoice.status.value.upper())
        
        elements.append(Paragraph(f"Estado: {status_text}", status_style))
        
        if invoice.paid_amount > 0:
            elements.append(Paragraph(f"Pagado: Q {invoice.paid_amount:,.2f}", status_style))
            elements.append(Paragraph(f"Saldo Pendiente: Q {invoice.balance_due:,.2f}", status_style))
        
        return elements

    def _create_footer(self, invoice: Invoice, company_info: CompanyInfo) -> list:
        """Create footer section"""
        elements = []
        
        elements.append(Spacer(1, 0.5*inch))
        
        # Payment terms
        if invoice.payment_terms:
            elements.append(Paragraph(f"<b>Términos de Pago:</b> {invoice.payment_terms}", self.styles['Normal']))
        
        # Notes
        if invoice.notes:
            elements.append(Spacer(1, 0.1*inch))
            elements.append(Paragraph(f"<b>Notas:</b> {invoice.notes}", self.styles['Normal']))
        
        # Footer line
        elements.append(Spacer(1, 0.3*inch))
        footer_line = Table([['', '']], colWidths=[16*cm])
        footer_line.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
        ]))
        elements.append(footer_line)
        
        # Thank you message
        elements.append(Spacer(1, 0.1*inch))
        thank_you_style = ParagraphStyle(
            name='ThankYou',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#7f8c8d'),
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique'
        )
        elements.append(Paragraph("¡Gracias por su preferencia!", thank_you_style))
        
        # Generation timestamp
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        elements.append(Paragraph(f"Documento generado el {timestamp}", thank_you_style))
        
        return elements

    def generate_pdf_buffer(self, invoice: Invoice, company_info: CompanyInfo) -> BytesIO:
        """Generate PDF and return as BytesIO buffer"""
        buffer = BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Build the PDF content (same as file version)
        story = []
        story.extend(self._create_header(company_info, invoice))
        story.append(Spacer(1, 0.5*inch))
        story.extend(self._create_client_info(invoice))
        story.append(Spacer(1, 0.3*inch))
        story.extend(self._create_items_table(invoice))
        story.append(Spacer(1, 0.3*inch))
        story.extend(self._create_payment_section(invoice))
        story.append(Spacer(1, 0.3*inch))
        story.extend(self._create_footer(invoice, company_info))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer
