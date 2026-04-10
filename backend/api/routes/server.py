import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps import (
    get_current_user,
    get_server_manager,
    require_admin,
)
from api.schemas import ServerEventOut, ServerStatus
from core.database import get_db
from core.events import CHANNEL_SERVER_UPDATE, get_event_bus
from core.scheduler import run_update_cycle
from core.server_manager import ServerManager
from models import ServerEvent, User

router = APIRouter(prefix="/server", tags=["server"])


@router.get("/status", response_model=ServerStatus)
async def get_server_status(
    _user: User = Depends(get_current_user),
    mgr: ServerManager = Depends(get_server_manager),
):
    return mgr.get_status()


@router.post("/update")
async def trigger_manual_update(
    _admin: User = Depends(require_admin),
):
    """Trigger a manual update cycle (admin only)."""
    asyncio.create_task(run_update_cycle())
    return {"status": "started", "message": "Update cycle queued"}


@router.post("/restart")
async def restart_server(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    mgr: ServerManager = Depends(get_server_manager),
):
    success = mgr.restart_server(db, triggered_by_id=admin.id)
    if not success:
        raise HTTPException(500, "Failed to restart server")
    return {"status": "success"}


@router.post("/backup")
async def create_backup(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    mgr: ServerManager = Depends(get_server_manager),
):
    backup_file = mgr.backup_world(db, triggered_by_id=admin.id)
    if not backup_file:
        raise HTTPException(500, "Backup failed")
    return {"status": "success", "backup_file": backup_file}


@router.get("/events", response_model=list[ServerEventOut])
async def get_server_events(
    limit: int = 20,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    events = (
        db.query(ServerEvent)
        .order_by(ServerEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return events
