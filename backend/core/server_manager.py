import logging
import os
import shutil
import subprocess
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from core.config import get_settings
from models import (
    AuditLog,
    EventSource,
    ServerEvent,
    ServerEventStatus,
    ServerEventType,
)

logger = logging.getLogger(__name__)


class ServerManager:
    def __init__(self):
        settings = get_settings()
        self.server_path = Path(settings.server_path)
        self.backup_path = Path(settings.backup_path)
        self.rcon_host = settings.rcon_host
        self.rcon_port = settings.rcon_port
        self.rcon_password = settings.rcon_password
        self.systemd_unit = settings.server_systemd_unit
        self.restart_warning_seconds = settings.restart_warning_seconds

        self.backup_path.mkdir(parents=True, exist_ok=True)

    # ── RCON ─────────────────────────────────────────────────────────

    def rcon_command(self, command: str) -> str:
        """Send a command to the Minecraft server via mcrcon."""
        try:
            result = subprocess.run(
                [
                    "mcrcon",
                    "-H", self.rcon_host,
                    "-P", str(self.rcon_port),
                    "-p", self.rcon_password,
                    "-c", command,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip()
        except FileNotFoundError:
            logger.error("mcrcon not found on PATH")
            return ""
        except subprocess.TimeoutExpired:
            logger.error("RCON command timed out: %s", command)
            return ""
        except Exception:
            logger.exception("RCON command failed: %s", command)
            return ""

    def announce(self, message: str) -> None:
        self.rcon_command(f'say [MineShare] {message}')

    def get_online_players(self) -> list[str]:
        """Get list of online player names."""
        resp = self.rcon_command("list")
        # Response: "There are X of Y players online: player1, player2"
        if ":" in resp:
            names_part = resp.split(":", 1)[1].strip()
            if names_part:
                return [n.strip() for n in names_part.split(",") if n.strip()]
        return []

    def save_world(self) -> bool:
        try:
            self.rcon_command("save-all flush")
            time.sleep(3)
            logger.info("World saved")
            return True
        except Exception:
            logger.exception("Failed to save world")
            return False

    # ── Whitelist / OP ───────────────────────────────────────────────

    def whitelist_add(self, mc_username: str) -> str:
        return self.rcon_command(f"whitelist add {mc_username}")

    def whitelist_remove(self, mc_username: str) -> str:
        return self.rcon_command(f"whitelist remove {mc_username}")

    def op_add(self, mc_username: str) -> str:
        return self.rcon_command(f"op {mc_username}")

    def op_remove(self, mc_username: str) -> str:
        return self.rcon_command(f"deop {mc_username}")

    # ── Backup ───────────────────────────────────────────────────────

    def backup_world(
        self, db: Session | None = None, triggered_by_id: int | None = None
    ) -> Optional[str]:
        event = None
        if db:
            event = ServerEvent(
                event_type=ServerEventType.BACKUP,
                status=ServerEventStatus.STARTED,
                triggered_by_id=triggered_by_id,
            )
            db.add(event)
            db.commit()

        world_path = self.server_path / "world"
        if not world_path.exists():
            logger.error("World directory not found: %s", world_path)
            if event and db:
                event.status = ServerEventStatus.FAILED
                event.details = "World directory not found"
                event.completed_at = datetime.now(timezone.utc)
                db.commit()
            return None

        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{stamp}"
        tar_path = self.backup_path / f"{backup_name}.tar.zst"

        try:
            # Create tar first
            tmp_tar = self.backup_path / f"{backup_name}.tar"
            with tarfile.open(tmp_tar, "w") as tar:
                tar.add(world_path, arcname="world")

            # Compress with zstd via CLI (widely available, fast)
            subprocess.run(
                ["zstd", "--rm", "-q", str(tmp_tar), "-o", str(tar_path)],
                check=True,
                timeout=300,
            )

            logger.info("Backup created: %s", tar_path)

            if event and db:
                event.status = ServerEventStatus.SUCCESS
                event.backup_path = str(tar_path)
                event.completed_at = datetime.now(timezone.utc)
                db.commit()

            self._cleanup_old_backups(keep=10)
            return str(tar_path)

        except Exception:
            logger.exception("Backup failed")
            if event and db:
                event.status = ServerEventStatus.FAILED
                event.details = "Backup process failed"
                event.completed_at = datetime.now(timezone.utc)
                db.commit()
            return None

    def _cleanup_old_backups(self, keep: int = 10) -> None:
        backups = sorted(self.backup_path.glob("backup_*.tar.zst"))
        for old in backups[:-keep]:
            old.unlink()
            logger.info("Removed old backup: %s", old.name)

    # ── Mod Swapping ─────────────────────────────────────────────────

    def swap_mods(self, staging_dir: Path) -> bool:
        """Replace the server mods/ directory with contents of staging_dir."""
        mods_path = self.server_path / "mods"
        try:
            if mods_path.exists():
                shutil.rmtree(mods_path)
            shutil.copytree(staging_dir, mods_path)
            logger.info("Mods swapped from %s", staging_dir)
            return True
        except Exception:
            logger.exception("Failed to swap mods")
            return False

    # ── Server Control ───────────────────────────────────────────────

    def restart_server(self, db: Session | None = None, triggered_by_id: int | None = None) -> bool:
        event = None
        if db:
            event = ServerEvent(
                event_type=ServerEventType.RESTART,
                status=ServerEventStatus.STARTED,
                triggered_by_id=triggered_by_id,
            )
            db.add(event)
            db.commit()

        try:
            subprocess.run(
                ["systemctl", "restart", self.systemd_unit],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            logger.info("Server restart command sent")
            if event and db:
                event.status = ServerEventStatus.SUCCESS
                event.completed_at = datetime.now(timezone.utc)
                db.commit()
            return True
        except Exception:
            logger.exception("Failed to restart server")
            if event and db:
                event.status = ServerEventStatus.FAILED
                event.completed_at = datetime.now(timezone.utc)
                db.commit()
            return False

    def health_check(self, timeout: int = 120) -> bool:
        """Wait for server to report 'Done' in journal logs."""
        start = time.time()
        logger.info("Running health check (timeout=%ds)...", timeout)
        while time.time() - start < timeout:
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", self.systemd_unit],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.stdout.strip() != "active":
                    time.sleep(5)
                    continue

                logs = subprocess.run(
                    ["journalctl", "-u", self.systemd_unit, "-n", "20", "--no-pager"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if "Done" in logs.stdout:
                    logger.info("Health check passed")
                    return True
            except Exception:
                pass
            time.sleep(5)

        logger.error("Health check timed out")
        return False

    def is_server_running(self) -> bool:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", self.systemd_unit],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip() == "active"
        except Exception:
            return False

    def get_status(self) -> dict:
        """Return a status summary dict."""
        running = self.is_server_running()
        players = self.get_online_players() if running else []
        return {
            "online": running,
            "players": players,
            "player_count": len(players),
        }

    # ── Full Update Loop ─────────────────────────────────────────────

    def run_update_loop(
        self,
        db: Session,
        staging_dir: Path,
        has_changes: bool,
        triggered_by_id: int | None = None,
    ) -> bool:
        """Execute the graceful update sequence.

        1. RCON announce + warning
        2. save-all
        3. Backup world
        4. Swap mods
        5. Restart server
        6. Health check
        """
        if not has_changes:
            logger.info("No mod changes to apply, skipping update loop")
            return True

        event = ServerEvent(
            event_type=ServerEventType.UPDATE_APPLIED,
            status=ServerEventStatus.STARTED,
            triggered_by_id=triggered_by_id,
        )
        db.add(event)
        db.commit()

        try:
            # 1. Announce
            players = self.get_online_players()
            warning_time = self.restart_warning_seconds if players else 5
            self.announce(
                f"Server restarting in {warning_time}s for mod updates!"
            )
            time.sleep(warning_time)

            # 2. Save
            if not self.save_world():
                raise RuntimeError("Failed to save world")

            # 3. Backup
            backup = self.backup_world(db, triggered_by_id)
            if not backup:
                raise RuntimeError("Failed to backup world")

            # 4. Swap mods
            if not self.swap_mods(staging_dir):
                raise RuntimeError("Failed to swap mods")

            # 5. Restart
            if not self.restart_server(db, triggered_by_id):
                raise RuntimeError("Failed to restart server")

            # 6. Health check
            if not self.health_check():
                logger.error("Health check failed, consider rollback")
                event.status = ServerEventStatus.FAILED
                event.details = "Health check failed after restart"
                event.completed_at = datetime.now(timezone.utc)
                db.commit()
                return False

            event.status = ServerEventStatus.SUCCESS
            event.completed_at = datetime.now(timezone.utc)
            db.add(
                AuditLog(
                    user_id=triggered_by_id,
                    action="server_updated",
                    details="Automated update completed successfully",
                    source=EventSource.SYSTEM,
                )
            )
            db.commit()
            logger.info("Update loop completed successfully")
            return True

        except Exception as exc:
            logger.exception("Update loop failed")
            event.status = ServerEventStatus.FAILED
            event.details = str(exc)
            event.completed_at = datetime.now(timezone.utc)
            db.commit()
            return False
