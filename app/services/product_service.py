from typing import Optional, List
from sqlalchemy.orm import Session
import pandas as pd
from pydantic import ValidationError
from ..repositories.product_repository import ProductRepository
from ..repositories.product_route_price_repository import ProductRoutePriceRepository
from ..repositories.route_repository import RouteRepository
from ..schemas.product import ProductCreate, ProductUpdate, ProductResponse
from ..schemas.product_route_price import ProductRoutePriceCreate, ProductRoutePriceUpdate, ProductRoutePriceResponse, ProductRoutePriceSimpleResponse
from ..schemas.bulk_upload import ProductBulkUploadResult, BulkUploadError
from ..models.product import Product
from ..models.product_route_price import ProductRoutePrice
from ..utils.excel_utils import ExcelProcessor


class ProductService:
    def __init__(self):
        self.repository = ProductRepository()
        self.route_price_repository = ProductRoutePriceRepository()
        self.route_repository = RouteRepository()

    def _convert_to_response(self, db: Session, product: Product) -> ProductResponse:
        """Convert Product model to ProductResponse with route prices"""
        # Get route prices for this product
        route_prices = self.get_product_route_prices(db, product.id)
        
        # Convert route prices to response format
        route_price_responses = []
        for route_price in route_prices:
            # Get route name from database
            route = self.route_repository.get(db, route_price.route_id)
            route_name = route.name if route else None
            
            route_price_responses.append(ProductRoutePriceSimpleResponse(
                product_id=route_price.product_id,
                route_id=route_price.route_id,
                price=route_price.price,
                route_name=route_name
            ))
        
        return ProductResponse(
            id=product.id,
            name=product.name,
            description=product.description,
            price=product.price,
            stock=product.stock,
            sku=product.sku,
            is_active=product.is_active,
            created_at=product.created_at,
            updated_at=product.updated_at,
            route_prices=route_price_responses if route_price_responses else None
        )

    def get_product(self, db: Session, product_id: int) -> Optional[Product]:
        return self.repository.get(db, product_id)

    def get_product_by_sku(self, db: Session, sku: str) -> Optional[Product]:
        return self.repository.get_by_sku(db, sku=sku)

    def get_products(self, db: Session, skip: int = 0,
                     limit: int = 100) -> List[ProductResponse]:
        products = self.repository.get_multi(db, skip=skip, limit=limit)
        return [self._convert_to_response(db, product) for product in products]

    def get_active_products(
            self,
            db: Session,
            skip: int = 0,
            limit: int = 100) -> List[ProductResponse]:
        products = self.repository.get_active_products(db, skip=skip, limit=limit)
        return [self._convert_to_response(db, product) for product in products]

    def search_products_by_name(self, db: Session, name: str) -> List[ProductResponse]:
        products = self.repository.search_by_name(db, name=name)
        return [self._convert_to_response(db, product) for product in products]

    def get_low_stock_products(
            self,
            db: Session,
            threshold: int = 10) -> List[ProductResponse]:
        products = self.repository.get_low_stock_products(db, threshold=threshold)
        return [self._convert_to_response(db, product) for product in products]

    def create_product(self, db: Session, product: ProductCreate) -> Product:
        # Check if product with SKU already exists
        if self.repository.get_by_sku(db, sku=product.sku):
            raise ValueError("Product with this SKU already exists")

        return self.repository.create(db, obj_in=product)

    def update_product(
            self,
            db: Session,
            product_id: int,
            product_update: ProductUpdate) -> Optional[Product]:
        db_product = self.repository.get(db, product_id)
        if not db_product:
            return None

        update_data = product_update.model_dump(exclude_unset=True)

        # Check if SKU is being updated and if it already exists
        if "sku" in update_data:
            existing_product = self.repository.get_by_sku(
                db, sku=update_data["sku"])
            if existing_product and existing_product.id != product_id:
                raise ValueError("Product with this SKU already exists")

        return self.repository.update(
            db, db_obj=db_product, obj_in=update_data)

    def delete_product(
            self,
            db: Session,
            product_id: int) -> Optional[Product]:
        # Soft delete - just mark as inactive
        db_product = self.repository.get(db, product_id)
        if not db_product:
            return None

        return self.repository.update(
            db, db_obj=db_product, obj_in={
                "is_active": False})

    def reactivate_product(
            self,
            db: Session,
            product_id: int) -> Optional[Product]:
        db_product = self.repository.get(db, product_id)
        if not db_product:
            return None

        return self.repository.update(
            db, db_obj=db_product, obj_in={
                "is_active": True})

    def update_stock(self, db: Session, product_id: int,
                     quantity: int) -> Optional[Product]:
        return self.repository.update_stock(
            db, product_id=product_id, quantity=quantity)

    def check_stock_availability(
            self,
            db: Session,
            product_id: int,
            required_quantity: int) -> bool:
        product = self.repository.get(db, product_id)
        if not product or not product.is_active:
            return False
        return product.stock >= required_quantity

    def reserve_stock(
            self,
            db: Session,
            product_id: int,
            quantity: int) -> bool:
        """Reserve stock for an order (decrease stock)"""
        if not self.check_stock_availability(db, product_id, quantity):
            return False

        return self.repository.update_stock(
            db, product_id=product_id, quantity=-quantity) is not None
    
    async def bulk_upload_products(
            self, 
            db: Session, 
            excel_file) -> ProductBulkUploadResult:
        """
        Process bulk upload of products from Excel file
        """
        # Validate Excel file
        ExcelProcessor.validate_excel_file(excel_file)
        
        # Try to read Excel file - first try "Productos", then try first sheet
        df = None
        sheet_used = None
        try:
            df = await ExcelProcessor.read_excel_to_dataframe(excel_file, sheet_name="Productos")
            sheet_used = "Productos"
        except:
            try:
                df = await ExcelProcessor.read_excel_to_dataframe(excel_file)
                sheet_used = "primera hoja"
            except Exception as e:
                raise ValueError(f"Error reading Excel file: {str(e)}")
        
        # Show available columns for debugging
        available_columns = list(df.columns)
        
        # Map Spanish/English column names
        column_mapping = {
            'name': ['name', 'nombre', 'Name', 'Nombre', 'NOMBRE', 'NAME'],
            'price': ['price', 'precio', 'Price', 'Precio', 'PRECIO', 'PRICE'],
            'sku': ['sku', 'SKU', 'Sku', 'codigo', 'código', 'Codigo', 'Código', 'CODIGO', 'CÓDIGO'],
            'description': ['description', 'descripcion', 'descripción', 'Description', 'Descripcion', 'Descripción', 'DESCRIPCION', 'DESCRIPCIÓN'],
            'stock': ['stock', 'Stock', 'STOCK', 'inventario', 'Inventario', 'INVENTARIO'],
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
        required_columns = ['name', 'price', 'sku']
        missing_columns = []
        for col in required_columns:
            if col not in normalized_df.columns:
                missing_columns.append(col)
        
        if missing_columns:
            error_msg = f"Missing required columns: {', '.join(missing_columns)}\n"
            error_msg += f"Sheet used: {sheet_used}\n"
            error_msg += f"Available columns: {', '.join(available_columns)}\n"
            error_msg += f"Required columns:\n"
            error_msg += f"  - Name: could be any of: name, nombre, Name, Nombre, NOMBRE\n"
            error_msg += f"  - Price: could be any of: price, precio, Price, Precio, PRECIO\n"
            error_msg += f"  - SKU: could be any of: sku, SKU, codigo, código, Codigo, Código\n"
            error_msg += f"Make sure your Excel file has columns for product name, price, and SKU."
            raise ValueError(error_msg)
        
        df = normalized_df
        
        # Clean DataFrame
        df = ExcelProcessor.clean_dataframe(df)
        
        # Initialize result
        result = ProductBulkUploadResult(
            total_rows=len(df),
            successful_uploads=0,
            failed_uploads=0,
            errors=[],
            created_products=[]
        )
        
        # Process each row
        for index, row in df.iterrows():
            try:
                # Prepare product data
                product_data = {}
                
                # Required fields
                product_data['name'] = str(row.get('name', '')).strip()
                if not product_data['name']:
                    result.errors.append(BulkUploadError(
                        row=index + 2,  # +2 because Excel starts at 1 and has header
                        field='name',
                        error='Name is required'
                    ))
                    result.failed_uploads += 1
                    continue
                
                # Price validation
                try:
                    price = float(row.get('price', 0))
                    if price <= 0:
                        result.errors.append(BulkUploadError(
                            row=index + 2,
                            field='price',
                            error='Price must be greater than 0'
                        ))
                        result.failed_uploads += 1
                        continue
                    product_data['price'] = price
                except (ValueError, TypeError):
                    result.errors.append(BulkUploadError(
                        row=index + 2,
                        field='price',
                        error='Price must be a valid number'
                    ))
                    result.failed_uploads += 1
                    continue
                
                # SKU validation
                sku = str(row.get('sku', '')).strip()
                if not sku:
                    result.errors.append(BulkUploadError(
                        row=index + 2,
                        field='sku',
                        error='SKU is required'
                    ))
                    result.failed_uploads += 1
                    continue
                product_data['sku'] = sku
                
                # Optional fields
                description = str(row.get('description', '')).strip()
                if description and description != 'nan' and description != '':
                    product_data['description'] = description
                
                # Stock validation
                try:
                    stock = int(float(row.get('stock', 0)))
                    if stock < 0:
                        result.errors.append(BulkUploadError(
                            row=index + 2,
                            field='stock',
                            error='Stock cannot be negative'
                        ))
                        result.failed_uploads += 1
                        continue
                    product_data['stock'] = stock
                except (ValueError, TypeError):
                    result.errors.append(BulkUploadError(
                        row=index + 2,
                        field='stock',
                        error='Stock must be a valid integer'
                    ))
                    result.failed_uploads += 1
                    continue
                
                # Handle is_active
                is_active = row.get('is_active', True)
                if isinstance(is_active, str):
                    is_active = is_active.lower() in ['true', '1', 'yes', 'y', 'activo']
                product_data['is_active'] = bool(is_active)
                
                # Create ProductCreate object
                product_create = ProductCreate(**product_data)
                
                # Create product
                new_product = self.create_product(db, product_create)
                
                result.successful_uploads += 1
                result.created_products.append({
                    'id': new_product.id,
                    'name': new_product.name,
                    'sku': new_product.sku,
                    'price': new_product.price,
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
        
        return result

    # Métodos para manejar precios por ruta
    def get_product_price_for_route(self, db: Session, product_id: int, route_id: Optional[int] = None) -> float:
        """Obtener el precio de un producto para una ruta específica o el precio por defecto"""
        product = self.get_product(db, product_id)
        if not product:
            raise ValueError("Product not found")
        
        if route_id:
            route_price = self.route_price_repository.get_price_for_product_route(db, product_id, route_id)
            if route_price is not None:
                return route_price
        
        # Usar precio por defecto del producto
        return product.price

    def set_product_route_price(self, db: Session, product_id: int, route_id: int, price: float) -> ProductRoutePrice:
        """Establecer precio específico de un producto para una ruta"""
        # Verificar que el producto existe
        product = self.get_product(db, product_id)
        if not product:
            raise ValueError("Product not found")
        
        # Verificar que la ruta existe (asumiendo que hay un servicio de rutas)
        # TODO: Agregar verificación de ruta cuando esté disponible
        
        # Crear o actualizar precio por ruta
        existing_price = self.route_price_repository.get_by_product_and_route(db, product_id, route_id)
        if existing_price:
            return self.route_price_repository.update(db, db_obj=existing_price, obj_in={"price": price})
        else:
            from ..schemas.product_route_price import ProductRoutePriceCreate
            create_data = ProductRoutePriceCreate(
                product_id=product_id,
                route_id=route_id,
                price=price
            )
            return self.route_price_repository.create(db, obj_in=create_data)

    def get_product_route_prices(self, db: Session, product_id: int) -> List[ProductRoutePrice]:
        """Obtener todos los precios por ruta de un producto"""
        return self.route_price_repository.get_by_product(db, product_id)

    def delete_product_route_price(self, db: Session, product_id: int, route_id: int) -> bool:
        """Eliminar precio específico de un producto para una ruta"""
        price_entry = self.route_price_repository.get_by_product_and_route(db, product_id, route_id)
        if not price_entry:
            return False
        
        self.route_price_repository.remove(db, id=price_entry.id)
        return True
