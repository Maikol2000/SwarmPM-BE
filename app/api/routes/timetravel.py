from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import require_scopes
from app.core.security import Principal
from app.db.session import get_db
from app.schemas import SnapshotCreateResponse
from app.services.snapshot_service import snapshot_service

router = APIRouter(prefix="/api/state", tags=["TT-01 point-in-time"])


@router.post("/snapshot", response_model=SnapshotCreateResponse)
def create_snapshot(
    data: dict,
    _: Principal = Depends(require_scopes("state:write")),
    db: Session = Depends(get_db),
):
    snapshot = snapshot_service.create_snapshot(db=db, data=data)
    return SnapshotCreateResponse(snapshot_id=snapshot.snapshot_id, created_at=snapshot.created_at)


@router.get("/snapshot/{snapshot_id}")
def get_snapshot(
    snapshot_id: str,
    _: Principal = Depends(require_scopes("state:read")),
    db: Session = Depends(get_db),
):
    snapshot = snapshot_service.get_snapshot(db=db, snapshot_id=snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return snapshot
