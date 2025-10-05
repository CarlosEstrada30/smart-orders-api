"""
Timezone utilities for handling client timezone conversion.
"""
from datetime import datetime, timezone
from typing import Optional, Union
import pytz
from fastapi import Request
from ..config import settings


def get_client_timezone(request: Request) -> str:
    """
    Get the client's timezone from request headers or use default.
    
    Priority:
    1. X-Timezone header
    2. Default timezone (Guatemala)
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: Timezone string (e.g., "America/Guatemala")
    """
    # Check for X-Timezone header
    timezone_header = request.headers.get(settings.TIMEZONE_HEADER)
    if timezone_header and is_valid_timezone(timezone_header):
        return timezone_header
    
    # Fallback to default timezone
    return settings.DEFAULT_TIMEZONE


def is_valid_timezone(timezone_str: str) -> bool:
    """
    Check if a timezone string is valid.
    
    Args:
        timezone_str: Timezone string to validate
        
    Returns:
        bool: True if valid timezone, False otherwise
    """
    try:
        pytz.timezone(timezone_str)
        return True
    except pytz.exceptions.UnknownTimeZoneError:
        return False


def convert_utc_to_client_timezone(
    utc_datetime: datetime, 
    client_timezone: str
) -> datetime:
    """
    Convert UTC datetime to client's timezone.
    
    Args:
        utc_datetime: UTC datetime object
        client_timezone: Client's timezone string
        
    Returns:
        datetime: Datetime in client's timezone
    """
    if utc_datetime is None:
        return None
        
    # Ensure the datetime is timezone-aware (UTC)
    if utc_datetime.tzinfo is None:
        utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)
    elif utc_datetime.tzinfo != timezone.utc:
        utc_datetime = utc_datetime.astimezone(timezone.utc)
    
    # Convert to client timezone
    client_tz = pytz.timezone(client_timezone)
    return utc_datetime.astimezone(client_tz)


def convert_client_timezone_to_utc(
    client_datetime: datetime, 
    client_timezone: str
) -> datetime:
    """
    Convert client's timezone datetime to UTC.
    
    Args:
        client_datetime: Datetime in client's timezone
        client_timezone: Client's timezone string
        
    Returns:
        datetime: UTC datetime object
    """
    if client_datetime is None:
        return None
        
    # If datetime is naive, assume it's in client timezone
    if client_datetime.tzinfo is None:
        client_tz = pytz.timezone(client_timezone)
        client_datetime = client_tz.localize(client_datetime)
    
    # Convert to UTC
    return client_datetime.astimezone(timezone.utc)


def format_datetime_for_client(
    utc_datetime: datetime, 
    client_timezone: str,
    format_string: str = "%Y-%m-%d %H:%M:%S"
) -> str:
    """
    Format UTC datetime to client's timezone as string.
    
    Args:
        utc_datetime: UTC datetime object
        client_timezone: Client's timezone string
        format_string: Format string for output
        
    Returns:
        str: Formatted datetime string in client's timezone
    """
    if utc_datetime is None:
        return None
        
    converted_datetime = convert_utc_to_client_timezone(utc_datetime, client_timezone)
    return converted_datetime.strftime(format_string)


def get_timezone_offset(client_timezone: str) -> str:
    """
    Get the timezone offset string for the client's timezone.
    
    Args:
        client_timezone: Client's timezone string
        
    Returns:
        str: Timezone offset (e.g., "-06:00")
    """
    try:
        tz = pytz.timezone(client_timezone)
        now = datetime.now(tz)
        offset = now.strftime('%z')
        return f"{offset[:3]}:{offset[3:]}"
    except:
        return "-06:00"  # Default to Guatemala offset


def create_timezone_aware_datetime(
    year: int, 
    month: int, 
    day: int, 
    hour: int = 0, 
    minute: int = 0, 
    second: int = 0,
    client_timezone: str = None
) -> datetime:
    """
    Create a timezone-aware datetime in the client's timezone.
    
    Args:
        year, month, day, hour, minute, second: Datetime components
        client_timezone: Client's timezone (uses default if None)
        
    Returns:
        datetime: Timezone-aware datetime object
    """
    if client_timezone is None:
        client_timezone = settings.DEFAULT_TIMEZONE
        
    tz = pytz.timezone(client_timezone)
    return tz.localize(datetime(year, month, day, hour, minute, second))


def get_current_time_in_timezone(client_timezone: str) -> datetime:
    """
    Get current time in the client's timezone.
    
    Args:
        client_timezone: Client's timezone string
        
    Returns:
        datetime: Current datetime in client's timezone
    """
    tz = pytz.timezone(client_timezone)
    return datetime.now(tz)
