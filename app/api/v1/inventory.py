from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime

from ...database import get_db
from ...schemas.inventory_entry import (
    InventoryEntryCreate, InventoryEntryUpdate, InventoryEntryResponse,
    InventoryEntryListResponse, InventoryEntrySummary, StockAdjustmentRequest,
    BatchUpdateRequest, InventoryReport, EntryValidationRequest
)
from ...services.inventory_entry_service import InventoryEntryService
from ...models.inventory_entry import EntryType, EntryStatus
from ..dependencies import get_inventory_entry_service
from .auth import get_current_active_user, get_tenant_db
from ...models.user import User
from ...utils.permissions import can_approve_inventory, can_complete_inventory

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.post("/entries", response_model=InventoryEntryResponse, status_code=status.HTTP_201_CREATED)
def create_inventory_entry(
    entry: InventoryEntryCreate,
    db: Session = Depends(get_tenant_db),
    inventory_service: InventoryEntryService = Depends(get_inventory_entry_service),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new inventory entry (requires authentication)"""
    try:
        return inventory_service.create_entry(db, entry, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/entries", response_model=List[InventoryEntryListResponse])
def get_inventory_entries(
    skip: int = 0,
    limit: int = 100,
    entry_type: Optional[str] = Query(None, description="Filter by entry type"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    product_id: Optional[int] = Query(None, description="Filter by product ID"),
    pending_only: bool = Query(False, description="Show only pending entries"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    db: Session = Depends(get_tenant_db),
    inventory_service: InventoryEntryService = Depends(get_inventory_entry_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get inventory entries with optional filters (requires authentication)"""
    try:
        if pending_only:
            return inventory_service.get_pending_entries(db, skip=skip, limit=limit)
        elif entry_type:
            entry_type_enum = EntryType(entry_type)
            return inventory_service.get_entries_by_type(db, entry_type_enum, skip=skip, limit=limit)
        elif status_filter:
            status_enum = EntryStatus(status_filter)
            return inventory_service.get_entries_by_status(db, status_enum, skip=skip, limit=limit)
        elif user_id:
            return inventory_service.get_entries_by_user(db, user_id, skip=skip, limit=limit)
        elif product_id:
            return inventory_service.get_entries_by_product(db, product_id, skip=skip, limit=limit)
        elif start_date and end_date:
            return inventory_service.get_entries_by_date_range(db, start_date, end_date, skip=skip, limit=limit)
        else:
            return inventory_service.get_entries(db, skip=skip, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/entries/summary", response_model=InventoryEntrySummary)
def get_inventory_summary(
    start_date: Optional[datetime] = Query(None, description="Start date for summary"),
    end_date: Optional[datetime] = Query(None, description="End date for summary"),
    db: Session = Depends(get_tenant_db),
    inventory_service: InventoryEntryService = Depends(get_inventory_entry_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get inventory entries summary/statistics (requires authentication)"""
    return inventory_service.get_entry_summary(db, start_date=start_date, end_date=end_date)


@router.get("/entries/{entry_id}", response_model=InventoryEntryResponse)
def get_inventory_entry(
    entry_id: int,
    db: Session = Depends(get_tenant_db),
    inventory_service: InventoryEntryService = Depends(get_inventory_entry_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific inventory entry by ID (requires authentication)"""
    entry = inventory_service.get_entry(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Inventory entry not found")
    return entry


@router.get("/entries/number/{entry_number}", response_model=InventoryEntryResponse)
def get_inventory_entry_by_number(
    entry_number: str,
    db: Session = Depends(get_tenant_db),
    inventory_service: InventoryEntryService = Depends(get_inventory_entry_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get inventory entry by entry number (requires authentication)"""
    entry = inventory_service.get_entry_by_number(db, entry_number)
    if not entry:
        raise HTTPException(status_code=404, detail="Inventory entry not found")
    return entry


@router.put("/entries/{entry_id}", response_model=InventoryEntryResponse)
def update_inventory_entry(
    entry_id: int,
    entry_update: InventoryEntryUpdate,
    db: Session = Depends(get_tenant_db),
    inventory_service: InventoryEntryService = Depends(get_inventory_entry_service),
    current_user: User = Depends(get_current_active_user)
):
    """Update an inventory entry (requires authentication)"""
    try:
        entry = inventory_service.update_entry(db, entry_id, entry_update)
        if not entry:
            raise HTTPException(status_code=404, detail="Inventory entry not found")
        return entry
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/entries/{entry_id}/approve", response_model=InventoryEntryResponse)
def approve_inventory_entry(
    entry_id: int,
    db: Session = Depends(get_tenant_db),
    inventory_service: InventoryEntryService = Depends(get_inventory_entry_service),
    current_user: User = Depends(get_current_active_user)
):
    """Approve an inventory entry (requires supervisor+ role)"""
    # Verificar permisos
    if not can_approve_inventory(current_user):
        raise HTTPException(
            status_code=403, 
            detail="No tienes permisos para aprobar entradas de inventario. Se requiere rol de Supervisor o superior."
        )
    
    try:
        entry = inventory_service.approve_entry(db, entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Inventory entry not found")
        return entry
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/entries/{entry_id}/complete", response_model=InventoryEntryResponse)
def complete_inventory_entry(
    entry_id: int,
    db: Session = Depends(get_tenant_db),
    inventory_service: InventoryEntryService = Depends(get_inventory_entry_service),
    current_user: User = Depends(get_current_active_user)
):
    """Complete an inventory entry and update stock (requires supervisor+ role)"""
    # Verificar permisos
    if not can_complete_inventory(current_user):
        raise HTTPException(
            status_code=403, 
            detail="No tienes permisos para completar entradas de inventario. Se requiere rol de Supervisor o superior."
        )
    
    try:
        entry = inventory_service.complete_entry(db, entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Inventory entry not found")
        return entry
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/entries/{entry_id}/cancel", response_model=InventoryEntryResponse)
def cancel_inventory_entry(
    entry_id: int,
    db: Session = Depends(get_tenant_db),
    inventory_service: InventoryEntryService = Depends(get_inventory_entry_service),
    current_user: User = Depends(get_current_active_user)
):
    """Cancel an inventory entry (requires authentication)"""
    try:
        entry = inventory_service.cancel_entry(db, entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Inventory entry not found")
        return entry
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/entries/batch-update")
def batch_update_entries(
    batch_request: BatchUpdateRequest,
    db: Session = Depends(get_tenant_db),
    inventory_service: InventoryEntryService = Depends(get_inventory_entry_service),
    current_user: User = Depends(get_current_active_user)
):
    """Update status for multiple entries (requires authentication)"""
    try:
        return inventory_service.batch_update_status(db, batch_request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/entries/{entry_id}/validate")
def validate_inventory_entry(
    entry_id: int,
    validation_options: EntryValidationRequest,
    db: Session = Depends(get_tenant_db),
    inventory_service: InventoryEntryService = Depends(get_inventory_entry_service),
    current_user: User = Depends(get_current_active_user)
):
    """Validate an inventory entry before approval/completion (requires authentication)"""
    try:
        validation_options.entry_id = entry_id  # Ensure consistency
        return inventory_service.validate_entry(db, validation_options)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===== STOCK ADJUSTMENTS =====

@router.post("/stock/adjust", response_model=InventoryEntryResponse)
def create_stock_adjustment(
    adjustment: StockAdjustmentRequest,
    db: Session = Depends(get_tenant_db),
    inventory_service: InventoryEntryService = Depends(get_inventory_entry_service),
    current_user: User = Depends(get_current_active_user)
):
    """Create a quick stock adjustment (requires authentication)"""
    try:
        return inventory_service.create_quick_stock_adjustment(db, adjustment, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===== REPORTS =====

@router.get("/reports/movements", response_model=List[InventoryReport])
def get_inventory_movement_report(
    product_id: Optional[int] = Query(None, description="Filter by specific product"),
    db: Session = Depends(get_tenant_db),
    inventory_service: InventoryEntryService = Depends(get_inventory_entry_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get inventory movement report (requires authentication)"""
    return inventory_service.get_inventory_report(db, product_id=product_id)


# ===== WORKFLOWS =====

@router.post("/workflows/production", response_model=InventoryEntryResponse)
def create_production_entry(
    entry: InventoryEntryCreate,
    auto_complete: bool = Query(False, description="Auto-complete entry after creation"),
    db: Session = Depends(get_tenant_db),
    inventory_service: InventoryEntryService = Depends(get_inventory_entry_service),
    current_user: User = Depends(get_current_active_user)
):
    """Create a production entry (specialized workflow) (requires authentication)"""
    try:
        # Ensure entry type is production
        entry.entry_type = EntryType.PRODUCTION
        
        # Create entry
        created_entry = inventory_service.create_entry(db, entry, current_user.id)
        
        # Auto-complete if requested
        if auto_complete:
            # Approve first
            inventory_service.approve_entry(db, created_entry.id)
            # Then complete
            created_entry = inventory_service.complete_entry(db, created_entry.id)
        
        return created_entry
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/workflows/purchase", response_model=InventoryEntryResponse)
def create_purchase_entry(
    entry: InventoryEntryCreate,
    auto_approve: bool = Query(False, description="Auto-approve entry after creation"),
    db: Session = Depends(get_tenant_db),
    inventory_service: InventoryEntryService = Depends(get_inventory_entry_service),
    current_user: User = Depends(get_current_active_user)
):
    """Create a purchase entry (specialized workflow) (requires authentication)"""
    try:
        # Ensure entry type is purchase
        entry.entry_type = EntryType.PURCHASE
        
        # Create entry
        created_entry = inventory_service.create_entry(db, entry, current_user.id)
        
        # Auto-approve if requested
        if auto_approve:
            created_entry = inventory_service.approve_entry(db, created_entry.id)
        
        return created_entry
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===== UTILITIES =====

@router.get("/types")
def get_entry_types(
    current_user: User = Depends(get_current_active_user)
):
    """Get available entry types (requires authentication)"""
    return {
        "entry_types": [
            {"value": entry_type.value, "label": entry_type.value.title().replace("_", " ")}
            for entry_type in EntryType
        ]
    }


@router.get("/statuses")
def get_entry_statuses(
    current_user: User = Depends(get_current_active_user)
):
    """Get available entry statuses (requires authentication)"""
    return {
        "statuses": [
            {"value": status.value, "label": status.value.title().replace("_", " ")}
            for status in EntryStatus
        ]
    }

