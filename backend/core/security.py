from datetime import UTC, datetime, timedelta

import jwt

from core.config import get_settings


def create_access_token(user_id: int, discord_id: str, role: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user_id),
        "discord_id": discord_id,
        "role": role,
        "exp": expire,
        "iat": now,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def verify_access_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
