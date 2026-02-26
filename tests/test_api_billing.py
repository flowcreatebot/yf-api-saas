from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings

client = TestClient(app)
pytestmark = [pytest.mark.integration, pytest.mark.billing, pytest.mark.critical]


def _new_email() -> str:
    return f"billing-{uuid4().hex[:10]}@example.com"


def _register_customer(password: str = "Passw0rd!") -> tuple[str, str]:
    email = _new_email()
    response = client.post(
        "/dashboard/api/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["session"]["token"]
    return email, token


def test_plans_endpoint(monkeypatch):
    monkeypatch.setattr(settings, "billing_starter_plan_id", "starter-config")
    monkeypatch.setattr(settings, "billing_starter_plan_name", "Starter Config")
    monkeypatch.setattr(settings, "billing_starter_plan_price_usd", 9.99)
    monkeypatch.setattr(settings, "billing_starter_plan_interval", "month")
    monkeypatch.setattr(settings, "billing_starter_plan_description", "Configured plan")

    r = client.get('/v1/billing/plans')
    assert r.status_code == 200
    body = r.json()
    assert body['plans'][0]['id'] == 'starter-config'
    assert body['plans'][0]['price_usd'] == 9.99


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


def test_checkout_session_attaches_authenticated_customer(monkeypatch):
    import app.routes.billing as billing
    from app.db import SessionLocal
    from app.models import User

    email, token = _register_customer()

    monkeypatch.setattr(settings, 'billing_allowed_redirect_hosts', '')
    monkeypatch.setattr(settings, 'stripe_secret_key', 'sk_test_mock')
    monkeypatch.setattr(settings, 'stripe_price_id_monthly', 'price_mock')

    calls: dict[str, dict] = {}

    class DummyCustomer:
        @staticmethod
        def create(**kwargs):
            calls['customer'] = kwargs
            return {'id': 'cus_test_new'}

    class DummySession:
        @staticmethod
        def create(**kwargs):
            calls['checkout'] = kwargs
            return {'id': 'cs_test_123', 'url': 'https://checkout.stripe.test/session', 'status': 'open'}

    monkeypatch.setattr(billing.stripe, 'Customer', DummyCustomer)
    monkeypatch.setattr(billing.stripe.checkout, 'Session', DummySession)

    response = client.post(
        '/v1/billing/checkout/session',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'email': email,
            'success_url': 'https://example.com/success',
            'cancel_url': 'https://example.com/cancel',
        },
    )
    assert response.status_code == 200

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        assert user.stripe_customer_id == 'cus_test_new'
        assert calls['checkout']['customer'] == 'cus_test_new'
        assert calls['checkout']['metadata']['user_id'] == str(user.id)


def test_checkout_session_rejects_mismatched_authenticated_email(monkeypatch):
    import app.routes.billing as billing

    _email, token = _register_customer()

    monkeypatch.setattr(settings, 'billing_allowed_redirect_hosts', '')
    monkeypatch.setattr(settings, 'stripe_secret_key', 'sk_test_mock')
    monkeypatch.setattr(settings, 'stripe_price_id_monthly', 'price_mock')

    class DummySession:
        @staticmethod
        def create(**kwargs):
            return {'id': 'cs_test_123', 'url': 'https://checkout.stripe.test/session', 'status': 'open'}

    monkeypatch.setattr(billing.stripe.checkout, 'Session', DummySession)

    response = client.post(
        '/v1/billing/checkout/session',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'email': _new_email(),
            'success_url': 'https://example.com/success',
            'cancel_url': 'https://example.com/cancel',
        },
    )
    assert response.status_code == 403


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
            return {
                'type': 'customer.subscription.updated',
                'data': {'object': {'id': 'sub_missing', 'status': 'active'}},
            }

    monkeypatch.setattr(billing.stripe, 'Webhook', DummyWebhook)

    r = client.post('/v1/billing/webhook/stripe', data='{}', headers={'Stripe-Signature': 'sig_mock'})
    assert r.status_code == 200
    assert r.json()['handled'] is False


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
            return {'type': 'charge.refunded', 'data': {'object': {}}}

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


def test_webhook_checkout_completed_creates_subscription_and_first_api_key(monkeypatch):
    import app.routes.billing as billing
    from app.db import SessionLocal
    from app.models import APIKey, Subscription, User

    email, _token = _register_customer()

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        user_id = user.id

    monkeypatch.setattr(settings, 'stripe_webhook_secret', 'whsec_mock')

    customer_id = f"cus_test_{uuid4().hex[:8]}"
    subscription_id = f"sub_test_{uuid4().hex[:8]}"

    class DummyWebhook:
        @staticmethod
        def construct_event(payload, sig_header, secret):
            return {
                'type': 'checkout.session.completed',
                'data': {
                    'object': {
                        'customer': customer_id,
                        'subscription': subscription_id,
                        'customer_email': email,
                        'payment_status': 'paid',
                        'metadata': {'user_id': str(user_id)},
                    }
                },
            }

    monkeypatch.setattr(billing.stripe, 'Webhook', DummyWebhook)

    response = client.post('/v1/billing/webhook/stripe', data='{}', headers={'Stripe-Signature': 'sig_mock'})
    assert response.status_code == 200
    assert response.json()['handled'] is True
    assert response.json()['provisioned_key'] is True

    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()
        assert user is not None
        assert user.stripe_customer_id == customer_id

        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        assert subscription is not None
        assert subscription.stripe_subscription_id == subscription_id
        assert subscription.status == 'active'

        key = db.query(APIKey).filter(APIKey.user_id == user_id, APIKey.status == 'active').first()
        assert key is not None


def test_webhook_checkout_completed_is_idempotent_for_subscription_and_key(monkeypatch):
    import app.routes.billing as billing
    from app.db import SessionLocal
    from app.models import APIKey, Subscription, User

    email, _token = _register_customer()

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        user_id = user.id

    monkeypatch.setattr(settings, 'stripe_webhook_secret', 'whsec_mock')

    customer_id = f"cus_idempotent_{uuid4().hex[:8]}"
    subscription_id = f"sub_idempotent_{uuid4().hex[:8]}"

    class DummyWebhook:
        @staticmethod
        def construct_event(payload, sig_header, secret):
            return {
                'type': 'checkout.session.completed',
                'data': {
                    'object': {
                        'customer': customer_id,
                        'subscription': subscription_id,
                        'customer_email': email,
                        'payment_status': 'paid',
                        'metadata': {'user_id': str(user_id)},
                    }
                },
            }

    monkeypatch.setattr(billing.stripe, 'Webhook', DummyWebhook)

    first = client.post('/v1/billing/webhook/stripe', data='{}', headers={'Stripe-Signature': 'sig_mock'})
    assert first.status_code == 200
    assert first.json()['handled'] is True
    assert first.json()['provisioned_key'] is True

    second = client.post('/v1/billing/webhook/stripe', data='{}', headers={'Stripe-Signature': 'sig_mock'})
    assert second.status_code == 200
    assert second.json()['handled'] is True
    assert second.json()['provisioned_key'] is False

    with SessionLocal() as db:
        subscription_count = (
            db.query(Subscription)
            .filter(Subscription.user_id == user_id, Subscription.stripe_subscription_id == subscription_id)
            .count()
        )
        assert subscription_count == 1

        active_key_count = (
            db.query(APIKey)
            .filter(APIKey.user_id == user_id, APIKey.status == 'active')
            .count()
        )
        assert active_key_count == 1


def test_webhook_subscription_updated_updates_existing_subscription(monkeypatch):
    import app.routes.billing as billing
    from app.db import SessionLocal
    from app.models import Subscription, User

    email, _token = _register_customer()

    subscription_id = f"sub_update_{uuid4().hex[:8]}"
    customer_id = f"cus_update_{uuid4().hex[:8]}"

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        user.stripe_customer_id = customer_id
        existing = Subscription(
            user_id=user.id,
            stripe_subscription_id=subscription_id,
            status='active',
            plan='starter-monthly',
        )
        db.add(existing)
        db.commit()

    monkeypatch.setattr(settings, 'stripe_webhook_secret', 'whsec_mock')

    class DummyWebhook:
        @staticmethod
        def construct_event(payload, sig_header, secret):
            return {
                'type': 'customer.subscription.updated',
                'data': {
                    'object': {
                        'id': subscription_id,
                        'customer': customer_id,
                        'status': 'past_due',
                        'current_period_end': 1760000000,
                    }
                },
            }

    monkeypatch.setattr(billing.stripe, 'Webhook', DummyWebhook)

    response = client.post('/v1/billing/webhook/stripe', data='{}', headers={'Stripe-Signature': 'sig_mock'})
    assert response.status_code == 200
    assert response.json()['handled'] is True

    with SessionLocal() as db:
        updated = db.query(Subscription).filter(Subscription.stripe_subscription_id == subscription_id).first()
        assert updated is not None
        assert updated.status == 'past_due'
        assert updated.current_period_end is not None


def test_webhook_subscription_updated_active_provisions_first_key_idempotently(monkeypatch):
    import app.routes.billing as billing
    from app.db import SessionLocal
    from app.models import APIKey, Subscription, User

    email, _token = _register_customer()

    subscription_id = f"sub_activate_{uuid4().hex[:8]}"
    customer_id = f"cus_activate_{uuid4().hex[:8]}"

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        user.stripe_customer_id = customer_id
        user_id = user.id
        db.commit()

    monkeypatch.setattr(settings, 'stripe_webhook_secret', 'whsec_mock')

    class DummyWebhook:
        @staticmethod
        def construct_event(payload, sig_header, secret):
            return {
                'type': 'customer.subscription.updated',
                'data': {
                    'object': {
                        'id': subscription_id,
                        'customer': customer_id,
                        'status': 'active',
                        'current_period_end': 1766000000,
                    }
                },
            }

    monkeypatch.setattr(billing.stripe, 'Webhook', DummyWebhook)

    first = client.post('/v1/billing/webhook/stripe', data='{}', headers={'Stripe-Signature': 'sig_mock'})
    assert first.status_code == 200
    assert first.json()['handled'] is True
    assert first.json()['provisioned_key'] is True

    second = client.post('/v1/billing/webhook/stripe', data='{}', headers={'Stripe-Signature': 'sig_mock'})
    assert second.status_code == 200
    assert second.json()['handled'] is True
    assert second.json()['provisioned_key'] is False

    with SessionLocal() as db:
        subscription_count = (
            db.query(Subscription)
            .filter(Subscription.user_id == user_id, Subscription.stripe_subscription_id == subscription_id)
            .count()
        )
        assert subscription_count == 1

        active_key_count = (
            db.query(APIKey)
            .filter(APIKey.user_id == user_id, APIKey.status == 'active')
            .count()
        )
        assert active_key_count == 1


def test_webhook_subscription_deleted_marks_subscription_canceled(monkeypatch):
    import app.routes.billing as billing
    from app.db import SessionLocal
    from app.models import Subscription, User

    email, _token = _register_customer()

    subscription_id = f"sub_deleted_{uuid4().hex[:8]}"
    customer_id = f"cus_deleted_{uuid4().hex[:8]}"

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        user.stripe_customer_id = customer_id
        existing = Subscription(
            user_id=user.id,
            stripe_subscription_id=subscription_id,
            status='active',
            plan='starter-monthly',
        )
        db.add(existing)
        db.commit()

    monkeypatch.setattr(settings, 'stripe_webhook_secret', 'whsec_mock')

    class DummyWebhook:
        @staticmethod
        def construct_event(payload, sig_header, secret):
            return {
                'type': 'customer.subscription.deleted',
                'data': {
                    'object': {
                        'id': subscription_id,
                        'customer': customer_id,
                        'status': 'canceled',
                        'current_period_end': 1765000000,
                    }
                },
            }

    monkeypatch.setattr(billing.stripe, 'Webhook', DummyWebhook)

    response = client.post('/v1/billing/webhook/stripe', data='{}', headers={'Stripe-Signature': 'sig_mock'})
    assert response.status_code == 200
    assert response.json()['handled'] is True

    with SessionLocal() as db:
        updated = db.query(Subscription).filter(Subscription.stripe_subscription_id == subscription_id).first()
        assert updated is not None
        assert updated.status == 'canceled'


def test_webhook_checkout_completed_unpaid_does_not_provision_key(monkeypatch):
    import app.routes.billing as billing
    from app.db import SessionLocal
    from app.models import APIKey, Subscription, User

    email, _token = _register_customer()

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        user_id = user.id

    monkeypatch.setattr(settings, 'stripe_webhook_secret', 'whsec_mock')

    class DummyWebhook:
        @staticmethod
        def construct_event(payload, sig_header, secret):
            return {
                'type': 'checkout.session.completed',
                'data': {
                    'object': {
                        'customer': f"cus_unpaid_{uuid4().hex[:8]}",
                        'subscription': f"sub_unpaid_{uuid4().hex[:8]}",
                        'customer_email': email,
                        'payment_status': 'unpaid',
                        'metadata': {'user_id': str(user_id)},
                    }
                },
            }

    monkeypatch.setattr(billing.stripe, 'Webhook', DummyWebhook)

    response = client.post('/v1/billing/webhook/stripe', data='{}', headers={'Stripe-Signature': 'sig_mock'})
    assert response.status_code == 200
    assert response.json()['handled'] is True
    assert response.json()['provisioned_key'] is False

    with SessionLocal() as db:
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).order_by(Subscription.id.desc()).first()
        assert subscription is not None
        assert subscription.status == 'incomplete'

        key = db.query(APIKey).filter(APIKey.user_id == user_id).first()
        assert key is None


@pytest.mark.e2e
def test_full_billing_flow_paid_provisions_key_and_cancellation_revokes_api_access(monkeypatch):
    import app.routes.billing as billing
    import app.routes.market as market

    from app.db import SessionLocal
    from app.models import APIKey, Subscription, User

    customer_id = f"cus_flow_{uuid4().hex[:10]}"
    subscription_id = f"sub_flow_{uuid4().hex[:10]}"

    class DummyCustomer:
        @staticmethod
        def create(**kwargs):
            return {'id': customer_id}

    class DummyCheckoutSession:
        @staticmethod
        def create(**kwargs):
            return {'id': 'cs_flow_123', 'url': 'https://checkout.stripe.test/session', 'status': 'open'}

    class DummyTicker:
        def __init__(self, symbol: str):
            self.symbol = symbol

        @property
        def fast_info(self):
            return {'lastPrice': 321.09}

    monkeypatch.setattr(settings, 'billing_allowed_redirect_hosts', '')
    monkeypatch.setattr(settings, 'stripe_secret_key', 'sk_test_mock')
    monkeypatch.setattr(settings, 'stripe_price_id_monthly', 'price_mock')
    monkeypatch.setattr(settings, 'stripe_webhook_secret', 'whsec_mock')

    monkeypatch.setattr(billing.stripe, 'Customer', DummyCustomer)
    monkeypatch.setattr(billing.stripe.checkout, 'Session', DummyCheckoutSession)
    monkeypatch.setattr(market.yf, 'Ticker', DummyTicker)

    provisioned_key_suffix = f"flowtoken_{uuid4().hex}"

    email, session_token = _register_customer()

    checkout_response = client.post(
        '/v1/billing/checkout/session',
        headers={'Authorization': f'Bearer {session_token}'},
        json={
            'email': email,
            'success_url': 'https://example.com/success',
            'cancel_url': 'https://example.com/cancel',
        },
    )
    assert checkout_response.status_code == 200

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        user_id = user.id

    monkeypatch.setattr(billing.secrets, 'token_urlsafe', lambda size: provisioned_key_suffix)

    class CheckoutCompletedWebhook:
        @staticmethod
        def construct_event(payload, sig_header, secret):
            return {
                'type': 'checkout.session.completed',
                'data': {
                    'object': {
                        'customer': customer_id,
                        'subscription': subscription_id,
                        'customer_email': email,
                        'payment_status': 'paid',
                        'metadata': {'user_id': str(user_id)},
                    }
                },
            }

    monkeypatch.setattr(billing.stripe, 'Webhook', CheckoutCompletedWebhook)

    webhook_paid_response = client.post('/v1/billing/webhook/stripe', data='{}', headers={'Stripe-Signature': 'sig_mock'})
    assert webhook_paid_response.status_code == 200
    assert webhook_paid_response.json()['handled'] is True
    assert webhook_paid_response.json()['provisioned_key'] is True

    dashboard_keys = client.get(
        '/dashboard/api/keys',
        headers={'Authorization': f'Bearer {session_token}'},
    )
    assert dashboard_keys.status_code == 200
    keys_payload = dashboard_keys.json()
    assert keys_payload['source'] == 'customer-db-store'
    assert len(keys_payload['keys']) == 1
    assert keys_payload['keys'][0]['active'] is True
    assert keys_payload['keys'][0]['env'] == 'live'

    raw_key = f"yf_live_{provisioned_key_suffix}"

    market_response = client.get('/v1/quote/AAPL', headers={'x-api-key': raw_key})
    assert market_response.status_code == 200

    dashboard_overview = client.get(
        '/dashboard/api/overview?range=24h',
        headers={'Authorization': f'Bearer {session_token}'},
    )
    assert dashboard_overview.status_code == 200
    overview_payload = dashboard_overview.json()
    assert overview_payload['requests'] >= 1
    assert any(entry['path'] == '/v1/quote/{symbol}' for entry in overview_payload['topEndpoints'])

    dashboard_metrics = client.get(
        '/dashboard/api/metrics?range=24h',
        headers={'Authorization': f'Bearer {session_token}'},
    )
    assert dashboard_metrics.status_code == 200
    metrics_payload = dashboard_metrics.json()
    assert metrics_payload['source'] == 'customer-db-store'
    assert metrics_payload['summary']['requests'] >= 1
    assert any(entry['path'] == '/v1/quote/{symbol}' for entry in metrics_payload['topEndpoints'])

    dashboard_activity = client.get(
        '/dashboard/api/activity?limit=20',
        headers={'Authorization': f'Bearer {session_token}'},
    )
    assert dashboard_activity.status_code == 200
    activity_payload = dashboard_activity.json()
    assert activity_payload['source'] == 'customer-db-store'
    assert any(
        event['action'] == 'usage.request' and event['target'] == '/v1/quote/{symbol}'
        for event in activity_payload['events']
    )

    class SubscriptionDeletedWebhook:
        @staticmethod
        def construct_event(payload, sig_header, secret):
            return {
                'type': 'customer.subscription.deleted',
                'data': {
                    'object': {
                        'id': subscription_id,
                        'customer': customer_id,
                        'status': 'canceled',
                        'current_period_end': 1765000000,
                    }
                },
            }

    monkeypatch.setattr(billing.stripe, 'Webhook', SubscriptionDeletedWebhook)

    webhook_deleted_response = client.post('/v1/billing/webhook/stripe', data='{}', headers={'Stripe-Signature': 'sig_mock'})
    assert webhook_deleted_response.status_code == 200
    assert webhook_deleted_response.json()['handled'] is True

    blocked_market_response = client.get('/v1/quote/AAPL', headers={'x-api-key': raw_key})
    assert blocked_market_response.status_code == 403
    assert blocked_market_response.json()['detail'] == 'Subscription inactive'

    with SessionLocal() as db:
        canceled_subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        assert canceled_subscription is not None
        assert canceled_subscription.status == 'canceled'

    class SubscriptionReactivatedWebhook:
        @staticmethod
        def construct_event(payload, sig_header, secret):
            return {
                'type': 'customer.subscription.updated',
                'data': {
                    'object': {
                        'id': subscription_id,
                        'customer': customer_id,
                        'status': 'active',
                        'current_period_end': 1769000000,
                    }
                },
            }

    monkeypatch.setattr(billing.stripe, 'Webhook', SubscriptionReactivatedWebhook)

    webhook_reactivated_response = client.post('/v1/billing/webhook/stripe', data='{}', headers={'Stripe-Signature': 'sig_mock'})
    assert webhook_reactivated_response.status_code == 200
    assert webhook_reactivated_response.json()['handled'] is True

    restored_market_response = client.get('/v1/quote/AAPL', headers={'x-api-key': raw_key})
    assert restored_market_response.status_code == 200
    assert restored_market_response.json()['symbol'] == 'AAPL'

    with SessionLocal() as db:
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        assert subscription is not None
        assert subscription.status == 'active'

        api_key = db.query(APIKey).filter(APIKey.user_id == user_id).first()
        assert api_key is not None
