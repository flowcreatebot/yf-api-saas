from fastapi.testclient import TestClient

from app.main import app
from app.config import settings

client = TestClient(app)


def test_plans_endpoint():
    r = client.get('/v1/billing/plans')
    assert r.status_code == 200
    body = r.json()
    assert 'plans' in body
    assert body['plans'][0]['price_usd'] == 4.99


def test_checkout_session_requires_config(monkeypatch):
    monkeypatch.setattr(settings, 'stripe_secret_key', '')
    r = client.post('/v1/billing/checkout/session', json={
        'email': 'boss@example.com',
        'success_url': 'https://example.com/success',
        'cancel_url': 'https://example.com/cancel'
    })
    assert r.status_code == 503


def test_checkout_session_ok(monkeypatch):
    import app.routes.billing as billing

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


def test_webhook_requires_secret_configured():
    r = client.post('/v1/billing/webhook/stripe', data='{}', headers={'Stripe-Signature': 'dummy'})
    assert r.status_code in (400, 503)


def test_checkout_rejects_insecure_redirect_urls(monkeypatch):
    monkeypatch.setattr(settings, 'stripe_secret_key', 'sk_test_mock')
    monkeypatch.setattr(settings, 'stripe_price_id_monthly', 'price_mock')

    r = client.post('/v1/billing/checkout/session', json={
        'email': 'boss@example.com',
        'success_url': 'http://evil.example/success',
        'cancel_url': 'https://example.com/cancel'
    })
    assert r.status_code == 422
