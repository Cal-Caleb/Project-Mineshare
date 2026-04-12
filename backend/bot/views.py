"""Persistent Discord UI views for voting and approvals."""

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


class VoteView(discord.ui.View):
    """Persistent vote buttons attached to a vote embed."""

    def __init__(self, vote_id: int):
        super().__init__(timeout=None)
        self.vote_id = vote_id

    @discord.ui.button(
        label="Vote Yes",
        style=discord.ButtonStyle.success,
        custom_id="vote_yes",
        emoji="\u2705",
    )
    async def vote_yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_vote(interaction, in_favor=True)

    @discord.ui.button(
        label="Vote No",
        style=discord.ButtonStyle.danger,
        custom_id="vote_no",
        emoji="\u274c",
    )
    async def vote_no(self, interaction: discord.Interaction, button: discord.ui.Button):
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
                    "Set your Minecraft username first (`/setmc`).", ephemeral=True
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

    @discord.ui.button(
        label="Veto",
        style=discord.ButtonStyle.secondary,
        custom_id="vote_admin_veto",
        emoji="\U0001f6ab",
        row=1,
    )
    async def admin_veto(self, interaction: discord.Interaction, button: discord.ui.Button):
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

    @discord.ui.button(
        label="Force Pass",
        style=discord.ButtonStyle.secondary,
        custom_id="vote_admin_force_pass",
        emoji="\u26a1",
        row=1,
    )
    async def admin_force_pass(self, interaction: discord.Interaction, button: discord.ui.Button):
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

class AdminVoteView(discord.ui.View):
    """Admin-only buttons for veto/force-pass — kept for backwards compat."""

    def __init__(self, vote_id: int):
        super().__init__(timeout=None)
        self.vote_id = vote_id

    @discord.ui.button(
        label="Veto",
        style=discord.ButtonStyle.danger,
        custom_id="admin_veto",
        emoji="\U0001f6ab",
    )
    async def veto(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = SessionLocal()
        try:
            user = _get_user(db, interaction.user.id)
            if not user or user.role != UserRole.ADMIN:
                await interaction.response.send_message(
                    "Admin access required.", ephemeral=True
                )
                return

            vote = db.query(Vote).filter(Vote.id == self.vote_id).first()
            if not vote:
                await interaction.response.send_message("Vote not found.", ephemeral=True)
                return

            mgr = VoteManager()
            try:
                mgr.veto(db, vote, user, source=EventSource.DISCORD)
            except (ValueError, PermissionError) as e:
                await interaction.response.send_message(str(e), ephemeral=True)
                return

            await interaction.response.send_message(
                f"\U0001f6ab **{interaction.user.display_name}** vetoed the vote on **{vote.mod.name}**!"
            )
        finally:
            db.close()

    @discord.ui.button(
        label="Force Pass",
        style=discord.ButtonStyle.primary,
        custom_id="admin_force_pass",
        emoji="\u26a1",
    )
    async def force_pass(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = SessionLocal()
        try:
            user = _get_user(db, interaction.user.id)
            if not user or user.role != UserRole.ADMIN:
                await interaction.response.send_message(
                    "Admin access required.", ephemeral=True
                )
                return

            vote = db.query(Vote).filter(Vote.id == self.vote_id).first()
            if not vote:
                await interaction.response.send_message("Vote not found.", ephemeral=True)
                return

            mgr = VoteManager()
            try:
                mgr.force_pass(db, vote, user, source=EventSource.DISCORD)
            except (ValueError, PermissionError) as e:
                await interaction.response.send_message(str(e), ephemeral=True)
                return

            await interaction.response.send_message(
                f"\u26a1 **{interaction.user.display_name}** force-passed the vote on **{vote.mod.name}**!"
            )
        finally:
            db.close()


class UploadApprovalView(discord.ui.View):
    """Admin approval/rejection buttons for uploaded mods."""

    def __init__(self, upload_id: int):
        super().__init__(timeout=None)
        self.upload_id = upload_id

    @discord.ui.button(
        label="Approve",
        style=discord.ButtonStyle.success,
        custom_id="upload_approve",
    )
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
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

    @discord.ui.button(
        label="Reject",
        style=discord.ButtonStyle.danger,
        custom_id="upload_reject",
    )
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
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
