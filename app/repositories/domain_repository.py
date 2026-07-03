from sqlalchemy.orm import Session

from app.models.domain import MilestoneModel, PositionAssignmentModel, SubmissionModel


class DomainRepository:
    def create_position_assignment(
        self,
        db: Session,
        *,
        user_id: str,
        role: str,
        capacity_hours: int,
        assigned_to: str,
        rationale: str,
    ) -> PositionAssignmentModel:
        model = PositionAssignmentModel(
            user_id=user_id,
            role=role,
            capacity_hours=capacity_hours,
            assigned_to=assigned_to,
            rationale=rationale,
        )
        db.add(model)
        db.flush()
        return model

    def create_milestone(self, db: Session, *, key: str, owner_id: str, status: str = "open") -> MilestoneModel:
        model = MilestoneModel(key=key, owner_id=owner_id, status=status)
        db.add(model)
        db.flush()
        return model

    def create_submission(
        self,
        db: Session,
        *,
        milestone_key: str,
        submitted_by: str,
        status: str = "submitted",
        notes: str = "",
    ) -> SubmissionModel:
        model = SubmissionModel(
            milestone_key=milestone_key,
            submitted_by=submitted_by,
            status=status,
            notes=notes,
        )
        db.add(model)
        db.flush()
        return model
