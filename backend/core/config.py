from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/modserver"

    # Discord
    discord_client_id: str = ""
    discord_client_secret: str = ""
    discord_bot_token: str = ""
    discord_guild_id: str = ""
    discord_role1_id: str = ""  # Member role ID
    discord_role2_id: str = ""  # Admin role ID
    discord_redirect_uri: str = "http://localhost:8000/api/auth/callback"

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_expire_minutes: int = 1440  # 24 hours

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Minecraft Server
    server_path: str = "/opt/minecraft/server"
    backup_path: str = "/opt/minecraft/backups"
    rcon_host: str = "localhost"
    rcon_port: int = 25575
    rcon_password: str = ""
    server_systemd_unit: str = "minecraft-server"

    # CurseForge
    curseforge_api_key: str = ""
    minecraft_game_id: int = 432
    minecraft_version: str = ""  # e.g. "1.21.5" — auto-detected from server if empty
    neoforge_loader_type: int = 6  # NeoForge modloader type for CF API

    # Uploads
    upload_dir: str = "/opt/minecraft/uploads"
    quarantine_dir: str = "/opt/minecraft/quarantine"
    mod_cache_dir: str = "/opt/minecraft/mod_cache"
    max_upload_size: int = 52428800  # 50MB

    # Voting
    vote_duration_hours: int = 12

    # Update loop
    update_interval_minutes: int = 30
    restart_warning_seconds: int = 60

    # Frontend
    frontend_url: str = "http://localhost:3000"

    # Discord channels
    channel_active_votes: str = ""
    channel_mod_proposals: str = ""
    channel_mod_uploads: str = ""
    channel_server_status: str = ""
    channel_mod_updates: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
