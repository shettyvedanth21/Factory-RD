from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestIDMiddleware
from app.core.database import check_db_health
from app.core.redis_client import check_redis_health, close_redis
from app.core.influx import check_influx_health, close_influx
from app.api.v1 import auth


# Configure logging first
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    Runs on startup and shutdown.
    """
    # Startup
    logger.info("api_starting", env=settings.app_env)
    
    # Verify dependencies
    db_ok = await check_db_health()
    redis_ok = await check_redis_health()
    influx_ok = await check_influx_health()
    
    if not db_ok:
        logger.error("startup_failed", reason="Database connection failed")
    if not redis_ok:
        logger.warning("startup_warning", reason="Redis connection failed")
    if not influx_ok:
        logger.warning("startup_warning", reason="InfluxDB connection failed")
    
    # Check MinIO bucket (optional for now, will implement in Phase 4)
    # TODO: Ensure MinIO bucket exists
    
    logger.info(
        "api_started",
        database=db_ok,
        redis=redis_ok,
        influxdb=influx_ok,
        app_env=settings.app_env,
        jwt_expiry_hours=settings.jwt_expiry_hours
    )
    
    yield
    
    # Shutdown
    logger.info("api_shutting_down")
    await close_redis()
    await close_influx()
    logger.info("api_shutdown_complete")


# Create FastAPI app
app = FastAPI(
    title="FactoryOps API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)


# Add middleware (order matters!)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.app_env == "development" else [settings.app_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
from app.api.v1 import devices, telemetry, dashboard

app.include_router(auth.router, prefix="/api/v1")
app.include_router(devices.router, prefix="/api/v1")
app.include_router(telemetry.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    Checks all critical dependencies.
    
    Returns:
        Health status with dependency checks
    """
    db_healthy = await check_db_health()
    redis_healthy = await check_redis_health()
    influx_healthy = await check_influx_health()
    
    overall_status = "healthy" if db_healthy else "unhealthy"
    
    return {
        "status": overall_status,
        "dependencies": {
            "mysql": "ok" if db_healthy else "error",
            "redis": "ok" if redis_healthy else "error",
            "influxdb": "ok" if influx_healthy else "error"
        }
    }


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle request validation errors (422).
    Returns errors in API spec format.
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        "validation_error",
        path=request.url.path,
        errors=errors
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": errors
            }
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Handle all unhandled exceptions.
    Logs full traceback and returns 500 error.
    """
    # Get request ID from context
    request_id = structlog.contextvars.get_contextvars().get("request_id", "unknown")
    
    logger.error(
        "unhandled_exception",
        exc_info=exc,
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "request_id": request_id
            }
        }
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "FactoryOps API",
        "version": "1.0.0",
        "status": "running"
    }
