import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings

client = TestClient(app)
pytestmark = [pytest.mark.integration, pytest.mark.billing, pytest.mark.critical]


def test_plans_endpoint():
    r = client.get('/v1/billing/plans')
    assert r.status_code == 200
    body = r.json()
    assert 'plans' in body
    assert body['plans'][0]['price_usd'] == 4.99


def test_checkout_session_requires_config(monkeypatch):
    monkeypatch.setattr(settings, 'billing_allowed_redirect_hosts', '')
    monkeypatch.setattr(settings, 'stripe_secret_key', '')
    r = client.post('/v1/billing/checkout/session', json={
        'email': 'boss@example.com',
        'success_url': 'https://example.com/success',
        'cancel_url': 'https://example.com/cancel'
    })
    assert r.status_code == 503


def test_checkout_session_requires_price_id(monkeypatch):
    monkeypatch.setattr(settings, 'billing_allowed_redirect_hosts', '')
    monkeypatch.setattr(settings, 'stripe_secret_key', 'sk_test_mock')
    monkeypatch.setattr(settings, 'stripe_price_id_monthly', '')
    r = client.post('/v1/billing/checkout/session', json={
        'email': 'boss@example.com',
        'success_url': 'https://example.com/success',
        'cancel_url': 'https://example.com/cancel'
    })
    assert r.status_code == 503


def test_checkout_session_ok(monkeypatch):
    import app.routes.billing as billing

    monkeypatch.setattr(settings, 'billing_allowed_redirect_hosts', '')
    monkeypatch.setattr(settings, 'stripe_secret_key', 'sk_test_mock')
    monkeypatch.setattr(settings, 'stripe_price_id_monthly', 'price_mock')

    class DummySession:
        @staticmethod
        def create(**kwargs):
            assert kwargs['mode'] == 'subscription'
            assert kwargs['line_items'][0]['price'] == 'price_mock'
            return {'id': 'cs_test_123', 'url': 'https://checkout.stripe.test/session', 'status': 'open'}

    monkeypatch.setattr(billing.stripe.checkout, 'Session', DummySession)

    r = client.post('/v1/billing/checkout/session', json={
        'email': 'boss@example.com',
        'success_url': 'https://example.com/success',
        'cancel_url': 'https://example.com/cancel'
    })
    assert r.status_code == 200
    body = r.json()
    assert body['id'] == 'cs_test_123'


def test_checkout_session_allows_redirect_hosts_from_allowlist(monkeypatch):
    import app.routes.billing as billing

    monkeypatch.setattr(settings, 'billing_allowed_redirect_hosts', ' app.example.com , CHECKOUT.EXAMPLE.COM ')
    monkeypatch.setattr(settings, 'stripe_secret_key', 'sk_test_mock')
    monkeypatch.setattr(settings, 'stripe_price_id_monthly', 'price_mock')

    class DummySession:
        @staticmethod
        def create(**kwargs):
            return {'id': 'cs_test_123', 'url': 'https://checkout.stripe.test/session', 'status': 'open'}

    monkeypatch.setattr(billing.stripe.checkout, 'Session', DummySession)

    r = client.post('/v1/billing/checkout/session', json={
        'email': 'boss@example.com',
        'success_url': 'https://checkout.example.com/success',
        'cancel_url': 'https://app.example.com/cancel'
    })
    assert r.status_code == 200


def test_checkout_session_rejects_redirect_host_not_in_allowlist(monkeypatch):
    monkeypatch.setattr(settings, 'billing_allowed_redirect_hosts', 'app.example.com')

    r = client.post('/v1/billing/checkout/session', json={
        'email': 'boss@example.com',
        'success_url': 'https://evil.example/success',
        'cancel_url': 'https://app.example.com/cancel'
    })
    assert r.status_code == 422
    body = r.json()
    assert body['detail'] == 'Validation failed'
    assert 'not in BILLING_ALLOWED_REDIRECT_HOSTS' in str(body['errors'])


def test_checkout_session_empty_allowlist_keeps_previous_behavior(monkeypatch):
    import app.routes.billing as billing

    monkeypatch.setattr(settings, 'billing_allowed_redirect_hosts', '')
    monkeypatch.setattr(settings, 'stripe_secret_key', 'sk_test_mock')
    monkeypatch.setattr(settings, 'stripe_price_id_monthly', 'price_mock')

    class DummySession:
        @staticmethod
        def create(**kwargs):
            return {'id': 'cs_test_123', 'url': 'https://checkout.stripe.test/session', 'status': 'open'}

    monkeypatch.setattr(billing.stripe.checkout, 'Session', DummySession)

    r = client.post('/v1/billing/checkout/session', json={
        'email': 'boss@example.com',
        'success_url': 'https://not-listed.example/success',
        'cancel_url': 'https://another.example/cancel'
    })
    assert r.status_code == 200


def test_webhook_requires_secret_configured():
    r = client.post('/v1/billing/webhook/stripe', data='{}', headers={'Stripe-Signature': 'dummy'})
    assert r.status_code in (400, 503)


def test_webhook_requires_signature_when_secret_enabled(monkeypatch):
    monkeypatch.setattr(settings, 'stripe_webhook_secret', 'whsec_mock')
    r = client.post('/v1/billing/webhook/stripe', data='{}')
    assert r.status_code == 400


def test_webhook_supported_event_is_marked_handled(monkeypatch):
    import app.routes.billing as billing

    monkeypatch.setattr(settings, 'stripe_webhook_secret', 'whsec_mock')

    class DummyWebhook:
        @staticmethod
        def construct_event(payload, sig_header, secret):
            return {'type': 'invoice.payment_succeeded'}

    monkeypatch.setattr(billing.stripe, 'Webhook', DummyWebhook)

    r = client.post('/v1/billing/webhook/stripe', data='{}', headers={'Stripe-Signature': 'sig_mock'})
    assert r.status_code == 200
    assert r.json()['handled'] is True


def test_webhook_invalid_signature_returns_400(monkeypatch):
    import app.routes.billing as billing

    monkeypatch.setattr(settings, 'stripe_webhook_secret', 'whsec_mock')

    class DummyWebhook:
        @staticmethod
        def construct_event(payload, sig_header, secret):
            raise ValueError('bad signature')

    monkeypatch.setattr(billing.stripe, 'Webhook', DummyWebhook)

    r = client.post('/v1/billing/webhook/stripe', data='{}', headers={'Stripe-Signature': 'sig_mock'})
    assert r.status_code == 400
    assert 'Invalid webhook' in r.json()['detail']


def test_webhook_unknown_event_is_unhandled(monkeypatch):
    import app.routes.billing as billing

    monkeypatch.setattr(settings, 'stripe_webhook_secret', 'whsec_mock')

    class DummyWebhook:
        @staticmethod
        def construct_event(payload, sig_header, secret):
            return {'type': 'charge.refunded'}

    monkeypatch.setattr(billing.stripe, 'Webhook', DummyWebhook)

    r = client.post('/v1/billing/webhook/stripe', data='{}', headers={'Stripe-Signature': 'sig_mock'})
    assert r.status_code == 200
    assert r.json()['handled'] is False


def test_checkout_rejects_insecure_redirect_urls(monkeypatch):
    monkeypatch.setattr(settings, 'billing_allowed_redirect_hosts', '')
    monkeypatch.setattr(settings, 'stripe_secret_key', 'sk_test_mock')
    monkeypatch.setattr(settings, 'stripe_price_id_monthly', 'price_mock')

    r = client.post('/v1/billing/checkout/session', json={
        'email': 'boss@example.com',
        'success_url': 'http://evil.example/success',
        'cancel_url': 'https://example.com/cancel'
    })
    assert r.status_code == 422
