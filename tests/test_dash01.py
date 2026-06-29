"""
DASH-01 full test suite.

Covers every requirement in the SOW:
  1. Message schema: id, sender_id, receiver_id, text, msg_type, timestamp
  2. Store history with sender/receiver/time indexes
  3. mark-as-read (PATCH) + unread count (GET)
  4. Track presence: online / away / busy / offline
  5. WebSocket: heartbeat (ping/pong) + rate-limit 60 msg/min + resume token
  6. PULSE observability metrics endpoint
"""
import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


# ── helpers ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _token(client: TestClient, user_id: str, role: str = "member", scopes: list[str] | None = None) -> str:
    resp = client.post(
        "/api/auth/token",
        json={
            "user_id": user_id,
            "role": role,
            "scopes": scopes or ["chat:read", "chat:write"],
        },
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _auth(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}"}


def _ws_url(user_id: str, token: str) -> str:
    return f"/api/chat/ws?user_id={user_id}&token={token}"


def _uid() -> str:
    return f"u-{uuid4()}"


# ═══════════════════════════════════════════════════════════════════════════
# 1. Message schema
# ═══════════════════════════════════════════════════════════════════════════

class TestMessageSchema:
    def test_all_required_fields_present(self, client):
        uid = _uid()
        peer = _uid()
        tok = _token(client, uid)

        resp = client.post(
            "/api/chat/messages",
            json={"sender_id": uid, "receiver_id": peer, "text": "hello", "msg_type": "text"},
            headers=_auth(tok),
        )
        assert resp.status_code == 200
        body = resp.json()
        for field in ("id", "sender_id", "receiver_id", "text", "msg_type", "timestamp"):
            assert field in body, f"Schema missing field: {field}"

    def test_field_values_correct(self, client):
        uid, peer = _uid(), _uid()
        tok = _token(client, uid)

        resp = client.post(
            "/api/chat/messages",
            json={"sender_id": uid, "receiver_id": peer, "text": "schema check", "msg_type": "text"},
            headers=_auth(tok),
        )
        body = resp.json()
        assert body["sender_id"] == uid
        assert body["receiver_id"] == peer
        assert body["text"] == "schema check"
        assert body["msg_type"] == "text"
        assert body["read"] is False
        assert body["id"]          # non-empty UUID
        assert body["timestamp"]   # non-empty ISO timestamp


# ═══════════════════════════════════════════════════════════════════════════
# 2. History stored with correct ordering (sender/receiver/time indexes)
# ═══════════════════════════════════════════════════════════════════════════

class TestChatHistory:
    def test_messages_retrieved_correctly(self, client):
        uid, peer = _uid(), _uid()
        tok = _token(client, uid)
        peer_tok = _token(client, peer)

        for txt in ("first", "second", "third"):
            client.post(
                "/api/chat/messages",
                json={"sender_id": uid, "receiver_id": peer, "text": txt, "msg_type": "text"},
                headers=_auth(tok),
            )

        resp = client.get(
            "/api/chat/history",
            params={"user_id": uid, "peer_id": peer},
            headers=_auth(tok),
        )
        assert resp.status_code == 200
        texts = [m["text"] for m in resp.json()]
        assert "first" in texts and "third" in texts

    def test_history_ordered_asc_by_timestamp(self, client):
        uid, peer = _uid(), _uid()
        tok = _token(client, uid)

        for i in range(3):
            client.post(
                "/api/chat/messages",
                json={"sender_id": uid, "receiver_id": peer, "text": str(i), "msg_type": "text"},
                headers=_auth(tok),
            )

        msgs = client.get(
            "/api/chat/history",
            params={"user_id": uid, "peer_id": peer},
            headers=_auth(tok),
        ).json()
        timestamps = [m["timestamp"] for m in msgs]
        assert timestamps == sorted(timestamps), "History not in ascending order"

    def test_history_bidirectional(self, client):
        """Messages sent by either party appear in both sides' history."""
        uid, peer = _uid(), _uid()
        tok_a = _token(client, uid)
        tok_b = _token(client, peer)

        client.post(
            "/api/chat/messages",
            json={"sender_id": uid, "receiver_id": peer, "text": "from A", "msg_type": "text"},
            headers=_auth(tok_a),
        )
        client.post(
            "/api/chat/messages",
            json={"sender_id": peer, "receiver_id": uid, "text": "from B", "msg_type": "text"},
            headers=_auth(tok_b),
        )

        msgs = client.get(
            "/api/chat/history",
            params={"user_id": uid, "peer_id": peer},
            headers=_auth(tok_a),
        ).json()
        texts = [m["text"] for m in msgs]
        assert "from A" in texts and "from B" in texts


# ═══════════════════════════════════════════════════════════════════════════
# 3. mark-as-read + unread count
# ═══════════════════════════════════════════════════════════════════════════

class TestMarkReadUnread:
    def test_unread_count_increments_on_new_message(self, client):
        sender, receiver = _uid(), _uid()
        tok_a = _token(client, sender)
        tok_b = _token(client, receiver)

        client.post(
            "/api/chat/messages",
            json={"sender_id": sender, "receiver_id": receiver, "text": "ping", "msg_type": "text"},
            headers=_auth(tok_a),
        )

        r = client.get("/api/chat/unread", params={"user_id": receiver}, headers=_auth(tok_b))
        assert r.status_code == 200
        assert r.json().get(sender, 0) >= 1

    def test_mark_read_returns_ok(self, client):
        sender, receiver = _uid(), _uid()
        tok_a = _token(client, sender)
        tok_b = _token(client, receiver)

        msg_id = client.post(
            "/api/chat/messages",
            json={"sender_id": sender, "receiver_id": receiver, "text": "hi", "msg_type": "text"},
            headers=_auth(tok_a),
        ).json()["id"]

        r = client.patch(
            f"/api/chat/messages/{msg_id}/read",
            params={"user_id": receiver},
            headers=_auth(tok_b),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_unread_count_decreases_after_mark_read(self, client):
        sender, receiver = _uid(), _uid()
        tok_a = _token(client, sender)
        tok_b = _token(client, receiver)

        ids = []
        for i in range(2):
            ids.append(
                client.post(
                    "/api/chat/messages",
                    json={"sender_id": sender, "receiver_id": receiver, "text": f"m{i}", "msg_type": "text"},
                    headers=_auth(tok_a),
                ).json()["id"]
            )

        before = client.get("/api/chat/unread", params={"user_id": receiver}, headers=_auth(tok_b)).json()
        assert before.get(sender, 0) >= 2

        client.patch(f"/api/chat/messages/{ids[0]}/read", params={"user_id": receiver}, headers=_auth(tok_b))

        after = client.get("/api/chat/unread", params={"user_id": receiver}, headers=_auth(tok_b)).json()
        assert after.get(sender, 0) < before.get(sender, 0)

    def test_mark_read_by_wrong_user_returns_404(self, client):
        sender, receiver, other = _uid(), _uid(), _uid()
        tok_a = _token(client, sender)
        tok_other = _token(client, other)

        msg_id = client.post(
            "/api/chat/messages",
            json={"sender_id": sender, "receiver_id": receiver, "text": "secret", "msg_type": "text"},
            headers=_auth(tok_a),
        ).json()["id"]

        r = client.patch(
            f"/api/chat/messages/{msg_id}/read",
            params={"user_id": other},
            headers=_auth(tok_other),
        )
        assert r.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# 4. Presence: online / away / busy / offline
# ═══════════════════════════════════════════════════════════════════════════

class TestPresence:
    def test_manual_set_away_and_busy(self, client):
        uid = _uid()
        tok = _token(client, uid)

        for st in ("away", "busy", "online"):
            r = client.put("/api/chat/presence", json={"status": st}, headers=_auth(tok))
            assert r.status_code == 200
            assert r.json()["status"] == st

    def test_presence_visible_to_other_users(self, client):
        uid, observer = _uid(), _uid()
        tok = _token(client, uid)
        tok_obs = _token(client, observer)

        client.put("/api/chat/presence", json={"status": "busy"}, headers=_auth(tok))

        presence = client.get("/api/chat/presence", headers=_auth(tok_obs)).json()
        assert uid in presence
        assert presence[uid]["status"] == "busy"

    def test_presence_has_updated_at_timestamp(self, client):
        uid = _uid()
        tok = _token(client, uid)

        r = client.put("/api/chat/presence", json={"status": "away"}, headers=_auth(tok))
        assert "updated_at" in r.json()

    def test_invalid_presence_status_rejected(self, client):
        uid = _uid()
        tok = _token(client, uid)
        r = client.put("/api/chat/presence", json={"status": "invisible"}, headers=_auth(tok))
        assert r.status_code == 422

    def test_ws_connect_sets_online_disconnect_sets_offline(self, client):
        uid = _uid()
        tok = _token(client, uid)
        observer = _uid()
        tok_obs = _token(client, observer)

        with client.websocket_connect(_ws_url(uid, tok)) as ws:
            ws.receive_json()  # connected event
            presence = client.get("/api/chat/presence", headers=_auth(tok_obs)).json()
            assert presence.get(uid, {}).get("status") == "online"

        # After disconnect presence must be offline
        presence = client.get("/api/chat/presence", headers=_auth(tok_obs)).json()
        assert presence.get(uid, {}).get("status") == "offline"


# ═══════════════════════════════════════════════════════════════════════════
# 5. WebSocket: resume token + heartbeat ping/pong + rate-limit
# ═══════════════════════════════════════════════════════════════════════════

class TestWebSocket:
    def test_connect_event_contains_resume_token(self, client):
        uid = _uid()
        tok = _token(client, uid)

        with client.websocket_connect(_ws_url(uid, tok)) as ws:
            event = ws.receive_json()
            assert event["type"] == "connected"
            assert "resume_token" in event and event["resume_token"]
            assert event["user_id"] == uid

    def test_echo_message_returned(self, client):
        uid = _uid()
        tok = _token(client, uid)

        with client.websocket_connect(_ws_url(uid, tok)) as ws:
            ws.receive_json()  # connected
            ws.send_text("hello ws")
            resp = ws.receive_json()
            assert resp["type"] == "message"
            assert resp["user_id"] == uid

    def test_pong_frame_not_echoed(self, client):
        """Client pong must be silently absorbed; next real message still echoed."""
        uid = _uid()
        tok = _token(client, uid)

        with client.websocket_connect(_ws_url(uid, tok)) as ws:
            ws.receive_json()  # connected
            ws.send_text(json.dumps({"type": "pong"}))
            ws.send_text("real message")
            resp = ws.receive_json()
            assert resp["type"] == "message"

    def test_rate_limit_60_messages_per_minute(self, client):
        """61st message within the 60-s window must receive an error frame."""
        uid = _uid()
        tok = _token(client, uid)

        with client.websocket_connect(_ws_url(uid, tok)) as ws:
            ws.receive_json()  # connected
            for i in range(60):
                ws.send_text(f"msg {i}")
                ws.receive_json()
            # 61st must be rate-limited
            ws.send_text("over the limit")
            resp = ws.receive_json()
            assert resp["type"] == "error"
            assert "Rate limit" in resp["detail"]

    def test_ws_rejects_wrong_user_id(self, client):
        """Token for user A cannot connect as user B."""
        uid = _uid()
        tok = _token(client, uid)
        other = f"other-{uuid4()}"

        with pytest.raises(Exception):
            with client.websocket_connect(f"/api/chat/ws?user_id={other}&token={tok}") as ws:
                ws.receive_json()

    def test_ws_reject_missing_token(self, client):
        uid = _uid()
        with pytest.raises(Exception):
            with client.websocket_connect(f"/api/chat/ws?user_id={uid}") as ws:
                ws.receive_json()


# ═══════════════════════════════════════════════════════════════════════════
# 6. PULSE observability metrics
# ═══════════════════════════════════════════════════════════════════════════

class TestPulseMetrics:
    def test_metrics_endpoint_accessible_by_manager(self, client):
        uid = _uid()
        tok = _token(client, uid, role="manager")
        r = client.get("/api/chat/metrics", headers=_auth(tok))
        assert r.status_code == 200
        body = r.json()
        for key in ("messages_sent_total", "active_connections", "presence_changes_total", "mark_read_total"):
            assert key in body

    def test_metrics_blocked_for_member_role(self, client):
        uid = _uid()
        tok = _token(client, uid, role="member")
        r = client.get("/api/chat/metrics", headers=_auth(tok))
        assert r.status_code == 403

    def test_messages_sent_counter_increments_on_ws_message(self, client):
        uid = _uid()
        tok = _token(client, uid, role="manager")

        before = client.get("/api/chat/metrics", headers=_auth(tok)).json()["messages_sent_total"]

        with client.websocket_connect(_ws_url(uid, tok)) as ws:
            ws.receive_json()
            ws.send_text("counting")
            ws.receive_json()

        after = client.get("/api/chat/metrics", headers=_auth(tok)).json()["messages_sent_total"]
        assert after > before

    def test_mark_read_counter_increments(self, client):
        sender, receiver = _uid(), _uid()
        tok_a = _token(client, sender)
        tok_b = _token(client, receiver)
        tok_manager = _token(client, _uid(), role="manager")

        msg_id = client.post(
            "/api/chat/messages",
            json={"sender_id": sender, "receiver_id": receiver, "text": "count read", "msg_type": "text"},
            headers=_auth(tok_a),
        ).json()["id"]

        before = client.get("/api/chat/metrics", headers=_auth(tok_manager)).json()["mark_read_total"]
        client.patch(f"/api/chat/messages/{msg_id}/read", params={"user_id": receiver}, headers=_auth(tok_b))
        after = client.get("/api/chat/metrics", headers=_auth(tok_manager)).json()["mark_read_total"]

        assert after == before + 1

    def test_presence_changes_counter_increments(self, client):
        uid = _uid()
        tok = _token(client, uid)
        tok_manager = _token(client, _uid(), role="manager")

        before = client.get("/api/chat/metrics", headers=_auth(tok_manager)).json()["presence_changes_total"]
        client.put("/api/chat/presence", json={"status": "away"}, headers=_auth(tok))
        after = client.get("/api/chat/metrics", headers=_auth(tok_manager)).json()["presence_changes_total"]

        assert after > before
