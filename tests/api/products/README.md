# Tests de Productos

Este directorio contiene los tests para los endpoints de productos.

## 📋 Tests Implementados

### `TestProductEndpoints`

#### ✅ Test de Creación
- **`test_create_product_endpoint`** - Crea un producto y verifica que se guardó en la BD
- **`test_create_product_with_minimal_data`** - Crea producto con datos mínimos (nombre y precio)
- **`test_create_product_without_authentication`** - Verifica que sin auth devuelve 403

#### ✅ Test de Lectura
- **`test_get_products_endpoint`** - Obtiene lista de productos usando factory
- **`test_get_product_by_id`** - Obtiene un producto específico por ID

#### ✅ Test de Actualización
- **`test_update_product_endpoint`** - Actualiza un producto y verifica en BD
- **`test_update_product_not_found`** - Verifica que devuelve 404 si no existe

#### ✅ Test de Eliminación
- **`test_delete_product_endpoint`** - Elimina (soft delete) y verifica is_active=False
- **`test_delete_product_not_found`** - Verifica que devuelve 404 si no existe

## 🚀 Ejecutar Tests

### Todos los tests de productos
```bash
pipenv run pytest tests/api/products/ -v
```

### Un test específico
```bash
pipenv run pytest tests/api/products/test_product_endpoints.py::TestProductEndpoints::test_create_product_endpoint -v
```

### Con cobertura
```bash
pipenv run pytest tests/api/products/ --cov=app.api.v1.products --cov-report=term-missing
```

## 📊 Resultados

**9 tests** - Todos pasando ✅

## 🔧 Características de los Tests

### Uso de Factories
Los tests utilizan `ProductFactory` del sistema de factories unificado:

```python
def test_get_products_endpoint(self, authenticated_client, setup_factories):
    # Crear productos con el factory
    ProductFactory.create(name="Product 1", price=10.99, stock=100)
    ProductFactory.create(name="Product 2", price=20.50, stock=50)
    
    # Probar el endpoint
    response = authenticated_client.get("/api/v1/products/")
    assert len(response.json()) == 2
```

### Verificación en Base de Datos
Los tests verifican tanto la respuesta del endpoint como la persistencia en BD:

```python
# Verificar respuesta
assert response.status_code == 201
product_data = response.json()

# Verificar en BD
db_session.expire_all()  # Refrescar sesión
product_service = ProductService()
db_product = product_service.get_product(db_session, product_data["id"])
assert db_product.name == product_data["name"]
```

### Manejo de Sesiones
Los tests usan `db_session.expire_all()` para refrescar la sesión y ver los cambios realizados por el endpoint en su propia transacción.

## 📝 Estructura de Datos

### ProductCreate (datos completos)
```python
{
    "name": "Test Product",
    "description": "A test product description",
    "price": 99.99,
    "stock": 50,
    "sku": "TEST-PROD-001",
    "is_active": True
}
```

### ProductCreate (datos mínimos)
```python
{
    "name": "Minimal Product",
    "price": 19.99
}
# SKU se genera automáticamente: "PROD-XXXXXXXX"
# stock = 0 (default)
# is_active = True (default)
```

### ProductUpdate
```python
{
    "name": "Updated Product",  # Opcional
    "price": 75.00,             # Opcional
    "stock": 150                # Opcional
}
```

## 🔍 Endpoints Testeados

| Método | Endpoint | Código | Descripción |
|--------|----------|--------|-------------|
| POST | `/api/v1/products/` | 201 | Crear producto |
| GET | `/api/v1/products/` | 200 | Listar productos |
| GET | `/api/v1/products/{id}` | 200 | Obtener por ID |
| PUT | `/api/v1/products/{id}` | 200 | Actualizar |
| DELETE | `/api/v1/products/{id}` | 204 | Eliminar (soft) |

## 💡 Buenas Prácticas Aplicadas

1. ✅ **Uso de Factories** - Para crear datos de prueba
2. ✅ **Verificación Dual** - Respuesta + Base de datos
3. ✅ **Tests de Errores** - 404 para recursos no encontrados
4. ✅ **Tests de Seguridad** - 403 sin autenticación
5. ✅ **Manejo de Sesiones** - `expire_all()` para sincronizar
6. ✅ **Tests de Casos Edge** - Datos mínimos, producto inexistente
7. ✅ **Soft Delete** - Verifica `is_active=False` en lugar de eliminar

## 🎯 Cobertura

Los tests cubren:
- ✅ CRUD completo (Create, Read, Update, Delete)
- ✅ Validación de datos
- ✅ Autenticación y autorización
- ✅ Casos de error (404, 403)
- ✅ Generación automática de SKU
- ✅ Soft delete
- ✅ Persistencia en base de datos

