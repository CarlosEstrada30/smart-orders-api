# Tests de API - Clientes

Este directorio contiene los tests para los endpoints de clientes de la API.

## 📁 Estructura

```
tests/api/clients/
├── __init__.py
└── test_client_endpoints.py  # Tests de endpoints de clientes
```

## 🧪 Tests Incluidos

### **Tests de Servicio (sin autenticación):**
- ✅ `test_create_client_success` - Crear cliente
- ✅ `test_get_client_by_id` - Obtener cliente por ID

### **Tests de Endpoint (con autenticación):**
- ✅ `test_create_client_endpoint` - POST /api/v1/clients/
- ✅ `test_get_clients_endpoint` - GET /api/v1/clients/
- ✅ `test_create_client_with_minimal_data` - Crear con datos mínimos

### **Tests de Validación:**
- ✅ `test_create_client_without_authentication` - Sin autenticación (debería fallar)

## 🚀 Ejecutar Tests

### **Todos los tests de clientes:**
```bash
python -m pytest tests/api/clients/ -v
```

### **Test específico:**
```bash
python -m pytest tests/api/clients/test_client_endpoints.py::TestClientSimple::test_create_client_success -v
```

### **Con el script principal:**
```bash
python run_tests.py
```

## 🔧 Fixtures Utilizados

- `db_session` - Sesión de PostgreSQL
- `client` - Cliente FastAPI básico
- `authenticated_client` - Cliente con JWT
- `sample_client_data` - Datos de cliente de muestra

## 📊 Cobertura

Los tests cubren:
- ✅ **Creación de clientes** (servicio y endpoint)
- ✅ **Obtención de clientes** (por ID y lista)
- ✅ **Autenticación** (con y sin JWT)
- ✅ **Validación de datos** (mínimos y completos)
- ✅ **Manejo de errores** (sin autenticación)

## 🎯 Casos de Uso

1. **Crear cliente con todos los datos**
2. **Crear cliente con datos mínimos**
3. **Obtener cliente por ID**
4. **Obtener lista de clientes**
5. **Validar autenticación requerida**
6. **Manejar errores de validación**

## 🔄 Flujo de Tests

```
INICIO DEL TEST
    ↓
CREAR TABLAS EN POSTGRESQL
    ↓
EJECUTAR TEST
    ↓
ELIMINAR TABLAS
    ↓
FIN DEL TEST
```

## 📈 Estadísticas

- **Total de tests:** 6
- **Tests de servicio:** 2
- **Tests de endpoint:** 4
- **Cobertura:** Endpoints principales de clientes
- **Tiempo estimado:** < 5 segundos

## 🚨 Troubleshooting

### Error de conexión a PostgreSQL:
```bash
# Verificar que PostgreSQL esté corriendo
sudo systemctl status postgresql

# Verificar variable de entorno
echo $DATABASE_URL
```

### Error de autenticación:
- Verificar que el JWT esté configurado correctamente en `conftest.py`
- Verificar que `SECRET_KEY` esté configurada

### Error de base de datos:
- Verificar que las tablas se crean correctamente
- Verificar que el usuario de test tiene permisos

