from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime

from ..repositories.inventory_entry_repository import InventoryEntryRepository
from ..repositories.product_repository import ProductRepository
from ..repositories.user_repository import UserRepository
from ..schemas.inventory_entry import (
    InventoryEntryCreate, InventoryEntryUpdate, InventoryEntryResponse,
    InventoryEntryListResponse, InventoryEntrySummary, StockAdjustmentRequest,
    BatchUpdateRequest, InventoryReport, EntryValidationRequest,
    InventoryEntryItemResponse
)
from ..models.inventory_entry import InventoryEntry, EntryType, EntryStatus


class InventoryEntryService:
    def __init__(self):
        self.inventory_repository = InventoryEntryRepository()
        self.product_repository = ProductRepository()
        self.user_repository = UserRepository()

    def get_entry(
            self,
            db: Session,
            entry_id: int) -> Optional[InventoryEntryResponse]:
        """Get a single inventory entry by ID"""
        entry = self.inventory_repository.get(db, entry_id)
        if not entry:
            return None
        return self._process_entry_response(entry)

    def get_entry_by_number(
            self,
            db: Session,
            entry_number: str) -> Optional[InventoryEntryResponse]:
        """Get entry by entry number"""
        entry = self.inventory_repository.get_by_entry_number(
            db, entry_number=entry_number)
        if not entry:
            return None
        return self._process_entry_response(entry)

    def get_entries(
            self,
            db: Session,
            skip: int = 0,
            limit: int = 100) -> List[InventoryEntryListResponse]:
        """Get all inventory entries with pagination"""
        entries = self.inventory_repository.get_multi(
            db, skip=skip, limit=limit)
        return [self._process_entry_list_response(entry) for entry in entries]

    def get_entries_by_type(
            self,
            db: Session,
            entry_type: EntryType,
            skip: int = 0,
            limit: int = 100) -> List[InventoryEntryListResponse]:
        """Get entries by type"""
        entries = self.inventory_repository.get_entries_by_type(
            db, entry_type=entry_type, skip=skip, limit=limit)
        return [self._process_entry_list_response(entry) for entry in entries]

    def get_entries_by_status(
            self,
            db: Session,
            status: EntryStatus,
            skip: int = 0,
            limit: int = 100) -> List[InventoryEntryListResponse]:
        """Get entries by status"""
        entries = self.inventory_repository.get_entries_by_status(
            db, status=status, skip=skip, limit=limit)
        return [self._process_entry_list_response(entry) for entry in entries]

    def get_entries_by_user(
            self,
            db: Session,
            user_id: int,
            skip: int = 0,
            limit: int = 100) -> List[InventoryEntryListResponse]:
        """Get entries by user"""
        entries = self.inventory_repository.get_entries_by_user(
            db, user_id=user_id, skip=skip, limit=limit)
        return [self._process_entry_list_response(entry) for entry in entries]

    def get_pending_entries(
            self,
            db: Session,
            skip: int = 0,
            limit: int = 100) -> List[InventoryEntryListResponse]:
        """Get pending entries (draft or pending approval)"""
        entries = self.inventory_repository.get_pending_entries(
            db, skip=skip, limit=limit)
        return [self._process_entry_list_response(entry) for entry in entries]

    def get_entries_by_product(
            self,
            db: Session,
            product_id: int,
            skip: int = 0,
            limit: int = 100) -> List[InventoryEntryListResponse]:
        """Get entries that include a specific product"""
        entries = self.inventory_repository.get_entries_by_product(
            db, product_id=product_id, skip=skip, limit=limit)
        return [self._process_entry_list_response(entry) for entry in entries]

    def get_entries_by_date_range(
            self,
            db: Session,
            start_date: datetime,
            end_date: datetime,
            skip: int = 0,
            limit: int = 100) -> List[InventoryEntryListResponse]:
        """Get entries by date range"""
        entries = self.inventory_repository.get_entries_by_date_range(
            db, start_date=start_date, end_date=end_date, skip=skip, limit=limit)
        return [self._process_entry_list_response(entry) for entry in entries]

    def create_entry(
            self,
            db: Session,
            entry_data: InventoryEntryCreate,
            user_id: int) -> InventoryEntryResponse:
        """Create a new inventory entry"""

        # Validate all products exist and are active
        for item in entry_data.items:
            product = self.product_repository.get(db, item.product_id)
            if not product or not product.is_active:
                raise ValueError(
                    f"Product {item.product_id} not found or inactive")

        # Validate user exists
        user = self.user_repository.get(db, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Create the entry
        entry = self.inventory_repository.create_entry_with_items(
            db, entry_data=entry_data, user_id=user_id)

        # Update product stock based on entry type
        self._update_product_stock(db, entry_data)

        return self._process_entry_response(entry)

    def _update_product_stock(self, db: Session, entry_data: InventoryEntryCreate):
        """Update product stock based on inventory entry"""
        try:
            print(f"DEBUG: Updating stock for entry_type: {entry_data.entry_type}")
            for item in entry_data.items:
                print(f"DEBUG: Processing item - product_id: {item.product_id}, quantity: {item.quantity}")
                product = self.product_repository.get(db, item.product_id)
                if product:
                    print(f"DEBUG: Product found - current stock: {product.stock}")
                    # Calculate quantity change based on entry type
                    if entry_data.entry_type in ["in", "production"]:
                        quantity_change = item.quantity
                        print(f"DEBUG: Adding {item.quantity} to stock")
                    elif entry_data.entry_type == "out":
                        quantity_change = -item.quantity
                        print(f"DEBUG: Subtracting {item.quantity} from stock")

                    # Update stock using the repository method
                    updated_product = self.product_repository.update_stock(db, product_id=product.id, quantity=quantity_change)
                    if updated_product:
                        print(f"DEBUG: Product updated successfully. New stock: {updated_product.stock}")
                    else:
                        print("DEBUG: Failed to update product")
                else:
                    print(f"DEBUG: Product {item.product_id} not found")

            print("DEBUG: Stock update completed successfully")
        except Exception as e:
            print(f"DEBUG ERROR in _update_product_stock: {str(e)}")
            import traceback
            print(f"DEBUG TRACEBACK: {traceback.format_exc()}")
            db.rollback()
            raise

    def update_entry(
            self,
            db: Session,
            entry_id: int,
            entry_update: InventoryEntryUpdate) -> Optional[InventoryEntryResponse]:
        """Update an inventory entry"""
        entry = self.inventory_repository.get(db, entry_id)
        if not entry:
            return None

        # Check if entry can be updated
        if entry.status == EntryStatus.COMPLETED:
            raise ValueError("Cannot update a completed entry")

        # Update entry
        update_data = entry_update.model_dump(exclude_unset=True)
        updated_entry = self.inventory_repository.update(
            db, db_obj=entry, obj_in=update_data)

        return self._process_entry_response(updated_entry)

    def approve_entry(
            self,
            db: Session,
            entry_id: int) -> Optional[InventoryEntryResponse]:
        """Approve an entry"""
        entry = self.inventory_repository.get(db, entry_id)
        if not entry:
            return None

        if entry.status not in [EntryStatus.DRAFT, EntryStatus.PENDING]:
            raise ValueError(
                f"Cannot approve entry with status {entry.status}")

        updated_entry = self.inventory_repository.approve_entry(
            db, entry_id=entry_id)
        return self._process_entry_response(updated_entry)

    def complete_entry(
            self,
            db: Session,
            entry_id: int) -> Optional[InventoryEntryResponse]:
        """Complete an entry and update product stock"""
        entry = self.inventory_repository.get(db, entry_id)
        if not entry:
            return None

        if entry.status not in [EntryStatus.APPROVED, EntryStatus.PENDING]:
            raise ValueError(
                f"Cannot complete entry with status {entry.status}. Entry must be approved first.")

        # Complete entry and update stock
        updated_entry = self.inventory_repository.complete_entry(
            db, entry_id=entry_id)
        return self._process_entry_response(updated_entry)

    def cancel_entry(
            self,
            db: Session,
            entry_id: int) -> Optional[InventoryEntryResponse]:
        """Cancel an entry"""
        entry = self.inventory_repository.get(db, entry_id)
        if not entry:
            return None

        if entry.status == EntryStatus.COMPLETED:
            raise ValueError("Cannot cancel a completed entry")

        updated_entry = self.inventory_repository.cancel_entry(
            db, entry_id=entry_id)
        return self._process_entry_response(updated_entry)

    def batch_update_status(
            self,
            db: Session,
            batch_request: BatchUpdateRequest) -> dict:
        """Update status for multiple entries"""

        # Validate all entries exist and can be updated
        for entry_id in batch_request.entry_ids:
            entry = self.inventory_repository.get(db, entry_id)
            if not entry:
                raise ValueError(f"Entry {entry_id} not found")

            if batch_request.status == EntryStatus.COMPLETED and entry.status not in [
                    EntryStatus.APPROVED, EntryStatus.PENDING]:
                raise ValueError(
                    f"Entry {entry_id} cannot be completed with status {entry.status}")

        # Perform batch update
        updated_count = self.inventory_repository.batch_update_status(
            db, entry_ids=batch_request.entry_ids, status=batch_request.status
        )

        # If completing entries, update stock
        if batch_request.status == EntryStatus.COMPLETED:
            for entry_id in batch_request.entry_ids:
                entry = self.inventory_repository.get(db, entry_id)
                if entry:
                    # Update stock for each item
                    for item in entry.items:
                        product = self.product_repository.get(
                            db, item.product_id)
                        if product:
                            product.stock += item.quantity
                            db.add(product)
            db.commit()

        return {
            "message": f"Updated {updated_count} entries to status {batch_request.status}",
            "updated_count": updated_count,
            "entry_ids": batch_request.entry_ids}

    def create_quick_stock_adjustment(
            self,
            db: Session,
            adjustment: StockAdjustmentRequest,
            user_id: int) -> InventoryEntryResponse:
        """Create a quick stock adjustment entry"""

        # Validate product exists
        product = self.product_repository.get(db, adjustment.product_id)
        if not product or not product.is_active:
            raise ValueError(
                f"Product {adjustment.product_id} not found or inactive")

        # Check for negative stock
        if adjustment.quantity < 0 and product.stock + adjustment.quantity < 0:
            raise ValueError(
                f"Cannot reduce stock below zero. Current stock: {product.stock}")

        # Determine entry type based on quantity
        entry_type = EntryType.ADJUSTMENT

        # Create entry data
        from ..schemas.inventory_entry import InventoryEntryCreate, InventoryEntryItemCreate

        entry_data = InventoryEntryCreate(
            entry_type=entry_type,
            notes=f"Stock adjustment: {adjustment.reason}. {adjustment.notes or ''}",
            items=[
                InventoryEntryItemCreate(
                    product_id=adjustment.product_id,
                    # Always positive in entry
                    quantity=abs(adjustment.quantity),
                    unit_cost=0.0,  # Adjustments don't have cost
                    notes=adjustment.notes
                )
            ]
        )

        # Create and immediately complete the entry
        entry = self.inventory_repository.create_entry_with_items(
            db, entry_data=entry_data, user_id=user_id)

        # Auto-approve and complete for adjustments
        self.inventory_repository.update_entry_status(
            db, entry_id=entry.id, status=EntryStatus.APPROVED)

        # Update stock directly (handle negative adjustments)
        product.stock += adjustment.quantity
        db.add(product)

        # Mark as completed
        completed_entry = self.inventory_repository.update_entry_status(
            db, entry_id=entry.id, status=EntryStatus.COMPLETED)

        return self._process_entry_response(completed_entry)

    def get_entry_summary(
            self,
            db: Session,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None) -> InventoryEntrySummary:
        """Get inventory entry summary/statistics"""
        summary_data = self.inventory_repository.get_entry_summary(
            db, start_date=start_date, end_date=end_date)
        return InventoryEntrySummary(**summary_data)

    def get_inventory_report(
            self,
            db: Session,
            product_id: Optional[int] = None) -> List[InventoryReport]:
        """Get inventory movement report"""
        report_data = self.inventory_repository.get_inventory_report(
            db, product_id=product_id)
        return [InventoryReport(**item) for item in report_data]

    def _validate_products(self, db: Session, entry, validation_results: dict):
        """Validate that all products exist and are active"""
        for item in entry.items:
            product = self.product_repository.get(db, item.product_id)
            if not product:
                validation_results["errors"].append(
                    f"Product {item.product_id} not found")
                validation_results["valid"] = False
            elif not product.is_active:
                validation_results["errors"].append(
                    f"Product {product.name} is inactive")
                validation_results["valid"] = False

    def _validate_costs(self, entry, validation_results: dict):
        """Validate costs for entry items if requested"""
        for item in entry.items:
            if item.unit_cost < 0:
                validation_results["errors"].append(
                    f"Negative unit cost for product {item.product_id}")
                validation_results["valid"] = False
            elif item.unit_cost == 0 and entry.entry_type in [EntryType.PURCHASE, EntryType.PRODUCTION]:
                validation_results["warnings"].append(
                    f"Zero cost for product {item.product_id} in {entry.entry_type} entry")

    def _validate_stock_quantities(self, entry, validation_results: dict):
        """Validate stock quantities for entry items if requested"""
        for item in entry.items:
            if item.quantity <= 0:
                validation_results["errors"].append(
                    f"Invalid quantity for product {item.product_id}")
                validation_results["valid"] = False

    def validate_entry(
            self,
            db: Session,
            validation_request: EntryValidationRequest) -> dict:
        """Validate an entry before approval/completion"""
        entry = self.inventory_repository.get(db, validation_request.entry_id)
        if not entry:
            raise ValueError(f"Entry {validation_request.entry_id} not found")

        validation_results = {
            "entry_id": validation_request.entry_id,
            "valid": True,
            "errors": [],
            "warnings": []
        }

        # Validate products exist and are active
        self._validate_products(db, entry, validation_results)

        # Validate costs if requested
        if validation_request.validate_costs:
            self._validate_costs(entry, validation_results)

        # Validate stock quantities if requested
        if validation_request.validate_stock:
            self._validate_stock_quantities(entry, validation_results)

        return validation_results

    def _process_entry_response(
            self, entry: InventoryEntry) -> InventoryEntryResponse:
        """Process entry and create response with complete data"""
        # Process items
        processed_items = []
        for item in entry.items:
            item_data = {
                "id": item.id,
                "entry_id": item.entry_id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_cost": item.unit_cost,
                "total_cost": item.total_cost,
                "batch_number": item.batch_number,
                "expiry_date": item.expiry_date,
                "notes": item.notes,
                "product_name": item.product.name if item.product else None,
                "product_sku": item.product.sku if item.product else None,
                "product_description": item.product.description if item.product else None}
            processed_items.append(InventoryEntryItemResponse(**item_data))

        # Create entry response
        entry_data = {
            "id": entry.id,
            "entry_number": entry.entry_number,
            "entry_type": entry.entry_type,
            "status": entry.status,
            "user_id": entry.user_id,
            "supplier_info": entry.supplier_info,
            "total_cost": entry.total_cost,
            "entry_date": entry.entry_date,
            "expected_date": entry.expected_date,
            "completed_date": entry.completed_date,
            "notes": entry.notes,
            "reference_document": entry.reference_document,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
            "items": processed_items,
            "user_name": entry.user.full_name if entry.user else None
        }
        return InventoryEntryResponse(**entry_data)

    def _process_entry_list_response(
            self, entry: InventoryEntry) -> InventoryEntryListResponse:
        """Process entry for list response"""
        entry_data = {
            "id": entry.id,
            "entry_number": entry.entry_number,
            "entry_type": entry.entry_type,
            "status": entry.status,
            "total_cost": entry.total_cost,
            "entry_date": entry.entry_date,
            "completed_date": entry.completed_date,
            "user_name": entry.user.full_name if entry.user else None,
            "items_count": len(entry.items),
            "supplier_info": entry.supplier_info
        }
        return InventoryEntryListResponse(**entry_data)
