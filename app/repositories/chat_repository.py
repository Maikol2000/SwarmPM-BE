from collections import defaultdict

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.chat import ChatMessageModel
from app.schemas import ChatMessage, ChatMessageIn


class ChatRepository:
    @staticmethod
    def _to_schema(model: ChatMessageModel) -> ChatMessage:
        return ChatMessage(
            id=model.id,
            sender_id=model.sender_id,
            receiver_id=model.receiver_id,
            text=model.text,
            msg_type=model.msg_type,
            timestamp=model.timestamp,
            read=model.read,
        )

    def add_message(self, db: Session, payload: ChatMessageIn) -> ChatMessage:
        model = ChatMessageModel(
            sender_id=payload.sender_id,
            receiver_id=payload.receiver_id,
            text=payload.text,
            msg_type=payload.msg_type,
            read=False,
        )
        db.add(model)
        db.commit()
        db.refresh(model)
        return self._to_schema(model)

    def history(self, db: Session, user_id: str, peer_id: str) -> list[ChatMessage]:
        stmt = (
            select(ChatMessageModel)
            .where(
                or_(
                    and_(ChatMessageModel.sender_id == user_id, ChatMessageModel.receiver_id == peer_id),
                    and_(ChatMessageModel.sender_id == peer_id, ChatMessageModel.receiver_id == user_id),
                )
            )
            .order_by(ChatMessageModel.timestamp.asc())
        )
        rows = db.execute(stmt).scalars().all()
        return [self._to_schema(row) for row in rows]

    def unread_counts(self, db: Session, user_id: str) -> dict[str, int]:
        stmt = (
            select(ChatMessageModel.sender_id, func.count(ChatMessageModel.id))
            .where(ChatMessageModel.receiver_id == user_id, ChatMessageModel.read.is_(False))
            .group_by(ChatMessageModel.sender_id)
        )
        counts: dict[str, int] = defaultdict(int)
        for sender_id, count in db.execute(stmt).all():
            counts[sender_id] = int(count)
        return dict(counts)

    def mark_read(self, db: Session, message_id: str, user_id: str) -> bool:
        model = db.get(ChatMessageModel, message_id)
        if not model or model.receiver_id != user_id:
            return False

        model.read = True
        db.add(model)
        db.commit()
        return True

    def total_messages(self, db: Session) -> int:
        stmt = select(func.count(ChatMessageModel.id))
        return int(db.execute(stmt).scalar_one())

    def total_read(self, db: Session) -> int:
        stmt = select(func.count(ChatMessageModel.id)).where(ChatMessageModel.read.is_(True))
        return int(db.execute(stmt).scalar_one())
