"""
AI query endpoint for natural language database queries and WhatsApp webhook.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from ...schemas.ai import (
    AIQueryRequest, AIQueryResponse, EvolutionWebhookEvent, DeviceStatusResponse
)
from ...services.ai_service import AIService
from ...services.whatsapp_service import WhatsAppService
from ..dependencies import get_ai_service, get_whatsapp_service
from .auth import get_current_active_user, get_tenant_db
from .settings import get_current_tenant
from ...models.user import User
from ...models.tenant import Tenant
import logging

logger = logging.getLogger(__name__)

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
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Error procesando la consulta: {str(e)}"
        )


@router.post("/webhook/whatsapp", status_code=status.HTTP_200_OK)
async def whatsapp_webhook(
    request: Request,
    ai_service: AIService = Depends(get_ai_service),
    whatsapp_service: WhatsAppService = Depends(get_whatsapp_service)
):
    """
    Webhook para recibir mensajes de EvolutionAPI de WhatsApp.

    Este endpoint:
    1. Recibe eventos de mensajes de EvolutionAPI
    2. Extrae el contenido del mensaje
    3. Procesa el mensaje con ChatGPT
    4. Envía la respuesta de vuelta a WhatsApp

    Args:
        request: Request de FastAPI con el body del webhook
        ai_service: Servicio de IA para procesar mensajes
        whatsapp_service: Servicio para enviar mensajes a WhatsApp

    Returns:
        dict: Confirmación de recepción del webhook
    """
    try:
        # Obtener el body del request como JSON
        body = await request.json()
        logger.info(f"Webhook recibido: {body.get('event', 'unknown')}")

        # Parsear el evento de EvolutionAPI
        try:
            webhook_event = EvolutionWebhookEvent(**body)
        except Exception as e:
            logger.warning(f"Error parseando webhook event: {e}")
            # Si no podemos parsear el evento, retornar 200 para que EvolutionAPI no reintente
            return {"status": "received", "message": "Event format not recognized"}

        # Solo procesar eventos de mensajes nuevos
        if webhook_event.event != "messages.upsert":
            logger.info(f"Evento ignorado: {webhook_event.event}")
            return {"status": "received", "message": f"Event {webhook_event.event} ignored"}

        # Extraer mensajes del evento
        messages = webhook_event.get_messages()

        if not messages:
            logger.info("No hay mensajes entrantes para procesar")
            return {"status": "received", "message": "No incoming messages to process"}

        # Procesar cada mensaje
        for message in messages:
            try:
                # Extraer el texto del mensaje
                text_content = message.get_text_content()

                if not text_content:
                    logger.info("Mensaje sin contenido de texto, ignorando")
                    continue

                # Obtener el número del remitente
                sender_number = message.get_sender_number()

                logger.info(f"Procesando mensaje de {sender_number}: {text_content[:50]}...")

                # Procesar el mensaje con ChatGPT
                response_text = ai_service.process_whatsapp_message(text_content)

                # Enviar la respuesta de vuelta a WhatsApp
                whatsapp_service.send_message(
                    to=sender_number,
                    message=response_text,
                    instance_name='default'
                )

                logger.info(f"Respuesta enviada exitosamente a {sender_number}")

            except Exception as e:
                logger.error(f"Error procesando mensaje individual: {e}")
                # Continuar con el siguiente mensaje aunque uno falle
                try:
                    # Intentar enviar un mensaje de error al usuario
                    sender_number = message.get_sender_number()
                    whatsapp_service.send_message(
                        to=sender_number,
                        message="Lo siento, hubo un error al procesar tu mensaje. Por favor intenta de nuevo más tarde.",
                        instance_name='default'
                    )
                except Exception:
                    pass  # Si falla enviar el error, no hacer nada más
                continue

        return {
            "status": "success",
            "message": f"Processed {len(messages)} message(s)"
        }

    except Exception as e:
        logger.error(f"Error procesando webhook: {e}")
        # Retornar 200 para evitar que EvolutionAPI reintente en caso de errores internos
        # que no se resolverán con reintentos
        return {
            "status": "error",
            "message": f"Error processing webhook: {str(e)}"
        }


@router.get("/device/status", response_model=DeviceStatusResponse, status_code=status.HTTP_200_OK)
def get_device_status(
    whatsapp_service: WhatsAppService = Depends(get_whatsapp_service),
    current_user: User = Depends(get_current_active_user),
    current_tenant: Optional[Tenant] = Depends(get_current_tenant)
):
    """
    Consulta el estado de conexión del dispositivo WhatsApp.

    Si el dispositivo está desconectado, obtiene y devuelve el código QR
    para reconectar. Si está conectado, indica el estado de conexión.

    Args:
        whatsapp_service: Servicio para interactuar con EvolutionAPI
        current_user: Usuario autenticado
        current_tenant: Tenant actual del usuario

    Returns:
        DeviceStatusResponse: Estado de conexión y QR code si está desconectado
    """
    try:
        # Validar que existe un tenant con schema_name
        if not current_tenant or not current_tenant.schema_name:
            raise HTTPException(
                status_code=400,
                detail="No se pudo determinar la instancia de WhatsApp. "
                       "El tenant no está configurado correctamente."
            )

        # Get instance_name from tenant schema
        instance_name = current_tenant.schema_name

        # Consultar el estado de conexión usando el schema del tenant
        connection_state = whatsapp_service.get_connection_state(instance_name=instance_name)

        # EvolutionAPI puede retornar el estado en diferentes campos
        # Intentamos diferentes campos posibles
        state = None
        if isinstance(connection_state, dict):
            state = (
                connection_state.get("state") or
                connection_state.get("status") or
                connection_state.get("connection") or
                connection_state.get("instance", {}).get("state")
            )

        # Normalizar el estado a lowercase para comparación
        state_lower = str(state).lower() if state else "unknown"

        # Verificar si está conectado
        # Estados comunes: "open", "connected", "ready"
        is_connected = state_lower in ["open", "connected", "ready", "authenticated"]

        if is_connected:
            logger.info(f"Dispositivo {instance_name} está conectado")
            return DeviceStatusResponse(
                status="connected",
                instance_name=instance_name,
                message=f"El dispositivo está conectado. Estado: {state}"
            )
        else:
            # Si está desconectado, obtener el QR code
            logger.info(f"Dispositivo {instance_name} está desconectado, obteniendo QR code")

            try:
                qr_data = whatsapp_service.get_qr_code(instance_name)

                # EvolutionAPI puede retornar el QR en diferentes formatos
                qr_code = None
                qr_url = None

                if isinstance(qr_data, dict):
                    # Intentar diferentes campos posibles
                    qr_code = (
                        qr_data.get("qrcode") or
                        qr_data.get("qr") or
                        qr_data.get("base64") or
                        qr_data.get("code") or
                        qr_data.get("data")
                    )
                    qr_url = qr_data.get("url") or qr_data.get("qr_url")
                elif isinstance(qr_data, str):
                    qr_code = qr_data

                # Si el QR viene con prefijo data:image, extraer solo el base64
                if qr_code and qr_code.startswith("data:image"):
                    # Formato: data:image/png;base64,iVBORw0KG...
                    parts = qr_code.split(",", 1)
                    if len(parts) > 1:
                        qr_code = parts[1]

                return DeviceStatusResponse(
                    status="disconnected",
                    instance_name=instance_name,
                    qr_code=qr_code,
                    qr_url=qr_url,
                    message=f"El dispositivo está desconectado. Estado: {state}. Escanea el QR code para conectar."
                )

            except Exception as qr_error:
                logger.error(f"Error al obtener QR code: {qr_error}")
                # Retornar estado desconectado sin QR si falla obtenerlo
                return DeviceStatusResponse(
                    status="disconnected",
                    instance_name=instance_name,
                    message=f"El dispositivo está desconectado. Estado: {state}. Error al obtener QR code: {str(qr_error)}"
                )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error consultando estado del dispositivo: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Error al consultar el estado del dispositivo: {str(e)}"
        )
