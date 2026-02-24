import os

import httpx
import pytest


def _base_url() -> str:
    return os.getenv("DEPLOYED_BASE_URL", "").strip().rstrip("/")


def _api_key() -> str:
    return os.getenv("DEPLOYED_API_KEY", "").strip()


def _expect_dashboard_checks() -> bool:
    return os.getenv("DEPLOYED_EXPECT_DASHBOARD", "").strip().lower() in {"1", "true", "yes", "on"}


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
    assert "price" in payload


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
