# Implementación Flujo Fábrica de Lácteos

## 📋 Problema Actual

### Proceso Manual Actual
La fábrica de lácteos (quesos, crema, quesillo, etc.) actualmente opera con el siguiente proceso:

1. **Captura de pedidos**: Contacto telefónico/WhatsApp sin validación de stock
2. **Consolidación manual**: Conteo manual de productos pedidos por todos los clientes
3. **Planificación de producción**: Producción basada en materia prima y tiempo disponible
4. **Ajuste manual de faltantes**: Si no hay suficiente producción, reducción manual de cantidades en algunos pedidos para cumplir con todos los clientes

### Problemas Identificados
- ❌ No hay control de stock al momento de tomar pedidos
- ❌ Proceso de consolidación completamente manual
- ❌ No hay criterio justo para distribuir faltantes
- ❌ No hay visibilidad automática para el equipo de producción
- ❌ Riesgo de errores en cálculos manuales

## 🎯 Flujo Propuesto

### Nuevo Proceso Automatizado
1. **Creación libre de órdenes**: Sin restricciones de stock (estado: PENDING)
2. **Modificación flexible**: Edición libre mientras esté en PENDING
3. **Evaluación FIFO**: Análisis automático por orden de llegada
4. **Confirmación controlada**: Descuento de stock solo al confirmar
5. **Consolidación automática**: Dashboard para producción
6. **Gestión inteligente de faltantes**: Sugerencias automáticas

## 🚀 Plan de Implementación Incremental

---

## **PASO 1: Órdenes sin descuento automático de stock**

### 🎯 Objetivo
Permitir crear órdenes sin afectar el inventario inmediatamente

### 📝 Descripción
Modificar el flujo actual para que al crear una orden NO se descuente stock automáticamente. Solo validar que los productos existen y están activos.

### 🔧 Cambios Técnicos
- **Archivo**: `app/services/order_service.py`
- **Método**: `create_order()`
- **Cambios**:
  - Remover llamada a `_validate_products_and_stock()`
  - Remover llamada a `_reserve_stock_for_items()`
  - Mantener solo `_validate_client()`, `_validate_route()` y validación básica de productos
  - Mantener funcionalidad de restauración de stock en `cancel_order()`

### ✅ Criterios de Aceptación
- [ ] Crear orden sin validar stock disponible
- [ ] Solo validar que productos existen y están activos
- [ ] La orden se crea con estado PENDING
- [ ] No se modifica el stock de los productos
- [ ] API funciona sin errores
- [ ] Tests actualizados

### 📊 Beneficio Inmediato
- ✅ Pueden crear todas las órdenes que necesiten sin restricciones
- ✅ Elimina el problema de "no puedo tomar más pedidos"
- ✅ Proceso más fluido para el equipo de ventas

### ⚠️ Riesgo
**Mínimo** - Solo modifica validaciones, no altera lógica core

---

## **PASO 2: Confirmación manual con descuento**

### 🎯 Objetivo
Implementar confirmación manual que descuente stock realmente

### 📝 Descripción
Modificar el proceso de cambio de estado para que al confirmar una orden (PENDING → CONFIRMED) se valide y descuente el stock.

### 🔧 Cambios Técnicos
- **Archivo**: `app/services/order_service.py`
- **Método**: `update_order_status()`
- **Cambios**:
  - Agregar validación especial para transición PENDING → CONFIRMED
  - Implementar `_validate_and_reserve_stock_on_confirm()`
  - Validar stock disponible antes de confirmar
  - Descontar stock solo si confirmación es exitosa
  - Manejar errores de stock insuficiente con mensajes específicos

### ✅ Criterios de Aceptación
- [ ] Solo al confirmar orden se valida stock
- [ ] Si no hay stock suficiente, mostrar error específico detallado
- [ ] Si hay stock, descontar automáticamente
- [ ] Orden cambia a CONFIRMED solo si stock es suficiente
- [ ] API maneja errores graciosamente
- [ ] Frontend muestra mensajes de error claros

### 📊 Beneficio Inmediato
- ✅ Control total sobre cuándo comprometer stock
- ✅ Visibilidad clara de qué órdenes están realmente confirmadas
- ✅ Flexibility para ajustar órdenes antes de confirmar

### ⚠️ Riesgo
**Bajo** - Usa funciones existentes de manejo de stock

---

## **PASO 3: Campo de completitud**

### 🎯 Objetivo
Agregar indicador visual de si una orden puede completarse con stock actual

### 📝 Descripción
Agregar campo `completion_status` al modelo Order para indicar si la orden puede ser completada con el stock disponible actualmente.

### 🔧 Cambios Técnicos
- **Migración**: Agregar campo `completion_status` ENUM
  - Valores: `'completable'`, `'incomplete'`, `'pending_check'`
  - Default: `'pending_check'`
- **Archivo**: `app/models/order.py`
- **Archivo**: `app/schemas/order.py`
- **Archivo**: `app/services/order_service.py`
  - Método: `check_order_completion_status()`
  - Evaluar stock disponible vs items de la orden

### 📋 Estados de Completitud
- **`pending_check`**: No evaluado aún
- **`completable`**: Puede completarse con stock actual
- **`incomplete`**: No puede completarse, falta stock

### ✅ Criterios de Aceptación
- [ ] Migración ejecuta sin errores
- [ ] Campo aparece en API responses
- [ ] Función de evaluación funciona correctamente
- [ ] Frontend muestra indicador visual claro
- [ ] Colores diferenciados: ✅ Verde (completable), ❌ Rojo (incomplete), ⏳ Amarillo (pending)

### 📊 Beneficio Inmediato
- ✅ Visibilidad inmediata de órdenes problemáticas
- ✅ Helps prioritize which orders to review
- ✅ No more guessing about stock availability

### ⚠️ Riesgo
**Bajo** - Solo agrega información, no cambia flujos existentes

---

## **PASO 4: Evaluación FIFO inteligente**

### 🎯 Objetivo
Automatizar el proceso de evaluación de todas las órdenes pendientes en orden FIFO

### 📝 Descripción
Crear función que evalúe todas las órdenes PENDING en orden cronológico (FIFO) y determine cuáles pueden completarse con el stock actual disponible.

### 🔧 Cambios Técnicos
- **Archivo**: `app/services/order_service.py`
  - Método: `evaluate_all_pending_orders_fifo()`
  - Algoritmo FIFO de simulación de stock
- **Archivo**: `app/api/v1/orders.py`
  - Endpoint: `POST /orders/evaluate-completion`
- **Frontend**: Botón "Evaluar todas las órdenes"

### 📋 Algoritmo FIFO
```python
def evaluate_all_pending_orders_fifo(db: Session):
    # 1. Obtener todas las órdenes PENDING ordenadas por created_at
    # 2. Obtener stock actual de todos los productos
    # 3. Simular descuentos orden por orden
    # 4. Marcar cada orden como completable/incomplete
    # 5. No afectar stock real, solo simulación
    # 6. Retornar estadísticas del proceso
```

### ✅ Criterios de Aceptación
- [ ] Evalúa órdenes estrictamente por orden de llegada (FIFO)
- [ ] Simula descuentos sin afectar stock real
- [ ] Actualiza completion_status de todas las órdenes
- [ ] Retorna estadísticas: total evaluadas, completables, incompletas
- [ ] Performance aceptable (< 2 segundos para 100+ órdenes)
- [ ] Endpoint seguro (solo admin/manager)

### 📊 Beneficio Inmediato
- ✅ Automatiza completamente el proceso de consolidación manual
- ✅ Evaluación justa por orden de llegada
- ✅ Visibilidad completa del estado de todas las órdenes

### ⚠️ Riesgo
**Medio** - Nueva lógica compleja, pero no afecta datos existentes

---

## **PASO 5: Dashboard de producción**

### 🎯 Objetivo
Crear interfaz específica para el equipo de producción con consolidado automático

### 📝 Descripción
Dashboard que muestre el consolidado de todos los pedidos pendientes, stock actual, faltantes, y lista priorizada para producción.

### 🔧 Cambios Técnicos
- **Archivo**: `app/api/v1/orders.py`
  - Endpoint: `GET /orders/production-dashboard`
- **Service**: Método para consolidar órdenes completables
- **Frontend**: Nueva página "Dashboard Producción"

### 📋 Información del Dashboard
```
CONSOLIDADO DE PRODUCCIÓN
━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 PRODUCTOS TOTALES NECESARIOS:
  • Queso Fresco: 150 unidades (Stock: 80, Faltante: 70)
  • Crema: 45 litros (Stock: 30, Faltante: 15)
  • Quesillo: 200 unidades (Stock: 200, Disponible: ✅)

🎯 ÓRDENES COMPLETABLES: 12 de 18
⚠️  ÓRDENES INCOMPLETAS: 6

📋 LISTA PRIORIZADA (por fecha):
  1. ORD-001 - Cliente ABC - ✅ Completable
  2. ORD-002 - Cliente XYZ - ❌ Incompleta (falta 20 quesos)
  ...
```

### ✅ Criterios de Aceptación
- [ ] Consolidado automático por producto
- [ ] Stock actual vs demanda total
- [ ] Lista de faltantes por producto
- [ ] Órdenes ordenadas cronológicamente
- [ ] Indicadores visuales claros
- [ ] Actualización en tiempo real
- [ ] Export a PDF/Excel

### 📊 Beneficio Inmediato
- ✅ Reemplaza completamente el proceso manual de consolidación
- ✅ Información siempre actualizada para producción
- ✅ Elimina errores de cálculo manual

### ⚠️ Riesgo
**Bajo** - Solo interfaces nuevas, no modifica lógica existente

---

## **PASO 6: Edición completa de órdenes pendientes**

### 🎯 Objetivo
Permitir modificación libre de órdenes mientras están en estado PENDING

### 📝 Descripción
Habilitar edición completa (items, cantidades, cliente) para órdenes en estado PENDING, manteniendo restricciones para estados posteriores.

### 🔧 Cambios Técnicos
- **Archivo**: `app/services/order_service.py`
  - Método: `update_pending_order()`
  - Validaciones específicas para PENDING
- **Archivo**: `app/api/v1/orders.py`
  - Endpoints de edición para órdenes PENDING
- **Frontend**: Formulario de edición completa

### 📋 Funcionalidades de Edición
- ✏️ Modificar items (agregar/quitar productos)
- 🔢 Cambiar cantidades
- 👤 Cambiar cliente
- 📝 Modificar notas
- 🚚 Cambiar ruta
- 💰 Recalculo automático de totales

### ✅ Criterios de Aceptación
- [ ] Solo órdenes PENDING son editables
- [ ] Edición completa de todos los campos
- [ ] Validaciones básicas (productos activos, cliente válido)
- [ ] Recalculo automático de totales
- [ ] Historial de cambios (opcional)
- [ ] UI intuitiva para edición

### 📊 Beneficio Inmediato
- ✅ Máxima flexibilidad antes de comprometer stock
- ✅ Corrección fácil de errores de captura
- ✅ Adaptación rápida a cambios de cliente

### ⚠️ Riesgo
**Bajo** - Usa validaciones y funciones existentes

---

## 📈 Estrategia de Testing

### Por cada paso:
- [ ] **Unit Tests**: Funciones críticas
- [ ] **Integration Tests**: APIs completas
- [ ] **Manual Testing**: Flujos de usuario
- [ ] **Performance Tests**: Para Paso 4 especialmente

## 🚀 Estrategia de Deploy

### Después de cada paso:
1. ✅ Deploy a ambiente de pruebas
2. ✅ Validación con usuarios reales
3. ✅ Feedback y ajustes menores
4. ✅ Deploy a producción
5. ✅ Monitoreo post-deploy

## 📋 Checklist de Finalización

### Al completar todos los pasos:
- [ ] Proceso manual de consolidación eliminado
- [ ] Control total sobre stock y confirmaciones
- [ ] Dashboard funcional para producción
- [ ] Flexibilidad máxima para ventas
- [ ] Documentación actualizada
- [ ] Capacitación a usuarios completada

---

## 💡 Notas Importantes

1. **Cada paso es independiente** - Se puede parar en cualquier momento
2. **Backward compatibility** - No se rompe funcionalidad existente
3. **Rollback fácil** - Cada cambio es reversible
4. **Feedback temprano** - Validación constante con usuarios
5. **Riesgo minimizado** - Cambios incrementales pequeños

---

**Fecha de creación**: Septiembre 2025  
**Estado**: Planificación  
**Próximo paso**: PASO 1 - Órdenes sin descuento automático

