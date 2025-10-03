from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ...schemas.product_route_price import (
    ProductRoutePriceCreate,
    ProductRoutePriceUpdate,
    ProductRoutePriceResponse
)
from ...services.product_service import ProductService
from ..dependencies import get_product_service
from .auth import get_current_active_user, get_tenant_db
from ...models.user import User

router = APIRouter(prefix="/product-route-prices", tags=["product-route-prices"])


@router.post("/", response_model=ProductRoutePriceResponse,
             status_code=status.HTTP_201_CREATED)
def create_product_route_price(
    product_route_price: ProductRoutePriceCreate,
    db: Session = Depends(get_tenant_db),
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_active_user)
):
    """Crear un precio específico para un producto en una ruta"""
    try:
        route_price = product_service.set_product_route_price(
            db,
            product_route_price.product_id,
            product_route_price.route_id,
            product_route_price.price
        )

        # Obtener información adicional para la respuesta
        product = product_service.get_product(db, product_route_price.product_id)

        return ProductRoutePriceResponse(
            id=route_price.id,
            product_id=route_price.product_id,
            route_id=route_price.route_id,
            price=route_price.price,
            product_name=product.name if product else None,
            route_name=None  # TODO: Implementar cuando esté disponible
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[ProductRoutePriceResponse])
def get_all_product_route_prices(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_tenant_db),
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_active_user)
):
    """Obtener todos los precios por ruta con paginación"""
    try:
        # Obtener todos los precios con paginación
        route_prices = product_service.route_price_repository.get_multi(db, skip=skip, limit=limit)

        # Convertir a respuesta con información adicional
        response = []
        for route_price in route_prices:
            product = product_service.get_product(db, route_price.product_id)
            response.append(ProductRoutePriceResponse(
                id=route_price.id,
                product_id=route_price.product_id,
                route_id=route_price.route_id,
                price=route_price.price,
                product_name=product.name if product else None,
                route_name=None  # TODO: Implementar cuando esté disponible
            ))

        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/product/{product_id}", response_model=List[ProductRoutePriceResponse])
def get_product_route_prices(
    product_id: int,
    db: Session = Depends(get_tenant_db),
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_active_user)
):
    """Obtener todos los precios por ruta de un producto"""

    try:
        route_prices = product_service.get_product_route_prices(db, product_id)

        # Convertir a respuesta con información adicional
        response = []
        for route_price in route_prices:
            product = product_service.get_product(db, route_price.product_id)
            response.append(ProductRoutePriceResponse(
                id=route_price.id,
                product_id=route_price.product_id,
                route_id=route_price.route_id,
                price=route_price.price,
                product_name=product.name if product else None,
                route_name=None  # TODO: Implementar cuando esté disponible
            ))

        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{route_price_id}", response_model=ProductRoutePriceResponse)
def get_product_route_price(
    route_price_id: int,
    db: Session = Depends(get_tenant_db),
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_active_user)
):
    """Obtener un precio específico por ruta por ID"""

    try:
        # Obtener el precio por ruta por ID
        route_price = product_service.route_price_repository.get(db, route_price_id)
        if not route_price:
            raise HTTPException(status_code=404, detail="Product route price not found")

        # Obtener información adicional
        product = product_service.get_product(db, route_price.product_id)

        return ProductRoutePriceResponse(
            id=route_price.id,
            product_id=route_price.product_id,
            route_id=route_price.route_id,
            price=route_price.price,
            product_name=product.name if product else None,
            route_name=None  # TODO: Implementar cuando esté disponible
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{route_price_id}", response_model=ProductRoutePriceResponse)
def update_product_route_price(
    route_price_id: int,
    product_route_price: ProductRoutePriceUpdate,
    db: Session = Depends(get_tenant_db),
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_active_user)
):
    """Actualizar el precio de un producto para una ruta específica"""

    try:
        # Obtener el precio existente
        existing_price = product_service.route_price_repository.get(db, route_price_id)
        if not existing_price:
            raise HTTPException(status_code=404, detail="Product route price not found")

        # Actualizar el precio
        updated_price = product_service.route_price_repository.update(
            db,
            db_obj=existing_price,
            obj_in=product_route_price
        )

        # Obtener información adicional para la respuesta
        product = product_service.get_product(db, updated_price.product_id)

        return ProductRoutePriceResponse(
            id=updated_price.id,
            product_id=updated_price.product_id,
            route_id=updated_price.route_id,
            price=updated_price.price,
            product_name=product.name if product else None,
            route_name=None  # TODO: Implementar cuando esté disponible
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{route_price_id}")
def delete_product_route_price(
    route_price_id: int,
    db: Session = Depends(get_tenant_db),
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_active_user)
):
    """Eliminar un precio específico de un producto para una ruta por ID"""

    try:
        # Verificar que el precio existe
        existing_price = product_service.route_price_repository.get(db, route_price_id)
        if not existing_price:
            raise HTTPException(status_code=404, detail="Product route price not found")

        # Eliminar el precio
        product_service.route_price_repository.remove(db, id=route_price_id)

        return {"message": "Product route price deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/product/{product_id}/route/{route_id}")
def delete_product_route_price_by_product_route(
    product_id: int,
    route_id: int,
    db: Session = Depends(get_tenant_db),
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_active_user)
):
    """Eliminar el precio específico de un producto para una ruta"""

    try:
        success = product_service.delete_product_route_price(db, product_id, route_id)
        if not success:
            raise HTTPException(status_code=404, detail="Product route price not found")

        return {"message": "Product route price deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
