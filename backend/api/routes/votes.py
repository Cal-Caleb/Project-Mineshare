from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps import (
    get_current_user,
    get_vote_manager,
    require_admin,
    require_mc_username,
)
from api.schemas import BallotOut, CastBallot, UserOut, VoteOut, VoteTally
from core.database import get_db
from core.vote_manager import VoteManager
from models import EventSource, User, Vote, VoteStatus

router = APIRouter(prefix="/votes", tags=["votes"])


@router.get("", response_model=list[VoteOut])
async def list_active_votes(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
    vote_mgr: VoteManager = Depends(get_vote_manager),
):
    votes = vote_mgr.get_active_votes(db)
    return [_vote_to_out(db, v, vote_mgr) for v in votes]


@router.get("/history", response_model=list[VoteOut])
async def vote_history(
    limit: int = 20,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
    vote_mgr: VoteManager = Depends(get_vote_manager),
):
    votes = (
        db.query(Vote)
        .filter(Vote.status != VoteStatus.PENDING)
        .order_by(Vote.resolved_at.desc())
        .limit(limit)
        .all()
    )
    return [_vote_to_out(db, v, vote_mgr) for v in votes]


@router.get("/{vote_id}", response_model=VoteOut)
async def get_vote(
    vote_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
    vote_mgr: VoteManager = Depends(get_vote_manager),
):
    vote = db.query(Vote).filter(Vote.id == vote_id).first()
    if not vote:
        raise HTTPException(404, "Vote not found")
    return _vote_to_out(db, vote, vote_mgr)


@router.post("/{vote_id}/cast", response_model=VoteOut)
async def cast_ballot(
    vote_id: int,
    body: CastBallot,
    db: Session = Depends(get_db),
    user: User = Depends(require_mc_username),
    vote_mgr: VoteManager = Depends(get_vote_manager),
):
    vote = db.query(Vote).filter(Vote.id == vote_id).first()
    if not vote:
        raise HTTPException(404, "Vote not found")

    try:
        vote_mgr.cast_vote(db, vote, user, body.in_favor)
    except ValueError as e:
        raise HTTPException(400, str(e))

    return _vote_to_out(db, vote, vote_mgr)


@router.post("/{vote_id}/veto", response_model=VoteOut)
async def veto_vote(
    vote_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    vote_mgr: VoteManager = Depends(get_vote_manager),
):
    vote = db.query(Vote).filter(Vote.id == vote_id).first()
    if not vote:
        raise HTTPException(404, "Vote not found")

    try:
        vote_mgr.veto(db, vote, admin)
    except (ValueError, PermissionError) as e:
        raise HTTPException(400, str(e))

    return _vote_to_out(db, vote, vote_mgr)


@router.post("/{vote_id}/force-pass", response_model=VoteOut)
async def force_pass_vote(
    vote_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    vote_mgr: VoteManager = Depends(get_vote_manager),
):
    vote = db.query(Vote).filter(Vote.id == vote_id).first()
    if not vote:
        raise HTTPException(404, "Vote not found")

    try:
        vote_mgr.force_pass(db, vote, admin)
    except (ValueError, PermissionError) as e:
        raise HTTPException(400, str(e))

    return _vote_to_out(db, vote, vote_mgr)


def _vote_to_out(db: Session, vote: Vote, vote_mgr: VoteManager) -> VoteOut:
    tally = vote_mgr.get_tally(db, vote)
    ballots = [
        BallotOut(
            id=b.id,
            user=UserOut.model_validate(b.user),
            in_favor=b.in_favor,
            cast_at=b.cast_at,
        )
        for b in vote.ballots
    ]
    return VoteOut(
        id=vote.id,
        mod=vote.mod,
        vote_type=vote.vote_type.value,
        initiated_by=UserOut.model_validate(vote.initiated_by_user)
        if vote.initiated_by_user
        else None,
        status=vote.status.value,
        created_at=vote.created_at,
        expires_at=vote.expires_at,
        resolved_at=vote.resolved_at,
        tally=VoteTally(**tally),
        ballots=ballots,
    )
