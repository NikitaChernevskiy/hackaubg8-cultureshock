"""CultureShock API — Emergency advisory service for travelers.

LEGAL: This service provides ADVISORY information only. All AI-generated
content includes mandatory disclaimers. See /api/v1/legal/disclaimer for
the full advisory notice.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from app.config import get_settings
from app.constants import ADVISORY_DISCLAIMER, DATA_FRESHNESS_WARNING, MEDICAL_DISCLAIMER
from app.middleware.compression import GZIP_MINIMUM_SIZE
from app.routers import alerts, emergency, guidance, health, notifications, transport

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup and shutdown logic."""
    settings = get_settings()
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info(
        "Starting %s v%s (debug=%s)",
        settings.app_name,
        settings.app_version,
        settings.debug,
    )
    logger.info(
        "Providers: alerts=%s, transport=%s, ai=%s, notifications=%s",
        settings.alert_provider,
        settings.transport_provider,
        settings.ai_provider,
        settings.notification_provider,
    )
    yield
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Emergency advisory API for travelers. Provides real-time alerts, "
            "transport status, and AI-generated advisory guidance for emergency "
            "situations.\n\n"
            "**IMPORTANT LEGAL NOTICE**: All advisory content provided by this "
            "API is for INFORMATIONAL purposes only and does not constitute "
            "professional emergency management, medical, or legal advice. "
            "Always follow instructions from local authorities and official "
            "emergency services."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # --- Middleware ---
    application.add_middleware(GZipMiddleware, minimum_size=GZIP_MINIMUM_SIZE)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Routers ---
    prefix = settings.api_v1_prefix
    application.include_router(health.router, prefix=prefix)
    application.include_router(emergency.router, prefix=prefix)
    application.include_router(alerts.router, prefix=prefix)
    application.include_router(transport.router, prefix=prefix)
    application.include_router(guidance.router, prefix=prefix)
    application.include_router(notifications.router, prefix=prefix)

    # --- Legal disclaimer endpoint (static) ---
    @application.get(
        f"{prefix}/legal/disclaimer",
        tags=["Legal"],
        summary="Full legal disclaimer",
        description="Returns all legal disclaimers for this service.",
    )
    async def get_legal_disclaimer():
        return {
            "advisory_disclaimer": ADVISORY_DISCLAIMER,
            "medical_disclaimer": MEDICAL_DISCLAIMER,
            "data_freshness_warning": DATA_FRESHNESS_WARNING,
        }

    return application


app = create_app()
