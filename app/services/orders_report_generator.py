from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from datetime import datetime
from typing import List, Dict
import requests
from io import BytesIO
from PIL import Image as PILImage
from collections import defaultdict

from ..models.order import Order
from ..models.settings import Settings


class OrdersReportGenerator:
    """Generador de reportes PDF para múltiples órdenes agrupadas por cliente"""

    def __init__(self):
        self.width, self.height = A4
        self.margin = 1.2 * cm  # Margen reducido para más espacio
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Configura estilos optimizados para reportes de múltiples órdenes"""

        # Estilo para el título principal del reporte
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=6,
            textColor=colors.Color(0.2, 0.2, 0.2),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        # Estilo para información de empresa
        self.styles.add(ParagraphStyle(
            name='CompanyInfo',
            parent=self.styles['Normal'],
            fontSize=8,
            spaceAfter=2,
            textColor=colors.Color(0.3, 0.3, 0.3),
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))

        # Estilo para títulos de cliente
        self.styles.add(ParagraphStyle(
            name='ClientTitle',
            parent=self.styles['Heading3'],
            fontSize=12,
            spaceBefore=8,
            spaceAfter=4,
            textColor=colors.Color(0.1, 0.1, 0.1),
            backgroundColor=colors.Color(0.94, 0.94, 0.94),
            borderWidth=1,
            borderColor=colors.Color(0.7, 0.7, 0.7),
            borderPadding=4,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        ))

        # Estilo para información del cliente
        self.styles.add(ParagraphStyle(
            name='ClientInfo',
            parent=self.styles['Normal'],
            fontSize=8,
            spaceAfter=1,
            textColor=colors.Color(0.4, 0.4, 0.4),
            alignment=TA_LEFT,
            fontName='Helvetica'
        ))

        # Estilo para títulos de orden
        self.styles.add(ParagraphStyle(
            name='OrderTitle',
            parent=self.styles['Normal'],
            fontSize=9,
            spaceBefore=4,
            spaceAfter=2,
            textColor=colors.Color(0.2, 0.2, 0.2),
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        ))

        # Estilo para texto normal compacto
        self.styles.add(ParagraphStyle(
            name='CompactText',
            parent=self.styles['Normal'],
            fontSize=8,
            spaceAfter=1,
            textColor=colors.Color(0.2, 0.2, 0.2),
            alignment=TA_LEFT,
            fontName='Helvetica'
        ))

        # Estilo para totales
        self.styles.add(ParagraphStyle(
            name='TotalText',
            parent=self.styles['Normal'],
            fontSize=9,
            spaceBefore=2,
            spaceAfter=2,
            textColor=colors.Color(0.1, 0.1, 0.1),
            alignment=TA_RIGHT,
            fontName='Helvetica-Bold'
        ))

    def generate_orders_report(
            self,
            orders: List[Order],
            settings: Settings,
            output_path: str,
            title: str = "Reporte de Órdenes") -> str:
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
        story.extend(self._create_report_header(settings, title, len(orders)))
        story.append(Spacer(1, 6 * mm))

        # Agrupar órdenes por cliente
        orders_by_client = self._group_orders_by_client(orders)

        # Generar contenido por cliente
        for client, client_orders in orders_by_client.items():
            story.extend(self._create_client_section(client, client_orders))
            story.append(Spacer(1, 4 * mm))

        # Resumen final
        story.extend(self._create_summary_section(orders))
        story.append(Spacer(1, 4 * mm))

        # Footer
        story.extend(self._create_report_footer(settings))

        doc.build(story)
        return output_path

    def generate_report_buffer(self, orders: List[Order], settings: Settings,
                               title: str = "Reporte de Órdenes") -> BytesIO:
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
        story.extend(self._create_report_header(settings, title, len(orders)))
        story.append(Spacer(1, 6 * mm))

        # Agrupar órdenes por cliente
        orders_by_client = self._group_orders_by_client(orders)

        # Generar contenido por cliente
        for client, client_orders in orders_by_client.items():
            story.extend(self._create_client_section(client, client_orders))
            story.append(Spacer(1, 4 * mm))

        # Resumen final
        story.extend(self._create_summary_section(orders))
        story.append(Spacer(1, 4 * mm))

        # Footer
        story.extend(self._create_report_footer(settings))

        doc.build(story)
        buffer.seek(0)
        return buffer

    def _create_report_header(
            self,
            settings: Settings,
            title: str,
            total_orders: int):
        """Crea el header del reporte con logo y información de empresa"""
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
                    settings.logo_url, max_width=2.2 * cm, max_height=2.2 * cm)
                if logo:
                    header_data = [
                        [logo, Paragraph(company_info, self.styles['Normal'])]]
                    header_table = Table(
                        header_data, colWidths=[
                            2.8 * cm, 14 * cm])
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

        # Información de contacto
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

        # Título del reporte
        elements.append(Spacer(1, 4 * mm))
        elements.append(Paragraph(title.upper(), self.styles['ReportTitle']))

        # Información del reporte
        report_info = f"Total de órdenes: {total_orders} | Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
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

    def _create_client_section(self, client, orders: List[Order]):
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
        headers = ['No. Orden', 'Fecha', 'Estado', 'Productos', 'Total']
        table_data = [headers]

        for order in orders:
            # Crear resumen compacto de productos
            products_summary = []
            for item in order.items:
                product_name = item.product.name if len(
                    item.product.name) <= 20 else item.product.name[:17] + "..."
                products_summary.append(f"{item.quantity}x {product_name}")

            # Limitar productos mostrados para mantener el diseño compacto
            if len(products_summary) > 3:
                shown_products = products_summary[:3]
                shown_products.append(f"... y {len(products_summary) - 3} más")
                products_text = "\n".join(shown_products)
            else:
                products_text = "\n".join(products_summary)

            # Formatear estado
            status_text = {
                'pending': 'Pendiente',
                'confirmed': 'Confirmado',
                'in_progress': 'En proceso',
                'shipped': 'Enviado',
                'delivered': 'Entregado',
                'cancelled': 'Cancelado'
            }.get(order.status.value, order.status.value.title())

            row = [
                order.order_number,
                order.created_at.strftime('%d/%m/%Y'),
                status_text,
                Paragraph(products_text, self.styles['CompactText']),
                f"Q {order.total_amount:,.2f}"
            ]
            table_data.append(row)

        # Crear tabla de órdenes
        col_widths = [3.2 * cm, 2.2 * cm, 2.2 * cm, 6.5 * cm, 2.5 * cm]
        orders_table = Table(table_data, colWidths=col_widths)

        table_style = [
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.3, 0.3, 0.3)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
            ('TOPPADDING', (0, 0), (-1, 0), 4),

            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (1, -1), 'CENTER'),  # No. Orden y Fecha centrados
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Estado centrado
            ('ALIGN', (4, 1), (4, -1), 'RIGHT'),   # Total a la derecha
            ('VALIGN', (0, 1), (-1, -1), 'TOP'),

            # Borders
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.7, 0.7, 0.7)),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.Color(0.3, 0.3, 0.3)),

            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 1), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
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

    def _create_summary_section(self, orders: List[Order]):
        """Crea la sección de resumen general"""
        elements = []

        # Línea separadora
        line_table = Table([['', '']], colWidths=[16 * cm])
        line_table.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, -1), 2, colors.Color(0.4, 0.4, 0.4)),
        ]))
        elements.append(line_table)

        elements.append(Spacer(1, 3 * mm))
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
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

            # Data rows
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 9),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),

            # Total row
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 11),
            ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.9, 0.9, 0.9)),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.Color(0.3, 0.3, 0.3)),

            # Borders
            ('GRID', (0, 0), (-1, -2), 0.5, colors.Color(0.7, 0.7, 0.7)),
            ('BOX', (0, -1), (-1, -1), 1, colors.Color(0.3, 0.3, 0.3)),

            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        elements.append(summary_table)

        return elements

    def _create_report_footer(self, settings: Settings):
        """Crea el footer del reporte"""
        elements = []

        elements.append(Spacer(1, 6 * mm))

        # Footer con información de contacto y timestamp
        footer_parts = [
            f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"]

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
            max_width=2.2 * cm,
            max_height=2.2 * cm):
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
