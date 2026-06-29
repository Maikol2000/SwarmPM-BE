from app.schemas import AssignmentRequest


def choose_assignment_target(payload: AssignmentRequest) -> tuple[str, str]:
    # Placeholder policy for milestone Q-BE-02.
    if payload.capacity_hours >= 30:
        return "high-throughput-lane", "Capacity >= 30h, route to high-throughput lane"
    if payload.capacity_hours >= 15:
        return "standard-lane", "Capacity between 15h and 29h, route to standard lane"
    return "light-lane", "Capacity under 15h, route to light lane"


def compute_workload_recommendation(hours: int) -> tuple[int, str]:
    if hours > 40:
        return 36, "Reduce load to prevent burnout risk"
    if hours < 10:
        return 14, "Increase load to improve utilization"
    return hours, "Current load is balanced"
