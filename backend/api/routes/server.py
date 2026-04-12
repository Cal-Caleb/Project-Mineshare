import asyncio
import io
import json
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.deps import (
    get_current_user,
    get_server_manager,
    require_admin,
)
from api.schemas import (
    ModExportEntry,
    ModExportOut,
    ModUpdateOut,
    ServerEventOut,
    ServerStatus,
    UptimeBucket,
    UptimeStats,
)
from core.config import get_settings
from core.database import get_db
from core.events import CHANNEL_SERVER_UPDATE, get_event_bus
from core.scheduler import run_update_cycle
from core.server_manager import ServerManager
from models import Mod, ModStatus, ModUpdateLog, ServerEvent, ServerHeartbeat, User


router = APIRouter(prefix="/server", tags=["server"])


@router.get("/status", response_model=ServerStatus)
async def get_server_status(
    _user: User = Depends(get_current_user),
    mgr: ServerManager = Depends(get_server_manager),
):
    return mgr.get_status()


@router.get("/uptime", response_model=UptimeStats)
async def get_uptime_stats(
    days: int = 30,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Return uptime history with 10-minute resolution."""
    days = min(days, 90)
    hours = days * 24
    # Use naive UTC datetimes to match what PostgreSQL DateTime stores
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now - timedelta(hours=hours)

    rows = (
        db.query(ServerHeartbeat)
        .filter(ServerHeartbeat.bucket >= cutoff)
        .order_by(ServerHeartbeat.bucket.asc())
        .all()
    )
    # Strip tzinfo from DB values in case some have it
    lookup = {}
    for r in rows:
        key = r.bucket.replace(tzinfo=None) if r.bucket.tzinfo else r.bucket
        lookup[key] = r

    buckets = []
    b = cutoff.replace(minute=cutoff.minute // 10 * 10, second=0, microsecond=0)
    while b <= now:
        row = lookup.get(b)
        buckets.append(UptimeBucket(
            bucket=b,
            online=row.online if row else None,
            player_count=row.player_count if row else 0,
        ))
        b += timedelta(minutes=10)

    known = [bk for bk in buckets if bk.online is not None]
    if known:
        up = sum(1 for bk in known if bk.online)
        uptime_pct = round(100 * up / len(known), 2)
    else:
        uptime_pct = 0.0

    player_counts = [bk.player_count for bk in buckets]
    peak = max(player_counts) if player_counts else 0
    online_players = [bk.player_count for bk in buckets if bk.online]
    avg = sum(online_players) / len(online_players) if online_players else 0.0

    settings = get_settings()
    world_size_mb = None
    try:
        world_path = Path(settings.server_path) / "world"
        if world_path.exists():
            total = sum(f.stat().st_size for f in world_path.rglob("*") if f.is_file())
            world_size_mb = round(total / (1024 * 1024), 1)
    except Exception:
        pass

    return UptimeStats(
        uptime_pct=uptime_pct,
        buckets=buckets,
        peak_players=peak,
        avg_players=round(avg, 1),
        world_size_mb=world_size_mb,
    )


@router.get("/updates", response_model=list[ModUpdateOut])
async def get_mod_updates(
    limit: int = 50,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Return recent mod update logs with changelogs."""
    logs = (
        db.query(ModUpdateLog)
        .order_by(ModUpdateLog.created_at.desc())
        .limit(min(limit, 200))
        .all()
    )
    result = []
    for log in logs:
        mod = log.mod
        result.append(ModUpdateOut(
            id=log.id,
            mod_id=log.mod_id,
            mod_name=mod.name if mod else "Unknown",
            mod_slug=mod.slug if mod else None,
            old_version=log.old_version,
            new_version=log.new_version,
            changelog=log.changelog,
            source_url=mod.source_url if mod else None,
            created_at=log.created_at,
        ))
    return result


@router.get("/modpack", response_model=ModExportOut)
async def get_modpack_manifest(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Return a JSON manifest of all active mods."""
    active = (
        db.query(Mod)
        .filter(Mod.status == ModStatus.ACTIVE)
        .order_by(Mod.name.asc())
        .all()
    )
    return ModExportOut(
        mod_count=len(active),
        mods=[
            ModExportEntry(
                name=m.name,
                author=m.author,
                source=m.source.value if m.source else "unknown",
                curse_project_id=m.curse_project_id,
                file_name=m.file_name,
                source_url=m.source_url,
                current_version=m.current_version,
            )
            for m in active
        ],
    )


@router.get("/modpack/download")
async def download_modpack(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Download a ZIP containing the mod list as JSON + TXT."""
    active = (
        db.query(Mod)
        .filter(Mod.status == ModStatus.ACTIVE)
        .order_by(Mod.name.asc())
        .all()
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Text list
        lines = [f"MineShare Mod List ({len(active)} mods)", "=" * 50, ""]
        for m in active:
            line = f"• {m.name}"
            if m.author:
                line += f" (by {m.author})"
            if m.current_version:
                line += f" — {m.current_version}"
            if m.source_url:
                line += f"\n  {m.source_url}"
            lines.append(line)
        zf.writestr("modlist.txt", "\n".join(lines))

        # JSON manifest
        manifest = {
            "name": "MineShare Modpack",
            "mod_count": len(active),
            "mods": [
                {
                    "name": m.name,
                    "author": m.author,
                    "source": m.source.value if m.source else "unknown",
                    "curse_project_id": m.curse_project_id,
                    "file_name": m.file_name,
                    "source_url": m.source_url,
                    "current_version": m.current_version,
                }
                for m in active
            ],
        }
        zf.writestr("modlist.json", json.dumps(manifest, indent=2))

        # CurseForge HTML page with links
        html_lines = [
            "<html><head><title>MineShare Mod List</title></head><body>",
            f"<h1>MineShare Mod List ({len(active)} mods)</h1><ul>",
        ]
        for m in active:
            if m.source_url:
                html_lines.append(f'<li><a href="{m.source_url}">{m.name}</a> by {m.author or "Unknown"}</li>')
            else:
                html_lines.append(f"<li>{m.name} by {m.author or 'Unknown'}</li>")
        html_lines.append("</ul></body></html>")
        zf.writestr("modlist.html", "\n".join(html_lines))

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=mineshare_modpack.zip"},
    )


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
