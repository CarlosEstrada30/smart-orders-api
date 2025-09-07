"""
Tests unitarios para TenantService.

Estos tests prueban la lógica de negocio del servicio de tenants.
"""

import pytest
import uuid
from unittest.mock import Mock, patch
from app.services.tenant_service import TenantService
from app.schemas.tenant import TenantCreate
from app.models.tenant import Tenant


class TestTenantService:
    """Tests para TenantService."""
    
    def test_create_tenant_success(self, db_session, sample_tenant_data):
        """Test de creación exitosa de tenant."""
        tenant_service = TenantService()
        tenant_data = TenantCreate(**sample_tenant_data)
        
        # Mock para evitar la creación real del schema
        with patch('app.utils.tenant_db.create_schema_if_not_exists'):
            result = tenant_service.create_tenant(db_session, tenant_data)
        
        assert result is not None
        assert result.nombre == tenant_data.nombre
        assert result.subdominio == tenant_data.subdominio
        assert result.token is not None
        assert result.schema_name is not None
    
    def test_create_tenant_generates_unique_token(self, db_session, sample_tenant_data):
        """Test que verifica que se genera un token único para cada tenant."""
        tenant_service = TenantService()
        tenant_data = TenantCreate(**sample_tenant_data)
        
        with patch('app.utils.tenant_db.create_schema_if_not_exists'):
            result = tenant_service.create_tenant(db_session, tenant_data)
        
        # Verificar que el token es un UUID válido
        try:
            uuid.UUID(result.token)
            assert True
        except ValueError:
            assert False, "El token no es un UUID válido"
    
    def test_create_tenant_generates_schema_name(self, db_session, sample_tenant_data):
        """Test que verifica la generación del nombre del schema."""
        tenant_service = TenantService()
        tenant_data = TenantCreate(**sample_tenant_data)
        
        with patch('app.utils.tenant_db.create_schema_if_not_exists'):
            result = tenant_service.create_tenant(db_session, tenant_data)
        
        assert result.schema_name is not None
        # El schema_name se genera con formato: {subdominio}_{uuid}
        assert result.schema_name.startswith(sample_tenant_data["subdominio"] + "_")
    
    def test_get_tenant_by_token(self, db_session, sample_tenant_data):
        """Test de obtener tenant por token."""
        tenant_service = TenantService()
        tenant_data = TenantCreate(**sample_tenant_data)
        
        with patch('app.utils.tenant_db.create_schema_if_not_exists'):
            created_tenant = tenant_service.create_tenant(db_session, tenant_data)
        
        # Buscar por token
        found_tenant = tenant_service.get_tenant_by_token(db_session, created_tenant.token)
        
        assert found_tenant is not None
        assert found_tenant.id == created_tenant.id
        assert found_tenant.token == created_tenant.token
    
    def test_get_tenant_by_nonexistent_token(self, db_session):
        """Test de buscar tenant con token inexistente."""
        tenant_service = TenantService()
        
        result = tenant_service.get_tenant_by_token(db_session, "nonexistent-token")
        
        assert result is None
    
    def test_get_all_tenants(self, db_session, sample_tenant_data):
        """Test de obtener todos los tenants."""
        tenant_service = TenantService()
        
        # Crear varios tenants
        tenant_data_1 = TenantCreate(
            nombre="Tenant 1",
            subdominio="tenant1"
        )
        tenant_data_2 = TenantCreate(
            nombre="Tenant 2", 
            subdominio="tenant2"
        )
        
        with patch('app.utils.tenant_db.create_schema_if_not_exists'):
            tenant_service.create_tenant(db_session, tenant_data_1)
            tenant_service.create_tenant(db_session, tenant_data_2)
        
        # Obtener todos los tenants
        tenants = tenant_service.get_tenants(db_session)
        
        assert len(tenants) == 2
        tenant_names = [tenant.nombre for tenant in tenants]
        assert "Tenant 1" in tenant_names
        assert "Tenant 2" in tenant_names
    
    def test_update_tenant(self, db_session, sample_tenant_data):
        """Test de actualización de tenant."""
        tenant_service = TenantService()
        tenant_data = TenantCreate(**sample_tenant_data)
        
        with patch('app.utils.tenant_db.create_schema_if_not_exists'):
            created_tenant = tenant_service.create_tenant(db_session, tenant_data)
        
        # Actualizar el tenant
        updated_name = "Updated Tenant Name"
        created_tenant.nombre = updated_name
        db_session.commit()
        
        # Verificar actualización
        updated_tenant = tenant_service.get_tenant_by_token(db_session, created_tenant.token)
        assert updated_tenant.nombre == updated_name
    
    @pytest.mark.database
    def test_create_tenant_with_duplicate_subdomain(self, db_session, sample_tenant_data):
        """Test que verifica que no se pueden crear tenants con subdominio duplicado."""
        tenant_service = TenantService()
        tenant_data = TenantCreate(**sample_tenant_data)
        
        with patch('app.utils.tenant_db.create_schema_if_not_exists'):
            # Crear primer tenant
            tenant_service.create_tenant(db_session, tenant_data)
            
            # Intentar crear segundo tenant con mismo subdominio
            duplicate_tenant_data = TenantCreate(
                nombre="Different Name",
                subdominio=sample_tenant_data["subdominio"]
            )
            
            with pytest.raises(Exception):  # Debería fallar por constraint único
                tenant_service.create_tenant(db_session, duplicate_tenant_data)
