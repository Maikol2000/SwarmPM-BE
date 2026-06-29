from fastapi import APIRouter

from app.core.security import create_access_token
from app.schemas import AuthTokenRequest, AuthTokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/token", response_model=AuthTokenResponse)
def issue_token(payload: AuthTokenRequest) -> AuthTokenResponse:
    access_token, expires_at = create_access_token(
        subject=payload.user_id,
        role=payload.role,
        scopes=payload.scopes,
    )
    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_at=expires_at,
        user_id=payload.user_id,
        role=payload.role,
        scopes=payload.scopes,
    )
