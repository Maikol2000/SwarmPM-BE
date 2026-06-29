from fastapi import Depends

from app.core.dependencies import get_current_principal
from app.core.security import Principal

def require_bearer_token(principal: Principal = Depends(get_current_principal)) -> str:
    return principal.sub
