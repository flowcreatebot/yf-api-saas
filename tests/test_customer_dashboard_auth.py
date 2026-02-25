import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
pytestmark = [pytest.mark.integration, pytest.mark.critical]


def _login(tenant_id: str = "tenant-acme", email: str = "owner@acme.test") -> str:
    response = client.post(
        "/dashboard/api/session/login",
        json={"tenantId": tenant_id, "email": email},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["source"] == "customer-session-store"
    return payload["session"]["token"]


def test_customer_dashboard_requires_session():
    response = client.get("/dashboard/api/overview")
    assert response.status_code == 401
    assert response.json()["detail"] == "Customer session required"


def test_customer_dashboard_session_me_contract():
    token = _login(tenant_id="tenant-blue", email="billing@blue.test")

    response = client.get(
        "/dashboard/api/session/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["ok"] is True
    assert payload["session"]["tenantId"] == "tenant-blue"
    assert payload["session"]["email"] == "billing@blue.test"
    assert payload["session"]["token"] == token


def test_customer_dashboard_scoped_response_includes_tenant_context():
    token = _login(tenant_id="tenant-orchid", email="ops@orchid.test")

    response = client.get(
        "/dashboard/api/overview?range=7d",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["source"] == "customer-placeholder"
    assert payload["range"] == "7d"
    assert payload["scope"]["tenantId"] == "tenant-orchid"
    assert payload["scope"]["email"] == "ops@orchid.test"


def test_customer_dashboard_logout_revokes_session():
    token = _login()

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
