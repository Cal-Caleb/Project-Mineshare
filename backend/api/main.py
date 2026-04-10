"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import audit, auth, mods, server, sse, uploads, users, votes
from core.config import get_settings
from core.database import Base, engine
from core.events import get_event_bus
from core.scheduler import start_scheduler, stop_scheduler
import models  # noqa: F401 — register all models with Base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting MineShare API...")
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    yield
    logger.info("Shutting down MineShare API...")
    stop_scheduler()
    bus = get_event_bus()
    await bus.close()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="MineShare API",
        description="Collaborative Modded Minecraft Server Management",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix="/api")
    app.include_router(users.router, prefix="/api")
    app.include_router(mods.router, prefix="/api")
    app.include_router(votes.router, prefix="/api")
    app.include_router(uploads.router, prefix="/api")
    app.include_router(server.router, prefix="/api")
    app.include_router(audit.router, prefix="/api")
    app.include_router(sse.router, prefix="/api")

    @app.get("/api/health")
    async def health():
        return {"status": "healthy"}

    return app


app = create_app()
