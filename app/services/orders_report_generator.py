from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
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
        Texto truncado con "..." si es necesario
    """
    try:
        # Convertir cm a puntos (1 cm = 28.35 puntos aproximadamente)
        max_width_pts = max_width_cm * 28.35
        
        # Medir el ancho del texto completo
        text_width = stringWidth(text, font_name, font_size)
        
        # Si el texto cabe, retornarlo completo
        if text_width <= max_width_pts:
            return text
        
        # Si no cabe, truncar progresivamente
        # Empezar con una estimación basada en la proporción
        estimated_chars = max(1, int(len(text) * (max_width_pts / text_width)))
        
        # Ajustar la estimación probando diferentes longitudes
        # Buscar desde la estimación hacia abajo
        for length in range(estimated_chars, 0, -1):
            truncated = text[:length] + "..."
            if stringWidth(truncated, font_name, font_size) <= max_width_pts:
                return truncated
        
        # Si incluso con un solo carácter no cabe, retornar "..."
        return "..."
    except Exception:
        # Fallback: usar truncamiento simple basado en caracteres si hay error
        # Estimación aproximada: ~12-15 caracteres por 6.3 cm con fuente 11pt
        max_chars = int(max_width_cm * 2.2)  # Aproximación conservadora
        if len(text) > max_chars:
            return text[:max_chars - 3] + "..."
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
            fontSize=10,  # Aumentado de 8 a 10 para mejor legibilidad
            spaceAfter=0.5,  # Reducido de 1 a 0.5
            spaceBefore=0.2,  # Reducido de 0.5 a 0.2
            leading=12,  # Aumentado de 8 a 12 para mejor legibilidad
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
        story.extend(self._create_report_header(settings, title, len(orders), client_timezone))
        # Sin espaciado adicional después del header

        # Agrupar órdenes por cliente
        orders_by_client = self._group_orders_by_client(orders)

        # Generar contenido por cliente
        for client, client_orders in orders_by_client.items():
            story.extend(self._create_client_section(client, client_orders, client_timezone))
            # Sin espaciado adicional después del header

        # Consolidado de rutas (antes del resumen general) - Nueva página
        story.append(PageBreak())  # Salto de página para empezar en página nueva
        story.extend(self._create_route_consolidation_section(orders))
        # Sin espaciado adicional después del header

        # Resumen final
        story.extend(self._create_summary_section(orders))
        # Sin espaciado adicional después del header

        # Footer
        story.extend(self._create_report_footer(settings, client_timezone))

        doc.build(story)
        return output_path

    def generate_report_buffer(self, orders: List[Order], settings: Settings,
                               title: str = "Reporte de Órdenes", client_timezone: Optional[str] = None) -> BytesIO:
        """Genera el reporte y lo retorna como BytesIO buffer"""
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
        story.extend(self._create_report_header(settings, title, len(orders), client_timezone))
        # Sin espaciado adicional después del header

        # Agrupar órdenes por cliente
        orders_by_client = self._group_orders_by_client(orders)

        # Generar contenido por cliente
        for client, client_orders in orders_by_client.items():
            story.extend(self._create_client_section(client, client_orders, client_timezone))
            # Sin espaciado adicional después del header

        # Consolidado de rutas (antes del resumen general) - Nueva página
        story.append(PageBreak())  # Salto de página para empezar en página nueva
        story.extend(self._create_route_consolidation_section(orders))
        # Sin espaciado adicional después del header

        # Resumen final
        story.extend(self._create_summary_section(orders))
        # Sin espaciado adicional después del header

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
        headers = ['No. Orden', 'Estado', 'Productos', 'Total']
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

                # Truncar el texto del producto para que quepa en la columna (6.65 cm menos padding)
                # Usamos 6.3 cm como ancho máximo para dejar margen de seguridad
                product_text = truncate_product_text(product_text, max_width_cm=6.3, font_size=11)

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
                # Ajustado para usar mejor el espacio disponible en la columna de productos (13.3 cm total)
                internal_table = Table(internal_table_data, colWidths=[6.65 * cm, 6.65 * cm])

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
                    ('FONTSIZE', (0, 0), (-1, -1), 11),  # Aumentado de 9 a 11 para mejor legibilidad
                    ('LEADING', (0, 0), (-1, -1), 12),  # Aumentado de 10 a 12 para mejor legibilidad
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

            # Crear número de orden con fecha debajo
            order_number_with_date = f"{order.order_number}<br/><font size='9'>{created_at_client.strftime('%d/%m/%Y')}</font>"

            row = [
                Paragraph(order_number_with_date, self.styles['OrderNumberText']),
                status_text,
                products_content,
                f"Q {order.total_amount:,.2f}"
            ]
            table_data.append(row)

        # Crear tabla de órdenes (expandir columna de productos con 2 columnas internas) - optimizada para más espacio
        # Ajustado para dar más espacio a productos y evitar superposición de nombres largos
        col_widths = [2.7 * cm, 1.8 * cm, 13.3 * cm, 2.0 * cm]
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
            # Números de orden y estado con tamaño aumentado un punto
            ('FONTSIZE', (0, 1), (0, -1), 9),  # No. Orden - aumentado de 8 a 9
            ('FONTSIZE', (1, 1), (1, -1), 10),  # Estado - aumentado de 9 a 10
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # No. Orden centrado
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),  # Estado centrado
            ('ALIGN', (3, 1), (3, -1), 'RIGHT'),   # Total a la derecha
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

        # Agregar colores alternados para las filas
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                table_style.append(
                    ('BACKGROUND', (0, i), (-1, i), colors.Color(0.97, 0.97, 0.97)))

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

        # Salto de página antes del resumen general
        elements.append(PageBreak())

        elements.append(Spacer(1, 2 * mm))  # Reducido de 3mm a 2mm
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
