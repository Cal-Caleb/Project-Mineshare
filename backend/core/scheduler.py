"""APScheduler-based 30-minute update loop.

Responsibilities:
- Check CurseForge mods for updates
- Expire stale votes
- Sync Discord roles → whitelist/OP
- Stage changed mods and trigger the server update sequence
"""

import contextlib
import logging
import shutil
import tempfile
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from core.config import get_settings
from core.database import SessionLocal
from core.events import (
    CHANNEL_MOD_UPDATED,
    CHANNEL_SERVER_UPDATE,
    get_event_bus,
)
from core.mod_manager import ModManager
from core.server_manager import ServerManager
from core.vote_manager import VoteManager
from core.whitelist_manager import WhitelistManager
from models import ModSource, ModUpdateLog

logger = logging.getLogger(__name__)

# File-based lock to prevent overlapping runs
_LOCK_FILE = Path(tempfile.gettempdir()) / "mineshare_update.lock"

scheduler = AsyncIOScheduler()


def _acquire_lock() -> bool:
    try:
        if _LOCK_FILE.exists():
            logger.warning("Update lock exists, skipping this cycle")
            return False
        _LOCK_FILE.write_text("locked")
        return True
    except Exception:
        return False


def _release_lock() -> None:
    with contextlib.suppress(Exception):
        _LOCK_FILE.unlink(missing_ok=True)


async def run_update_cycle() -> None:
    """Main 30-minute update cycle."""
    if not _acquire_lock():
        return

    settings = get_settings()
    mod_mgr = ModManager()
    server_mgr = ServerManager()
    vote_mgr = VoteManager()
    wl_mgr = WhitelistManager(server_mgr)
    bus = get_event_bus()
    db = SessionLocal()

    try:
        logger.info("=== Update cycle started ===")

        # 1. Expire stale votes
        expired = vote_mgr.expire_stale_votes(db)
        if expired:
            logger.info("Expired %d stale votes", len(expired))

        # 2. Sync Discord roles and whitelist/OP
        try:
            role_changes = await wl_mgr.sync_roles_from_discord(db)
            if role_changes:
                logger.info("Role changes synced: %d users updated", role_changes)
            wl_result = wl_mgr.sync_all_users(db)
            if any(wl_result.values()):
                logger.info("Whitelist sync: %s", wl_result)
        except Exception:
            logger.exception("Role/whitelist sync failed (non-fatal)")

        # 3. Check CurseForge mods for updates
        cf_mods = mod_mgr.get_curseforge_mods(db)
        updates_found = []

        for mod in cf_mods:
            if not mod.curse_project_id or not mod.curse_file_id:
                continue
            try:
                updated_info = await mod_mgr.check_for_update(mod.curse_project_id, mod.curse_file_id)
                if updated_info:
                    updates_found.append((mod, updated_info))
                    logger.info(
                        "Update available for %s: %s -> %s",
                        mod.name,
                        mod.file_name,
                        updated_info.latest_file_name,
                    )
            except Exception:
                logger.exception("Failed to check update for %s", mod.name)

        # 4. Build desired staging directory
        staging_dir = Path(tempfile.mkdtemp(prefix="mineshare_staging_"))
        server_mods_dir = Path(settings.server_path) / "mods"
        cache_dir = Path(settings.mod_cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Apply CurseForge updates to DB and fetch new files into cache
        for mod, info in updates_found:
            try:
                new_file = await mod_mgr.download_mod_file(info.project_id, info.latest_file_id, cache_dir)
                if new_file:
                    old_file_name = mod.file_name
                    old_file_id = mod.curse_file_id

                    # Fetch changelog from CurseForge
                    changelog = None
                    try:
                        changelog = await mod_mgr.get_file_changelog(info.project_id, info.latest_file_id)
                    except Exception:
                        logger.warning("Could not fetch changelog for %s", mod.name)

                    mod.curse_file_id = info.latest_file_id
                    mod.current_version = info.latest_file_name
                    mod.file_name = info.latest_file_name
                    mod.file_hash = ModManager.calculate_file_hash(new_file)

                    # Record update log with changelog
                    db.add(
                        ModUpdateLog(
                            mod_id=mod.id,
                            old_version=old_file_name,
                            new_version=info.latest_file_name,
                            old_file_id=old_file_id,
                            new_file_id=info.latest_file_id,
                            changelog=changelog,
                        )
                    )
                    db.commit()

                    await bus.publish(
                        CHANNEL_MOD_UPDATED,
                        {
                            "mod_id": mod.id,
                            "name": mod.name,
                            "old_version": old_file_name,
                            "new_version": info.latest_file_name,
                            "changelog": (changelog[:500] if changelog else None),
                        },
                    )
            except Exception:
                logger.exception("Failed to download update for %s", mod.name)

        # Collect every active mod into staging
        all_active = mod_mgr.get_active_mods(db)

        for mod in all_active:
            if not mod.file_name:
                continue
            dest = staging_dir / mod.file_name
            if dest.exists():
                continue

            if mod.source == ModSource.UPLOAD and mod.file_path:
                src = Path(mod.file_path)
                if src.exists():
                    shutil.copy2(src, dest)
                    logger.debug("Staged uploaded mod: %s", mod.file_name)
                else:
                    logger.warning("Upload file missing for %s: %s", mod.name, mod.file_path)

            elif mod.source == ModSource.CURSEFORGE:
                # Try cache → server mods folder → fresh download
                cached = cache_dir / mod.file_name
                on_server = server_mods_dir / mod.file_name
                if cached.exists():
                    shutil.copy2(cached, dest)
                elif on_server.exists():
                    shutil.copy2(on_server, dest)
                    shutil.copy2(on_server, cached)
                elif mod.curse_project_id and mod.curse_file_id:
                    try:
                        downloaded = await mod_mgr.download_mod_file(mod.curse_project_id, mod.curse_file_id, cache_dir)
                        if downloaded and downloaded.exists():
                            shutil.copy2(downloaded, dest)
                        else:
                            logger.warning("Could not fetch CF mod %s", mod.name)
                    except Exception:
                        logger.exception("Failed to fetch CF mod %s", mod.name)

        # 5. Diff desired staging vs current server mods dir
        desired_files = {f.name: f.stat().st_size for f in staging_dir.iterdir() if f.is_file()}
        current_files = (
            {f.name: f.stat().st_size for f in server_mods_dir.iterdir() if f.is_file()}
            if server_mods_dir.exists()
            else {}
        )
        has_changes = desired_files != current_files

        if has_changes:
            added = set(desired_files) - set(current_files)
            removed = set(current_files) - set(desired_files)
            logger.info(
                "Mods diff: +%d / -%d / total desired=%d",
                len(added),
                len(removed),
                len(desired_files),
            )

        # 5. Run server update loop if changes exist
        if has_changes:
            await bus.publish(
                CHANNEL_SERVER_UPDATE,
                {"status": "starting", "updates": len(updates_found)},
            )

            success = server_mgr.run_update_loop(
                db=db,
                staging_dir=staging_dir,
                has_changes=True,
            )

            await bus.publish(
                CHANNEL_SERVER_UPDATE,
                {
                    "status": "success" if success else "failed",
                    "updates": len(updates_found),
                },
            )
        else:
            logger.info("No mod updates found this cycle")

        # Cleanup staging
        shutil.rmtree(staging_dir, ignore_errors=True)

        logger.info("=== Update cycle completed ===")

    except Exception:
        logger.exception("Update cycle failed")
    finally:
        db.close()
        _release_lock()


def start_scheduler() -> None:
    settings = get_settings()
    scheduler.add_job(
        run_update_cycle,
        trigger=IntervalTrigger(minutes=settings.update_interval_minutes),
        id="update_cycle",
        name="Mod update cycle",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info("Scheduler started (interval=%dm)", settings.update_interval_minutes)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        _release_lock()
