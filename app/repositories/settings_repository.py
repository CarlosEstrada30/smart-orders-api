from typing import Optional
from sqlalchemy.orm import Session
from .base import BaseRepository
from ..models.settings import Settings
from ..schemas.settings import SettingsCreate, SettingsUpdate


class SettingsRepository(
        BaseRepository[Settings, SettingsCreate, SettingsUpdate]):
    def __init__(self):
        super().__init__(Settings)

    def get_company_settings(self, db: Session) -> Optional[Settings]:
        """
        Obtiene la configuración de la empresa (debería ser única por tenant)
        """
        return db.query(Settings).filter(Settings.is_active).first()

    def get_by_nit(self, db: Session, *, nit: str) -> Optional[Settings]:
        """
        Busca configuración por NIT
        """
        return db.query(Settings).filter(Settings.nit == nit).first()

    def update_logo_url(
            self,
            db: Session,
            *,
            settings_id: int,
            logo_url: str) -> Optional[Settings]:
        """
        Actualiza la URL del logo de la empresa
        """
        settings = self.get(db, settings_id)
        if settings:
            settings.logo_url = logo_url
            db.commit()
            db.refresh(settings)
        return settings
