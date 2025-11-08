"""
Schemas for AI query endpoint and WhatsApp webhook.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class AIQueryRequest(BaseModel):
    """Request schema for AI query endpoint."""
    query: str = Field(
        ...,
        description="Consulta del usuario en lenguaje natural (ej: 'cual es el cliente con mas ventas')",
        min_length=1,
        max_length=1000
    )


class AIQueryResponse(BaseModel):
    """Response schema for AI query endpoint."""
    answer: str = Field(
        ...,
        description="Respuesta interpretada de ChatGPT basada en los resultados de la consulta"
    )
    sql_query: str = Field(
        ...,
        description="Query SQL generada por ChatGPT y ejecutada en la base de datos"
    )
    raw_results: list = Field(
        ...,
        description="Resultados raw de la base de datos"
    )


# EvolutionAPI Webhook Schemas
class EvolutionMessageKey(BaseModel):
    """Message key from EvolutionAPI."""
    remoteJid: str = Field(..., description="WhatsApp ID del remitente")
    fromMe: bool = Field(False, description="Si el mensaje es enviado por nosotros")
    id: str = Field(..., description="ID del mensaje")

    class Config:
        populate_by_name = True
        # Permitir campos en camelCase
        allow_population_by_field_name = True


class EvolutionMessage(BaseModel):
    """Message content from EvolutionAPI."""
    key: EvolutionMessageKey
    message: Optional[Dict[str, Any]] = Field(None, description="Contenido del mensaje")
    messageTimestamp: Optional[int] = Field(None, description="Timestamp del mensaje")
    messageType: Optional[str] = Field(None, description="Tipo de mensaje")
    pushName: Optional[str] = Field(None, description="Nombre del contacto")

    class Config:
        populate_by_name = True
        # Permitir campos en camelCase
        allow_population_by_field_name = True

    def get_text_content(self) -> Optional[str]:
        """Extrae el contenido de texto del mensaje."""
        if not self.message:
            return None

        # EvolutionAPI puede enviar mensajes en diferentes formatos
        # Intentar extraer texto de diferentes campos posibles
        if "conversation" in self.message:
            return self.message["conversation"]
        elif "extendedTextMessage" in self.message:
            text_data = self.message["extendedTextMessage"]
            if isinstance(text_data, dict) and "text" in text_data:
                return text_data["text"]
        elif "text" in self.message:
            return self.message["text"]

        return None

    def get_sender_number(self) -> str:
        """Obtiene el número de teléfono del remitente."""
        # El remoteJid tiene formato: 50212345678@s.whatsapp.net
        jid = self.key.remoteJid
        if "@" in jid:
            return jid.split("@")[0]
        return jid

    def is_from_me(self) -> bool:
        """Verifica si el mensaje fue enviado por nosotros."""
        return self.key.fromMe


class EvolutionWebhookEvent(BaseModel):
    """Webhook event from EvolutionAPI."""
    event: str = Field(..., description="Tipo de evento (messages.upsert, etc.)")
    instance: str = Field(..., description="Nombre de la instancia")
    data: Dict[str, Any] = Field(..., description="Datos del evento")
    apikey: Optional[str] = Field(None, description="API key de EvolutionAPI")
    sender: Optional[str] = Field(None, description="Remitente del mensaje")

    def get_messages(self) -> list[EvolutionMessage]:
        """Extrae los mensajes del evento."""
        messages = []

        if self.event == "messages.upsert":
            # EvolutionAPI envía el mensaje directamente en data
            # La estructura es: data = { key: {...}, message: {...}, ... }
            try:
                # Construir el objeto mensaje desde data directamente
                message_data = {
                    "key": self.data.get("key", {}),
                    "message": self.data.get("message", {}),
                    "messageTimestamp": self.data.get("messageTimestamp"),
                    "messageType": self.data.get("messageType"),
                    "pushName": self.data.get("pushName")
                }

                # Convertir el mensaje a nuestro schema
                message = EvolutionMessage(**message_data)

                # Solo procesar mensajes entrantes (no enviados por nosotros)
                if message.is_from_me():
                    messages.append(message)
            except Exception as e:
                # Si hay error parseando el mensaje, loguear y continuar
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error parseando mensaje de EvolutionAPI: {e}")
                logger.debug(f"Datos recibidos: {self.data}")

        return messages


# Device Status Schemas
class DeviceStatusResponse(BaseModel):
    """Response schema for device status endpoint."""
    status: str = Field(..., description="Estado de conexión: 'connected' o 'disconnected'")
    instance_name: str = Field(..., description="Nombre de la instancia")
    qr_code: Optional[str] = Field(None, description="Código QR en base64 (solo si está desconectado)")
    qr_url: Optional[str] = Field(None, description="URL del QR code (solo si está desconectado)")
    message: Optional[str] = Field(None, description="Mensaje adicional sobre el estado")
