from typing import Optional, BinaryIO
from sqlalchemy.orm import Session
import boto3
import uuid
import os
from botocore.exceptions import ClientError, NoCredentialsError
from ..repositories.settings_repository import SettingsRepository
from ..schemas.settings import SettingsCreate, SettingsUpdate
from ..models.settings import Settings
from ..config import settings


class SettingsService:
    def __init__(self):
        self.repository = SettingsRepository()
        self._s3_client = None

    @property
    def s3_client(self):
        """
        Lazy initialization del cliente S3 para Cloudflare R2
        """
        if self._s3_client is None:
            if not all([
                settings.R2_ACCOUNT_ID,
                settings.R2_ACCESS_KEY_ID, 
                settings.R2_SECRET_ACCESS_KEY,
                settings.R2_BUCKET_NAME
            ]):
                raise ValueError("Cloudflare R2 configuration is incomplete. Check environment variables.")
            
            # Construir endpoint URL si no se proporciona
            endpoint_url = settings.R2_ENDPOINT_URL
            if not endpoint_url:
                endpoint_url = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
            
            self._s3_client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                region_name='auto'  # Cloudflare R2 usa 'auto' como región
            )
        
        return self._s3_client

    def get_company_settings(self, db: Session) -> Optional[Settings]:
        """Obtiene la configuración única de la empresa"""
        return self.repository.get_company_settings(db)

    def get_settings_by_id(self, db: Session, settings_id: int) -> Optional[Settings]:
        """Obtiene configuración por ID"""
        return self.repository.get(db, settings_id)

    def create_settings(self, db: Session, settings: SettingsCreate) -> Settings:
        """Crea nueva configuración de empresa"""
        # Verificar que no exista ya una configuración activa
        existing = self.repository.get_company_settings(db)
        if existing:
            raise ValueError("Company settings already exist. Use update instead.")
        
        return self.repository.create(db, obj_in=settings)

    def update_settings(self, db: Session, settings_id: int, settings_update: SettingsUpdate) -> Optional[Settings]:
        """Actualiza configuración de empresa"""
        db_settings = self.repository.get(db, settings_id)
        if not db_settings:
            return None
        
        update_data = settings_update.model_dump(exclude_unset=True)
        return self.repository.update(db, db_obj=db_settings, obj_in=update_data)

    def upload_logo(self, db: Session, settings_id: int, file: BinaryIO, filename: str, content_type: str) -> Optional[str]:
        """
        Sube un logo a Cloudflare R2 y actualiza la URL en la configuración
        
        Args:
            db: Sesión de base de datos
            settings_id: ID de la configuración
            file: Archivo binario del logo
            filename: Nombre original del archivo
            content_type: Tipo de contenido (image/png, image/jpeg, etc.)
            
        Returns:
            URL del logo subido o None si hubo error
        """
        try:
            # Verificar que la configuración existe
            db_settings = self.repository.get(db, settings_id)
            if not db_settings:
                raise ValueError("Settings not found")

            # Generar nombre único para el archivo
            file_extension = os.path.splitext(filename)[1].lower()
            unique_filename = f"logos/{uuid.uuid4().hex}{file_extension}"

            # Subir archivo a R2
            self.s3_client.upload_fileobj(
                file,
                settings.R2_BUCKET_NAME,
                unique_filename,
                ExtraArgs={
                    'ContentType': content_type,
                    'ACL': 'public-read'  # Hacer el archivo público para acceso directo
                }
            )

            # Construir URL pública del archivo
            logo_url = f"https://pub-{settings.R2_ACCOUNT_ID}.r2.dev/{unique_filename}"

            # Actualizar la configuración con la nueva URL
            updated_settings = self.repository.update_logo_url(db, settings_id=settings_id, logo_url=logo_url)
            
            if updated_settings:
                return logo_url
            else:
                # Si falló la actualización, intentar eliminar el archivo subido
                try:
                    self.s3_client.delete_object(Bucket=settings.R2_BUCKET_NAME, Key=unique_filename)
                except:
                    pass  # Ignorar errores de limpieza
                return None

        except (ClientError, NoCredentialsError) as e:
            raise ValueError(f"Failed to upload logo to R2: {str(e)}")
        except Exception as e:
            raise ValueError(f"Unexpected error uploading logo: {str(e)}")

    def delete_logo(self, db: Session, settings_id: int, tenant_token: Optional[str] = None) -> bool:
        """
        Elimina el logo actual y limpia la URL de la configuración
        """
        try:
            db_settings = self.repository.get(db, settings_id)
            if not db_settings or not db_settings.logo_url:
                return False

            # Extraer la clave del archivo desde la URL
            if "r2.dev/" in db_settings.logo_url:
                file_key = db_settings.logo_url.split("r2.dev/")[1]
                
                # Eliminar archivo de R2
                self.s3_client.delete_object(Bucket=settings.R2_BUCKET_NAME, Key=file_key)

            # Limpiar URL de la base de datos
            self.repository.update_logo_url(db, settings_id=settings_id, logo_url=None)
            return True

        except (ClientError, NoCredentialsError) as e:
            raise ValueError(f"Failed to delete logo from R2: {str(e)}")
        except Exception as e:
            raise ValueError(f"Unexpected error deleting logo: {str(e)}")

    def create_or_update_settings(
        self, 
        db: Session, 
        settings_data: dict, 
        logo_file: Optional[BinaryIO] = None, 
        logo_filename: Optional[str] = None, 
        logo_content_type: Optional[str] = None,
        tenant_token: Optional[str] = None
    ) -> Settings:
        """
        Crea o actualiza la configuración de la empresa (solo puede haber una por tenant)
        Si se proporciona un logo, lo sube a R2 automáticamente
        """
        try:
            # Buscar si ya existe una configuración activa
            existing_settings = self.repository.get_company_settings(db)
            
            if existing_settings:
                # Actualizar configuración existente
                updated_settings = self.repository.update(db, db_obj=existing_settings, obj_in=settings_data)
            else:
                # Crear nueva configuración
                from ..schemas.settings import SettingsCreate
                settings_create = SettingsCreate(**settings_data)
                updated_settings = self.repository.create(db, obj_in=settings_create)
            
            # Si se proporcionó un logo, subirlo
            if logo_file and logo_filename and logo_content_type:
                logo_url = self._upload_logo_file(
                    db, 
                    updated_settings.id, 
                    logo_file, 
                    logo_filename, 
                    logo_content_type,
                    tenant_token
                )
                if logo_url:
                    # Actualizar con la URL del logo
                    updated_settings = self.repository.update_logo_url(
                        db, 
                        settings_id=updated_settings.id, 
                        logo_url=logo_url
                    )
            
            return updated_settings
            
        except Exception as e:
            raise ValueError(f"Failed to create or update settings: {str(e)}")

    def _upload_logo_file(self, db: Session, settings_id: int, file: BinaryIO, filename: str, content_type: str, tenant_token: Optional[str] = None) -> Optional[str]:
        """
        Método privado para subir logo con estructura de directorios por tenant
        """
        try:
            # Si existe un logo anterior, eliminarlo
            db_settings = self.repository.get(db, settings_id)
            if db_settings and db_settings.logo_url:
                try:
                    if "r2.dev/" in db_settings.logo_url:
                        file_key = db_settings.logo_url.split("r2.dev/")[1]
                        self.s3_client.delete_object(Bucket=settings.R2_BUCKET_NAME, Key=file_key)
                except:
                    pass  # Ignorar errores al eliminar logo anterior

            # Generar estructura de directorios con tenant_token
            file_extension = os.path.splitext(filename)[1].lower()
            if tenant_token:
                # Estructura: {tenant_token}/logo/logo.png
                unique_filename = f"{tenant_token}/logo/logo{file_extension}"
            else:
                # Fallback para usuarios sin tenant (schema public)
                unique_filename = f"public/logo/logo{file_extension}"

            # Subir archivo a R2
            self.s3_client.upload_fileobj(
                file,
                settings.R2_BUCKET_NAME,
                unique_filename,
                ExtraArgs={
                    'ContentType': content_type,
                    'ACL': 'public-read'
                }
            )

            # Construir URL pública del archivo
            logo_url = f"{settings.R2_PUBLIC_URL}/{unique_filename}"
            return logo_url

        except (ClientError, NoCredentialsError) as e:
            raise ValueError(f"Failed to upload logo to R2: {str(e)}")
        except Exception as e:
            raise ValueError(f"Unexpected error uploading logo: {str(e)}")

    def deactivate_settings(self, db: Session, settings_id: int) -> Optional[Settings]:
        """Desactiva configuración (soft delete)"""
        db_settings = self.repository.get(db, settings_id)
        if not db_settings:
            return None
        
        return self.repository.update(db, db_obj=db_settings, obj_in={"is_active": False})
