from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import APIKey, Subscription, User

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


def _ensure_active_subscription(email: str):
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        subscription = db.query(Subscription).filter(Subscription.user_id == user.id).first()
        if subscription is None:
            db.add(
                Subscription(
                    user_id=user.id,
                    stripe_subscription_id=f"sub_test_{user.id}",
                    status="active",
                    plan="starter-monthly",
                )
            )
        else:
            subscription.status = "active"
        db.commit()


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
    assert payload["source"] == "customer-db-store"
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


def test_customer_dashboard_key_crud_persists_in_database():
    email = _new_email()
    token = _register(email)
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/dashboard/api/keys/create",
        headers=headers,
        json={"label": "Primary", "env": "test"},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["source"] == "customer-db-store"
    assert body["data"]["rawKey"].startswith("yf_test_")

    key_id = body["data"]["key"]["id"]

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        key_row = db.query(APIKey).filter(APIKey.id == int(key_id), APIKey.user_id == user.id).first()
        assert key_row is not None
        assert key_row.status == "active"
        assert key_row.name == "test:Primary"

    rotated = client.post(f"/dashboard/api/keys/{key_id}/rotate", headers=headers)
    assert rotated.status_code == 200
    assert rotated.json()["data"]["rawKey"].startswith("yf_test_")

    revoked = client.post(f"/dashboard/api/keys/{key_id}/revoke", headers=headers)
    assert revoked.status_code == 200

    with SessionLocal() as db:
        row = db.query(APIKey).filter(APIKey.id == int(key_id)).first()
        assert row is not None
        assert row.status == "revoked"

    activated = client.post(f"/dashboard/api/keys/{key_id}/activate", headers=headers)
    assert activated.status_code == 200

    with SessionLocal() as db:
        row = db.query(APIKey).filter(APIKey.id == int(key_id)).first()
        assert row is not None
        assert row.status == "active"


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

    create_a = client.post(
        "/dashboard/api/keys/create",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"label": "Tenant A", "env": "test"},
    )
    create_b = client.post(
        "/dashboard/api/keys/create",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"label": "Tenant B", "env": "test"},
    )
    assert create_a.status_code == 200
    assert create_b.status_code == 200

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

    assert payload_a["scope"]["tenantId"].startswith("user-")
    assert payload_b["scope"]["tenantId"].startswith("user-")
    assert targets_a.isdisjoint(targets_b)

    actors_a = {event["actor"] for event in payload_a["events"]}
    actors_b = {event["actor"] for event in payload_b["events"]}
    assert email_a in actors_a
    assert email_b in actors_b


@pytest.mark.e2e
def test_customer_dashboard_rotated_and_reactivated_key_controls_market_access(monkeypatch):
    import app.routes.market as market

    class DummyTicker:
        def __init__(self, symbol: str):
            self.symbol = symbol

        @property
        def fast_info(self):
            return {
                "currency": "USD",
                "exchange": "NASDAQ",
                "lastPrice": 211.0,
            }

    monkeypatch.setattr(market.yf, "Ticker", DummyTicker)

    email = _new_email()
    token = _register(email)
    _ensure_active_subscription(email)

    auth_headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/dashboard/api/keys/create",
        headers=auth_headers,
        json={"label": "Lifecycle Probe", "env": "test"},
    )
    assert create_response.status_code == 200
    create_payload = create_response.json()["data"]
    key_id = create_payload["key"]["id"]
    raw_key_v1 = create_payload["rawKey"]

    first_market_call = client.get("/v1/quote/AAPL", headers={"x-api-key": raw_key_v1})
    assert first_market_call.status_code == 200

    rotate_response = client.post(
        f"/dashboard/api/keys/{key_id}/rotate",
        headers=auth_headers,
    )
    assert rotate_response.status_code == 200
    raw_key_v2 = rotate_response.json()["data"]["rawKey"]
    assert raw_key_v2 != raw_key_v1

    old_key_after_rotate = client.get("/v1/quote/AAPL", headers={"x-api-key": raw_key_v1})
    assert old_key_after_rotate.status_code == 401
    assert old_key_after_rotate.json()["detail"] == "Invalid API key"

    new_key_after_rotate = client.get("/v1/quote/AAPL", headers={"x-api-key": raw_key_v2})
    assert new_key_after_rotate.status_code == 200

    revoke_response = client.post(
        f"/dashboard/api/keys/{key_id}/revoke",
        headers=auth_headers,
    )
    assert revoke_response.status_code == 200

    revoked_market_call = client.get("/v1/quote/AAPL", headers={"x-api-key": raw_key_v2})
    assert revoked_market_call.status_code == 401
    assert revoked_market_call.json()["detail"] == "Invalid API key"

    activate_response = client.post(
        f"/dashboard/api/keys/{key_id}/activate",
        headers=auth_headers,
    )
    assert activate_response.status_code == 200

    reactivated_market_call = client.get("/v1/quote/AAPL", headers={"x-api-key": raw_key_v2})
    assert reactivated_market_call.status_code == 200

    overview_response = client.get("/dashboard/api/overview?range=24h", headers=auth_headers)
    assert overview_response.status_code == 200
    overview_payload = overview_response.json()
    assert overview_payload["requests"] >= 3


def test_customer_dashboard_overview_and_metrics_use_real_usage_data(monkeypatch):
    import app.routes.market as market

    class DummyTicker:
        def __init__(self, symbol: str):
            self.symbol = symbol

        @property
        def fast_info(self):
            return {
                "currency": "USD",
                "exchange": "NASDAQ",
                "lastPrice": 123.45,
                "open": 121.0,
                "dayHigh": 124.0,
                "dayLow": 120.5,
                "previousClose": 122.5,
                "lastVolume": 1000000,
                "marketCap": 1000000000,
            }

    monkeypatch.setattr(market.yf, "Ticker", DummyTicker)

    email = _new_email()
    token = _register(email)
    _ensure_active_subscription(email)

    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/dashboard/api/keys/create",
        headers=headers,
        json={"label": "Usage Probe", "env": "test"},
    )
    assert created.status_code == 200
    raw_key = created.json()["data"]["rawKey"]

    before = client.get("/dashboard/api/overview?range=24h", headers=headers)
    assert before.status_code == 200
    before_payload = before.json()
    assert before_payload["requests"] == 0

    call_quote = client.get("/v1/quote/AAPL", headers={"x-api-key": raw_key})
    assert call_quote.status_code == 200

    after_overview = client.get("/dashboard/api/overview?range=24h", headers=headers)
    assert after_overview.status_code == 200
    overview_payload = after_overview.json()
    assert overview_payload["source"] == "customer-db-store"
    assert overview_payload["requests"] >= 1
    assert overview_payload["totalKeys"] >= 1
    assert any(entry["path"] == "/v1/quote/{symbol}" for entry in overview_payload["topEndpoints"])

    metrics = client.get("/dashboard/api/metrics?range=24h", headers=headers)
    assert metrics.status_code == 200
    metrics_payload = metrics.json()
    assert metrics_payload["source"] == "customer-db-store"
    assert metrics_payload["summary"]["requests"] >= 1
    assert any(entry["path"] == "/v1/quote/{symbol}" for entry in metrics_payload["topEndpoints"])


def test_customer_dashboard_activity_uses_db_events(monkeypatch):
    import app.routes.market as market

    class DummyTicker:
        def __init__(self, symbol: str):
            self.symbol = symbol

        @property
        def fast_info(self):
            return {
                "currency": "USD",
                "exchange": "NASDAQ",
                "lastPrice": 99.5,
            }

    monkeypatch.setattr(market.yf, "Ticker", DummyTicker)

    email = _new_email()
    token = _register(email)
    _ensure_active_subscription(email)
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/dashboard/api/keys/create",
        headers=headers,
        json={"label": "Activity Probe", "env": "test"},
    )
    assert created.status_code == 200
    raw_key = created.json()["data"]["rawKey"]

    quote = client.get("/v1/quote/MSFT", headers={"x-api-key": raw_key})
    assert quote.status_code == 200

    activity = client.get("/dashboard/api/activity?limit=20", headers=headers)
    assert activity.status_code == 200
    payload = activity.json()
    assert payload["source"] == "customer-db-store"
    assert any(event["action"] == "usage.request" and event["target"] == "/v1/quote/{symbol}" for event in payload["events"])
    assert any(event["action"] == "key.create" for event in payload["events"])


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
