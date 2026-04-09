import logging
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from core.config import get_settings
from core.server_manager import ServerManager
from models import AuditLog, EventSource, User, UserRole

logger = logging.getLogger(__name__)


class WhitelistManager:
    """Syncs Minecraft whitelist and OP status based on Discord roles.

    Rules:
    - Users with a Minecraft username AND role >= MEMBER get whitelisted
    - Users with role == ADMIN also get OP
    - When a user loses their role, whitelist/OP is revoked
    - Requires mc_username to be set before any whitelist actions
    """

    def __init__(self, server_manager: ServerManager):
        self.server = server_manager
        settings = get_settings()
        self.guild_id = settings.discord_guild_id
        self.role1_id = settings.discord_role1_id
        self.role2_id = settings.discord_role2_id
        self.bot_token = settings.discord_bot_token

    def set_minecraft_username(
        self, db: Session, user: User, mc_username: str
    ) -> User:
        """Set or update a user's Minecraft username and sync whitelist."""
        old_name = user.mc_username

        # Remove old whitelist/OP if changing username
        if old_name and old_name != mc_username:
            if user.is_whitelisted:
                self.server.whitelist_remove(old_name)
            if user.is_op:
                self.server.op_remove(old_name)

        user.mc_username = mc_username

        # Apply whitelist/OP based on current role
        self._sync_user(db, user)

        db.add(
            AuditLog(
                user_id=user.id,
                action="mc_username_set",
                details=f"Set MC username to '{mc_username}'"
                + (f" (was '{old_name}')" if old_name else ""),
                source=EventSource.WEB,
            )
        )
        db.commit()
        db.refresh(user)
        return user

    def sync_all_users(self, db: Session) -> dict:
        """Sync whitelist and OP for all users. Called by the 30-min loop."""
        users = db.query(User).filter(User.mc_username.isnot(None)).all()
        added = 0
        removed = 0
        opped = 0
        deopped = 0

        for user in users:
            changes = self._sync_user(db, user)
            added += changes.get("whitelisted", 0)
            removed += changes.get("unwhitelisted", 0)
            opped += changes.get("opped", 0)
            deopped += changes.get("deopped", 0)

        if added or removed or opped or deopped:
            db.commit()

        return {
            "whitelisted": added,
            "unwhitelisted": removed,
            "opped": opped,
            "deopped": deopped,
        }

    async def sync_roles_from_discord(self, db: Session) -> int:
        """Fetch current guild member roles from Discord and update DB.

        Returns the number of users whose roles changed.
        """
        if not self.bot_token or not self.guild_id:
            logger.warning("Bot token or guild ID not set, skipping role sync")
            return 0

        changed = 0
        users = db.query(User).all()

        async with httpx.AsyncClient() as client:
            for user in users:
                try:
                    resp = await client.get(
                        f"https://discord.com/api/v10/guilds/{self.guild_id}"
                        f"/members/{user.discord_id}",
                        headers={"Authorization": f"Bot {self.bot_token}"},
                    )
                    if resp.status_code == 404:
                        # User left the guild — revoke everything
                        if user.role != UserRole.MEMBER or user.is_whitelisted:
                            user.role = UserRole.MEMBER
                            user.is_whitelisted = False
                            user.is_op = False
                            if user.mc_username:
                                self.server.whitelist_remove(user.mc_username)
                                self.server.op_remove(user.mc_username)
                            changed += 1
                        continue

                    if resp.status_code != 200:
                        continue

                    member = resp.json()
                    roles = member.get("roles", [])

                    new_role = UserRole.MEMBER
                    if self.role2_id and self.role2_id in roles:
                        new_role = UserRole.ADMIN
                    elif self.role1_id and self.role1_id not in roles:
                        # No role1 = no access at all
                        new_role = UserRole.MEMBER

                    if user.role != new_role:
                        user.role = new_role
                        changed += 1

                except Exception:
                    logger.exception(
                        "Failed to sync roles for user %s", user.discord_id
                    )

        if changed:
            db.commit()
            # Re-sync whitelist/OP after role changes
            self.sync_all_users(db)

        return changed

    def _sync_user(self, db: Session, user: User) -> dict:
        """Ensure a single user's whitelist/OP matches their role."""
        changes: dict = {}
        if not user.mc_username:
            return changes

        should_whitelist = user.role in (UserRole.MEMBER, UserRole.ADMIN)
        should_op = user.role == UserRole.ADMIN

        if should_whitelist and not user.is_whitelisted:
            self.server.whitelist_add(user.mc_username)
            user.is_whitelisted = True
            changes["whitelisted"] = 1
        elif not should_whitelist and user.is_whitelisted:
            self.server.whitelist_remove(user.mc_username)
            user.is_whitelisted = False
            changes["unwhitelisted"] = 1

        if should_op and not user.is_op:
            self.server.op_add(user.mc_username)
            user.is_op = True
            changes["opped"] = 1
        elif not should_op and user.is_op:
            self.server.op_remove(user.mc_username)
            user.is_op = False
            changes["deopped"] = 1

        return changes
