import hashlib
import logging
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from core.config import get_settings
from models import (
    AuditLog,
    EventSource,
    Mod,
    ModSource,
    ModStatus,
    User,
    UserRole,
)

logger = logging.getLogger(__name__)


@dataclass
class CurseForgeModInfo:
    project_id: int
    name: str
    slug: str
    summary: str
    author: str
    logo_url: str | None
    latest_file_id: int | None
    latest_file_name: str | None
    latest_file_date: str | None
    download_count: int


class ModManager:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.curseforge_api_key
        self.base_url = "https://api.curseforge.com"
        self.game_id = settings.minecraft_game_id
        self.server_mods_path = Path(settings.server_path) / "mods"
        self._headers = {
            "Accept": "application/json",
            "x-api-key": self.api_key,
        }

    # ── CurseForge API ───────────────────────────────────────────────

    async def resolve_curseforge_url(self, url: str) -> Optional[CurseForgeModInfo]:
        """Resolve a CurseForge URL to mod info.

        Supports URLs like:
            https://www.curseforge.com/minecraft/mc-mods/sodium
            https://www.curseforge.com/minecraft/mc-mods/sodium/files
        """
        slug = self._extract_slug(url)
        if not slug:
            return None
        return await self.search_by_slug(slug)

    def _extract_slug(self, url: str) -> Optional[str]:
        url = url.strip().rstrip("/")
        try:
            if "curseforge.com/minecraft" not in url:
                return None
            parts = url.split("/")
            mc_mods_idx = parts.index("mc-mods")
            if mc_mods_idx + 1 < len(parts):
                return parts[mc_mods_idx + 1]
        except (ValueError, IndexError):
            pass
        return None

    async def search_by_slug(self, slug: str) -> Optional[CurseForgeModInfo]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/v1/mods/search",
                headers=self._headers,
                params={
                    "gameId": self.game_id,
                    "slug": slug,
                    "pageSize": 1,
                },
            )
            if resp.status_code != 200:
                logger.error("CurseForge search failed: %s", resp.text)
                return None

            data = resp.json().get("data", [])
            if not data:
                return None
            return self._parse_mod(data[0])

    async def get_project(self, project_id: int) -> Optional[CurseForgeModInfo]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/v1/mods/{project_id}",
                headers=self._headers,
            )
            if resp.status_code != 200:
                return None
            project = resp.json().get("data")
            if not project:
                return None
            return self._parse_mod(project)

    async def check_for_update(
        self, project_id: int, current_file_id: int
    ) -> Optional[CurseForgeModInfo]:
        """Check if a newer file exists for this project."""
        info = await self.get_project(project_id)
        if not info or not info.latest_file_id:
            return None
        if info.latest_file_id != current_file_id:
            return info
        return None

    async def download_mod_file(
        self, project_id: int, file_id: int, dest_dir: Path
    ) -> Optional[Path]:
        """Download a mod file from CurseForge."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            # Get file info for download URL
            resp = await client.get(
                f"{self.base_url}/v1/mods/{project_id}/files/{file_id}",
                headers=self._headers,
            )
            if resp.status_code != 200:
                return None

            file_data = resp.json().get("data", {})
            download_url = file_data.get("downloadUrl")
            file_name = file_data.get("fileName")

            if not download_url or not file_name:
                # Some mods require distribution through 3rd party
                logger.warning(
                    "No direct download URL for project %d file %d",
                    project_id,
                    file_id,
                )
                return None

            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / file_name

            dl_resp = await client.get(download_url)
            if dl_resp.status_code != 200:
                return None

            dest_path.write_bytes(dl_resp.content)
            return dest_path

    def _parse_mod(self, data: dict) -> CurseForgeModInfo:
        latest_files = data.get("latestFiles", [])
        latest = latest_files[0] if latest_files else {}
        authors = data.get("authors", [])
        logo = data.get("logo", {})
        return CurseForgeModInfo(
            project_id=data["id"],
            name=data["name"],
            slug=data.get("slug", ""),
            summary=data.get("summary", ""),
            author=authors[0]["name"] if authors else "Unknown",
            logo_url=logo.get("url") if logo else None,
            latest_file_id=latest.get("id"),
            latest_file_name=latest.get("fileName"),
            latest_file_date=latest.get("fileDate"),
            download_count=data.get("downloadCount", 0),
        )

    # ── DB Operations ────────────────────────────────────────────────

    def add_mod_from_curseforge(
        self,
        db: Session,
        info: CurseForgeModInfo,
        user: User,
        source_url: str,
        force: bool = False,
    ) -> Mod:
        """Create a Mod record from CurseForge data.

        If user is admin and force=True, mod goes directly to active.
        Otherwise it goes to pending_vote.
        """
        existing = (
            db.query(Mod)
            .filter(Mod.curse_project_id == info.project_id)
            .first()
        )
        if existing and existing.status != ModStatus.REMOVED:
            raise ValueError(f"Mod '{info.name}' is already tracked")

        status = ModStatus.ACTIVE if (force and user.role == UserRole.ADMIN) else ModStatus.PENDING_VOTE

        mod = Mod(
            name=info.name,
            slug=info.slug,
            description=info.summary,
            author=info.author,
            source=ModSource.CURSEFORGE,
            source_url=source_url,
            curse_project_id=info.project_id,
            curse_file_id=info.latest_file_id,
            current_version=info.latest_file_name,
            file_name=info.latest_file_name,
            download_count=info.download_count,
            status=status,
            added_by_id=user.id,
        )
        db.add(mod)

        db.add(
            AuditLog(
                user_id=user.id,
                action="mod_added" if status == ModStatus.ACTIVE else "mod_proposed",
                details=f"{info.name} from CurseForge (force={force})",
                source=EventSource.WEB,
            )
        )
        db.commit()
        db.refresh(mod)
        return mod

    def add_mod_from_upload(
        self,
        db: Session,
        name: str,
        file_path: str,
        file_hash: str,
        user: User,
    ) -> Mod:
        """Create a Mod record from a custom upload."""
        mod = Mod(
            name=name,
            source=ModSource.UPLOAD,
            file_path=file_path,
            file_hash=file_hash,
            file_name=Path(file_path).name,
            status=ModStatus.PENDING_APPROVAL,
            added_by_id=user.id,
        )
        db.add(mod)
        db.add(
            AuditLog(
                user_id=user.id,
                action="mod_uploaded",
                details=f"Custom upload: {name}",
                source=EventSource.WEB,
            )
        )
        db.commit()
        db.refresh(mod)
        return mod

    def remove_mod(self, db: Session, mod: Mod, user: User) -> None:
        mod.status = ModStatus.REMOVED
        mod.updated_at = datetime.now(timezone.utc)
        db.add(
            AuditLog(
                user_id=user.id,
                action="mod_removed",
                details=f"Removed mod: {mod.name}",
                source=EventSource.WEB,
            )
        )
        db.commit()

    def activate_mod(self, db: Session, mod: Mod) -> None:
        mod.status = ModStatus.ACTIVE
        mod.updated_at = datetime.now(timezone.utc)
        db.commit()

    def get_active_mods(self, db: Session) -> list[Mod]:
        return db.query(Mod).filter(Mod.status == ModStatus.ACTIVE).all()

    def get_curseforge_mods(self, db: Session) -> list[Mod]:
        return (
            db.query(Mod)
            .filter(
                Mod.source == ModSource.CURSEFORGE,
                Mod.status == ModStatus.ACTIVE,
                Mod.curse_project_id.isnot(None),
            )
            .all()
        )

    # ── File Utilities ───────────────────────────────────────────────

    @staticmethod
    def calculate_file_hash(file_path: str | Path) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def validate_jar(file_path: str | Path) -> bool:
        path = Path(file_path)
        if path.suffix.lower() != ".jar":
            return False
        try:
            with zipfile.ZipFile(path, "r") as zf:
                names = zf.namelist()
                return any(
                    n.endswith(".class") or n == "META-INF/MANIFEST.MF" for n in names
                )
        except (zipfile.BadZipFile, Exception):
            return False
