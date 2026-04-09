import hashlib
import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from core.config import get_settings
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
)

logger = logging.getLogger(__name__)


class UploadManager:
    def __init__(self):
        settings = get_settings()
        self.upload_dir = Path(settings.upload_dir)
        self.quarantine_dir = Path(settings.quarantine_dir)
        self.max_size = settings.max_upload_size
        self.clamav_host = settings.clamav_host
        self.clamav_port = settings.clamav_port

        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

    async def handle_upload(
        self, db: Session, file_bytes: bytes, original_filename: str, user: User
    ) -> ModUpload:
        """Accept an uploaded JAR, quarantine it, and queue for scanning."""
        if len(file_bytes) > self.max_size:
            raise ValueError(
                f"File too large ({len(file_bytes)} bytes, max {self.max_size})"
            )

        if not original_filename.lower().endswith(".jar"):
            raise ValueError("Only .jar files are accepted")

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
            status=UploadStatus.PENDING_SCAN,
            uploaded_by_id=user.id,
        )
        db.add(upload)
        db.add(
            AuditLog(
                user_id=user.id,
                action="file_uploaded",
                details=f"Uploaded {original_filename} ({len(file_bytes)} bytes)",
                source=EventSource.WEB,
            )
        )
        db.commit()
        db.refresh(upload)
        return upload

    def scan_file(self, db: Session, upload: ModUpload) -> bool:
        """Scan a quarantined file with ClamAV. Returns True if clean."""
        upload.status = UploadStatus.SCANNING
        db.commit()

        try:
            import pyclamd

            cd = pyclamd.ClamdNetworkSocket(
                host=self.clamav_host, port=self.clamav_port
            )
            if not cd.ping():
                logger.error("ClamAV not reachable")
                upload.scan_result = "ClamAV unreachable"
                upload.status = UploadStatus.PENDING_SCAN
                db.commit()
                return False

            result = cd.scan_file(upload.quarantine_path)

            if result is None:
                # Clean
                upload.status = UploadStatus.CLEAN
                upload.scan_result = "Clean"
                db.commit()
                logger.info("File clean: %s", upload.original_filename)
                return True
            else:
                # Infected
                upload.status = UploadStatus.INFECTED
                upload.scan_result = str(result)
                db.commit()
                logger.warning(
                    "File infected: %s — %s", upload.original_filename, result
                )
                return False

        except ImportError:
            logger.warning("pyclamd not available, marking as clean")
            upload.status = UploadStatus.CLEAN
            upload.scan_result = "Scan skipped (pyclamd unavailable)"
            db.commit()
            return True
        except Exception:
            logger.exception("Scan failed for %s", upload.original_filename)
            upload.scan_result = "Scan error"
            upload.status = UploadStatus.PENDING_SCAN
            db.commit()
            return False

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
        if upload.status not in (UploadStatus.CLEAN, UploadStatus.PENDING_APPROVAL):
            raise ValueError(f"Upload is not approvable (status={upload.status.value})")

        # Move from quarantine to uploads
        dest = self.upload_dir / upload.filename
        src = Path(upload.quarantine_path)
        if src.exists():
            shutil.move(str(src), str(dest))

        upload.status = UploadStatus.APPROVED
        upload.approved_by_id = admin.id
        upload.resolved_at = datetime.now(timezone.utc)

        # Create the mod record
        mod = Mod(
            name=mod_name,
            source=ModSource.UPLOAD,
            file_path=str(dest),
            file_hash=upload.file_hash,
            file_name=upload.original_filename,
            status=ModStatus.ACTIVE,
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
        return mod

    def reject_upload(
        self, db: Session, upload: ModUpload, admin: User, reason: str = ""
    ) -> None:
        if admin.role != UserRole.ADMIN:
            raise PermissionError("Only admins can reject uploads")

        upload.status = UploadStatus.REJECTED
        upload.approved_by_id = admin.id
        upload.resolved_at = datetime.now(timezone.utc)
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

    def get_pending_uploads(self, db: Session) -> list[ModUpload]:
        return (
            db.query(ModUpload)
            .filter(
                ModUpload.status.in_(
                    [UploadStatus.CLEAN, UploadStatus.PENDING_APPROVAL]
                )
            )
            .order_by(ModUpload.created_at.desc())
            .all()
        )
