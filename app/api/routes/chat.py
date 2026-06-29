import asyncio
import json
import time
from collections import deque

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles, require_scopes
from app.core.security import Principal, authorize_websocket_token
from app.db.session import SessionLocal, get_db
from app.schemas import ChatMessageIn, PresenceStatus, PresenceUpdate
from app.services.chat_service import chat_service

router = APIRouter(prefix="/api/chat", tags=["DASH-01 chat"])

_HEARTBEAT_INTERVAL = 30   # seconds between server pings
_HEARTBEAT_TIMEOUT = 10    # seconds to wait for client pong
_RATE_LIMIT_MAX = 60       # messages per window
_RATE_LIMIT_WINDOW = 60    # window size in seconds


class _RateLimiter:
    """Sliding-window rate limiter: max 60 messages per 60-second window."""

    __slots__ = ("_max", "_window", "_times")

    def __init__(self, max_msgs: int = _RATE_LIMIT_MAX, window: int = _RATE_LIMIT_WINDOW) -> None:
        self._max = max_msgs
        self._window = window
        self._times: deque[float] = deque()

    def is_allowed(self) -> bool:
        now = time.monotonic()
        while self._times and now - self._times[0] > self._window:
            self._times.popleft()
        if len(self._times) >= self._max:
            return False
        self._times.append(now)
        return True


def _ensure_user_access(user_id: str, principal: Principal) -> None:
    if principal.sub != user_id and principal.role != "admin" and "admin:all" not in principal.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access another user messages",
        )


# ── REST endpoints ──────────────────────────────────────────────────────────

@router.get("/history")
def chat_history(
    user_id: str = Query(...),
    peer_id: str = Query(...),
    principal: Principal = Depends(require_scopes("chat:read")),
    db: Session = Depends(get_db),
):
    _ensure_user_access(user_id, principal)
    return chat_service.history(db=db, user_id=user_id, peer_id=peer_id)


@router.get("/unread")
def unread_counts(
    user_id: str = Query(...),
    principal: Principal = Depends(require_scopes("chat:read")),
    db: Session = Depends(get_db),
):
    _ensure_user_access(user_id, principal)
    return chat_service.unread_counts(db=db, user_id=user_id)


@router.patch("/messages/{message_id}/read")
def mark_read(
    message_id: str,
    user_id: str = Query(...),
    principal: Principal = Depends(require_scopes("chat:write")),
    db: Session = Depends(get_db),
):
    _ensure_user_access(user_id, principal)
    if not chat_service.mark_read(db=db, message_id=message_id, user_id=user_id):
        raise HTTPException(status_code=404, detail="Message not found")
    return {"status": "ok"}


@router.get("/presence")
def get_presence(
    _: Principal = Depends(require_scopes("chat:read")),
    db: Session = Depends(get_db),
):
    return chat_service.get_presence(db=db)


@router.put("/presence")
def update_presence(
    payload: PresenceUpdate,
    principal: Principal = Depends(require_scopes("chat:write")),
    db: Session = Depends(get_db),
):
    """Manually set presence status (online/away/busy/offline)."""
    return chat_service.set_presence(db=db, user_id=principal.sub, status=payload.status)


@router.post("/messages")
def create_message(
    payload: ChatMessageIn,
    principal: Principal = Depends(require_scopes("chat:write")),
    db: Session = Depends(get_db),
):
    if payload.sender_id != principal.sub and principal.role != "admin" and "admin:all" not in principal.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot send as another user",
        )
    return chat_service.add_message(db=db, payload=payload)


@router.get("/metrics")
def chat_metrics(
    _: Principal = Depends(require_roles("manager", "admin")),
    db: Session = Depends(get_db),
):
    """PULSE observability: chat counters for monitoring dashboards."""
    return chat_service.get_metrics(db=db)


# ── WebSocket ────────────────────────────────────────────────────────────────

@router.websocket("/ws")
async def chat_ws(
    websocket: WebSocket,
    user_id: str = Query(...),
    token: str | None = Query(default=None),
):
    # Accept token from query param or from Authorization header as fallback
    if not token:
        auth_header = None
        for hdr in websocket.scope.get("headers", []):
            # hdr is a (name_bytes, value_bytes) tuple
            try:
                name = hdr[0].decode().lower()
                value = hdr[1].decode()
            except Exception:
                continue
            if name == "authorization":
                auth_header = value
                break
        if auth_header:
            scheme, _, tok = auth_header.partition(" ")
            if scheme and scheme.lower() == "bearer":
                token = tok

    principal = authorize_websocket_token(token)
    if user_id != principal.sub and principal.role != "admin" and "admin:all" not in principal.scopes:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Cannot connect as another user")
        return

    await websocket.accept()

    # Issue resume token and mark presence
    resume_token = chat_service.register_connection(user_id)
    with SessionLocal() as db:
        chat_service.set_presence(db=db, user_id=user_id, status=PresenceStatus.online)
    await websocket.send_json({"type": "connected", "resume_token": resume_token, "user_id": user_id})

    rate_limiter = _RateLimiter()
    pong_event = asyncio.Event()
    pong_event.set()   # no pending ping at start

    async def _heartbeat() -> None:
        """Send ping every 30 s; close connection if pong not received within 10 s."""
        while True:
            await asyncio.sleep(_HEARTBEAT_INTERVAL)
            pong_event.clear()
            try:
                await websocket.send_json({"type": "ping"})
            except Exception:
                return
            try:
                await asyncio.wait_for(pong_event.wait(), timeout=_HEARTBEAT_TIMEOUT)
            except asyncio.TimeoutError:
                try:
                    await websocket.close(code=1001, reason="Heartbeat timeout")
                except Exception:
                    pass
                return

    hb_task = asyncio.create_task(_heartbeat())

    try:
        while True:
            text = await websocket.receive_text()

            # Handle pong frame (client responding to server ping)
            try:
                msg = json.loads(text)
                if isinstance(msg, dict) and msg.get("type") == "pong":
                    pong_event.set()
                    continue
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

            # Rate limit: 60 messages / 60 s per connection
            if not rate_limiter.is_allowed():
                await websocket.send_json({"type": "error", "detail": "Rate limit exceeded (60 msg/min)"})
                continue

            chat_service.increment_messages_sent()
            await websocket.send_json({"type": "message", "echo": text, "user_id": user_id})

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        hb_task.cancel()
        try:
            await hb_task
        except asyncio.CancelledError:
            pass
        chat_service.unregister_connection(user_id)
        with SessionLocal() as db:
            chat_service.set_presence(db=db, user_id=user_id, status=PresenceStatus.offline)

