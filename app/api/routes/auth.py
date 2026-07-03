from fastapi import APIRouter

from app.core.security import create_access_token, create_service_token
from app.schemas import AuthServiceTokenRequest, AuthServiceTokenResponse, AuthTokenRequest, AuthTokenResponse

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


@router.post("/service-token", response_model=AuthServiceTokenResponse)
def issue_service_token(payload: AuthServiceTokenRequest) -> AuthServiceTokenResponse:
    access_token, expires_at = create_service_token(
        service_id=payload.service_id,
        scopes=payload.scopes,
    )
    return AuthServiceTokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_at=expires_at,
        service_id=payload.service_id,
        scopes=payload.scopes,
    )
