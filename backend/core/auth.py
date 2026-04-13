"""Discord OAuth2 helpers — used by the auth route.

Most auth logic lives in api/routes/auth.py and core/security.py.
This module is kept for any shared OAuth utilities.
"""

from core.config import get_settings


def get_oauth_url() -> str:
    settings = get_settings()
    return (
        "https://discord.com/api/oauth2/authorize"
        f"?client_id={settings.discord_client_id}"
        f"&redirect_uri={settings.discord_redirect_uri}"
        "&response_type=code"
        "&scope=identify+guilds+guilds.members.read"
    )
