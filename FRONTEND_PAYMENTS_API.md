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

### 2. Crear Múltiples Pagos (Bulk)

**Endpoint:** `POST /api/v1/payments/bulk`

**Permisos:** Requiere rol de Vendedor o superior

**Descripción:** Permite crear múltiples pagos en una sola solicitud. Útil cuando necesitas registrar pagos para varias órdenes al mismo tiempo. Si algunos pagos fallan, los pagos válidos se procesarán y se reportarán los que fallaron.

**Request Body:**
```json
{
  "payments": [
    {
      "order_id": 123,
      "amount": 500.00,
      "payment_method": "cash",
      "notes": "Pago parcial en efectivo"
    },
    {
      "order_id": 124,
      "amount": 750.50,
      "payment_method": "bank_transfer",
      "notes": "Pago completo por transferencia"
    },
    {
      "order_id": 125,
      "amount": 300.00,
      "payment_method": "credit_card",
      "notes": "Pago con tarjeta de crédito"
    }
  ]
}
```

**Response (201 Created):**
```json
{
  "payments": [
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
    },
    {
      "id": 2,
      "payment_number": "PAY-E5F6G7H8",
      "order_id": 124,
      "amount": 750.50,
      "payment_method": "bank_transfer",
      "status": "confirmed",
      "payment_date": "2025-01-15T10:30:00Z",
      "notes": "Pago completo por transferencia",
      "created_by_user_id": 5,
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z"
    },
    {
      "id": 3,
      "payment_number": "PAY-I9J0K1L2",
      "order_id": 125,
      "amount": 300.00,
      "payment_method": "credit_card",
      "status": "confirmed",
      "payment_date": "2025-01-15T10:30:00Z",
      "notes": "Pago con tarjeta de crédito",
      "created_by_user_id": 5,
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total_payments": 3,
  "total_amount": 1550.50,
  "success_count": 3,
  "failed_count": 0
}
```

**Campos de Respuesta:**
- `payments` - Lista de pagos creados exitosamente
- `total_payments` - Total de pagos enviados en la solicitud
- `total_amount` - Suma de todos los montos de los pagos creados exitosamente
- `success_count` - Número de pagos creados exitosamente
- `failed_count` - Número de pagos que fallaron (por validación o error)
- `errors` - Lista detallada de pagos que fallaron con información sobre la razón del fallo

**Comportamiento:**
- Si algunos pagos fallan (por ejemplo, orden no encontrada, orden cancelada, monto inválido), los pagos válidos se procesarán normalmente
- Los pagos que fallan no se crean, pero no impiden que los demás se procesen
- Todas las órdenes afectadas se actualizan automáticamente con sus nuevos saldos
- **Las órdenes canceladas no pueden recibir pagos** y se reportarán en el campo `errors` con la razón "No se pueden registrar pagos para órdenes canceladas"

**Ejemplo con Pagos que Fallan:**
```json
{
  "payments": [
    {
      "order_id": 123,
      "amount": 500.00,
      "payment_method": "cash",
      "notes": "Pago válido"
    },
    {
      "order_id": 999,
      "amount": 200.00,
      "payment_method": "cash",
      "notes": "Orden que no existe"
    },
    {
      "order_id": 125,
      "amount": 300.00,
      "payment_method": "credit_card",
      "notes": "Pago válido"
    },
    {
      "order_id": 126,
      "amount": 150.00,
      "payment_method": "bank_transfer",
      "notes": "Orden cancelada"
    }
  ]
}
```

**Response (201 Created):**
```json
{
  "payments": [
    {
      "id": 1,
      "payment_number": "PAY-A1B2C3D4",
      "order_id": 123,
      "amount": 500.00,
      "payment_method": "cash",
      "status": "confirmed",
      "notes": "Pago válido",
      ...
    },
    {
      "id": 2,
      "payment_number": "PAY-E5F6G7H8",
      "order_id": 125,
      "amount": 300.00,
      "payment_method": "credit_card",
      "status": "confirmed",
      "notes": "Pago válido",
      ...
    }
  ],
  "total_payments": 4,
  "total_amount": 800.00,
  "success_count": 2,
  "failed_count": 2,
  "errors": [
    {
      "order_id": 999,
      "order_number": null,
      "client_name": null,
      "amount": 200.00,
      "payment_method": "cash",
      "reason": "Orden no encontrada",
      "notes": "Orden que no existe"
    },
    {
      "order_id": 126,
      "order_number": "ORD-ABC12345",
      "client_name": "Juan Pérez",
      "amount": 150.00,
      "payment_method": "bank_transfer",
      "reason": "No se pueden registrar pagos para órdenes canceladas",
      "notes": "Orden cancelada"
    }
  ]
}
```

**Campo `errors` - Información de Pagos Fallidos:**
Cada error en el array `errors` contiene:
- `order_id` - ID de la orden que no se pudo procesar
- `order_number` - Número de la orden (si existe, `null` si la orden no existe)
- `client_name` - Nombre del cliente (si la orden existe, `null` si la orden no existe)
- `amount` - Monto del pago que falló
- `payment_method` - Método de pago intentado
- `reason` - Razón por la cual falló el pago (mensaje descriptivo)
- `notes` - Notas del pago que falló (si se proporcionaron)

**Razones Comunes de Error:**
- `"Orden no encontrada"` - La orden con el ID especificado no existe
- `"No se pueden registrar pagos para órdenes canceladas"` - La orden está en estado cancelado
- `"El monto del pago debe ser mayor a 0"` - El monto proporcionado es inválido
- `"Error inesperado: ..."` - Otros errores del sistema

**Efecto Automático:**
- Se actualizan automáticamente `paid_amount` y `balance_due` en todas las órdenes afectadas
- Se actualiza `payment_status` de cada orden (unpaid → partial → paid)
- Los pagos válidos se crean y confirman automáticamente

**Casos de Uso:**
- Registrar pagos de múltiples órdenes al final del día
- Procesar pagos de un cliente que tiene varias órdenes pendientes
- Importar pagos desde un sistema externo
- Registrar pagos masivos después de una venta en efectivo

---

### 3. Listar Pagos

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

### 4. Obtener un Pago Específico

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

### 5. Cancelar un Pago

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

### 6. Obtener Pagos de una Orden

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

### 7. Obtener Resumen de Pagos de una Orden

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

### Flujo 5: Crear Múltiples Pagos (Bulk)
- Usar el endpoint `/bulk` para registrar pagos de varias órdenes en una sola solicitud
- Útil para:
  - Registrar pagos al final del día de múltiples órdenes
  - Procesar pagos de un cliente con varias órdenes pendientes
  - Importar pagos desde un sistema externo
- El sistema procesa todos los pagos válidos, incluso si algunos fallan
- Revisar `success_count` y `failed_count` en la respuesta para verificar el resultado
- Revisar el campo `errors` para obtener información detallada sobre los pagos que fallaron
- **Las órdenes canceladas se ignoran automáticamente** y se reportan en el campo `errors` con la razón específica

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

**Nota:** En el endpoint `/bulk`, las órdenes canceladas no detienen el procesamiento. Se reportan en el campo `errors` de la respuesta:
```json
{
  "errors": [
    {
      "order_id": 126,
      "order_number": "ORD-ABC12345",
      "client_name": "Juan Pérez",
      "amount": 150.00,
      "payment_method": "bank_transfer",
      "reason": "No se pueden registrar pagos para órdenes canceladas",
      "notes": "Orden cancelada"
    }
  ]
}
```

**Nota sobre `order_number` y `client_name`:**
- Si la orden existe, estos campos contendrán el número de orden y el nombre del cliente
- Si la orden no existe (por ejemplo, ID inválido), estos campos serán `null`
- Esto permite identificar fácilmente qué órdenes fallaron y a qué clientes pertenecen

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
   - En el endpoint individual (`POST /payments/`): Retorna error 400
   - En el endpoint bulk (`POST /payments/bulk`): Se ignora el pago y se reporta en el campo `errors`
2. **El monto del pago debe ser mayor a 0**
3. **Solo se pueden cancelar pagos confirmados**
4. **Al cancelar un pago, se recalcula automáticamente el saldo de la orden**
5. **En el endpoint bulk, los errores no detienen el procesamiento de otros pagos válidos**

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

