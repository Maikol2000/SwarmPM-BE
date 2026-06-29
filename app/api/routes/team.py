from fastapi import APIRouter, Depends

from app.core.dependencies import require_roles, require_scopes
from app.core.security import Principal
from app.schemas import (
    AssignmentRequest,
    AssignmentResponse,
    RebalanceItem,
    RebalanceRequest,
    RebalanceResponse,
)
from app.services.core_logic import choose_assignment_target, compute_workload_recommendation

router = APIRouter(prefix="/api/team", tags=["TM-01 and TM-04"])


@router.post("/assign", response_model=AssignmentResponse)
def assign_position(
    payload: AssignmentRequest,
    _: Principal = Depends(require_roles("manager", "admin")),
    __: Principal = Depends(require_scopes("team:write")),
):
    target, rationale = choose_assignment_target(payload)
    return AssignmentResponse(user_id=payload.user_id, assigned_to=target, rationale=rationale)


@router.post("/rebalance", response_model=RebalanceResponse)
def rebalance(
    payload: RebalanceRequest,
    _: Principal = Depends(require_roles("manager", "admin")),
    __: Principal = Depends(require_scopes("team:write")),
):
    updates = []
    for member in payload.team:
        recommended, reason = compute_workload_recommendation(member.capacity_hours)
        updates.append(
            RebalanceItem(
                user_id=member.user_id,
                recommended_capacity=recommended,
                reason=reason,
            )
        )
    return RebalanceResponse(updates=updates)
