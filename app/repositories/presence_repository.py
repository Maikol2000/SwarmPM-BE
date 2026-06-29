from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.presence import PresenceModel
from app.schemas import PresenceEntry, PresenceStatus


class PresenceRepository:
    @staticmethod
    def _to_schema(model: PresenceModel) -> PresenceEntry:
        return PresenceEntry(
            status=PresenceStatus(model.status),
            updated_at=model.updated_at,
        )

    def set_presence(self, db: Session, user_id: str, status: PresenceStatus) -> PresenceEntry:
        model = db.get(PresenceModel, user_id)
        now = datetime.now(timezone.utc)

        if model is None:
            model = PresenceModel(user_id=user_id, status=status.value, updated_at=now)
        else:
            model.status = status.value
            model.updated_at = now

        db.add(model)
        db.commit()
        db.refresh(model)
        return self._to_schema(model)

    def get_presence(self, db: Session) -> dict[str, PresenceEntry]:
        rows = db.execute(select(PresenceModel)).scalars().all()
        return {row.user_id: self._to_schema(row) for row in rows}

    def count_presence(self, db: Session) -> int:
        stmt = select(func.count(PresenceModel.user_id))
        return int(db.execute(stmt).scalar_one())