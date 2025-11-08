"""
Schemas for AI query endpoint.
"""
from pydantic import BaseModel, Field


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


