from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from .database import engine
from .models import Base
from .api.v1 import users, clients, products, orders, routes, auth, invoices, inventory, tenants, settings
import os

# IMPORTANTE: No crear tablas automáticamente en producción
# En producción usamos migraciones de Alembic
if os.getenv("ENVIRONMENT") != "production":
    Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Smart Orders API",
    description="API para gestión de pedidos con arquitectura limpia",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(clients.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(routes.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(invoices.router, prefix="/api/v1")
app.include_router(inventory.router, prefix="/api/v1")
app.include_router(tenants.router, prefix="/api/v1")
app.include_router(settings.router, prefix="/api/v1")


@app.get("/")
async def root():
    """
    Endpoint raíz con información básica de la API
    """
    return {
        "service": "Smart Orders API",
        "message": "API para gestión de pedidos multitenant",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """
    Endpoint de health check básico para servicios de deployment
    Verifica la conexión a la base de datos
    """
    try:
        # Verificar conexión a base de datos
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "service": "smart-orders-api",
                "environment": os.getenv("ENVIRONMENT", "development"),
                "database": "connected",
                "timestamp": f"{__import__('time').time()}"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "smart-orders-api", 
                "environment": os.getenv("ENVIRONMENT", "development"),
                "error": str(e),
                "database": "disconnected",
                "timestamp": f"{__import__('time').time()}"
            }
        )


@app.get("/health/detailed")
async def detailed_health_check():
    """
    Health check detallado que incluye verificación de migraciones
    """
    try:
        # Importar aquí para evitar errores de arranque
        import sys
        sys.path.append(".")
        from scripts.health_check import run_health_checks
        
        result = await run_health_checks()
        
        status_code = 200
        if result["status"] == "unhealthy":
            status_code = 503
        elif result["status"] == "warning":
            status_code = 200  # Warnings no deben fallar el health check
        
        return JSONResponse(
            status_code=status_code,
            content=result
        )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": f"Detailed health check failed: {str(e)}",
                "service": "smart-orders-api",
                "timestamp": f"{__import__('time').time()}"
            }
        )
