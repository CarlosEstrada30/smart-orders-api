"""
Timezone middleware for FastAPI to handle client timezone conversion.
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import logging

from ..utils.timezone import get_client_timezone

logger = logging.getLogger(__name__)


class TimezoneMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and store client timezone information.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request to extract timezone information.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain
            
        Returns:
            Response: HTTP response
        """
        # Extract client timezone
        client_timezone = get_client_timezone(request)
        
        # Store timezone in request state for use in endpoints
        request.state.client_timezone = client_timezone
        
        # Log timezone for debugging (optional)
        logger.debug(f"Client timezone: {client_timezone}")
        
        # Continue with request processing
        response = await call_next(request)
        
        return response


def get_request_timezone(request: Request) -> str:
    """
    Get the client timezone from request state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: Client timezone string
    """
    return getattr(request.state, 'client_timezone', None)
