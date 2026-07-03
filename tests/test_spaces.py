from fastapi.testclient import TestClient

from app.main import app


def _token_for(
    client: TestClient,
    user_id: str = "user-1",
    role: str = "member",
    scopes: list[str] | None = None,
) -> str:
    response = client.post(
        "/api/auth/token",
        json={
            "user_id": user_id,
            "role": role,
            "scopes": scopes or ["spaces:read"],
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_categories_contract_includes_dash_04_fields() -> None:
    client = TestClient(app)
    token = _token_for(client)

    response = client.get("/api/spaces/categories", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body
    assert {"id", "name", "icon", "order", "subcategories"} <= body[0].keys()
    assert {"id", "category_id", "name", "badge_count", "ticker", "stats"} <= body[0]["subcategories"][0].keys()


def test_subcategories_endpoint_filters_by_category() -> None:
    client = TestClient(app)
    token = _token_for(client)

    response = client.get(
        "/api/spaces/categories/build/subcategories",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body
    assert all(item["category_id"] == "build" for item in body)


def test_content_endpoint_returns_panel_payload() -> None:
    client = TestClient(app)
    token = _token_for(client)

    response = client.get(
        "/api/spaces/content/ops/ops-standup",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["category_id"] == "ops"
    assert body["subcategory_id"] == "ops-standup"
    assert body["items"]


def test_departments_and_trending_endpoints_exist() -> None:
    client = TestClient(app)
    token = _token_for(client)

    departments_response = client.get("/api/spaces/departments", headers={"Authorization": f"Bearer {token}"})
    trending_response = client.get("/api/spaces/trending", headers={"Authorization": f"Bearer {token}"})

    assert departments_response.status_code == 200
    assert trending_response.status_code == 200
    assert departments_response.json()
    assert trending_response.json()


def test_admin_cache_refresh_requires_manager_role() -> None:
    client = TestClient(app)
    member_token = _token_for(client, role="member")
    manager_token = _token_for(client, role="manager")

    member_response = client.post(
        "/api/spaces/admin/cache/refresh",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    manager_response = client.post(
        "/api/spaces/admin/cache/refresh",
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    assert member_response.status_code == 403
    assert manager_response.status_code == 200
    assert manager_response.json()["status"] == "refreshed"


def test_unknown_category_and_content_return_404() -> None:
    client = TestClient(app)
    token = _token_for(client)

    missing_category = client.get(
        "/api/spaces/categories/unknown/subcategories",
        headers={"Authorization": f"Bearer {token}"},
    )
    missing_content = client.get(
        "/api/spaces/content/unknown/unknown",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert missing_category.status_code == 404
    assert missing_content.status_code == 404