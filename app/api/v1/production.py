from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date

from ...models.user import User
from .auth import get_current_active_user, get_tenant_db
from ...services.production_service import ProductionService
from ...schemas.production import ProductionDashboardResponse


router = APIRouter()


def get_production_service() -> ProductionService:
    """Dependency para obtener el servicio de producción"""
    return ProductionService()


@router.get("/dashboard", response_model=ProductionDashboardResponse)
def get_production_dashboard(
    route_id: int = Query(..., description="ID de la ruta"),
    date: date = Query(..., description="Fecha objetivo (YYYY-MM-DD)"),
    db: Session = Depends(get_tenant_db),
    production_service: ProductionService = Depends(get_production_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Dashboard de Producción

    Obtiene información detallada sobre la producción necesaria para una ruta y fecha específica.

    **Parámetros:**
    - `route_id`: ID de la ruta a analizar
    - `date`: Fecha objetivo para el análisis

    **Respuesta:**
    - Información de la ruta y fecha
    - Resumen de producción
    - Lista detallada de productos con stock, demanda y déficit
    """
    try:
        # Obtener dashboard de producción
        dashboard = production_service.get_production_dashboard(
            route_id=route_id,
            target_date=date,
            db=db
        )

        return dashboard

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback
        error_detail = f"Error generando dashboard de producción: {str(e)}\nTraceback: {traceback.format_exc()}"
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )
