import os
from uuid import uuid4

import httpx
import pytest

pytestmark = [pytest.mark.e2e]


def _base_url() -> str:
    return os.getenv("DEPLOYED_BASE_URL", "").strip().rstrip("/")


def _api_key() -> str:
    return os.getenv("DEPLOYED_API_KEY", "").strip()


def _expect_webhook_secret_checks() -> bool:
    return os.getenv("DEPLOYED_EXPECT_STRIPE_WEBHOOK_SECRET", "").strip().lower() in {"1", "true", "yes", "on"}


def _expect_stripe_checkout_checks() -> bool:
    return os.getenv("DEPLOYED_EXPECT_STRIPE_CHECKOUT", "").strip().lower() in {"1", "true", "yes", "on"}


def _expect_customer_dashboard_checks() -> bool:
    return os.getenv("DEPLOYED_EXPECT_CUSTOMER_DASHBOARD", "").strip().lower() in {"1", "true", "yes", "on"}


@pytest.fixture(scope="module")
def deployed_base_url() -> str:
    base_url = _base_url()
    if not base_url:
        pytest.skip("DEPLOYED_BASE_URL is not set; skipping deployed smoke tests")
    return base_url


@pytest.fixture(scope="module")
def deployed_client(deployed_base_url: str):
    with httpx.Client(base_url=deployed_base_url, timeout=20.0, follow_redirects=True) as client:
        yield client


@pytest.fixture(scope="module")
def customer_dashboard_checks_enabled() -> bool:
    if not _expect_customer_dashboard_checks():
        pytest.skip(
            "DEPLOYED_EXPECT_CUSTOMER_DASHBOARD is not enabled; skipping deployed customer dashboard session canaries"
        )
    return True


@pytest.mark.deployed
@pytest.mark.critical
def test_deployed_health_endpoint_ok(deployed_client: httpx.Client):
    response = deployed_client.get("/v1/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload.get("ok") is True


@pytest.mark.deployed
@pytest.mark.billing
@pytest.mark.critical
def test_deployed_public_billing_plans_contract(deployed_client: httpx.Client):
    response = deployed_client.get("/v1/billing/plans")
    assert response.status_code == 200

    payload = response.json()
    assert isinstance(payload.get("plans"), list)
    assert payload["plans"], "Expected at least one plan in deployed billing response"

    first_plan = payload["plans"][0]
    for key in ("id", "name", "price_usd", "interval"):
        assert key in first_plan


@pytest.mark.deployed
@pytest.mark.critical
def test_deployed_protected_quote_requires_api_key(deployed_client: httpx.Client):
    response = deployed_client.get("/v1/quote/AAPL")
    assert response.status_code == 401
    assert response.json().get("detail") == "Missing API key"


@pytest.mark.deployed
@pytest.mark.critical
def test_deployed_quote_rejects_invalid_api_key(deployed_client: httpx.Client):
    response = deployed_client.get("/v1/quote/AAPL", headers={"x-api-key": "invalid-smoke-key"})
    assert response.status_code == 401
    assert response.json().get("detail") == "Invalid API key"


@pytest.mark.deployed
@pytest.mark.critical
def test_deployed_quote_auth_precedence_hides_symbol_validation(deployed_client: httpx.Client):
    response = deployed_client.get("/v1/quote/@@@", headers={"x-api-key": "invalid-smoke-key"})
    assert response.status_code == 401

    payload = response.json()
    assert payload.get("detail") == "Invalid API key"


@pytest.mark.deployed
@pytest.mark.critical
def test_deployed_quote_with_real_key_if_provided(deployed_client: httpx.Client):
    api_key = _api_key()
    if not api_key:
        pytest.skip("DEPLOYED_API_KEY not provided; skipping authenticated deployed quote check")

    response = deployed_client.get("/v1/quote/AAPL", headers={"x-api-key": api_key})
    assert response.status_code in (200, 502)

    payload = response.json()
    if response.status_code == 200:
        assert payload.get("symbol") == "AAPL"
        assert payload.get("last_price") is not None
    else:
        assert "Upstream provider error" in payload.get("detail", "")


@pytest.mark.deployed
@pytest.mark.critical
def test_deployed_protected_history_requires_api_key(deployed_client: httpx.Client):
    response = deployed_client.get("/v1/history/AAPL?period=5d&interval=1d")
    assert response.status_code == 401
    assert response.json().get("detail") == "Missing API key"


@pytest.mark.deployed
@pytest.mark.critical
def test_deployed_history_rejects_invalid_api_key(deployed_client: httpx.Client):
    response = deployed_client.get(
        "/v1/history/AAPL?period=5d&interval=1d",
        headers={"x-api-key": "invalid-smoke-key"},
    )
    assert response.status_code == 401
    assert response.json().get("detail") == "Invalid API key"


@pytest.mark.deployed
@pytest.mark.critical
def test_deployed_history_auth_precedence_hides_query_validation(deployed_client: httpx.Client):
    response = deployed_client.get(
        "/v1/history/@@@?period=not-a-real-period&interval=bogus",
        headers={"x-api-key": "invalid-smoke-key"},
    )
    assert response.status_code == 401

    payload = response.json()
    assert payload.get("detail") == "Invalid API key"


@pytest.mark.deployed
@pytest.mark.critical
def test_deployed_history_with_real_key_if_provided(deployed_client: httpx.Client):
    api_key = _api_key()
    if not api_key:
        pytest.skip("DEPLOYED_API_KEY not provided; skipping authenticated deployed history check")

    response = deployed_client.get(
        "/v1/history/AAPL?period=5d&interval=1d",
        headers={"x-api-key": api_key},
    )
    assert response.status_code in (200, 502)

    payload = response.json()
    if response.status_code == 200:
        assert payload.get("symbol") == "AAPL"
        assert payload.get("period") == "5d"
        assert payload.get("interval") == "1d"
        assert isinstance(payload.get("data"), list)
        assert payload.get("count", 0) >= 1

        first_row = payload["data"][0]
        for key in ("ts", "open", "high", "low", "close", "volume"):
            assert key in first_row
    else:
        assert "Upstream provider error" in payload.get("detail", "")


@pytest.mark.deployed
@pytest.mark.critical
def test_deployed_bulk_quotes_requires_api_key(deployed_client: httpx.Client):
    response = deployed_client.get("/v1/quotes?symbols=AAPL,MSFT")
    assert response.status_code == 401
    assert response.json().get("detail") == "Missing API key"


@pytest.mark.deployed
@pytest.mark.critical
def test_deployed_bulk_quotes_rejects_invalid_api_key(deployed_client: httpx.Client):
    response = deployed_client.get(
        "/v1/quotes?symbols=AAPL,MSFT",
        headers={"x-api-key": "invalid-smoke-key"},
    )
    assert response.status_code == 401
    assert response.json().get("detail") == "Invalid API key"


@pytest.mark.deployed
@pytest.mark.critical
def test_deployed_bulk_quotes_auth_precedence_hides_symbols_validation(deployed_client: httpx.Client):
    response = deployed_client.get(
        "/v1/quotes?symbols=@@@",
        headers={"x-api-key": "invalid-smoke-key"},
    )
    assert response.status_code == 401

    payload = response.json()
    assert payload.get("detail") == "Invalid API key"


@pytest.mark.deployed
@pytest.mark.critical
def test_deployed_bulk_quotes_with_real_key_if_provided(deployed_client: httpx.Client):
    api_key = _api_key()
    if not api_key:
        pytest.skip("DEPLOYED_API_KEY not provided; skipping authenticated deployed bulk quotes check")

    response = deployed_client.get(
        "/v1/quotes?symbols=AAPL,MSFT",
        headers={"x-api-key": api_key},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload.get("count") == 2
    assert isinstance(payload.get("data"), list)
    assert len(payload["data"]) == 2

    symbols_seen = set()
    for row in payload["data"]:
        assert row.get("symbol") in {"AAPL", "MSFT"}
        assert isinstance(row.get("ok"), bool)
        symbols_seen.add(row.get("symbol"))
    assert symbols_seen == {"AAPL", "MSFT"}


@pytest.mark.deployed
@pytest.mark.critical
def test_deployed_fundamentals_requires_api_key(deployed_client: httpx.Client):
    response = deployed_client.get("/v1/fundamentals/AAPL")
    assert response.status_code == 401
    assert response.json().get("detail") == "Missing API key"


@pytest.mark.deployed
@pytest.mark.critical
def test_deployed_fundamentals_rejects_invalid_api_key(deployed_client: httpx.Client):
    response = deployed_client.get("/v1/fundamentals/AAPL", headers={"x-api-key": "invalid-smoke-key"})
    assert response.status_code == 401
    assert response.json().get("detail") == "Invalid API key"


@pytest.mark.deployed
@pytest.mark.critical
def test_deployed_fundamentals_auth_precedence_hides_symbol_validation(
    deployed_client: httpx.Client,
):
    response = deployed_client.get(
        "/v1/fundamentals/@@@",
        headers={"x-api-key": "invalid-smoke-key"},
    )
    assert response.status_code == 401

    payload = response.json()
    assert payload.get("detail") == "Invalid API key"


@pytest.mark.deployed
@pytest.mark.critical
def test_deployed_fundamentals_with_real_key_if_provided(deployed_client: httpx.Client):
    api_key = _api_key()
    if not api_key:
        pytest.skip("DEPLOYED_API_KEY not provided; skipping authenticated deployed fundamentals check")

    response = deployed_client.get("/v1/fundamentals/AAPL", headers={"x-api-key": api_key})
    assert response.status_code in (200, 502)

    payload = response.json()
    if response.status_code == 200:
        assert payload.get("symbol") == "AAPL"
        assert payload.get("stale") in (False, True)
        for key in ("long_name", "sector", "industry"):
            assert key in payload
    else:
        assert "Upstream provider error" in payload.get("detail", "")


@pytest.mark.deployed
@pytest.mark.billing
@pytest.mark.critical
@pytest.mark.mutation
def test_deployed_checkout_rejects_insecure_redirect_url(deployed_client: httpx.Client):
    response = deployed_client.post(
        "/v1/billing/checkout/session",
        json={
            "email": "deployed-smoke@example.com",
            "success_url": "http://evil.example/success",
            "cancel_url": "https://example.com/cancel",
        },
    )
    assert response.status_code == 422

    payload = response.json()
    detail = payload.get("detail")
    errors_blob = str(payload.get("errors", "")) + str(detail)
    assert "https" in errors_blob.lower()


@pytest.mark.deployed
@pytest.mark.billing
@pytest.mark.critical
@pytest.mark.mutation
def test_deployed_checkout_session_happy_path_or_expected_config_guard(
    deployed_client: httpx.Client,
):
    response = deployed_client.post(
        "/v1/billing/checkout/session",
        json={
            "email": "deployed-smoke@example.com",
            "success_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel",
        },
    )

    if _expect_stripe_checkout_checks():
        assert response.status_code == 200
    else:
        assert response.status_code in (200, 503)

    payload = response.json()
    if response.status_code == 200:
        assert payload.get("id")
        assert payload.get("url")
        assert str(payload.get("url", "")).startswith("https://")
    else:
        assert payload.get("detail") in {
            "Stripe secret key not configured",
            "Stripe monthly price id not configured",
        }


@pytest.mark.deployed
@pytest.mark.billing
@pytest.mark.critical
@pytest.mark.mutation
def test_deployed_webhook_requires_signature_header_or_secret_not_configured(
    deployed_client: httpx.Client,
):
    response = deployed_client.post("/v1/billing/webhook/stripe", content="{}")
    assert response.status_code in (400, 503)

    payload = response.json()
    if response.status_code == 400:
        assert payload.get("detail") == "Missing Stripe-Signature header"
    else:
        assert payload.get("detail") == "Stripe webhook secret not configured"


@pytest.mark.deployed
@pytest.mark.billing
@pytest.mark.critical
@pytest.mark.mutation
def test_deployed_webhook_rejects_invalid_signature_when_secret_enabled(
    deployed_client: httpx.Client,
):
    response = deployed_client.post(
        "/v1/billing/webhook/stripe",
        content="{}",
        headers={"Stripe-Signature": "smoke-invalid-signature"},
    )

    if _expect_webhook_secret_checks():
        assert response.status_code == 400
    else:
        assert response.status_code in (400, 503)

    payload = response.json()
    if response.status_code == 400:
        assert "Invalid webhook" in payload.get("detail", "")
    else:
        assert payload.get("detail") == "Stripe webhook secret not configured"


@pytest.mark.deployed
@pytest.mark.critical
@pytest.mark.mutation
def test_deployed_customer_session_login_me_logout_flow(
    deployed_client: httpx.Client,
    customer_dashboard_checks_enabled: bool,
):
    unauth = deployed_client.get("/dashboard/api/session/me")
    assert unauth.status_code == 401
    assert unauth.json().get("detail") == "Customer session required"

    email = f"deployed-customer-{uuid4().hex[:10]}@example.com"
    password = "SmokePass123!"

    register_response = deployed_client.post(
        "/dashboard/api/auth/register",
        json={
            "email": email,
            "password": password,
        },
    )
    assert register_response.status_code == 200

    login_response = deployed_client.post(
        "/dashboard/api/session/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert login_response.status_code == 200

    login_payload = login_response.json()
    assert login_payload.get("ok") is True
    assert login_payload.get("source") == "customer-db-session"
    session = login_payload.get("session") or {}
    token = session.get("token")
    assert token

    me_response = deployed_client.get(
        "/dashboard/api/session/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200

    me_payload = me_response.json()
    assert me_payload.get("ok") is True
    assert me_payload.get("source") == "customer-db-session"
    assert (me_payload.get("session") or {}).get("email") == email

    logout_response = deployed_client.post(
        "/dashboard/api/session/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_response.status_code == 200
    assert logout_response.json().get("ok") is True

    post_logout = deployed_client.get(
        "/dashboard/api/session/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert post_logout.status_code == 401
    assert post_logout.json().get("detail") == "Invalid customer session"


@pytest.mark.deployed
@pytest.mark.critical
@pytest.mark.mutation
def test_deployed_customer_created_key_enforces_api_auth(
    deployed_client: httpx.Client,
    customer_dashboard_checks_enabled: bool,
):
    email = f"deployed-key-{uuid4().hex[:10]}@example.com"
    password = "SmokePass123!"

    register_response = deployed_client.post(
        "/dashboard/api/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 200

    session = (register_response.json().get("session") or {})
    token = session.get("token")
    assert token

    auth_headers = {"Authorization": f"Bearer {token}"}

    create_key = deployed_client.post(
        "/dashboard/api/keys/create",
        headers=auth_headers,
        json={"label": "Deployed Smoke", "env": "test"},
    )
    assert create_key.status_code == 200

    key_payload = create_key.json().get("data") or {}
    raw_key = key_payload.get("rawKey")
    assert raw_key
    assert str(raw_key).startswith("yf_")

    before_overview = deployed_client.get(
        "/dashboard/api/overview?range=24h",
        headers=auth_headers,
    )
    assert before_overview.status_code == 200
    before_requests = int(before_overview.json().get("requests") or 0)

    quote_response = deployed_client.get(
        "/v1/quote/AAPL",
        headers={"x-api-key": raw_key},
    )
    assert quote_response.status_code in (200, 403, 502)

    quote_payload = quote_response.json()
    if quote_response.status_code == 200:
        assert quote_payload.get("symbol") == "AAPL"
        assert quote_payload.get("last_price") is not None
    elif quote_response.status_code == 403:
        assert quote_payload.get("detail") == "Subscription inactive"
    else:
        assert "Upstream provider error" in quote_payload.get("detail", "")

    after_overview = deployed_client.get(
        "/dashboard/api/overview?range=24h",
        headers=auth_headers,
    )
    assert after_overview.status_code == 200
    after_requests = int(after_overview.json().get("requests") or 0)

    if quote_response.status_code in (200, 502):
        assert after_requests >= before_requests + 1
    else:
        assert after_requests == before_requests


