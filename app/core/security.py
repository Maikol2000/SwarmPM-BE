from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, WebSocketException, status
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from app.core.config import get_settings


class Principal(BaseModel):
    sub: str
    role: str = "member"
    scopes: set[str] = Field(default_factory=set)


class ServicePrincipal(BaseModel):
    service_id: str
    scopes: set[str] = Field(default_factory=set)


def _normalize_scopes(scopes: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for scope in scopes:
        if not isinstance(scope, str):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token scopes must be strings")
        value = scope.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


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
    normalized_scopes = _normalize_scopes(scopes)
    payload = {
        "sub": subject,
        "role": role,
        "scopes": normalized_scopes,
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_at


def create_service_token(service_id: str, scopes: list[str]) -> tuple[str, datetime]:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.service_token_expire_minutes)
    normalized_scopes = _normalize_scopes(scopes)
    payload = {
        "sub": service_id,
        "token_type": "service",
        "scopes": normalized_scopes,
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_at


def _decode_token(token: str) -> dict:
    settings = get_settings()
    decode_kwargs: dict = {
        "key": settings.jwt_secret,
        "algorithms": [settings.jwt_algorithm],
    }
    if settings.oidc_audience:
        decode_kwargs["audience"] = settings.oidc_audience
    if settings.oidc_issuer:
        decode_kwargs["issuer"] = settings.oidc_issuer

    return jwt.decode(token, **decode_kwargs)


def authenticate_bearer_token(token: str) -> Principal:
    settings = get_settings()

    if settings.allow_legacy_dev_token and token == "dev-token":
        return _legacy_principal()

    try:
        payload = _decode_token(token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject")

    role = payload.get("role", "member")
    scopes = payload.get("scopes", [])
    if not isinstance(scopes, list):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token scopes must be a list")

    normalized_scopes = _normalize_scopes(scopes)
    return Principal(sub=subject, role=role, scopes=set(normalized_scopes))


def authenticate_service_token(token: str) -> ServicePrincipal:
    try:
        payload = _decode_token(token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid service token") from exc

    token_type = payload.get("token_type")
    if token_type != "service":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid service token type")

    service_id = payload.get("sub")
    if not service_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Service token missing subject")

    scopes = payload.get("scopes", [])
    if not isinstance(scopes, list):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Service token scopes must be a list")

    return ServicePrincipal(service_id=service_id, scopes=set(_normalize_scopes(scopes)))


def authorize_websocket_token(token: str | None) -> Principal:
    if not token:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Missing websocket token")

    try:
        return authenticate_bearer_token(token)
    except HTTPException as exc:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason=exc.detail) from exc
