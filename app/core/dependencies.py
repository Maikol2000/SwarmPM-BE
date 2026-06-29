from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, status

from app.core.security import Principal, authenticate_bearer_token


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
