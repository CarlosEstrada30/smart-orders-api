from typing import Optional, List
from sqlalchemy.orm import Session
from .base import BaseRepository
from ..models.product import Product
from ..schemas.product import ProductCreate, ProductUpdate


class ProductRepository(BaseRepository[Product, ProductCreate, ProductUpdate]):
    def __init__(self):
        super().__init__(Product)

    def get_by_sku(self, db: Session, *, sku: str) -> Optional[Product]:
        return db.query(Product).filter(Product.sku == sku).first()

    def get_active_products(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[Product]:
        return db.query(Product).filter(Product.is_active == True).offset(skip).limit(limit).all()

    def search_by_name(self, db: Session, *, name: str) -> List[Product]:
        return db.query(Product).filter(Product.name.ilike(f"%{name}%")).all()

    def get_low_stock_products(self, db: Session, *, threshold: int = 10) -> List[Product]:
        return db.query(Product).filter(Product.stock <= threshold).all()

    def update_stock(self, db: Session, *, product_id: int, quantity: int) -> Optional[Product]:
        product = self.get(db, product_id)
        if product:
            product.stock += quantity
            db.commit()
            db.refresh(product)
        return product 