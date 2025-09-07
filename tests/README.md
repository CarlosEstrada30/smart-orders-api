# Tests para Smart Orders API

Este directorio contiene todos los tests para el proyecto Smart Orders API. Utilizamos **pytest** como framework principal de testing.

## Estructura de Tests

```
tests/
├── conftest.py              # Configuración global y fixtures
├── fixtures/                # Datos de prueba reutilizables
│   ├── __init__.py
│   └── test_data.py        # Factory de datos y mocks
├── integration/            # Tests de integración
│   ├── auth/
│   │   └── test_authentication.py
│   ├── orders/
│   └── tenants/
└── unit/                   # Tests unitarios
    ├── api/                # Tests de endpoints
    ├── repositories/       # Tests de repositorios
    └── services/           # Tests de servicios
        ├── test_tenant_service.py
        └── test_receipt_generator.py
```

## Tipos de Tests

### Tests Unitarios (`tests/unit/`)
- Prueban funciones y clases individuales
- No requieren base de datos real
- Usan mocks para dependencias externas
- Son rápidos de ejecutar

### Tests de Integración (`tests/integration/`)
- Prueban la interacción entre múltiples componentes
- Usan base de datos de prueba en memoria
- Prueban endpoints completos de la API
- Pueden ser más lentos

## Fixtures y Datos de Prueba

### Fixtures Globales (conftest.py)
- `db_session`: Sesión de base de datos para cada test
- `client`: Cliente de pruebas de FastAPI
- `sample_user_data`: Datos de usuario de muestra
- `sample_tenant_data`: Datos de tenant de muestra
- `app_settings`: Configuración de la aplicación

### Factory de Datos (test_data.py)
- `TestDataFactory`: Factory para generar datos de prueba
- Mock objects para simular modelos complejos
- Datos personalizables con overrides

## Ejecutar Tests

### Usando el script personalizado (Recomendado)

```bash
# Todos los tests
python run_tests.py

# Solo tests unitarios
python run_tests.py --type unit

# Solo tests de integración
python run_tests.py --type integration

# Tests con cobertura
python run_tests.py --coverage

# Test específico
python run_tests.py --file unit/services/test_tenant_service.py

# Función específica
python run_tests.py --file unit/services/test_tenant_service.py --function test_create_tenant_success
```

### Usando pytest directamente

```bash
# Activar entorno virtual
pipenv shell

# Todos los tests
pytest

# Tests con marcadores específicos
pytest -m unit           # Solo tests unitarios
pytest -m integration   # Solo tests de integración
pytest -m database      # Tests que requieren BD
pytest -m slow          # Tests lentos

# Archivo específico
pytest tests/unit/services/test_tenant_service.py

# Con cobertura
pytest --cov=app --cov-report=html
```

## Markers (Etiquetas)

Los tests pueden estar marcados con las siguientes etiquetas:

- `@pytest.mark.unit`: Tests unitarios
- `@pytest.mark.integration`: Tests de integración
- `@pytest.mark.database`: Tests que requieren base de datos
- `@pytest.mark.slow`: Tests que pueden tardar
- `@pytest.mark.api`: Tests de endpoints API
- `@pytest.mark.auth`: Tests de autenticación
- `@pytest.mark.tenant`: Tests de funcionalidad multitenant

## Configuración

### pytest.ini
Contiene la configuración principal de pytest incluyendo:
- Directorios de tests
- Markers personalizados
- Opciones por defecto
- Configuración de logging

### Variables de Entorno para Tests
Los tests usan estas variables de entorno automáticamente:
- `DATABASE_URL=sqlite:///:memory:` (BD en memoria)
- `SECRET_KEY=test-secret-key-for-testing-only`
- `ACCESS_TOKEN_EXPIRE_MINUTES=30`

## Mejores Prácticas

### Escritura de Tests
1. **Nombres descriptivos**: Los tests deben explicar qué prueban
2. **Arrange-Act-Assert**: Organizar el código del test claramente
3. **Un concepto por test**: Cada test debe probar una sola cosa
4. **Usar fixtures**: Reutilizar datos de prueba cuando sea posible

### Organización
1. **Tests unitarios**: Por módulo/servicio/repository
2. **Tests de integración**: Por feature/endpoint
3. **Mocks apropiados**: Mockear dependencias externas, no lógica interna
4. **Datos de prueba**: Usar factories en lugar de datos hardcodeados

### Ejemplo de Test Bien Estructurado

```python
def test_create_user_success(db_session, sample_user_data):
    """Test que verifica la creación exitosa de un usuario."""
    # Arrange
    user_service = UserService()
    user_data = UserCreate(**sample_user_data)
    
    # Act
    result = user_service.create_user(db_session, user_data)
    
    # Assert
    assert result is not None
    assert result.email == user_data.email
    assert result.name == user_data.name
```

## Migración desde scripts/

Los tests antiguos en `scripts/` se pueden migrar siguiendo estos patrones:

1. **Scripts de prueba manual** → **Tests de integración** con fixtures
2. **Tests con requests** → **TestClient** de FastAPI
3. **Datos hardcodeados** → **Fixtures** reutilizables
4. **Print statements** → **Assertions** de pytest

## Cobertura de Tests

Para generar reportes de cobertura:

```bash
# Generar reporte HTML
python run_tests.py --coverage

# El reporte se genera en htmlcov/index.html
```

## Debugging Tests

```bash
# Ver output completo
pytest -s

# Parar en el primer fallo
pytest -x

# Ver logs durante tests
pytest --log-cli-level=DEBUG
```
