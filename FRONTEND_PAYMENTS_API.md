# API de Pagos - Guía para Frontend

## 📋 Resumen

Esta guía describe cómo usar los endpoints de pagos implementados en el sistema. Los pagos permiten registrar pagos parciales o completos para órdenes, y el sistema calcula automáticamente los saldos pendientes.

## 🔐 Autenticación

Todos los endpoints requieren autenticación mediante token. Incluir el token en el header:

```
Authorization: Bearer <token>
```

## 📊 Endpoints Disponibles

### 1. Crear un Pago

**Endpoint:** `POST /api/v1/payments/`

**Permisos:** Requiere rol de Vendedor o superior

**Request Body:**
```json
{
  "order_id": 123,
  "amount": 500.00,
  "payment_method": "cash",
  "notes": "Pago parcial en efectivo"
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "payment_number": "PAY-A1B2C3D4",
  "order_id": 123,
  "amount": 500.00,
  "payment_method": "cash",
  "status": "confirmed",
  "payment_date": "2025-01-15T10:30:00Z",
  "notes": "Pago parcial en efectivo",
  "created_by_user_id": 5,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

**Métodos de Pago Disponibles:**
- `cash` - Efectivo
- `credit_card` - Tarjeta de crédito
- `debit_card` - Tarjeta de débito
- `bank_transfer` - Transferencia bancaria
- `check` - Cheque
- `other` - Otro método

**Efecto Automático:**
- Se actualiza automáticamente `paid_amount` y `balance_due` en la orden
- Se actualiza `payment_status` de la orden (unpaid → partial → paid)

---

### 2. Listar Pagos

**Endpoint:** `GET /api/v1/payments/`

**Permisos:** Requiere permiso de ver pagos

**Query Parameters:**
- `skip` (int, default: 0) - Número de registros a saltar
- `limit` (int, default: 100) - Número máximo de registros
- `order_id` (int, optional) - Filtrar por ID de orden
- `payment_method` (string, optional) - Filtrar por método de pago
- `status_filter` (string, optional) - Filtrar por estado (confirmed, cancelled)
- `date_from` (date, optional) - Filtrar desde esta fecha (YYYY-MM-DD)
- `date_to` (date, optional) - Filtrar hasta esta fecha (YYYY-MM-DD)
- `only_confirmed` (bool, default: true) - Solo mostrar pagos confirmados

**Response (200 OK):**
```json
{
  "items": [
    {
      "id": 1,
      "payment_number": "PAY-A1B2C3D4",
      "order_id": 123,
      "amount": 500.00,
      "payment_method": "cash",
      "status": "confirmed",
      "payment_date": "2025-01-15T10:30:00Z",
      "notes": "Pago parcial",
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 100
}
```

---

### 3. Obtener un Pago Específico

**Endpoint:** `GET /api/v1/payments/{payment_id}`

**Permisos:** Requiere permiso de ver pagos

**Response (200 OK):**
```json
{
  "id": 1,
  "payment_number": "PAY-A1B2C3D4",
  "order_id": 123,
  "amount": 500.00,
  "payment_method": "cash",
  "status": "confirmed",
  "payment_date": "2025-01-15T10:30:00Z",
  "notes": "Pago parcial",
  "created_by_user_id": 5,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

---

### 4. Cancelar un Pago

**Endpoint:** `POST /api/v1/payments/{payment_id}/cancel`

**Permisos:** Requiere rol de Vendedor o superior

**Response (200 OK):**
```json
{
  "id": 1,
  "payment_number": "PAY-A1B2C3D4",
  "order_id": 123,
  "amount": 500.00,
  "payment_method": "cash",
  "status": "cancelled",
  "payment_date": "2025-01-15T10:30:00Z",
  "notes": "Pago parcial",
  "created_by_user_id": 5,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:35:00Z"
}
```

**Efecto Automático:**
- El pago cambia su status a `cancelled`
- Se recalcula automáticamente `paid_amount` y `balance_due` en la orden
- Se actualiza `payment_status` de la orden

---

### 5. Obtener Pagos de una Orden

**Endpoint:** `GET /api/v1/orders/{order_id}/payments`

**Permisos:** Requiere permiso de ver pagos

**Query Parameters:**
- `only_confirmed` (bool, default: true) - Solo mostrar pagos confirmados

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "payment_number": "PAY-A1B2C3D4",
    "order_id": 123,
    "amount": 500.00,
    "payment_method": "cash",
    "status": "confirmed",
    "payment_date": "2025-01-15T10:30:00Z",
    "notes": "Pago parcial",
    "created_at": "2025-01-15T10:30:00Z"
  },
  {
    "id": 2,
    "payment_number": "PAY-E5F6G7H8",
    "order_id": 123,
    "amount": 500.00,
    "payment_method": "bank_transfer",
    "status": "confirmed",
    "payment_date": "2025-01-16T14:20:00Z",
    "notes": "Saldo completo",
    "created_at": "2025-01-16T14:20:00Z"
  }
]
```

---

### 6. Obtener Resumen de Pagos de una Orden

**Endpoint:** `GET /api/v1/orders/{order_id}/payment-summary`

**Permisos:** Requiere permiso de ver pagos

**Response (200 OK):**
```json
{
  "order_id": 123,
  "order_number": "ORD-12345678",
  "total_amount": 1000.00,
  "paid_amount": 1000.00,
  "balance_due": 0.00,
  "payment_status": "paid",
  "payment_count": 2,
  "payments": [
    {
      "id": 1,
      "payment_number": "PAY-A1B2C3D4",
      "amount": 500.00,
      "payment_method": "cash",
      "status": "confirmed",
      "payment_date": "2025-01-15T10:30:00Z"
    },
    {
      "id": 2,
      "payment_number": "PAY-E5F6G7H8",
      "amount": 500.00,
      "payment_method": "bank_transfer",
      "status": "confirmed",
      "payment_date": "2025-01-16T14:20:00Z"
    }
  ]
}
```

---

## 📦 Campos de Orden Actualizados

Cuando obtienes una orden (`GET /api/v1/orders/{order_id}`), ahora incluye campos de pago:

```json
{
  "id": 123,
  "order_number": "ORD-12345678",
  "total_amount": 1000.00,
  "paid_amount": 500.00,        // Nuevo: Monto total pagado
  "balance_due": 500.00,        // Nuevo: Saldo pendiente
  "payment_status": "partial",   // Nuevo: Estado de pago (unpaid, partial, paid)
  // ... otros campos
}
```

**Estados de Pago de Orden:**
- `unpaid` - Sin pagos
- `partial` - Pago parcial
- `paid` - Pagado completamente

---

## 🔄 Flujos de Trabajo Comunes

### Flujo 1: Crear Pago Completo
- Crear un pago con el monto igual al `total_amount` de la orden
- Resultado: `order.payment_status = "paid"`, `balance_due = 0.00`

### Flujo 2: Crear Pagos Parciales Múltiples
- Crear primer pago parcial (ej: 50% del total)
- Resultado: `order.payment_status = "partial"`, `balance_due` se actualiza
- Crear segundo pago con el saldo restante
- Resultado: `order.payment_status = "paid"`, `balance_due = 0.00`

### Flujo 3: Ver Resumen de Pagos
- Obtener el resumen de pagos de una orden para mostrar:
  - `total_amount` - Monto total de la orden
  - `paid_amount` - Monto total pagado
  - `balance_due` - Saldo pendiente
  - `payment_status` - Estado de pago (unpaid, partial, paid)
  - `payment_count` - Número de pagos

### Flujo 4: Cancelar un Pago
- Cancelar un pago erróneo o incorrecto
- El sistema recalcula automáticamente:
  - Resta el monto del pago de `paid_amount`
  - Recalcula `balance_due`
  - Actualiza `payment_status` de la orden

---

## ⚠️ Validaciones y Errores

### Error: Orden No Encontrada
```json
{
  "detail": "Orden no encontrada"
}
```
**Status:** 404 Not Found

### Error: Orden Cancelada
```json
{
  "detail": "No se pueden registrar pagos para órdenes canceladas"
}
```
**Status:** 400 Bad Request

### Error: Sin Permisos
```json
{
  "detail": "No tienes permisos para crear pagos. Se requiere rol de Vendedor o superior."
}
```
**Status:** 403 Forbidden

### Error: Pago Ya Cancelado
```json
{
  "detail": "Solo se pueden cancelar pagos confirmados"
}
```
**Status:** 400 Bad Request

---

## 📊 Estados y Validaciones

### Estados de Pago Individual
- `confirmed` - Pago confirmado (por defecto al crear)
- `cancelled` - Pago cancelado

### Estados de Pago de Orden
- `unpaid` - Sin pagos
- `partial` - Pago parcial (tiene pagos pero aún hay saldo pendiente)
- `paid` - Pagado completamente (balance_due = 0)

### Validaciones Importantes
1. **No se pueden crear pagos para órdenes canceladas**
2. **El monto del pago debe ser mayor a 0**
3. **Solo se pueden cancelar pagos confirmados**
4. **Al cancelar un pago, se recalcula automáticamente el saldo de la orden**

---

## 🔍 Consultas Útiles

### Filtrar Órdenes con Saldo Pendiente
- Usar el endpoint `GET /api/v1/orders/` con el parámetro `payment_status=partial` o `payment_status=unpaid`

### Obtener Pagos de un Período
- Usar el endpoint `GET /api/v1/payments/` con los parámetros:
  - `date_from` (YYYY-MM-DD)
  - `date_to` (YYYY-MM-DD)
  - `only_confirmed=true`

### Obtener Pagos por Método
- Usar el endpoint `GET /api/v1/payments/` con el parámetro `payment_method` (cash, credit_card, debit_card, bank_transfer, check, other)

---

## 🎯 Mejores Prácticas

1. **Siempre verificar el saldo pendiente antes de crear un pago**
   - Obtener el resumen de pagos de la orden primero
   - Validar que el monto no exceda el saldo pendiente
   - Mostrar mensaje de error si el monto es inválido

2. **Actualizar la vista después de crear/cancelar un pago**
   - Después de crear o cancelar un pago, refrescar el resumen de pagos
   - Actualizar los campos `paid_amount`, `balance_due` y `payment_status` en la orden

3. **Usar el estado de pago para indicadores visuales**
   - `unpaid` - Sin pagos (rojo)
   - `partial` - Pago parcial (amarillo)
   - `paid` - Pagado completamente (verde)

4. **Manejar errores apropiadamente**
   - Capturar y mostrar mensajes de error al usuario
   - Validar permisos antes de mostrar opciones de crear/cancelar pagos

---

## 📝 Notas Importantes

- Los pagos se crean con `status=confirmed` automáticamente
- Solo los pagos confirmados se suman en `paid_amount`
- Los pagos cancelados no se eliminan, solo cambian su status
- El sistema recalcula automáticamente los saldos al crear/cancelar pagos
- Cada pago tiene un `payment_number` único (formato: PAY-XXXXXXXX)

