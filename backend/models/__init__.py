import enum
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Enums ────────────────────────────────────────────────────────────────


class UserRole(str, enum.Enum):
    GUEST = "guest"
    MEMBER = "member"
    ADMIN = "admin"


class ModSource(str, enum.Enum):
    CURSEFORGE = "curseforge"
    UPLOAD = "upload"


class ModStatus(str, enum.Enum):
    ACTIVE = "active"
    PENDING_VOTE = "pending_vote"
    PENDING_APPROVAL = "pending_approval"
    REMOVED = "removed"


class VoteType(str, enum.Enum):
    ADD = "add"
    REMOVE = "remove"


class VoteStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    VETOED = "vetoed"
    FORCE_APPROVED = "force_approved"
    EXPIRED = "expired"


class UploadStatus(str, enum.Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


class EventSource(str, enum.Enum):
    WEB = "web"
    DISCORD = "discord"
    SYSTEM = "system"


class ServerEventType(str, enum.Enum):
    UPDATE_CHECK = "update_check"
    UPDATE_APPLIED = "update_applied"
    RESTART = "restart"
    BACKUP = "backup"
    ROLLBACK = "rollback"
    HEALTH_CHECK = "health_check"


class ServerEventStatus(str, enum.Enum):
    STARTED = "started"
    SUCCESS = "success"
    FAILED = "failed"


# ── Models ───────────────────────────────────────────────────────────────


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    discord_id: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    discord_username: Mapped[str] = mapped_column(String(100), nullable=False)
    discord_avatar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mc_username: Mapped[str | None] = mapped_column(
        String(16), nullable=True, unique=True
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.MEMBER, nullable=False
    )
    is_whitelisted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_op: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    mods_added: Mapped[list["Mod"]] = relationship(
        back_populates="added_by_user", foreign_keys="Mod.added_by_id"
    )
    votes_initiated: Mapped[list["Vote"]] = relationship(
        back_populates="initiated_by_user", foreign_keys="Vote.initiated_by_id"
    )
    ballots: Mapped[list["VoteBallot"]] = relationship(back_populates="user")
    uploads: Mapped[list["ModUpload"]] = relationship(
        back_populates="uploaded_by_user", foreign_keys="ModUpload.uploaded_by_id"
    )


class Mod(Base):
    __tablename__ = "mods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[ModSource] = mapped_column(Enum(ModSource), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    curse_project_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, unique=True
    )
    curse_file_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[ModStatus] = mapped_column(
        Enum(ModStatus), default=ModStatus.PENDING_VOTE, nullable=False
    )
    added_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    added_by_user: Mapped["User"] = relationship(
        back_populates="mods_added", foreign_keys=[added_by_id]
    )
    votes: Mapped[list["Vote"]] = relationship(back_populates="mod")
    uploads: Mapped[list["ModUpload"]] = relationship(back_populates="mod")


class Vote(Base):
    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mod_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("mods.id"), nullable=False
    )
    vote_type: Mapped[VoteType] = mapped_column(Enum(VoteType), nullable=False)
    initiated_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    status: Mapped[VoteStatus] = mapped_column(
        Enum(VoteStatus), default=VoteStatus.PENDING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    discord_message_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    discord_channel_id: Mapped[str | None] = mapped_column(String(20), nullable=True)

    mod: Mapped["Mod"] = relationship(back_populates="votes")
    initiated_by_user: Mapped["User"] = relationship(
        back_populates="votes_initiated", foreign_keys=[initiated_by_id]
    )
    resolved_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[resolved_by_id]
    )
    ballots: Mapped[list["VoteBallot"]] = relationship(
        back_populates="vote", cascade="all, delete-orphan"
    )


class VoteBallot(Base):
    __tablename__ = "vote_ballots"
    __table_args__ = (
        UniqueConstraint("vote_id", "user_id", name="uq_vote_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vote_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("votes.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    in_favor: Mapped[bool] = mapped_column(Boolean, nullable=False)
    cast_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    vote: Mapped["Vote"] = relationship(back_populates="ballots")
    user: Mapped["User"] = relationship(back_populates="ballots")


class ModUpload(Base):
    __tablename__ = "mod_uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mod_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("mods.id"), nullable=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    quarantine_path: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[UploadStatus] = mapped_column(
        Enum(UploadStatus), default=UploadStatus.PENDING_APPROVAL, nullable=False
    )
    scan_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    approved_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    discord_message_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    discord_channel_id: Mapped[str | None] = mapped_column(String(20), nullable=True)

    mod: Mapped["Mod | None"] = relationship(back_populates="uploads")
    uploaded_by_user: Mapped["User"] = relationship(
        back_populates="uploads", foreign_keys=[uploaded_by_id]
    )
    approved_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[approved_by_id]
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[EventSource] = mapped_column(Enum(EventSource), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    user: Mapped["User | None"] = relationship()


class ServerEvent(Base):
    __tablename__ = "server_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[ServerEventType] = mapped_column(
        Enum(ServerEventType), nullable=False
    )
    status: Mapped[ServerEventStatus] = mapped_column(
        Enum(ServerEventStatus), nullable=False
    )
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    backup_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    triggered_by_user: Mapped["User | None"] = relationship()
