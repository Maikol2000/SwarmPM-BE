from fastapi import APIRouter, Depends

from app.core.dependencies import require_scopes
from app.core.security import Principal
from app.schemas import AuraAskRequest, AuraAskResponse, AuraInsightRequest, AuraInsightResponse
from app.services.aura_service import ask_aura, generate_insight

router = APIRouter(prefix="/api/aura", tags=["AURA-01 and AURA-02"])


@router.post("/insights", response_model=AuraInsightResponse)
def insights(payload: AuraInsightRequest, _: Principal = Depends(require_scopes("aura:use"))):
    return generate_insight(payload.metrics)


@router.post("/ask", response_model=AuraAskResponse)
def ask(payload: AuraAskRequest, _: Principal = Depends(require_scopes("aura:use"))):
    return ask_aura(payload)
