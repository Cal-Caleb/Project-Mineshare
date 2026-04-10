import logging
import os
import shutil
import socket
import struct
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
        self.pause_flag = self.server_path / "mineshare_pause.flag"

        self.backup_path.mkdir(parents=True, exist_ok=True)

    # ── RCON ─────────────────────────────────────────────────────────

    def rcon_command(self, command: str) -> str:
        """Send a command to the Minecraft server via RCON protocol."""
        try:
            return self._rcon_send(command)
        except (ConnectionRefusedError, ConnectionError, OSError):
            logger.debug("RCON unavailable (server likely offline): %s", command)
            return ""
        except Exception:
            logger.exception("RCON command failed: %s", command)
            return ""

    def _rcon_send(self, command: str) -> str:
        """Pure-Python Minecraft RCON client."""
        SERVERDATA_AUTH = 3
        SERVERDATA_EXECCOMMAND = 2

        def _pack(req_id: int, req_type: int, payload: str) -> bytes:
            data = struct.pack("<ii", req_id, req_type) + payload.encode("utf-8") + b"\x00\x00"
            return struct.pack("<i", len(data)) + data

        def _unpack(sock: socket.socket) -> tuple[int, int, str]:
            raw_len = sock.recv(4)
            if len(raw_len) < 4:
                raise ConnectionError("RCON connection closed")
            length = struct.unpack("<i", raw_len)[0]
            data = b""
            while len(data) < length:
                data += sock.recv(length - len(data))
            req_id, req_type = struct.unpack("<ii", data[:8])
            body = data[8:-2].decode("utf-8")
            return req_id, req_type, body

        with socket.create_connection((self.rcon_host, self.rcon_port), timeout=10) as sock:
            # Authenticate
            sock.sendall(_pack(1, SERVERDATA_AUTH, self.rcon_password))
            auth_id, _, _ = _unpack(sock)
            if auth_id == -1:
                logger.error("RCON authentication failed")
                return ""

            # Send command
            sock.sendall(_pack(2, SERVERDATA_EXECCOMMAND, command))
            _, _, body = _unpack(sock)
            return body.strip()

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
        tar_path = self.backup_path / f"{backup_name}.tar.gz"

        try:
            with tarfile.open(tar_path, "w:gz", compresslevel=6) as tar:
                tar.add(world_path, arcname="world")

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
        backups = sorted(self.backup_path.glob("backup_*.tar.gz"))
        for old in backups[:-keep]:
            old.unlink()
            logger.info("Removed old backup: %s", old.name)

    # ── Mod Swapping ─────────────────────────────────────────────────

    def swap_mods(self, staging_dir: Path) -> bool:
        """Replace the server mods/ directory with contents of staging_dir.

        Does an in-place sync (delete files not in staging, copy everything
        from staging) instead of rmtree/copytree, which is more robust on
        Windows bind mounts where file locks and permission errors are common.
        """
        mods_path = self.server_path / "mods"
        try:
            mods_path.mkdir(parents=True, exist_ok=True)

            desired = {
                f.name: f for f in staging_dir.iterdir() if f.is_file()
            }
            current = {
                f.name: f for f in mods_path.iterdir() if f.is_file()
            }

            removed = 0
            for name, path in current.items():
                if name not in desired:
                    try:
                        path.unlink()
                        removed += 1
                    except Exception:
                        logger.exception("Could not remove %s", path)
                        return False

            added = 0
            updated = 0
            for name, src in desired.items():
                dest = mods_path / name
                if dest.exists():
                    if src.stat().st_size == dest.stat().st_size:
                        continue
                    try:
                        dest.unlink()
                    except Exception:
                        logger.exception("Could not replace %s", dest)
                        return False
                    shutil.copy2(src, dest)
                    updated += 1
                else:
                    shutil.copy2(src, dest)
                    added += 1

            logger.info(
                "Mods synced: +%d / ~%d / -%d (total %d)",
                added,
                updated,
                removed,
                len(desired),
            )
            return True
        except Exception:
            logger.exception("Failed to swap mods")
            return False

    # ── Server Control ───────────────────────────────────────────────

    def restart_server(self, db: Session | None = None, triggered_by_id: int | None = None) -> bool:
        """Restart the server by sending RCON 'stop'.

        The host systemd service should be configured with Restart=always
        so the server comes back up automatically after stop.
        """
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
            self.rcon_command("stop")
            logger.info("Server stop command sent via RCON (systemd will restart)")
            # Wait for server to come back
            if not self.health_check():
                raise RuntimeError("Server did not come back after restart")
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

    def wait_for_stop(self, timeout: int = 90) -> bool:
        """Wait for the server to stop responding to RCON."""
        start = time.time()
        logger.info("Waiting for server to stop (timeout=%ds)...", timeout)
        while time.time() - start < timeout:
            try:
                with socket.create_connection(
                    (self.rcon_host, self.rcon_port), timeout=2
                ):
                    pass
                # RCON port still open — still running
            except (ConnectionRefusedError, OSError):
                logger.info("Server confirmed stopped")
                return True
            time.sleep(2)
        logger.error("Server did not stop within %ds", timeout)
        return False

    def health_check(self, timeout: int = 180) -> bool:
        """Wait for the server to accept RCON connections again."""
        start = time.time()
        logger.info("Running health check (timeout=%ds)...", timeout)
        # Wait a few seconds for the server to actually stop first
        time.sleep(10)
        while time.time() - start < timeout:
            try:
                resp = self.rcon_command("list")
                if resp:
                    logger.info("Health check passed")
                    return True
            except Exception:
                pass
            time.sleep(5)

        logger.error("Health check timed out")
        return False

    def is_server_running(self) -> bool:
        try:
            resp = self.rcon_command("list")
            return bool(resp)
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
            server_was_running = self.is_server_running()

            # Set pause flag so the wrapper script holds off on relaunching
            try:
                self.pause_flag.write_text("locked")
                logger.info("Pause flag set at %s", self.pause_flag)
            except Exception:
                logger.exception("Failed to write pause flag")

            if server_was_running:
                # 1. Announce
                players = self.get_online_players()
                warning_time = self.restart_warning_seconds if players else 5
                self.announce(
                    f"Server restarting in {warning_time}s for mod updates!"
                )
                time.sleep(warning_time)

                # 2. Save
                self.save_world()

                # 3. Stop the server (wrapper holds due to pause flag)
                logger.info("Sending RCON stop for update...")
                self.rcon_command("stop")
                if not self.wait_for_stop(timeout=90):
                    raise RuntimeError("Server did not stop in time")
                # Extra grace period so file handles fully drain on Windows
                time.sleep(3)

            # 4. Swap mods FIRST so the mods dir is settled before anything else
            if not self.swap_mods(staging_dir):
                raise RuntimeError("Failed to swap mods")

            # 5. Backup (safe — server is offline)
            backup = self.backup_world(db, triggered_by_id)
            if not backup:
                raise RuntimeError("Failed to backup world")

            # 6. Release the pause flag so wrapper can relaunch
            try:
                self.pause_flag.unlink(missing_ok=True)
                logger.info("Pause flag cleared")
            except Exception:
                logger.exception("Failed to clear pause flag")

            # 7. Wait for wrapper to bring server back
            if server_was_running and not self.health_check(timeout=240):
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
        finally:
            # Always clear the pause flag so the server can relaunch
            try:
                self.pause_flag.unlink(missing_ok=True)
            except Exception:
                pass
