"""Persistent Discord UI views for voting and approvals.

Every view uses dynamic custom_ids that include the entity ID
(e.g. "vote_yes:42") so that discord.py can route button presses
to the correct handler even after a bot restart.
"""

import discord

from core.database import SessionLocal
from core.vote_manager import VoteManager
from core.upload_manager import UploadManager
from models import (
    EventSource,
    ModUpload,
    User,
    UserRole,
    Vote,
)


def _get_user(db, discord_id: str) -> User | None:
    return db.query(User).filter(User.discord_id == str(discord_id)).first()


# ── Vote View ────────────────────────────────────────────────────────


class VoteView(discord.ui.View):
    """Persistent vote buttons attached to a vote embed.

    Each button's custom_id includes the vote ID so multiple VoteViews
    can coexist and survive bot restarts.
    """

    def __init__(self, vote_id: int):
        super().__init__(timeout=None)
        self.vote_id = vote_id

        # Row 0 — member buttons
        yes_btn = discord.ui.Button(
            label="Vote Yes",
            style=discord.ButtonStyle.success,
            custom_id=f"vote_yes:{vote_id}",
            emoji="\u2705",
            row=0,
        )
        yes_btn.callback = self._vote_yes
        self.add_item(yes_btn)

        no_btn = discord.ui.Button(
            label="Vote No",
            style=discord.ButtonStyle.danger,
            custom_id=f"vote_no:{vote_id}",
            emoji="\u274c",
            row=0,
        )
        no_btn.callback = self._vote_no
        self.add_item(no_btn)

        # Row 1 — admin buttons
        veto_btn = discord.ui.Button(
            label="Veto",
            style=discord.ButtonStyle.secondary,
            custom_id=f"vote_veto:{vote_id}",
            emoji="\U0001f6ab",
            row=1,
        )
        veto_btn.callback = self._admin_veto
        self.add_item(veto_btn)

        force_btn = discord.ui.Button(
            label="Force Pass",
            style=discord.ButtonStyle.secondary,
            custom_id=f"vote_force:{vote_id}",
            emoji="\u26a1",
            row=1,
        )
        force_btn.callback = self._admin_force_pass
        self.add_item(force_btn)

    async def _vote_yes(self, interaction: discord.Interaction):
        await self._handle_vote(interaction, in_favor=True)

    async def _vote_no(self, interaction: discord.Interaction):
        await self._handle_vote(interaction, in_favor=False)

    async def _handle_vote(self, interaction: discord.Interaction, in_favor: bool):
        db = SessionLocal()
        try:
            user = _get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message(
                    "You need to register on the web app first.", ephemeral=True
                )
                return
            if not user.mc_username:
                await interaction.response.send_message(
                    "Set your Minecraft username first.", ephemeral=True
                )
                return

            vote = db.query(Vote).filter(Vote.id == self.vote_id).first()
            if not vote:
                await interaction.response.send_message(
                    "Vote not found.", ephemeral=True
                )
                return

            mgr = VoteManager()
            try:
                mgr.cast_vote(db, vote, user, in_favor, source=EventSource.DISCORD)
            except ValueError as e:
                await interaction.response.send_message(str(e), ephemeral=True)
                return

            tally = mgr.get_tally(db, vote)
            label = "Yes" if in_favor else "No"
            await interaction.response.send_message(
                f"**{interaction.user.display_name}** voted **{label}**! "
                f"(Yes: {tally['yes']} / No: {tally['no']})",
                ephemeral=True,
            )
        finally:
            db.close()

    async def _admin_veto(self, interaction: discord.Interaction):
        db = SessionLocal()
        try:
            user = _get_user(db, interaction.user.id)
            if not user or user.role != UserRole.ADMIN:
                await interaction.response.send_message(
                    "Admin only.", ephemeral=True
                )
                return
            vote = db.query(Vote).filter(Vote.id == self.vote_id).first()
            if not vote:
                await interaction.response.send_message("Vote not found.", ephemeral=True)
                return
            try:
                VoteManager().veto(db, vote, user, source=EventSource.DISCORD)
            except (ValueError, PermissionError) as e:
                await interaction.response.send_message(str(e), ephemeral=True)
                return
            await interaction.response.send_message(
                f"\U0001f6ab Vote on **{vote.mod.name}** vetoed.", ephemeral=True
            )
        finally:
            db.close()

    async def _admin_force_pass(self, interaction: discord.Interaction):
        db = SessionLocal()
        try:
            user = _get_user(db, interaction.user.id)
            if not user or user.role != UserRole.ADMIN:
                await interaction.response.send_message(
                    "Admin only.", ephemeral=True
                )
                return
            vote = db.query(Vote).filter(Vote.id == self.vote_id).first()
            if not vote:
                await interaction.response.send_message("Vote not found.", ephemeral=True)
                return
            try:
                VoteManager().force_pass(db, vote, user, source=EventSource.DISCORD)
            except (ValueError, PermissionError) as e:
                await interaction.response.send_message(str(e), ephemeral=True)
                return
            await interaction.response.send_message(
                f"\u26a1 Vote on **{vote.mod.name}** force-passed.", ephemeral=True
            )
        finally:
            db.close()


# ── Remove Mod View ──────────────────────────────────────────────────


class RemoveModView(discord.ui.View):
    """Button on a mod-list card to start a removal vote."""

    def __init__(self, mod_id: int):
        super().__init__(timeout=None)
        self.mod_id = mod_id

        btn = discord.ui.Button(
            label="Vote to Remove",
            style=discord.ButtonStyle.danger,
            custom_id=f"mod_remove:{mod_id}",
            emoji="\U0001f5d1",
        )
        btn.callback = self._vote_remove
        self.add_item(btn)

    async def _vote_remove(self, interaction: discord.Interaction):
        from models import Mod, ModStatus, VoteType

        db = SessionLocal()
        try:
            user = _get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message(
                    "Register on the web app first.", ephemeral=True
                )
                return
            if not user.mc_username:
                await interaction.response.send_message(
                    "Set your Minecraft username first.",
                    ephemeral=True,
                )
                return

            mod = db.query(Mod).filter(Mod.id == self.mod_id).first()
            if not mod or mod.status != ModStatus.ACTIVE:
                await interaction.response.send_message(
                    "Mod not found or already removed.", ephemeral=True
                )
                return

            mgr = VoteManager()
            try:
                mgr.create_vote(
                    db,
                    mod,
                    VoteType.REMOVE,
                    user,
                    source=EventSource.DISCORD,
                )
            except (ValueError, PermissionError) as e:
                await interaction.response.send_message(str(e), ephemeral=True)
                return

            await interaction.response.send_message(
                f"\U0001f5f3\ufe0f Removal vote started for **{mod.name}** — check the votes channel.",
                ephemeral=True,
            )
        finally:
            db.close()


# ── Upload Approval View ─────────────────────────────────────────────


class UploadApprovalView(discord.ui.View):
    """Admin approval/rejection buttons for uploaded mods."""

    def __init__(self, upload_id: int):
        super().__init__(timeout=None)
        self.upload_id = upload_id

        approve_btn = discord.ui.Button(
            label="Approve",
            style=discord.ButtonStyle.success,
            custom_id=f"upload_approve:{upload_id}",
        )
        approve_btn.callback = self._approve
        self.add_item(approve_btn)

        reject_btn = discord.ui.Button(
            label="Reject",
            style=discord.ButtonStyle.danger,
            custom_id=f"upload_reject:{upload_id}",
        )
        reject_btn.callback = self._reject
        self.add_item(reject_btn)

    async def _approve(self, interaction: discord.Interaction):
        db = SessionLocal()
        try:
            user = _get_user(db, interaction.user.id)
            if not user or user.role != UserRole.ADMIN:
                await interaction.response.send_message(
                    "Admin access required.", ephemeral=True
                )
                return

            upload = db.query(ModUpload).filter(ModUpload.id == self.upload_id).first()
            if not upload:
                await interaction.response.send_message(
                    "Upload not found.", ephemeral=True
                )
                return

            # Updates skip the name prompt and the vote.
            if upload.mod_id is not None:
                mgr = UploadManager()
                try:
                    mgr.approve_mod_update(db, upload, user)
                except (ValueError, PermissionError) as e:
                    await interaction.response.send_message(str(e), ephemeral=True)
                    return
                await interaction.response.send_message(
                    f"\u2705 Update **{upload.original_filename}** approved."
                )
            else:
                # New mods still need an admin-chosen display name
                await interaction.response.send_modal(
                    UploadApproveModal(self.upload_id)
                )
        finally:
            db.close()

    async def _reject(self, interaction: discord.Interaction):
        db = SessionLocal()
        try:
            user = _get_user(db, interaction.user.id)
            if not user or user.role != UserRole.ADMIN:
                await interaction.response.send_message(
                    "Admin access required.", ephemeral=True
                )
                return

            upload = db.query(ModUpload).filter(ModUpload.id == self.upload_id).first()
            if not upload:
                await interaction.response.send_message("Upload not found.", ephemeral=True)
                return

            mgr = UploadManager()
            mgr.reject_upload(db, upload, user, reason="Rejected via Discord")
            await interaction.response.send_message(
                f"\u274c Upload **{upload.original_filename}** rejected."
            )
        finally:
            db.close()


class UploadApproveModal(discord.ui.Modal, title="Approve Upload"):
    mod_name = discord.ui.TextInput(
        label="Mod Name",
        placeholder="Enter the display name for this mod",
        required=True,
        max_length=255,
    )

    def __init__(self, upload_id: int):
        super().__init__()
        self.upload_id = upload_id

    async def on_submit(self, interaction: discord.Interaction):
        db = SessionLocal()
        try:
            user = _get_user(db, interaction.user.id)
            if not user or user.role != UserRole.ADMIN:
                await interaction.response.send_message(
                    "Admin access required.", ephemeral=True
                )
                return

            upload = db.query(ModUpload).filter(ModUpload.id == self.upload_id).first()
            if not upload:
                await interaction.response.send_message("Upload not found.", ephemeral=True)
                return

            mgr = UploadManager()
            try:
                mgr.approve_upload(db, upload, user, self.mod_name.value)
            except (ValueError, PermissionError) as e:
                await interaction.response.send_message(str(e), ephemeral=True)
                return

            await interaction.response.send_message(
                f"\u2705 Upload **{upload.original_filename}** approved as **{self.mod_name.value}**!"
            )
        finally:
            db.close()


# Keep for backwards compat — old messages might reference these custom_ids
class AdminVoteView(discord.ui.View):
    """Legacy view — no longer used for new messages."""

    def __init__(self, vote_id: int):
        super().__init__(timeout=None)
        self.vote_id = vote_id
