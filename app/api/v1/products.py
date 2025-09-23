from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io
from ...schemas.product import ProductCreate, ProductUpdate, ProductResponse
from ...schemas.bulk_upload import ProductBulkUploadResult
from ...services.product_service import ProductService
from ...utils.excel_utils import ExcelGenerator
from ..dependencies import get_product_service
from .auth import get_current_active_user, get_tenant_db
from ...models.user import User

router = APIRouter(prefix="/products", tags=["products"])


@router.post("/", response_model=ProductResponse,
             status_code=status.HTTP_201_CREATED)
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


@router.get("/export")
async def export_products(
    active_only: bool = False,
    skip: int = 0,
    limit: int = 10000,
    db: Session = Depends(get_tenant_db),
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Export products to Excel file (requires authentication)
    
    Parameters:
    - active_only: Export only active products (default: false)
    - skip: Number of records to skip (default: 0)  
    - limit: Maximum number of records to export (default: 10000)
    
    Returns an Excel file with the same format as the import template.
    """
    try:
        # Get products data
        if active_only:
            products = product_service.get_active_products(db, skip=skip, limit=limit)
        else:
            products = product_service.get_products(db, skip=skip, limit=limit)
        
        # Convert to dict format for Excel generator
        products_data = []
        for product in products:
            products_data.append({
                'name': product.name,
                'description': product.description,
                'price': product.price,
                'stock': product.stock,
                'sku': product.sku,
                'is_active': product.is_active
            })
        
        # Generate Excel data
        excel_data = ExcelGenerator.export_products_data(products_data)
        
        # Generate filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"productos_export_{timestamp}.xlsx"
        
        return StreamingResponse(
            io.BytesIO(excel_data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting products: {str(e)}")


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
        product = product_service.update_product(
            db, product_id, product_update)
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


@router.post("/bulk-upload", response_model=ProductBulkUploadResult)
async def bulk_upload_products(
    file: UploadFile = File(..., description="Excel file with product data"),
    db: Session = Depends(get_tenant_db),
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Bulk upload products from Excel file (requires authentication)
    
    The Excel file should preferably have a 'Productos' sheet, but any sheet will work.
    Accepts column names in Spanish or English:
    
    REQUIRED COLUMNS (any of these names):
    - nombre / name / Name / Nombre / NOMBRE: Product name
    - precio / price / Price / Precio / PRECIO: Product price (must be > 0)
    - sku / SKU / codigo / código / Codigo / Código: Product SKU (must be unique)
    
    OPTIONAL COLUMNS (any of these names):
    - descripcion / description / Description / Descripción: Product description
    - stock / Stock / inventario / Inventario: Stock quantity (default: 0)
    - activo / is_active / active / Active: true/false for active status (default: true)
    
    Download the template using GET /api/v1/products/template/download for the correct format.
    """
    try:
        result = await product_service.bulk_upload_products(db, file)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@router.get("/template/download")
async def download_products_template(
    current_user: User = Depends(get_current_active_user)
):
    """
    Download Excel template for bulk product upload (requires authentication)
    """
    try:
        excel_data = ExcelGenerator.create_products_template()
        
        return StreamingResponse(
            io.BytesIO(excel_data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=plantilla_productos.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating template: {str(e)}")
