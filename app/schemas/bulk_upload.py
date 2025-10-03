from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class BulkUploadError(BaseModel):
    row: int
    field: Optional[str] = None
    error: str


class BulkUploadResult(BaseModel):
    total_rows: int
    successful_uploads: int
    failed_uploads: int
    errors: List[BulkUploadError] = []

    @property
    def success_rate(self) -> float:
        if self.total_rows == 0:
            return 0.0
        return (self.successful_uploads / self.total_rows) * 100


class ClientBulkUploadResult(BulkUploadResult):
    created_clients: List[Dict[str, Any]] = []


class ProductBulkUploadResult(BulkUploadResult):
    created_products: List[Dict[str, Any]] = []
