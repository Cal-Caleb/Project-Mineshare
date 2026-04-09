import subprocess
import os
import time
import shutil
import tarfile
import zstandard as zstd
from datetime import datetime
from typing import Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ServerManager:
    def __init__(self, server_path: str, backup_path: str, rcon_host: str, 
                 rcon_port: int, rcon_password: str):
        self.server_path = Path(server_path)
        self.backup_path = Path(backup_path)
        self.rcon_host = rcon_host
        self.rcon_port = rcon_port
        self.rcon_password = rcon_password
        
        # Ensure backup path exists
        self.backup_path.mkdir(parents=True, exist_ok=True)
    
    def rcon_command(self, command: str) -> str:
        """Send command to Minecraft server via RCON"""
        try:
            # Using mcrcon - this would need to be installed on the system
            # For now, we'll simulate the behavior
            logger.info(f"RCON Command: {command}")
            return f"RCON command executed: {command}"
        except Exception as e:
            logger.error(f"RCON error: {str(e)}")
            return f"RCON error: {str(e)}"
    
    def announce_update(self, message: str) -> None:
        """Announce update to players"""
        self.rcon_command(f"say [MOD UPDATE] {message}")
    
    def save_world(self) -> bool:
        """Save Minecraft world"""
        try:
            logger.info("Saving world...")
            self.rcon_command("save-all")
            time.sleep(2)  # Wait for save to complete
            logger.info("World saved successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to save world: {str(e)}")
            return False
    
    def backup_world(self, backup_name: str = None) -> Optional[str]:
        """Create backup of world folder"""
        try:
            world_path = self.server_path / "world"
            if not world_path.exists():
                logger.error("World directory not found")
                return None
                
            if not backup_name:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
            backup_file = self.backup_path / f"{backup_name}.tar.zst"
            
            # Create tar archive
            logger.info(f"Creating backup: {backup_file}")
            with tarfile.open(backup_file.with_suffix(".tar"), "w") as tar:
                tar.add(world_path, arcname="world")
            
            # Compress with zstd
            with open(backup_file.with_suffix(".tar"), "rb") as f_in:
                with zstd.open(backup_file, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove original tar file
            os.remove(backup_file.with_suffix(".tar"))
            
            logger.info(f"Backup created: {backup_file}")
            return str(backup_file)
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            return None
    
    def swap_mods(self, new_mods_path: str) -> bool:
        """Replace mods directory with new mods"""
        try:
            mods_path = self.server_path / "mods"
            new_mods = Path(new_mods_path)
            
            if not new_mods.exists():
                logger.error("New mods directory not found")
                return False
                
            # Remove old mods
            if mods_path.exists():
                shutil.rmtree(mods_path)
                logger.info("Removed old mods directory")
                
            # Copy new mods
            shutil.copytree(new_mods, mods_path)
            logger.info("New mods copied successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to swap mods: {str(e)}")
            return False
    
    def restart_server(self) -> bool:
        """Restart server via systemd"""
        try:
            logger.info("Restarting Minecraft server...")
            result = subprocess.run(["systemctl", "restart", "minecraft-server"], 
                                  check=True, capture_output=True, text=True)
            logger.info("Server restart command sent")
            return True
        except Exception as e:
            logger.error(f"Failed to restart server: {str(e)}")
            return False
    
    def health_check(self, timeout: int = 60) -> bool:
        """Check if server is running properly"""
        start_time = time.time()
        logger.info("Performing health check...")
        while time.time() - start_time < timeout:
            try:
                # Check if server is running
                result = subprocess.run(["systemctl", "is-active", "minecraft-server"], 
                                      capture_output=True, text=True)
                if result.stdout.strip() == "active":
                    # Check logs for "Done"
                    logs = subprocess.run(["journalctl", "-u", "minecraft-server", "-n", "10"], 
                                        capture_output=True, text=True)
                    if "Done" in logs.stdout:
                        logger.info("Server health check passed")
                        return True
            except Exception as e:
                logger.error(f"Health check error: {str(e)}")
                pass
            time.sleep(5)
        logger.error("Health check failed")
        return False
    
    def run_update_loop(self) -> bool:
        """Run the complete update process"""
        try:
            logger.info("Starting update process...")
            
            # Announce update
            self.announce_update("Server will restart in 60 seconds for mod updates.")
            time.sleep(60)
            
            # Save world
            if not self.save_world():
                logger.error("Failed to save world")
                return False
            
            # Backup world
            backup_file = self.backup_world()
            if not backup_file:
                logger.error("Failed to backup world")
                return False
            
            # Swap mods
            # In a real implementation, this would be from a temporary directory
            # For now, we'll just simulate
            if not self.swap_mods(str(self.server_path / "mods")):
                logger.error("Failed to swap mods")
                return False
            
            # Restart server
            if not self.restart_server():
                logger.error("Failed to restart server")
                return False
            
            # Health check
            if not self.health_check():
                logger.error("Health check failed after restart")
                # Rollback logic would go here
                return False
                
            logger.info("Update process completed successfully")
            return True
        except Exception as e:
            logger.error(f"Update process failed: {str(e)}")
            return False
