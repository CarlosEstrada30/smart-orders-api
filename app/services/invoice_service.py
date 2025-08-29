from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os
import tempfile
from io import BytesIO

from ..repositories.invoice_repository import InvoiceRepository
from ..repositories.order_repository import OrderRepository
from ..schemas.invoice import (
    InvoiceCreate, InvoiceUpdate, InvoiceResponse, InvoiceListResponse,
    InvoiceSummary, PaymentCreate, CompanyInfo
)
from ..models.invoice import Invoice, InvoiceStatus, PaymentMethod
from ..models.order import OrderStatus
from .simple_pdf_generator import SimplePDFGenerator


class InvoiceService:
    def __init__(self):
        self.invoice_repository = InvoiceRepository()
        self.order_repository = OrderRepository()
        self.pdf_generator = SimplePDFGenerator()
        self.pdf_storage_path = "invoices/pdfs"  # Configurable
        
        # Default company info (should be configurable)
        self.company_info = CompanyInfo(
            name="Smart Orders Guatemala",
            address="Zona 10, Ciudad de Guatemala, Guatemala",
            phone="+502 2222-3333",
            email="facturacion@smartorders.gt",
            nit="12345678-9"
        )
        
        # Ensure PDF storage directory exists
        os.makedirs(self.pdf_storage_path, exist_ok=True)

    def get_invoice(self, db: Session, invoice_id: int) -> Optional[InvoiceResponse]:
        """Get a single invoice by ID"""
        invoice = self.invoice_repository.get(db, invoice_id)
        if not invoice:
            return None
        return self._process_invoice_response(invoice)

    def get_invoice_by_number(self, db: Session, invoice_number: str) -> Optional[InvoiceResponse]:
        """Get invoice by invoice number"""
        invoice = self.invoice_repository.get_by_invoice_number(db, invoice_number=invoice_number)
        if not invoice:
            return None
        return self._process_invoice_response(invoice)

    def get_invoice_by_order(self, db: Session, order_id: int) -> Optional[InvoiceResponse]:
        """Get invoice for a specific order"""
        invoice = self.invoice_repository.get_by_order_id(db, order_id=order_id)
        if not invoice:
            return None
        return self._process_invoice_response(invoice)

    def get_invoices(self, db: Session, skip: int = 0, limit: int = 100) -> List[InvoiceListResponse]:
        """Get all invoices with pagination"""
        invoices = self.invoice_repository.get_multi(db, skip=skip, limit=limit)
        return [self._process_invoice_list_response(invoice) for invoice in invoices]

    def get_invoices_by_status(self, db: Session, status: InvoiceStatus, skip: int = 0, limit: int = 100) -> List[InvoiceListResponse]:
        """Get invoices by status"""
        invoices = self.invoice_repository.get_invoices_by_status(db, status=status, skip=skip, limit=limit)
        return [self._process_invoice_list_response(invoice) for invoice in invoices]

    def get_invoices_by_client(self, db: Session, client_id: int, skip: int = 0, limit: int = 100) -> List[InvoiceListResponse]:
        """Get invoices for a specific client"""
        invoices = self.invoice_repository.get_invoices_by_client(db, client_id=client_id, skip=skip, limit=limit)
        return [self._process_invoice_list_response(invoice) for invoice in invoices]

    def get_overdue_invoices(self, db: Session, skip: int = 0, limit: int = 100) -> List[InvoiceListResponse]:
        """Get overdue invoices"""
        invoices = self.invoice_repository.get_overdue_invoices(db, skip=skip, limit=limit)
        return [self._process_invoice_list_response(invoice) for invoice in invoices]

    def get_pending_invoices(self, db: Session, skip: int = 0, limit: int = 100) -> List[InvoiceListResponse]:
        """Get pending invoices"""
        invoices = self.invoice_repository.get_pending_invoices(db, skip=skip, limit=limit)
        return [self._process_invoice_list_response(invoice) for invoice in invoices]

    def create_invoice_from_order(self, db: Session, order_id: int, invoice_data: InvoiceCreate) -> InvoiceResponse:
        """Create invoice from an existing order"""
        # Validate order exists and is eligible for invoicing
        order = self.order_repository.get(db, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order.status == OrderStatus.CANCELLED:
            raise ValueError("Cannot create invoice for cancelled order")
        
        # Check if invoice already exists
        existing_invoice = self.invoice_repository.get_by_order_id(db, order_id=order_id)
        if existing_invoice:
            raise ValueError(f"Invoice already exists for order {order_id}")
        
        # Set default due date if not provided (30 days from now)
        if not invoice_data.due_date:
            invoice_data.due_date = datetime.now() + timedelta(days=30)
        
        # Create invoice
        invoice = self.invoice_repository.create_invoice_from_order(db, order_id=order_id, invoice_data=invoice_data)
        
        return self._process_invoice_response(invoice)

    def update_invoice(self, db: Session, invoice_id: int, invoice_update: InvoiceUpdate) -> Optional[InvoiceResponse]:
        """Update an invoice"""
        invoice = self.invoice_repository.get(db, invoice_id)
        if not invoice:
            return None
        
        # Handle payment recording
        if invoice_update.paid_amount is not None and invoice_update.paid_amount != invoice.paid_amount:
            payment_amount = invoice_update.paid_amount - invoice.paid_amount
            if payment_amount > 0:
                self.invoice_repository.record_payment(
                    db, 
                    invoice_id=invoice_id, 
                    payment_amount=payment_amount,
                    payment_date=invoice_update.paid_date
                )
                # Refresh invoice after payment
                invoice = self.invoice_repository.get(db, invoice_id)
        
        # Update other fields
        update_data = invoice_update.model_dump(exclude_unset=True, exclude={'paid_amount', 'paid_date'})
        if update_data:
            invoice = self.invoice_repository.update(db, db_obj=invoice, obj_in=update_data)
        
        return self._process_invoice_response(invoice)

    def record_payment(self, db: Session, payment_data: PaymentCreate) -> Optional[InvoiceResponse]:
        """Record a payment against an invoice"""
        invoice = self.invoice_repository.get(db, payment_data.invoice_id)
        if not invoice:
            raise ValueError(f"Invoice {payment_data.invoice_id} not found")
        
        if payment_data.amount > invoice.balance_due:
            raise ValueError(f"Payment amount ({payment_data.amount}) exceeds balance due ({invoice.balance_due})")
        
        # Record payment
        updated_invoice = self.invoice_repository.record_payment(
            db,
            invoice_id=payment_data.invoice_id,
            payment_amount=payment_data.amount,
            payment_date=payment_data.payment_date or datetime.now()
        )
        
        return self._process_invoice_response(updated_invoice)

    def update_invoice_status(self, db: Session, invoice_id: int, status: InvoiceStatus) -> Optional[InvoiceResponse]:
        """Update invoice status"""
        invoice = self.invoice_repository.update_invoice_status(db, invoice_id=invoice_id, status=status)
        if not invoice:
            return None
        return self._process_invoice_response(invoice)

    def cancel_invoice(self, db: Session, invoice_id: int) -> Optional[InvoiceResponse]:
        """Cancel an invoice"""
        invoice = self.invoice_repository.get(db, invoice_id)
        if not invoice:
            return None
        
        if invoice.status == InvoiceStatus.PAID:
            raise ValueError("Cannot cancel a paid invoice")
        
        invoice = self.invoice_repository.update_invoice_status(db, invoice_id=invoice_id, status=InvoiceStatus.CANCELLED)
        return self._process_invoice_response(invoice)

    def generate_pdf(self, db: Session, invoice_id: int, regenerate: bool = False) -> str:
        """Generate PDF for an invoice and return file path"""
        invoice = self.invoice_repository.get(db, invoice_id)
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        # Check if PDF already exists and regenerate is False
        if invoice.pdf_generated and invoice.pdf_path and not regenerate:
            if os.path.exists(invoice.pdf_path):
                return invoice.pdf_path
        
        # Generate PDF filename
        filename = f"invoice_{invoice.invoice_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        file_path = os.path.join(self.pdf_storage_path, filename)
        
        # Generate PDF
        self.pdf_generator.generate_invoice_pdf(invoice, self.company_info, file_path)
        
        # Update invoice with PDF info
        self.invoice_repository.update(
            db,
            db_obj=invoice,
            obj_in={
                "pdf_generated": True,
                "pdf_path": file_path
            }
        )
        
        return file_path

    def get_pdf_buffer(self, db: Session, invoice_id: int) -> BytesIO:
        """Generate PDF and return as BytesIO buffer for download"""
        invoice = self.invoice_repository.get(db, invoice_id)
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        return self.pdf_generator.generate_pdf_buffer(invoice, self.company_info)

    def get_invoice_summary(self, db: Session, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> InvoiceSummary:
        """Get invoice summary/statistics"""
        summary_data = self.invoice_repository.get_invoice_summary(db, start_date=start_date, end_date=end_date)
        return InvoiceSummary(**summary_data)

    def mark_overdue_invoices(self, db: Session) -> int:
        """Mark invoices as overdue (useful for scheduled tasks)"""
        return self.invoice_repository.mark_overdue_invoices(db)

    def auto_create_invoice_for_order(self, db: Session, order_id: int) -> Optional[InvoiceResponse]:
        """Automatically create invoice when order is delivered"""
        order = self.order_repository.get(db, order_id)
        if not order:
            return None
        
        # Only create invoice for delivered orders
        if order.status != OrderStatus.DELIVERED:
            return None
        
        # Check if invoice already exists
        existing_invoice = self.invoice_repository.get_by_order_id(db, order_id=order_id)
        if existing_invoice:
            return self._process_invoice_response(existing_invoice)
        
        # Create invoice with default settings
        invoice_data = InvoiceCreate(
            order_id=order_id,
            tax_rate=0.12,  # 12% IVA Guatemala
            discount_amount=0.0,
            due_date=datetime.now() + timedelta(days=30),
            payment_terms="Pago contra entrega",
            notes="Factura generada automáticamente"
        )
        
        return self.create_invoice_from_order(db, order_id, invoice_data)

    def _process_invoice_response(self, invoice: Invoice) -> InvoiceResponse:
        """Process invoice and create response with complete data"""
        invoice_data = {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "order_id": invoice.order_id,
            "status": invoice.status,
            "payment_method": invoice.payment_method,
            "subtotal": invoice.subtotal,
            "tax_rate": invoice.tax_rate,
            "tax_amount": invoice.tax_amount,
            "discount_amount": invoice.discount_amount,
            "total_amount": invoice.total_amount,
            "paid_amount": invoice.paid_amount,
            "balance_due": invoice.balance_due,
            "issue_date": invoice.issue_date,
            "due_date": invoice.due_date,
            "paid_date": invoice.paid_date,
            "notes": invoice.notes,
            "payment_terms": invoice.payment_terms,
            "pdf_generated": invoice.pdf_generated,
            "pdf_path": invoice.pdf_path,
            "created_at": invoice.created_at,
            "updated_at": invoice.updated_at
        }
        return InvoiceResponse(**invoice_data)

    def _process_invoice_list_response(self, invoice: Invoice) -> InvoiceListResponse:
        """Process invoice for list response"""
        invoice_data = {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "order_id": invoice.order_id,
            "status": invoice.status,
            "total_amount": invoice.total_amount,
            "balance_due": invoice.balance_due,
            "issue_date": invoice.issue_date,
            "due_date": invoice.due_date,
            "client_name": invoice.order.client.name if invoice.order and invoice.order.client else None
        }
        return InvoiceListResponse(**invoice_data)
