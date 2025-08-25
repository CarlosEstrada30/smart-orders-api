from typing import Optional, List
from sqlalchemy.orm import Session
from .base import BaseRepository
from ..models.client import Client
from ..schemas.client import ClientCreate, ClientUpdate


class ClientRepository(BaseRepository[Client, ClientCreate, ClientUpdate]):
    def __init__(self):
        super().__init__(Client)

    def get_by_email(self, db: Session, *, email: str) -> Optional[Client]:
        return db.query(Client).filter(Client.email == email).first()

    def get_active_clients(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[Client]:
        return db.query(Client).filter(Client.is_active == True).offset(skip).limit(limit).all()

    def search_by_name(self, db: Session, *, name: str) -> List[Client]:
        return db.query(Client).filter(Client.name.ilike(f"%{name}%")).all()
    
    def get_by_nit(self, db: Session, *, nit: str) -> Optional[Client]:
        return db.query(Client).filter(Client.nit == nit).first() 