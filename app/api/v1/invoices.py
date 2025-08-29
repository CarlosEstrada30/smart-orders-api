from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
import os
from io import BytesIO

from ...database import get_db
from ...schemas.invoice import (
    InvoiceCreate, InvoiceUpdate, InvoiceResponse, InvoiceListResponse,
    InvoiceSummary, PaymentCreate, InvoicePDFRequest
)
from ...services.invoice_service import InvoiceService
from ...models.invoice import InvoiceStatus
from ..dependencies import get_invoice_service
from .auth import get_current_active_user
from ...models.user import User

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post("/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice(
    order_id: int,
    invoice: InvoiceCreate,
    db: Session = Depends(get_db),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new invoice from an order (requires authentication)"""
    try:
        return invoice_service.create_invoice_from_order(db, order_id, invoice)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[InvoiceListResponse])
def get_invoices(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = Query(None, description="Filter by invoice status"),
    client_id: Optional[int] = Query(None, description="Filter by client ID"),
    overdue_only: bool = Query(False, description="Show only overdue invoices"),
    pending_only: bool = Query(False, description="Show only pending invoices"),
    db: Session = Depends(get_db),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get all invoices with optional filters (requires authentication)"""
    try:
        if overdue_only:
            return invoice_service.get_overdue_invoices(db, skip=skip, limit=limit)
        elif pending_only:
            return invoice_service.get_pending_invoices(db, skip=skip, limit=limit)
        elif status_filter:
            status_enum = InvoiceStatus(status_filter)
            return invoice_service.get_invoices_by_status(db, status_enum, skip=skip, limit=limit)
        elif client_id:
            return invoice_service.get_invoices_by_client(db, client_id, skip=skip, limit=limit)
        else:
            return invoice_service.get_invoices(db, skip=skip, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/summary", response_model=InvoiceSummary)
def get_invoice_summary(
    start_date: Optional[datetime] = Query(None, description="Start date for summary"),
    end_date: Optional[datetime] = Query(None, description="End date for summary"),
    db: Session = Depends(get_db),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get invoice summary/statistics (requires authentication)"""
    return invoice_service.get_invoice_summary(db, start_date=start_date, end_date=end_date)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific invoice by ID (requires authentication)"""
    invoice = invoice_service.get_invoice(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.get("/number/{invoice_number}", response_model=InvoiceResponse)
def get_invoice_by_number(
    invoice_number: str,
    db: Session = Depends(get_db),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get invoice by invoice number (requires authentication)"""
    invoice = invoice_service.get_invoice_by_number(db, invoice_number)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.get("/order/{order_id}", response_model=InvoiceResponse)
def get_invoice_by_order(
    order_id: int,
    db: Session = Depends(get_db),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get invoice for a specific order (requires authentication)"""
    invoice = invoice_service.get_invoice_by_order(db, order_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found for this order")
    return invoice


@router.put("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(
    invoice_id: int,
    invoice_update: InvoiceUpdate,
    db: Session = Depends(get_db),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user)
):
    """Update an invoice (requires authentication)"""
    try:
        invoice = invoice_service.update_invoice(db, invoice_id, invoice_update)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return invoice
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{invoice_id}/status/{new_status}", response_model=InvoiceResponse)
def update_invoice_status(
    invoice_id: int,
    new_status: str,
    db: Session = Depends(get_db),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user)
):
    """Update invoice status (requires authentication)"""
    try:
        status_enum = InvoiceStatus(new_status)
        invoice = invoice_service.update_invoice_status(db, invoice_id, status_enum)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return invoice
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{invoice_id}/cancel", response_model=InvoiceResponse)
def cancel_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user)
):
    """Cancel an invoice (requires authentication)"""
    try:
        invoice = invoice_service.cancel_invoice(db, invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return invoice
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/payments", response_model=InvoiceResponse)
def record_payment(
    payment: PaymentCreate,
    db: Session = Depends(get_db),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user)
):
    """Record a payment against an invoice (requires authentication)"""
    try:
        return invoice_service.record_payment(db, payment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{invoice_id}/pdf", response_class=StreamingResponse)
def download_invoice_pdf(
    invoice_id: int,
    regenerate: bool = Query(False, description="Force regenerate PDF"),
    db: Session = Depends(get_db),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user)
):
    """Download invoice PDF (requires authentication)"""
    try:
        # Get invoice to check if it exists and get invoice number
        invoice = invoice_service.get_invoice(db, invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Generate PDF buffer
        pdf_buffer = invoice_service.get_pdf_buffer(db, invoice_id)
        
        # Set filename
        filename = f"factura_{invoice.invoice_number}.pdf"
        
        # Return as streaming response
        return StreamingResponse(
            BytesIO(pdf_buffer.getvalue()),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")


@router.post("/{invoice_id}/pdf/generate")
def generate_invoice_pdf(
    invoice_id: int,
    regenerate: bool = Query(False, description="Force regenerate PDF"),
    db: Session = Depends(get_db),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user)
):
    """Generate and save invoice PDF (requires authentication)"""
    try:
        file_path = invoice_service.generate_pdf(db, invoice_id, regenerate=regenerate)
        return {
            "message": "PDF generated successfully",
            "file_path": file_path,
            "invoice_id": invoice_id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")


@router.post("/orders/{order_id}/auto-invoice", response_model=InvoiceResponse)
def auto_create_invoice(
    order_id: int,
    db: Session = Depends(get_db),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user)
):
    """Auto-create invoice for delivered order (requires authentication)"""
    try:
        invoice = invoice_service.auto_create_invoice_for_order(db, order_id)
        if not invoice:
            raise HTTPException(
                status_code=400, 
                detail="Cannot create invoice for this order. Order must be delivered and not have existing invoice."
            )
        return invoice
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/maintenance/mark-overdue")
def mark_overdue_invoices(
    db: Session = Depends(get_db),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user)
):
    """Mark overdue invoices (maintenance endpoint) (requires authentication)"""
    count = invoice_service.mark_overdue_invoices(db)
    return {
        "message": f"Marked {count} invoices as overdue",
        "count": count
    }


# Preview endpoint (useful for testing the PDF design)
@router.get("/{invoice_id}/pdf/preview", response_class=StreamingResponse)
def preview_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user)
):
    """Preview invoice PDF in browser (requires authentication)"""
    try:
        # Get invoice to check if it exists
        invoice = invoice_service.get_invoice(db, invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Generate PDF buffer
        pdf_buffer = invoice_service.get_pdf_buffer(db, invoice_id)
        
        # Return as inline PDF (for preview in browser)
        return StreamingResponse(
            BytesIO(pdf_buffer.getvalue()),
            media_type="application/pdf",
            headers={"Content-Disposition": "inline"}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")
