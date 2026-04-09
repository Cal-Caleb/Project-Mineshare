from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps import get_current_user, get_whitelist_manager
from api.schemas import SetMinecraftUsername, UserOut
from core.database import get_db
from core.whitelist_manager import WhitelistManager
from models import User

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.put("/me/minecraft", response_model=UserOut)
async def set_minecraft_username(
    body: SetMinecraftUsername,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    wl: WhitelistManager = Depends(get_whitelist_manager),
):
    """Set or update your Minecraft username. Required before any server interaction."""
    # Check uniqueness
    existing = (
        db.query(User)
        .filter(User.mc_username == body.mc_username, User.id != user.id)
        .first()
    )
    if existing:
        raise HTTPException(409, "That Minecraft username is already claimed")

    updated = wl.set_minecraft_username(db, user, body.mc_username)
    return updated
