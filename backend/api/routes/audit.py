from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import get_current_user
from api.schemas import AuditLogOut, UserOut
from core.database import get_db
from models import AuditLog, User

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
async def get_audit_log(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    action: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    logs = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    return [
        AuditLogOut(
            id=log.id,
            user=UserOut.model_validate(log.user) if log.user else None,
            action=log.action,
            details=log.details,
            source=log.source.value,
            created_at=log.created_at,
        )
        for log in logs
    ]
