from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.deps import (
    get_upload_manager,
    require_admin,
    require_mc_username,
)
from api.schemas import ApproveUpload, RejectUpload, UploadOut
from core.database import get_db
from core.events import CHANNEL_UPLOAD_PENDING, get_event_bus
from core.upload_manager import UploadManager
from models import ModUpload, User

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=UploadOut)
async def upload_mod_jar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_mc_username),
    mgr: UploadManager = Depends(get_upload_manager),
):
    """Upload a custom .jar mod file."""
    content = await file.read()

    try:
        upload = await mgr.handle_upload(db, content, file.filename or "mod.jar", user)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    bus = get_event_bus()
    await bus.publish(
        CHANNEL_UPLOAD_PENDING,
        {
            "upload_id": upload.id,
            "filename": upload.original_filename,
            "user": user.discord_username,
            "status": upload.status.value,
        },
    )

    return _upload_to_out(upload)


@router.post("/update/{mod_id}", response_model=UploadOut)
async def upload_mod_update(
    mod_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_mc_username),
    mgr: UploadManager = Depends(get_upload_manager),
):
    """Upload an update for an existing uploaded mod. Requires admin approval (no vote)."""
    content = await file.read()

    try:
        upload = await mgr.handle_upload(db, content, file.filename or "mod.jar", user, mod_id=mod_id)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e

    bus = get_event_bus()
    await bus.publish(
        CHANNEL_UPLOAD_PENDING,
        {
            "upload_id": upload.id,
            "filename": upload.original_filename,
            "user": user.discord_username,
            "status": upload.status.value,
            "is_update": True,
            "mod_id": mod_id,
        },
    )

    return _upload_to_out(upload)


@router.get("", response_model=list[UploadOut])
async def list_pending_uploads(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    mgr: UploadManager = Depends(get_upload_manager),
):
    uploads = mgr.get_pending_uploads(db)
    return [_upload_to_out(u) for u in uploads]


@router.post("/{upload_id}/approve", response_model=UploadOut)
async def approve_upload(
    upload_id: int,
    body: ApproveUpload,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    mgr: UploadManager = Depends(get_upload_manager),
):
    upload = db.query(ModUpload).filter(ModUpload.id == upload_id).first()
    if not upload:
        raise HTTPException(404, "Upload not found")

    try:
        if upload.mod_id is not None:
            # Update to existing mod — no vote needed
            mgr.approve_mod_update(db, upload, admin)
        else:
            if not body.mod_name:
                raise HTTPException(400, "mod_name is required for new mod uploads")
            mgr.approve_upload(db, upload, admin, body.mod_name)
    except (ValueError, PermissionError) as e:
        raise HTTPException(400, str(e)) from e

    return _upload_to_out(upload)


@router.post("/{upload_id}/reject", response_model=UploadOut)
async def reject_upload(
    upload_id: int,
    body: RejectUpload,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    mgr: UploadManager = Depends(get_upload_manager),
):
    upload = db.query(ModUpload).filter(ModUpload.id == upload_id).first()
    if not upload:
        raise HTTPException(404, "Upload not found")

    try:
        mgr.reject_upload(db, upload, admin, body.reason)
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e

    return _upload_to_out(upload)


@router.get("/{upload_id}/download")
async def download_upload(
    upload_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    mgr: UploadManager = Depends(get_upload_manager),
):
    """Admin-only: download the uploaded file for manual review."""
    upload = db.query(ModUpload).filter(ModUpload.id == upload_id).first()
    if not upload:
        raise HTTPException(404, "Upload not found")

    file_path = mgr.get_upload_file_path(upload)
    if not file_path:
        raise HTTPException(404, "File no longer available")

    return FileResponse(
        path=str(file_path),
        filename=upload.original_filename,
        media_type="application/java-archive",
    )


def _upload_to_out(upload: ModUpload) -> UploadOut:
    return UploadOut(
        id=upload.id,
        original_filename=upload.original_filename,
        file_hash=upload.file_hash,
        file_size=upload.file_size,
        status=upload.status.value,
        scan_result=upload.scan_result,
        mod_id=upload.mod_id,
        created_at=upload.created_at,
        resolved_at=upload.resolved_at,
    )
