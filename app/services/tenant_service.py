from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging
from ..repositories.tenant_repository import TenantRepository
from ..schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from ..schemas.user import UserCreate
from ..models.tenant import Tenant
from ..models.user import UserRole
from ..services.user_service import UserService
from ..utils.tenant_db import create_schema_if_not_exists, run_migrations_for_schema, drop_schema_if_exists, get_session_for_schema

logger = logging.getLogger(__name__)


class TenantService:
    def __init__(self):
        self.repository = TenantRepository()
        self.user_service = UserService()

    def get_tenant(self, db: Session, tenant_id: int) -> Optional[Tenant]:
        return self.repository.get(db, tenant_id)

    def get_tenant_by_token(self, db: Session, token: str) -> Optional[Tenant]:
        return self.repository.get_by_token(db, token=token)

    def get_tenant_by_subdominio(self, db: Session, subdominio: str) -> Optional[Tenant]:
        return self.repository.get_by_subdominio(db, subdominio=subdominio)

    def get_tenants(self, db: Session, skip: int = 0, limit: int = 100) -> List[Tenant]:
        return self.repository.get_multi(db, skip=skip, limit=limit)

    def create_tenant(self, db: Session, tenant: TenantCreate) -> Tenant:
        """
        Crea un nuevo tenant:
        1. Valida que no exista un tenant con el mismo subdominio
        2. Crea el registro en la tabla tenants del schema public (token se autogenera como UUID)
        3. Crea un nuevo schema en la base de datos
        4. Ejecuta las migraciones en el nuevo schema
        """
        try:
            # Validar que no exista un tenant con el mismo subdominio
            # (El token se autogenera como UUID, por lo que no necesita validación)
            if self.repository.get_by_subdominio(db, subdominio=tenant.subdominio):
                raise ValueError("Ya existe un tenant con este subdominio")

            # Crear datos del tenant con schema generado
            tenant_data = tenant.model_dump()
            
            # Generar token UUID manualmente
            import uuid
            token = str(uuid.uuid4())
            tenant_data['token'] = token
            
            # Generar el nombre del schema
            clean_name = tenant_data['nombre'].replace(" ", "").lower()
            schema_name = f"{clean_name}_{token.lower()}"
            tenant_data['schema_name'] = schema_name
            
            # Validar que no exista otro tenant con el mismo schema
            if self.repository.get_by_schema_name(db, schema_name=schema_name):
                raise ValueError("Ya existe un tenant con este schema")

            # Crear el tenant en la base de datos con el schema incluido
            db_tenant = Tenant(**tenant_data)
            db.add(db_tenant)
            db.commit()
            db.refresh(db_tenant)
            
            # Crear el schema en la base de datos
            if not create_schema_if_not_exists(db_tenant.schema_name):
                raise ValueError(f"No se pudo crear el schema '{db_tenant.schema_name}'")
            
            # Ejecutar migraciones en el nuevo schema
            if not run_migrations_for_schema(db_tenant.schema_name):
                raise ValueError(f"No se pudieron ejecutar las migraciones en el schema '{db_tenant.schema_name}'")
            
            # Crear superusuario por defecto para el tenant
            self._create_default_superuser(db_tenant.schema_name, db_tenant.subdominio)
            
            logger.info(f"Tenant creado exitosamente: {db_tenant.id}, Schema: {db_tenant.schema_name}")
            return db_tenant
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error de base de datos al crear tenant: {str(e)}")
            raise ValueError(f"Error al crear tenant: {str(e)}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error al crear tenant: {str(e)}")
            raise ValueError(f"Error al crear tenant: {str(e)}")



    def update_tenant(self, db: Session, tenant_id: int, tenant_update: TenantUpdate) -> Optional[Tenant]:
        db_tenant = self.repository.get(db, tenant_id)
        if not db_tenant:
            return None
        
        update_data = tenant_update.model_dump(exclude_unset=True)
        
        # Validar unicidad si se actualiza subdominio
        # (El token no es actualizable, se autogenera como UUID)
        if "subdominio" in update_data:
            existing = self.repository.get_by_subdominio(db, subdominio=update_data["subdominio"])
            if existing and existing.id != tenant_id:
                raise ValueError("Ya existe un tenant con este subdominio")
        
        return self.repository.update(db, db_obj=db_tenant, obj_in=update_data)

    def delete_tenant(self, db: Session, tenant_id: int) -> Optional[Tenant]:
        """
        Elimina un tenant y opcionalmente su schema
        NOTA: Esta operación es destructiva y eliminará todos los datos del schema
        """
        db_tenant = self.repository.get(db, tenant_id)
        if not db_tenant:
            return None
        
        schema_name = db_tenant.schema_name
        
        # Eliminar el tenant de la base de datos
        deleted_tenant = self.repository.remove(db, id=tenant_id)
        
        # TODO: Implementar lógica para eliminar el schema si es necesario
        # CUIDADO: Esto eliminará todos los datos del tenant
        # self.drop_tenant_schema(schema_name)
        
        return deleted_tenant

    def drop_tenant_schema(self, schema_name: str) -> bool:
        """
        Elimina el schema de un tenant - OPERACIÓN DESTRUCTIVA
        
        Returns:
            bool: True si se eliminó exitosamente, False en caso contrario
        """
        return drop_schema_if_exists(schema_name)
    
    def _create_default_superuser(self, schema_name: str, subdominio: str) -> None:
        """
        Crea un superusuario por defecto en el schema del tenant
        
        Args:
            schema_name: Nombre del schema del tenant
            subdominio: Subdominio del tenant para generar credenciales
        """
        try:
            # Crear sesión específica para el schema del tenant
            tenant_db = get_session_for_schema(schema_name)
            
            # Generar credenciales basadas en el subdominio
            admin_email = f"admin@{subdominio}.com"
            admin_password = f"admin{subdominio}123"
            admin_username = f"admin_{subdominio}"
            admin_full_name = f"Administrador {subdominio.title()}"
            
            # Crear datos del usuario administrador
            admin_user_data = UserCreate(
                email=admin_email,
                username=admin_username,
                full_name=admin_full_name,
                password=admin_password,
                is_superuser=True,
                role=UserRole.ADMIN
            )
            
            try:
                # Crear el usuario administrador en el schema del tenant
                self.user_service.create_user(tenant_db, admin_user_data)
                logger.info(f"Superusuario creado exitosamente para tenant: {admin_email}")
                
            except ValueError as e:
                logger.warning(f"No se pudo crear superusuario para tenant {subdominio}: {str(e)}")
                # No lanzar excepción aquí para no fallar la creación del tenant
                
            finally:
                tenant_db.close()
                
        except Exception as e:
            logger.error(f"Error creando superusuario para tenant {subdominio}: {str(e)}")
            # No lanzar excepción aquí para no fallar la creación del tenant
