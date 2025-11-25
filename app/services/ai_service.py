"""
Service for handling AI queries using ChatGPT.
"""
import json
import logging
from decimal import Decimal
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from openai import OpenAI
from ..config import settings

logger = logging.getLogger(__name__)


class AIService:
    """Service for handling AI queries with ChatGPT integration."""

    @staticmethod
    def _convert_to_json_serializable(value: Any) -> Any:
        """
        Convierte valores no serializables a JSON a tipos serializables.

        Args:
            value: Valor a convertir

        Returns:
            Valor convertido a tipo JSON serializable
        """
        if isinstance(value, Decimal):
            # Convertir Decimal a float para JSON
            return float(value)
        elif hasattr(value, 'isoformat'):
            # Convertir datetime/date a string ISO
            return value.isoformat()
        elif isinstance(value, (bytes, bytearray)):
            # Convertir bytes a string
            return value.decode('utf-8')
        elif isinstance(value, dict):
            # Recursivamente convertir diccionarios
            return {k: AIService._convert_to_json_serializable(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple)):
            # Recursivamente convertir listas y tuplas
            return [AIService._convert_to_json_serializable(item) for item in value]
        else:
            return value

    def __init__(self):
        """Initialize AI service with OpenAI client."""
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key:
            raise ValueError("OPENAI_API_KEY no está configurada en las variables de entorno")
        # Inicializar cliente de OpenAI sin argumentos adicionales que puedan causar conflictos
        self.client = OpenAI(api_key=api_key, timeout=60.0)
        self.model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')

    def _get_database_schema(self, db: Session) -> str:
        """
        Obtiene el schema de la base de datos en formato texto.

        Args:
            db: Sesión de base de datos

        Returns:
            str: Schema de la base de datos en formato texto
        """
        schema_parts = []

        # Obtener el engine de la sesión
        engine = db.get_bind()
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        for table_name in tables:
            # Obtener columnas de la tabla
            columns = inspector.get_columns(table_name)
            foreign_keys = inspector.get_foreign_keys(table_name)

            schema_parts.append(f"\nTabla: {table_name}")
            schema_parts.append("Columnas:")
            for col in columns:
                col_type = str(col['type'])
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                default = f" DEFAULT {col['default']}" if col.get('default') else ""
                schema_parts.append(f"  - {col['name']}: {col_type} {nullable}{default}")

            if foreign_keys:
                schema_parts.append("Foreign Keys:")
                for fk in foreign_keys:
                    schema_parts.append(
                        f"  - {fk['constrained_columns']} -> "
                        f"{fk['referred_table']}.{fk['referred_columns']}"
                    )

        return "\n".join(schema_parts)

    def _generate_sql_query(self, user_query: str, db_schema: str) -> str:
        """
        Genera una query SQL usando ChatGPT basada en la consulta del usuario.

        Args:
            user_query: Consulta del usuario en lenguaje natural
            db_schema: Schema de la base de datos

        Returns:
            str: Query SQL generada
        """
        system_prompt = """Eres un experto en SQL y bases de datos PostgreSQL.
Tu tarea es generar queries SQL válidas basadas en consultas en lenguaje natural.

IMPORTANTE:
- Solo devuelve la query SQL, sin explicaciones adicionales
- No incluyas markdown ni bloques de código
- La query debe ser válida para PostgreSQL
- Usa nombres de tablas y columnas exactos del schema proporcionado
- Solo genera queries SELECT (no INSERT, UPDATE, DELETE)
- Si la consulta requiere JOINs, úsalos correctamente
- Devuelve solo la query SQL, sin texto adicional"""

        user_prompt = f"""Schema de la base de datos:

{db_schema}

Consulta del usuario: {user_query}

Genera una query SQL que responda a esta consulta. Solo devuelve la query SQL, sin explicaciones."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )

            sql_query = response.choices[0].message.content.strip()

            # Limpiar la query de posibles bloques de código markdown
            if sql_query.startswith("```sql"):
                sql_query = sql_query[6:]
            if sql_query.startswith("```"):
                sql_query = sql_query[3:]
            if sql_query.endswith("```"):
                sql_query = sql_query[:-3]
            sql_query = sql_query.strip()

            # return sql_query
            return "SELECT * FROM routes"
        except Exception as e:
            logger.error(f"Error generando query SQL: {e}")
            raise ValueError(f"Error al generar la query SQL: {str(e)}")

    def _execute_query(self, db: Session, sql_query: str) -> List[Dict[str, Any]]:
        """
        Ejecuta una query SQL en la base de datos.

        Args:
            db: Sesión de base de datos
            sql_query: Query SQL a ejecutar

        Returns:
            List[Dict[str, Any]]: Resultados de la query
        """
        try:
            # Validar que la query sea solo SELECT
            query_upper = sql_query.strip().upper()
            if not query_upper.startswith("SELECT"):
                raise ValueError("Solo se permiten queries SELECT")

            # Ejecutar la query
            result = db.execute(text(sql_query))
            rows = result.fetchall()

            # Convertir a lista de diccionarios
            columns = result.keys()
            results = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # Convertir tipos que no son JSON serializables (Decimal, datetime, etc.)
                    value = self._convert_to_json_serializable(value)
                    row_dict[col] = value
                results.append(row_dict)

            return results

        except Exception as e:
            logger.error(f"Error ejecutando query: {e}")
            raise ValueError(f"Error al ejecutar la query: {str(e)}")

    def _interpret_results(
        self,
        user_query: str,
        sql_query: str,
        results: List[Dict[str, Any]]
    ) -> str:
        """
        Interpreta los resultados de la query usando ChatGPT.

        Args:
            user_query: Consulta original del usuario
            sql_query: Query SQL ejecutada
            results: Resultados de la query

        Returns:
            str: Respuesta interpretada de ChatGPT
        """
        system_prompt = """Eres un asistente experto en análisis de datos.
Tu tarea es interpretar los resultados de una consulta SQL y proporcionar
una respuesta clara y útil en español al usuario.

IMPORTANTE:
- Responde en español
- Sé claro y conciso
- Si no hay resultados, explica por qué
- Si hay resultados, interpreta los datos de manera útil
- No repitas la query SQL, solo interpreta los resultados"""

        results_json = json.dumps(results, ensure_ascii=False, indent=2)

        user_prompt = f"""Consulta original del usuario: {user_query}

Query SQL ejecutada: {sql_query}

Resultados de la base de datos:
{results_json}

Interpreta estos resultados y proporciona una respuesta clara al usuario en español."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error interpretando resultados: {e}")
            raise ValueError(f"Error al interpretar los resultados: {str(e)}")

    def process_query(
        self,
        db: Session,
        user_query: str
    ) -> Dict[str, Any]:
        """
        Procesa una consulta del usuario: genera SQL, ejecuta y interpreta resultados.

        Args:
            db: Sesión de base de datos
            user_query: Consulta del usuario en lenguaje natural

        Returns:
            Dict con:
                - answer: Respuesta interpretada
                - sql_query: Query SQL generada
                - raw_results: Resultados raw de la BD
        """
        try:
            # 1. Obtener schema de la BD
            logger.info("Obteniendo schema de la base de datos...")
            db_schema = self._get_database_schema(db)

            # 2. Generar query SQL
            logger.info("Generando query SQL con ChatGPT...")
            sql_query = self._generate_sql_query(user_query, db_schema)
            logger.info(f"Query SQL generada: {sql_query}")

            # 3. Ejecutar query
            logger.info("Ejecutando query en la base de datos...")
            results = self._execute_query(db, sql_query)
            logger.info(f"Query ejecutada, {len(results)} resultados obtenidos")

            # 4. Interpretar resultados
            logger.info("Interpretando resultados con ChatGPT...")
            answer = self._interpret_results(user_query, sql_query, results)
            logger.info("Resultados interpretados exitosamente")

            return {
                "answer": answer,
                "sql_query": sql_query,
                "raw_results": results
            }

        except Exception as e:
            logger.error(f"Error procesando consulta: {e}")
            raise

    def process_whatsapp_message(
        self,
        user_message: str,
        context: Optional[str] = None
    ) -> str:
        """
        Procesa un mensaje de WhatsApp con ChatGPT y devuelve una respuesta conversacional.

        Args:
            user_message: Mensaje del usuario desde WhatsApp
            context: Contexto adicional opcional (ej: información del sistema)

        Returns:
            str: Respuesta generada por ChatGPT
        """
        system_prompt = """Eres un asistente virtual amigable y profesional para un sistema de gestión de pedidos.
Tu tarea es ayudar a los usuarios con consultas sobre pedidos, productos, clientes y otras operaciones del negocio.

IMPORTANTE:
- Responde en español de manera clara y concisa
- Sé amigable y profesional
- Si el usuario pregunta sobre información específica de la BD, puedes mencionar que necesitas acceso a la BD para consultarla
- Para consultas generales, proporciona respuestas útiles
- Si no entiendes algo, pide aclaración de manera amigable
- Mantén las respuestas breves y directas (idealmente menos de 200 palabras)"""

        user_prompt = user_message

        if context:
            user_prompt = f"Contexto: {context}\n\nMensaje del usuario: {user_message}"

        try:
            logger.info(f"Procesando mensaje de WhatsApp con ChatGPT: {user_message[:50]}...")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )

            answer = response.choices[0].message.content.strip()
            logger.info("Respuesta generada exitosamente por ChatGPT")

            return answer

        except Exception as e:
            logger.error(f"Error procesando mensaje de WhatsApp: {e}")
            raise ValueError(f"Error al procesar el mensaje: {str(e)}")
