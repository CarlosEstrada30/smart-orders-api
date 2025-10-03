from typing import Optional, List
from sqlalchemy.orm import Session
from pydantic import ValidationError
from ..repositories.client_repository import ClientRepository
from ..schemas.client import ClientCreate, ClientUpdate
from ..schemas.bulk_upload import ClientBulkUploadResult, BulkUploadError
from ..models.client import Client
from ..utils.excel_utils import ExcelProcessor


class ClientService:
    def __init__(self):
        self.repository = ClientRepository()

    def get_client(self, db: Session, client_id: int) -> Optional[Client]:
        return self.repository.get(db, client_id)

    def get_client_by_email(self, db: Session, email: str) -> Optional[Client]:
        return self.repository.get_by_email(db, email=email)

    def get_client_by_nit(self, db: Session, nit: str) -> Optional[Client]:
        return self.repository.get_by_nit(db, nit=nit)

    def get_clients(self, db: Session, skip: int = 0,
                    limit: int = 100) -> List[Client]:
        return self.repository.get_multi(db, skip=skip, limit=limit)

    def get_active_clients(
            self,
            db: Session,
            skip: int = 0,
            limit: int = 100) -> List[Client]:
        return self.repository.get_active_clients(db, skip=skip, limit=limit)

    def search_clients_by_name(self, db: Session, name: str) -> List[Client]:
        return self.repository.search_by_name(db, name=name)

    def create_client(self, db: Session, client: ClientCreate) -> Client:
        # Check if client with email already exists (only if email is provided)
        if client.email and self.repository.get_by_email(
                db, email=client.email):
            raise ValueError("Client with this email already exists")

        return self.repository.create(db, obj_in=client)

    def update_client(
            self,
            db: Session,
            client_id: int,
            client_update: ClientUpdate) -> Optional[Client]:
        db_client = self.repository.get(db, client_id)
        if not db_client:
            return None

        update_data = client_update.model_dump(exclude_unset=True)

        # Check if email is being updated and if it already exists (only if
        # email is not None)
        if "email" in update_data and update_data["email"]:
            existing_client = self.repository.get_by_email(
                db, email=update_data["email"])
            if existing_client and existing_client.id != client_id:
                raise ValueError("Client with this email already exists")

        return self.repository.update(db, db_obj=db_client, obj_in=update_data)

    def delete_client(self, db: Session, client_id: int) -> Optional[Client]:
        # Soft delete - just mark as inactive
        db_client = self.repository.get(db, client_id)
        if not db_client:
            return None

        return self.repository.update(
            db, db_obj=db_client, obj_in={
                "is_active": False})

    def reactivate_client(
            self,
            db: Session,
            client_id: int) -> Optional[Client]:
        db_client = self.repository.get(db, client_id)
        if not db_client:
            return None

        return self.repository.update(
            db, db_obj=db_client, obj_in={
                "is_active": True})

    async def bulk_upload_clients(
            self,
            db: Session,
            excel_file) -> ClientBulkUploadResult:
        """
        Process bulk upload of clients from Excel file
        """
        # Validate Excel file
        ExcelProcessor.validate_excel_file(excel_file)

        # Read and normalize Excel file
        df, sheet_used = await self._read_excel_file(excel_file)
        df = self._normalize_columns(df, sheet_used)

        # Initialize result
        result = ClientBulkUploadResult(
            total_rows=len(df),
            successful_uploads=0,
            failed_uploads=0,
            errors=[],
            created_clients=[]
        )

        # Process each row
        for index, row in df.iterrows():
            self._process_client_row(db, result, index, row)

        return result

    async def _read_excel_file(self, excel_file):
        """Read Excel file and return dataframe with sheet info"""
        try:
            df = await ExcelProcessor.read_excel_to_dataframe(excel_file, sheet_name="Clientes")
            sheet_used = "Clientes"
        except Exception:
            try:
                df = await ExcelProcessor.read_excel_to_dataframe(excel_file)
                sheet_used = "primera hoja"
            except Exception as e:
                raise ValueError(f"Error reading Excel file: {str(e)}")

        return df, sheet_used

    def _normalize_columns(self, df, sheet_used):
        """Normalize column names and validate required columns"""
        available_columns = list(df.columns)
        # Map Spanish/English column names
        column_mapping = {
            'name': ['name', 'nombre', 'Name', 'Nombre', 'NOMBRE', 'NAME'],
            'email': ['email', 'correo', 'Email', 'Correo', 'EMAIL', 'CORREO'],
            'phone': ['phone', 'telefono', 'teléfono', 'Phone', 'Teléfono', 'TELÉFONO', 'TELEFONO'],
            'nit': ['nit', 'NIT', 'Nit'],
            'address': ['address', 'direccion', 'dirección', 'Address', 'Dirección', 'DIRECCIÓN'],
            'is_active': ['is_active', 'activo', 'active', 'Active', 'Activo', 'ACTIVO', 'IS_ACTIVE']
        }

        # Normalize column names
        normalized_df = df.copy()
        column_map = {}

        for standard_name, possible_names in column_mapping.items():
            for possible_name in possible_names:
                if possible_name in df.columns:
                    normalized_df = normalized_df.rename(columns={possible_name: standard_name})
                    column_map[possible_name] = standard_name
                    break

        # Validate required columns (after normalization)
        required_columns = ['name']
        missing_columns = []
        for col in required_columns:
            if col not in normalized_df.columns:
                missing_columns.append(col)

        if missing_columns:
            error_msg = f"Missing required columns: {', '.join(missing_columns)}\n"
            error_msg += f"Sheet used: {sheet_used}\n"
            error_msg += f"Available columns: {', '.join(available_columns)}\n"
            error_msg += "Required: Column for 'name' (could be: name, nombre, Name, Nombre, NOMBRE, NAME)\n"
            error_msg += "Make sure your Excel file has a column for the client name."
            raise ValueError(error_msg)

        # Clean DataFrame
        return ExcelProcessor.clean_dataframe(normalized_df)

    def _process_client_row(self, db, result, index, row):
        """Process a single client row from the Excel file"""
        try:
            client_data = self._extract_client_data(row)
            # Validate required fields
            if not client_data.get('name'):
                result.errors.append(BulkUploadError(
                    row=index + 2,  # +2 because Excel starts at 1 and has header
                    field='name',
                    error='Name is required'
                ))
                result.failed_uploads += 1
                return

            # Create ClientCreate object
            client_create = ClientCreate(**client_data)

            # Create client
            new_client = self.create_client(db, client_create)

            result.successful_uploads += 1
            result.created_clients.append({
                'id': new_client.id,
                'name': new_client.name,
                'email': new_client.email,
                'row': index + 2
            })

        except ValueError as e:
            result.errors.append(BulkUploadError(
                row=index + 2,
                error=str(e)
            ))
            result.failed_uploads += 1

        except ValidationError as e:
            for error in e.errors():
                result.errors.append(BulkUploadError(
                    row=index + 2,
                    field=error.get('loc', [None])[0] if error.get('loc') else None,
                    error=error.get('msg', 'Validation error')
                ))
            result.failed_uploads += 1

        except Exception as e:
            result.errors.append(BulkUploadError(
                row=index + 2,
                error=f"Unexpected error: {str(e)}"
            ))
            result.failed_uploads += 1

    def _extract_client_data(self, row):
        """Extract and clean client data from a row"""
        client_data = {}

        # Required fields
        client_data['name'] = str(row.get('name', '')).strip()

        # Optional fields
        email = str(row.get('email', '')).strip()
        if email and email != 'nan' and email != '':
            client_data['email'] = email

        phone = str(row.get('phone', '')).strip()
        if phone and phone != 'nan' and phone != '':
            client_data['phone'] = phone

        nit = str(row.get('nit', '')).strip()
        if nit and nit != 'nan' and nit != '':
            client_data['nit'] = nit

        address = str(row.get('address', '')).strip()
        if address and address != 'nan' and address != '':
            client_data['address'] = address

        # Handle is_active
        is_active = row.get('is_active', True)
        if isinstance(is_active, str):
            is_active = is_active.lower() in ['true', '1', 'yes', 'y', 'activo']
        client_data['is_active'] = bool(is_active)

        return client_data
