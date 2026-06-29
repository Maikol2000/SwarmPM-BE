from app.schemas import AuraAskRequest, AuraAskResponse, AuraInsightResponse


def generate_insight(metrics: dict[str, float]) -> AuraInsightResponse:
    flags: list[str] = []
    risk = metrics.get("risk", 0.0)
    velocity = metrics.get("velocity", 0.0)

    if risk > 0.7:
        flags.append("high_risk")
    if velocity < 0.4:
        flags.append("low_velocity")

    summary = "Team trend is stable"
    if flags:
        summary = "Attention needed: " + ", ".join(flags)

    return AuraInsightResponse(summary=summary, flags=flags)


def ask_aura(payload: AuraAskRequest) -> AuraAskResponse:
    q = payload.question.lower()
    if "blocker" in q:
        return AuraAskResponse(
            answer="Prioritize unresolved dependencies and escalate owner in standup.",
            confidence=0.82,
        )
    if "velocity" in q:
        return AuraAskResponse(
            answer="Compare planned vs completed milestones for the last 7 days.",
            confidence=0.77,
        )
    return AuraAskResponse(
        answer="Use dashboard unified data and workload balance results for next action.",
        confidence=0.65,
    )
