from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.events import DomainEventPublisher, build_event_publisher, encode_event_payload
from app.repositories.domain_repository import DomainRepository
from app.schemas import AssignmentRequest, RebalanceRequest
from app.services.core_logic_gateway import CoreLogicGateway, CoreLogicGatewayFactory


@dataclass(slots=True)
class PositionAssignmentResult:
    assignment_id: str
    assigned_to: str
    rationale: str
    created_at: datetime


@dataclass(slots=True)
class MilestoneResult:
    milestone_id: str
    key: str
    status: str


@dataclass(slots=True)
class SubmissionResult:
    submission_id: str
    milestone_key: str
    status: str


class PositionService(Protocol):
    def assign_position(self, db: Session, payload: AssignmentRequest, actor_id: str) -> PositionAssignmentResult:
        ...


class MilestoneService(Protocol):
    def create_milestone(self, db: Session, key: str, owner_id: str) -> MilestoneResult:
        ...


class SubmissionService(Protocol):
    def create_submission(
        self,
        db: Session,
        milestone_key: str,
        submitted_by: str,
        notes: str = "",
    ) -> SubmissionResult:
        ...


class SQLPositionService(PositionService):
    def __init__(
        self,
        repository: DomainRepository,
        gateway: CoreLogicGateway,
        events: DomainEventPublisher,
    ) -> None:
        self._repo = repository
        self._gateway = gateway
        self._events = events

    def assign_position(self, db: Session, payload: AssignmentRequest, actor_id: str) -> PositionAssignmentResult:
        decision = self._gateway.assign(payload)
        with db.begin():
            model = self._repo.create_position_assignment(
                db,
                user_id=payload.user_id,
                role=payload.role,
                capacity_hours=payload.capacity_hours,
                assigned_to=decision.assigned_to,
                rationale=decision.rationale,
            )

        event = encode_event_payload(
            {
                "event": "position.assignment.created",
                "assignment_id": model.id,
                "user_id": payload.user_id,
                "actor_id": actor_id,
                "assigned_to": decision.assigned_to,
            }
        )
        self._events.publish("assignment:new", event)

        return PositionAssignmentResult(
            assignment_id=model.id,
            assigned_to=decision.assigned_to,
            rationale=decision.rationale,
            created_at=model.created_at,
        )


class SQLMilestoneService(MilestoneService):
    def __init__(self, repository: DomainRepository, events: DomainEventPublisher) -> None:
        self._repo = repository
        self._events = events

    def create_milestone(self, db: Session, key: str, owner_id: str) -> MilestoneResult:
        with db.begin():
            model = self._repo.create_milestone(db, key=key, owner_id=owner_id)

        self._events.publish(
            "milestone:new",
            encode_event_payload({"event": "milestone.created", "milestone_id": model.id, "key": model.key}),
        )
        return MilestoneResult(milestone_id=model.id, key=model.key, status=model.status)


class SQLSubmissionService(SubmissionService):
    def __init__(self, repository: DomainRepository, events: DomainEventPublisher) -> None:
        self._repo = repository
        self._events = events

    def create_submission(
        self,
        db: Session,
        milestone_key: str,
        submitted_by: str,
        notes: str = "",
    ) -> SubmissionResult:
        with db.begin():
            model = self._repo.create_submission(
                db,
                milestone_key=milestone_key,
                submitted_by=submitted_by,
                notes=notes,
            )

        self._events.publish(
            "submission:new",
            encode_event_payload(
                {
                    "event": "submission.created",
                    "submission_id": model.id,
                    "milestone_key": model.milestone_key,
                }
            ),
        )
        return SubmissionResult(submission_id=model.id, milestone_key=model.milestone_key, status=model.status)


class CoreDomainServices:
    def __init__(self) -> None:
        repository = DomainRepository()
        events = build_event_publisher()
        self.position_service: PositionService = SQLPositionService(
            repository=repository,
            gateway=CoreLogicGatewayFactory.build(),
            events=events,
        )
        self.milestone_service: MilestoneService = SQLMilestoneService(repository=repository, events=events)
        self.submission_service: SubmissionService = SQLSubmissionService(repository=repository, events=events)


core_domain_services = CoreDomainServices()
