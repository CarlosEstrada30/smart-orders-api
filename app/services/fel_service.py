"""
FEL (Facturación Electrónica en Línea) Service for Guatemala
Handles electronic invoicing with SAT through certified providers
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
import logging
import xml.etree.ElementTree as ET
import requests
import uuid
from io import StringIO

from ..repositories.invoice_repository import InvoiceRepository
from ..models.invoice import Invoice, InvoiceStatus
from ..schemas.invoice import FELConfiguration, FELProcessResponse
from ..config import settings

# Configure logging
logger = logging.getLogger(__name__)


class FELService:
    """Service for handling FEL (Electronic Invoice) processing in Guatemala"""
    
    def __init__(self):
        self.invoice_repository = InvoiceRepository()
        self.fel_storage_path = "invoices/fel_xml"  # Configurable
        
        # Default FEL configurations - should be in config/env vars
        self.fel_configs = {
            "digifact": FELConfiguration(
                certifier_name="Digifact",
                base_url="https://felgtaws.digifact.com.gt",
                username=getattr(settings, 'FEL_DIGIFACT_USERNAME', 'test_user'),
                password=getattr(settings, 'FEL_DIGIFACT_PASSWORD', 'test_password'),
                nit_empresa=getattr(settings, 'COMPANY_NIT', '12345678-9'),
                environment=getattr(settings, 'FEL_ENVIRONMENT', 'test')
            ),
            "facturasgt": FELConfiguration(
                certifier_name="FacturasGT", 
                base_url="https://ws.facturasgt.com",
                username=getattr(settings, 'FEL_FACTURASGT_USERNAME', 'test_user'),
                password=getattr(settings, 'FEL_FACTURASGT_PASSWORD', 'test_password'),
                nit_empresa=getattr(settings, 'COMPANY_NIT', '12345678-9'),
                environment=getattr(settings, 'FEL_ENVIRONMENT', 'test')
            )
        }
        
        # Ensure FEL storage directory exists
        import os
        os.makedirs(self.fel_storage_path, exist_ok=True)

    def process_fel_authorization(self, db: Session, invoice_id: int, certifier: str = "digifact") -> FELProcessResponse:
        """Process FEL authorization for an invoice"""
        
        invoice = self.invoice_repository.get(db, invoice_id)
        if not invoice:
            return FELProcessResponse(
                success=False,
                invoice_id=invoice_id,
                status=InvoiceStatus.FEL_REJECTED,
                error_message="Invoice not found",
                processed_at=datetime.now()
            )
        
        # Check if invoice requires FEL
        if not invoice.requires_fel:
            return FELProcessResponse(
                success=False,
                invoice_id=invoice_id,
                status=invoice.status,
                error_message="Invoice does not require FEL processing",
                processed_at=datetime.now()
            )
        
        # Check if already processed
        if invoice.fel_uuid and invoice.status == InvoiceStatus.FEL_AUTHORIZED:
            return FELProcessResponse(
                success=True,
                invoice_id=invoice_id,
                status=InvoiceStatus.FEL_AUTHORIZED,
                fel_uuid=invoice.fel_uuid,
                dte_number=invoice.dte_number,
                fel_series=invoice.fel_series,
                fel_number=invoice.fel_number,
                processed_at=invoice.fel_authorization_date or datetime.now(),
                certifier=invoice.fel_certifier
            )
        
        try:
            # Keep status as DRAFT but mark FEL processing started
            # Update FEL fields to track processing without changing main status
            self.invoice_repository.update(db, db_obj=invoice, obj_in={
                "fel_error_message": "FEL processing started",
                "fel_certifier": certifier
            })
            db.commit()
            
            # Generate FEL XML
            fel_xml = self._generate_fel_xml(invoice)
            
            # Save XML to storage
            xml_filename = f"invoice_{invoice.invoice_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
            xml_path = f"{self.fel_storage_path}/{xml_filename}"
            with open(xml_path, 'w', encoding='utf-8') as f:
                f.write(fel_xml)
            
            # Send to FEL certifier
            fel_response = self._send_to_fel_certifier(fel_xml, certifier)
            
            if fel_response["success"]:
                # Update invoice with FEL data and change status to ISSUED (FEL authorized)
                fel_data = {
                    "fel_uuid": fel_response["uuid"],
                    "dte_number": fel_response["dte_number"],
                    "fel_authorization_date": datetime.now(),
                    "fel_certification_date": datetime.now(),
                    "fel_certifier": certifier,
                    "fel_series": fel_response.get("series"),
                    "fel_number": fel_response.get("number"),
                    "fel_xml_path": xml_path,
                    "fel_error_message": None  # Clear any previous errors
                }
                
                # Update FEL fields
                self.invoice_repository.update(db, db_obj=invoice, obj_in=fel_data)
                # Update status to ISSUED (FEL authorized and ready)
                self.invoice_repository.update_invoice_status(db, invoice_id=invoice_id, status=InvoiceStatus.ISSUED)
                db.commit()
                
                return FELProcessResponse(
                    success=True,
                    invoice_id=invoice_id,
                    status=InvoiceStatus.ISSUED,
                    fel_uuid=fel_response["uuid"],
                    dte_number=fel_response["dte_number"],
                    fel_series=fel_response.get("series"),
                    fel_number=fel_response.get("number"),
                    processed_at=datetime.now(),
                    certifier=certifier
                )
            else:
                # Update invoice with error but keep status as DRAFT
                error_data = {
                    "fel_error_message": fel_response["error"]
                }
                
                self.invoice_repository.update(db, db_obj=invoice, obj_in=error_data)
                db.commit()
                
                return FELProcessResponse(
                    success=False,
                    invoice_id=invoice_id,
                    status=InvoiceStatus.DRAFT,
                    error_message=fel_response["error"],
                    processed_at=datetime.now(),
                    certifier=certifier
                )
                
        except Exception as e:
            logger.error(f"Error processing FEL for invoice {invoice_id}: {str(e)}")
            
            # Update with error message but keep status as DRAFT for retry
            error_data = {
                "fel_error_message": f"Processing error: {str(e)}"
            }
            
            self.invoice_repository.update(db, db_obj=invoice, obj_in=error_data)
            db.commit()
            
            return FELProcessResponse(
                success=False,
                invoice_id=invoice_id,
                status=InvoiceStatus.DRAFT,
                error_message=f"Processing error: {str(e)}",
                processed_at=datetime.now(),
                certifier=certifier
            )

    def _generate_fel_xml(self, invoice: Invoice) -> str:
        """Generate FEL XML document for invoice"""
        
        # Create XML structure for Guatemala FEL
        # This is a simplified version - real FEL XML is more complex
        
        root = ET.Element("dte:GTDocumento")
        root.set("xmlns:dte", "http://www.sat.gob.gt/dte/fel/0.2.0")
        root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        root.set("Version", "0.1")
        root.set("xsi:schemaLocation", "http://www.sat.gob.gt/dte/fel/0.2.0")
        
        # SAT section
        sat = ET.SubElement(root, "dte:SAT")
        sat.set("ClaseDocumento", "dte")
        
        # DTE section  
        dte = ET.SubElement(sat, "dte:DTE")
        dte.set("ID", "DatosCertificados")
        
        # Data section
        datos_emision = ET.SubElement(dte, "dte:DatosEmision")
        datos_emision.set("ID", "DatosEmision")
        
        # General data
        datos_generales = ET.SubElement(datos_emision, "dte:DatosGenerales")
        datos_generales.set("CodigoMoneda", "GTQ")
        datos_generales.set("FechaHoraEmision", invoice.issue_date.isoformat())
        datos_generales.set("NumeroDocumento", invoice.invoice_number)
        datos_generales.set("Tipo", "FACT")  # FACT = Factura
        
        # Issuer (Emisor)
        emisor = ET.SubElement(datos_emision, "dte:Emisor")
        emisor.set("AfiliacionIVA", "GEN")
        emisor.set("CodigoEstablecimiento", "1")
        emisor.set("CorreoEmisor", "facturacion@smartorders.gt")
        emisor.set("NITEmisor", "12345678-9")  # Should come from settings
        emisor.set("NombreComercial", "Smart Orders Guatemala")
        emisor.set("NombreEmisor", "Smart Orders Guatemala")
        
        # Emisor address
        direccion_emisor = ET.SubElement(emisor, "dte:DireccionEmisor")
        direccion_emisor.set("Departamento", "Guatemala")
        direccion_emisor.set("Direccion", "Zona 10, Ciudad de Guatemala")
        direccion_emisor.set("Municipio", "Guatemala")
        direccion_emisor.set("CodigoPais", "GT")
        direccion_emisor.set("CodigoPostal", "01010")
        
        # Recipient (Receptor) 
        receptor = ET.SubElement(datos_emision, "dte:Receptor")
        receptor.set("CorreoReceptor", invoice.order.client.email or "")
        receptor.set("IDReceptor", invoice.order.client.nit if hasattr(invoice.order.client, 'nit') else "CF")
        receptor.set("NombreReceptor", invoice.order.client.name)
        
        # Recipient address
        direccion_receptor = ET.SubElement(receptor, "dte:DireccionReceptor")
        direccion_receptor.set("Departamento", "Guatemala")
        direccion_receptor.set("Direccion", invoice.order.client.address or "Ciudad de Guatemala")
        direccion_receptor.set("Municipio", "Guatemala")
        direccion_receptor.set("CodigoPais", "GT")
        direccion_receptor.set("CodigoPostal", "01010")
        
        # Items (Frases)
        frases = ET.SubElement(datos_emision, "dte:Frases")
        frase = ET.SubElement(frases, "dte:Frase")
        frase.set("CodigoEscenario", "1")
        frase.set("TipoFrase", "1")
        
        # Items details
        items = ET.SubElement(datos_emision, "dte:Items")
        
        for idx, item in enumerate(invoice.order.items, 1):
            item_element = ET.SubElement(items, "dte:Item")
            item_element.set("BienOServicio", "B")  # B = Bien, S = Servicio
            item_element.set("NumeroLinea", str(idx))
            
            # Quantities and prices
            cantidad = ET.SubElement(item_element, "dte:Cantidad")
            cantidad.text = str(item.quantity)
            
            descripcion = ET.SubElement(item_element, "dte:Descripcion")
            descripcion.text = item.product.name[:80]  # Limit description
            
            precio_unitario = ET.SubElement(item_element, "dte:PrecioUnitario")
            precio_unitario.text = f"{item.unit_price:.2f}"
            
            precio = ET.SubElement(item_element, "dte:Precio")
            precio.text = f"{item.total_price:.2f}"
            
            descuento = ET.SubElement(item_element, "dte:Descuento")
            descuento.text = "0.00"
            
            # Taxes
            impuestos = ET.SubElement(item_element, "dte:Impuestos")
            impuesto = ET.SubElement(impuestos, "dte:Impuesto")
            
            nombre_corto = ET.SubElement(impuesto, "dte:NombreCorto")
            nombre_corto.text = "IVA"
            
            codigo_unidad_gravable = ET.SubElement(impuesto, "dte:CodigoUnidadGravable")
            codigo_unidad_gravable.text = "1"
            
            monto_gravable = ET.SubElement(impuesto, "dte:MontoGravable")
            monto_gravable.text = f"{item.total_price:.2f}"
            
            monto_impuesto = ET.SubElement(impuesto, "dte:MontoImpuesto")
            tax_amount = item.total_price * invoice.tax_rate
            monto_impuesto.text = f"{tax_amount:.2f}"
            
        # Totals
        totales = ET.SubElement(datos_emision, "dte:Totales")
        
        total_impuestos = ET.SubElement(totales, "dte:TotalImpuestos")
        total_impuesto = ET.SubElement(total_impuestos, "dte:TotalImpuesto")
        total_impuesto.set("NombreCorto", "IVA")
        total_impuesto.set("TotalMontoImpuesto", f"{invoice.tax_amount:.2f}")
        
        gran_total = ET.SubElement(totales, "dte:GranTotal")
        gran_total.text = f"{invoice.total_amount:.2f}"
        
        # Convert to string
        xml_str = ET.tostring(root, encoding='unicode')
        
        # Format XML nicely
        from xml.dom import minidom
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent="  ", encoding=None)

    def _send_to_fel_certifier(self, fel_xml: str, certifier: str) -> Dict[str, Any]:
        """Send FEL XML to certifier for processing"""
        
        if certifier not in self.fel_configs:
            return {
                "success": False,
                "error": f"Unknown FEL certifier: {certifier}"
            }
        
        config = self.fel_configs[certifier]
        
        try:
            if certifier == "digifact":
                return self._send_to_digifact(fel_xml, config)
            elif certifier == "facturasgt":
                return self._send_to_facturasgt(fel_xml, config)
            else:
                return {
                    "success": False,
                    "error": f"Certifier {certifier} not implemented yet"
                }
                
        except Exception as e:
            logger.error(f"Error sending to FEL certifier {certifier}: {str(e)}")
            return {
                "success": False,
                "error": f"Connection error with certifier: {str(e)}"
            }

    def _send_to_digifact(self, fel_xml: str, config: FELConfiguration) -> Dict[str, Any]:
        """Send FEL to Digifact certifier"""
        
        # This is a mock implementation
        # Real implementation would use Digifact's API specification
        
        if config.environment == "test":
            # Mock successful response for testing
            mock_uuid = str(uuid.uuid4())
            return {
                "success": True,
                "uuid": mock_uuid,
                "dte_number": f"DTE-{mock_uuid[:8]}",
                "series": "A",
                "number": f"{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "authorization_date": datetime.now().isoformat()
            }
        else:
            # Real API call would go here
            endpoint = f"{config.base_url}/api/fel/submit"
            
            headers = {
                "Content-Type": "application/xml",
                "Authorization": f"Bearer {self._get_auth_token(config)}"
            }
            
            response = requests.post(
                endpoint,
                data=fel_xml,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                # Parse response and extract FEL data
                # This would depend on Digifact's response format
                return {
                    "success": True,
                    "uuid": "real-uuid-from-digifact",
                    "dte_number": "real-dte-number",
                    "series": "A",
                    "number": "real-number"
                }
            else:
                return {
                    "success": False,
                    "error": f"Digifact API error: {response.status_code} - {response.text}"
                }

    def _send_to_facturasgt(self, fel_xml: str, config: FELConfiguration) -> Dict[str, Any]:
        """Send FEL to FacturasGT certifier"""
        
        # Mock implementation for FacturasGT
        if config.environment == "test":
            mock_uuid = str(uuid.uuid4())
            return {
                "success": True,
                "uuid": mock_uuid,
                "dte_number": f"DTE-FGT-{mock_uuid[:8]}",
                "series": "B", 
                "number": f"FGT{datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
        else:
            # Real implementation would go here
            return {
                "success": False,
                "error": "FacturasGT production API not implemented yet"
            }

    def _get_auth_token(self, config: FELConfiguration) -> str:
        """Get authentication token from FEL certifier"""
        
        # Mock token for testing
        if config.environment == "test":
            return "test-auth-token"
        
        # Real implementation would authenticate with the certifier
        # and return a valid token
        return "real-auth-token"

    def retry_failed_fel_processing(self, db: Session, certifier: str = "digifact") -> Dict[str, Any]:
        """Retry FEL processing for failed invoices"""
        
        # Get invoices with FEL errors that need retry (DRAFT status with fel_error_message)
        failed_invoices = db.query(Invoice).filter(
            Invoice.status == InvoiceStatus.DRAFT,
            Invoice.requires_fel == True,
            Invoice.fel_error_message.isnot(None),
            Invoice.fel_uuid.is_(None)  # Not yet processed successfully
        ).all()
        
        results = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "details": []
        }
        
        for invoice in failed_invoices:
            result = self.process_fel_authorization(db, invoice.id, certifier)
            results["total_processed"] += 1
            
            if result.success:
                results["successful"] += 1
            else:
                results["failed"] += 1
                
            results["details"].append({
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "success": result.success,
                "error": result.error_message
            })
        
        return results

    def get_fel_status_summary(self, db: Session) -> Dict[str, Any]:
        """Get summary of FEL processing status"""
        
        from sqlalchemy import func, case
        
        # Query FEL invoices with derived status
        fel_invoices = db.query(
            case(
                # Successfully processed FEL invoices
                (Invoice.fel_uuid.isnot(None), "fel_processed"),
                # Failed FEL invoices (have error message but no UUID)
                ((Invoice.fel_error_message.isnot(None)) & (Invoice.fel_uuid.is_(None)), "fel_failed"),
                # Pending FEL invoices (no error, no UUID)
                else_="fel_pending"
            ).label('fel_status'),
            func.count(Invoice.id).label('count')
        ).filter(
            Invoice.requires_fel == True
        ).group_by('fel_status').all()
        
        # Also get overall status counts
        status_counts = db.query(
            Invoice.status,
            func.count(Invoice.id).label('count')
        ).filter(
            Invoice.requires_fel == True
        ).group_by(Invoice.status).all()
        
        total_fel = sum(count for _, count in status_counts)
        
        summary = {
            "total_fel_invoices": total_fel,
            "by_status": {status.value: count for status, count in status_counts},
            "fel_processing": {fel_status: count for fel_status, count in fel_invoices},
            "processing_needed": 0,
            "successfully_processed": 0,
            "failed_processing": 0
        }
        
        # Calculate derived metrics from FEL processing
        for fel_status, count in fel_invoices:
            if fel_status == "fel_pending":
                summary["processing_needed"] += count
            elif fel_status == "fel_processed":
                summary["successfully_processed"] += count
            elif fel_status == "fel_failed":
                summary["failed_processing"] += count
        
        return summary
