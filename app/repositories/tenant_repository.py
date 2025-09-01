from typing import Optional
from sqlalchemy.orm import Session
from .base import BaseRepository
from ..models.tenant import Tenant
from ..schemas.tenant import TenantCreate, TenantUpdate


class TenantRepository(BaseRepository[Tenant, TenantCreate, TenantUpdate]):
    def __init__(self):
        super().__init__(Tenant)

    def get_by_token(self, db: Session, *, token: str) -> Optional[Tenant]:
        return db.query(Tenant).filter(Tenant.token == token).first()

    def get_by_subdominio(self, db: Session, *, subdominio: str) -> Optional[Tenant]:
        return db.query(Tenant).filter(Tenant.subdominio == subdominio).first()

    def get_by_schema_name(self, db: Session, *, schema_name: str) -> Optional[Tenant]:
        """Busca un tenant por el nombre del schema"""
        return db.query(Tenant).filter(Tenant.schema_name == schema_name).first()
