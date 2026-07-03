from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import require_roles, require_scopes
from app.core.security import Principal
from app.schemas import SpaceCategory, SpaceContent, SpaceDepartment, SpaceSubcategory, SpaceTrend
from app.services.spaces_service import get_space_content, list_categories, list_departments, list_subcategories, list_trending, refresh_cache

router = APIRouter(prefix="/api/spaces", tags=["DASH-04 spaces"])


@router.get("/categories", response_model=list[SpaceCategory])
def categories(_: Principal = Depends(require_scopes("spaces:read"))):
    return list_categories()


@router.get("/categories/{category_id}/subcategories", response_model=list[SpaceSubcategory])
def subcategories(category_id: str, _: Principal = Depends(require_scopes("spaces:read"))):
    category_subcategories = list_subcategories(category_id)
    if category_subcategories is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category_subcategories


@router.get("/content/{category_id}/{subcategory_id}", response_model=SpaceContent)
def content(category_id: str, subcategory_id: str, _: Principal = Depends(require_scopes("spaces:read"))):
    panel_content = get_space_content(category_id, subcategory_id)
    if panel_content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Space content not found")
    return panel_content


@router.get("/departments", response_model=list[SpaceDepartment])
def departments(_: Principal = Depends(require_scopes("spaces:read"))):
    return list_departments()


@router.get("/trending", response_model=list[SpaceTrend])
def trending(_: Principal = Depends(require_scopes("spaces:read"))):
    return list_trending()


@router.post("/admin/cache/refresh")
def admin_refresh_cache(_: Principal = Depends(require_roles("admin", "manager"))):
    return refresh_cache()
