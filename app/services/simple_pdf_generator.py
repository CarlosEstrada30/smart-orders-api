from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from datetime import datetime
from io import BytesIO

from ..models.invoice import Invoice
from ..schemas.invoice import CompanyInfo


class SimplePDFGenerator:
    """Simple PDF generator using basic reportlab canvas to avoid compatibility issues"""

    def __init__(self):
        self.width, self.height = A4
        self.margin = 2 * cm

    def generate_invoice_pdf(
            self,
            invoice: Invoice,
            company_info: CompanyInfo,
            output_path: str) -> str:
        """Generate a simple but professional invoice PDF"""

        # Create PDF
        c = canvas.Canvas(output_path, pagesize=A4)
        self._draw_invoice(c, invoice, company_info)
        c.save()

        return output_path

    def generate_pdf_buffer(
            self,
            invoice: Invoice,
            company_info: CompanyInfo) -> BytesIO:
        """Generate PDF and return as BytesIO buffer"""
        buffer = BytesIO()

        # Create PDF
        c = canvas.Canvas(buffer, pagesize=A4)
        self._draw_invoice(c, invoice, company_info)
        c.save()

        buffer.seek(0)
        return buffer

    def _draw_invoice(
            self,
            c: canvas.Canvas,
            invoice: Invoice,
            company_info: CompanyInfo):
        """Draw the complete invoice on the canvas"""

        # Header
        self._draw_header(c, invoice, company_info)

        # Client info
        self._draw_client_info(c, invoice)

        # Items table
        self._draw_items_table(c, invoice)

        # Totals
        self._draw_totals(c, invoice)

        # Footer
        self._draw_footer(c, invoice, company_info)

    def _draw_header(
            self,
            c: canvas.Canvas,
            invoice: Invoice,
            company_info: CompanyInfo):
        """Draw header with company info and invoice details"""
        y = self.height - self.margin

        # Company name
        c.setFont("Helvetica-Bold", 20)
        c.setFillColor(colors.darkblue)
        c.drawString(self.margin, y, company_info.name)

        # FACTURA title (right aligned)
        c.setFont("Helvetica-Bold", 24)
        c.setFillColor(colors.red)
        title_width = c.stringWidth("FACTURA", "Helvetica-Bold", 24)
        c.drawString(self.width - self.margin - title_width, y, "FACTURA")

        # Company info (left side)
        y -= 30
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.black)

        company_lines = [
            f"Dirección: {company_info.address}",
            f"Teléfono: {company_info.phone}",
            f"Email: {company_info.email}",
            f"NIT: {company_info.nit}"
        ]

        for line in company_lines:
            c.drawString(self.margin, y, line)
            y -= 15

        # Invoice info (right side)
        y = self.height - self.margin - 30
        c.setFont("Helvetica-Bold", 10)

        invoice_lines = [
            f"No. Factura: {invoice.invoice_number}",
            f"No. Pedido: {invoice.order.order_number}",
            f"Fecha Emisión: {invoice.issue_date.strftime('%d/%m/%Y')}",
            f"Fecha Vencimiento: {invoice.due_date.strftime('%d/%m/%Y') if invoice.due_date else 'N/A'}"]

        for line in invoice_lines:
            line_width = c.stringWidth(line, "Helvetica-Bold", 10)
            c.drawString(self.width - self.margin - line_width, y, line)
            y -= 15

        # Line separator
        y -= 10
        c.setStrokeColor(colors.red)
        c.setLineWidth(2)
        c.line(self.margin, y, self.width - self.margin, y)

    def _draw_client_info(self, c: canvas.Canvas, invoice: Invoice):
        """Draw client information"""
        y = self.height - self.margin - 140

        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.black)
        c.drawString(self.margin, y, "FACTURAR A:")

        y -= 20
        c.setFont("Helvetica", 10)

        client = invoice.order.client
        client_lines = [
            f"Cliente: {client.name}",
            f"Email: {client.email or 'N/A'}",
            f"Teléfono: {client.phone or 'N/A'}",
            f"NIT: {client.nit or 'C/F'}",
            f"Dirección: {client.address or 'N/A'}"
        ]

        for line in client_lines:
            c.drawString(self.margin, y, line)
            y -= 15

    def _draw_items_table(self, c: canvas.Canvas, invoice: Invoice):
        """Draw items table"""
        y = self.height - self.margin - 280

        # Table headers
        headers = ["Producto", "SKU", "Cantidad", "Precio Unit.", "Total"]
        col_widths = [200, 80, 60, 80, 80]
        col_positions = [self.margin]

        for width in col_widths[:-1]:
            col_positions.append(col_positions[-1] + width)

        # Header background
        c.setFillColor(colors.darkgrey)
        c.rect(self.margin, y - 15, sum(col_widths), 20, fill=1)

        # Header text
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)

        for i, header in enumerate(headers):
            c.drawString(col_positions[i] + 5, y - 10, header)

        # Items rows
        y -= 25
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 9)

        for i, item in enumerate(invoice.order.items):
            # Alternate row colors
            if i % 2 == 0:
                c.setFillColor(colors.lightgrey)
                c.rect(self.margin, y - 15, sum(col_widths), 20, fill=1)

            c.setFillColor(colors.black)

            row_data = [
                item.product.name[:25] + "..." if len(item.product.name) > 25 else item.product.name,
                item.product.sku or "N/A",
                f"{item.quantity:,}",
                f"Q {item.unit_price:,.2f}",
                f"Q {item.total_price:,.2f}"
            ]

            for j, data in enumerate(row_data):
                c.drawString(col_positions[j] + 5, y - 10, str(data))

            y -= 20

        # Table border
        c.setStrokeColor(colors.black)
        c.setLineWidth(1)
        table_height = 20 + (len(invoice.order.items) * 20) + 25
        c.rect(self.margin, y + 5, sum(col_widths), table_height)

    def _draw_totals(self, c: canvas.Canvas, invoice: Invoice):
        """Draw totals section"""
        y = 200  # Fixed position from bottom

        # Totals box
        totals_x = self.width - self.margin - 150

        c.setFont("Helvetica", 10)
        c.setFillColor(colors.black)

        totals_lines = [
            f"Subtotal: Q {invoice.subtotal:,.2f}",
            f"Descuento: Q {invoice.discount_amount:,.2f}",
            f"IVA (12%): Q {invoice.tax_amount:,.2f}",
        ]

        for line in totals_lines:
            line_width = c.stringWidth(line, "Helvetica", 10)
            c.drawString(totals_x + 150 - line_width, y, line)
            y -= 15

        # Total line
        y -= 5
        c.setStrokeColor(colors.green)
        c.setLineWidth(2)
        c.line(totals_x, y, totals_x + 150, y)

        y -= 15
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(colors.green)
        total_line = f"TOTAL: Q {invoice.total_amount:,.2f}"
        line_width = c.stringWidth(total_line, "Helvetica-Bold", 14)
        c.drawString(totals_x + 150 - line_width, y, total_line)

        # Payment status
        y -= 25
        c.setFont("Helvetica-Bold", 12)

        status_colors = {
            'paid': colors.green,
            'issued': colors.orange,
            'overdue': colors.red,
            'draft': colors.grey
        }

        status_text = {
            'paid': 'PAGADO',
            'issued': 'PENDIENTE',
            'overdue': 'VENCIDO',
            'draft': 'BORRADOR'
        }.get(invoice.status.value, invoice.status.value.upper())

        c.setFillColor(status_colors.get(invoice.status.value, colors.black))
        status_line = f"Estado: {status_text}"
        line_width = c.stringWidth(status_line, "Helvetica-Bold", 12)
        c.drawString(totals_x + 150 - line_width, y, status_line)

        if invoice.paid_amount > 0:
            y -= 15
            c.setFont("Helvetica", 10)
            c.setFillColor(colors.black)

            paid_line = f"Pagado: Q {invoice.paid_amount:,.2f}"
            line_width = c.stringWidth(paid_line, "Helvetica", 10)
            c.drawString(totals_x + 150 - line_width, y, paid_line)

            y -= 12
            balance_line = f"Saldo: Q {invoice.balance_due:,.2f}"
            line_width = c.stringWidth(balance_line, "Helvetica", 10)
            c.drawString(totals_x + 150 - line_width, y, balance_line)

    def _draw_footer(
            self,
            c: canvas.Canvas,
            invoice: Invoice,
            company_info: CompanyInfo):
        """Draw footer section"""
        y = 120

        # Payment terms
        if invoice.payment_terms:
            c.setFont("Helvetica", 10)
            c.setFillColor(colors.black)
            c.drawString(
                self.margin,
                y,
                f"Términos de Pago: {invoice.payment_terms}")
            y -= 15

        # Notes
        if invoice.notes:
            c.drawString(self.margin, y, f"Notas: {invoice.notes}")
            y -= 20

        # Footer line
        c.setStrokeColor(colors.lightgrey)
        c.setLineWidth(1)
        c.line(self.margin, y, self.width - self.margin, y)

        # Thank you message
        y -= 15
        c.setFont("Helvetica-Oblique", 10)
        c.setFillColor(colors.grey)

        thank_you = "¡Gracias por su preferencia!"
        thank_you_width = c.stringWidth(thank_you, "Helvetica-Oblique", 10)
        center_x = (self.width - thank_you_width) / 2
        c.drawString(center_x, y, thank_you)

        # Generation timestamp
        y -= 12
        timestamp = f"Documento generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        timestamp_width = c.stringWidth(timestamp, "Helvetica-Oblique", 8)
        center_x = (self.width - timestamp_width) / 2
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(center_x, y, timestamp)
