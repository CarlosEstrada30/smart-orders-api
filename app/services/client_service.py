from typing import Optional, List
from sqlalchemy.orm import Session
from ..repositories.client_repository import ClientRepository
from ..schemas.client import ClientCreate, ClientUpdate, ClientResponse
from ..models.client import Client


class ClientService:
    def __init__(self):
        self.repository = ClientRepository()

    def get_client(self, db: Session, client_id: int) -> Optional[Client]:
        return self.repository.get(db, client_id)

    def get_client_by_email(self, db: Session, email: str) -> Optional[Client]:
        return self.repository.get_by_email(db, email=email)

    def get_clients(self, db: Session, skip: int = 0, limit: int = 100) -> List[Client]:
        return self.repository.get_multi(db, skip=skip, limit=limit)

    def get_active_clients(self, db: Session, skip: int = 0, limit: int = 100) -> List[Client]:
        return self.repository.get_active_clients(db, skip=skip, limit=limit)

    def search_clients_by_name(self, db: Session, name: str) -> List[Client]:
        return self.repository.search_by_name(db, name=name)

    def create_client(self, db: Session, client: ClientCreate) -> Client:
        # Check if client with email already exists
        if self.repository.get_by_email(db, email=client.email):
            raise ValueError("Client with this email already exists")
        
        return self.repository.create(db, obj_in=client)

    def update_client(self, db: Session, client_id: int, client_update: ClientUpdate) -> Optional[Client]:
        db_client = self.repository.get(db, client_id)
        if not db_client:
            return None
        
        update_data = client_update.model_dump(exclude_unset=True)
        
        # Check if email is being updated and if it already exists
        if "email" in update_data:
            existing_client = self.repository.get_by_email(db, email=update_data["email"])
            if existing_client and existing_client.id != client_id:
                raise ValueError("Client with this email already exists")
        
        return self.repository.update(db, db_obj=db_client, obj_in=update_data)

    def delete_client(self, db: Session, client_id: int) -> Optional[Client]:
        # Soft delete - just mark as inactive
        db_client = self.repository.get(db, client_id)
        if not db_client:
            return None
        
        return self.repository.update(db, db_obj=db_client, obj_in={"is_active": False})

    def reactivate_client(self, db: Session, client_id: int) -> Optional[Client]:
        db_client = self.repository.get(db, client_id)
        if not db_client:
            return None
        
        return self.repository.update(db, db_obj=db_client, obj_in={"is_active": True}) 