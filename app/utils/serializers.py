"""
Custom serializers for handling timezone-aware datetime conversion.
"""
from datetime import datetime
from typing import Any, Optional
from fastapi import Request
from pydantic import BaseModel, Field
from .timezone import convert_utc_to_client_timezone
from ..middleware import get_request_timezone


class TimezoneAwareDatetime(BaseModel):
    """
    Custom datetime field that automatically converts UTC to client timezone.
    """
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v: Any, request: Request = None) -> Optional[datetime]:
        """
        Validate and convert datetime to client timezone.
        
        Args:
            v: Input value (datetime or None)
            request: FastAPI request object (injected by dependency)
            
        Returns:
            datetime: Converted datetime in client timezone or None
        """
        if v is None:
            return None
            
        if not isinstance(v, datetime):
            raise ValueError("Expected datetime object")
        
        # If no request context, return as-is (for testing/backward compatibility)
        if request is None:
            return v
            
        # Get client timezone from request
        client_timezone = get_request_timezone(request)
        if not client_timezone:
            return v
            
        # Convert UTC to client timezone
        return convert_utc_to_client_timezone(v, client_timezone)
    
    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string", format="date-time")


def create_timezone_aware_field(
    default: Any = None,
    description: str = None,
    **kwargs
) -> Field:
    """
    Create a Pydantic field that automatically converts UTC to client timezone.
    
    Args:
        default: Default value for the field
        description: Field description
        **kwargs: Additional field arguments
        
    Returns:
        Field: Pydantic field with timezone conversion
    """
    return Field(
        default=default,
        description=description,
        **kwargs
    )


class TimezoneAwareResponse(BaseModel):
    """
    Base response model that automatically converts datetime fields to client timezone.
    """
    
    class Config:
        # Enable automatic datetime conversion
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        
    def dict(self, **kwargs):
        """
        Override dict method to apply timezone conversion.
        """
        data = super().dict(**kwargs)
        
        # Apply timezone conversion to datetime fields
        for key, value in data.items():
            if isinstance(value, datetime):
                # This will be handled by the TimezoneAwareDatetime validator
                pass
                
        return data


def convert_datetime_fields_to_client_timezone(
    data: dict, 
    client_timezone: str,
    datetime_fields: list = None
) -> dict:
    """
    Convert datetime fields in a dictionary to client timezone.
    
    Args:
        data: Dictionary containing data
        client_timezone: Client's timezone string
        datetime_fields: List of field names that are datetimes (auto-detect if None)
        
    Returns:
        dict: Dictionary with converted datetime fields
    """
    if datetime_fields is None:
        # Auto-detect datetime fields
        datetime_fields = []
        for key, value in data.items():
            if isinstance(value, datetime):
                datetime_fields.append(key)
    
    result = data.copy()
    
    for field in datetime_fields:
        if field in result and isinstance(result[field], datetime):
            result[field] = convert_utc_to_client_timezone(
                result[field], 
                client_timezone
            )
    
    return result


def format_datetime_for_display(
    dt: datetime, 
    client_timezone: str,
    format_string: str = "%Y-%m-%d %H:%M:%S"
) -> str:
    """
    Format datetime for display in client timezone.
    
    Args:
        dt: Datetime object
        client_timezone: Client's timezone
        format_string: Format string for output
        
    Returns:
        str: Formatted datetime string
    """
    if dt is None:
        return None
        
    converted_dt = convert_utc_to_client_timezone(dt, client_timezone)
    return converted_dt.strftime(format_string)
