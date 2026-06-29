from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, WebSocketException, status
from jwt import InvalidTokenError
from pydantic import BaseModel, Field

from app.core.config import get_settings


class Principal(BaseModel):
    sub: str
    role: str = "member"
    scopes: set[str] = Field(default_factory=set)


def _legacy_principal() -> Principal:
    return Principal(
        sub="dev-user",
        role="admin",
        scopes={
            "chat:read",
            "chat:write",
            "spaces:read",
            "dashboard:read",
            "team:write",
            "aura:use",
            "state:read",
            "state:write",
            "admin:all",
        },
    )


def create_access_token(subject: str, role: str, scopes: list[str]) -> tuple[str, datetime]:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": subject,
        "role": role,
        "scopes": scopes,
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_at


def authenticate_bearer_token(token: str) -> Principal:
    settings = get_settings()

    if settings.allow_legacy_dev_token and token == "dev-token":
        return _legacy_principal()

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject")

    role = payload.get("role", "member")
    scopes = payload.get("scopes", [])
    if not isinstance(scopes, list):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token scopes must be a list")

    return Principal(sub=subject, role=role, scopes=set(scopes))


def authorize_websocket_token(token: str | None) -> Principal:
    if not token:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Missing websocket token")

    try:
        return authenticate_bearer_token(token)
    except HTTPException as exc:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason=exc.detail) from exc
