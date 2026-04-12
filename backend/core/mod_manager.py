import hashlib
import logging
import re
import zipfile
from dataclasses import dataclass, field
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

# CurseForge modLoaderType constants
LOADER_NEOFORGE = 6
LOADER_FORGE = 1

# CurseForge releaseType: 1=Release, 2=Beta, 3=Alpha
RELEASE_TYPES_ALLOWED = {1, 2}  # Release + Beta


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
    supports_neoforge: bool = False
    game_versions: list[str] = field(default_factory=list)


@dataclass
class CurseForgeFileInfo:
    file_id: int
    file_name: str
    file_date: str | None
    download_url: str | None
    game_versions: list[str] = field(default_factory=list)
    mod_loader: str | None = None
    release_type: int = 1


class ModManager:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.curseforge_api_key
        self.base_url = "https://api.curseforge.com"
        self.game_id = settings.minecraft_game_id
        self.server_mods_path = Path(settings.server_path) / "mods"
        self.mc_version = settings.minecraft_version or self._detect_mc_version(settings)
        self.neoforge_loader_type = settings.neoforge_loader_type
        self._headers = {
            "Accept": "application/json",
            "x-api-key": self.api_key,
        }

    @staticmethod
    def _detect_mc_version(settings) -> str:
        """Try to read --fml.mcVersion from server args."""
        server_path = Path(settings.server_path)
        for args_file in server_path.glob("libraries/net/neoforged/neoforge/*/unix_args.txt"):
            try:
                text = args_file.read_text()
                m = re.search(r"--fml\.mcVersion\s+(\S+)", text)
                if m:
                    logger.info("Auto-detected MC version: %s", m.group(1))
                    return m.group(1)
            except Exception:
                pass
        logger.warning("Could not detect MC version, falling back to 1.21.5")
        return "1.21.5"

    # ── CurseForge API ───────────────────────────────────────────────

    async def resolve_curseforge_url(self, url: str) -> Optional[CurseForgeModInfo]:
        """Resolve a CurseForge URL to mod info, validated for NeoForge + our MC version."""
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
                logger.error(
                    "CurseForge search failed: %s: %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return None

            data = resp.json().get("data", [])
            if not data:
                return None

            mod_data = data[0]
            info = self._parse_mod(mod_data)

            # Find a compatible file for our MC version + NeoForge
            best = await self._find_best_file(client, info.project_id)
            if best:
                info.latest_file_id = best.file_id
                info.latest_file_name = best.file_name
                info.latest_file_date = best.file_date
                info.supports_neoforge = True
                info.game_versions = best.game_versions
            else:
                # Check if ANY file supports our version at all
                info.supports_neoforge = False

            return info

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

    async def _find_best_file(
        self,
        client: httpx.AsyncClient,
        project_id: int,
    ) -> Optional[CurseForgeFileInfo]:
        """Find the newest compatible file for our MC version + NeoForge.

        CurseForge /files endpoint supports gameVersion + modLoaderType filters.
        """
        resp = await client.get(
            f"{self.base_url}/v1/mods/{project_id}/files",
            headers=self._headers,
            params={
                "gameVersion": self.mc_version,
                "modLoaderType": self.neoforge_loader_type,
                "pageSize": 20,
            },
        )
        if resp.status_code != 200:
            logger.warning(
                "CF files query failed for project %d: %s",
                project_id,
                resp.status_code,
            )
            return None

        files = resp.json().get("data", [])

        # Filter to stable/beta releases, sort by date descending
        candidates = []
        for f in files:
            rt = f.get("releaseType", 1)
            if rt not in RELEASE_TYPES_ALLOWED:
                continue
            versions = f.get("gameVersions", [])
            # Double-check our MC version is in the list
            if self.mc_version not in versions:
                continue
            # Check NeoForge is listed (CF uses "NeoForge" as a gameVersion string)
            loaders = [v for v in versions if v.lower() in ("neoforge", "forge")]
            if not any(v.lower() == "neoforge" for v in loaders):
                # Also accept if modLoader field on sortableGameVersions says neoforge
                sgv = f.get("sortableGameVersions", [])
                nf_match = any(
                    g.get("gameVersion", "").lower() == "neoforge"
                    or g.get("gameVersionTypeId") == self.neoforge_loader_type
                    for g in sgv
                )
                if not nf_match:
                    continue

            candidates.append(
                CurseForgeFileInfo(
                    file_id=f["id"],
                    file_name=f.get("fileName", ""),
                    file_date=f.get("fileDate"),
                    download_url=f.get("downloadUrl"),
                    game_versions=versions,
                    release_type=rt,
                )
            )

        if not candidates:
            return None

        # Sort by fileDate descending (newest first)
        candidates.sort(key=lambda c: c.file_date or "", reverse=True)
        return candidates[0]

    async def check_for_update(
        self, project_id: int, current_file_id: int
    ) -> Optional[CurseForgeModInfo]:
        """Check if a newer compatible file exists for this project.

        Only returns an update if the newer file supports our MC version + NeoForge.
        """
        async with httpx.AsyncClient() as client:
            best = await self._find_best_file(client, project_id)
            if not best:
                return None
            if best.file_id == current_file_id:
                return None

            # Build a CurseForgeModInfo with the updated file info
            info = await self.get_project(project_id)
            if not info:
                return None
            info.latest_file_id = best.file_id
            info.latest_file_name = best.file_name
            info.latest_file_date = best.file_date
            info.game_versions = best.game_versions
            info.supports_neoforge = True
            return info

    async def download_mod_file(
        self, project_id: int, file_id: int, dest_dir: Path
    ) -> Optional[Path]:
        """Download a mod file from CurseForge."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
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

        Validates NeoForge + MC version compatibility before adding.
        """
        if not info.supports_neoforge:
            raise ValueError(
                f"'{info.name}' has no NeoForge-compatible file for "
                f"Minecraft {self.mc_version}. "
                f"Check that the mod supports NeoForge on this version."
            )

        existing = (
            db.query(Mod)
            .filter(Mod.curse_project_id == info.project_id)
            .first()
        )
        if existing and existing.status != ModStatus.REMOVED:
            raise ValueError(f"Mod '{info.name}' is already tracked")

        status = (
            ModStatus.ACTIVE
            if (force and user.role == UserRole.ADMIN)
            else ModStatus.PENDING_VOTE
        )

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
                details=(
                    f"{info.name} from CurseForge (NeoForge, MC {self.mc_version})"
                    f" (force={force})"
                ),
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
                    n.endswith(".class") or n == "META-INF/MANIFEST.MF"
                    for n in names
                )
        except (zipfile.BadZipFile, Exception):
            return False
