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
    InvoiceSummary, PaymentCreate, InvoicePDFRequest, FELProcessRequest, FELProcessResponse
)
from ...services.invoice_service import InvoiceService
from ...models.invoice import InvoiceStatus
from ..dependencies import get_invoice_service
from .auth import get_current_active_user, get_tenant_db
from ...models.user import User

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post("/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice(
    order_id: int,
    invoice: InvoiceCreate,
    db: Session = Depends(get_tenant_db),
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
    db: Session = Depends(get_tenant_db),
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
    db: Session = Depends(get_tenant_db),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get invoice summary/statistics (requires authentication)"""
    return invoice_service.get_invoice_summary(db, start_date=start_date, end_date=end_date)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_tenant_db),
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
    db: Session = Depends(get_tenant_db),
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
    db: Session = Depends(get_tenant_db),
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
    db: Session = Depends(get_tenant_db),
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
    db: Session = Depends(get_tenant_db),
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
    db: Session = Depends(get_tenant_db),
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
    db: Session = Depends(get_tenant_db),
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
    db: Session = Depends(get_tenant_db),
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
    db: Session = Depends(get_tenant_db),
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
    db: Session = Depends(get_tenant_db),
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
    db: Session = Depends(get_tenant_db),
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
    db: Session = Depends(get_tenant_db),
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


# FEL (Facturación Electrónica en Línea) - Guatemala Endpoints
@router.post("/{invoice_id}/fel/process", response_model=FELProcessResponse)
def process_invoice_fel(
    invoice_id: int,
    certifier: str = Query(default="digifact", description="FEL certifier to use (digifact, facturasgt)"),
    db: Session = Depends(get_tenant_db),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user)
):
    """Process invoice through FEL (Guatemala electronic invoicing) (requires authentication)"""
    try:
        result = invoice_service.process_fel_for_invoice(db, invoice_id, certifier)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing FEL: {str(e)}")


@router.post("/orders/{order_id}/auto-invoice-with-fel", response_model=InvoiceResponse)
def auto_create_invoice_with_fel(
    order_id: int,
    certifier: str = Query(default="digifact", description="FEL certifier to use"),
    db: Session = Depends(get_tenant_db),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user)
):
    """Auto-create invoice for delivered order and process FEL (requires authentication)"""
    try:
        invoice = invoice_service.auto_create_invoice_for_order(db, order_id, requires_fel=True)
        if not invoice:
            raise HTTPException(
                status_code=400, 
                detail="Cannot create invoice for this order. Order must be delivered and not have existing invoice."
            )
        return invoice
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/{order_id}/receipt-only")
def create_receipt_only(
    order_id: int,
    db: Session = Depends(get_tenant_db),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user)
):
    """Process delivered order with receipt only (no FEL invoice) (requires authentication)"""
    try:
        result = invoice_service.create_receipt_only_order_process(db, order_id)
        
        # Return receipt as download
        return StreamingResponse(
            BytesIO(result["document_buffer"].getvalue()),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=comprobante_{result['order_number']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating receipt: {str(e)}")


@router.post("/fel/retry-failed")
def retry_failed_fel_processing(
    certifier: str = Query(default="digifact", description="FEL certifier to use"),
    db: Session = Depends(get_tenant_db),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user)
):
    """Retry FEL processing for failed invoices (maintenance endpoint) (requires authentication)"""
    try:
        result = invoice_service.retry_fel_processing(db, certifier)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrying FEL processing: {str(e)}")


@router.get("/fel/status-summary")
def get_fel_status_summary(
    db: Session = Depends(get_tenant_db),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get FEL processing status summary (requires authentication)"""
    try:
        summary = invoice_service.get_fel_status_summary(db)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting FEL summary: {str(e)}")


@router.get("/revenue/fiscal")
def get_fiscal_revenue(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_tenant_db),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get fiscal revenue (only FEL-authorized invoices) (requires authentication)"""
    try:
        from datetime import datetime
        from sqlalchemy import func, text
        from ...models.invoice import Invoice
        
        # Parse dates if provided
        start_dt = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None
        
        # Get the enum values to avoid mapping issues
        fel_authorized = InvoiceStatus.FEL_AUTHORIZED.value
        issued = InvoiceStatus.ISSUED.value 
        paid = InvoiceStatus.PAID.value
        
        # Query for FEL-authorized invoices using raw SQL for status filtering
        query = db.query(
            func.sum(Invoice.total_amount).label('total_invoiced'),
            func.sum(Invoice.paid_amount).label('total_collected'),
            func.count(Invoice.id).label('total_invoices')
        ).filter(
            text("invoices.status IN (:fel_auth, :issued, :paid)").params(
                fel_auth=fel_authorized, issued=issued, paid=paid
            ),
            Invoice.fel_uuid.isnot(None)
        )
        
        if start_dt:
            query = query.filter(Invoice.issue_date >= start_dt)
        if end_dt:
            query = query.filter(Invoice.issue_date <= end_dt)
        
        result = query.first()
        
        return {
            "period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "fiscal_revenue": {
                "total_invoiced": float(result.total_invoiced or 0),
                "total_collected": float(result.total_collected or 0),
                "total_invoices": result.total_invoices or 0,
                "average_invoice": float(result.total_invoiced or 0) / max(result.total_invoices or 1, 1),
                "collection_rate": float(result.total_collected or 0) / max(float(result.total_invoiced or 0), 1) * 100
            },
            "note": "Only includes FEL-authorized invoices (fiscally valid)"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating fiscal revenue: {str(e)}")
