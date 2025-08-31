# 📋 PROMPT FRONTEND - SISTEMA FACTURACIÓN FEL GUATEMALA

## 🎯 OBJETIVO
Desarrollar módulo de facturación con **dos flujos**:
- **Facturas FEL**: Válidas fiscalmente (con UUID SAT)
- **Comprobantes**: Sin valor fiscal

## 🔄 FLUJO PRINCIPAL

### Desde Orden Entregada:
```
Orden DELIVERED → Usuario elige:
├─ Factura FEL → Procesa con SAT → UUID → PDF oficial
└─ Comprobante → PDF inmediato → "NO FACTURA FISCAL"
```

### Estados Factura:
- `DRAFT`: Recién creada
- `ISSUED`: FEL exitosa (con UUID)
- `PAID`: Pagada
- `OVERDUE`: Vencida

### Estados FEL:
- **fel_uuid**: Si existe = válida fiscalmente
- **fel_error_message**: Error si falló
- **requires_fel**: Boolean

## 🔌 ENDPOINTS CLAVE

```http
# Crear factura FEL
POST /invoices/orders/{order_id}/auto-invoice-with-fel
→ {factura con UUID si exitosa}

# Generar comprobante
POST /invoices/orders/{order_id}/receipt-only  
→ PDF download

# Estado FEL
GET /invoices/fel/status-summary
→ {conteos, errores, exitosas}

# Reintentar FEL fallidas
POST /invoices/{invoice_id}/fel/process

# Ingresos fiscales
GET /invoices/revenue/fiscal
→ {solo facturas con UUID}
```

## 🎨 PANTALLAS PRINCIPALES

### 1. Dashboard
- Órdenes sin documento
- Botones: [Facturar FEL] [Comprobante]
- Alertas: "2 FEL fallaron"
- Métricas: Fiscales vs Totales

### 2. Lista Facturas
```
FAC-001 | Cliente | Q1,200 | 🟢 ISSUED | FEL✅
UUID: abc123... | [PDF] [Pagar]

FAC-002 | Cliente | Q800 | 🔴 ERROR | FEL❌  
Error: Datos cliente | [Reintentar] [Comprobante]
```

### 3. Modal Selector
```
¿Qué documento necesita?

📄 COMPROBANTE
• Sin valor fiscal
• Generación inmediata
[Generar]

📜 FACTURA FEL  
• Válida ante SAT
• Cliente deduce IVA
• Proceso 15-30 seg
[Crear FEL]
```

## 🚦 ESTADOS VISUALES
- 🟢 Verde: FEL autorizada, pagada
- 🟡 Amarillo: Procesando, borrador
- 🔴 Rojo: Error FEL, vencida
- ⏳ Spinner: "Procesando con SAT..."

## ⚡ CASOS DE USO

### Cliente Empresa:
1. Clic "Crear Factura FEL"
2. Loading: "Procesando con SAT..."
3. Resultado: ✅ UUID o ❌ Error
4. Si error: [Reintentar] [Comprobante]

### Cliente Individual:
1. Clic "Generar Comprobante"  
2. Descarga PDF inmediata
3. PDF marca "NO FACTURA FISCAL"

### Pago:
1. Factura ISSUED → [Registrar Pago]
2. Modal: monto, método, fecha
3. Estado → PAID

## 🔧 COMPONENTES NECESARIOS

### FELStatusIndicator
- Props: fel_uuid, fel_error, status
- Visual: ✅❌⏳ + colores

### DocumentActions  
- Props: orderId, hasInvoice, status
- Botones dinámicos según estado

### PaymentModal
- Campos: monto (max=balance), método, fecha
- Validación: monto > 0, fecha ≤ hoy

## ⚠️ VALIDACIONES
- Orden debe estar DELIVERED
- No factura duplicada
- Monto pago ≤ saldo pendiente
- Datos cliente completos para FEL

## 📊 ERRORES COMUNES FEL
```javascript
const FEL_ERRORS = {
  'connection_timeout': 'Sin conexión SAT',
  'invalid_nit': 'NIT inválido',  
  'client_incomplete': 'Datos cliente incompletos'
};
```

## 🔄 POLLING FEL
```javascript
// Verificar estado cada 2 seg hasta UUID o error
const pollFELStatus = async (invoiceId) => {
  // Max 30 intentos = 60 segundos
  // Si UUID || error → stop polling
};
```

## 📱 RESPONSIVE
- Mobile: Cards apiladas, FAB, swipe actions
- Desktop: Tablas, sidebars, multi-column
- Loading: Progress indicators claros

## 💾 DATOS CLAVE
```json
{
  "order": {
    "id": 123,
    "status": "DELIVERED",
    "invoice": {
      "id": 456,
      "status": "ISSUED",  
      "fel_uuid": "abc123",
      "fel_error_message": null,
      "total_amount": 1120.00,
      "balance_due": 0.00
    }
  }
}
```

## 🎯 ENTREGABLE
Interfaz que permita:
- Decidir entre FEL/comprobante fácilmente
- Ver estado procesamiento FEL en tiempo real  
- Gestionar ciclo completo de facturas
- Dashboard con métricas fiscales vs totales
- Manejo de errores con opciones de recuperación

**Prioridad**: Flujo principal FEL → Dashboard → Gestión pagos → Reportes

---

## 📋 ESTRUCTURA DE ARCHIVOS SUGERIDA

```
src/
├── components/
│   ├── FEL/
│   │   ├── FELStatusIndicator.tsx
│   │   ├── DocumentSelector.tsx
│   │   ├── FELProcessingLoader.tsx
│   │   └── FELErrorHandler.tsx
│   ├── Invoices/
│   │   ├── InvoicesList.tsx
│   │   ├── InvoiceCard.tsx
│   │   ├── PaymentModal.tsx
│   │   └── DocumentActions.tsx
│   └── Dashboard/
│       ├── FELDashboard.tsx
│       ├── RevenueMetrics.tsx
│       └── OrdersWithoutDoc.tsx
├── hooks/
│   ├── useFELProcessing.ts
│   ├── useInvoicePolling.ts
│   └── usePaymentFlow.ts
├── services/
│   ├── felApi.ts
│   ├── invoiceApi.ts
│   └── orderApi.ts
└── types/
    ├── invoice.ts
    ├── fel.ts
    └── order.ts
```

## 🧪 TESTING MÍNIMO
- Flujo FEL exitoso
- Manejo de errores FEL
- Generación comprobante
- Registro de pagos
- Estados visuales
- Polling timeout

---

**Creado**: Diciembre 2024  
**Versión**: 1.0  
**Backend**: Smart Orders API con FEL Guatemala integrado

