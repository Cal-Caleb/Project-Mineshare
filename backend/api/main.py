"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

import models  # noqa: F401 — register all models with Base
from api.routes import audit, auth, mods, server, sse, uploads, users, votes
from core.config import get_settings
from core.database import Base, engine
from core.events import get_event_bus
from core.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _apply_lightweight_migrations() -> None:
    """Idempotent ALTERs for columns added to existing tables."""
    alters = [
        "ALTER TABLE mod_uploads ADD COLUMN IF NOT EXISTS discord_message_id VARCHAR(20)",
        "ALTER TABLE mod_uploads ADD COLUMN IF NOT EXISTS discord_channel_id VARCHAR(20)",
        "ALTER TABLE votes ADD COLUMN IF NOT EXISTS discord_message_id VARCHAR(20)",
        "ALTER TABLE votes ADD COLUMN IF NOT EXISTS discord_channel_id VARCHAR(20)",
        # Add GUEST to userrole enum if it isn't there yet
        "ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'GUEST'",
        # Mod catalogue channel tracking
        "ALTER TABLE mods ADD COLUMN IF NOT EXISTS discord_message_id VARCHAR(20)",
        "ALTER TABLE mods ADD COLUMN IF NOT EXISTS discord_channel_id VARCHAR(20)",
        # Server heartbeats table (created by Base.metadata.create_all but just in case)
        # mod_update_logs table (created by Base.metadata.create_all)
    ]
    with engine.begin() as conn:
        for stmt in alters:
            try:
                conn.execute(text(stmt))
            except Exception:
                logger.exception("Migration failed: %s", stmt)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting MineShare API...")
    Base.metadata.create_all(bind=engine)
    _apply_lightweight_migrations()
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
