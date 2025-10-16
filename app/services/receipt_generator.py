from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from datetime import datetime
from io import BytesIO
from typing import Optional

from ..models.order import Order
from ..schemas.invoice import CompanyInfo
from ..utils.timezone import convert_utc_to_client_timezone


class ReceiptGenerator:
    """Generator for order receipts/vouchers (comprobantes)"""

    def __init__(self):
        self.width, self.height = A4
        self.margin = 2 * cm

    def generate_order_receipt(
            self,
            order: Order,
            company_info: CompanyInfo,
            output_path: str,
            client_timezone: Optional[str] = None) -> str:
        """Generate a simple order receipt PDF"""

        # Create PDF
        c = canvas.Canvas(output_path, pagesize=A4)
        self._draw_receipt(c, order, company_info, client_timezone)
        c.save()

        return output_path

    def generate_receipt_buffer(
            self,
            order: Order,
            company_info: CompanyInfo,
            client_timezone: Optional[str] = None) -> BytesIO:
        """Generate receipt and return as BytesIO buffer"""
        buffer = BytesIO()

        # Create PDF
        c = canvas.Canvas(buffer, pagesize=A4)
        self._draw_receipt(c, order, company_info, client_timezone)
        c.save()

        buffer.seek(0)
        return buffer

    def _draw_receipt(
            self,
            c: canvas.Canvas,
            order: Order,
            company_info: CompanyInfo,
            client_timezone: Optional[str] = None):
        """Draw the complete receipt on the canvas"""

        # Header
        self._draw_header(c, order, company_info)

        # Customer info
        self._draw_customer_info(c, order)

        # Order details
        self._draw_order_details(c, order, client_timezone)

        # Items table
        self._draw_items_table(c, order)

        # Total
        self._draw_total(c, order)

        # Footer
        self._draw_footer(c, order, company_info)

    def _draw_header(
            self,
            c: canvas.Canvas,
            order: Order,
            company_info: CompanyInfo):
        """Draw header with company info and receipt title"""
        y = self.height - self.margin

        # Company name
        c.setFont("Helvetica-Bold", 18)
        c.setFillColor(colors.darkblue)
        c.drawString(self.margin, y, company_info.name)

        # COMPROBANTE title (right aligned)
        c.setFont("Helvetica-Bold", 20)
        c.setFillColor(colors.darkgreen)
        title_width = c.stringWidth(
            "COMPROBANTE DE PEDIDO", "Helvetica-Bold", 20)
        c.drawString(
            self.width -
            self.margin -
            title_width,
            y,
            "COMPROBANTE DE PEDIDO")

        # Company info (left side)
        y -= 25
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.black)

        company_lines = [
            f"📍 {company_info.address}",
            f"📞 {company_info.phone}",
            f"📧 {company_info.email}",
            f"🆔 NIT: {company_info.nit}"
        ]

        for line in company_lines:
            c.drawString(self.margin, y, line)
            y -= 12

        # Receipt info (right side)
        y = self.height - self.margin - 25
        c.setFont("Helvetica-Bold", 10)

        receipt_lines = [
            f"No. Pedido: {order.order_number}",
            f"Fecha: {order.created_at.strftime('%d/%m/%Y %H:%M')}",
            f"Estado: {order.status.value.upper()}",
            f"Cliente ID: #{order.client_id}"
        ]

        for line in receipt_lines:
            line_width = c.stringWidth(line, "Helvetica-Bold", 10)
            c.drawString(self.width - self.margin - line_width, y, line)
            y -= 12

        # Line separator
        y -= 15
        c.setStrokeColor(colors.darkgreen)
        c.setLineWidth(2)
        c.line(self.margin, y, self.width - self.margin, y)

    def _draw_customer_info(self, c: canvas.Canvas, order: Order):
        """Draw customer information"""
        y = self.height - self.margin - 140

        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.darkgreen)
        c.drawString(self.margin, y, "📋 INFORMACIÓN DEL CLIENTE")

        y -= 20
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.black)

        client = order.client
        client_lines = [
            f"Nombre: {client.name}",
            f"Email: {client.email or 'No proporcionado'}",
            f"Teléfono: {client.phone or 'No proporcionado'}",
            f"Dirección: {client.address or 'No proporcionada'}"
        ]

        for line in client_lines:
            c.drawString(self.margin + 20, y, line)
            y -= 14

    def _draw_order_details(self, c: canvas.Canvas, order: Order, client_timezone: Optional[str] = None):
        """Draw order details"""
        y = self.height - self.margin - 260

        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.darkgreen)
        c.drawString(self.margin, y, "📦 DETALLES DEL PEDIDO")

        y -= 20
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.black)

        # Status color
        status_colors = {
            'pending': colors.orange,
            'confirmed': colors.blue,
            'in_progress': colors.purple,
            'shipped': colors.darkblue,
            'delivered': colors.green,
            'cancelled': colors.red
        }

        status_color = status_colors.get(order.status.value, colors.black)

        # Convert order dates to client timezone if provided
        if client_timezone:
            created_at_client = convert_utc_to_client_timezone(order.created_at, client_timezone)
            updated_at_client = convert_utc_to_client_timezone(order.updated_at, client_timezone) if order.updated_at else None
        else:
            created_at_client = order.created_at
            updated_at_client = order.updated_at

        updated_text = (updated_at_client.strftime('%d de %B de %Y a las %H:%M')
                        if updated_at_client else 'N/A')
        details_lines = [
            "Estado del Pedido: ",
            f"Fecha de Creación: {created_at_client.strftime('%d de %B de %Y a las %H:%M')}",
            f"Última Actualización: {updated_text}",
            f"Total de Productos: {len(order.items)} artículos",
        ]

        for i, line in enumerate(details_lines):
            if i == 0:  # Status line with color
                c.drawString(self.margin + 20, y, line)
                status_x = self.margin + 20 + \
                    c.stringWidth(line, "Helvetica", 10)
                c.setFillColor(status_color)
                c.setFont("Helvetica-Bold", 10)
                c.drawString(status_x, y, order.status.value.upper())
                c.setFillColor(colors.black)
                c.setFont("Helvetica", 10)
            else:
                c.drawString(self.margin + 20, y, line)
            y -= 14

        # Notes if available
        if order.notes:
            y -= 5
            c.setFont("Helvetica-Bold", 10)
            c.drawString(self.margin + 20, y, "Notas:")
            y -= 12
            c.setFont("Helvetica", 9)
            # Wrap long notes
            note_text = order.notes[:80] + \
                "..." if len(order.notes) > 80 else order.notes
            c.drawString(self.margin + 20, y, note_text)

    def _draw_items_table(self, c: canvas.Canvas, order: Order):
        """Draw items table"""
        y = self.height - self.margin - 420

        # Table title
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.darkgreen)
        c.drawString(self.margin, y, "🛒 PRODUCTOS PEDIDOS")
        y -= 25

        # Table headers
        headers = [
            "Producto",
            "Descripción",
            "Cantidad",
            "Precio Unit.",
            "Total"]
        col_widths = [120, 160, 60, 80, 80]
        col_positions = [self.margin]

        for width in col_widths[:-1]:
            col_positions.append(col_positions[-1] + width)

        # Header background
        c.setFillColor(colors.lightgrey)
        c.rect(self.margin, y - 15, sum(col_widths), 18, fill=1)

        # Header text
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 9)

        for i, header in enumerate(headers):
            c.drawString(col_positions[i] + 3, y - 8, header)

        # Items rows
        y -= 20
        c.setFont("Helvetica", 8)

        for i, item in enumerate(order.items):
            # Alternate row colors
            if i % 2 == 0:
                c.setFillColor(colors.beige)
                c.rect(self.margin, y - 12, sum(col_widths), 16, fill=1)

            c.setFillColor(colors.black)

            # Truncate long product names
            product_name = item.product.name[:15] + "..." if len(
                item.product.name) > 15 else item.product.name
            description = item.product.description[:20] + "..." if item.product.description and len(
                item.product.description) > 20 else (item.product.description or "N/A")

            row_data = [
                product_name,
                description,
                f"{item.quantity:,}",
                f"Q {item.unit_price:,.2f}",
                f"Q {item.total_price:,.2f}"
            ]

            for j, data in enumerate(row_data):
                c.drawString(col_positions[j] + 3, y - 8, str(data))

            y -= 16

        # Table border
        c.setStrokeColor(colors.darkgrey)
        c.setLineWidth(1)
        table_height = 18 + (len(order.items) * 16) + 20
        c.rect(self.margin, y + 4, sum(col_widths), table_height)

    def _draw_total(self, c: canvas.Canvas, order: Order):
        """Draw total section"""
        y = 180  # Fixed position from bottom

        # Total box
        total_x = self.width - self.margin - 180

        # Background for total
        c.setFillColor(colors.lightgreen)
        c.rect(total_x, y - 30, 180, 40, fill=1)

        # Total amount
        c.setFont("Helvetica-Bold", 16)
        c.setFillColor(colors.darkgreen)
        total_text = f"TOTAL: Q {order.total_amount:,.2f}"
        text_width = c.stringWidth(total_text, "Helvetica-Bold", 16)
        c.drawString(total_x + (180 - text_width) / 2, y - 15, total_text)

        # Additional info
        y -= 45
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.black)

        info_lines = [
            f"Total de artículos: {sum(item.quantity for item in order.items)} unidades",
            f"Productos diferentes: {len(order.items)} tipos"]

        for line in info_lines:
            line_width = c.stringWidth(line, "Helvetica", 9)
            c.drawString(total_x + 180 - line_width, y, line)
            y -= 12

    def _draw_footer(
            self,
            c: canvas.Canvas,
            order: Order,
            company_info: CompanyInfo):
        """Draw footer section"""
        y = 100

        # Important notes
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.darkred)
        c.drawString(self.margin, y, "⚠️ IMPORTANTE:")

        y -= 15
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.black)

        notes = [
            "• Este es un comprobante de pedido, NO es una factura fiscal",
            "• Conserve este documento para referencia y seguimiento",
            "• Para facturación fiscal, solicite su factura por separado"
        ]

        for note in notes:
            c.drawString(self.margin, y, note)
            y -= 12

        # Footer line
        y -= 8
        c.setStrokeColor(colors.lightgrey)
        c.setLineWidth(1)
        c.line(self.margin, y, self.width - self.margin, y)

        # Thank you message and timestamp
        y -= 15
        c.setFont("Helvetica-Oblique", 9)
        c.setFillColor(colors.grey)

        thank_you = "¡Gracias por elegirnos! Su pedido está siendo procesado."
        thank_you_width = c.stringWidth(thank_you, "Helvetica-Oblique", 9)
        center_x = (self.width - thank_you_width) / 2
        c.drawString(center_x, y, thank_you)

        # Generation timestamp
        y -= 12
        timestamp = f"Comprobante generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}"
        timestamp_width = c.stringWidth(timestamp, "Helvetica-Oblique", 8)
        center_x = (self.width - timestamp_width) / 2
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(center_x, y, timestamp)

        # Contact info
        y -= 15
        contact = f"Para consultas: {company_info.phone} | {company_info.email}"
        contact_width = c.stringWidth(contact, "Helvetica-Oblique", 8)
        center_x = (self.width - contact_width) / 2
        c.drawString(center_x, y, contact)
