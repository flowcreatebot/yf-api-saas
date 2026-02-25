import os

import httpx
import pytest

pytestmark = [pytest.mark.e2e]


def _base_url() -> str:
    return os.getenv("DEPLOYED_BASE_URL", "").strip().rstrip("/")


def _api_key() -> str:
    return os.getenv("DEPLOYED_API_KEY", "").strip()


def _expect_dashboard_checks() -> bool:
    return os.getenv("DEPLOYED_EXPECT_DASHBOARD", "").strip().lower() in {"1", "true", "yes", "on"}


def _expect_webhook_secret_checks() -> bool:
    return os.getenv("DEPLOYED_EXPECT_STRIPE_WEBHOOK_SECRET", "").strip().lower() in {"1", "true", "yes", "on"}


def _expect_stripe_checkout_checks() -> bool:
    return os.getenv("DEPLOYED_EXPECT_STRIPE_CHECKOUT", "").strip().lower() in {"1", "true", "yes", "on"}


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
def dashboard_checks_enabled() -> bool:
    if not _expect_dashboard_checks():
        pytest.skip("DEPLOYED_EXPECT_DASHBOARD is not enabled; skipping deployed dashboard canaries")
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
def test_deployed_quote_with_real_key_if_provided(deployed_client: httpx.Client):
    api_key = _api_key()
    if not api_key:
        pytest.skip("DEPLOYED_API_KEY not provided; skipping authenticated deployed quote check")

    response = deployed_client.get("/v1/quote/AAPL", headers={"x-api-key": api_key})
    assert response.status_code == 200

    payload = response.json()
    assert payload.get("symbol") == "AAPL"
    assert payload.get("last_price") is not None


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
def test_deployed_history_with_real_key_if_provided(deployed_client: httpx.Client):
    api_key = _api_key()
    if not api_key:
        pytest.skip("DEPLOYED_API_KEY not provided; skipping authenticated deployed history check")

    response = deployed_client.get(
        "/v1/history/AAPL?period=5d&interval=1d",
        headers={"x-api-key": api_key},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload.get("symbol") == "AAPL"
    assert payload.get("period") == "5d"
    assert payload.get("interval") == "1d"
    assert isinstance(payload.get("data"), list)
    assert payload.get("count", 0) >= 1

    first_row = payload["data"][0]
    for key in ("ts", "open", "high", "low", "close", "volume"):
        assert key in first_row


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
def test_deployed_fundamentals_with_real_key_if_provided(deployed_client: httpx.Client):
    api_key = _api_key()
    if not api_key:
        pytest.skip("DEPLOYED_API_KEY not provided; skipping authenticated deployed fundamentals check")

    response = deployed_client.get("/v1/fundamentals/AAPL", headers={"x-api-key": api_key})
    assert response.status_code == 200

    payload = response.json()
    assert payload.get("symbol") == "AAPL"
    assert payload.get("stale") in (False, True)
    for key in ("long_name", "sector", "industry"):
        assert key in payload


@pytest.mark.deployed
@pytest.mark.billing
@pytest.mark.critical
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
def test_deployed_internal_root_redirects_to_dashboard(
    deployed_client: httpx.Client,
    dashboard_checks_enabled: bool,
):
    response = deployed_client.get("/internal", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers.get("location") == "/internal/dashboard/"


@pytest.mark.deployed
@pytest.mark.critical
def test_deployed_dashboard_shell_available(
    deployed_client: httpx.Client,
    dashboard_checks_enabled: bool,
):
    response = deployed_client.get("/internal/dashboard/")
    assert response.status_code == 200
    assert "Y Finance Dashboard" in response.text


@pytest.mark.deployed
@pytest.mark.critical
def test_deployed_dashboard_overview_api_contract(
    deployed_client: httpx.Client,
    dashboard_checks_enabled: bool,
):
    response = deployed_client.get("/internal/api/overview?range=24h")
    assert response.status_code == 200

    payload = response.json()
    assert payload.get("source") == "placeholder"
    assert payload.get("range") == "24h"
    assert isinstance(payload.get("topEndpoints"), list)
    assert payload.get("topEndpoints"), "Expected at least one endpoint in dashboard overview"
