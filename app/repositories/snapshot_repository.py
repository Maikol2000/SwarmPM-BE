from sqlalchemy.orm import Session

from app.models.snapshot import SnapshotModel
from app.schemas import SnapshotData


class SnapshotRepository:
    @staticmethod
    def _to_schema(model: SnapshotModel) -> SnapshotData:
        return SnapshotData(
            snapshot_id=model.snapshot_id,
            created_at=model.created_at,
            data=model.data,
        )

    def create_snapshot(self, db: Session, data: dict) -> SnapshotData:
        model = SnapshotModel(data=data)
        db.add(model)
        db.commit()
        db.refresh(model)
        return self._to_schema(model)

    def get_snapshot(self, db: Session, snapshot_id: str) -> SnapshotData | None:
        model = db.get(SnapshotModel, snapshot_id)
        if not model:
            return None
        return self._to_schema(model)
