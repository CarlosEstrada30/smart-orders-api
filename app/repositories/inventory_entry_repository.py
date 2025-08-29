from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc
from datetime import datetime, timedelta
from .base import BaseRepository
from ..models.inventory_entry import InventoryEntry, InventoryEntryItem, EntryType, EntryStatus
from ..models.product import Product
from ..models.user import User
from ..schemas.inventory_entry import InventoryEntryCreate, InventoryEntryUpdate
import uuid


class InventoryEntryRepository(BaseRepository[InventoryEntry, InventoryEntryCreate, InventoryEntryUpdate]):
    def __init__(self):
        super().__init__(InventoryEntry)

    def get_by_entry_number(self, db: Session, *, entry_number: str) -> Optional[InventoryEntry]:
        return db.query(InventoryEntry).options(
            joinedload(InventoryEntry.user),
            joinedload(InventoryEntry.items).joinedload(InventoryEntryItem.product)
        ).filter(InventoryEntry.entry_number == entry_number).first()

    def get_entries_by_type(self, db: Session, *, entry_type: EntryType, skip: int = 0, limit: int = 100) -> List[InventoryEntry]:
        return db.query(InventoryEntry).options(
            joinedload(InventoryEntry.user),
            joinedload(InventoryEntry.items).joinedload(InventoryEntryItem.product)
        ).filter(InventoryEntry.entry_type == entry_type).offset(skip).limit(limit).all()

    def get_entries_by_status(self, db: Session, *, status: EntryStatus, skip: int = 0, limit: int = 100) -> List[InventoryEntry]:
        return db.query(InventoryEntry).options(
            joinedload(InventoryEntry.user),
            joinedload(InventoryEntry.items).joinedload(InventoryEntryItem.product)
        ).filter(InventoryEntry.status == status).offset(skip).limit(limit).all()

    def get_entries_by_user(self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100) -> List[InventoryEntry]:
        return db.query(InventoryEntry).options(
            joinedload(InventoryEntry.user),
            joinedload(InventoryEntry.items).joinedload(InventoryEntryItem.product)
        ).filter(InventoryEntry.user_id == user_id).offset(skip).limit(limit).all()

    def get_entries_by_date_range(self, db: Session, *, start_date: datetime, end_date: datetime, skip: int = 0, limit: int = 100) -> List[InventoryEntry]:
        return db.query(InventoryEntry).options(
            joinedload(InventoryEntry.user),
            joinedload(InventoryEntry.items).joinedload(InventoryEntryItem.product)
        ).filter(
            and_(
                InventoryEntry.entry_date >= start_date,
                InventoryEntry.entry_date <= end_date
            )
        ).offset(skip).limit(limit).all()

    def get_pending_entries(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[InventoryEntry]:
        return db.query(InventoryEntry).options(
            joinedload(InventoryEntry.user),
            joinedload(InventoryEntry.items).joinedload(InventoryEntryItem.product)
        ).filter(
            InventoryEntry.status.in_([EntryStatus.DRAFT, EntryStatus.PENDING])
        ).offset(skip).limit(limit).all()

    def get_entries_by_product(self, db: Session, *, product_id: int, skip: int = 0, limit: int = 100) -> List[InventoryEntry]:
        return db.query(InventoryEntry).options(
            joinedload(InventoryEntry.user),
            joinedload(InventoryEntry.items).joinedload(InventoryEntryItem.product)
        ).join(InventoryEntryItem).filter(
            InventoryEntryItem.product_id == product_id
        ).offset(skip).limit(limit).all()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[InventoryEntry]:
        return db.query(InventoryEntry).options(
            joinedload(InventoryEntry.user),
            joinedload(InventoryEntry.items).joinedload(InventoryEntryItem.product)
        ).order_by(desc(InventoryEntry.created_at)).offset(skip).limit(limit).all()

    def get(self, db: Session, id: int) -> Optional[InventoryEntry]:
        return db.query(InventoryEntry).options(
            joinedload(InventoryEntry.user),
            joinedload(InventoryEntry.items).joinedload(InventoryEntryItem.product)
        ).filter(InventoryEntry.id == id).first()

    def create_entry_with_items(self, db: Session, *, entry_data: InventoryEntryCreate, user_id: int) -> InventoryEntry:
        # Generate unique entry number
        entry_number = f"INV-{uuid.uuid4().hex[:8].upper()}"
        
        # Calculate total cost
        total_cost = sum(item.quantity * item.unit_cost for item in entry_data.items)
        
        # Create entry
        entry = InventoryEntry(
            entry_number=entry_number,
            entry_type=entry_data.entry_type,
            status=EntryStatus.DRAFT,
            user_id=user_id,
            supplier_info=entry_data.supplier_info,
            total_cost=total_cost,
            expected_date=entry_data.expected_date,
            notes=entry_data.notes,
            reference_document=entry_data.reference_document
        )
        db.add(entry)
        db.flush()  # Get the entry ID
        
        # Create entry items
        for item_data in entry_data.items:
            entry_item = InventoryEntryItem(
                entry_id=entry.id,
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                unit_cost=item_data.unit_cost,
                total_cost=item_data.quantity * item_data.unit_cost,
                batch_number=item_data.batch_number,
                expiry_date=item_data.expiry_date,
                notes=item_data.notes
            )
            db.add(entry_item)
        
        db.commit()
        db.refresh(entry)
        
        return entry

    def update_entry_status(self, db: Session, *, entry_id: int, status: EntryStatus) -> Optional[InventoryEntry]:
        entry = self.get(db, entry_id)
        if entry:
            entry.status = status
            if status == EntryStatus.COMPLETED:
                entry.completed_date = datetime.now()
            db.commit()
            db.refresh(entry)
        return entry

    def approve_entry(self, db: Session, *, entry_id: int) -> Optional[InventoryEntry]:
        """Approve an entry and change status to approved"""
        return self.update_entry_status(db, entry_id=entry_id, status=EntryStatus.APPROVED)

    def complete_entry(self, db: Session, *, entry_id: int) -> Optional[InventoryEntry]:
        """Complete an entry and update stock"""
        entry = self.get(db, entry_id)
        if not entry:
            return None
        
        if entry.status not in [EntryStatus.APPROVED, EntryStatus.PENDING]:
            raise ValueError(f"Cannot complete entry with status {entry.status}")
        
        # Update product stock for each item
        from ..models.product import Product
        for item in entry.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                product.stock += item.quantity
                db.add(product)
        
        # Update entry status
        entry.status = EntryStatus.COMPLETED
        entry.completed_date = datetime.now()
        
        db.commit()
        db.refresh(entry)
        
        return entry

    def cancel_entry(self, db: Session, *, entry_id: int) -> Optional[InventoryEntry]:
        """Cancel an entry"""
        entry = self.get(db, entry_id)
        if not entry:
            return None
        
        if entry.status == EntryStatus.COMPLETED:
            raise ValueError("Cannot cancel a completed entry")
        
        entry.status = EntryStatus.CANCELLED
        db.commit()
        db.refresh(entry)
        
        return entry

    def get_entry_summary(self, db: Session, *, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> dict:
        """Get summary statistics for inventory entries"""
        query = db.query(InventoryEntry)
        
        if start_date:
            query = query.filter(InventoryEntry.entry_date >= start_date)
        if end_date:
            query = query.filter(InventoryEntry.entry_date <= end_date)
        
        # Get basic counts and totals
        total_entries = query.count()
        total_cost = db.query(func.sum(InventoryEntry.total_cost)).filter(
            InventoryEntry.entry_date >= start_date if start_date else True,
            InventoryEntry.entry_date <= end_date if end_date else True
        ).scalar() or 0
        
        # Entries by type
        entries_by_type = {}
        for entry_type in EntryType:
            count = query.filter(InventoryEntry.entry_type == entry_type).count()
            entries_by_type[entry_type.value] = count
        
        # Entries by status
        entries_by_status = {}
        for status in EntryStatus:
            count = query.filter(InventoryEntry.status == status).count()
            entries_by_status[status.value] = count
        
        # Pending entries
        pending_entries = query.filter(
            InventoryEntry.status.in_([EntryStatus.DRAFT, EntryStatus.PENDING])
        ).count()
        
        # Completed today
        today = datetime.now().date()
        completed_today = query.filter(
            and_(
                InventoryEntry.status == EntryStatus.COMPLETED,
                func.date(InventoryEntry.completed_date) == today
            )
        ).count()
        
        return {
            "total_entries": total_entries,
            "total_cost": float(total_cost),
            "entries_by_type": entries_by_type,
            "entries_by_status": entries_by_status,
            "pending_entries": pending_entries,
            "completed_today": completed_today
        }

    def get_inventory_report(self, db: Session, *, product_id: Optional[int] = None) -> List[dict]:
        """Get inventory movement report"""
        
        if product_id:
            # Report for specific product
            query = db.query(
                Product.id.label('product_id'),
                Product.name.label('product_name'),
                Product.sku.label('product_sku'),
                Product.stock.label('current_stock'),
                func.count(InventoryEntryItem.id).label('total_entries'),
                func.sum(InventoryEntryItem.quantity).label('total_quantity_added'),
                func.max(InventoryEntry.entry_date).label('last_entry_date'),
                func.avg(InventoryEntryItem.unit_cost).label('average_cost')
            ).join(
                InventoryEntryItem, Product.id == InventoryEntryItem.product_id
            ).join(
                InventoryEntry, InventoryEntryItem.entry_id == InventoryEntry.id
            ).filter(
                Product.id == product_id,
                InventoryEntry.status == EntryStatus.COMPLETED
            ).group_by(Product.id).all()
        else:
            # Report for all products with entries
            query = db.query(
                Product.id.label('product_id'),
                Product.name.label('product_name'),
                Product.sku.label('product_sku'),
                Product.stock.label('current_stock'),
                func.count(InventoryEntryItem.id).label('total_entries'),
                func.sum(InventoryEntryItem.quantity).label('total_quantity_added'),
                func.max(InventoryEntry.entry_date).label('last_entry_date'),
                func.avg(InventoryEntryItem.unit_cost).label('average_cost')
            ).join(
                InventoryEntryItem, Product.id == InventoryEntryItem.product_id
            ).join(
                InventoryEntry, InventoryEntryItem.entry_id == InventoryEntry.id
            ).filter(
                InventoryEntry.status == EntryStatus.COMPLETED
            ).group_by(Product.id).all()
        
        return [
            {
                "product_id": row.product_id,
                "product_name": row.product_name,
                "product_sku": row.product_sku,
                "current_stock": row.current_stock,
                "total_entries": row.total_entries,
                "total_quantity_added": row.total_quantity_added or 0,
                "last_entry_date": row.last_entry_date,
                "average_cost": float(row.average_cost or 0)
            }
            for row in query
        ]

    def batch_update_status(self, db: Session, *, entry_ids: List[int], status: EntryStatus) -> int:
        """Update status for multiple entries"""
        updated_count = db.query(InventoryEntry).filter(
            InventoryEntry.id.in_(entry_ids)
        ).update(
            {"status": status},
            synchronize_session=False
        )
        
        if status == EntryStatus.COMPLETED:
            # Update completion date for completed entries
            db.query(InventoryEntry).filter(
                InventoryEntry.id.in_(entry_ids),
                InventoryEntry.status == EntryStatus.COMPLETED
            ).update(
                {"completed_date": datetime.now()},
                synchronize_session=False
            )
        
        db.commit()
        return updated_count

