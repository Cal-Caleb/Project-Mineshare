import asyncio
import hashlib
import logging
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from core.config import get_settings
from core.events import CHANNEL_UPLOAD_RESOLVED, get_event_bus
from models import (
    AuditLog,
    EventSource,
    Mod,
    ModSource,
    ModStatus,
    ModUpload,
    UploadStatus,
    User,
    UserRole,
    VoteType,
)

logger = logging.getLogger(__name__)
_background_tasks: set[asyncio.Task] = set()  # prevent GC of fire-and-forget tasks


def _publish(channel: str, data: dict) -> None:
    try:
        bus = get_event_bus()
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(bus.publish(channel, data))
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
        except RuntimeError:
            asyncio.run(bus.publish(channel, data))
    except Exception:
        logger.exception("Failed to publish %s", channel)


class UploadManager:
    def __init__(self):
        settings = get_settings()
        self.upload_dir = Path(settings.upload_dir)
        self.quarantine_dir = Path(settings.quarantine_dir)
        self.max_size = settings.max_upload_size

        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

    async def handle_upload(
        self,
        db: Session,
        file_bytes: bytes,
        original_filename: str,
        user: User,
        mod_id: int | None = None,
    ) -> ModUpload:
        """Accept an uploaded JAR and quarantine it.

        If mod_id is provided, this is treated as an update to an existing mod.
        The uploader must be the original adder of that mod (or an admin).
        """
        if len(file_bytes) > self.max_size:
            raise ValueError(f"File too large ({len(file_bytes)} bytes, max {self.max_size})")

        if not original_filename.lower().endswith(".jar"):
            raise ValueError("Only .jar files are accepted")

        # If this is an update, verify the user owns the mod
        if mod_id is not None:
            mod = db.query(Mod).filter(Mod.id == mod_id).first()
            if not mod:
                raise ValueError("Mod not found")
            if mod.source != ModSource.UPLOAD:
                raise ValueError("Only uploaded mods can be updated this way")
            if mod.added_by_id != user.id and user.role != UserRole.ADMIN:
                raise PermissionError("Only the original uploader can update this mod")

        file_hash = hashlib.sha256(file_bytes).hexdigest()

        # Store in quarantine with a unique name
        safe_name = f"{uuid.uuid4().hex}_{original_filename}"
        quarantine_path = self.quarantine_dir / safe_name
        quarantine_path.write_bytes(file_bytes)

        upload = ModUpload(
            filename=safe_name,
            original_filename=original_filename,
            file_hash=file_hash,
            file_size=len(file_bytes),
            quarantine_path=str(quarantine_path),
            status=UploadStatus.PENDING_APPROVAL,
            uploaded_by_id=user.id,
            mod_id=mod_id,
        )
        db.add(upload)
        db.add(
            AuditLog(
                user_id=user.id,
                action="file_uploaded" if mod_id is None else "mod_update_uploaded",
                details=(
                    f"Uploaded {original_filename} ({len(file_bytes)} bytes)"
                    + (f" as update for mod {mod_id}" if mod_id else "")
                ),
                source=EventSource.WEB,
            )
        )
        db.commit()
        db.refresh(upload)
        return upload

    def get_upload_file_path(self, upload: ModUpload) -> Path | None:
        """Return the quarantined file path if it exists, for admin download."""
        path = Path(upload.quarantine_path)
        return path if path.exists() else None

    def approve_upload(
        self,
        db: Session,
        upload: ModUpload,
        admin: User,
        mod_name: str,
    ) -> Mod:
        """Admin approves a clean upload, creating the Mod record."""
        if admin.role != UserRole.ADMIN:
            raise PermissionError("Only admins can approve uploads")
        if upload.status != UploadStatus.PENDING_APPROVAL:
            raise ValueError(f"Upload is not approvable (status={upload.status.value})")

        # Move from quarantine to uploads
        dest = self.upload_dir / upload.filename
        src = Path(upload.quarantine_path)
        if src.exists():
            shutil.move(str(src), str(dest))

        upload.status = UploadStatus.APPROVED
        upload.approved_by_id = admin.id
        upload.resolved_at = datetime.now(UTC)

        # Create the mod record
        mod = Mod(
            name=mod_name,
            source=ModSource.UPLOAD,
            file_path=str(dest),
            file_hash=upload.file_hash,
            file_name=upload.original_filename,
            status=ModStatus.PENDING_VOTE,
            added_by_id=upload.uploaded_by_id,
        )
        db.add(mod)
        db.flush()

        upload.mod_id = mod.id

        db.add(
            AuditLog(
                user_id=admin.id,
                action="upload_approved",
                details=f"Approved upload: {upload.original_filename} as '{mod_name}'",
                source=EventSource.WEB,
            )
        )
        db.commit()
        db.refresh(mod)

        _publish(
            CHANNEL_UPLOAD_RESOLVED,
            {
                "upload_id": upload.id,
                "filename": upload.original_filename,
                "status": "approved",
                "by": admin.discord_username,
                "is_update": False,
                "mod_id": mod.id,
                "discord_message_id": upload.discord_message_id,
                "discord_channel_id": upload.discord_channel_id,
            },
        )

        # Create a community vote for the uploaded mod
        from core.vote_manager import VoteManager

        vote_mgr = VoteManager()
        vote_mgr.create_vote(db, mod, VoteType.ADD, admin)

        return mod

    def approve_mod_update(
        self,
        db: Session,
        upload: ModUpload,
        admin: User,
    ) -> Mod:
        """Admin approves an update upload — replaces the mod file, no vote needed."""
        if admin.role != UserRole.ADMIN:
            raise PermissionError("Only admins can approve uploads")
        if upload.status != UploadStatus.PENDING_APPROVAL:
            raise ValueError(f"Upload is not approvable (status={upload.status.value})")
        if not upload.mod_id:
            raise ValueError("This upload is not linked to an existing mod")

        mod = db.query(Mod).filter(Mod.id == upload.mod_id).first()
        if not mod:
            raise ValueError("Linked mod not found")

        # Remove old file
        if mod.file_path:
            old_path = Path(mod.file_path)
            if old_path.exists():
                old_path.unlink()

        # Move new file from quarantine to uploads
        dest = self.upload_dir / upload.filename
        src = Path(upload.quarantine_path)
        if src.exists():
            shutil.move(str(src), str(dest))

        # Update mod record
        old_file_name = mod.file_name
        mod.file_path = str(dest)
        mod.file_hash = upload.file_hash
        mod.file_name = upload.original_filename

        upload.status = UploadStatus.APPROVED
        upload.approved_by_id = admin.id
        upload.resolved_at = datetime.now(UTC)

        db.add(
            AuditLog(
                user_id=admin.id,
                action="mod_update_approved",
                details=f"Approved update for '{mod.name}': {old_file_name} -> {upload.original_filename}",
                source=EventSource.WEB,
            )
        )
        db.commit()
        db.refresh(mod)

        _publish(
            CHANNEL_UPLOAD_RESOLVED,
            {
                "upload_id": upload.id,
                "filename": upload.original_filename,
                "status": "approved",
                "by": admin.discord_username,
                "is_update": True,
                "mod_id": mod.id,
                "mod_name": mod.name,
                "discord_message_id": upload.discord_message_id,
                "discord_channel_id": upload.discord_channel_id,
            },
        )
        return mod

    def reject_upload(self, db: Session, upload: ModUpload, admin: User, reason: str = "") -> None:
        if admin.role != UserRole.ADMIN:
            raise PermissionError("Only admins can reject uploads")

        upload.status = UploadStatus.REJECTED
        upload.approved_by_id = admin.id
        upload.resolved_at = datetime.now(UTC)
        upload.scan_result = reason or upload.scan_result

        # Remove quarantined file
        qpath = Path(upload.quarantine_path)
        if qpath.exists():
            qpath.unlink()

        db.add(
            AuditLog(
                user_id=admin.id,
                action="upload_rejected",
                details=f"Rejected upload: {upload.original_filename} — {reason}",
                source=EventSource.WEB,
            )
        )
        db.commit()

        _publish(
            CHANNEL_UPLOAD_RESOLVED,
            {
                "upload_id": upload.id,
                "filename": upload.original_filename,
                "status": "rejected",
                "by": admin.discord_username,
                "is_update": upload.mod_id is not None,
                "reason": reason,
                "discord_message_id": upload.discord_message_id,
                "discord_channel_id": upload.discord_channel_id,
            },
        )

    def get_pending_uploads(self, db: Session) -> list[ModUpload]:
        return (
            db.query(ModUpload)
            .filter(ModUpload.status == UploadStatus.PENDING_APPROVAL)
            .order_by(ModUpload.created_at.desc())
            .all()
        )
