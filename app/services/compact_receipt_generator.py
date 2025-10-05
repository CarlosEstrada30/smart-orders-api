from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from datetime import datetime
import requests
from io import BytesIO
from PIL import Image as PILImage
from typing import Optional

from ..models.order import Order
from ..models.settings import Settings
from ..utils.timezone import convert_utc_to_client_timezone


class CompactReceiptGenerator:
    """Generador compacto de comprobantes de órdenes para una sola página"""

    def __init__(self):
        self.width, self.height = A4
        self.margin = 1.5 * cm  # Reducido el margen
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Configura estilos compactos para el PDF"""
        # Estilo para el título principal - más compacto
        self.styles.add(ParagraphStyle(
            name='CompanyTitle',
            parent=self.styles['Heading1'],
            fontSize=18,  # Reducido de 24
            spaceAfter=4,
            textColor=colors.Color(0.2, 0.2, 0.2),  # Gris oscuro
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        # Estilo para información de empresa - más compacto
        self.styles.add(ParagraphStyle(
            name='CompanyInfo',
            parent=self.styles['Normal'],
            fontSize=9,  # Reducido de 10
            spaceAfter=2,
            textColor=colors.Color(0.3, 0.3, 0.3),
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))

        # Estilo para títulos de sección - más compacto
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=11,  # Reducido de 14
            spaceBefore=6,  # Reducido de 15
            spaceAfter=4,   # Reducido de 8
            textColor=colors.Color(0.3, 0.3, 0.3),  # Gris oscuro
            borderWidth=1,
            borderColor=colors.Color(0.7, 0.7, 0.7),  # Gris medio
            borderPadding=3,  # Reducido de 5
            backColor=colors.Color(0.96, 0.96, 0.96),  # Gris muy claro
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        ))

        # Estilo para texto normal más compacto
        self.styles.add(ParagraphStyle(
            name='NormalText',
            parent=self.styles['Normal'],
            fontSize=9,  # Reducido de 10
            spaceAfter=2,  # Reducido de 4
            textColor=colors.Color(0.2, 0.2, 0.2),
            alignment=TA_LEFT,
            fontName='Helvetica'
        ))

        # Estilo para el total - más compacto
        self.styles.add(ParagraphStyle(
            name='TotalAmount',
            parent=self.styles['Normal'],
            fontSize=16,  # Reducido de 18
            spaceBefore=5,  # Reducido de 10
            spaceAfter=5,   # Reducido de 10
            textColor=colors.Color(0.2, 0.2, 0.2),  # Gris oscuro
            alignment=TA_RIGHT,
            fontName='Helvetica-Bold'
        ))

    def generate_order_receipt(
            self,
            order: Order,
            settings: Settings,
            output_path: str,
            client_timezone: Optional[str] = None) -> str:
        """Genera un comprobante compacto de orden"""
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )

        story = []

        # Header compacto con logo y información de empresa
        story.extend(self._create_compact_header(settings))
        story.append(Spacer(1, 4 * mm))

        # Título del documento
        story.append(
            Paragraph(
                "COMPROBANTE DE PEDIDO",
                self.styles['CompanyTitle']))
        story.append(Spacer(1, 4 * mm))

        # Información del pedido y cliente en layout limpio
        story.extend(self._create_clean_order_client_info(order, client_timezone))
        story.append(Spacer(1, 4 * mm))

        # Tabla de productos compacta
        story.extend(self._create_compact_products_table(order))
        story.append(Spacer(1, 4 * mm))

        # Total destacado
        story.extend(self._create_compact_total_section(order))
        story.append(Spacer(1, 4 * mm))

        # Footer mínimo
        story.extend(self._create_minimal_footer(settings, client_timezone))

        doc.build(story)
        return output_path

    def generate_receipt_buffer(
            self,
            order: Order,
            settings: Settings,
            client_timezone: Optional[str] = None) -> BytesIO:
        """Genera el comprobante compacto y lo retorna como BytesIO buffer"""
        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )

        story = []

        # Header compacto con logo y información de empresa
        story.extend(self._create_compact_header(settings))
        story.append(Spacer(1, 4 * mm))

        # Título del documento
        story.append(
            Paragraph(
                "COMPROBANTE DE PEDIDO",
                self.styles['CompanyTitle']))
        story.append(Spacer(1, 4 * mm))

        # Información del pedido y cliente en layout limpio
        story.extend(self._create_clean_order_client_info(order, client_timezone))
        story.append(Spacer(1, 4 * mm))

        # Tabla de productos compacta
        story.extend(self._create_compact_products_table(order))
        story.append(Spacer(1, 4 * mm))

        # Total destacado
        story.extend(self._create_compact_total_section(order))
        story.append(Spacer(1, 4 * mm))

        # Footer mínimo
        story.extend(self._create_minimal_footer(settings, client_timezone))

        doc.build(story)
        buffer.seek(0)
        return buffer

    def _create_compact_header(self, settings: Settings):
        """Crea el header compacto con logo y información de empresa"""
        elements = []

        # Información de la empresa en formato compacto
        company_parts = [f"<b>{settings.company_name}</b>"]
        if settings.business_name:
            company_parts.append(settings.business_name)
        company_parts.append(f"NIT: {settings.nit}")

        company_info = f'<para align="center">{" | ".join(company_parts)}</para>'

        # Si hay logo, crear tabla con logo e info
        if settings.logo_url:
            try:
                logo = self._get_logo_image(
                    settings.logo_url, max_width=2.5 * cm, max_height=2.5 * cm)
                if logo:
                    header_data = [
                        [logo, Paragraph(company_info, self.styles['Normal'])]]
                    header_table = Table(
                        header_data, colWidths=[
                            3 * cm, 13 * cm])
                    header_table.setStyle(TableStyle([
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                        ('ALIGN', (1, 0), (1, 0), 'LEFT'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 0),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ]))
                    elements.append(header_table)
                else:
                    elements.append(
                        Paragraph(
                            company_info,
                            self.styles['Normal']))
            except BaseException:
                elements.append(Paragraph(company_info, self.styles['Normal']))
        else:
            elements.append(Paragraph(company_info, self.styles['Normal']))

        # Información de contacto en una línea
        contact_parts = []
        if settings.address:
            contact_parts.append(settings.address)
        if settings.phone:
            contact_parts.append(f"Tel: {settings.phone}")
        if settings.email:
            contact_parts.append(settings.email)

        if contact_parts:
            contact_text = " | ".join(contact_parts)
            elements.append(
                Paragraph(
                    f'<para align="center">{contact_text}</para>',
                    self.styles['CompanyInfo']))

        return elements

    def _create_clean_order_client_info(self, order: Order, client_timezone: Optional[str] = None):
        """Crea un layout limpio para información del pedido y cliente"""
        elements = []

        client = order.client

        # Convert order dates to client timezone if provided
        if client_timezone:
            created_at_client = convert_utc_to_client_timezone(order.created_at, client_timezone)
            updated_at_client = convert_utc_to_client_timezone(order.updated_at, client_timezone) if order.updated_at else None
        else:
            created_at_client = order.created_at
            updated_at_client = order.updated_at

        # Crear tabla simple de dos columnas sin colores de fondo
        order_client_data = [
            # Headers
            [Paragraph("<b>INFORMACIÓN DEL PEDIDO</b>", self.styles['NormalText']),
             Paragraph("<b>INFORMACIÓN DEL CLIENTE</b>", self.styles['NormalText'])],
            # Data rows
            [f"No. Pedido: {order.order_number}", f"Cliente: {client.name}"],
            [f"Fecha: {created_at_client.strftime('%d/%m/%Y')}",
             f"Email: {client.email or 'No proporcionado'}"],
            [f"Hora: {created_at_client.strftime('%H:%M')}",
             f"Teléfono: {client.phone or 'No proporcionado'}"],
            ["", f"Dirección: {client.address or 'No proporcionada'}"]
        ]

        info_table = Table(order_client_data, colWidths=[8 * cm, 8 * cm])
        info_table.setStyle(TableStyle([
            # Headers en primera fila
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('TEXTCOLOR', (0, 0), (-1, 0),
             colors.Color(0.2, 0.2, 0.2)),  # Gris oscuro
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),

            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),

            # Padding uniforme
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 1), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 2),

            # Solo línea divisoria debajo de headers
            ('LINEBELOW', (0, 0), (-1, 0), 1,
             colors.Color(0.5, 0.5, 0.5)),  # Gris medio
        ]))

        elements.append(info_table)
        return elements

    def _create_compact_products_table(self, order: Order):
        """Crea la tabla de productos más compacta"""
        elements = []

        elements.append(
            Paragraph(
                "PRODUCTOS SOLICITADOS",
                self.styles['SectionTitle']))

        # Headers de la tabla - columnas más estrechas
        headers = ['#', 'Producto', 'Cant.', 'P. Unit.', 'Total']

        # Datos de la tabla
        table_data = [headers]

        for i, item in enumerate(order.items, 1):
            # Nombre más corto
            product_name = item.product.name
            if len(product_name) > 25:
                product_name = product_name[:22] + "..."

            row = [
                str(i),
                product_name,
                f"{item.quantity:,}",
                f"Q {item.unit_price:,.2f}",
                # Con decimales y espacio después de Q
                f"Q {item.total_price:,.2f}"
            ]
            table_data.append(row)

        # Crear tabla más compacta
        col_widths = [1 * cm, 6 * cm, 2 * cm, 3 * cm, 4 * cm]
        products_table = Table(table_data, colWidths=col_widths)

        # Estilos de la tabla más compactos
        table_style = [
            # Header
            ('BACKGROUND', (0, 0), (-1, 0),
             colors.Color(0.4, 0.4, 0.4)),  # Gris oscuro
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),  # Reducido
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),  # Reducido
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Número
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Cantidad
            ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),  # Precios

            # Borders
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.7, 0.7, 0.7)),
            ('LINEBELOW', (0, 0), (-1, 0), 2,
             colors.Color(0.4, 0.4, 0.4)),  # Gris oscuro

            # Padding reducido
            ('LEFTPADDING', (0, 0), (-1, -1), 2),  # Reducido
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),   # Reducido
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]

        # Agregar colores alternados para las filas
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                table_style.append(
                    ('BACKGROUND', (0, i), (-1, i), colors.Color(0.97, 0.97, 0.97)))

        products_table.setStyle(TableStyle(table_style))
        elements.append(products_table)

        return elements

    def _create_compact_total_section(self, order: Order):
        """Crea la sección de total más compacta"""
        elements = []

        # Total en tabla para mejor control de layout
        total_data = [["Total de productos:",
                       f"{len(order.items)} tipos",
                       "Total de unidades:",
                       f"{sum(item.quantity for item in order.items):,}"],
                      ["",
                       "",
                       "TOTAL A PAGAR:",
                       f"Q {order.total_amount:,.2f}"]]

        # Ajustar anchos para que el texto "TOTAL A PAGAR" no se desborde
        total_table = Table(
            total_data, colWidths=[
                3 * cm, 2 * cm, 5 * cm, 6 * cm])
        total_table.setStyle(TableStyle([
            # Fila de información
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (1, 0), 'LEFT'),
            ('ALIGN', (2, 0), (3, 0), 'RIGHT'),

            # Fila del total
            ('FONTNAME', (2, 1), (3, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (2, 1), (3, 1), 14),
            ('ALIGN', (2, 1), (3, 1), 'RIGHT'),
            ('TEXTCOLOR', (2, 1), (3, 1), colors.Color(
                0.1, 0.1, 0.1)),  # Negro/gris muy oscuro

            # Background para el total
            ('BACKGROUND', (2, 1), (3, 1), colors.Color(
                0.93, 0.93, 0.93)),  # Gris claro
            ('BOX', (2, 1), (3, 1), 1, colors.Color(
                0.5, 0.5, 0.5)),  # Borde gris medio

            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))

        elements.append(total_table)

        return elements

    def _create_minimal_footer(self, settings: Settings, client_timezone: Optional[str] = None):
        """Crea un footer mínimo y compacto"""
        elements = []

        # Solo las notas más importantes
        notes = [
            "• Este es un comprobante de pedido, NO constituye factura fiscal.",
            "• Conserve este documento para seguimiento de su pedido.",
        ]

        for note in notes:
            elements.append(Paragraph(note, self.styles['NormalText']))

        # Información de contacto y timestamp en una línea
        if client_timezone:
            # Convert current time to client timezone
            current_time = datetime.now()
            client_time = convert_utc_to_client_timezone(current_time, client_timezone)
            timestamp = client_time.strftime('%d/%m/%Y %H:%M')
        else:
            timestamp = datetime.now().strftime('%d/%m/%Y %H:%M')
            
        footer_parts = [f"Generado: {timestamp}"]

        if settings.phone:
            footer_parts.append(f"Tel: {settings.phone}")
        if settings.email:
            footer_parts.append(settings.email)

        footer_text = " | ".join(footer_parts)
        elements.append(
            Paragraph(
                f'<para align="center">{footer_text}</para>',
                self.styles['CompanyInfo']))

        return elements

    def _get_logo_image(
            self,
            logo_url: str,
            max_width=2.5 * cm,
            max_height=2.5 * cm):
        """Descarga y prepara el logo para insertar en el PDF"""
        try:
            response = requests.get(logo_url, timeout=5)
            response.raise_for_status()

            # Crear imagen desde los bytes
            img_buffer = BytesIO(response.content)
            pil_img = PILImage.open(img_buffer)

            # Calcular dimensiones manteniendo proporción
            width, height = pil_img.size
            aspect_ratio = width / height

            if width > height:
                new_width = min(max_width, width)
                new_height = new_width / aspect_ratio
            else:
                new_height = min(max_height, height)
                new_width = new_height * aspect_ratio

            # Crear imagen ReportLab
            img_buffer.seek(0)
            img = Image(img_buffer, width=new_width, height=new_height)
            return img

        except Exception as e:
            print(f"Error loading logo: {e}")
            return None
