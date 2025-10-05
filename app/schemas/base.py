"""
Base schemas with timezone-aware datetime handling.
"""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field
from ..utils.timezone import convert_utc_to_client_timezone


class TimezoneAwareBaseModel(BaseModel):
    """
    Base model that automatically converts UTC datetime fields to client timezone.
    """
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    def dict(self, **kwargs) -> dict:
        """
        Override dict method to apply timezone conversion to datetime fields.
        """
        data = super().dict(**kwargs)
        
        # Get client timezone from context (if available)
        client_timezone = getattr(self, '_client_timezone', None)
        if not client_timezone:
            return data
        
        # Convert datetime fields to client timezone
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = convert_utc_to_client_timezone(value, client_timezone)
        
        return data
    
    def set_client_timezone(self, timezone: str):
        """
        Set the client timezone for datetime conversion.
        
        Args:
            timezone: Client timezone string
        """
        self._client_timezone = timezone


def create_timezone_aware_datetime_field(
    description: str = None,
    **kwargs
) -> Field:
    """
    Create a datetime field that will be converted to client timezone.
    
    Args:
        description: Field description
        **kwargs: Additional field arguments
        
    Returns:
        Field: Pydantic field for datetime
    """
    return Field(
        description=description,
        **kwargs
    )


class TimestampMixin(BaseModel):
    """
    Mixin for models that have created_at and updated_at timestamps.
    """
    created_at: datetime = create_timezone_aware_datetime_field(
        description="Fecha y hora de creación (en zona horaria del cliente)"
    )
    updated_at: Optional[datetime] = create_timezone_aware_datetime_field(
        default=None,
        description="Fecha y hora de última actualización (en zona horaria del cliente)"
    )


class DateRangeMixin(BaseModel):
    """
    Mixin for models that have date range fields.
    """
    date_from: Optional[datetime] = create_timezone_aware_datetime_field(
        default=None,
        description="Fecha de inicio (en zona horaria del cliente)"
    )
    date_to: Optional[datetime] = create_timezone_aware_datetime_field(
        default=None,
        description="Fecha de fin (en zona horaria del cliente)"
    )
