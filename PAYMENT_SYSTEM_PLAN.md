# Plan de Desarrollo: Sistema de Control de Pagos de Órdenes

## 📋 Resumen Ejecutivo

Este documento describe el plan de desarrollo para implementar un sistema completo de control de pagos de órdenes. El sistema permitirá registrar pagos parciales o completos, rastrear el estado de pago de cada orden, y generar reportes de pagos pendientes.

## 🎯 Objetivos

1. **Registrar pagos** de órdenes (parciales o completos)
2. **Rastrear el estado de pago** de cada orden
3. **Gestionar múltiples pagos** por orden
4. **Calcular automáticamente** el saldo pendiente
5. **Generar reportes** de pagos y saldos pendientes
6. **Integrar con el sistema de órdenes** existente

## 🏗️ Arquitectura del Sistema

### Modelo de Datos

#### 1. Modelo `Payment` (Nuevo) - SIMPLIFICADO

```python
class PaymentStatus(str, enum.Enum):
    CONFIRMED = "confirmed"       # Pago confirmado (por defecto al crear)
    CANCELLED = "cancelled"       # Pago cancelado

class PaymentMethod(str, enum.Enum):
    CASH = "cash"                 # Efectivo
    CREDIT_CARD = "credit_card"   # Tarjeta de crédito
    DEBIT_CARD = "debit_card"     # Tarjeta de débito
    BANK_TRANSFER = "bank_transfer"  # Transferencia bancaria
    CHECK = "check"               # Cheque
    OTHER = "other"               # Otro método

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    payment_number = Column(String, unique=True, index=True, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    
    # Payment details
    amount = Column(Numeric(10, 2), nullable=False)  # Monto del pago
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.CONFIRMED)
    
    # Payment tracking
    payment_date = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text, nullable=True)  # Notas opcionales
    
    # User tracking (auditoría)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    order = relationship("Order", back_populates="payments")
    created_by = relationship("User")
```

**Simplificaciones aplicadas:**
- ✅ `PaymentStatus` solo tiene `CONFIRMED` y `CANCELLED` (eliminado `PENDING` y `REFUNDED`)
- ✅ Por defecto es `CONFIRMED` al crear
- ✅ Eliminado `reference_number` (se puede usar `notes` si es necesario)
- ✅ Mantenido `created_by_user_id` para auditoría (registrar quién crea el pago)
- ✅ Eliminado `MOBILE_PAYMENT` del enum (se puede usar `OTHER`)

#### 2. Modificaciones al Modelo `Order`

Agregar campos y relaciones al modelo `Order` existente:

```python
# Nuevos campos en Order
paid_amount = Column(Numeric(10, 2), default=0.0)  # Monto total pagado
balance_due = Column(Numeric(10, 2), nullable=False)  # Saldo pendiente
payment_status = Column(Enum(OrderPaymentStatus), default=OrderPaymentStatus.UNPAID)

# Nueva relación
payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")
```

**Nota importante:**
- `payment_status` en `Order` usa `OrderPaymentStatus` (UNPAID, PARTIAL, PAID)
- `status` en `Payment` usa `PaymentStatus` (CONFIRMED, CANCELLED)
- Son dos enums diferentes con propósitos distintos

#### 3. Enum de Estado de Pago de Orden - SIMPLIFICADO

```python
class OrderPaymentStatus(str, enum.Enum):
    UNPAID = "unpaid"           # Sin pagos
    PARTIAL = "partial"          # Pago parcial
    PAID = "paid"               # Pagado completamente
```

**Simplificación aplicada:**
- ✅ Eliminado `OVERPAID` (si se paga de más, se puede manejar como `PAID` y registrar la diferencia en `notes`)

## 📦 Componentes a Desarrollar

### 1. Modelos (`app/models/payment.py`)

- [ ] Crear modelo `Payment`
- [ ] Crear enum `PaymentStatus`
- [ ] Crear enum `PaymentMethod`
- [ ] Crear enum `OrderPaymentStatus`
- [ ] Modificar modelo `Order` para agregar campos de pago
- [ ] Agregar relación `payments` en `Order`

### 2. Esquemas (`app/schemas/payment.py`)

- [ ] `PaymentBase` - Esquema base
- [ ] `PaymentCreate` - Para crear pagos (solo amount, payment_method, notes)
- [ ] `PaymentResponse` - Respuesta con datos completos
- [ ] `OrderPaymentSummary` - Resumen de pagos de una orden
- [ ] `PaymentListResponse` - Lista paginada de pagos

**Simplificación aplicada:**
- ✅ Eliminado `PaymentUpdate` (no se actualizan pagos, solo se cancelan)

### 3. Repositorio (`app/repositories/payment_repository.py`)

- [ ] `create_payment()` - Crear nuevo pago
- [ ] `get_payment()` - Obtener pago por ID
- [ ] `get_payment_by_number()` - Obtener pago por número
- [ ] `get_payments_by_order()` - Obtener todos los pagos de una orden (solo confirmados)
- [ ] `cancel_payment()` - Cancelar pago (cambiar status a CANCELLED)
- [ ] `get_payments_with_filters()` - Filtrar pagos (por orden, fecha, método, etc.)
- [ ] `calculate_order_payment_summary()` - Calcular resumen de pagos de una orden

**Simplificación aplicada:**
- ✅ Eliminado `update_payment()` (no se actualizan pagos)
- ✅ Eliminado `delete_payment()` (solo se cancelan, no se eliminan)
- ✅ Agregado `cancel_payment()` para cancelar pagos

### 4. Servicio (`app/services/payment_service.py`)

- [ ] `create_payment()` - Crear pago (status=CONFIRMED) y actualizar orden
- [ ] `get_payment()` - Obtener pago
- [ ] `get_payments_by_order()` - Obtener pagos confirmados de una orden
- [ ] `cancel_payment()` - Cancelar pago (status=CANCELLED) y recalcular orden
- [ ] `calculate_order_balance()` - Calcular saldo pendiente (suma solo pagos confirmados)
- [ ] `update_order_payment_status()` - Actualizar estado de pago de orden automáticamente
- [ ] `get_payment_summary()` - Obtener resumen de pagos
- [ ] `validate_payment_amount()` - Validar que el pago no exceda el saldo

**Simplificación aplicada:**
- ✅ Eliminado `update_payment()` (no se actualizan pagos)
- ✅ Eliminado `delete_payment()` (solo se cancelan)
- ✅ Agregado `cancel_payment()` que recalcula automáticamente

### 5. Endpoints API (`app/api/v1/payments.py`)

- [ ] `POST /payments/` - Crear nuevo pago (status=CONFIRMED automáticamente)
- [ ] `GET /payments/` - Listar pagos (con filtros, solo confirmados por defecto)
- [ ] `GET /payments/{payment_id}` - Obtener pago específico
- [ ] `POST /payments/{payment_id}/cancel` - Cancelar pago (recalcula orden)
- [ ] `GET /orders/{order_id}/payments` - Obtener pagos de una orden
- [ ] `GET /orders/{order_id}/payment-summary` - Obtener resumen de pagos de una orden

**Simplificación aplicada:**
- ✅ Eliminado `PUT /payments/{payment_id}` (no se actualizan pagos)
- ✅ Eliminado `DELETE /payments/{payment_id}` (solo se cancelan)
- ✅ Eliminado `POST /orders/{order_id}/payments` (redundante, usar `POST /payments/` con `order_id` en el body)
- ✅ Agregado `POST /payments/{payment_id}/cancel` para cancelar pagos

### 6. Migración de Base de Datos

- [ ] Crear migración Alembic para tabla `payments`
- [ ] Agregar campos a tabla `orders` (paid_amount, balance_due, payment_status)
- [ ] Crear índices necesarios
- [ ] Migrar datos existentes (si hay órdenes sin pagos, inicializar campos)

## 🔄 Flujo de Trabajo

### Crear un Pago

1. Usuario crea un pago para una orden
2. Validar que la orden existe y está activa
3. Validar que el monto del pago no exceda el saldo pendiente
4. Crear el registro de pago con:
   - `status=CONFIRMED` (por defecto)
   - `created_by_user_id` = ID del usuario autenticado
5. Sumar el monto a `paid_amount` en la orden
6. Recalcular `balance_due = total_amount - paid_amount` en la orden
7. Actualizar `payment_status` de la orden según corresponda:
   - Si `balance_due == 0`: `PAID`
   - Si `paid_amount > 0` y `balance_due > 0`: `PARTIAL`
   - Si `paid_amount == 0`: `UNPAID`

### Cancelar un Pago

1. Validar que el pago existe y está confirmado
2. Cambiar `status` del pago a `CANCELLED`
3. Restar el monto del pago de `paid_amount` en la orden
4. Recalcular `balance_due = total_amount - paid_amount` en la orden
5. Actualizar `payment_status` de la orden según corresponda

**Simplificación aplicada:**
- ✅ Eliminado flujo de "Actualizar un Pago" (no se actualizan)
- ✅ Eliminado flujo de "Eliminar un Pago" (solo se cancelan)
- ✅ Simplificado flujo de cancelación (solo cambia status y recalcula)

## 📊 Reportes y Consultas

### Consultas Necesarias

1. **Pagos por orden**: Listar todos los pagos de una orden específica
2. **Órdenes con saldo pendiente**: Filtrar órdenes que tienen `balance_due > 0`
3. **Pagos por rango de fechas**: Filtrar pagos entre dos fechas
4. **Pagos por método**: Filtrar pagos por método de pago
5. **Resumen de pagos**: Total de pagos recibidos en un período
6. **Órdenes pagadas completamente**: Filtrar órdenes con `payment_status = PAID`

## 🔐 Permisos y Seguridad

### Permisos Necesarios

- **Crear pagos**: Requiere rol de Vendedor o superior
- **Ver pagos**: Requiere rol de Vendedor o superior
- **Cancelar pagos**: Requiere rol de Vendedor o superior (o Administrador para mayor seguridad)

### Validaciones

- No permitir pagos mayores al saldo pendiente
- No permitir cancelar pagos de órdenes ya facturadas (si aplica)
- Solo se pueden cancelar pagos con `status=CONFIRMED`
- Validar que la orden existe y está activa antes de crear pago
- Al cancelar, recalcular automáticamente los montos de la orden
- Registrar `created_by_user_id` automáticamente desde el usuario autenticado

**Simplificación aplicada:**
- ✅ Eliminado permiso de "Actualizar pagos" (no existe)
- ✅ Simplificado permiso de cancelación

## 🧪 Testing

### Tests Unitarios

- [ ] Test crear pago (status=CONFIRMED por defecto)
- [ ] Test cancelar pago
- [ ] Test cálculo de saldo pendiente (solo pagos confirmados)
- [ ] Test actualización de estado de pago de orden
- [ ] Test validaciones (monto excedido, orden inexistente, etc.)
- [ ] Test que pagos cancelados no se cuentan en paid_amount

### Tests de Integración

- [ ] Test flujo completo: crear orden → crear pago → verificar saldo
- [ ] Test múltiples pagos en una orden
- [ ] Test cancelar pago y verificar ajuste de saldo
- [ ] Test cancelar múltiples pagos y verificar recálculo correcto

## 📝 Documentación

- [ ] Documentar endpoints en código
- [ ] Actualizar README con nueva funcionalidad
- [ ] Crear ejemplos de uso de la API
- [ ] Documentar flujos de trabajo

## 🚀 Plan de Implementación por Fases

### Fase 1: Modelo de Datos y Migración (Día 1-2)

1. Crear modelo `Payment`
2. Modificar modelo `Order`
3. Crear migración Alembic
4. Probar migración en desarrollo

### Fase 2: Repositorio y Servicio (Día 3-4)

1. Crear repositorio de pagos
2. Crear servicio de pagos
3. Implementar lógica de cálculo de saldos
4. Tests unitarios de repositorio y servicio

### Fase 3: API Endpoints (Día 5-6)

1. Crear endpoints de pagos
2. Integrar con sistema de autenticación
3. Implementar validaciones y permisos
4. Tests de integración

### Fase 4: Integración y Testing (Día 7-8)

1. Integrar con frontend (si aplica)
2. Testing completo del sistema
3. Corrección de bugs
4. Optimización de consultas

### Fase 5: Documentación y Despliegue (Día 9-10)

1. Documentar funcionalidad
2. Preparar para producción
3. Desplegar a staging
4. Testing en staging
5. Desplegar a producción

## ⚠️ Consideraciones Importantes

### Multitenant

- Asegurar que los pagos se crean en el schema correcto del tenant
- Validar que la orden pertenece al tenant actual

### Transacciones

- Usar transacciones de base de datos para operaciones críticas
- Asegurar consistencia entre `Payment` y `Order`

### Performance

- Crear índices en `order_id` y `payment_date`
- Optimizar consultas de resumen de pagos
- Considerar caché para consultas frecuentes

### Auditoría

- Registrar quién crea/modifica pagos
- Mantener historial de cambios (opcional, para futuras mejoras)

## 🔮 Mejoras Futuras (Fuera del Scope Inicial)

1. **Pagos recurrentes**: Para órdenes con pagos programados
2. **Notificaciones**: Alertas de pagos pendientes
3. **Integración con pasarelas de pago**: Stripe, PayPal, etc.
4. **Reportes avanzados**: Dashboard de pagos, gráficos, etc.
5. **Exportación**: Exportar pagos a Excel/CSV
6. **Historial de cambios**: Auditoría completa de modificaciones

## 📋 Checklist de Implementación

### Modelos
- [ ] Modelo `Payment` creado
- [ ] Enums `PaymentStatus`, `PaymentMethod`, `OrderPaymentStatus` creados
- [ ] Modelo `Order` modificado con campos de pago
- [ ] Relaciones configuradas correctamente

### Migración
- [ ] Migración Alembic creada
- [ ] Migración probada en desarrollo
- [ ] Datos existentes migrados correctamente

### Repositorio
- [ ] Métodos CRUD implementados
- [ ] Métodos de consulta con filtros implementados
- [ ] Tests de repositorio pasando

### Servicio
- [ ] Lógica de negocio implementada
- [ ] Cálculo de saldos implementado
- [ ] Validaciones implementadas
- [ ] Tests de servicio pasando

### API
- [ ] Endpoints creados
- [ ] Autenticación y permisos configurados
- [ ] Validaciones de entrada implementadas
- [ ] Tests de API pasando

### Documentación
- [ ] Código documentado
- [ ] README actualizado
- [ ] Ejemplos de uso creados

### Testing
- [ ] Tests unitarios pasando
- [ ] Tests de integración pasando
- [ ] Testing manual completado

### Despliegue
- [ ] Migración aplicada en staging
- [ ] Testing en staging completado
- [ ] Migración aplicada en producción
- [ ] Sistema funcionando en producción

## ✅ Resumen de Simplificaciones Aplicadas

### Modelo de Datos
- ✅ **PaymentStatus**: Solo `CONFIRMED` y `CANCELLED` (eliminado `PENDING` y `REFUNDED`)
- ✅ **Por defecto**: Los pagos se crean con `status=CONFIRMED` automáticamente
- ✅ **OrderPaymentStatus**: Eliminado `OVERPAID` (solo `UNPAID`, `PARTIAL`, `PAID`)
- ✅ **PaymentMethod**: Eliminado `MOBILE_PAYMENT` (usar `OTHER` si es necesario)
- ✅ **Campos eliminados**: `reference_number` (se puede usar `notes` si es necesario)
- ✅ **Mantenido**: `created_by_user_id` para auditoría (registrar quién crea el pago)

### Funcionalidad
- ✅ **No se actualizan pagos**: Solo se crean y se cancelan
- ✅ **No se eliminan pagos**: Solo se cancelan (cambian status a `CANCELLED`)
- ✅ **Recálculo automático**: Al cancelar un pago, se recalcula automáticamente `paid_amount` y `balance_due` de la orden
- ✅ **Solo pagos confirmados cuentan**: Los pagos cancelados no se suman en `paid_amount`

### API Endpoints
- ✅ **Eliminado `PUT /payments/{payment_id}`**: No se actualizan pagos
- ✅ **Eliminado `DELETE /payments/{payment_id}`**: No se eliminan pagos
- ✅ **Eliminado `POST /orders/{order_id}/payments`**: Redundante, usar `POST /payments/` con `order_id` en el body
- ✅ **Agregado `POST /payments/{payment_id}/cancel`**: Para cancelar pagos

### Esquemas
- ✅ **Eliminado `PaymentUpdate`**: No se actualizan pagos, solo se cancelan

### Repositorio y Servicio
- ✅ **Eliminado `update_payment()`**: No se actualizan pagos
- ✅ **Eliminado `delete_payment()`**: No se eliminan pagos
- ✅ **Agregado `cancel_payment()`**: Para cancelar pagos y recalcular orden

### Beneficios de las Simplificaciones
1. **Menos complejidad**: Menos estados y flujos que manejar
2. **Más simple de entender**: Solo crear y cancelar, nada más
3. **Menos código**: Menos métodos, menos endpoints, menos validaciones
4. **Más rápido de implementar**: Menos componentes que desarrollar
5. **Más fácil de mantener**: Menos casos edge que considerar
6. **Historial completo**: Los pagos cancelados quedan registrados (no se eliminan)

