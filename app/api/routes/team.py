from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import enforce_rate_limit, require_roles, require_scopes
from app.core.security import Principal
from app.db.session import get_db
from app.schemas import (
    AssignmentRequest,
    AssignmentResponse,
    RebalanceItem,
    RebalanceRequest,
    RebalanceResponse,
)
from app.services.core_domain_service import core_domain_services
from app.services.core_logic_gateway import CoreLogicGatewayFactory

router = APIRouter(prefix="/api/team", tags=["TM-01 and TM-04"])


@router.post("/assign", response_model=AssignmentResponse)
def assign_position(
    payload: AssignmentRequest,
    _: Principal = Depends(require_roles("manager", "admin")),
    ___: None = Depends(enforce_rate_limit("team.assign", max_requests=60, window_seconds=60)),
    principal: Principal = Depends(require_scopes("team:write")),
    db: Session = Depends(get_db),
):
    result = core_domain_services.position_service.assign_position(db=db, payload=payload, actor_id=principal.sub)
    return AssignmentResponse(user_id=payload.user_id, assigned_to=result.assigned_to, rationale=result.rationale)


@router.post("/rebalance", response_model=RebalanceResponse)
def rebalance(
    payload: RebalanceRequest,
    _: Principal = Depends(require_roles("manager", "admin")),
    __: Principal = Depends(require_scopes("team:write")),
    ___: None = Depends(enforce_rate_limit("team.rebalance", max_requests=30, window_seconds=60)),
):
    gateway = CoreLogicGatewayFactory.build()
    result = gateway.rebalance(payload)
    updates = [
        RebalanceItem(
            user_id=str(item["user_id"]),
            recommended_capacity=int(item["recommended_capacity"]),
            reason=str(item["reason"]),
        )
        for item in result.updates
    ]
    return RebalanceResponse(updates=updates)
