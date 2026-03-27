# SmartOrders API

Python FastAPI backend — SQLAlchemy 2.0, PostgreSQL, Pydantic v2, schema-per-tenant multi-tenancy.

## Stack
| Tool | Version | Purpose |
|------|---------|---------|
| FastAPI | 0.104 | Web framework |
| Uvicorn | 0.24 | ASGI server |
| SQLAlchemy | 2.0 | ORM (sync sessions) |
| Alembic | 1.12 | DB migrations |
| PostgreSQL | — | Database (schema-per-tenant) |
| Pydantic | v2 | Request/response validation |
| pydantic-settings | v2 | Config via .env |
| python-jose | — | JWT auth |
| passlib/bcrypt | — | Password hashing |
| ReportLab + WeasyPrint | — | PDF generation |
| OpenAI | v1.55 | AI endpoints |
| EvolutionAPI | — | WhatsApp notifications |
| Cloudflare R2 (boto3) | — | File storage |
| FEL | — | Guatemalan e-invoicing |

## Project Layout
```
app/
├── main.py                # App construction, middleware, router registration
├── config.py              # Settings (pydantic-settings) — all config here
├── database.py            # Engine, SessionLocal, get_db() dependency
├── api/
│   ├── dependencies.py    # Shared Depends() factories
│   └── v1/
│       ├── auth.py        # Login, /me, /permissions + get_tenant_db
│       ├── ai.py, orders.py, products.py, ...  # One file per resource
│       └── __init__.py
├── middleware/
│   └── timezone_middleware.py   # Reads X-Timezone header
├── models/                # SQLAlchemy ORM models
├── schemas/
│   ├── base.py            # TimezoneAwareBaseModel, TimestampMixin
│   └── {resource}.py
├── repositories/
│   ├── base.py            # Generic BaseRepository[Model, Create, Update]
│   └── {resource}_repository.py
├── services/              # Business logic (no DB access here)
│   └── {resource}_service.py
└── utils/
    ├── permissions.py     # can_*() functions, get_user_permissions()
    ├── tenant_db.py       # Schema creation, get_session_for_schema()
    └── timezone.py        # UTC <-> client timezone conversion
alembic/
    versions/              # Migration files — never edit manually
tests/
    conftest.py            # pytest fixtures (client, db_session, auth_headers)
    factories.py           # Test data factories
    api/                   # Integration tests per resource
    unit/                  # Unit tests
```

## Architecture: 4-Layer Pattern
Every resource strictly follows this layering:
```
Router  (api/v1/{resource}.py)              — HTTP handling, auth/permission checks
  -> Service  (services/{resource}_service.py)      — business logic only
  -> Repository  (repositories/{resource}_repo.py)  — DB queries only
  -> Model  (models/{resource}.py)                  — ORM definition
```
No raw SQL in routers or services. No business logic in repositories.

## Multi-Tenancy — Critical Rules
- Each tenant has its own PostgreSQL schema (e.g. `lacteos_abc123`).
- JWT payload contains `tenant_schema`.
- **`get_tenant_db`** (from `app.api.v1.auth`) → use for ALL tenant-scoped routes.
- **`get_db`** → use ONLY for superadmin / tenant-management routes.
- `get_session_for_schema(schema_name)` in `app.utils.tenant_db` creates tenant sessions.
- **Never** mix sessions from different schemas in one request.
- New tenant: call `create_schema_if_not_exists()` then `run_migrations_for_schema()`.

## Standard Endpoint Signature
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..api.v1.auth import get_tenant_db, get_current_active_user
from ..models.user import User

router = APIRouter(prefix="/resource", tags=["resource"])

@router.get("/", response_model=list[ResourceResponse])
def list_resources(
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_active_user),
):
    if not can_view_resource(current_user):
        raise HTTPException(status_code=403, detail="Sin permisos")
    return resource_service.get_all(db)
```

## Roles (ascending privilege)
`EMPLOYEE < SALES < DRIVER < SUPERVISOR < MANAGER < ADMIN`
- `is_superuser=True` bypasses all role checks.
- Permission functions live in `app/utils/permissions.py` — always call them in the router.
- Raise `HTTPException(403)` on permission failure, `HTTPException(404)` when not found.
- `ValueError` from service layer → catch in router → re-raise as `HTTPException(400)`.

## Model Template
```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class NewModel(Base):
    __tablename__ = "new_models"
    id = Column(Integer, primary_key=True, index=True)
    # ...fields...
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

## Schema (Pydantic v2) Template
```python
from pydantic import BaseModel
from typing import Optional
from .base import TimezoneAwareBaseModel

class NewModelBase(BaseModel):
    name: str

class NewModelCreate(NewModelBase):
    pass

class NewModelUpdate(BaseModel):
    name: Optional[str] = None   # all Optional for PATCH

class NewModelResponse(NewModelBase, TimezoneAwareBaseModel):
    id: int
    class Config:
        from_attributes = True
```
- Use `model_dump(exclude_unset=True)` for update operations.
- Inherit `TimezoneAwareBaseModel` for any response schema with datetime fields.

## Repository Template
```python
from .base import BaseRepository
from ..models.new_model import NewModel
from ..schemas.new_model import NewModelCreate, NewModelUpdate

class NewModelRepository(BaseRepository[NewModel, NewModelCreate, NewModelUpdate]):
    def __init__(self):
        super().__init__(NewModel)
    # custom query methods go here
```
`BaseRepository` provides: `get()`, `get_multi()`, `create()`, `update()`, `remove()`.

## Migrations (Alembic)
```bash
# After modifying a model:
alembic revision --autogenerate -m "describe_the_change"
# Review the generated file in alembic/versions/ before applying:
alembic upgrade head
# Roll back one step:
alembic downgrade -1
```
**NEVER** call `Base.metadata.create_all()` in production — tenant schemas use `run_migrations_for_schema()`.

## Settings
```python
from ..config import settings
# settings.DATABASE_URL, settings.SECRET_KEY, settings.ENVIRONMENT
# settings.DEFAULT_TIMEZONE  → "America/Guatemala"
# settings.is_production     → bool
```

## Timezone Handling
- Store all datetimes as UTC in DB (`DateTime(timezone=True)` columns).
- Default timezone: `America/Guatemala` (UTC-6).
- Client sends `X-Timezone` header → `get_request_timezone(request)` reads it.
- Use `convert_utc_to_client_timezone()` from `app.utils.timezone` when returning display values.

## Running the Server
```bash
# Development (from smart-orders-api/, venv active):
uvicorn app.main:app --reload --port 8000
# Docs: http://localhost:8000/docs (Swagger), /redoc

# Production (via entrypoint.sh):
gunicorn app.main:app -k uvicorn.workers.UvicornWorker
```

## Testing
```bash
PIPENV_IGNORE_VIRTUALENVS=1 pipenv run pytest tests/ -v   # Full suite
PIPENV_IGNORE_VIRTUALENVS=1 pipenv run pytest tests/api/ -v
PIPENV_IGNORE_VIRTUALENVS=1 pipenv run pytest -k "test_orders" -v
```
Test env vars are injected by `pytest-env` via `pytest.ini` (no need to load `.env` manually).

### Test naming rules
- **All test function and class names must be in English** — no Spanish identifiers.
  - Good: `test_create_order_success`, `test_employee_cannot_confirm`
  - Bad: `test_crear_orden_exitoso`, `test_empleado_no_puede_confirmar`
- Use the pattern `test_{action}_{condition}` or `test_{action}_{object}_{result}`.
- Class names follow `Test{Resource}{Action}` (e.g. `TestCreateOrder`, `TestGetMe`).
- Docstrings and inline comments inside tests may be in Spanish.

## Coding Style
- Type annotations on all functions.
- Docstrings on public service and repository methods.
- Spanish comments are acceptable (legacy codebase uses them).
- Import order: stdlib → third-party → local (relative).
- No `import *`. Line length: 88 chars (Black-compatible).
- Prefer explicit over magic; avoid overriding SQLAlchemy internals.

## Key Files
- [app/main.py](app/main.py) — app construction, middleware, router registration
- [app/config.py](app/config.py) — all settings with defaults
- [app/database.py](app/database.py) — engine, SessionLocal, get_db()
- [app/api/v1/auth.py](app/api/v1/auth.py) — JWT auth + `get_tenant_db`
- [app/utils/tenant_db.py](app/utils/tenant_db.py) — schema creation, session-per-schema
- [app/utils/permissions.py](app/utils/permissions.py) — role-based permission functions
- [app/repositories/base.py](app/repositories/base.py) — generic CRUD BaseRepository
- [app/schemas/base.py](app/schemas/base.py) — TimezoneAwareBaseModel
