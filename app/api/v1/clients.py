from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io
from ...schemas.client import ClientCreate, ClientUpdate, ClientResponse
from ...schemas.bulk_upload import ClientBulkUploadResult
from ...services.client_service import ClientService
from ...utils.excel_utils import ExcelGenerator
from ..dependencies import get_client_service
from .auth import get_current_active_user, get_tenant_db
from ...models.user import User

router = APIRouter(prefix="/clients", tags=["clients"])


@router.post("/", response_model=ClientResponse,
             status_code=status.HTTP_201_CREATED)
def create_client(
    client: ClientCreate,
    db: Session = Depends(get_tenant_db),
    client_service: ClientService = Depends(get_client_service),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new client (requires authentication)"""
    try:
        return client_service.create_client(db, client)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[ClientResponse])
def get_clients(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    db: Session = Depends(get_tenant_db),
    client_service: ClientService = Depends(get_client_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get all clients (requires authentication)"""
    if active_only:
        return client_service.get_active_clients(db, skip=skip, limit=limit)
    return client_service.get_clients(db, skip=skip, limit=limit)


@router.get("/search", response_model=List[ClientResponse])
def search_clients(
    name: str,
    db: Session = Depends(get_tenant_db),
    client_service: ClientService = Depends(get_client_service),
    current_user: User = Depends(get_current_active_user)
):
    """Search clients by name (requires authentication)"""
    return client_service.search_clients_by_name(db, name=name)


@router.get("/export")
async def export_clients(
    active_only: bool = False,
    skip: int = 0,
    limit: int = 10000,
    db: Session = Depends(get_tenant_db),
    client_service: ClientService = Depends(get_client_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Export clients to Excel file (requires authentication)

    Parameters:
    - active_only: Export only active clients (default: false)
    - skip: Number of records to skip (default: 0)
    - limit: Maximum number of records to export (default: 10000)

    Returns an Excel file with the same format as the import template.
    """
    try:
        # Get clients data
        if active_only:
            clients = client_service.get_active_clients(db, skip=skip, limit=limit)
        else:
            clients = client_service.get_clients(db, skip=skip, limit=limit)

        # Convert to dict format for Excel generator
        clients_data = []
        for client in clients:
            clients_data.append({
                'name': client.name,
                'email': client.email,
                'phone': client.phone,
                'nit': client.nit,
                'address': client.address,
                'is_active': client.is_active
            })

        # Generate Excel data
        excel_data = ExcelGenerator.export_clients_data(clients_data)

        # Generate filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"clientes_export_{timestamp}.xlsx"

        return StreamingResponse(
            io.BytesIO(excel_data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting clients: {str(e)}")


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: int,
    db: Session = Depends(get_tenant_db),
    client_service: ClientService = Depends(get_client_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific client by ID (requires authentication)"""
    client = client_service.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    client_update: ClientUpdate,
    db: Session = Depends(get_tenant_db),
    client_service: ClientService = Depends(get_client_service),
    current_user: User = Depends(get_current_active_user)
):
    """Update a client (requires authentication)"""
    try:
        client = client_service.update_client(db, client_id, client_update)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        return client
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: int,
    db: Session = Depends(get_tenant_db),
    client_service: ClientService = Depends(get_client_service),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a client (soft delete) (requires authentication)"""
    client = client_service.delete_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return None


@router.post("/{client_id}/reactivate", response_model=ClientResponse)
def reactivate_client(
    client_id: int,
    db: Session = Depends(get_tenant_db),
    client_service: ClientService = Depends(get_client_service),
    current_user: User = Depends(get_current_active_user)
):
    """Reactivate a deleted client (requires authentication)"""
    client = client_service.reactivate_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.post("/bulk-upload", response_model=ClientBulkUploadResult)
async def bulk_upload_clients(
    file: UploadFile = File(..., description="Excel file with client data"),
    db: Session = Depends(get_tenant_db),
    client_service: ClientService = Depends(get_client_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Bulk upload clients from Excel file (requires authentication)

    The Excel file should preferably have a 'Clientes' sheet, but any sheet will work.
    Accepts column names in Spanish or English:

    REQUIRED COLUMNS (any of these names):
    - name / nombre / Name / Nombre / NOMBRE: Client name

    OPTIONAL COLUMNS (any of these names):
    - email / correo / Email / Correo: Client email
    - phone / telefono / teléfono / Phone / Teléfono: Client phone
    - nit / NIT / Nit: Client NIT
    - address / direccion / dirección / Address / Dirección: Client address
    - is_active / activo / Active / Activo: true/false for active status

    Download the template using GET /api/v1/clients/template/download for the correct format.
    """
    try:
        result = await client_service.bulk_upload_clients(db, file)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@router.get("/template/download")
async def download_clients_template(
    current_user: User = Depends(get_current_active_user)
):
    """
    Download Excel template for bulk client upload (requires authentication)
    """
    try:
        excel_data = ExcelGenerator.create_clients_template()

        return StreamingResponse(
            io.BytesIO(excel_data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=plantilla_clientes.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating template: {str(e)}")
