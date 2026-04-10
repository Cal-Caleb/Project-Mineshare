from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Auth ─────────────────────────────────────────────────────────────


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


# ── Users ────────────────────────────────────────────────────────────


class SetMinecraftUsername(BaseModel):
    mc_username: str = Field(..., min_length=3, max_length=16, pattern=r"^[a-zA-Z0-9_]+$")


class UserOut(BaseModel):
    id: int
    discord_id: str
    discord_username: str
    discord_avatar: Optional[str] = None
    mc_username: Optional[str] = None
    role: str
    is_whitelisted: bool
    is_op: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Mods ─────────────────────────────────────────────────────────────


class CurseForgePreview(BaseModel):
    project_id: int
    name: str
    slug: str
    summary: str
    author: str
    logo_url: Optional[str] = None
    latest_file_name: Optional[str] = None
    download_count: int


class AddCurseForgeMod(BaseModel):
    url: str
    force: bool = False


class ModOut(BaseModel):
    id: int
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    source: str
    source_url: Optional[str] = None
    curse_project_id: Optional[int] = None
    current_version: Optional[str] = None
    file_name: Optional[str] = None
    status: str
    download_count: int
    added_by: Optional[UserOut] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Votes ────────────────────────────────────────────────────────────


class CreateVote(BaseModel):
    mod_id: int
    vote_type: str = Field(..., pattern=r"^(add|remove)$")


class CastBallot(BaseModel):
    in_favor: bool


class VoteTally(BaseModel):
    yes: int
    no: int
    total: int


class BallotOut(BaseModel):
    id: int
    user: UserOut
    in_favor: bool
    cast_at: datetime

    model_config = {"from_attributes": True}


class VoteOut(BaseModel):
    id: int
    mod: ModOut
    vote_type: str
    initiated_by: Optional[UserOut] = None
    status: str
    created_at: datetime
    expires_at: datetime
    resolved_at: Optional[datetime] = None
    tally: Optional[VoteTally] = None
    ballots: list[BallotOut] = []

    model_config = {"from_attributes": True}


# ── Uploads ──────────────────────────────────────────────────────────


class ApproveUpload(BaseModel):
    mod_name: str = Field(..., min_length=1, max_length=255)


class RejectUpload(BaseModel):
    reason: str = ""


class UploadOut(BaseModel):
    id: int
    original_filename: str
    file_hash: str
    file_size: int
    status: str
    scan_result: Optional[str] = None
    uploaded_by: Optional[UserOut] = None
    approved_by: Optional[UserOut] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Audit ────────────────────────────────────────────────────────────


class AuditLogOut(BaseModel):
    id: int
    user: Optional[UserOut] = None
    action: str
    details: Optional[str] = None
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Server ───────────────────────────────────────────────────────────


class ServerStatus(BaseModel):
    online: bool
    players: list[str]
    player_count: int


class ServerEventOut(BaseModel):
    id: int
    event_type: str
    status: str
    details: Optional[str] = None
    backup_path: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# Rebuild forward refs
TokenResponse.model_rebuild()
