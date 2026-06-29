from fastapi.testclient import TestClient

from app.main import app


def _token_for(client: TestClient, user_id: str = "user-1", role: str = "member", scopes: list[str] | None = None) -> str:
    payload = {
        "user_id": user_id,
        "role": role,
        "scopes": scopes or ["spaces:read", "chat:read", "chat:write", "state:read", "state:write", "dashboard:read", "aura:use"],
    }
    response = client.post("/api/auth/token", json=payload)
    assert response.status_code == 200
    return response.json()["access_token"]


def test_protected_endpoint_requires_auth() -> None:
    client = TestClient(app)
    response = client.get("/api/spaces/categories")
    assert response.status_code == 401


def test_protected_endpoint_accepts_valid_token() -> None:
    client = TestClient(app)
    token = _token_for(client)
    response = client.get("/api/spaces/categories", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_scope_enforcement_blocks_access() -> None:
    client = TestClient(app)
    token = _token_for(client, scopes=["spaces:read"])
    response = client.get("/api/chat/unread", params={"user_id": "user-1"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
