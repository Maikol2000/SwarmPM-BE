from uuid import uuid4

from sqlalchemy.orm import Session

from app.repositories.chat_repository import ChatRepository
from app.repositories.presence_repository import PresenceRepository
from app.schemas import ChatMessage, ChatMessageIn, PresenceEntry, PresenceStatus


class ChatService:
    def __init__(self) -> None:
        self._repo = ChatRepository()
        self._presence_repo = PresenceRepository()
        self._resume_tokens: dict[str, str] = {}
        # PULSE metrics counters
        self._messages_sent_total: int = 0
        self._active_connections: int = 0
        self._presence_changes_total: int = 0
        self._mark_read_total: int = 0

    # ---------- presence ----------

    def set_presence(self, db: Session, user_id: str, status: PresenceStatus | str) -> PresenceEntry:
        if isinstance(status, str):
            status = PresenceStatus(status)
        entry = self._presence_repo.set_presence(db=db, user_id=user_id, status=status)
        self._presence_changes_total += 1
        return entry

    def get_presence(self, db: Session) -> dict[str, PresenceEntry]:
        return self._presence_repo.get_presence(db=db)

    # ---------- WebSocket lifecycle ----------

    def register_connection(self, user_id: str) -> str:
        """Create and store a resume token; increment active connection counter."""
        token = str(uuid4())
        self._resume_tokens[user_id] = token
        self._active_connections += 1
        return token

    def unregister_connection(self, user_id: str) -> None:
        self._active_connections = max(0, self._active_connections - 1)
        self._resume_tokens.pop(user_id, None)

    # ---------- PULSE metrics ----------

    def get_metrics(self, db: Session | None = None) -> dict:
        """Return metrics. If a DB session is provided, compute persisted counters from DB.

        Runtime counters (active connections) remain in-memory. Persisted counters are derived
        from the database so metrics reflect stored history across restarts.
        """
        messages_total = self._messages_sent_total
        mark_read = self._mark_read_total
        presence_count = self._presence_changes_total

        if db is not None:
            try:
                messages_total = self._repo.total_messages(db)
                mark_read = self._repo.total_read(db)
                presence_count = self._presence_repo.count_presence(db)
            except Exception:
                # fallback to in-memory counters on DB error
                pass

        return {
            "messages_sent_total": messages_total,
            "active_connections": self._active_connections,
            "presence_changes_total": presence_count,
            "mark_read_total": mark_read,
        }

    def increment_messages_sent(self) -> None:
        self._messages_sent_total += 1

    # ---------- chat operations ----------

    def add_message(self, db: Session, payload: ChatMessageIn) -> ChatMessage:
        return self._repo.add_message(db, payload)

    def history(self, db: Session, user_id: str, peer_id: str) -> list[ChatMessage]:
        return self._repo.history(db, user_id=user_id, peer_id=peer_id)

    def unread_counts(self, db: Session, user_id: str) -> dict[str, int]:
        return self._repo.unread_counts(db, user_id)

    def mark_read(self, db: Session, message_id: str, user_id: str) -> bool:
        result = self._repo.mark_read(db, message_id=message_id, user_id=user_id)
        if result:
            self._mark_read_total += 1
        return result


chat_service = ChatService()
