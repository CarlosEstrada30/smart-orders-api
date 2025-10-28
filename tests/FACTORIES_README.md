# Sistema de Factories para Testing

Este documento explica cómo usar el sistema de factories para crear datos de prueba en los tests.

## 📋 Resumen

El sistema de factories permite crear objetos de prueba de manera fácil y consistente, sin tener que configurar manualmente la sesión de base de datos en cada test.

## 🚀 Uso Básico

### 1. Importar el factory que necesitas

```python
from tests.factories import ClientFactory, ProductFactory, OrderFactory
```

### 2. Usar el fixture `setup_factories` en tu test

```python
def test_something(self, setup_factories):
    # Crear un cliente con datos aleatorios
    client = ClientFactory.create()
    
    # Crear un cliente con datos específicos
    client = ClientFactory.create(
        name="Mi Cliente",
        email="cliente@example.com"
    )
```

## 📚 Factories Disponibles

### ClientFactory
Crea clientes de prueba.

```python
# Cliente con datos aleatorios
client = ClientFactory.create()

# Cliente con datos personalizados
client = ClientFactory.create(
    name="Empresa ABC",
    email="contacto@abc.com",
    phone="1234-5678",
    nit="12345678-9"
)

# Crear múltiples clientes
clients = ClientFactory.create_batch(5)
```

### ProductFactory
Crea productos de prueba.

```python
# Producto con datos aleatorios
product = ProductFactory.create()

# Producto con datos personalizados
product = ProductFactory.create(
    name="Producto Premium",
    price=99.99,
    stock=100,
    sku="PREM-001"
)

# Crear múltiples productos
products = ProductFactory.create_batch(10)
```

### RouteFactory
Crea rutas de prueba.

```python
# Ruta con nombre automático
route = RouteFactory.create()

# Ruta con nombre específico
route = RouteFactory.create(name="Ruta Central")

# Crear múltiples rutas
routes = RouteFactory.create_batch(3)
```

### UserFactory
Crea usuarios de prueba.

```python
# Usuario con datos aleatorios
user = UserFactory.create()

# Usuario con datos personalizados
user = UserFactory.create(
    username="testuser",
    email="test@example.com",
    role=UserRole.ADMIN
)

# Password por defecto es "test" (ya hasheada)
```

### OrderFactory
Crea órdenes de prueba (incluye cliente y ruta automáticamente).

```python
# Orden completa con cliente y ruta
order = OrderFactory.create()

# Orden con cliente específico
client = ClientFactory.create()
order = OrderFactory.create(client=client)

# Orden con datos personalizados
order = OrderFactory.create(
    total_amount=1500.00,
    discount_amount=150.0,
    status=OrderStatus.CONFIRMED
)
```

### OrderItemFactory
Crea items de orden de prueba.

```python
# Item con orden y producto automáticos
item = OrderItemFactory.create()

# Item con orden y producto específicos
order = OrderFactory.create()
product = ProductFactory.create()
item = OrderItemFactory.create(
    order=order,
    product=product,
    quantity=5
)
```

## 💡 Ejemplos Completos

### Test de Endpoint GET

```python
class TestClientEndpoint:
    def test_get_clients(self, authenticated_client, setup_factories):
        """Test del endpoint de obtener clientes."""
        # Crear clientes en la BD usando factory
        ClientFactory.create_batch(3)
        
        # Llamar al endpoint
        response = authenticated_client.get("/api/v1/clients/")
        
        assert response.status_code == 200
        clients = response.json()
        assert len(clients) == 3
```

### Test con Relaciones

```python
def test_order_with_items(self, setup_factories):
    """Test de orden con múltiples items."""
    # Crear orden con cliente y ruta
    order = OrderFactory.create()
    
    # Agregar items a la orden
    products = ProductFactory.create_batch(3)
    for product in products:
        OrderItemFactory.create(
            order=order,
            product=product,
            quantity=2
        )
    
    # Verificar
    assert len(order.items) == 3
```

### Test con Validaciones

```python
def test_client_service(self, setup_factories, db_session):
    """Test del servicio de clientes."""
    # Crear cliente
    client = ClientFactory.create(name="Test Client")
    
    # Usar el servicio
    service = ClientService()
    result = service.get_client(db_session, client.id)
    
    assert result.name == "Test Client"
```

## ⚙️ Configuración Interna

El fixture `setup_factories` se encarga automáticamente de:

1. Configurar todos los factories con la sesión de BD del test
2. Hacer commit automático después de crear cada objeto
3. Limpiar la sesión al finalizar el test

**No necesitas:**
- Configurar manualmente `ClientFactory._meta.sqlalchemy_session = db_session`
- Hacer `db_session.commit()` después de crear objetos
- Cerrar o limpiar la sesión manualmente

## 🎯 Buenas Prácticas

### ✅ Hacer

```python
# Usar el fixture setup_factories
def test_something(self, setup_factories):
    client = ClientFactory.create()

# Crear datos específicos para el test
def test_with_data(self, setup_factories):
    client = ClientFactory.create(name="Specific Name")

# Usar create_batch para múltiples objetos
def test_multiple(self, setup_factories):
    clients = ClientFactory.create_batch(10)
```

### ❌ Evitar

```python
# No configurar manualmente la sesión
def test_bad(self, db_session):
    ClientFactory._meta.sqlalchemy_session = db_session  # ❌ No hacer esto
    client = ClientFactory.create()

# No hacer commit manual
def test_bad2(self, setup_factories, db_session):
    client = ClientFactory.create()
    db_session.commit()  # ❌ No necesario, ya se hace automático

# No crear objetos sin el fixture
def test_bad3(self):
    client = ClientFactory.create()  # ❌ Faltará la sesión
```

## 🔧 Agregar Nuevos Factories

Si necesitas crear un nuevo factory, edita `tests/factories.py`:

```python
class MiNuevoFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory para MiModelo."""
    
    class Meta:
        model = MiModelo
        sqlalchemy_session_persistence = "commit"
    
    campo1 = factory.LazyAttribute(lambda _: faker.word())
    campo2 = factory.Sequence(lambda n: f"Valor {n}")
```

Luego agrégalo a la lista en `configure_factories()`:

```python
def configure_factories(session):
    factories = [
        ClientFactory,
        ProductFactory,
        MiNuevoFactory,  # ← Agregar aquí
    ]
    
    for factory_class in factories:
        factory_class._meta.sqlalchemy_session = session
```

## 📖 Recursos

- [Factory Boy Documentation](https://factoryboy.readthedocs.io/)
- [Faker Documentation](https://faker.readthedocs.io/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/14/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites)

