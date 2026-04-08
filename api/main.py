"""FastAPI application factory."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from longevity.common.config import get_settings
from longevity.common.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: load models on startup, cleanup on shutdown."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("startup", environment=settings.environment)

    # Lazy model loading — models loaded on first request to avoid startup delay
    # In production, preload here:
    # app.state.bioage_model = BloodAgeClock.load("models/bioage/blood_clock.joblib")
    # app.state.mortality_model = ...

    yield

    logger.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Longevity Intelligence Platform",
        description="Biological age, mortality risk, and digital twin health simulation API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    settings = get_settings()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # Register routers
    from api.routers import bioage, coach, food, health, mortality, twin

    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(bioage.router, prefix="/api/v1/bioage", tags=["bioage"])
    app.include_router(mortality.router, prefix="/api/v1/mortality", tags=["mortality"])
    app.include_router(twin.router, prefix="/api/v1/twin", tags=["twin"])
    app.include_router(coach.router, prefix="/api/v1/coach", tags=["coach"])
    app.include_router(food.router, prefix="/api/v1/food", tags=["food"])

    return app


app = create_app()
