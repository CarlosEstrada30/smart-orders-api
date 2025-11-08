"""
AI query endpoint for natural language database queries.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ...schemas.ai import AIQueryRequest, AIQueryResponse
from ...services.ai_service import AIService
from ..dependencies import get_ai_service
from .auth import get_current_active_user, get_tenant_db
from ...models.user import User

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/query", response_model=AIQueryResponse, status_code=status.HTTP_200_OK)
def query_database(
    request: AIQueryRequest,
    db: Session = Depends(get_tenant_db),
    ai_service: AIService = Depends(get_ai_service)
):
    """
    Procesa una consulta del usuario en lenguaje natural y devuelve una respuesta interpretada.
    
    El flujo es:
    1. Recibe la consulta del usuario (ej: "cual es el cliente con mas ventas")
    2. Pasa la consulta a ChatGPT junto con el schema de la BD
    3. ChatGPT genera una query SQL
    4. Se ejecuta la query en la BD
    5. Los resultados se pasan a ChatGPT para interpretación
    6. Se devuelve la respuesta interpretada al usuario
    
    Args:
        request: Request con la consulta del usuario
        db: Sesión de base de datos
        ai_service: Servicio de IA
        current_user: Usuario autenticado
        
    Returns:
        AIQueryResponse: Respuesta con la interpretación, query SQL y resultados raw
    """
    try:
        result = ai_service.process_query(db, request.query)
        return AIQueryResponse(
            answer=result["answer"],
            sql_query=result["sql_query"],
            raw_results=result["raw_results"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando la consulta: {str(e)}"
        )

