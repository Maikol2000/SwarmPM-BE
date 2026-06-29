from fastapi.testclient import TestClient

from app.main import app


def _token_for(client: TestClient) -> str:
    response = client.post(
        "/api/auth/token",
        json={
            "user_id": "snapshot-user",
            "role": "member",
            "scopes": ["state:read", "state:write"],
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_snapshot_create_and_read() -> None:
    client = TestClient(app)
    token = _token_for(client)

    create_response = client.post(
        "/api/state/snapshot",
        json={"foo": "bar"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_response.status_code == 200
    snapshot_id = create_response.json()["snapshot_id"]

    get_response = client.get(
        f"/api/state/snapshot/{snapshot_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_response.status_code == 200
    assert get_response.json()["data"] == {"foo": "bar"}
