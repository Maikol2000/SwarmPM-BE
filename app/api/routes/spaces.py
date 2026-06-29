from fastapi import APIRouter, Depends

from app.core.dependencies import require_scopes
from app.core.security import Principal
from app.services.spaces_service import list_categories

router = APIRouter(prefix="/api/spaces", tags=["DASH-04 spaces"])


@router.get("/categories")
def categories(_: Principal = Depends(require_scopes("spaces:read"))):
    return list_categories()
