from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
pytestmark = [pytest.mark.integration, pytest.mark.critical]


def _register(email: str, password: str = "Passw0rd!") -> str:
    response = client.post(
        "/dashboard/api/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["source"] == "customer-db-session"
    return payload["session"]["token"]


def _login(email: str, password: str = "Passw0rd!") -> str:
    response = client.post(
        "/dashboard/api/session/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["source"] == "customer-db-session"
    return payload["session"]["token"]


def _new_email() -> str:
    return f"user-{uuid4().hex[:10]}@example.com"


@pytest.mark.parametrize(
    ("method", "path", "json_payload"),
    [
        ("GET", "/dashboard/api/overview", None),
        ("GET", "/dashboard/api/metrics", None),
        ("GET", "/dashboard/api/activity", None),
        ("GET", "/dashboard/api/keys", None),
        ("GET", "/dashboard/api/session/me", None),
        ("POST", "/dashboard/api/session/logout", None),
        ("POST", "/dashboard/api/keys/create", {"label": "No Session", "env": "test"}),
        ("POST", "/dashboard/api/keys/key_missing/rotate", None),
        ("POST", "/dashboard/api/keys/key_missing/revoke", None),
        ("POST", "/dashboard/api/keys/key_missing/activate", None),
    ],
)
def test_customer_dashboard_requires_session(method: str, path: str, json_payload: dict | None):
    response = client.request(method, path, json=json_payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Customer session required"


def test_customer_dashboard_can_register_user_via_api():
    email = _new_email()
    token = _register(email)

    session_me = client.get(
        "/dashboard/api/session/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert session_me.status_code == 200
    payload = session_me.json()
    assert payload["session"]["email"] == email
    assert payload["session"]["tenantId"].startswith("user-")


def test_customer_dashboard_login_contract():
    email = _new_email()
    _register(email)
    token = _login(email)

    response = client.get(
        "/dashboard/api/session/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["ok"] is True
    assert payload["source"] == "customer-db-session"
    assert payload["session"]["email"] == email
    assert payload["session"]["token"] == token


def test_customer_dashboard_rejects_invalid_password():
    email = _new_email()
    _register(email)

    response = client.post(
        "/dashboard/api/session/login",
        json={"email": email, "password": "wrong-pass"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_customer_dashboard_scoped_response_includes_tenant_context():
    email = _new_email()
    token = _register(email)

    response = client.get(
        "/dashboard/api/overview?range=7d",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["source"] == "customer-placeholder"
    assert payload["range"] == "7d"
    assert payload["scope"]["tenantId"].startswith("user-")
    assert payload["scope"]["email"] == email


def test_customer_dashboard_logout_revokes_session():
    email = _new_email()
    token = _register(email)

    logout = client.post(
        "/dashboard/api/session/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout.status_code == 200
    assert logout.json()["ok"] is True

    after = client.get(
        "/dashboard/api/session/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert after.status_code == 401
    assert after.json()["detail"] == "Invalid customer session"


def test_customer_dashboard_keys_are_tenant_scoped():
    email_a = _new_email()
    email_b = _new_email()
    token_a = _register(email_a)
    token_b = _register(email_b)

    create_a = client.post(
        "/dashboard/api/keys/create",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"label": "Alpha CI", "env": "test"},
    )
    assert create_a.status_code == 200
    key_a = create_a.json()["data"]["key"]

    list_b = client.get(
        "/dashboard/api/keys",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert list_b.status_code == 200
    ids_b = {entry["id"] for entry in list_b.json()["keys"]}
    assert key_a["id"] not in ids_b


@pytest.mark.parametrize("action", ["rotate", "revoke", "activate"])
def test_customer_dashboard_cross_tenant_key_action_denied(action: str):
    token_a = _register(_new_email())
    token_b = _register(_new_email())

    create_a = client.post(
        "/dashboard/api/keys/create",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"label": "Cobalt Server", "env": "live"},
    )
    assert create_a.status_code == 200
    key_id = create_a.json()["data"]["key"]["id"]

    attempt = client.post(
        f"/dashboard/api/keys/{key_id}/{action}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert attempt.status_code == 404

    detail = attempt.json()["detail"]
    assert detail["ok"] is False
    assert detail["error"]["code"] == "KEY_NOT_FOUND"


def test_customer_dashboard_activity_is_tenant_scoped():
    email_a = _new_email()
    email_b = _new_email()
    token_a = _register(email_a)
    token_b = _register(email_b)

    activity_a = client.get(
        "/dashboard/api/activity",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    activity_b = client.get(
        "/dashboard/api/activity",
        headers={"Authorization": f"Bearer {token_b}"},
    )

    assert activity_a.status_code == 200
    assert activity_b.status_code == 200

    payload_a = activity_a.json()
    payload_b = activity_b.json()

    targets_a = {event["target"] for event in payload_a["events"]}
    targets_b = {event["target"] for event in payload_b["events"]}

    tenant_a = payload_a["scope"]["tenantId"]
    tenant_b = payload_b["scope"]["tenantId"]

    assert all(tenant_a in target for target in targets_a)
    assert all(tenant_b in target for target in targets_b)
    assert targets_a.isdisjoint(targets_b)

    actors_a = {event["actor"] for event in payload_a["events"]}
    actors_b = {event["actor"] for event in payload_b["events"]}
    assert email_a in actors_a
    assert email_b in actors_b


def test_customer_dashboard_accepts_custom_session_header():
    token = _register(_new_email())

    response = client.get(
        "/dashboard/api/session/me",
        headers={"X-Customer-Session": token},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["session"]["token"] == token


def test_customer_dashboard_legacy_internal_routes_redirect_to_dashboard_shell():
    root_redirect = client.get("/internal", follow_redirects=False)
    assert root_redirect.status_code in (301, 302, 307, 308)
    assert root_redirect.headers["location"] == "/dashboard"

    shell_redirect = client.get("/internal/", follow_redirects=False)
    assert shell_redirect.status_code in (301, 302, 307, 308)
    assert shell_redirect.headers["location"] == "/dashboard/"

    shell = client.get("/internal/")
    assert shell.status_code == 200
    assert "<title>Y Finance Dashboard" in shell.text


def test_customer_dashboard_frontend_login_flow_stays_authenticated_across_pages():
    dashboard_shell = client.get("/dashboard")
    assert dashboard_shell.status_code == 200
    assert "<title>Y Finance Dashboard" in dashboard_shell.text

    token = _register(_new_email())
    headers = {"Authorization": f"Bearer {token}"}

    for path in [
        "/dashboard/api/session/me",
        "/dashboard/api/overview?range=24h",
        "/dashboard/api/metrics?range=24h",
        "/dashboard/api/activity?limit=10",
        "/dashboard/api/keys",
    ]:
        response = client.get(path, headers=headers)
        assert response.status_code == 200

    create_key = client.post(
        "/dashboard/api/keys/create",
        headers=headers,
        json={"label": "Frontend Smoke", "env": "test"},
    )
    assert create_key.status_code == 200
    key_id = create_key.json()["data"]["key"]["id"]

    rotate = client.post(f"/dashboard/api/keys/{key_id}/rotate", headers=headers)
    assert rotate.status_code == 200
