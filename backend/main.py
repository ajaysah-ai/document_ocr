"""FastAPI application entrypoint.

Start with:  uvicorn backend.main:app --reload
Interactive API docs: http://localhost:8000/docs
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import get_ocr_service, router
from backend.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the OCR engine exactly once at startup."""
    logger.info("Initializing PaddleOCR engine (one-time, CPU)...")
    service = get_ocr_service()
    service.initialize()
    if service.ready:
        logger.info("PaddleOCR engine is ready.")
    else:
        logger.error("PaddleOCR failed to initialize: %s", service.error)
    yield
    logger.info("Application shutdown.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Document OCR & Intelligence API",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "app": "Document OCR & Intelligence API",
            "docs": "/docs",
            "health": "/api/health",
        }

    return app


app = create_app()
