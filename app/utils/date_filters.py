"""
Utilities for handling date filters with timezone conversion.
"""
from datetime import datetime, date, timedelta
from typing import Optional, Tuple
from ..utils.timezone import convert_client_timezone_to_utc


def convert_date_filter_to_utc(
    date_filter: Optional[date],
    client_timezone: str,
    is_start_date: bool = True
) -> Optional[datetime]:
    """
    Convert a date filter from client timezone to UTC for database queries.

    Args:
        date_filter: Date filter from client (date object)
        client_timezone: Client's timezone string
        is_start_date: If True, use start of day (00:00:00), if False, use end of day (23:59:59)

    Returns:
        datetime: UTC datetime for database query
    """
    if date_filter is None:
        return None

    # Convert date to datetime in client timezone
    if is_start_date:
        # Start of day: 00:00:00
        client_datetime = datetime.combine(date_filter, datetime.min.time())
    else:
        # End of day: 23:59:59
        client_datetime = datetime.combine(date_filter, datetime.max.time().replace(microsecond=0))

    # Convert to UTC
    return convert_client_timezone_to_utc(client_datetime, client_timezone)


def convert_datetime_filter_to_utc(
    datetime_filter: Optional[datetime],
    client_timezone: str
) -> Optional[datetime]:
    """
    Convert a datetime filter from client timezone to UTC for database queries.

    Args:
        datetime_filter: Datetime filter from client
        client_timezone: Client's timezone string

    Returns:
        datetime: UTC datetime for database query
    """
    if datetime_filter is None:
        return None

    # If datetime is naive, assume it's in client timezone
    if datetime_filter.tzinfo is None:
        return convert_client_timezone_to_utc(datetime_filter, client_timezone)

    # If datetime is already timezone-aware, convert to UTC
    return datetime_filter.astimezone().replace(tzinfo=None)


def create_date_range_utc(
    start_date: Optional[date],
    end_date: Optional[date],
    client_timezone: str
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Create UTC datetime range from client date filters.

    Args:
        start_date: Start date from client
        end_date: End date from client
        client_timezone: Client's timezone string

    Returns:
        tuple: (start_datetime_utc, end_datetime_utc)
    """
    start_utc = convert_date_filter_to_utc(start_date, client_timezone, is_start_date=True)
    end_utc = convert_date_filter_to_utc(end_date, client_timezone, is_start_date=False)

    return start_utc, end_utc


def create_datetime_range_utc(
    start_datetime: Optional[datetime],
    end_datetime: Optional[datetime],
    client_timezone: str
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Create UTC datetime range from client datetime filters.

    Args:
        start_datetime: Start datetime from client
        end_datetime: End datetime from client
        client_timezone: Client's timezone string

    Returns:
        tuple: (start_datetime_utc, end_datetime_utc)
    """
    start_utc = convert_datetime_filter_to_utc(start_datetime, client_timezone)
    end_utc = convert_datetime_filter_to_utc(end_datetime, client_timezone)

    return start_utc, end_utc


def validate_date_range(
    start_date: Optional[date],
    end_date: Optional[date]
) -> None:
    """
    Validate that start_date is not later than end_date.

    Args:
        start_date: Start date
        end_date: End date

    Raises:
        ValueError: If date range is invalid
    """
    if start_date and end_date and start_date > end_date:
        raise ValueError("start_date cannot be later than end_date")


def validate_datetime_range(
    start_datetime: Optional[datetime],
    end_datetime: Optional[datetime]
) -> None:
    """
    Validate that start_datetime is not later than end_datetime.

    Args:
        start_datetime: Start datetime
        end_datetime: End datetime

    Raises:
        ValueError: If datetime range is invalid
    """
    if start_datetime and end_datetime and start_datetime > end_datetime:
        raise ValueError("start_datetime cannot be later than end_datetime")
