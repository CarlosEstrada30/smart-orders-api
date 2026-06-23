#!/usr/bin/env python3
"""
test_engine_leak.py — Verifica la fuga de engines de SQLAlchemy por request.

Genera el JWT automáticamente haciendo login contra la API, luego dispara
N requests en paralelo al endpoint de órdenes.

Observar en los logs del servidor:
  SIN FIX → aparece "[ENGINE #N]" en cada request (N líneas distintas)
  CON FIX → aparece "[ENGINE #1]" solo la primera vez, luego silencio

Uso:
    python scripts/test_engine_leak.py \\
        --email admin@bethel.com \\
        --password mipassword \\
        --subdominio bethel \\
        --requests 20

    # Sin subdominio (schema public):
    python scripts/test_engine_leak.py --email admin@example.com --password pw

    # Leer credenciales de .env:
    python scripts/test_engine_leak.py --from-env --subdominio bethel
"""
import argparse
import asyncio
import os
import sys
import time
from collections import Counter
from pathlib import Path

try:
    import httpx
except ImportError:
    print("[ERROR] Instala httpx: pip install httpx")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_dotenv(env_path: Path) -> dict:
    """Lee un .env básico sin dependencias externas."""
    values = {}
    if not env_path.exists():
        return values
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def pg_connection_count(database_url: str, app_name: str = "smart-orders-api-tenant") -> int | None:
    """Consulta pg_stat_activity para contar conexiones del tenant engine."""
    try:
        import psycopg2  # type: ignore
        conn = psycopg2.connect(database_url, connect_timeout=5)
        cur = conn.cursor()
        cur.execute(
            "SELECT count(*) FROM pg_stat_activity WHERE application_name = %s",
            (app_name,),
        )
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return count
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def get_token(api_url: str, email: str, password: str, subdominio: str | None) -> str:
    payload = {"email": email, "password": password}
    if subdominio:
        payload["subdominio"] = subdominio

    with httpx.Client(timeout=15) as client:
        resp = client.post(f"{api_url}/api/v1/auth/login", json=payload)

    if resp.status_code != 200:
        print(f"[ERROR] Login falló ({resp.status_code}): {resp.text}")
        sys.exit(1)

    token = resp.json().get("access_token")
    if not token:
        print(f"[ERROR] Respuesta sin access_token: {resp.json()}")
        sys.exit(1)

    return token


# ---------------------------------------------------------------------------
# Load test
# ---------------------------------------------------------------------------

async def fire_requests(
    api_url: str,
    token: str,
    n: int,
    endpoint: str,
) -> list[int]:
    """Dispara N requests en paralelo y devuelve lista de códigos HTTP."""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{api_url}{endpoint}"

    async with httpx.AsyncClient(timeout=30) as client:
        tasks = [client.get(url, headers=headers) for _ in range(n)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    codes = []
    for r in responses:
        if isinstance(r, Exception):
            codes.append(0)  # timeout / connection error
        else:
            codes.append(r.status_code)
    return codes


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Test de fuga de engines SQLAlchemy")
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--endpoint", default="/api/v1/orders/")
    parser.add_argument("--email", help="Email del usuario")
    parser.add_argument("--password", help="Password del usuario")
    parser.add_argument("--subdominio", default=None, help="Subdominio del tenant (omitir para schema public)")
    parser.add_argument("--requests", type=int, default=20, dest="n", metavar="N",
                        help="Número de requests en paralelo (default: 20)")
    parser.add_argument("--from-env", action="store_true",
                        help="Leer TEST_EMAIL/TEST_PASSWORD/TEST_SUBDOMINIO del .env")
    args = parser.parse_args()

    # Resolver credenciales
    env_file = Path(__file__).parent.parent / ".env"
    env = load_dotenv(env_file)

    if args.from_env:
        email = env.get("TEST_EMAIL", args.email)
        password = env.get("TEST_PASSWORD", args.password)
        subdominio = env.get("TEST_SUBDOMINIO", args.subdominio)
    else:
        email = args.email
        password = args.password
        subdominio = args.subdominio

    if not email or not password:
        parser.error("Proporciona --email y --password (o --from-env con TEST_EMAIL/TEST_PASSWORD en .env)")

    database_url = env.get("DATABASE_URL")

    # --- Header ---
    print("=" * 55)
    print("  Test de fuga de engines — SmartOrders API")
    print("=" * 55)
    print(f"  API       : {args.api_url}")
    print(f"  Endpoint  : {args.endpoint}")
    print(f"  Usuario   : {email}")
    print(f"  Subdominio: {subdominio or '(public)'}")
    print(f"  Requests  : {args.n} en paralelo")
    print()

    # --- Verificar servidor ---
    try:
        with httpx.Client(timeout=5) as c:
            c.get(f"{args.api_url}/health")
    except Exception:
        print(f"[ERROR] El servidor no responde en {args.api_url}")
        print("        Inicia el servidor con: uvicorn app.main:app --reload")
        sys.exit(1)
    print(f"[OK] Servidor activo en {args.api_url}")

    # --- Login ---
    print(f"[..] Haciendo login como {email}...")
    token = get_token(args.api_url, email, password, subdominio)
    print(f"[OK] Token obtenido: {token[:30]}...")
    print()

    # --- Conexiones antes ---
    pg_before = pg_connection_count(database_url) if database_url else None
    if pg_before is not None:
        print(f"[PG] Conexiones tenant ANTES: {pg_before}")

    # --- Fire ---
    print(f"Disparando {args.n} requests en paralelo...")
    print("  >> Revisa los logs del servidor para ver [ENGINE #N] <<")
    print("-" * 55)

    t0 = time.perf_counter()
    codes = asyncio.run(fire_requests(args.api_url, token, args.n, args.endpoint))
    elapsed = time.perf_counter() - t0

    print(f"  Completado en {elapsed:.2f}s")
    print()

    # --- Resultados HTTP ---
    counter = Counter(codes)
    print("Resultados HTTP:")
    for code, count in sorted(counter.items()):
        label = "OK" if 200 <= code < 300 else ("Error de red" if code == 0 else "Error")
        print(f"  HTTP {code or 'TIMEOUT'} ({label}) → {count} requests")

    # --- Conexiones después ---
    if database_url:
        pg_after = pg_connection_count(database_url)
        if pg_after is not None:
            delta = pg_after - (pg_before or 0)
            print()
            print(f"[PG] Conexiones tenant ANTES : {pg_before}")
            print(f"[PG] Conexiones tenant DESPUÉS: {pg_after}")
            if delta > 5:
                print(f"[!]  Conexiones crecieron en {delta} — fuga confirmada.")
            else:
                print(f"[OK] Conexiones estables (delta={delta:+d}).")

    # --- Interpretación ---
    print()
    print("=" * 55)
    print("  Interpreta los logs del servidor:")
    print(f"  SIN FIX → {args.n} líneas '[ENGINE #N]' distintas")
    print(f"  CON FIX → solo '[ENGINE #1]' la primera vez")
    print("=" * 55)


if __name__ == "__main__":
    main()
