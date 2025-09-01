from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from ...database import get_db
from ...schemas.route import RouteCreate, RouteUpdate, RouteResponse
from ...services.route_service import RouteService
from ..dependencies import get_route_service
from .auth import get_current_active_user, get_tenant_db
from ...models.user import User

router = APIRouter(prefix="/routes", tags=["routes"])


@router.post("/", response_model=RouteResponse, status_code=status.HTTP_201_CREATED)
def create_route(
    route: RouteCreate,
    db: Session = Depends(get_tenant_db),
    route_service: RouteService = Depends(get_route_service),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new route (requires authentication)"""
    try:
        return route_service.create_route(db, route)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[RouteResponse])
def get_routes(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = Query(False, description="Filter only active routes"),
    search: str = Query(None, description="Search routes by name"),
    db: Session = Depends(get_tenant_db),
    route_service: RouteService = Depends(get_route_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get all routes (requires authentication)"""
    if search:
        routes = route_service.search_routes_by_name(db, search)
        return routes
    elif active_only:
        return route_service.get_active_routes(db, skip=skip, limit=limit)
    else:
        return route_service.get_routes(db, skip=skip, limit=limit)


@router.get("/{route_id}", response_model=RouteResponse)
def get_route(
    route_id: int,
    db: Session = Depends(get_tenant_db),
    route_service: RouteService = Depends(get_route_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific route by ID (requires authentication)"""
    route = route_service.get_route(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route


@router.put("/{route_id}", response_model=RouteResponse)
def update_route(
    route_id: int,
    route_update: RouteUpdate,
    db: Session = Depends(get_tenant_db),
    route_service: RouteService = Depends(get_route_service),
    current_user: User = Depends(get_current_active_user)
):
    """Update a route (requires authentication)"""
    try:
        route = route_service.update_route(db, route_id, route_update)
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        return route
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_route(
    route_id: int,
    db: Session = Depends(get_tenant_db),
    route_service: RouteService = Depends(get_route_service),
    current_user: User = Depends(get_current_active_user)
):
    """Delete (deactivate) a route (requires authentication)"""
    route = route_service.delete_route(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return None


@router.post("/{route_id}/reactivate", response_model=RouteResponse)
def reactivate_route(
    route_id: int,
    db: Session = Depends(get_tenant_db),
    route_service: RouteService = Depends(get_route_service),
    current_user: User = Depends(get_current_active_user)
):
    """Reactivate a route (requires authentication)"""
    route = route_service.reactivate_route(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route
