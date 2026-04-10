import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from core.config import get_settings
from models import (
    AuditLog,
    EventSource,
    Mod,
    ModStatus,
    User,
    UserRole,
    Vote,
    VoteBallot,
    VoteStatus,
    VoteType,
)

logger = logging.getLogger(__name__)


class VoteManager:
    def __init__(self):
        settings = get_settings()
        self.duration_hours = settings.vote_duration_hours

    # ── Create ───────────────────────────────────────────────────────

    def create_vote(
        self,
        db: Session,
        mod: Mod,
        vote_type: VoteType,
        user: User,
        source: EventSource = EventSource.WEB,
    ) -> Vote:
        # Check for existing active vote on this mod
        existing = (
            db.query(Vote)
            .filter(
                Vote.mod_id == mod.id,
                Vote.status == VoteStatus.PENDING,
            )
            .first()
        )
        if existing:
            raise ValueError(f"An active vote already exists for '{mod.name}'")

        # Removal votes can only be started by the original adder or admin
        if vote_type == VoteType.REMOVE:
            if mod.added_by_id != user.id and user.role != UserRole.ADMIN:
                raise PermissionError(
                    "Only the original adder or an admin can initiate removal"
                )

        now = datetime.now(timezone.utc)
        vote = Vote(
            mod_id=mod.id,
            vote_type=vote_type,
            initiated_by_id=user.id,
            status=VoteStatus.PENDING,
            created_at=now,
            expires_at=now + timedelta(hours=self.duration_hours),
        )
        db.add(vote)
        db.add(
            AuditLog(
                user_id=user.id,
                action=f"vote_created_{vote_type.value}",
                details=f"Vote to {vote_type.value} '{mod.name}'",
                source=source,
            )
        )
        db.commit()
        db.refresh(vote)
        return vote

    # ── Cast ─────────────────────────────────────────────────────────

    def cast_vote(
        self,
        db: Session,
        vote: Vote,
        user: User,
        in_favor: bool,
        source: EventSource = EventSource.WEB,
    ) -> VoteBallot:
        if vote.status != VoteStatus.PENDING:
            raise ValueError("This vote is no longer active")

        expires_at = vote.expires_at.replace(tzinfo=timezone.utc) if vote.expires_at.tzinfo is None else vote.expires_at
        if datetime.now(timezone.utc) > expires_at:
            self._expire_vote(db, vote)
            raise ValueError("This vote has expired")

        # DB unique constraint prevents double-voting; catch it gracefully
        existing = (
            db.query(VoteBallot)
            .filter(VoteBallot.vote_id == vote.id, VoteBallot.user_id == user.id)
            .first()
        )
        if existing:
            if existing.in_favor == in_favor:
                raise ValueError("You have already voted this way")
            existing.in_favor = in_favor
            existing.cast_at = datetime.now(timezone.utc)
            db.add(
                AuditLog(
                    user_id=user.id,
                    action="vote_changed",
                    details=f"Changed to {'Yes' if in_favor else 'No'} on '{vote.mod.name}'",
                    source=source,
                )
            )
            db.commit()
            db.refresh(existing)
            return existing

        ballot = VoteBallot(
            vote_id=vote.id,
            user_id=user.id,
            in_favor=in_favor,
        )
        db.add(ballot)
        db.add(
            AuditLog(
                user_id=user.id,
                action="vote_cast",
                details=f"{'Yes' if in_favor else 'No'} on '{vote.mod.name}'",
                source=source,
            )
        )
        db.commit()
        db.refresh(ballot)
        return ballot

    # ── Admin Actions ────────────────────────────────────────────────

    def veto(
        self,
        db: Session,
        vote: Vote,
        admin: User,
        source: EventSource = EventSource.WEB,
    ) -> Vote:
        if admin.role != UserRole.ADMIN:
            raise PermissionError("Only admins can veto")
        if vote.status != VoteStatus.PENDING:
            raise ValueError("This vote is no longer active")

        vote.status = VoteStatus.VETOED
        vote.resolved_at = datetime.now(timezone.utc)
        vote.resolved_by_id = admin.id
        self._apply_rejection(db, vote)

        db.add(
            AuditLog(
                user_id=admin.id,
                action="vote_vetoed",
                details=f"Vetoed vote on '{vote.mod.name}'",
                source=source,
            )
        )
        db.commit()
        db.refresh(vote)
        return vote

    def force_pass(
        self,
        db: Session,
        vote: Vote,
        admin: User,
        source: EventSource = EventSource.WEB,
    ) -> Vote:
        if admin.role != UserRole.ADMIN:
            raise PermissionError("Only admins can force pass")
        if vote.status != VoteStatus.PENDING:
            raise ValueError("This vote is no longer active")

        vote.status = VoteStatus.FORCE_APPROVED
        vote.resolved_at = datetime.now(timezone.utc)
        vote.resolved_by_id = admin.id

        self._apply_result(db, vote)

        db.add(
            AuditLog(
                user_id=admin.id,
                action="vote_force_passed",
                details=f"Force-passed vote on '{vote.mod.name}'",
                source=source,
            )
        )
        db.commit()
        db.refresh(vote)
        return vote

    # ── Expiration ───────────────────────────────────────────────────

    def expire_stale_votes(self, db: Session) -> list[Vote]:
        """Find and expire all votes past their deadline."""
        now = datetime.now(timezone.utc)
        stale = (
            db.query(Vote)
            .filter(Vote.status == VoteStatus.PENDING, Vote.expires_at <= now)
            .all()
        )
        expired = []
        for vote in stale:
            self._expire_vote(db, vote)
            expired.append(vote)
        if expired:
            db.commit()
        return expired

    # ── Tallies ──────────────────────────────────────────────────────

    def get_tally(self, db: Session, vote: Vote) -> dict:
        yes = (
            db.query(func.count())
            .filter(VoteBallot.vote_id == vote.id, VoteBallot.in_favor.is_(True))
            .scalar()
        )
        no = (
            db.query(func.count())
            .filter(VoteBallot.vote_id == vote.id, VoteBallot.in_favor.is_(False))
            .scalar()
        )
        return {"yes": yes, "no": no, "total": yes + no}

    def get_active_votes(self, db: Session) -> list[Vote]:
        self.expire_stale_votes(db)
        return db.query(Vote).filter(Vote.status == VoteStatus.PENDING).all()

    # ── Internal ─────────────────────────────────────────────────────


    def _expire_vote(self, db: Session, vote: Vote) -> None:
        # On expiry: strict majority approves, otherwise rejected (ties = rejected)
        tally = self.get_tally(db, vote)
        if tally["total"] > 0 and tally["yes"] > tally["no"]:
            vote.status = VoteStatus.APPROVED
            self._apply_result(db, vote)
        else:
            vote.status = VoteStatus.REJECTED
            self._apply_rejection(db, vote)
        vote.resolved_at = datetime.now(timezone.utc)

    def _apply_result(self, db: Session, vote: Vote) -> None:
        """Apply the outcome of a successful vote to the mod."""
        mod = vote.mod
        if vote.vote_type == VoteType.ADD:
            mod.status = ModStatus.ACTIVE
        elif vote.vote_type == VoteType.REMOVE:
            mod.status = ModStatus.REMOVED

    def _apply_rejection(self, db: Session, vote: Vote) -> None:
        """Apply the outcome of a failed/vetoed vote to the mod."""
        mod = vote.mod
        if vote.vote_type == VoteType.ADD:
            mod.status = ModStatus.REMOVED
        # For removal votes that fail, mod stays ACTIVE (no change needed)
