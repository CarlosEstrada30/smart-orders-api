from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ...database import get_db
from ...schemas.client import ClientCreate, ClientUpdate, ClientResponse
from ...services.client_service import ClientService
from ..dependencies import get_client_service
from .auth import get_current_active_user
from ...models.user import User

router = APIRouter(prefix="/clients", tags=["clients"])


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    client: ClientCreate,
    db: Session = Depends(get_db),
    client_service: ClientService = Depends(get_client_service),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new client (requires authentication)"""
    try:
        return client_service.create_client(db, client)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[ClientResponse])
def get_clients(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    db: Session = Depends(get_db),
    client_service: ClientService = Depends(get_client_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get all clients (requires authentication)"""
    if active_only:
        return client_service.get_active_clients(db, skip=skip, limit=limit)
    return client_service.get_clients(db, skip=skip, limit=limit)


@router.get("/search", response_model=List[ClientResponse])
def search_clients(
    name: str,
    db: Session = Depends(get_db),
    client_service: ClientService = Depends(get_client_service),
    current_user: User = Depends(get_current_active_user)
):
    """Search clients by name (requires authentication)"""
    return client_service.search_clients_by_name(db, name=name)


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    client_service: ClientService = Depends(get_client_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific client by ID (requires authentication)"""
    client = client_service.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    client_update: ClientUpdate,
    db: Session = Depends(get_db),
    client_service: ClientService = Depends(get_client_service),
    current_user: User = Depends(get_current_active_user)
):
    """Update a client (requires authentication)"""
    try:
        client = client_service.update_client(db, client_id, client_update)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        return client
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    client_service: ClientService = Depends(get_client_service),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a client (soft delete) (requires authentication)"""
    client = client_service.delete_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return None


@router.post("/{client_id}/reactivate", response_model=ClientResponse)
def reactivate_client(
    client_id: int,
    db: Session = Depends(get_db),
    client_service: ClientService = Depends(get_client_service),
    current_user: User = Depends(get_current_active_user)
):
    """Reactivate a deleted client (requires authentication)"""
    client = client_service.reactivate_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client 