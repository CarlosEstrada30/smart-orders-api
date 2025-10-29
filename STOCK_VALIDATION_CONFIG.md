# Configuración de Validación de Stock

## Variable de Entorno: ENABLE_STOCK_VALIDATION

Esta variable de entorno controla si el sistema debe realizar validaciones y gestión de stock al cambiar el estado de las órdenes.

### Valores Posibles:
- `true` o `True`: Habilita las validaciones de stock
- `false` o `False`: Deshabilita las validaciones de stock (valor por defecto)

### Comportamiento:

#### Cuando ENABLE_STOCK_VALIDATION=false (por defecto):
- ✅ Las órdenes pueden cambiar de estado libremente sin validaciones de stock
- ✅ No se reserva stock al confirmar órdenes
- ✅ No se restaura stock al cancelar órdenes
- ✅ No se valida disponibilidad de stock en actualizaciones masivas
- ✅ Solo se valida que los productos existan y estén activos

#### Cuando ENABLE_STOCK_VALIDATION=true:
- ✅ Se valida disponibilidad de stock antes de confirmar órdenes
- ✅ Se reserva stock al pasar de PENDING/CANCELLED a CONFIRMED/IN_PROGRESS/SHIPPED/DELIVERED
- ✅ Se restaura stock al pasar de estados confirmados a PENDING/CANCELLED
- ✅ Se valida stock en actualizaciones masivas de estado
- ✅ Se previenen cambios de estado si no hay stock suficiente

### Configuración:

Agregar la siguiente línea al archivo `.env`:

```bash
# Para deshabilitar validaciones de stock (por defecto)
ENABLE_STOCK_VALIDATION=false

# Para habilitar validaciones de stock
ENABLE_STOCK_VALIDATION=true
```

### Casos de Uso:

1. **Desarrollo/Testing**: `ENABLE_STOCK_VALIDATION=false`
   - Permite probar flujos de órdenes sin preocuparse por el stock
   - Facilita el desarrollo y testing

2. **Producción con Control de Stock**: `ENABLE_STOCK_VALIDATION=true`
   - Control completo del inventario
   - Previene overselling
   - Gestión automática de stock reservado

3. **Producción sin Control de Stock**: `ENABLE_STOCK_VALIDATION=false`
   - Para negocios que manejan stock externamente
   - Permite cambios de estado libres
   - Solo valida existencia de productos

### Funciones Afectadas:

- `_validate_and_reserve_stock_on_confirm()`: Valida y reserva stock al confirmar
- `_restore_stock_on_status_change()`: Restaura stock al cambiar estado
- `_validate_stock_availability_for_order()`: Valida disponibilidad para órdenes
- `cancel_order()`: Restaura stock al cancelar órdenes confirmadas
- `batch_update_status()`: Valida stock en actualizaciones masivas
