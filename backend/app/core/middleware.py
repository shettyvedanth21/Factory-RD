import uuid
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add a unique request ID to each request.
    - Generates a UUID for each request
    - Adds it to response headers as X-Request-ID
    - Binds it to structlog context for all logs in that request
    """
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Bind to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all API requests with structured logging.
    Logs: method, path, status_code, duration_ms, factory_id, user_id
    """
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        start_time = time.time()
        
        # Extract factory_id and user_id from request state if available
        factory_id = None
        user_id = None
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Extract user info from request state if set by auth dependency
        if hasattr(request.state, "user"):
            user = request.state.user
            user_id = user.id
            factory_id = getattr(user, "_token_factory_id", None)
        
        # Log request
        log_data = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
        }
        
        if factory_id:
            log_data["factory_id"] = factory_id
        if user_id:
            log_data["user_id"] = user_id
        
        logger.info("api.request", **log_data)
        
        return response
