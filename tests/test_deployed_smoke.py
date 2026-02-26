import hashlib
import hmac
import json
import os
import time
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


def _expect_stripe_mutation_e2e_checks() -> bool:
    return os.getenv("DEPLOYED_EXPECT_STRIPE_MUTATION_E2E", "").strip().lower() in {"1", "true", "yes", "on"}


def _stripe_webhook_secret() -> str:
    return os.getenv("DEPLOYED_STRIPE_WEBHOOK_SECRET", "").strip()


def _stripe_signature_header(payload: bytes, *, secret: str) -> str:
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.".encode("utf-8") + payload
    digest = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def _post_signed_webhook(deployed_client: httpx.Client, event: dict) -> httpx.Response:
    webhook_payload = json.dumps(event).encode("utf-8")
    signature_header = _stripe_signature_header(webhook_payload, secret=_stripe_webhook_secret())
    return deployed_client.post(
        "/v1/billing/webhook/stripe",
        content=webhook_payload,
        headers={
            "Content-Type": "application/json",
            "Stripe-Signature": signature_header,
        },
    )


def _user_id_from_tenant(tenant_id: str) -> int:
    if not tenant_id.startswith("user-"):
        raise AssertionError(f"Unexpected tenantId format: {tenant_id}")
    return int(tenant_id.split("-", 1)[1])


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


@pytest.fixture(scope="module")
def stripe_checkout_checks_enabled(customer_dashboard_checks_enabled: bool) -> bool:
    if not _expect_stripe_checkout_checks():
        pytest.skip(
            "DEPLOYED_EXPECT_STRIPE_CHECKOUT is not enabled; skipping deployed Stripe checkout session canaries"
        )

    return True


@pytest.fixture(scope="module")
def stripe_mutation_e2e_checks_enabled(customer_dashboard_checks_enabled: bool) -> bool:
    if not _expect_stripe_mutation_e2e_checks():
        pytest.skip(
            "DEPLOYED_EXPECT_STRIPE_MUTATION_E2E is not enabled; skipping deployed Stripe mutation e2e canary"
        )

    if not _expect_webhook_secret_checks():
        pytest.skip(
            "DEPLOYED_EXPECT_STRIPE_WEBHOOK_SECRET must be enabled for deployed Stripe mutation e2e canary"
        )

    if not _stripe_webhook_secret():
        pytest.skip(
            "DEPLOYED_STRIPE_WEBHOOK_SECRET is not set; skipping deployed Stripe mutation e2e canary"
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
@pytest.mark.checkout
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
@pytest.mark.checkout
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
@pytest.mark.checkout
def test_deployed_authenticated_checkout_links_to_customer_account(
    deployed_client: httpx.Client,
    deployed_base_url: str,
    stripe_checkout_checks_enabled: bool,
):
    email = f"deployed-checkout-{uuid4().hex[:10]}@example.com"
    password = "SmokePass123!"

    register_response = deployed_client.post(
        "/dashboard/api/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 200

    token = (((register_response.json().get("session") or {}).get("token")))
    assert token

    auth_headers = {"Authorization": f"Bearer {token}"}
    success_url = f"{deployed_base_url}/dashboard/?checkout=success"
    cancel_url = f"{deployed_base_url}/dashboard/?checkout=cancel"

    checkout_response = deployed_client.post(
        "/v1/billing/checkout/session",
        headers=auth_headers,
        json={
            "email": email,
            "success_url": success_url,
            "cancel_url": cancel_url,
        },
    )
    assert checkout_response.status_code == 200

    checkout_payload = checkout_response.json()
    assert checkout_payload.get("id")
    assert checkout_payload.get("url")
    assert str(checkout_payload.get("url", "")).startswith("https://")

    mismatched_email_response = deployed_client.post(
        "/v1/billing/checkout/session",
        headers=auth_headers,
        json={
            "email": f"mismatch-{uuid4().hex[:10]}@example.com",
            "success_url": success_url,
            "cancel_url": cancel_url,
        },
    )
    assert mismatched_email_response.status_code == 403
    assert mismatched_email_response.json().get("detail") == "Checkout email must match authenticated account"


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
@pytest.mark.billing
@pytest.mark.critical
@pytest.mark.mutation
def test_deployed_checkout_and_signed_webhook_activate_customer_subscription(
    deployed_client: httpx.Client,
    stripe_mutation_e2e_checks_enabled: bool,
):
    email = f"deployed-billing-{uuid4().hex[:10]}@example.com"
    password = "SmokePass123!"

    register_response = deployed_client.post(
        "/dashboard/api/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 200

    register_payload = register_response.json()
    session_payload = register_payload.get("session") or {}
    token = session_payload.get("token")
    tenant_id = session_payload.get("tenantId")
    assert token
    assert tenant_id

    auth_headers = {"Authorization": f"Bearer {token}"}

    create_key_response = deployed_client.post(
        "/dashboard/api/keys/create",
        headers=auth_headers,
        json={"label": "Stripe Mutation E2E", "env": "test"},
    )
    assert create_key_response.status_code == 200
    raw_key = ((create_key_response.json().get("data") or {}).get("rawKey"))
    assert raw_key

    pre_subscription_quote = deployed_client.get(
        "/v1/quote/AAPL",
        headers={"x-api-key": raw_key},
    )
    assert pre_subscription_quote.status_code == 403
    assert pre_subscription_quote.json().get("detail") == "Subscription inactive"

    user_id = _user_id_from_tenant(str(tenant_id))

    webhook_event = {
        "id": f"evt_smoke_{uuid4().hex[:14]}",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": f"cus_smoke_{uuid4().hex[:10]}",
                "subscription": f"sub_smoke_{uuid4().hex[:10]}",
                "customer_email": email,
                "payment_status": "paid",
                "metadata": {
                    "user_id": str(user_id),
                    "email": email,
                    "plan_id": "starter-monthly",
                },
            }
        },
    }

    webhook_response = _post_signed_webhook(deployed_client, webhook_event)
    assert webhook_response.status_code == 200
    webhook_body = webhook_response.json()
    assert webhook_body.get("received") is True
    assert webhook_body.get("type") == "checkout.session.completed"
    assert webhook_body.get("handled") is True

    post_subscription_quote = deployed_client.get(
        "/v1/quote/AAPL",
        headers={"x-api-key": raw_key},
    )
    assert post_subscription_quote.status_code in (200, 502)

    post_payload = post_subscription_quote.json()
    if post_subscription_quote.status_code == 200:
        assert post_payload.get("symbol") == "AAPL"
        assert post_payload.get("last_price") is not None
    else:
        assert "Upstream provider error" in post_payload.get("detail", "")


@pytest.mark.deployed
@pytest.mark.billing
@pytest.mark.critical
@pytest.mark.mutation
def test_deployed_checkout_signed_webhook_is_idempotent_for_first_key_provisioning(
    deployed_client: httpx.Client,
    stripe_mutation_e2e_checks_enabled: bool,
):
    email = f"deployed-idempotent-{uuid4().hex[:10]}@example.com"
    password = "SmokePass123!"

    register_response = deployed_client.post(
        "/dashboard/api/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 200

    register_payload = register_response.json()
    session_payload = register_payload.get("session") or {}
    token = session_payload.get("token")
    tenant_id = session_payload.get("tenantId")
    assert token
    assert tenant_id

    auth_headers = {"Authorization": f"Bearer {token}"}

    pre_keys_response = deployed_client.get("/dashboard/api/keys", headers=auth_headers)
    assert pre_keys_response.status_code == 200
    pre_keys = ((pre_keys_response.json().get("data") or {}).get("keys") or [])
    assert pre_keys == []

    user_id = _user_id_from_tenant(str(tenant_id))
    webhook_event = {
        "id": f"evt_smoke_{uuid4().hex[:14]}",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": f"cus_smoke_{uuid4().hex[:10]}",
                "subscription": f"sub_smoke_{uuid4().hex[:10]}",
                "customer_email": email,
                "payment_status": "paid",
                "metadata": {
                    "user_id": str(user_id),
                    "email": email,
                    "plan_id": "starter-monthly",
                },
            }
        },
    }

    first_webhook = _post_signed_webhook(deployed_client, webhook_event)
    assert first_webhook.status_code == 200
    first_body = first_webhook.json()
    assert first_body.get("received") is True
    assert first_body.get("type") == "checkout.session.completed"
    assert first_body.get("handled") is True
    assert first_body.get("provisioned_key") is True

    first_keys_response = deployed_client.get("/dashboard/api/keys", headers=auth_headers)
    assert first_keys_response.status_code == 200
    first_keys = ((first_keys_response.json().get("data") or {}).get("keys") or [])
    assert len(first_keys) == 1
    assert first_keys[0].get("active") is True

    second_webhook = _post_signed_webhook(deployed_client, webhook_event)
    assert second_webhook.status_code == 200
    second_body = second_webhook.json()
    assert second_body.get("received") is True
    assert second_body.get("type") == "checkout.session.completed"
    assert second_body.get("handled") is True
    assert second_body.get("provisioned_key") is False

    second_keys_response = deployed_client.get("/dashboard/api/keys", headers=auth_headers)
    assert second_keys_response.status_code == 200
    second_keys = ((second_keys_response.json().get("data") or {}).get("keys") or [])
    assert len(second_keys) == 1
    assert second_keys[0].get("id") == first_keys[0].get("id")
    assert second_keys[0].get("active") is True


@pytest.mark.deployed
@pytest.mark.billing
@pytest.mark.critical
@pytest.mark.mutation
def test_deployed_checkout_no_payment_required_provisions_trialing_first_key_idempotently(
    deployed_client: httpx.Client,
    stripe_mutation_e2e_checks_enabled: bool,
):
    email = f"deployed-checkout-trialing-{uuid4().hex[:10]}@example.com"
    password = "SmokePass123!"

    register_response = deployed_client.post(
        "/dashboard/api/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 200

    session_payload = (register_response.json().get("session") or {})
    token = session_payload.get("token")
    tenant_id = session_payload.get("tenantId")
    assert token
    assert tenant_id

    auth_headers = {"Authorization": f"Bearer {token}"}

    pre_keys_response = deployed_client.get("/dashboard/api/keys", headers=auth_headers)
    assert pre_keys_response.status_code == 200
    pre_keys_payload = pre_keys_response.json()
    assert pre_keys_payload.get("source") == "customer-db-store"
    pre_keys = ((pre_keys_payload.get("data") or {}).get("keys") or [])
    assert pre_keys == []

    user_id = _user_id_from_tenant(str(tenant_id))
    customer_id = f"cus_checkout_trialing_{uuid4().hex[:10]}"
    subscription_id = f"sub_checkout_trialing_{uuid4().hex[:10]}"

    checkout_trialing_event = {
        "id": f"evt_smoke_{uuid4().hex[:14]}",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": customer_id,
                "subscription": subscription_id,
                "customer_email": email,
                "payment_status": "no_payment_required",
                "metadata": {
                    "user_id": str(user_id),
                    "email": email,
                    "plan_id": "starter-monthly",
                },
            }
        },
    }

    first_webhook = _post_signed_webhook(deployed_client, checkout_trialing_event)
    assert first_webhook.status_code == 200
    first_payload = first_webhook.json()
    assert first_payload.get("received") is True
    assert first_payload.get("type") == "checkout.session.completed"
    assert first_payload.get("handled") is True
    assert first_payload.get("provisioned_key") is True

    keys_after_first_response = deployed_client.get("/dashboard/api/keys", headers=auth_headers)
    assert keys_after_first_response.status_code == 200
    keys_after_first_payload = keys_after_first_response.json()
    assert keys_after_first_payload.get("source") == "customer-db-store"
    keys_after_first = ((keys_after_first_payload.get("data") or {}).get("keys") or [])
    assert len(keys_after_first) == 1
    assert keys_after_first[0].get("active") is True

    duplicate_webhook = _post_signed_webhook(deployed_client, checkout_trialing_event)
    assert duplicate_webhook.status_code == 200
    duplicate_payload = duplicate_webhook.json()
    assert duplicate_payload.get("received") is True
    assert duplicate_payload.get("type") == "checkout.session.completed"
    assert duplicate_payload.get("handled") is True
    assert duplicate_payload.get("provisioned_key") is False

    keys_after_duplicate_response = deployed_client.get("/dashboard/api/keys", headers=auth_headers)
    assert keys_after_duplicate_response.status_code == 200
    keys_after_duplicate_payload = keys_after_duplicate_response.json()
    assert keys_after_duplicate_payload.get("source") == "customer-db-store"
    keys_after_duplicate = ((keys_after_duplicate_payload.get("data") or {}).get("keys") or [])
    assert len(keys_after_duplicate) == 1
    assert keys_after_duplicate[0].get("id") == keys_after_first[0].get("id")
    assert keys_after_duplicate[0].get("active") is True


@pytest.mark.deployed
@pytest.mark.billing
@pytest.mark.critical
@pytest.mark.mutation
def test_deployed_unpaid_checkout_then_subscription_updated_active_provisions_first_key_idempotently(
    deployed_client: httpx.Client,
    stripe_mutation_e2e_checks_enabled: bool,
):
    email = f"deployed-sub-updated-{uuid4().hex[:10]}@example.com"
    password = "SmokePass123!"

    register_response = deployed_client.post(
        "/dashboard/api/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 200

    session_payload = (register_response.json().get("session") or {})
    token = session_payload.get("token")
    tenant_id = session_payload.get("tenantId")
    assert token
    assert tenant_id

    auth_headers = {"Authorization": f"Bearer {token}"}

    pre_keys_response = deployed_client.get("/dashboard/api/keys", headers=auth_headers)
    assert pre_keys_response.status_code == 200
    pre_keys_payload = pre_keys_response.json()
    assert pre_keys_payload.get("source") == "customer-db-store"
    pre_keys = ((pre_keys_payload.get("data") or {}).get("keys") or [])
    assert pre_keys == []

    user_id = _user_id_from_tenant(str(tenant_id))
    customer_id = f"cus_sub_updated_{uuid4().hex[:10]}"
    subscription_id = f"sub_sub_updated_{uuid4().hex[:10]}"

    checkout_unpaid_event = {
        "id": f"evt_smoke_{uuid4().hex[:14]}",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": customer_id,
                "subscription": subscription_id,
                "customer_email": email,
                "payment_status": "unpaid",
                "metadata": {
                    "user_id": str(user_id),
                    "email": email,
                    "plan_id": "starter-monthly",
                },
            }
        },
    }

    unpaid_webhook = _post_signed_webhook(deployed_client, checkout_unpaid_event)
    assert unpaid_webhook.status_code == 200
    unpaid_payload = unpaid_webhook.json()
    assert unpaid_payload.get("received") is True
    assert unpaid_payload.get("type") == "checkout.session.completed"
    assert unpaid_payload.get("handled") is True
    assert unpaid_payload.get("provisioned_key") is False

    keys_after_unpaid_response = deployed_client.get("/dashboard/api/keys", headers=auth_headers)
    assert keys_after_unpaid_response.status_code == 200
    keys_after_unpaid_payload = keys_after_unpaid_response.json()
    assert keys_after_unpaid_payload.get("source") == "customer-db-store"
    keys_after_unpaid = ((keys_after_unpaid_payload.get("data") or {}).get("keys") or [])
    assert keys_after_unpaid == []

    subscription_updated_active_event = {
        "id": f"evt_smoke_{uuid4().hex[:14]}",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": subscription_id,
                "customer": customer_id,
                "status": "active",
                "current_period_end": int(time.time()) + 3600,
            }
        },
    }

    first_update_webhook = _post_signed_webhook(deployed_client, subscription_updated_active_event)
    assert first_update_webhook.status_code == 200
    first_update_payload = first_update_webhook.json()
    assert first_update_payload.get("received") is True
    assert first_update_payload.get("type") == "customer.subscription.updated"
    assert first_update_payload.get("handled") is True
    assert first_update_payload.get("provisioned_key") is True

    keys_after_first_update_response = deployed_client.get("/dashboard/api/keys", headers=auth_headers)
    assert keys_after_first_update_response.status_code == 200
    keys_after_first_update_payload = keys_after_first_update_response.json()
    assert keys_after_first_update_payload.get("source") == "customer-db-store"
    keys_after_first_update = ((keys_after_first_update_payload.get("data") or {}).get("keys") or [])
    assert len(keys_after_first_update) == 1
    assert keys_after_first_update[0].get("active") is True

    duplicate_update_webhook = _post_signed_webhook(deployed_client, subscription_updated_active_event)
    assert duplicate_update_webhook.status_code == 200
    duplicate_update_payload = duplicate_update_webhook.json()
    assert duplicate_update_payload.get("received") is True
    assert duplicate_update_payload.get("type") == "customer.subscription.updated"
    assert duplicate_update_payload.get("handled") is True
    assert duplicate_update_payload.get("provisioned_key") is False

    keys_after_duplicate_response = deployed_client.get("/dashboard/api/keys", headers=auth_headers)
    assert keys_after_duplicate_response.status_code == 200
    keys_after_duplicate_payload = keys_after_duplicate_response.json()
    assert keys_after_duplicate_payload.get("source") == "customer-db-store"
    keys_after_duplicate = ((keys_after_duplicate_payload.get("data") or {}).get("keys") or [])
    assert len(keys_after_duplicate) == 1
    assert keys_after_duplicate[0].get("id") == keys_after_first_update[0].get("id")
    assert keys_after_duplicate[0].get("active") is True


@pytest.mark.deployed
@pytest.mark.billing
@pytest.mark.critical
@pytest.mark.mutation
def test_deployed_unpaid_checkout_then_subscription_updated_trialing_provisions_first_key_idempotently(
    deployed_client: httpx.Client,
    stripe_mutation_e2e_checks_enabled: bool,
):
    email = f"deployed-sub-trialing-{uuid4().hex[:10]}@example.com"
    password = "SmokePass123!"

    register_response = deployed_client.post(
        "/dashboard/api/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 200

    session_payload = (register_response.json().get("session") or {})
    token = session_payload.get("token")
    tenant_id = session_payload.get("tenantId")
    assert token
    assert tenant_id

    auth_headers = {"Authorization": f"Bearer {token}"}

    pre_keys_response = deployed_client.get("/dashboard/api/keys", headers=auth_headers)
    assert pre_keys_response.status_code == 200
    pre_keys_payload = pre_keys_response.json()
    assert pre_keys_payload.get("source") == "customer-db-store"
    pre_keys = ((pre_keys_payload.get("data") or {}).get("keys") or [])
    assert pre_keys == []

    user_id = _user_id_from_tenant(str(tenant_id))
    customer_id = f"cus_sub_trialing_{uuid4().hex[:10]}"
    subscription_id = f"sub_sub_trialing_{uuid4().hex[:10]}"

    checkout_unpaid_event = {
        "id": f"evt_smoke_{uuid4().hex[:14]}",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": customer_id,
                "subscription": subscription_id,
                "customer_email": email,
                "payment_status": "unpaid",
                "metadata": {
                    "user_id": str(user_id),
                    "email": email,
                    "plan_id": "starter-monthly",
                },
            }
        },
    }

    unpaid_webhook = _post_signed_webhook(deployed_client, checkout_unpaid_event)
    assert unpaid_webhook.status_code == 200
    unpaid_payload = unpaid_webhook.json()
    assert unpaid_payload.get("received") is True
    assert unpaid_payload.get("type") == "checkout.session.completed"
    assert unpaid_payload.get("handled") is True
    assert unpaid_payload.get("provisioned_key") is False

    subscription_updated_trialing_event = {
        "id": f"evt_smoke_{uuid4().hex[:14]}",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": subscription_id,
                "customer": customer_id,
                "status": "trialing",
                "current_period_end": int(time.time()) + 3600,
            }
        },
    }

    first_update_webhook = _post_signed_webhook(deployed_client, subscription_updated_trialing_event)
    assert first_update_webhook.status_code == 200
    first_update_payload = first_update_webhook.json()
    assert first_update_payload.get("received") is True
    assert first_update_payload.get("type") == "customer.subscription.updated"
    assert first_update_payload.get("handled") is True
    assert first_update_payload.get("provisioned_key") is True

    keys_after_first_update_response = deployed_client.get("/dashboard/api/keys", headers=auth_headers)
    assert keys_after_first_update_response.status_code == 200
    keys_after_first_update_payload = keys_after_first_update_response.json()
    assert keys_after_first_update_payload.get("source") == "customer-db-store"
    keys_after_first_update = ((keys_after_first_update_payload.get("data") or {}).get("keys") or [])
    assert len(keys_after_first_update) == 1
    assert keys_after_first_update[0].get("active") is True

    duplicate_update_webhook = _post_signed_webhook(deployed_client, subscription_updated_trialing_event)
    assert duplicate_update_webhook.status_code == 200
    duplicate_update_payload = duplicate_update_webhook.json()
    assert duplicate_update_payload.get("received") is True
    assert duplicate_update_payload.get("type") == "customer.subscription.updated"
    assert duplicate_update_payload.get("handled") is True
    assert duplicate_update_payload.get("provisioned_key") is False

    keys_after_duplicate_response = deployed_client.get("/dashboard/api/keys", headers=auth_headers)
    assert keys_after_duplicate_response.status_code == 200
    keys_after_duplicate_payload = keys_after_duplicate_response.json()
    assert keys_after_duplicate_payload.get("source") == "customer-db-store"
    keys_after_duplicate = ((keys_after_duplicate_payload.get("data") or {}).get("keys") or [])
    assert len(keys_after_duplicate) == 1
    assert keys_after_duplicate[0].get("id") == keys_after_first_update[0].get("id")
    assert keys_after_duplicate[0].get("active") is True


@pytest.mark.deployed
@pytest.mark.billing
@pytest.mark.critical
@pytest.mark.mutation
def test_deployed_unpaid_checkout_then_subscription_created_trialing_provisions_first_key_idempotently(
    deployed_client: httpx.Client,
    stripe_mutation_e2e_checks_enabled: bool,
):
    email = f"deployed-sub-created-{uuid4().hex[:10]}@example.com"
    password = "SmokePass123!"

    register_response = deployed_client.post(
        "/dashboard/api/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 200

    session_payload = (register_response.json().get("session") or {})
    token = session_payload.get("token")
    tenant_id = session_payload.get("tenantId")
    assert token
    assert tenant_id

    auth_headers = {"Authorization": f"Bearer {token}"}

    user_id = _user_id_from_tenant(str(tenant_id))
    customer_id = f"cus_sub_created_{uuid4().hex[:10]}"
    subscription_id = f"sub_sub_created_{uuid4().hex[:10]}"

    checkout_unpaid_event = {
        "id": f"evt_smoke_{uuid4().hex[:14]}",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": customer_id,
                "subscription": subscription_id,
                "customer_email": email,
                "payment_status": "unpaid",
                "metadata": {
                    "user_id": str(user_id),
                    "email": email,
                    "plan_id": "starter-monthly",
                },
            }
        },
    }

    unpaid_webhook = _post_signed_webhook(deployed_client, checkout_unpaid_event)
    assert unpaid_webhook.status_code == 200
    unpaid_payload = unpaid_webhook.json()
    assert unpaid_payload.get("received") is True
    assert unpaid_payload.get("type") == "checkout.session.completed"
    assert unpaid_payload.get("handled") is True
    assert unpaid_payload.get("provisioned_key") is False

    subscription_created_trialing_event = {
        "id": f"evt_smoke_{uuid4().hex[:14]}",
        "type": "customer.subscription.created",
        "data": {
            "object": {
                "id": subscription_id,
                "customer": customer_id,
                "status": "trialing",
                "current_period_end": int(time.time()) + 3600,
            }
        },
    }

    first_create_webhook = _post_signed_webhook(deployed_client, subscription_created_trialing_event)
    assert first_create_webhook.status_code == 200
    first_create_payload = first_create_webhook.json()
    assert first_create_payload.get("received") is True
    assert first_create_payload.get("type") == "customer.subscription.created"
    assert first_create_payload.get("handled") is True
    assert first_create_payload.get("provisioned_key") is True

    keys_after_first_create_response = deployed_client.get("/dashboard/api/keys", headers=auth_headers)
    assert keys_after_first_create_response.status_code == 200
    keys_after_first_create_payload = keys_after_first_create_response.json()
    assert keys_after_first_create_payload.get("source") == "customer-db-store"
    keys_after_first_create = ((keys_after_first_create_payload.get("data") or {}).get("keys") or [])
    assert len(keys_after_first_create) == 1
    assert keys_after_first_create[0].get("active") is True

    duplicate_create_webhook = _post_signed_webhook(deployed_client, subscription_created_trialing_event)
    assert duplicate_create_webhook.status_code == 200
    duplicate_create_payload = duplicate_create_webhook.json()
    assert duplicate_create_payload.get("received") is True
    assert duplicate_create_payload.get("type") == "customer.subscription.created"
    assert duplicate_create_payload.get("handled") is True
    assert duplicate_create_payload.get("provisioned_key") is False

    keys_after_duplicate_response = deployed_client.get("/dashboard/api/keys", headers=auth_headers)
    assert keys_after_duplicate_response.status_code == 200
    keys_after_duplicate_payload = keys_after_duplicate_response.json()
    assert keys_after_duplicate_payload.get("source") == "customer-db-store"
    keys_after_duplicate = ((keys_after_duplicate_payload.get("data") or {}).get("keys") or [])
    assert len(keys_after_duplicate) == 1
    assert keys_after_duplicate[0].get("id") == keys_after_first_create[0].get("id")
    assert keys_after_duplicate[0].get("active") is True


@pytest.mark.deployed
@pytest.mark.billing
@pytest.mark.critical
@pytest.mark.mutation
def test_deployed_unpaid_checkout_then_subscription_created_active_provisions_first_key_idempotently(
    deployed_client: httpx.Client,
    stripe_mutation_e2e_checks_enabled: bool,
):
    email = f"deployed-sub-created-active-{uuid4().hex[:10]}@example.com"
    password = "SmokePass123!"

    register_response = deployed_client.post(
        "/dashboard/api/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 200

    session_payload = (register_response.json().get("session") or {})
    token = session_payload.get("token")
    tenant_id = session_payload.get("tenantId")
    assert token
    assert tenant_id

    auth_headers = {"Authorization": f"Bearer {token}"}

    user_id = _user_id_from_tenant(str(tenant_id))
    customer_id = f"cus_sub_created_active_{uuid4().hex[:10]}"
    subscription_id = f"sub_sub_created_active_{uuid4().hex[:10]}"

    checkout_unpaid_event = {
        "id": f"evt_smoke_{uuid4().hex[:14]}",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": customer_id,
                "subscription": subscription_id,
                "customer_email": email,
                "payment_status": "unpaid",
                "metadata": {
                    "user_id": str(user_id),
                    "email": email,
                    "plan_id": "starter-monthly",
                },
            }
        },
    }

    unpaid_webhook = _post_signed_webhook(deployed_client, checkout_unpaid_event)
    assert unpaid_webhook.status_code == 200
    unpaid_payload = unpaid_webhook.json()
    assert unpaid_payload.get("received") is True
    assert unpaid_payload.get("type") == "checkout.session.completed"
    assert unpaid_payload.get("handled") is True
    assert unpaid_payload.get("provisioned_key") is False

    subscription_created_active_event = {
        "id": f"evt_smoke_{uuid4().hex[:14]}",
        "type": "customer.subscription.created",
        "data": {
            "object": {
                "id": subscription_id,
                "customer": customer_id,
                "status": "active",
                "current_period_end": int(time.time()) + 3600,
            }
        },
    }

    first_create_webhook = _post_signed_webhook(deployed_client, subscription_created_active_event)
    assert first_create_webhook.status_code == 200
    first_create_payload = first_create_webhook.json()
    assert first_create_payload.get("received") is True
    assert first_create_payload.get("type") == "customer.subscription.created"
    assert first_create_payload.get("handled") is True
    assert first_create_payload.get("provisioned_key") is True

    keys_after_first_create_response = deployed_client.get("/dashboard/api/keys", headers=auth_headers)
    assert keys_after_first_create_response.status_code == 200
    keys_after_first_create_payload = keys_after_first_create_response.json()
    assert keys_after_first_create_payload.get("source") == "customer-db-store"
    keys_after_first_create = ((keys_after_first_create_payload.get("data") or {}).get("keys") or [])
    assert len(keys_after_first_create) == 1
    assert keys_after_first_create[0].get("active") is True

    duplicate_create_webhook = _post_signed_webhook(deployed_client, subscription_created_active_event)
    assert duplicate_create_webhook.status_code == 200
    duplicate_create_payload = duplicate_create_webhook.json()
    assert duplicate_create_payload.get("received") is True
    assert duplicate_create_payload.get("type") == "customer.subscription.created"
    assert duplicate_create_payload.get("handled") is True
    assert duplicate_create_payload.get("provisioned_key") is False

    keys_after_duplicate_response = deployed_client.get("/dashboard/api/keys", headers=auth_headers)
    assert keys_after_duplicate_response.status_code == 200
    keys_after_duplicate_payload = keys_after_duplicate_response.json()
    assert keys_after_duplicate_payload.get("source") == "customer-db-store"
    keys_after_duplicate = ((keys_after_duplicate_payload.get("data") or {}).get("keys") or [])
    assert len(keys_after_duplicate) == 1
    assert keys_after_duplicate[0].get("id") == keys_after_first_create[0].get("id")
    assert keys_after_duplicate[0].get("active") is True


@pytest.mark.deployed
@pytest.mark.billing
@pytest.mark.critical
@pytest.mark.mutation
def test_deployed_subscription_deleted_webhook_revokes_market_access(
    deployed_client: httpx.Client,
    stripe_mutation_e2e_checks_enabled: bool,
):
    email = f"deployed-cancel-{uuid4().hex[:10]}@example.com"
    password = "SmokePass123!"

    register_response = deployed_client.post(
        "/dashboard/api/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 200

    register_payload = register_response.json()
    session_payload = register_payload.get("session") or {}
    token = session_payload.get("token")
    tenant_id = session_payload.get("tenantId")
    assert token
    assert tenant_id

    auth_headers = {"Authorization": f"Bearer {token}"}

    create_key_response = deployed_client.post(
        "/dashboard/api/keys/create",
        headers=auth_headers,
        json={"label": "Cancellation E2E", "env": "test"},
    )
    assert create_key_response.status_code == 200
    raw_key = ((create_key_response.json().get("data") or {}).get("rawKey"))
    assert raw_key

    user_id = _user_id_from_tenant(str(tenant_id))
    customer_id = f"cus_cancel_{uuid4().hex[:10]}"
    subscription_id = f"sub_cancel_{uuid4().hex[:10]}"

    activate_event = {
        "id": f"evt_smoke_{uuid4().hex[:14]}",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": customer_id,
                "subscription": subscription_id,
                "customer_email": email,
                "payment_status": "paid",
                "metadata": {
                    "user_id": str(user_id),
                    "email": email,
                    "plan_id": "starter-monthly",
                },
            }
        },
    }

    activate_webhook = _post_signed_webhook(deployed_client, activate_event)
    assert activate_webhook.status_code == 200
    activate_payload = activate_webhook.json()
    assert activate_payload.get("received") is True
    assert activate_payload.get("handled") is True

    active_quote = deployed_client.get("/v1/quote/AAPL", headers={"x-api-key": raw_key})
    assert active_quote.status_code in (200, 502)

    cancel_event = {
        "id": f"evt_smoke_{uuid4().hex[:14]}",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": subscription_id,
                "customer": customer_id,
                "status": "canceled",
                "current_period_end": int(time.time()),
            }
        },
    }

    cancel_webhook = _post_signed_webhook(deployed_client, cancel_event)
    assert cancel_webhook.status_code == 200
    cancel_payload = cancel_webhook.json()
    assert cancel_payload.get("received") is True
    assert cancel_payload.get("type") == "customer.subscription.deleted"
    assert cancel_payload.get("handled") is True

    post_cancel_quote = deployed_client.get("/v1/quote/AAPL", headers={"x-api-key": raw_key})
    assert post_cancel_quote.status_code == 403
    assert post_cancel_quote.json().get("detail") == "Subscription inactive"


@pytest.mark.deployed
@pytest.mark.billing
@pytest.mark.critical
@pytest.mark.mutation
def test_deployed_subscription_updated_webhook_restores_market_access(
    deployed_client: httpx.Client,
    stripe_mutation_e2e_checks_enabled: bool,
):
    email = f"deployed-reactivate-{uuid4().hex[:10]}@example.com"
    password = "SmokePass123!"

    register_response = deployed_client.post(
        "/dashboard/api/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 200

    session_payload = (register_response.json().get("session") or {})
    token = session_payload.get("token")
    tenant_id = session_payload.get("tenantId")
    assert token
    assert tenant_id

    auth_headers = {"Authorization": f"Bearer {token}"}

    create_key_response = deployed_client.post(
        "/dashboard/api/keys/create",
        headers=auth_headers,
        json={"label": "Reactivation E2E", "env": "test"},
    )
    assert create_key_response.status_code == 200
    raw_key = ((create_key_response.json().get("data") or {}).get("rawKey"))
    assert raw_key

    user_id = _user_id_from_tenant(str(tenant_id))
    customer_id = f"cus_reactivate_{uuid4().hex[:10]}"
    subscription_id = f"sub_reactivate_{uuid4().hex[:10]}"

    activate_event = {
        "id": f"evt_smoke_{uuid4().hex[:14]}",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": customer_id,
                "subscription": subscription_id,
                "customer_email": email,
                "payment_status": "paid",
                "metadata": {
                    "user_id": str(user_id),
                    "email": email,
                    "plan_id": "starter-monthly",
                },
            }
        },
    }

    activate_webhook = _post_signed_webhook(deployed_client, activate_event)
    assert activate_webhook.status_code == 200
    assert activate_webhook.json().get("handled") is True

    active_quote = deployed_client.get("/v1/quote/AAPL", headers={"x-api-key": raw_key})
    assert active_quote.status_code in (200, 502)

    cancel_event = {
        "id": f"evt_smoke_{uuid4().hex[:14]}",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": subscription_id,
                "customer": customer_id,
                "status": "canceled",
                "current_period_end": int(time.time()),
            }
        },
    }

    cancel_webhook = _post_signed_webhook(deployed_client, cancel_event)
    assert cancel_webhook.status_code == 200
    assert cancel_webhook.json().get("handled") is True

    blocked_quote = deployed_client.get("/v1/quote/AAPL", headers={"x-api-key": raw_key})
    assert blocked_quote.status_code == 403
    assert blocked_quote.json().get("detail") == "Subscription inactive"

    reactivate_event = {
        "id": f"evt_smoke_{uuid4().hex[:14]}",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": subscription_id,
                "customer": customer_id,
                "status": "active",
                "current_period_end": int(time.time()) + 3600,
            }
        },
    }

    reactivate_webhook = _post_signed_webhook(deployed_client, reactivate_event)
    assert reactivate_webhook.status_code == 200
    reactivate_payload = reactivate_webhook.json()
    assert reactivate_payload.get("received") is True
    assert reactivate_payload.get("type") == "customer.subscription.updated"
    assert reactivate_payload.get("handled") is True

    restored_quote = deployed_client.get("/v1/quote/AAPL", headers={"x-api-key": raw_key})
    assert restored_quote.status_code in (200, 502)

    restored_payload = restored_quote.json()
    if restored_quote.status_code == 200:
        assert restored_payload.get("symbol") == "AAPL"
        assert restored_payload.get("last_price") is not None
    else:
        assert "Upstream provider error" in restored_payload.get("detail", "")


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
def test_deployed_customer_signup_login_then_created_key_enforces_api_auth(
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

    login_response = deployed_client.post(
        "/dashboard/api/session/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200

    login_payload = login_response.json()
    assert login_payload.get("ok") is True
    assert login_payload.get("source") == "customer-db-session"
    token = ((login_payload.get("session") or {}).get("token"))
    assert token

    auth_headers = {"Authorization": f"Bearer {token}"}

    create_key = deployed_client.post(
        "/dashboard/api/keys/create",
        headers=auth_headers,
        json={"label": "Deployed Smoke", "env": "test"},
    )
    assert create_key.status_code == 200
    create_key_payload = create_key.json()
    assert create_key_payload.get("source") == "customer-db-store"

    key_payload = create_key_payload.get("data") or {}
    raw_key = key_payload.get("rawKey")
    assert raw_key
    assert str(raw_key).startswith("yf_")

    before_overview = deployed_client.get(
        "/dashboard/api/overview?range=24h",
        headers=auth_headers,
    )
    assert before_overview.status_code == 200
    before_overview_payload = before_overview.json()
    assert before_overview_payload.get("source") == "customer-db-store"
    before_requests = int(before_overview_payload.get("requests") or 0)

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
    after_overview_payload = after_overview.json()
    assert after_overview_payload.get("source") == "customer-db-store"
    after_requests = int(after_overview_payload.get("requests") or 0)

    if quote_response.status_code in (200, 502):
        assert after_requests >= before_requests + 1
    else:
        assert after_requests == before_requests

    metrics_response = deployed_client.get(
        "/dashboard/api/metrics?range=24h",
        headers=auth_headers,
    )
    assert metrics_response.status_code == 200
    assert metrics_response.json().get("source") == "customer-db-store"

    activity_response = deployed_client.get(
        "/dashboard/api/activity?limit=10",
        headers=auth_headers,
    )
    assert activity_response.status_code == 200
    assert activity_response.json().get("source") == "customer-db-store"

    key_id = str((key_payload.get("key") or {}).get("id") or "")
    assert key_id

    revoke_response = deployed_client.post(
        f"/dashboard/api/keys/{key_id}/revoke",
        headers=auth_headers,
    )
    assert revoke_response.status_code == 200

    revoked_quote = deployed_client.get(
        "/v1/quote/AAPL",
        headers={"x-api-key": raw_key},
    )
    assert revoked_quote.status_code == 401
    assert revoked_quote.json().get("detail") == "Invalid API key"


@pytest.mark.deployed
@pytest.mark.critical
@pytest.mark.mutation
def test_deployed_customer_key_rotate_and_activate_transitions_auth_state(
    deployed_client: httpx.Client,
    customer_dashboard_checks_enabled: bool,
):
    email = f"deployed-key-lifecycle-{uuid4().hex[:10]}@example.com"
    password = "SmokePass123!"

    register_response = deployed_client.post(
        "/dashboard/api/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 200

    login_response = deployed_client.post(
        "/dashboard/api/session/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200

    token = ((login_response.json().get("session") or {}).get("token"))
    assert token
    auth_headers = {"Authorization": f"Bearer {token}"}

    create_key = deployed_client.post(
        "/dashboard/api/keys/create",
        headers=auth_headers,
        json={"label": "Deployed Lifecycle", "env": "test"},
    )
    assert create_key.status_code == 200
    create_payload = create_key.json()
    assert create_payload.get("source") == "customer-db-store"

    data = create_payload.get("data") or {}
    key_id = str((data.get("key") or {}).get("id") or "")
    raw_key_v1 = data.get("rawKey")
    assert key_id
    assert raw_key_v1

    first_quote = deployed_client.get("/v1/quote/AAPL", headers={"x-api-key": raw_key_v1})
    assert first_quote.status_code == 403
    assert first_quote.json().get("detail") == "Subscription inactive"

    rotate_response = deployed_client.post(
        f"/dashboard/api/keys/{key_id}/rotate",
        headers=auth_headers,
    )
    assert rotate_response.status_code == 200
    rotate_payload = rotate_response.json()
    assert rotate_payload.get("source") == "customer-db-store"

    raw_key_v2 = ((rotate_payload.get("data") or {}).get("rawKey"))
    assert raw_key_v2
    assert raw_key_v2 != raw_key_v1

    old_key_quote = deployed_client.get("/v1/quote/AAPL", headers={"x-api-key": raw_key_v1})
    assert old_key_quote.status_code == 401
    assert old_key_quote.json().get("detail") == "Invalid API key"

    rotated_key_quote = deployed_client.get("/v1/quote/AAPL", headers={"x-api-key": raw_key_v2})
    assert rotated_key_quote.status_code == 403
    assert rotated_key_quote.json().get("detail") == "Subscription inactive"

    revoke_response = deployed_client.post(
        f"/dashboard/api/keys/{key_id}/revoke",
        headers=auth_headers,
    )
    assert revoke_response.status_code == 200

    revoked_quote = deployed_client.get("/v1/quote/AAPL", headers={"x-api-key": raw_key_v2})
    assert revoked_quote.status_code == 401
    assert revoked_quote.json().get("detail") == "Invalid API key"

    activate_response = deployed_client.post(
        f"/dashboard/api/keys/{key_id}/activate",
        headers=auth_headers,
    )
    assert activate_response.status_code == 200

    activated_quote = deployed_client.get("/v1/quote/AAPL", headers={"x-api-key": raw_key_v2})
    assert activated_quote.status_code == 403
    assert activated_quote.json().get("detail") == "Subscription inactive"


