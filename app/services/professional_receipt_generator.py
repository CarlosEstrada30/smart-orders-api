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


def format_quantity(quantity) -> str:
    """Formatea una cantidad mostrando decimales solo cuando es necesario"""
    if quantity == int(quantity):
        return f"{int(quantity):,}"
    else:
        return f"{quantity:,.2f}"


class ProfessionalReceiptGenerator:
    """Generador profesional de comprobantes de órdenes usando información de settings"""

    def __init__(self):
        self.width, self.height = A4
        self.margin = 2 * cm
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Configura estilos personalizados para el PDF"""
        # Estilo para el título principal
        self.styles.add(ParagraphStyle(
            name='CompanyTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=6,
            textColor=colors.Color(0.1, 0.2, 0.5),  # Azul oscuro
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        # Estilo para información de empresa
        self.styles.add(ParagraphStyle(
            name='CompanyInfo',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=3,
            textColor=colors.Color(0.3, 0.3, 0.3),
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))

        # Estilo para títulos de sección
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=8,
            textColor=colors.Color(0.1, 0.4, 0.1),  # Verde oscuro
            borderWidth=1,
            borderColor=colors.Color(0.8, 0.8, 0.8),
            borderPadding=5,
            backColor=colors.Color(0.95, 0.98, 0.95),
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        ))

        # Estilo para información importante
        self.styles.add(ParagraphStyle(
            name='ImportantInfo',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=4,
            textColor=colors.Color(0.2, 0.2, 0.2),
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        ))

        # Estilo para texto normal con mejor espaciado
        self.styles.add(ParagraphStyle(
            name='NormalText',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=4,
            textColor=colors.Color(0.2, 0.2, 0.2),
            alignment=TA_LEFT,
            fontName='Helvetica'
        ))

        # Estilo para el total
        self.styles.add(ParagraphStyle(
            name='TotalAmount',
            parent=self.styles['Normal'],
            fontSize=18,
            spaceBefore=10,
            spaceAfter=10,
            textColor=colors.Color(0.1, 0.5, 0.1),  # Verde
            alignment=TA_RIGHT,
            fontName='Helvetica-Bold'
        ))

    def generate_order_receipt(
            self,
            order: Order,
            settings: Settings,
            output_path: str,
            client_timezone: Optional[str] = None) -> str:
        """Genera un comprobante profesional de orden"""
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )

        story = []

        # Header con logo y información de empresa
        story.extend(self._create_header(settings))
        story.append(Spacer(1, 15 * mm))

        # Título del documento
        story.append(
            Paragraph(
                "ORDEN DE PEDIDO",
                self.styles['CompanyTitle']))
        story.append(Spacer(1, 10 * mm))

        # Información del pedido
        story.extend(self._create_order_info(order, client_timezone))
        story.append(Spacer(1, 8 * mm))

        # Información del cliente
        story.extend(self._create_customer_info(order))
        story.append(Spacer(1, 8 * mm))

        # Tabla de productos
        story.extend(self._create_products_table(order))
        story.append(Spacer(1, 10 * mm))

        # Resumen y total
        story.extend(self._create_summary_section(order))
        story.append(Spacer(1, 15 * mm))

        # Footer con notas importantes
        story.extend(self._create_footer(settings, client_timezone))

        doc.build(story)
        return output_path

    def generate_receipt_buffer(
            self,
            order: Order,
            settings: Settings,
            client_timezone: Optional[str] = None) -> BytesIO:
        """Genera el comprobante y lo retorna como BytesIO buffer"""
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

        # Header con logo y información de empresa
        story.extend(self._create_header(settings))
        story.append(Spacer(1, 15 * mm))

        # Título del documento
        story.append(
            Paragraph(
                "ORDEN DE PEDIDO",
                self.styles['CompanyTitle']))
        story.append(Spacer(1, 10 * mm))

        # Información del pedido
        story.extend(self._create_order_info(order, client_timezone))
        story.append(Spacer(1, 8 * mm))

        # Información del cliente
        story.extend(self._create_customer_info(order))
        story.append(Spacer(1, 8 * mm))

        # Tabla de productos
        story.extend(self._create_products_table(order))
        story.append(Spacer(1, 10 * mm))

        # Resumen y total
        story.extend(self._create_summary_section(order))
        story.append(Spacer(1, 15 * mm))

        # Footer con notas importantes
        story.extend(self._create_footer(settings, client_timezone))

        doc.build(story)
        buffer.seek(0)
        return buffer

    def _create_header(self, settings: Settings):
        """Crea el header con logo y información de empresa"""
        elements = []

        # Crear una tabla para layout de header (logo + info empresa)
        header_data = []

        # Logo (si existe)
        logo_cell = ""
        if settings.logo_url:
            try:
                logo_cell = self._get_logo_image(settings.logo_url)
            except BaseException:
                logo_cell = ""  # Si no se puede cargar el logo, continuar sin él

        # Información de la empresa
        company_info = f"""
        <para align="center">
        <font size="20" color="#1a4b8c"><b>{settings.company_name}</b></font>
        </para>
        """

        # Si tenemos logo y información
        if logo_cell:
            header_data = [[logo_cell, Paragraph(
                company_info, self.styles['Normal'])]]
            header_table = Table(header_data, colWidths=[4 * cm, 12 * cm])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('ALIGN', (1, 0), (1, 0), 'LEFT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
        else:
            # Solo información sin logo
            header_table = Paragraph(company_info, self.styles['Normal'])

        elements.append(header_table)

        # Información de contacto debajo (sin email)
        contact_info = []
        if settings.address:
            contact_info.append(f"📍 {settings.address}")
        if settings.phone:
            contact_info.append(f"📞 {settings.phone}")
        if settings.website:
            contact_info.append(f"🌐 {settings.website}")

        if contact_info:
            contact_text = " | ".join(contact_info)
            elements.append(
                Paragraph(
                    f'<para align="center">{contact_text}</para>',
                    self.styles['CompanyInfo']))

        # Línea separadora
        elements.append(Spacer(1, 5 * mm))

        return elements

    def _get_logo_image(
            self,
            logo_url: str,
            max_width=3 * cm,
            max_height=3 * cm):
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

    def _create_order_info(self, order: Order, client_timezone: Optional[str] = None):
        """Crea la sección con información del pedido"""
        elements = []

        elements.append(
            Paragraph(
                "INFORMACIÓN DEL PEDIDO",
                self.styles['SectionTitle']))

        # Convert order dates to client timezone if provided
        if client_timezone:
            created_at_client = convert_utc_to_client_timezone(order.created_at, client_timezone)
            updated_at_client = convert_utc_to_client_timezone(order.updated_at, client_timezone) if order.updated_at else None
        else:
            created_at_client = order.created_at
            updated_at_client = order.updated_at

        # Crear tabla con información del pedido
        order_data = [
            ["Número de Pedido:", order.order_number],
            ["Fecha:", created_at_client.strftime('%d de %B de %Y')],
            ["Hora:", created_at_client.strftime('%I:%M %p')],
            ["Estado:", self._format_status(order.status.value)],
        ]

        if updated_at_client and updated_at_client != created_at_client:
            order_data.append(["Última Actualización:",
                               updated_at_client.strftime('%d/%m/%Y %I:%M %p')])

        order_table = Table(order_data, colWidths=[4 * cm, 8 * cm])
        order_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))

        elements.append(order_table)

        # Notas del pedido si existen
        if order.notes:
            elements.append(Spacer(1, 5 * mm))
            elements.append(
                Paragraph(
                    "<b>Notas del Pedido:</b>",
                    self.styles['ImportantInfo']))
            elements.append(Paragraph(order.notes, self.styles['NormalText']))

        return elements

    def _create_customer_info(self, order: Order):
        """Crea la sección con información del cliente"""
        elements = []

        elements.append(
            Paragraph(
                "INFORMACIÓN DEL CLIENTE",
                self.styles['SectionTitle']))

        client = order.client
        client_data = [
            ["Cliente:", client.name],
            ["Email:", client.email or "No proporcionado"],
            ["Teléfono:", client.phone or "No proporcionado"],
            ["Dirección:", client.address or "No proporcionada"],
        ]

        client_table = Table(client_data, colWidths=[3 * cm, 9 * cm])
        client_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))

        elements.append(client_table)

        return elements

    def _create_products_table(self, order: Order):
        """Crea la tabla de productos profesional"""
        elements = []

        elements.append(
            Paragraph(
                "PRODUCTOS SOLICITADOS",
                self.styles['SectionTitle']))

        # Headers de la tabla
        headers = [
            '#',
            'Producto',
            'Descripción',
            'Cantidad',
            'Precio Unit.',
            'Total']

        # Datos de la tabla
        table_data = [headers]

        for i, item in enumerate(order.items, 1):
            # Formatear nombre del producto (truncar si es muy largo)
            product_name = item.product.name
            if len(product_name) > 20:
                product_name = product_name[:17] + "..."

            # Formatear descripción
            description = item.product.description or "Sin descripción"
            if len(description) > 25:
                description = description[:22] + "..."

            row = [
                str(i),
                product_name,
                description,
                format_quantity(item.quantity),
                f"Q {item.unit_price:,.2f}",
                f"Q {item.total_price:,.2f}"
            ]
            table_data.append(row)

        # Crear tabla
        col_widths = [1 * cm, 3.5 * cm, 4.5 * cm, 2 * cm, 2.5 * cm, 2.5 * cm]
        products_table = Table(table_data, colWidths=col_widths)

        # Estilos de la tabla
        table_style = [
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.4, 0.6)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Número
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Cantidad
            ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),  # Precios

            # Borders
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.7, 0.7, 0.7)),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.Color(0.2, 0.4, 0.6)),

            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),

            # Alternating row colors
        ]

        # Agregar colores alternados para las filas
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                table_style.append(
                    ('BACKGROUND', (0, i), (-1, i), colors.Color(0.97, 0.97, 0.97)))

        products_table.setStyle(TableStyle(table_style))
        elements.append(products_table)

        return elements

    def _create_summary_section(self, order: Order):
        """Crea la sección de resumen y total"""
        elements = []

        # Información de resumen
        total_items = sum(float(item.quantity) for item in order.items)
        different_products = len(order.items)

        summary_info = [
            f"Total de artículos: {total_items:,} unidades",
            f"Productos diferentes: {different_products} tipos"
        ]

        for info in summary_info:
            elements.append(Paragraph(info, self.styles['NormalText']))

        elements.append(Spacer(1, 10 * mm))

        # Calcular subtotal (suma de todos los items)
        subtotal = sum(item.total_price for item in order.items)

        # Crear tabla de desglose de totales
        total_data = []

        # Subtotal
        total_data.append([
            Paragraph("Subtotal:", self.styles['NormalText']),
            Paragraph(f"Q {subtotal:,.2f}", self.styles['NormalText'])
        ])

        # Descuento si aplica
        if order.discount_amount and order.discount_amount > 0:
            total_data.append([
                Paragraph("Descuento:", self.styles['NormalText']),
                Paragraph(f"-Q {order.discount_amount:,.2f}", self.styles['NormalText'])
            ])

        # Total final
        total_data.append([
            Paragraph("TOTAL DEL PEDIDO:", self.styles['TotalAmount']),
            Paragraph(f"Q {order.total_amount:,.2f}", self.styles['TotalAmount'])
        ])

        # Crear tabla de totales
        total_table = Table(total_data, colWidths=[8 * cm, 4 * cm])
        total_table.setStyle(TableStyle([
            # Alineación
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),

            # Estilos para el total final
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 18),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.Color(0.1, 0.5, 0.1)),

            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),

            # Línea superior para el total final
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.Color(0.1, 0.5, 0.1)),
        ]))

        elements.append(total_table)

        # Línea decorativa debajo del total
        elements.append(Spacer(1, 3 * mm))

        return elements

    def _create_footer(self, settings: Settings, client_timezone: Optional[str] = None):
        """Crea el footer con información importante"""
        elements = []

        # Spacer antes del footer
        elements.append(Spacer(1, 15 * mm))

        # Notas importantes
        elements.append(
            Paragraph(
                "INFORMACIÓN IMPORTANTE",
                self.styles['SectionTitle']))

        important_notes = [
            "• Este es una orden de pedido, NO constituye una factura fiscal.",
            "• Conserve este documento para seguimiento y referencia de su pedido.",
            "• Para facturación fiscal, solicite su factura correspondiente por separado.",
            "• Si tiene preguntas sobre su pedido, conserve el número de referencia."]

        for note in important_notes:
            elements.append(Paragraph(note, self.styles['NormalText']))

        elements.append(Spacer(1, 10 * mm))

        # Mensaje de agradecimiento
        thank_you = "¡Gracias por elegirnos! Su pedido está siendo procesado con cuidado."
        elements.append(
            Paragraph(
                f'<para align="center"><i>{thank_you}</i></para>',
                self.styles['CompanyInfo']))

        # Timestamp de generación
        if client_timezone:
            # Convert current time to client timezone
            current_time = datetime.now()
            client_time = convert_utc_to_client_timezone(current_time, client_timezone)
            timestamp = f"Orden de pedido generada el {client_time.strftime('%d de %B de %Y a las %I:%M %p')}"
        else:
            timestamp = f"Orden de pedido generada el {datetime.now().strftime('%d de %B de %Y a las %I:%M %p')}"

        elements.append(
            Paragraph(
                f'<para align="center">{timestamp}</para>',
                self.styles['CompanyInfo']))

        # Información de contacto final
        if settings.phone or settings.email:
            contact_parts = []
            if settings.phone:
                contact_parts.append(f"Tel: {settings.phone}")
            if settings.email:
                contact_parts.append(f"Email: {settings.email}")

            contact_text = " | ".join(contact_parts)
            elements.append(
                Paragraph(
                    f'<para align="center">Para consultas: {contact_text}</para>',
                    self.styles['CompanyInfo']))

        return elements

    def _format_status(self, status: str) -> str:
        """Formatea el estado del pedido en español"""
        status_translations = {
            'pending': 'Pendiente',
            'confirmed': 'Confirmado',
            'in_progress': 'En Proceso',
            'shipped': 'Enviado',
            'delivered': 'Entregado',
            'cancelled': 'Cancelado'
        }
        return status_translations.get(status.lower(), status.capitalize())
