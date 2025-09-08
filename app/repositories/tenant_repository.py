from typing import Optional, List
from sqlalchemy.orm import Session
from .base import BaseRepository
from ..models.tenant import Tenant
from ..schemas.tenant import TenantCreate, TenantUpdate


class TenantRepository(BaseRepository[Tenant, TenantCreate, TenantUpdate]):
    def __init__(self):
        super().__init__(Tenant)

    def get_by_token(
            self,
            db: Session,
            *,
            token: str,
            include_inactive: bool = False) -> Optional[Tenant]:
        query = db.query(Tenant).filter(Tenant.token == token)
        if not include_inactive:
            query = query.filter(Tenant.active)
        return query.first()

    def get_by_subdominio(
            self,
            db: Session,
            *,
            subdominio: str,
            include_inactive: bool = False) -> Optional[Tenant]:
        query = db.query(Tenant).filter(Tenant.subdominio == subdominio)
        if not include_inactive:
            query = query.filter(Tenant.active)
        return query.first()

    def get_by_schema_name(
            self,
            db: Session,
            *,
            schema_name: str,
            include_inactive: bool = False) -> Optional[Tenant]:
        """Busca un tenant por el nombre del schema"""
        query = db.query(Tenant).filter(Tenant.schema_name == schema_name)
        if not include_inactive:
            query = query.filter(Tenant.active)
        return query.first()

    def get_active_tenants(
            self,
            db: Session,
            skip: int = 0,
            limit: int = 100) -> List[Tenant]:
        """Obtiene solo los tenants activos"""
        return db.query(Tenant).filter(
            Tenant.active).offset(skip).limit(limit).all()

    def get_all_tenants(self, db: Session, skip: int = 0,
                        limit: int = 100) -> List[Tenant]:
        """Obtiene todos los tenants, incluyendo inactivos"""
        return db.query(Tenant).offset(skip).limit(limit).all()

    def soft_delete(self, db: Session, *, id: int) -> Optional[Tenant]:
        """Realiza soft delete marcando active=False"""
        db_obj = db.query(Tenant).filter(Tenant.id == id).first()
        if db_obj:
            db_obj.active = False
            db.commit()
            db.refresh(db_obj)
        return db_obj

    def restore(self, db: Session, *, id: int) -> Optional[Tenant]:
        """Restaura un tenant inactivo marcando active=True"""
        db_obj = db.query(Tenant).filter(Tenant.id == id).first()
        if db_obj:
            db_obj.active = True
            db.commit()
            db.refresh(db_obj)
        return db_obj
