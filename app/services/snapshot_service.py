from sqlalchemy.orm import Session

from app.schemas import SnapshotData
from app.repositories.snapshot_repository import SnapshotRepository


class SnapshotService:
    def __init__(self) -> None:
        self._repo = SnapshotRepository()

    def create_snapshot(self, db: Session, data: dict) -> SnapshotData:
        return self._repo.create_snapshot(db, data)

    def get_snapshot(self, db: Session, snapshot_id: str) -> SnapshotData | None:
        return self._repo.get_snapshot(db, snapshot_id)


snapshot_service = SnapshotService()
