"""
Utilidades para el manejo de monedas por tenant.

Cada tenant puede configurar su propia moneda (currency_code) en Settings.
Este módulo centraliza el catálogo de monedas soportadas y el formateo
de montos monetarios para PDFs y comprobantes.
"""

CURRENCIES: dict[str, dict] = {
    "GTQ": {
        "symbol": "Q",
        "name": "Quetzal guatemalteco",
        "locale": "es-GT",
    },
    "USD": {
        "symbol": "$",
        "name": "Dólar estadounidense",
        "locale": "en-US",
    },
    "MXN": {
        "symbol": "$",
        "name": "Peso mexicano",
        "locale": "es-MX",
    },
    "HNL": {
        "symbol": "L",
        "name": "Lempira hondureño",
        "locale": "es-HN",
    },
    "CRC": {
        "symbol": "₡",
        "name": "Colón costarricense",
        "locale": "es-CR",
    },
    "COP": {
        "symbol": "$",
        "name": "Peso colombiano",
        "locale": "es-CO",
    },
    "NIO": {
        "symbol": "C$",
        "name": "Córdoba nicaragüense",
        "locale": "es-NI",
    },
    "PAB": {
        "symbol": "B/.",
        "name": "Balboa panameño",
        "locale": "es-PA",
    },
    "PEN": {
        "symbol": "S/",
        "name": "Sol peruano",
        "locale": "es-PE",
    },
}


def format_currency(amount: float, currency_code: str = "GTQ") -> str:
    """
    Formatea un monto monetario usando el símbolo de la moneda del tenant.

    Args:
        amount: Monto a formatear.
        currency_code: Código ISO 4217 de la moneda (por defecto "GTQ").
            Si el código no existe en CURRENCIES, se usa el símbolo de GTQ.

    Returns:
        Cadena formateada, p.ej. "Q 1,234.56".
    """
    currency = CURRENCIES.get(currency_code, CURRENCIES["GTQ"])
    symbol = currency["symbol"]
    return f"{symbol} {amount:,.2f}"
