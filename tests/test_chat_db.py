from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def _token_for(client: TestClient, user_id: str, scopes: list[str]) -> str:
    response = client.post(
        "/api/auth/token",
        json={
            "user_id": user_id,
            "role": "member",
            "scopes": scopes,
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_chat_message_is_persisted_in_db() -> None:
    client = TestClient(app)
    user_id = f"u-{uuid4()}"
    peer_id = f"p-{uuid4()}"
    token = _token_for(client, user_id=user_id, scopes=["chat:read", "chat:write"])

    create_response = client.post(
        "/api/chat/messages",
        json={
            "sender_id": user_id,
            "receiver_id": peer_id,
            "text": "hello from db test",
            "msg_type": "text",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_response.status_code == 200

    history_response = client.get(
        "/api/chat/history",
        params={"user_id": user_id, "peer_id": peer_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) >= 1
    assert any(item["text"] == "hello from db test" for item in history)
