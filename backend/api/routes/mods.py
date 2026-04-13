from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps import (
    get_current_user,
    get_mod_manager,
    get_vote_manager,
    require_mc_username,
)
from api.schemas import (
    AddCurseForgeMod,
    CurseForgePreview,
    ModOut,
)
from core.database import get_db
from core.events import CHANNEL_MOD_ADDED, CHANNEL_MOD_REMOVED, get_event_bus
from core.mod_manager import ModManager
from core.vote_manager import VoteManager
from models import Mod, ModStatus, User, UserRole, VoteType

router = APIRouter(prefix="/mods", tags=["mods"])


@router.get("", response_model=list[ModOut])
async def list_mods(
    status: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    query = db.query(Mod)
    if status:
        query = query.filter(Mod.status == status)
    mods = query.order_by(Mod.name).all()
    return [_mod_to_out(m) for m in mods]


@router.get("/{mod_id}", response_model=ModOut)
async def get_mod(
    mod_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    mod = db.query(Mod).filter(Mod.id == mod_id).first()
    if not mod:
        raise HTTPException(404, "Mod not found")
    return _mod_to_out(mod)


@router.post("/curseforge/preview", response_model=CurseForgePreview)
async def preview_curseforge(
    body: AddCurseForgeMod,
    mgr: ModManager = Depends(get_mod_manager),
    _user: User = Depends(require_mc_username),
):
    """Preview a CurseForge mod before adding it."""
    info = await mgr.resolve_curseforge_url(body.url)
    if not info:
        raise HTTPException(400, "Could not resolve that CurseForge URL")
    return CurseForgePreview(
        project_id=info.project_id,
        name=info.name,
        slug=info.slug,
        summary=info.summary,
        author=info.author,
        logo_url=info.logo_url,
        latest_file_name=info.latest_file_name,
        download_count=info.download_count,
        supports_neoforge=info.supports_neoforge,
        game_versions=info.game_versions,
    )


@router.post("/curseforge", response_model=ModOut)
async def add_curseforge_mod(
    body: AddCurseForgeMod,
    db: Session = Depends(get_db),
    user: User = Depends(require_mc_username),
    mgr: ModManager = Depends(get_mod_manager),
    vote_mgr: VoteManager = Depends(get_vote_manager),
):
    """Add a mod from CurseForge.

    - Admin with force=True: instant add
    - Otherwise: creates a vote
    """
    info = await mgr.resolve_curseforge_url(body.url)
    if not info:
        raise HTTPException(400, "Could not resolve that CurseForge URL")

    try:
        mod = mgr.add_mod_from_curseforge(db, info, user, body.url, force=body.force)
    except ValueError as e:
        raise HTTPException(409, str(e)) from e

    # If not force-added, create a vote
    if mod.status == ModStatus.PENDING_VOTE:
        vote_mgr.create_vote(db, mod, VoteType.ADD, user)

    # Publish event
    bus = get_event_bus()
    await bus.publish(
        CHANNEL_MOD_ADDED,
        {"mod_id": mod.id, "name": mod.name, "status": mod.status.value},
    )

    return _mod_to_out(mod)


@router.delete("/{mod_id}", response_model=ModOut)
async def remove_mod(
    mod_id: int,
    force: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(require_mc_username),
    mgr: ModManager = Depends(get_mod_manager),
    vote_mgr: VoteManager = Depends(get_vote_manager),
):
    """Remove a mod.

    - Admin with force=True: instant remove
    - Original adder or admin without force: creates a removal vote
    """
    mod = db.query(Mod).filter(Mod.id == mod_id).first()
    if not mod:
        raise HTTPException(404, "Mod not found")

    if mod.status == ModStatus.REMOVED:
        raise HTTPException(409, "Mod is already removed")

    if force and user.role == UserRole.ADMIN:
        mgr.remove_mod(db, mod, user)
    else:
        if mod.added_by_id != user.id and user.role != UserRole.ADMIN:
            raise HTTPException(403, "Only the original adder or an admin can remove")
        try:
            vote_mgr.create_vote(db, mod, VoteType.REMOVE, user)
        except ValueError as e:
            raise HTTPException(409, str(e)) from e

    bus = get_event_bus()
    await bus.publish(
        CHANNEL_MOD_REMOVED,
        {"mod_id": mod.id, "name": mod.name, "status": mod.status.value},
    )

    db.refresh(mod)
    return _mod_to_out(mod)


def _mod_to_out(mod: Mod) -> ModOut:
    return ModOut(
        id=mod.id,
        name=mod.name,
        slug=mod.slug,
        description=mod.description,
        author=mod.author,
        source=mod.source.value,
        source_url=mod.source_url,
        curse_project_id=mod.curse_project_id,
        current_version=mod.current_version,
        file_name=mod.file_name,
        status=mod.status.value,
        download_count=mod.download_count,
        created_at=mod.created_at,
        updated_at=mod.updated_at,
    )
