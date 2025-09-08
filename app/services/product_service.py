from typing import Optional, List
from sqlalchemy.orm import Session
from ..repositories.product_repository import ProductRepository
from ..schemas.product import ProductCreate, ProductUpdate
from ..models.product import Product


class ProductService:
    def __init__(self):
        self.repository = ProductRepository()

    def get_product(self, db: Session, product_id: int) -> Optional[Product]:
        return self.repository.get(db, product_id)

    def get_product_by_sku(self, db: Session, sku: str) -> Optional[Product]:
        return self.repository.get_by_sku(db, sku=sku)

    def get_products(self, db: Session, skip: int = 0,
                     limit: int = 100) -> List[Product]:
        return self.repository.get_multi(db, skip=skip, limit=limit)

    def get_active_products(
            self,
            db: Session,
            skip: int = 0,
            limit: int = 100) -> List[Product]:
        return self.repository.get_active_products(db, skip=skip, limit=limit)

    def search_products_by_name(self, db: Session, name: str) -> List[Product]:
        return self.repository.search_by_name(db, name=name)

    def get_low_stock_products(
            self,
            db: Session,
            threshold: int = 10) -> List[Product]:
        return self.repository.get_low_stock_products(db, threshold=threshold)

    def create_product(self, db: Session, product: ProductCreate) -> Product:
        # Check if product with SKU already exists
        if self.repository.get_by_sku(db, sku=product.sku):
            raise ValueError("Product with this SKU already exists")

        return self.repository.create(db, obj_in=product)

    def update_product(
            self,
            db: Session,
            product_id: int,
            product_update: ProductUpdate) -> Optional[Product]:
        db_product = self.repository.get(db, product_id)
        if not db_product:
            return None

        update_data = product_update.model_dump(exclude_unset=True)

        # Check if SKU is being updated and if it already exists
        if "sku" in update_data:
            existing_product = self.repository.get_by_sku(
                db, sku=update_data["sku"])
            if existing_product and existing_product.id != product_id:
                raise ValueError("Product with this SKU already exists")

        return self.repository.update(
            db, db_obj=db_product, obj_in=update_data)

    def delete_product(
            self,
            db: Session,
            product_id: int) -> Optional[Product]:
        # Soft delete - just mark as inactive
        db_product = self.repository.get(db, product_id)
        if not db_product:
            return None

        return self.repository.update(
            db, db_obj=db_product, obj_in={
                "is_active": False})

    def reactivate_product(
            self,
            db: Session,
            product_id: int) -> Optional[Product]:
        db_product = self.repository.get(db, product_id)
        if not db_product:
            return None

        return self.repository.update(
            db, db_obj=db_product, obj_in={
                "is_active": True})

    def update_stock(self, db: Session, product_id: int,
                     quantity: int) -> Optional[Product]:
        return self.repository.update_stock(
            db, product_id=product_id, quantity=quantity)

    def check_stock_availability(
            self,
            db: Session,
            product_id: int,
            required_quantity: int) -> bool:
        product = self.repository.get(db, product_id)
        if not product or not product.is_active:
            return False
        return product.stock >= required_quantity

    def reserve_stock(
            self,
            db: Session,
            product_id: int,
            quantity: int) -> bool:
        """Reserve stock for an order (decrease stock)"""
        if not self.check_stock_availability(db, product_id, quantity):
            return False

        return self.repository.update_stock(
            db, product_id=product_id, quantity=-quantity) is not None
