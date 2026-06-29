from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_scopes
from app.core.security import Principal
from app.db.session import get_db
from app.services.chat_service import chat_service
from app.services.spaces_service import list_categories

router = APIRouter(prefix="/api/dashboard", tags=["DASH-07 dashboard"])


@router.get("/unified")
def unified_dashboard(
    user_id: str,
    principal: Principal = Depends(require_scopes("dashboard:read")),
    db: Session = Depends(get_db),
):
    if user_id != principal.sub and principal.role != "admin" and "admin:all" not in principal.scopes:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access another user dashboard")

    return {
        "user_id": user_id,
        "spaces": list_categories(),
        "presence": chat_service.get_presence(),
        "unread": chat_service.unread_counts(db=db, user_id=user_id),
        "status": "ok",
    }
