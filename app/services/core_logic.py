from app.schemas import AssignmentRequest


HIGH_THROUGHPUT_MIN_HOURS = 30
STANDARD_MIN_HOURS = 15
MAX_HEALTHY_LOAD_HOURS = 40
MIN_HEALTHY_LOAD_HOURS = 10


def choose_assignment_target(payload: AssignmentRequest) -> tuple[str, str]:
    if payload.capacity_hours >= HIGH_THROUGHPUT_MIN_HOURS:
        return "high-throughput-lane", "Capacity >= 30h, route to high-throughput lane"
    if payload.capacity_hours >= STANDARD_MIN_HOURS:
        return "standard-lane", "Capacity between 15h and 29h, route to standard lane"
    return "light-lane", "Capacity under 15h, route to light lane"


def compute_workload_recommendation(hours: int) -> tuple[int, str]:
    if hours > MAX_HEALTHY_LOAD_HOURS:
        return 36, "Reduce load to prevent burnout risk"
    if hours < MIN_HEALTHY_LOAD_HOURS:
        return 14, "Increase load to improve utilization"
    return hours, "Current load is balanced"
