from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, Frame, PageTemplate, NextPageTemplate
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase.pdfmetrics import stringWidth
from datetime import datetime
from typing import List, Dict, Optional
import requests
from io import BytesIO
from PIL import Image as PILImage
from collections import defaultdict

from ..models.order import Order
from ..models.settings import Settings
from ..utils.timezone import convert_utc_to_client_timezone


def format_quantity(quantity) -> str:
    """Formatea una cantidad mostrando decimales solo cuando es necesario"""
    if quantity == int(quantity):
        return f"{int(quantity):,}"
    else:
        return f"{quantity:,.2f}"


def truncate_product_text(text: str, max_width_cm: float, font_size: int = 11, font_name: str = 'Helvetica') -> str:
    """
    Trunca un texto para que quepa en un ancho máximo dado.

    Args:
        text: Texto a truncar
        max_width_cm: Ancho máximo en centímetros
        font_size: Tamaño de fuente en puntos
        font_name: Nombre de la fuente

    Returns:
        Texto truncado sin puntos suspensivos para maximizar caracteres visibles
    """
    try:
        # Convertir cm a puntos (1 cm = 28.35 puntos aproximadamente)
        max_width_pts = max_width_cm * 28.35

        # Medir el ancho del texto completo
        text_width = stringWidth(text, font_name, font_size)

        # Si el texto cabe, retornarlo completo
        if text_width <= max_width_pts:
            return text

        # Si no cabe, truncar progresivamente sin agregar "..."
        # Empezar con una estimación basada en la proporción
        estimated_chars = max(1, int(len(text) * (max_width_pts / text_width)))

        # Ajustar la estimación probando diferentes longitudes
        # Buscar desde la estimación hacia abajo
        for length in range(estimated_chars, 0, -1):
            truncated = text[:length]
            if stringWidth(truncated, font_name, font_size) <= max_width_pts:
                return truncated

        # Si incluso con un solo carácter no cabe, retornar el primer carácter
        return text[0] if len(text) > 0 else ""
    except Exception:
        # Fallback: usar truncamiento simple basado en caracteres si hay error
        # Estimación aproximada: ~10-12 caracteres por 6.3 cm con fuente 12pt
        max_chars = int(max_width_cm * 2.0)  # Aproximación conservadora ajustada para fuente 12pt
        if len(text) > max_chars:
            return text[:max_chars]
        return text


class OrdersReportGenerator:
    """Generador de reportes PDF para múltiples órdenes agrupadas por cliente"""

    def __init__(self):
        self.width, self.height = A4
        self.margin = 0.3 * cm  # Margen ultra compacto para máximo espacio
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Configura estilos optimizados para reportes de múltiples órdenes"""

        # Estilo para el título principal del reporte - más grande
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=18,  # Aumentado de 16 a 18 para mejor legibilidad
            spaceAfter=0.5,  # Mantenido
            textColor=colors.Color(0.2, 0.2, 0.2),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        # Estilo para información de empresa - ultra compacto
        self.styles.add(ParagraphStyle(
            name='CompanyInfo',
            parent=self.styles['Normal'],
            fontSize=10,  # Aumentado de 8 a 10 para mejor legibilidad
            spaceAfter=0.2,  # Reducido de 0.5 a 0.2
            textColor=colors.Color(0.3, 0.3, 0.3),
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))

        # Estilo para títulos de cliente - ultra compacto
        self.styles.add(ParagraphStyle(
            name='ClientTitle',
            parent=self.styles['Heading3'],
            fontSize=14,  # Aumentado de 12 a 14 para mejor legibilidad
            spaceBefore=1,  # Reducido de 4 a 1
            spaceAfter=1,  # Reducido de 2 a 1
            textColor=colors.Color(0.1, 0.1, 0.1),
            backgroundColor=colors.Color(0.94, 0.94, 0.94),
            borderWidth=0.5,  # Reducido de 1 a 0.5
            borderColor=colors.Color(0.7, 0.7, 0.7),
            borderPadding=1,  # Reducido de 2 a 1
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        ))

        # Estilo para información del cliente - ultra compacto
        self.styles.add(ParagraphStyle(
            name='ClientInfo',
            parent=self.styles['Normal'],
            fontSize=11,  # Aumentado de 9 a 11 para mejor legibilidad
            spaceAfter=0.2,  # Reducido de 0.5 a 0.2
            textColor=colors.Color(0.4, 0.4, 0.4),
            alignment=TA_LEFT,
            fontName='Helvetica'
        ))

        # Estilo para títulos de orden
        self.styles.add(ParagraphStyle(
            name='OrderTitle',
            parent=self.styles['Normal'],
            fontSize=12,  # Aumentado de 10 a 12 para mejor legibilidad
            spaceBefore=2,  # Reducido de 4 a 2
            spaceAfter=1,  # Reducido de 2 a 1
            textColor=colors.Color(0.2, 0.2, 0.2),
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        ))

        # Estilo para texto normal ultra compacto
        self.styles.add(ParagraphStyle(
            name='CompactText',
            parent=self.styles['Normal'],
            fontSize=12,  # Aumentado de 11 a 12 para mejor legibilidad
            spaceAfter=0.5,  # Reducido de 1 a 0.5
            spaceBefore=0.2,  # Reducido de 0.5 a 0.2
            leading=14,  # Aumentado de 13 a 14 para mejor legibilidad
            textColor=colors.Color(0.2, 0.2, 0.2),
            alignment=TA_LEFT,
            fontName='Helvetica'
        ))

        # Estilo para números de orden - tamaño original más pequeño
        self.styles.add(ParagraphStyle(
            name='OrderNumberText',
            parent=self.styles['Normal'],
            fontSize=9,  # Aumentado de 8 a 9
            spaceAfter=0.5,
            spaceBefore=0.2,
            leading=9,
            textColor=colors.Color(0.2, 0.2, 0.2),
            alignment=TA_LEFT,
            fontName='Helvetica'
        ))

        # Estilo para totales - ultra compacto
        self.styles.add(ParagraphStyle(
            name='TotalText',
            parent=self.styles['Normal'],
            fontSize=11,  # Aumentado de 9 a 11 para mejor legibilidad
            spaceBefore=0.5,  # Reducido de 1 a 0.5
            spaceAfter=0.5,  # Reducido de 1 a 0.5
            textColor=colors.Color(0.1, 0.1, 0.1),
            alignment=TA_RIGHT,
            fontName='Helvetica-Bold'
        ))

    def generate_orders_report(
            self,
            orders: List[Order],
            settings: Settings,
            output_path: str,
            title: str = "Reporte de Órdenes",
            client_timezone: Optional[str] = None) -> str:
        """Genera un reporte PDF de múltiples órdenes agrupadas por cliente"""
        # Usar BaseDocTemplate para soportar múltiples orientaciones de página
        doc = BaseDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )

        # Crear frames para portrait y landscape
        portrait_frame = Frame(
            self.margin, self.margin,
            A4[0] - 2 * self.margin, A4[1] - 2 * self.margin,
            id='portrait_frame'
        )

        landscape_size = landscape(A4)
        landscape_frame = Frame(
            self.margin, self.margin,
            landscape_size[0] - 2 * self.margin, landscape_size[1] - 2 * self.margin,
            id='landscape_frame'
        )

        # Crear templates de página
        portrait_template = PageTemplate(id='portrait', frames=[portrait_frame], pagesize=A4)
        landscape_template = PageTemplate(id='landscape', frames=[landscape_frame], pagesize=landscape_size)

        doc.addPageTemplates([portrait_template, landscape_template])

        story = []

        # Header con logo y información de empresa
        story.extend(self._create_report_header(settings, title, len(orders), client_timezone))
        # Sin espaciado adicional después del header

        # Agrupar órdenes por cliente
        orders_by_client = self._group_orders_by_client(orders)

        # Generar contenido por cliente
        for client, client_orders in orders_by_client.items():
            story.extend(self._create_client_section(client, client_orders, client_timezone))
            # Sin espaciado adicional después del header

        # Consolidado de rutas - Nueva página
        story.append(PageBreak())
        story.extend(self._create_route_consolidation_section(orders))

        # Matriz de órdenes por producto (página horizontal)
        story.append(NextPageTemplate('landscape'))
        story.append(PageBreak())
        story.extend(self._create_orders_matrix_section(orders, settings, title, client_timezone))

        # Volver a portrait para el resumen final
        story.append(NextPageTemplate('portrait'))
        story.append(PageBreak())

        # Resumen General (última página)
        story.extend(self._create_summary_section(orders))

        # Footer
        story.extend(self._create_report_footer(settings, client_timezone))

        doc.build(story)
        return output_path

    def generate_report_buffer(self, orders: List[Order], settings: Settings,
                               title: str = "Reporte de Órdenes", client_timezone: Optional[str] = None) -> BytesIO:
        """Genera el reporte y lo retorna como BytesIO buffer"""
        buffer = BytesIO()

        # Usar BaseDocTemplate para soportar múltiples orientaciones de página
        doc = BaseDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )

        # Crear frames para portrait y landscape
        portrait_frame = Frame(
            self.margin, self.margin,
            A4[0] - 2 * self.margin, A4[1] - 2 * self.margin,
            id='portrait_frame'
        )

        landscape_size = landscape(A4)
        landscape_frame = Frame(
            self.margin, self.margin,
            landscape_size[0] - 2 * self.margin, landscape_size[1] - 2 * self.margin,
            id='landscape_frame'
        )

        # Crear templates de página
        portrait_template = PageTemplate(id='portrait', frames=[portrait_frame], pagesize=A4)
        landscape_template = PageTemplate(id='landscape', frames=[landscape_frame], pagesize=landscape_size)

        doc.addPageTemplates([portrait_template, landscape_template])

        story = []

        # Header con logo y información de empresa
        story.extend(self._create_report_header(settings, title, len(orders), client_timezone))
        # Sin espaciado adicional después del header

        # Agrupar órdenes por cliente
        orders_by_client = self._group_orders_by_client(orders)

        # Generar contenido por cliente
        for client, client_orders in orders_by_client.items():
            story.extend(self._create_client_section(client, client_orders, client_timezone))
            # Sin espaciado adicional después del header

        # Consolidado de rutas - Nueva página
        story.append(PageBreak())
        story.extend(self._create_route_consolidation_section(orders))

        # Matriz de órdenes por producto (página horizontal)
        story.append(NextPageTemplate('landscape'))
        story.append(PageBreak())
        story.extend(self._create_orders_matrix_section(orders, settings, title, client_timezone))

        # Volver a portrait para el resumen final
        story.append(NextPageTemplate('portrait'))
        story.append(PageBreak())

        # Resumen General (última página)
        story.extend(self._create_summary_section(orders))

        # Footer
        story.extend(self._create_report_footer(settings, client_timezone))

        doc.build(story)
        buffer.seek(0)
        return buffer

    def _create_report_header(
            self,
            settings: Settings,
            title: str,
            total_orders: int,
            client_timezone: Optional[str] = None):
        """Crea el header del reporte con logo y información de empresa"""
        elements = []

        # Información de la empresa en formato ultra compacto - una sola línea
        company_info = f'<para align="center"><b>{settings.company_name}</b> | Tel: {settings.phone}</para>'

        # Si hay logo, crear tabla con logo e info - más compacto
        if settings.logo_url:
            try:
                logo = self._get_logo_image(
                    settings.logo_url, max_width=0.6 * cm, max_height=0.6 * cm)  # Reducido de 0.8cm a 0.6cm
                if logo:
                    header_data = [
                        [logo, Paragraph(company_info, self.styles['CompanyInfo'])]]
                    header_table = Table(
                        header_data, colWidths=[
                            1.0 * cm, 17.0 * cm])  # Ajustado para logo más pequeño
                    header_table.setStyle(TableStyle([
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                        ('ALIGN', (1, 0), (1, 0), 'LEFT'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 0),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                        # Padding mínimo para tabla de header
                        ('TOPPADDING', (0, 0), (-1, -1), 0),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
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

        # Eliminamos la línea duplicada de teléfono ya que está en company_info

        # Título del reporte - sin espaciado adicional
        elements.append(Paragraph(title.upper(), self.styles['ReportTitle']))

        # Información del reporte - solo total de órdenes
        report_info = f"Total: {total_orders} órdenes"
        elements.append(
            Paragraph(
                f'<para align="center">{report_info}</para>',
                self.styles['CompanyInfo']))

        return elements

    def _group_orders_by_client(self, orders: List[Order]) -> Dict:
        """Agrupa las órdenes por cliente, ordenadas por nombre del cliente"""
        orders_by_client = defaultdict(list)

        for order in orders:
            orders_by_client[order.client].append(order)

        # Ordenar clientes por nombre y órdenes por fecha
        sorted_clients = dict(
            sorted(
                orders_by_client.items(),
                key=lambda x: x[0].name))

        for client, client_orders in sorted_clients.items():
            client_orders.sort(key=lambda x: x.created_at, reverse=True)

        return sorted_clients

    def _create_client_section(self, client, orders: List[Order], client_timezone: Optional[str] = None):
        """Crea la sección de un cliente con todas sus órdenes"""
        elements = []

        # Título del cliente
        client_title = f"Cliente: {client.name}"
        elements.append(Paragraph(client_title, self.styles['ClientTitle']))

        # Información del cliente en una tabla compacta
        client_info_data = []
        if client.phone:
            client_info_data.append(f"Tel: {client.phone}")
        if client.address:
            client_info_data.append(f"Dir: {client.address}")

        if client_info_data:
            client_info = " | ".join(client_info_data)
            elements.append(Paragraph(client_info, self.styles['ClientInfo']))

        # Crear tabla compacta para todas las órdenes del cliente
        headers = ['No. Orden', 'Productos', 'Total']
        table_data = [headers]

        for order in orders:
            # Crear resumen compacto de productos en 2 columnas internas
            products_left = []
            products_right = []

            for i, item in enumerate(order.items):
                product_name = item.product.name
                quantity = item.quantity

                # Formato: cantidad + nombre del producto
                if hasattr(item.product, 'unit') and item.product.unit:
                    product_text = f"{format_quantity(quantity)} {item.product.unit} {product_name}"
                else:
                    product_text = f"{format_quantity(quantity)}x {product_name}"

                # Truncar el texto del producto para que quepa en la columna (7.8 cm menos padding)
                # Usamos 7.5 cm como ancho máximo para dejar margen de seguridad
                product_text = truncate_product_text(product_text, max_width_cm=7.5, font_size=13)

                # Distribuir productos en dos columnas
                if i % 2 == 0:
                    products_left.append(product_text)
                else:
                    products_right.append(product_text)

            # Crear tabla de ReportLab para las dos columnas de productos (múltiples filas)
            if products_left or products_right:
                # Crear filas para la tabla interna - cada producto en su propia fila
                internal_table_data = []

                # Determinar el número máximo de filas
                max_rows = max(len(products_left), len(products_right))

                for i in range(max_rows):
                    left_product = products_left[i] if i < len(products_left) else ""
                    right_product = products_right[i] if i < len(products_right) else ""
                    internal_table_data.append([left_product, right_product])

                # Crear tabla interna con ReportLab - columnas más anchas para evitar superposición de nombres largos
                # Ajustado para usar mejor el espacio disponible en la columna de productos (15.6 cm total)
                internal_table = Table(internal_table_data, colWidths=[7.8 * cm, 7.8 * cm])

                # Estilos para la tabla interna (solo línea divisoria central) - espaciado mínimo
                internal_table.setStyle(TableStyle([
                    # Solo línea divisoria central en todas las filas - mismo grosor que las demás líneas
                    ('LINEBEFORE', (1, 0), (1, -1), 0.5, colors.Color(0.7, 0.7, 0.7)),

                    # Padding interno ultra mínimo
                    ('LEFTPADDING', (0, 0), (-1, -1), 3),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                    ('TOPPADDING', (0, 0), (-1, -1), 0.5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5),

                    # Alineación
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),

                    # Fuente con leading reducido
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 13),  # Aumentado de 12 a 13 para mejor legibilidad
                    ('LEADING', (0, 0), (-1, -1), 14),  # Aumentado de 13 a 14 para mejor legibilidad
                ]))

                # Crear el contenido de la celda con la tabla interna
                products_content = internal_table
            else:
                products_content = Paragraph("Sin productos", self.styles['CompactText'])

            # Formatear estado
            status_text = {
                'pending': 'Pendiente',
                'confirmed': 'Confirmado',
                'in_progress': 'En proceso',
                'shipped': 'Enviado',
                'delivered': 'Entregado',
                'cancelled': 'Cancelado'
            }.get(order.status.value, order.status.value.title())

            # Convert order date to client timezone if provided
            if client_timezone:
                created_at_client = convert_utc_to_client_timezone(order.created_at, client_timezone)
            else:
                created_at_client = order.created_at

            # Crear número de orden con fecha y estado debajo
            date_str = created_at_client.strftime('%d/%m/%Y')
            order_number_with_date_status = (
                f"{order.order_number}<br/><font size='9'>{date_str}<br/>{status_text}</font>"
            )

            row = [
                Paragraph(order_number_with_date_status, self.styles['OrderNumberText']),
                products_content,
                f"Q {order.total_amount:,.2f}"
            ]
            table_data.append(row)

            # Agregar fila de nota si la orden tiene notas
            if order.notes and order.notes.strip():
                note_text = f"<b>Nota:</b> {order.notes.strip()}"
                note_row = [
                    Paragraph(note_text, self.styles['CompactText']),  # Nota empieza desde la primera columna
                    "",  # Columna Productos vacía (se unirá con SPAN)
                    ""   # Columna Total vacía
                ]
                table_data.append(note_row)

        # Crear tabla de órdenes (expandir columna de productos con 2 columnas internas) - optimizada para más espacio
        # Ajustado para dar más espacio a productos y evitar superposición de nombres largos
        # Sin columna de estado, más espacio para productos
        col_widths = [2.5 * cm, 15.6 * cm, 2.0 * cm]
        orders_table = Table(table_data, colWidths=col_widths)

        table_style = [
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.3, 0.3, 0.3)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),  # Aumentado de 9 a 11 para mejor legibilidad
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
            ('TOPPADDING', (0, 0), (-1, 0), 4),

            # Data rows - tamaño de fuente general
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 11),  # Aumentado de 9 a 11 para mejor legibilidad
            # Números de orden con tamaño aumentado un punto
            ('FONTSIZE', (0, 1), (0, -1), 9),  # No. Orden - aumentado de 8 a 9
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # No. Orden centrado
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),   # Total a la derecha
            ('VALIGN', (0, 1), (-1, -1), 'TOP'),

            # Borders
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.7, 0.7, 0.7)),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.Color(0.3, 0.3, 0.3)),

            # Padding ultra optimizado
            ('LEFTPADDING', (0, 0), (-1, -1), 1),  # Reducido de 2 a 1
            ('RIGHTPADDING', (0, 0), (-1, -1), 1),  # Reducido de 2 a 1
            ('TOPPADDING', (0, 1), (-1, -1), 1),  # Reducido de 2 a 1
            ('BOTTOMPADDING', (0, 1), (-1, -1), 1),  # Reducido de 2 a 1
        ]

        # Agregar colores alternados para las filas de órdenes (no para las filas de notas)
        # Identificar filas de notas: son las que tienen la segunda columna (Productos) vacía
        note_row_indices = []
        order_row_count = 0  # Contador de filas de órdenes (sin contar notas)

        for i in range(1, len(table_data)):
            # Si la segunda columna (Productos) está vacía, es una fila de nota
            second_cell = table_data[i][1]
            if isinstance(second_cell, str) and second_cell.strip() == "":
                note_row_indices.append(i)
            else:
                # Es una fila de orden
                order_row_count += 1
                # Aplicar color alternado solo a filas de órdenes pares
                if order_row_count % 2 == 0:
                    table_style.append(
                        ('BACKGROUND', (0, i), (-1, i), colors.Color(0.97, 0.97, 0.97)))

        # Aplicar estilo especial a las filas de notas
        for note_idx in note_row_indices:
            # Fondo más visible para notas (amarillo muy claro)
            table_style.append(
                ('BACKGROUND', (0, note_idx), (-1, note_idx), colors.Color(0.98, 0.98, 0.90)))
            # Unir las primeras 2 columnas (No. Orden, Productos) para la nota
            table_style.append(
                ('SPAN', (0, note_idx), (1, note_idx)))
            # Alineación izquierda para la nota (que está en la primera columna)
            table_style.append(
                ('ALIGN', (0, note_idx), (0, note_idx), 'LEFT'))
            # Estilo de fuente para notas
            table_style.append(
                ('FONTSIZE', (0, note_idx), (0, note_idx), 12))
            # Sin borde superior para que se vea como parte de la orden anterior
            table_style.append(
                ('LINEABOVE', (0, note_idx), (-1, note_idx), 0, colors.Color(1, 1, 1)))
            # Padding adicional para la nota
            table_style.append(
                ('TOPPADDING', (0, note_idx), (-1, note_idx), 2))
            table_style.append(
                ('BOTTOMPADDING', (0, note_idx), (-1, note_idx), 2))

        orders_table.setStyle(TableStyle(table_style))
        elements.append(orders_table)

        # Total del cliente
        client_total = sum(order.total_amount for order in orders)
        total_orders_count = len(orders)
        total_text = f"Total del cliente ({total_orders_count} órdenes): Q {client_total:,.2f}"
        elements.append(Paragraph(total_text, self.styles['TotalText']))

        return elements

    def _create_route_consolidation_section(self, orders: List[Order]):
        """Crea la sección de consolidado de rutas"""
        elements = []

        elements.append(Spacer(1, 2 * mm))
        elements.append(
            Paragraph(
                "CONSOLIDADO DE RUTAS",
                self.styles['ReportTitle']))

        # Agrupar órdenes por ruta
        orders_by_route = self._group_orders_by_route(orders)

        # Crear sección para cada ruta
        for route, route_orders in orders_by_route.items():
            elements.extend(self._create_route_section(route, route_orders))

        return elements

    def _group_orders_by_route(self, orders: List[Order]) -> Dict:
        """Agrupa las órdenes por ruta"""
        orders_by_route = defaultdict(list)

        for order in orders:
            if order.route:
                orders_by_route[order.route].append(order)
            else:
                # Si no tiene ruta, agrupar como "Sin Ruta"
                orders_by_route["Sin Ruta"].append(order)

        # Ordenar rutas por nombre
        return dict(sorted(orders_by_route.items(), key=lambda x: x[0].name if hasattr(x[0], 'name') else str(x[0])))

    def _create_route_section(self, route, orders: List[Order]):
        """Crea la sección de una ruta específica"""
        elements = []

        # Título de la ruta
        route_name = route.name if hasattr(route, 'name') else str(route)
        elements.append(Spacer(1, 3 * mm))
        elements.append(Paragraph(f"Ruta: {route_name}", self.styles['ClientTitle']))

        # Calcular rango de fechas
        dates = [order.created_at for order in orders]
        min_date = min(dates)
        max_date = max(dates)

        if min_date.date() == max_date.date():
            date_range = f"Fecha: {min_date.strftime('%d/%m/%Y')}"
        else:
            date_range = f"Período: {min_date.strftime('%d/%m/%Y')} - {max_date.strftime('%d/%m/%Y')}"

        elements.append(Paragraph(date_range, self.styles['ClientInfo']))

        # Consolidar productos de la ruta
        product_consolidation = self._consolidate_products_by_route(orders)

        if product_consolidation:
            # Crear tabla de consolidado
            headers = ['Producto', 'Total del Producto', 'Valor']
            table_data = [headers]

            for product_name, data in product_consolidation.items():
                total_quantity = data['total_quantity']
                total_value = data['total_value']
                unit = data.get('unit', 'unidades')

                # Formatear cantidad con unidad (mostrar decimales exactos)
                if unit and unit != 'unidades':
                    # Si es un número entero, mostrar sin decimales; si tiene decimales, mostrarlos
                    if total_quantity == int(total_quantity):
                        quantity_text = f"{int(total_quantity):,} {unit}"
                    else:
                        quantity_text = f"{total_quantity:,.2f} {unit}"
                else:
                    # Si es un número entero, mostrar sin decimales; si tiene decimales, mostrarlos
                    if total_quantity == int(total_quantity):
                        quantity_text = f"{int(total_quantity):,} unidades"
                    else:
                        quantity_text = f"{total_quantity:,.2f} unidades"

                table_data.append([
                    product_name,
                    quantity_text,
                    f"Q {total_value:,.2f}"
                ])

            # Crear tabla
            col_widths = [8 * cm, 4 * cm, 4 * cm]
            consolidation_table = Table(table_data, colWidths=col_widths)

            table_style = [
                # Header
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.3, 0.3, 0.3)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),  # Aumentado de 9 a 11 para mejor legibilidad
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 3),
                ('TOPPADDING', (0, 0), (-1, 0), 3),

                # Data rows
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 11),  # Aumentado de 9 a 11 para mejor legibilidad
                ('ALIGN', (1, 1), (1, -1), 'CENTER'),  # Total del Producto centrado
                ('ALIGN', (2, 1), (2, -1), 'RIGHT'),   # Valor a la derecha
                ('VALIGN', (0, 1), (-1, -1), 'TOP'),

                # Borders
                ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.7, 0.7, 0.7)),
                ('LINEBELOW', (0, 0), (-1, 0), 1, colors.Color(0.3, 0.3, 0.3)),

                # Padding optimizado
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 1), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 2),
            ]

            # Agregar colores alternados para las filas
            for i in range(1, len(table_data)):
                if i % 2 == 0:
                    table_style.append(
                        ('BACKGROUND', (0, i), (-1, i), colors.Color(0.97, 0.97, 0.97)))

            consolidation_table.setStyle(TableStyle(table_style))
            elements.append(consolidation_table)

            # Total de la ruta
            route_total = sum(data['total_value'] for data in product_consolidation.values())
            total_products = len(product_consolidation)
            total_text = f"Total de la ruta ({total_products} productos): Q {route_total:,.2f}"
            elements.append(Paragraph(total_text, self.styles['TotalText']))

        return elements

    def _consolidate_products_by_route(self, orders: List[Order]) -> Dict:
        """Consolida productos por ruta, sumando cantidades y valores"""
        product_consolidation = {}

        for order in orders:
            for item in order.items:
                product_name = item.product.name
                quantity = item.quantity
                unit_price = item.unit_price
                subtotal = float(quantity) * unit_price
                unit = getattr(item.product, 'unit', 'unidades')

                if product_name not in product_consolidation:
                    product_consolidation[product_name] = {
                        'total_quantity': 0.0,  # Cambiar a float para compatibilidad con Decimal
                        'total_value': 0.0,
                        'unit': unit
                    }

                product_consolidation[product_name]['total_quantity'] += float(quantity)
                product_consolidation[product_name]['total_value'] += subtotal

        # Ordenar por nombre del producto
        return dict(sorted(product_consolidation.items()))

    def _create_summary_section(self, orders: List[Order]):
        """Crea la sección de resumen general"""
        elements = []

        elements.append(Spacer(1, 2 * mm))
        elements.append(
            Paragraph(
                "RESUMEN GENERAL",
                self.styles['ReportTitle']))

        # Resumen por estado
        status_summary = defaultdict(int)
        status_totals = defaultdict(float)

        for order in orders:
            status_summary[order.status.value] += 1
            status_totals[order.status.value] += order.total_amount

        # Crear tabla de resumen
        summary_headers = ['Estado', 'Cantidad', 'Total']
        summary_data = [summary_headers]

        status_names = {
            'pending': 'Pendientes',
            'confirmed': 'Confirmados',
            'in_progress': 'En Proceso',
            'shipped': 'Enviados',
            'delivered': 'Entregados',
            'cancelled': 'Cancelados'
        }

        for status, count in status_summary.items():
            status_name = status_names.get(status, status.title())
            total = status_totals[status]
            summary_data.append([status_name, f"{count:,}", f"Q {total:,.2f}"])

        # Total general
        total_orders = len(orders)
        grand_total = sum(order.total_amount for order in orders)
        summary_data.append(['', '', ''])  # Separador
        summary_data.append(
            ['TOTAL GENERAL', f"{total_orders:,}", f"Q {grand_total:,.2f}"])

        summary_table = Table(summary_data, colWidths=[8 * cm, 4 * cm, 4 * cm])
        summary_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.3, 0.3, 0.3)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),  # Aumentado de 10 a 12 para mejor legibilidad
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

            # Data rows
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 12),  # Aumentado de 10 a 12 para mejor legibilidad
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),

            # Total row
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 13),  # Aumentado de 11 a 13 para mejor legibilidad
            ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.9, 0.9, 0.9)),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.Color(0.3, 0.3, 0.3)),

            # Borders
            ('GRID', (0, 0), (-1, -2), 0.5, colors.Color(0.7, 0.7, 0.7)),
            ('BOX', (0, -1), (-1, -1), 1, colors.Color(0.3, 0.3, 0.3)),

            # Padding optimizado
            ('LEFTPADDING', (0, 0), (-1, -1), 4),  # Reducido de 6 a 4
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),  # Reducido de 6 a 4
            ('TOPPADDING', (0, 0), (-1, -1), 3),  # Reducido de 4 a 3
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),  # Reducido de 4 a 3
        ]))

        elements.append(summary_table)

        return elements

    def _create_report_footer(self, settings: Settings, client_timezone: Optional[str] = None):
        """Crea el footer del reporte"""
        elements = []

        elements.append(Spacer(1, 3 * mm))  # Reducido de 6mm a 3mm

        # Footer con información de contacto y timestamp
        current_time = datetime.now()
        if client_timezone:
            from ..utils.timezone import convert_utc_to_client_timezone
            current_time = convert_utc_to_client_timezone(current_time, client_timezone)
        footer_parts = [
            f"Generado: {current_time.strftime('%d/%m/%Y %H:%M')}"]

        if settings.phone:
            footer_parts.append(f"Tel: {settings.phone}")
        if settings.email:
            footer_parts.append(settings.email)
        if settings.website:
            footer_parts.append(settings.website)

        footer_text = " | ".join(footer_parts)
        elements.append(
            Paragraph(
                f'<para align="center">{footer_text}</para>',
                self.styles['CompanyInfo']))

        return elements

    def _get_logo_image(
            self,
            logo_url: str,
            max_width=0.6 * cm,
            max_height=0.6 * cm):
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

    def _wrap_product_name(self, name: str, max_chars_per_line: int, max_lines: int = 3) -> str:
        """
        Divide el nombre del producto en múltiples líneas.
        Si excede max_lines, corta en la última línea con '…'
        """
        words = name.split()
        lines = []
        current_line = ""

        for word in words:
            # Si la palabra sola es más larga que el máximo, cortarla
            if len(word) > max_chars_per_line:
                if current_line:
                    lines.append(current_line.strip())
                    current_line = ""
                # Cortar la palabra larga
                while len(word) > max_chars_per_line:
                    lines.append(word[:max_chars_per_line - 1] + "-")
                    word = word[max_chars_per_line - 1:]
                if word:
                    current_line = word + " "
            elif len(current_line) + len(word) <= max_chars_per_line:
                current_line += word + " "
            else:
                lines.append(current_line.strip())
                current_line = word + " "

        if current_line.strip():
            lines.append(current_line.strip())

        # Limitar a max_lines
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            # Truncar la última línea si es necesario
            if len(lines[-1]) > max_chars_per_line - 1:
                lines[-1] = lines[-1][:max_chars_per_line - 1] + "…"
            else:
                lines[-1] = lines[-1] + "…"

        return "<br/>".join(lines)

    def _create_orders_matrix_section(
            self,
            orders: List[Order],
            settings: Settings,
            title: str = "Reporte de Órdenes",
            client_timezone: Optional[str] = None):
        """
        Crea una tabla matriz/pivot con órdenes como filas y productos como columnas.
        Cada celda muestra la cantidad pedida de ese producto en esa orden.
        """
        elements = []

        # Header con logo y información de empresa (mismo que la primera página)
        # Reemplazar "Reporte de Órdenes" por "Venta Diaria" en el título
        matrix_title = title.replace("Reporte de Órdenes", "Venta Diaria")
        elements.extend(self._create_report_header(
            settings,
            matrix_title,
            len(orders),
            client_timezone
        ))
        elements.append(Spacer(1, 3 * mm))

        # Recolectar todos los productos únicos de todas las órdenes
        all_products = {}  # {product_id: product_name}
        for order in orders:
            for item in order.items:
                if item.product.id not in all_products:
                    all_products[item.product.id] = item.product.name

        # Ordenar productos alfabéticamente por nombre (case-insensitive)
        sorted_products = sorted(all_products.items(), key=lambda x: x[1].lower())
        product_ids = [p[0] for p in sorted_products]
        product_names = [p[1] for p in sorted_products]

        # Calcular ancho disponible para la página landscape
        landscape_width = landscape(A4)[0] - 2 * self.margin

        # Calcular anchos de columnas dinámicamente
        num_products = len(product_names)
        first_col_width = 3.5 * cm   # Cliente + No. Orden
        total_col_width = 2.2 * cm   # Total
        payment_date_col_width = 2.0 * cm  # Pago Fecha
        balance_col_width = 2.0 * cm  # Saldo

        # Espacio disponible para columnas de productos
        fixed_cols_width = first_col_width + total_col_width + payment_date_col_width + balance_col_width
        available_for_products = landscape_width - fixed_cols_width

        if num_products > 0:
            # Ancho mínimo y máximo por columna de producto
            min_product_col_width = 1.5 * cm
            max_product_col_width = 3.5 * cm

            product_col_width = available_for_products / num_products
            product_col_width = max(min_product_col_width, min(product_col_width, max_product_col_width))

            # Si no caben todos los productos, ajustar
            if product_col_width * num_products > available_for_products:
                product_col_width = available_for_products / num_products
        else:
            product_col_width = 2 * cm

        # Calcular caracteres por línea aproximados para los encabezados de productos
        chars_per_line = max(5, int(product_col_width / (0.20 * cm)))

        # Crear estilo para encabezados de productos (multi-línea)
        header_style = ParagraphStyle(
            'MatrixHeader',
            parent=self.styles['Normal'],
            fontSize=7,
            leading=8,
            alignment=TA_CENTER,
            textColor=colors.whitesmoke,
            fontName='Helvetica-Bold'
        )

        # Crear estilo para la primera columna (cliente + orden)
        client_order_style = ParagraphStyle(
            'ClientOrderCell',
            parent=self.styles['Normal'],
            fontSize=8,
            leading=10,
            alignment=TA_LEFT,
            textColor=colors.Color(0.1, 0.1, 0.1),
            fontName='Helvetica'
        )

        # Crear encabezados con nombres de productos en múltiples líneas
        header_paragraphs = [Paragraph('<b>Cliente<br/>No. Orden</b>', header_style)]
        for name in product_names:
            wrapped_name = self._wrap_product_name(name, chars_per_line, max_lines=3)
            header_paragraphs.append(Paragraph(f'<b>{wrapped_name}</b>', header_style))
        header_paragraphs.append(Paragraph('<b>Total</b>', header_style))
        header_paragraphs.append(Paragraph('<b>Fecha<br/>Pago</b>', header_style))
        header_paragraphs.append(Paragraph('<b>Saldo</b>', header_style))

        table_data = [header_paragraphs]

        # Crear mapa de producto_id -> índice de columna
        product_col_index = {pid: idx for idx, pid in enumerate(product_ids)}

        # Ordenar órdenes por nombre de cliente
        sorted_orders = sorted(orders, key=lambda o: o.client.name)

        # Inicializar totales por producto (para la fila de totales)
        product_totals = [0.0] * num_products

        # Estilo para la nota con fondo amarillo
        note_style = ParagraphStyle(
            'MatrixNoteStyle',
            parent=self.styles['Normal'],
            fontSize=6,
            leading=7,
            alignment=TA_LEFT,
            textColor=colors.Color(0.1, 0.1, 0.1),
            fontName='Helvetica'
        )

        # Crear filas para cada orden
        for order in sorted_orders:
            # Primera columna: Cliente (nombre arriba) + No. Orden (abajo, más pequeño)
            client_order_text = (
                f"<b>{order.client.name}</b><br/>"
                f"<font size='6' color='#666666'>{order.order_number}</font>"
            )

            # Si hay nota, crear una tabla anidada con fondo amarillo para la nota
            if order.notes and order.notes.strip():
                # Truncar nota si es muy larga (máximo ~50 caracteres)
                note = order.notes.strip()
                if len(note) > 50:
                    note = note[:47] + "..."

                # Crear tabla interna: fila 1 = cliente+orden, fila 2 = nota con fondo
                inner_data = [
                    [Paragraph(client_order_text, client_order_style)],
                    [Paragraph(f"<b>Nota:</b> {note}", note_style)]
                ]
                inner_table = Table(inner_data, colWidths=[first_col_width - 6])
                inner_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                    # Fondo amarillo claro solo para la fila de la nota
                    ('BACKGROUND', (0, 1), (-1, 1), colors.Color(0.98, 0.98, 0.90)),
                ]))
                first_cell = inner_table
            else:
                # Sin nota, solo el texto normal
                first_cell = Paragraph(client_order_text, client_order_style)

            # Crear fila
            row = [first_cell]

            # Inicializar cantidades de productos como vacías
            product_quantities = [''] * num_products

            # Llenar cantidades de productos que están en esta orden
            for item in order.items:
                col_idx = product_col_index.get(item.product.id)
                if col_idx is not None:
                    quantity = float(item.quantity)
                    product_quantities[col_idx] = format_quantity(item.quantity)
                    product_totals[col_idx] += quantity

            row.extend(product_quantities)

            # Columna Total de la orden
            row.append(f"Q {order.total_amount:,.2f}")

            # Columnas Pago Fecha y Saldo (vacías para llenar a mano)
            row.append('')
            row.append('')

            table_data.append(row)

        # Agregar fila de totales al final
        totals_row_style = ParagraphStyle(
            'TotalsRowCell',
            parent=self.styles['Normal'],
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.Color(0.1, 0.1, 0.1),
            fontName='Helvetica-Bold'
        )

        totals_row = [Paragraph('<b>TOTALES</b>', totals_row_style)]
        for total in product_totals:
            if total > 0:
                totals_row.append(Paragraph(f'<b>{format_quantity(total)}</b>', totals_row_style))
            else:
                totals_row.append('')

        # Total general de todas las órdenes
        grand_total = sum(order.total_amount for order in orders)
        totals_row.append(Paragraph(f'<b>Q {grand_total:,.2f}</b>', totals_row_style))

        # Columnas Pago Fecha y Saldo en totales (vacías)
        totals_row.append('')
        totals_row.append('')

        table_data.append(totals_row)

        # Calcular anchos de columnas
        col_widths = ([first_col_width] +
                      [product_col_width] * num_products +
                      [total_col_width, payment_date_col_width, balance_col_width])

        # Crear la tabla
        matrix_table = Table(table_data, colWidths=col_widths)

        # Índice de la fila de totales
        totals_row_idx = len(table_data) - 1

        # Estilo de la tabla (mismo diseño que las tablas de arriba)
        table_style = [
            # Header - mismo estilo que las otras tablas
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.3, 0.3, 0.3)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
            ('TOPPADDING', (0, 0), (-1, 0), 4),

            # Data rows (excluyendo la fila de totales)
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 9),
            ('ALIGN', (0, 1), (0, -2), 'LEFT'),  # Cliente/Orden a la izquierda
            ('ALIGN', (1, 1), (-2, -2), 'CENTER'),  # Cantidades centradas
            ('ALIGN', (-1, 1), (-1, -2), 'RIGHT'),  # Total a la derecha
            ('VALIGN', (0, 1), (-1, -2), 'TOP'),

            # Fila de totales - mismo estilo gris que el header
            ('BACKGROUND', (0, totals_row_idx), (-1, totals_row_idx), colors.Color(0.9, 0.9, 0.9)),
            ('FONTNAME', (0, totals_row_idx), (-1, totals_row_idx), 'Helvetica-Bold'),
            ('ALIGN', (0, totals_row_idx), (-1, totals_row_idx), 'CENTER'),
            ('VALIGN', (0, totals_row_idx), (-1, totals_row_idx), 'MIDDLE'),
            ('LINEABOVE', (0, totals_row_idx), (-1, totals_row_idx), 1, colors.Color(0.3, 0.3, 0.3)),
            ('TOPPADDING', (0, totals_row_idx), (-1, totals_row_idx), 4),
            ('BOTTOMPADDING', (0, totals_row_idx), (-1, totals_row_idx), 4),

            # Borders - mismo estilo que las otras tablas
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.7, 0.7, 0.7)),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.Color(0.3, 0.3, 0.3)),

            # Padding - mismo que las otras tablas
            ('LEFTPADDING', (0, 0), (-1, -1), 1),
            ('RIGHTPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 1), (-1, -2), 1),
            ('BOTTOMPADDING', (0, 1), (-1, -2), 1),
        ]

        # Agregar colores alternados para las filas de datos (no header ni totales)
        for i in range(1, totals_row_idx):
            if i % 2 == 0:
                table_style.append(
                    ('BACKGROUND', (0, i), (-1, i), colors.Color(0.97, 0.97, 0.97)))

        # Columna de totales en negrita
        table_style.append(
            ('FONTNAME', (-1, 1), (-1, -2), 'Helvetica-Bold'))

        matrix_table.setStyle(TableStyle(table_style))
        elements.append(matrix_table)

        return elements
