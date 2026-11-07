import os
from pathlib import Path

PROMETHEUS_DIR = (
    Path(__file__).resolve().parents[1]
    / "storage"
    / "prometheus"
)

PROMETHEUS_DIR.mkdir(parents=True, exist_ok=True)

os.environ["PROMETHEUS_MULTIPROC_DIR"] = str(PROMETHEUS_DIR)

from database.connection import initialize_database
from contextlib import asynccontextmanager
from observability.tracing import configure_tracing, shutdown_tracing
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from config import get_settings
from config.logging_config import configure_logging, get_logger

from api.routes import (
    petitions,
    runs,
    feedback,
    health,
)

from observability.metrics import get_metrics


settings = get_settings()

configure_logging(settings.log_level)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""

    initialize_database()

    logger.info(
        "application_starting",
        app_name=settings.app_name,
        environment=settings.app_env,
    )

    configure_tracing()

    try:
        yield
    finally:
        shutdown_tracing()
        logger.info("application_shutdown")


app = FastAPI(
    title=settings.app_name,
    description=(
        "Academic Regulation and Student Petition Triage Service. "
        "Provides evidence-backed eligibility positions for "
        "human examination officer review."
    ),
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan,
)

# --------------------------------------------------
# CORS Configuration
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# --------------------------------------------------
# Register API routers
# --------------------------------------------------

app.include_router(
    health.router,
)

app.include_router(
    petitions.router,
    prefix=settings.api_v1_prefix,
)

app.include_router(
    runs.router,
    prefix=settings.api_v1_prefix,
)

app.include_router(
    feedback.router,
    prefix=settings.api_v1_prefix,
)


# --------------------------------------------------
# Prometheus Metrics Endpoint
# --------------------------------------------------

@app.get(
    "/metrics",
    tags=["Monitoring"],
    include_in_schema=False,
)
def prometheus_metrics():
    """
    Expose application metrics in Prometheus format.
    """

    metrics_data, content_type = get_metrics()

    return Response(
        content=metrics_data,
        media_type=content_type,
    )


# --------------------------------------------------
# Root Endpoint
# --------------------------------------------------

@app.get(
    "/",
    tags=["Root"],
)
def root():
    return {
        "service": settings.app_name,
        "status": "running",
        "documentation": "/docs",
        "metrics": "/metrics",
    }
