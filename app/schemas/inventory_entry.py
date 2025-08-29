from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from ..models.inventory_entry import EntryType, EntryStatus


class InventoryEntryItemBase(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0, description="Quantity must be greater than 0")
    unit_cost: float = Field(default=0.0, ge=0, description="Unit cost must be non-negative")
    batch_number: Optional[str] = Field(None, max_length=100)
    expiry_date: Optional[datetime] = None
    notes: Optional[str] = None

    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be greater than 0')
        return v


class InventoryEntryItemCreate(InventoryEntryItemBase):
    pass


class InventoryEntryItemUpdate(BaseModel):
    quantity: Optional[int] = Field(None, gt=0)
    unit_cost: Optional[float] = Field(None, ge=0)
    batch_number: Optional[str] = Field(None, max_length=100)
    expiry_date: Optional[datetime] = None
    notes: Optional[str] = None


class InventoryEntryItemResponse(InventoryEntryItemBase):
    id: int
    entry_id: int
    total_cost: float
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    product_description: Optional[str] = None

    class Config:
        from_attributes = True


class InventoryEntryBase(BaseModel):
    entry_type: EntryType
    supplier_info: Optional[str] = Field(None, max_length=255)
    expected_date: Optional[datetime] = None
    notes: Optional[str] = None
    reference_document: Optional[str] = Field(None, max_length=100)


class InventoryEntryCreate(InventoryEntryBase):
    items: List[InventoryEntryItemCreate] = Field(..., min_items=1)

    @validator('items')
    def validate_items(cls, v):
        if not v:
            raise ValueError('At least one item is required')
        return v


class InventoryEntryUpdate(BaseModel):
    entry_type: Optional[EntryType] = None
    status: Optional[EntryStatus] = None
    supplier_info: Optional[str] = Field(None, max_length=255)
    expected_date: Optional[datetime] = None
    notes: Optional[str] = None
    reference_document: Optional[str] = Field(None, max_length=100)


class InventoryEntryResponse(InventoryEntryBase):
    id: int
    entry_number: str
    status: EntryStatus
    user_id: int
    total_cost: float
    entry_date: datetime
    completed_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    items: List[InventoryEntryItemResponse] = []
    user_name: Optional[str] = None  # Will be populated from user relationship

    class Config:
        from_attributes = True


class InventoryEntryListResponse(BaseModel):
    id: int
    entry_number: str
    entry_type: EntryType
    status: EntryStatus
    total_cost: float
    entry_date: datetime
    completed_date: Optional[datetime] = None
    user_name: Optional[str] = None
    items_count: int = 0
    supplier_info: Optional[str] = None

    class Config:
        from_attributes = True


class InventoryEntrySummary(BaseModel):
    """Summary for dashboard/reports"""
    total_entries: int
    total_cost: float
    entries_by_type: dict
    entries_by_status: dict
    pending_entries: int
    completed_today: int


class BatchUpdateRequest(BaseModel):
    """For batch operations"""
    entry_ids: List[int] = Field(..., min_items=1)
    status: EntryStatus


class StockAdjustmentRequest(BaseModel):
    """For quick stock adjustments"""
    product_id: int
    quantity: int = Field(..., description="Positive for increase, negative for decrease")
    reason: str = Field(..., max_length=255)
    notes: Optional[str] = None


class InventoryReport(BaseModel):
    """Inventory movement report"""
    product_id: int
    product_name: str
    product_sku: Optional[str] = None
    current_stock: int
    total_entries: int
    total_quantity_added: int
    last_entry_date: Optional[datetime] = None
    average_cost: float


class EntryValidationRequest(BaseModel):
    """For validating entries before approval"""
    entry_id: int
    validate_stock: bool = True
    validate_costs: bool = True

