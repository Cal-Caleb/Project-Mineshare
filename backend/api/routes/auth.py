from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.config import Settings, get_settings
from core.database import get_db
from core.security import create_access_token
from models import User, UserRole

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login(settings: Settings = Depends(get_settings)):
    """Redirect user to Discord OAuth2 consent screen.

    Discord will redirect back to DISCORD_REDIRECT_URI (/api/auth/callback).
    """
    url = (
        "https://discord.com/api/oauth2/authorize"
        f"?client_id={settings.discord_client_id}"
        f"&redirect_uri={settings.discord_redirect_uri}"
        "&response_type=code"
        "&scope=identify+guilds+guilds.members.read"
    )
    return RedirectResponse(url)


@router.get("/callback")
async def callback(
    code: str = Query(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Exchange Discord OAuth2 code, then redirect to frontend with JWT.

    Flow:
      1. Discord redirects here with ?code=...
      2. We exchange the code for a Discord access token
      3. We fetch user info + guild roles
      4. We upsert the user in our DB
      5. We issue our own JWT
      6. We redirect to the frontend at /auth/callback?token=<jwt>
    """
    async with httpx.AsyncClient() as client:
        # 1. Exchange code for Discord token
        token_resp = await client.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": settings.discord_client_id,
                "client_secret": settings.discord_client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.discord_redirect_uri,
                "scope": "identify guilds guilds.members.read",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_resp.status_code != 200:
            return _frontend_error(settings, "Failed to authenticate with Discord")

        tokens = token_resp.json()
        discord_token = tokens["access_token"]

        # 2. Get Discord user info
        user_resp = await client.get(
            "https://discord.com/api/v10/users/@me",
            headers={"Authorization": f"Bearer {discord_token}"},
        )
        if user_resp.status_code != 200:
            return _frontend_error(settings, "Failed to get Discord user info")

        discord_user = user_resp.json()
        discord_id = discord_user["id"]
        username = discord_user.get("global_name") or discord_user["username"]
        avatar = discord_user.get("avatar")

        # 3. Check guild membership and roles
        role = UserRole.GUEST
        if settings.discord_guild_id:
            member_resp = await client.get(
                f"https://discord.com/api/v10/users/@me/guilds/{settings.discord_guild_id}/member",
                headers={"Authorization": f"Bearer {discord_token}"},
            )
            if member_resp.status_code == 200:
                member = member_resp.json()
                member_roles = member.get("roles", [])
                if settings.discord_role2_id and settings.discord_role2_id in member_roles:
                    role = UserRole.ADMIN
                elif settings.discord_role1_id and settings.discord_role1_id in member_roles:
                    role = UserRole.MEMBER
            else:
                return _frontend_error(settings, "You are not a member of the server Discord")

    # 4. Upsert user
    db_user = db.query(User).filter(User.discord_id == discord_id).first()
    if db_user:
        db_user.discord_username = username
        db_user.discord_avatar = avatar
        db_user.role = role
    else:
        db_user = User(
            discord_id=discord_id,
            discord_username=username,
            discord_avatar=avatar,
            role=role,
        )
        db.add(db_user)

    db.commit()
    db.refresh(db_user)

    # 5. Issue our JWT
    jwt_token = create_access_token(db_user.id, discord_id, role.value)

    # 6. Redirect to frontend with token
    frontend = settings.frontend_url.rstrip("/")
    return RedirectResponse(f"{frontend}/auth/callback?token={jwt_token}")


def _frontend_error(settings: Settings, message: str) -> RedirectResponse:
    frontend = settings.frontend_url.rstrip("/")
    return RedirectResponse(f"{frontend}/auth/callback?error={urlencode({'m': message})}")
