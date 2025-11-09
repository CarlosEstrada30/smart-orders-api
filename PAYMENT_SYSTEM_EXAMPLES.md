# Ejemplos de Uso: Sistema de Control de Pagos de Órdenes

## 📋 Ejemplos de API

### 1. Crear un Pago para una Orden

**Endpoint**: `POST /api/v1/payments/`

**Request Body**:
```json
{
  "order_id": 123,
  "amount": 500.00,
  "payment_method": "cash",
  "reference_number": "REF-001",
  "notes": "Pago parcial en efectivo"
}
```

**Response** (201 Created):
```json
{
  "id": 1,
  "payment_number": "PAY-A1B2C3D4",
  "order_id": 123,
  "amount": 500.00,
  "payment_method": "cash",
  "status": "confirmed",
  "payment_date": "2025-01-15T10:30:00Z",
  "reference_number": "REF-001",
  "notes": "Pago parcial en efectivo",
  "created_by_user_id": 5,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

**Efecto en la Orden**:
- `paid_amount`: 0.00 → 500.00
- `balance_due`: 1000.00 → 500.00
- `payment_status`: "unpaid" → "partial"

### 2. Obtener Pagos de una Orden

**Endpoint**: `GET /api/v1/orders/123/payments`

**Response** (200 OK):
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
    "reference_number": "REF-001",
    "notes": "Pago parcial en efectivo",
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
    "reference_number": "TRF-789456",
    "notes": "Transferencia bancaria - saldo completo",
    "created_at": "2025-01-16T14:20:00Z"
  }
]
```

### 3. Obtener Resumen de Pagos de una Orden

**Endpoint**: `GET /api/v1/orders/123/payment-summary`

**Response** (200 OK):
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
      "payment_date": "2025-01-15T10:30:00Z"
    },
    {
      "id": 2,
      "payment_number": "PAY-E5F6G7H8",
      "amount": 500.00,
      "payment_method": "bank_transfer",
      "payment_date": "2025-01-16T14:20:00Z"
    }
  ]
}
```

### 4. Listar Todas las Órdenes con Saldo Pendiente

**Endpoint**: `GET /api/v1/orders/?payment_status=partial&balance_due_gt=0`

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": 123,
      "order_number": "ORD-12345678",
      "client_id": 45,
      "total_amount": 1000.00,
      "paid_amount": 500.00,
      "balance_due": 500.00,
      "payment_status": "partial",
      "status": "delivered",
      "created_at": "2025-01-10T08:00:00Z"
    },
    {
      "id": 124,
      "order_number": "ORD-87654321",
      "client_id": 46,
      "total_amount": 2500.00,
      "paid_amount": 1000.00,
      "balance_due": 1500.00,
      "payment_status": "partial",
      "status": "delivered",
      "created_at": "2025-01-11T09:00:00Z"
    }
  ],
  "total": 2,
  "skip": 0,
  "limit": 100
}
```

### 5. Actualizar un Pago

**Endpoint**: `PUT /api/v1/payments/1`

**Request Body**:
```json
{
  "amount": 600.00,
  "payment_method": "credit_card",
  "reference_number": "CC-123456",
  "notes": "Pago actualizado - corrección de monto"
}
```

**Response** (200 OK):
```json
{
  "id": 1,
  "payment_number": "PAY-A1B2C3D4",
  "order_id": 123,
  "amount": 600.00,
  "payment_method": "credit_card",
  "status": "confirmed",
  "payment_date": "2025-01-15T10:30:00Z",
  "reference_number": "CC-123456",
  "notes": "Pago actualizado - corrección de monto",
  "updated_at": "2025-01-17T11:00:00Z"
}
```

**Efecto en la Orden**:
- `paid_amount`: 500.00 → 600.00
- `balance_due`: 500.00 → 400.00
- `payment_status`: "partial" (se mantiene)

### 6. Eliminar un Pago

**Endpoint**: `DELETE /api/v1/payments/1`

**Response** (204 No Content)

**Efecto en la Orden**:
- `paid_amount`: 1000.00 → 500.00
- `balance_due`: 0.00 → 500.00
- `payment_status`: "paid" → "partial"

## 🔄 Flujos de Trabajo Completos

### Flujo 1: Orden con Pago Completo en una Transacción

1. **Crear Orden**:
   ```json
   POST /api/v1/orders/
   {
     "client_id": 45,
     "items": [...],
     "total_amount": 1000.00
   }
   ```
   - Orden creada con `payment_status: "unpaid"`, `paid_amount: 0.00`, `balance_due: 1000.00`

2. **Crear Pago Completo**:
   ```json
   POST /api/v1/payments/
   {
     "order_id": 123,
     "amount": 1000.00,
     "payment_method": "cash"
   }
   ```
   - Pago creado
   - Orden actualizada: `payment_status: "paid"`, `paid_amount: 1000.00`, `balance_due: 0.00`

### Flujo 2: Orden con Pagos Parciales Múltiples

1. **Crear Orden**:
   - Orden creada con `total_amount: 2000.00`

2. **Primer Pago Parcial**:
   ```json
   POST /api/v1/payments/
   {
     "order_id": 123,
     "amount": 500.00,
     "payment_method": "cash"
   }
   ```
   - `paid_amount: 500.00`, `balance_due: 1500.00`, `payment_status: "partial"`

3. **Segundo Pago Parcial**:
   ```json
   POST /api/v1/payments/
   {
     "order_id": 123,
     "amount": 1000.00,
     "payment_method": "bank_transfer"
   }
   ```
   - `paid_amount: 1500.00`, `balance_due: 500.00`, `payment_status: "partial"`

4. **Tercer Pago (Completa el Saldo)**:
   ```json
   POST /api/v1/payments/
   {
     "order_id": 123,
     "amount": 500.00,
     "payment_method": "credit_card"
   }
   ```
   - `paid_amount: 2000.00`, `balance_due: 0.00`, `payment_status: "paid"`

### Flujo 3: Corrección de Pago (Actualizar)

1. **Pago Incorrecto Creado**:
   - Pago de 500.00 creado por error

2. **Corregir el Pago**:
   ```json
   PUT /api/v1/payments/1
   {
     "amount": 1000.00
   }
   ```
   - Pago actualizado a 1000.00
   - Orden ajustada automáticamente

### Flujo 4: Eliminar Pago Erróneo

1. **Pago Erróneo Creado**:
   - Pago de 500.00 creado por error para orden que ya estaba pagada

2. **Eliminar el Pago**:
   ```
   DELETE /api/v1/payments/1
   ```
   - Pago eliminado
   - Orden ajustada: `paid_amount` y `balance_due` recalculados

## 📊 Casos de Uso de Negocio

### Caso 1: Cliente Paga en Efectivo al Momento de Entrega

```python
# 1. Orden entregada
PUT /api/v1/orders/123/status/delivered

# 2. Registrar pago en efectivo
POST /api/v1/payments/
{
  "order_id": 123,
  "amount": 1000.00,
  "payment_method": "cash",
  "notes": "Pago en efectivo al momento de entrega"
}
```

### Caso 2: Cliente Paga con Transferencia Bancaria

```python
# Registrar pago con referencia de transferencia
POST /api/v1/payments/
{
  "order_id": 123,
  "amount": 1000.00,
  "payment_method": "bank_transfer",
  "reference_number": "TRF-20250115-001",
  "notes": "Transferencia bancaria confirmada"
}
```

### Caso 3: Cliente Paga Parcialmente y Promete Pagar el Resto

```python
# Primer pago parcial
POST /api/v1/payments/
{
  "order_id": 123,
  "amount": 500.00,
  "payment_method": "cash",
  "notes": "Pago inicial - cliente promete pagar resto en 7 días"
}

# Más tarde, segundo pago
POST /api/v1/payments/
{
  "order_id": 123,
  "amount": 500.00,
  "payment_method": "cash",
  "notes": "Pago final - saldo completo"
}
```

### Caso 4: Reporte de Órdenes con Saldo Pendiente

```python
# Obtener todas las órdenes con saldo pendiente
GET /api/v1/orders/?payment_status=partial&balance_due_gt=0

# Filtrar por cliente específico
GET /api/v1/orders/?client_id=45&payment_status=partial

# Filtrar por rango de fechas
GET /api/v1/orders/?date_from=2025-01-01&date_to=2025-01-31&payment_status=partial
```

## ⚠️ Validaciones y Errores

### Error: Pago Excede el Saldo Pendiente

**Request**:
```json
POST /api/v1/payments/
{
  "order_id": 123,
  "amount": 1500.00,  // Orden tiene balance_due: 1000.00
  "payment_method": "cash"
}
```

**Response** (400 Bad Request):
```json
{
  "detail": "El monto del pago (1500.00) excede el saldo pendiente (1000.00)"
}
```

### Error: Orden No Encontrada

**Request**:
```json
POST /api/v1/payments/
{
  "order_id": 99999,  // Orden no existe
  "amount": 500.00,
  "payment_method": "cash"
}
```

**Response** (404 Not Found):
```json
{
  "detail": "Orden no encontrada"
}
```

### Error: Orden Cancelada

**Request**:
```json
POST /api/v1/payments/
{
  "order_id": 123,  // Orden con status: "cancelled"
  "amount": 500.00,
  "payment_method": "cash"
}
```

**Response** (400 Bad Request):
```json
{
  "detail": "No se pueden registrar pagos para órdenes canceladas"
}
```

## 🔍 Consultas Útiles

### Obtener Total de Pagos Recibidos en un Período

```python
GET /api/v1/payments/?date_from=2025-01-01&date_to=2025-01-31
```

### Filtrar Pagos por Método

```python
GET /api/v1/payments/?payment_method=cash
GET /api/v1/payments/?payment_method=bank_transfer
```

### Obtener Pagos de un Cliente Específico

```python
# Primero obtener órdenes del cliente
GET /api/v1/orders/?client_id=45

# Luego obtener pagos de esas órdenes
GET /api/v1/payments/?order_id=123
GET /api/v1/payments/?order_id=124
```

## 📈 Reportes y Analytics

### Resumen de Pagos del Mes

```python
GET /api/v1/payments/analytics/monthly-summary?year=2025&month=1
```

**Response**:
```json
{
  "year": 2025,
  "month": 1,
  "total_payments": 45,
  "total_amount": 125000.00,
  "by_method": {
    "cash": 25000.00,
    "bank_transfer": 50000.00,
    "credit_card": 50000.00
  },
  "by_status": {
    "confirmed": 125000.00,
    "pending": 0.00
  }
}
```


