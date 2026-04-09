import requests
import hashlib
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Mod:
    id: int
    name: str
    source_url: str
    curse_id: int
    file_hash: str
    added_by: str
    added_at: datetime
    status: str  # active, inactive, pending

@dataclass
class CurseForgeMod:
    id: int
    name: str
    latest_file_id: int
    latest_file_name: str
    latest_file_url: str
    latest_file_date: str
    download_count: int

class ModManager:
    def __init__(self, curse_api_key: str = None):
        self.curse_api_key = curse_api_key
        self.base_url = "https://api.curseforge.com"
        self.headers = {"X-Api-Key": curse_api_key} if curse_api_key else {}
    
    def resolve_curseforge_url(self, url: str) -> Optional[CurseForgeMod]:
        """Extract project ID from CurseForge URL"""
        try:
            # Example: https://www.curseforge.com/minecraft/mc-mods/modname
            if "curseforge.com/minecraft" in url:
                parts = url.strip("/").split("/")
                project_id = parts[-1] if parts else None
                if project_id and project_id.isdigit():
                    return self.get_curseforge_project(int(project_id))
        except Exception:
            pass
        return None
    
    def get_curseforge_project(self, project_id: int) -> Optional[CurseForgeMod]:
        """Fetch project info from CurseForge API"""
        try:
            response = requests.get(
                f"{self.base_url}/v1/mods/{project_id}",
                headers=self.headers
            )
            if response.status_code == 200:
                data = response.json()
                project = data.get("data", {})
                return CurseForgeMod(
                    id=project.get("id"),
                    name=project.get("name"),
                    latest_file_id=project.get("latestFiles", [{}])[0].get("id") if project.get("latestFiles") else None,
                    latest_file_name=project.get("latestFiles", [{}])[0].get("fileName") if project.get("latestFiles") else None,
                    latest_file_url=project.get("latestFiles", [{}])[0].get("downloadUrl") if project.get("latestFiles") else None,
                    latest_file_date=project.get("latestFiles", [{}])[0].get("fileDate") if project.get("latestFiles") else None,
                    download_count=project.get("downloadCount", 0)
                )
        except Exception:
            pass
        return None
    
    def get_curseforge_files(self, project_id: int) -> List[Dict]:
        """Get all files for a CurseForge project"""
        try:
            response = requests.get(
                f"{self.base_url}/v1/mods/{project_id}/files",
                headers=self.headers
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
        except Exception:
            pass
        return []
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file"""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception:
            return ""
    
    def validate_jar(self, file_path: str) -> bool:
        """Basic JAR validation"""
        try:
            if not file_path.endswith(".jar"):
                return False
            
            # Check if it's a valid ZIP file (JARs are ZIPs)
            import zipfile
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                # Try to read the manifest
                zip_ref.read('META-INF/MANIFEST.MF')
            return True
        except Exception:
            return False
