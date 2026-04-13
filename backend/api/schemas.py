from datetime import datetime

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
    discord_avatar: str | None = None
    mc_username: str | None = None
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
    logo_url: str | None = None
    latest_file_name: str | None = None
    download_count: int
    supports_neoforge: bool = False
    game_versions: list[str] = []


class AddCurseForgeMod(BaseModel):
    url: str
    force: bool = False


class ModOut(BaseModel):
    id: int
    name: str
    slug: str | None = None
    description: str | None = None
    author: str | None = None
    source: str
    source_url: str | None = None
    curse_project_id: int | None = None
    current_version: str | None = None
    file_name: str | None = None
    status: str
    download_count: int
    added_by: UserOut | None = None
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
    initiated_by: UserOut | None = None
    status: str
    created_at: datetime
    expires_at: datetime
    resolved_at: datetime | None = None
    tally: VoteTally | None = None
    ballots: list[BallotOut] = []

    model_config = {"from_attributes": True}


# ── Uploads ──────────────────────────────────────────────────────────


class ApproveUpload(BaseModel):
    mod_name: str | None = Field(None, min_length=1, max_length=255)


class RejectUpload(BaseModel):
    reason: str = ""


class UploadOut(BaseModel):
    id: int
    original_filename: str
    file_hash: str
    file_size: int
    status: str
    scan_result: str | None = None
    mod_id: int | None = None
    uploaded_by: UserOut | None = None
    approved_by: UserOut | None = None
    created_at: datetime
    resolved_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Audit ────────────────────────────────────────────────────────────


class AuditLogOut(BaseModel):
    id: int
    user: UserOut | None = None
    action: str
    details: str | None = None
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
    details: str | None = None
    backup_path: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Uptime / Status History ──────────────────────────────────────────


class UptimeBucket(BaseModel):
    bucket: datetime
    online: bool | None = None
    player_count: int = 0


class UptimeStats(BaseModel):
    uptime_pct: float
    buckets: list[UptimeBucket]
    peak_players: int
    avg_players: float
    world_size_mb: float | None = None


# ── Mod Updates ─────────────────────────────────────────────────────


class ModUpdateOut(BaseModel):
    id: int
    mod_id: int
    mod_name: str
    mod_slug: str | None = None
    old_version: str | None = None
    new_version: str | None = None
    changelog: str | None = None
    source_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Mod Export ──────────────────────────────────────────────────────


class ModExportEntry(BaseModel):
    name: str
    author: str | None = None
    source: str
    curse_project_id: int | None = None
    file_name: str | None = None
    source_url: str | None = None
    current_version: str | None = None


class ModExportOut(BaseModel):
    name: str = "MineShare Modpack"
    mod_count: int
    mods: list[ModExportEntry]


# Rebuild forward refs
TokenResponse.model_rebuild()
