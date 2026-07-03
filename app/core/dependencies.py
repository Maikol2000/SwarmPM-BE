from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, Request, status

from app.core.config import get_settings
from app.core.security import Principal, authenticate_bearer_token
from app.gateway.rate_limit import rate_limiter


def _extract_bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token format")

    return token


def get_current_principal(token: str = Depends(_extract_bearer_token)) -> Principal:
    return authenticate_bearer_token(token)


def require_scopes(*required_scopes: str) -> Callable[[Principal], Principal]:
    def checker(principal: Principal = Depends(get_current_principal)) -> Principal:
        if "admin:all" in principal.scopes:
            return principal

        missing = [scope for scope in required_scopes if scope not in principal.scopes]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scopes: {', '.join(missing)}",
            )
        return principal

    return checker


def require_roles(*allowed_roles: str) -> Callable[[Principal], Principal]:
    def checker(principal: Principal = Depends(get_current_principal)) -> Principal:
        if principal.role not in allowed_roles and "admin:all" not in principal.scopes:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return principal

    return checker


def enforce_rate_limit(
    route_key: str,
    max_requests: int | None = None,
    window_seconds: int | None = None,
) -> Callable[[Request, Principal], None]:
    def checker(request: Request, principal: Principal = Depends(get_current_principal)) -> None:
        settings = get_settings()
        limit = max_requests if max_requests is not None else settings.gateway_rate_limit_requests
        window = window_seconds if window_seconds is not None else settings.gateway_rate_limit_window_seconds
        limiter_key = f"{route_key}:{principal.sub}:{request.client.host if request.client else 'unknown'}"
        if not rate_limiter.allow(limiter_key, max_requests=limit, window_seconds=window):
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

    return checker
