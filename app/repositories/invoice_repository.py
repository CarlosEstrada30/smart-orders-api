from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta
from .base import BaseRepository
from ..models.invoice import Invoice, InvoiceStatus
from ..models.order import Order, OrderItem
from ..schemas.invoice import InvoiceCreate, InvoiceUpdate
import uuid


class InvoiceRepository(BaseRepository[Invoice, InvoiceCreate, InvoiceUpdate]):
    def __init__(self):
        super().__init__(Invoice)

    def get_by_invoice_number(self, db: Session, *, invoice_number: str) -> Optional[Invoice]:
        return db.query(Invoice).options(
            joinedload(Invoice.order).joinedload(Order.client),
            joinedload(Invoice.order).joinedload(Order.items).joinedload(OrderItem.product)
        ).filter(Invoice.invoice_number == invoice_number).first()

    def get_by_order_id(self, db: Session, *, order_id: int) -> Optional[Invoice]:
        return db.query(Invoice).options(
            joinedload(Invoice.order).joinedload(Order.client),
            joinedload(Invoice.order).joinedload(Order.items).joinedload(OrderItem.product)
        ).filter(Invoice.order_id == order_id).first()

    def get_invoices_by_status(self, db: Session, *, status: InvoiceStatus, skip: int = 0, limit: int = 100) -> List[Invoice]:
        return db.query(Invoice).options(
            joinedload(Invoice.order).joinedload(Order.client),
            joinedload(Invoice.order).joinedload(Order.items).joinedload(OrderItem.product)
        ).filter(Invoice.status == status).offset(skip).limit(limit).all()

    def get_invoices_by_client(self, db: Session, *, client_id: int, skip: int = 0, limit: int = 100) -> List[Invoice]:
        return db.query(Invoice).options(
            joinedload(Invoice.order).joinedload(Order.client),
            joinedload(Invoice.order).joinedload(Order.items).joinedload(OrderItem.product)
        ).join(Order).filter(Order.client_id == client_id).offset(skip).limit(limit).all()

    def get_overdue_invoices(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[Invoice]:
        today = datetime.now()
        return db.query(Invoice).options(
            joinedload(Invoice.order).joinedload(Order.client),
            joinedload(Invoice.order).joinedload(Order.items).joinedload(OrderItem.product)
        ).filter(
            and_(
                Invoice.due_date < today,
                Invoice.status.in_([InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE]),
                Invoice.balance_due > 0
            )
        ).offset(skip).limit(limit).all()

    def get_pending_invoices(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[Invoice]:
        return db.query(Invoice).options(
            joinedload(Invoice.order).joinedload(Order.client),
            joinedload(Invoice.order).joinedload(Order.items).joinedload(OrderItem.product)
        ).filter(
            and_(
                Invoice.status.in_([InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE]),
                Invoice.balance_due > 0
            )
        ).offset(skip).limit(limit).all()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[Invoice]:
        return db.query(Invoice).options(
            joinedload(Invoice.order).joinedload(Order.client),
            joinedload(Invoice.order).joinedload(Order.items).joinedload(OrderItem.product)
        ).offset(skip).limit(limit).all()

    def get(self, db: Session, id: int) -> Optional[Invoice]:
        return db.query(Invoice).options(
            joinedload(Invoice.order).joinedload(Order.client),
            joinedload(Invoice.order).joinedload(Order.items).joinedload(OrderItem.product)
        ).filter(Invoice.id == id).first()

    def create_invoice_from_order(self, db: Session, *, order_id: int, invoice_data: InvoiceCreate) -> Invoice:
        # Get order to calculate amounts
        order = db.query(Order).options(
            joinedload(Order.items)
        ).filter(Order.id == order_id).first()
        
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        # Check if invoice already exists for this order
        existing_invoice = self.get_by_order_id(db, order_id=order_id)
        if existing_invoice:
            raise ValueError(f"Invoice already exists for order {order_id}")
        
        # Generate unique invoice number
        invoice_number = f"INV-{uuid.uuid4().hex[:8].upper()}"
        
        # Calculate financial amounts
        subtotal = order.total_amount - invoice_data.discount_amount
        tax_amount = subtotal * invoice_data.tax_rate
        total_amount = subtotal + tax_amount
        
        # Create invoice
        invoice = Invoice(
            invoice_number=invoice_number,
            order_id=order_id,
            status=InvoiceStatus.DRAFT,
            payment_method=invoice_data.payment_method,
            subtotal=subtotal,
            tax_rate=invoice_data.tax_rate,
            tax_amount=tax_amount,
            discount_amount=invoice_data.discount_amount,
            total_amount=total_amount,
            paid_amount=0.0,
            balance_due=total_amount,
            due_date=invoice_data.due_date,
            notes=invoice_data.notes,
            payment_terms=invoice_data.payment_terms
        )
        
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        return invoice

    def update_invoice_status(self, db: Session, *, invoice_id: int, status: InvoiceStatus) -> Optional[Invoice]:
        invoice = self.get(db, invoice_id)
        if invoice:
            invoice.status = status
            
            # Auto-update overdue status
            if status == InvoiceStatus.ISSUED and invoice.due_date and invoice.due_date < datetime.now():
                invoice.status = InvoiceStatus.OVERDUE
            
            db.commit()
            db.refresh(invoice)
        return invoice

    def record_payment(self, db: Session, *, invoice_id: int, payment_amount: float, payment_date: Optional[datetime] = None) -> Optional[Invoice]:
        invoice = self.get(db, invoice_id)
        if not invoice:
            return None
        
        # Update payment information
        invoice.paid_amount += payment_amount
        invoice.balance_due = invoice.total_amount - invoice.paid_amount
        
        # Update status based on payment
        if invoice.balance_due <= 0:
            invoice.status = InvoiceStatus.PAID
            invoice.paid_date = payment_date or datetime.now()
        elif invoice.paid_amount > 0:
            # Partial payment - keep current status unless it's draft
            if invoice.status == InvoiceStatus.DRAFT:
                invoice.status = InvoiceStatus.ISSUED
        
        db.commit()
        db.refresh(invoice)
        return invoice

    def get_invoice_summary(self, db: Session, *, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> dict:
        """Get summary statistics for invoices"""
        query = db.query(Invoice)
        
        if start_date:
            query = query.filter(Invoice.issue_date >= start_date)
        if end_date:
            query = query.filter(Invoice.issue_date <= end_date)
        
        # Get basic counts and amounts
        total_invoices = query.count()
        total_amount = db.query(func.sum(Invoice.total_amount)).filter(
            Invoice.issue_date >= start_date if start_date else True,
            Invoice.issue_date <= end_date if end_date else True
        ).scalar() or 0
        
        paid_amount = db.query(func.sum(Invoice.paid_amount)).filter(
            Invoice.issue_date >= start_date if start_date else True,
            Invoice.issue_date <= end_date if end_date else True
        ).scalar() or 0
        
        pending_amount = total_amount - paid_amount
        
        # Get overdue information
        overdue_query = query.filter(
            Invoice.status == InvoiceStatus.OVERDUE,
            Invoice.balance_due > 0
        )
        overdue_count = overdue_query.count()
        overdue_amount = db.query(func.sum(Invoice.balance_due)).filter(
            Invoice.status == InvoiceStatus.OVERDUE,
            Invoice.balance_due > 0,
            Invoice.issue_date >= start_date if start_date else True,
            Invoice.issue_date <= end_date if end_date else True
        ).scalar() or 0
        
        return {
            "total_invoices": total_invoices,
            "total_amount": float(total_amount),
            "paid_amount": float(paid_amount),
            "pending_amount": float(pending_amount),
            "overdue_count": overdue_count,
            "overdue_amount": float(overdue_amount)
        }

    def mark_overdue_invoices(self, db: Session) -> int:
        """Mark invoices as overdue if past due date"""
        today = datetime.now()
        
        overdue_invoices = db.query(Invoice).filter(
            and_(
                Invoice.due_date < today,
                Invoice.status == InvoiceStatus.ISSUED,
                Invoice.balance_due > 0
            )
        ).all()
        
        count = 0
        for invoice in overdue_invoices:
            invoice.status = InvoiceStatus.OVERDUE
            count += 1
        
        if count > 0:
            db.commit()
        
        return count
