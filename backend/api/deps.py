"""FastAPI dependencies for auth, DB sessions, and service managers."""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from core.config import get_settings
from core.database import get_db
from core.mod_manager import ModManager
from core.security import verify_access_token
from core.server_manager import ServerManager
from core.upload_manager import UploadManager
from core.vote_manager import VoteManager
from core.whitelist_manager import WhitelistManager
from models import User, UserRole

security = HTTPBearer(auto_error=False)


def get_current_user(
    db: Session = Depends(get_db),
    creds: HTTPAuthorizationCredentials | None = Depends(security),
) -> User:
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    payload = verify_access_token(creds.credentials)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


def require_mc_username(user: User = Depends(get_current_user)) -> User:
    """Require that the user has set their Minecraft username."""
    if not user.mc_username:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You must set your Minecraft username before performing this action",
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return user


def get_mod_manager() -> ModManager:
    return ModManager()


def get_vote_manager() -> VoteManager:
    return VoteManager()


def get_server_manager() -> ServerManager:
    return ServerManager()


def get_upload_manager() -> UploadManager:
    return UploadManager()


def get_whitelist_manager(
    server: ServerManager = Depends(get_server_manager),
) -> WhitelistManager:
    return WhitelistManager(server)
