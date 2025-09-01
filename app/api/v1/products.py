from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ...database import get_db
from ...schemas.product import ProductCreate, ProductUpdate, ProductResponse
from ...services.product_service import ProductService
from ..dependencies import get_product_service
from .auth import get_current_active_user, get_tenant_db
from ...models.user import User

router = APIRouter(prefix="/products", tags=["products"])


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_tenant_db),
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new product (requires authentication)"""
    try:
        return product_service.create_product(db, product)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[ProductResponse])
def get_products(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    db: Session = Depends(get_tenant_db),
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get all products (requires authentication)"""
    if active_only:
        return product_service.get_active_products(db, skip=skip, limit=limit)
    return product_service.get_products(db, skip=skip, limit=limit)


@router.get("/search", response_model=List[ProductResponse])
def search_products(
    name: str,
    db: Session = Depends(get_tenant_db),
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_active_user)
):
    """Search products by name (requires authentication)"""
    return product_service.search_products_by_name(db, name=name)


@router.get("/low-stock", response_model=List[ProductResponse])
def get_low_stock_products(
    threshold: int = 10,
    db: Session = Depends(get_tenant_db),
    product_service: ProductService = Depends(get_product_service)
):
    """Get products with low stock"""
    return product_service.get_low_stock_products(db, threshold=threshold)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_tenant_db),
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific product by ID (requires authentication)"""
    product = product_service.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/sku/{sku}", response_model=ProductResponse)
def get_product_by_sku(
    sku: str,
    db: Session = Depends(get_tenant_db),
    product_service: ProductService = Depends(get_product_service)
):
    """Get a specific product by SKU"""
    product = product_service.get_product_by_sku(db, sku=sku)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_tenant_db),
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_active_user)
):
    """Update a product (requires authentication)"""
    try:
        product = product_service.update_product(db, product_id, product_update)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_tenant_db),
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a product (soft delete) (requires authentication)"""
    product = product_service.delete_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return None


@router.post("/{product_id}/reactivate", response_model=ProductResponse)
def reactivate_product(
    product_id: int,
    db: Session = Depends(get_tenant_db),
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_active_user)
):
    """Reactivate a deleted product (requires authentication)"""
    product = product_service.reactivate_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}/stock", response_model=ProductResponse)
def update_stock(
    product_id: int,
    stock_change: int,
    db: Session = Depends(get_tenant_db),
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_active_user)
):
    """Update product stock (requires authentication)"""
    try:
        product = product_service.update_stock(db, product_id, stock_change)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) 