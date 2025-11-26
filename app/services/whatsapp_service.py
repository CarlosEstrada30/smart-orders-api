"""
Service for sending WhatsApp messages via EvolutionAPI.
"""
import logging
import httpx
import base64
from typing import Optional
from io import BytesIO
from ..config import settings

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Service for sending WhatsApp messages through EvolutionAPI."""

    def __init__(self):
        """Initialize WhatsApp service with EvolutionAPI configuration."""
        self.api_url = getattr(settings, 'EVOLUTION_API_URL', None)
        self.api_key = getattr(settings, 'EVOLUTION_API_KEY', None)

        if not self.api_url or not self.api_key:
            logger.warning(
                "EvolutionAPI configuration incomplete. "
                "WhatsApp messages will not be sent. "
                "Set EVOLUTION_API_URL, EVOLUTION_API_KEY, and EVOLUTION_INSTANCE_NAME."
            )

    def send_message(
        self,
        to: str,
        message: str,
        instance_name: str,
        delay: Optional[int] = None
    ) -> dict:
        """
        Envía un mensaje de texto a través de EvolutionAPI.

        Args:
            to: Número de teléfono del destinatario (formato: 50212345678)
            message: Contenido del mensaje
            delay: Delay opcional antes de enviar (en milisegundos)

        Returns:
            dict: Respuesta de EvolutionAPI

        Raises:
            ValueError: Si la configuración de EvolutionAPI está incompleta
            Exception: Si hay un error al enviar el mensaje
        """
        if not self.api_url or not self.api_key or not instance_name:
            raise ValueError(
                "EvolutionAPI configuration incomplete. "
                "Cannot send WhatsApp messages."
            )

        # Asegurar que el número tenga el formato correcto
        # EvolutionAPI espera el número sin @s.whatsapp.net
        if "@" in to:
            to = to.split("@")[0]

        # Construir la URL del endpoint
        url = f"{self.api_url.rstrip('/')}/message/sendText/{instance_name}"

        # Preparar el payload
        payload = {
            "number": to,
            "text": message
        }

        if delay:
            payload["delay"] = delay

        # Headers
        headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key
        }

        try:
            logger.info(f"Enviando mensaje a {to} a través de EvolutionAPI")

            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                result = response.json()
                logger.info(f"Mensaje enviado exitosamente a {to}")
                return result

        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP al enviar mensaje: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Error al enviar mensaje: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Error de conexión al enviar mensaje: {str(e)}")
            raise Exception(f"Error de conexión con EvolutionAPI: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado al enviar mensaje: {str(e)}")
            raise

    def send_message_with_context(
        self,
        to: str,
        message: str,
        instance_name: str,
        quoted_message_id: Optional[str] = None
    ) -> dict:
        """
        Envía un mensaje con contexto (respondiendo a otro mensaje).

        Args:
            to: Número de teléfono del destinatario
            message: Contenido del mensaje
            quoted_message_id: ID del mensaje al que se está respondiendo

        Returns:
            dict: Respuesta de EvolutionAPI
        """
        if not self.api_url or not self.api_key or not instance_name:
            raise ValueError(
                "EvolutionAPI configuration incomplete. "
                "Cannot send WhatsApp messages."
            )

        # Asegurar que el número tenga el formato correcto
        if "@" in to:
            to = to.split("@")[0]

        url = f"{self.api_url.rstrip('/')}/message/sendText/{instance_name}"

        payload = {
            "number": to,
            "text": message
        }

        if quoted_message_id:
            payload["quoted"] = quoted_message_id

        headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key
        }

        try:
            logger.info(f"Enviando mensaje con contexto a {to}")

            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                result = response.json()
                logger.info(f"Mensaje con contexto enviado exitosamente a {to}")
                return result

        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP al enviar mensaje con contexto: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Error al enviar mensaje: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Error de conexión al enviar mensaje con contexto: {str(e)}")
            raise Exception(f"Error de conexión con EvolutionAPI: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado al enviar mensaje con contexto: {str(e)}")
            raise

    def get_connection_state(self, instance_name: Optional[str] = None) -> dict:
        """
        Consulta el estado de conexión del dispositivo WhatsApp.

        Args:
            instance_name: Nombre de la instancia de EvolutionAPI

        Returns:
            dict: Estado de conexión con información del dispositivo

        Raises:
            ValueError: Si la configuración de EvolutionAPI está incompleta
            Exception: Si hay un error al consultar el estado
        """
        # Usar instance_name proporcionado o el de la configuración
        instance = instance_name

        if not self.api_url or not self.api_key or not instance:
            raise ValueError(
                "EvolutionAPI configuration incomplete. "
                "Cannot check connection state. "
                "Provide instance_name or set EVOLUTION_INSTANCE_NAME in settings."
            )

        # Construir la URL del endpoint
        url = f"{self.api_url.rstrip('/')}/instance/connectionState/{instance}"

        # Headers
        headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key
        }

        try:
            logger.info(f"Consultando estado de conexión de {instance}")

            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()

                result = response.json()
                logger.info(f"Estado de conexión obtenido: {result.get('state', 'unknown')}")
                return result

        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP al consultar estado: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Error al consultar estado: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Error de conexión al consultar estado: {str(e)}")
            raise Exception(f"Error de conexión con EvolutionAPI: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado al consultar estado: {str(e)}")
            raise

    def get_qr_code(self, instance_name) -> dict:
        """
        Obtiene el código QR para conectar/reconectar el dispositivo WhatsApp.

        Returns:
            dict: Información del QR code (puede incluir base64, url, etc.)

        Raises:
            ValueError: Si la configuración de EvolutionAPI está incompleta
            Exception: Si hay un error al obtener el QR
        """
        if not self.api_url or not self.api_key or not instance_name:
            raise ValueError(
                "EvolutionAPI configuration incomplete. "
                "Cannot get QR code."
            )

        # Construir la URL del endpoint
        # EvolutionAPI puede usar diferentes endpoints, intentamos el más común
        url = f"{self.api_url.rstrip('/')}/instance/connect/{instance_name}"

        # Headers
        headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key
        }

        try:
            logger.info(f"Obteniendo QR code para {instance_name}")

            with httpx.Client(timeout=30.0) as client:
                # Algunas versiones de EvolutionAPI usan GET, otras POST
                # Intentamos primero con POST (más común)
                response = client.post(url, headers=headers)

                # Si falla con POST, intentamos con GET
                if response.status_code == 404:
                    response = client.get(url, headers=headers)

                response.raise_for_status()

                result = response.json()
                logger.info("QR code obtenido exitosamente")
                return result

        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP al obtener QR: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Error al obtener QR: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Error de conexión al obtener QR: {str(e)}")
            raise Exception(f"Error de conexión con EvolutionAPI: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado al obtener QR: {str(e)}")
            raise

    def send_document(
        self,
        to: str,
        file_buffer: BytesIO,
        filename: str,
        instance_name: Optional[str] = None,
        caption: Optional[str] = None,
        delay: Optional[int] = None
    ) -> dict:
        """
        Envía un documento (PDF, imagen, etc.) a través de EvolutionAPI.

        Args:
            to: Número de teléfono del destinatario (formato: 50212345678)
            file_buffer: BytesIO buffer con el contenido del archivo
            filename: Nombre del archivo (ej: comprobante.pdf)
            instance_name: Nombre de la instancia de EvolutionAPI
            caption: Texto opcional que acompaña al documento
            delay: Delay opcional antes de enviar (en milisegundos)

        Returns:
            dict: Respuesta de EvolutionAPI

        Raises:
            ValueError: Si la configuración de EvolutionAPI está incompleta
            Exception: Si hay un error al enviar el documento
        """
        # Usar instance_name proporcionado o el de la configuración
        instance = instance_name

        if not self.api_url or not self.api_key or not instance:
            raise ValueError(
                "EvolutionAPI configuration incomplete. "
                "Cannot send WhatsApp documents. "
                "Provide instance_name or set EVOLUTION_INSTANCE_NAME in settings."
            )

        # Asegurar que el número tenga el formato correcto
        if "@" in to:
            to = to.split("@")[0]

        # Construir la URL del endpoint correcto
        url = f"{self.api_url.rstrip('/')}/message/sendMedia/{instance}"

        # Preparar el archivo para envío
        file_buffer.seek(0)  # Asegurar que estamos al inicio del buffer

        # Leer el contenido del archivo y convertirlo a base64
        file_content = file_buffer.read()
        file_base64 = base64.b64encode(file_content).decode('utf-8')

        # Determinar el tipo de media basado en la extensión del archivo
        media_type = "document"  # Por defecto documento
        mime_type = "application/pdf"  # Por defecto PDF
        if filename.lower().endswith(('.jpg', '.jpeg')):
            media_type = "image"
            mime_type = "image/jpeg"
        elif filename.lower().endswith('.png'):
            media_type = "image"
            mime_type = "image/png"
        elif filename.lower().endswith('.gif'):
            media_type = "image"
            mime_type = "image/gif"
        elif filename.lower().endswith('.webp'):
            media_type = "image"
            mime_type = "image/webp"
        elif filename.lower().endswith(('.mp4', '.avi', '.mov', '.webm')):
            media_type = "video"
            mime_type = "video/mp4"
        elif filename.lower().endswith(('.mp3', '.ogg', '.wav', '.m4a')):
            media_type = "audio"
            mime_type = "audio/mpeg"
        elif filename.lower().endswith('.pdf'):
            media_type = "document"
            mime_type = "application/pdf"
        elif filename.lower().endswith(('.doc', '.docx')):
            media_type = "document"
            mime_type = "application/msword"
        elif filename.lower().endswith(('.xls', '.xlsx')):
            media_type = "document"
            mime_type = "application/vnd.ms-excel"

        # Preparar el payload JSON según la documentación actualizada de EvolutionAPI
        # Todas las propiedades están en el nivel raíz del payload
        payload = {
            "number": to,
            "mediatype": media_type,
            "mimetype": mime_type,
            "media": file_base64,
            "fileName": filename
        }

        # Agregar caption si se proporciona
        if caption:
            payload["caption"] = caption

        # Agregar delay si se proporciona
        if delay:
            payload["delay"] = delay

        # Headers
        headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key
        }

        try:
            logger.info(f"Enviando documento {filename} a {to} a través de EvolutionAPI")
            logger.debug(f"Payload: {payload}")

            with httpx.Client(timeout=60.0) as client:  # Timeout más largo para archivos
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                result = response.json()
                logger.info(f"Documento {filename} enviado exitosamente a {to}")
                return result

        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP al enviar documento: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Error al enviar documento: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Error de conexión al enviar documento: {str(e)}")
            raise Exception(f"Error de conexión con EvolutionAPI: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado al enviar documento: {str(e)}")
            raise
