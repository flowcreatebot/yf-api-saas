import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
pytestmark = [pytest.mark.integration, pytest.mark.critical]


PROTECTED_ENDPOINTS = [
    '/v1/quote/AAPL',
    '/v1/quotes?symbols=AAPL,MSFT',
    '/v1/history/AAPL?period=1mo&interval=1d',
    '/v1/fundamentals/AAPL',
]


def test_health_ok():
    r = client.get('/v1/health')
    assert r.status_code == 200
    assert r.json().get('ok') is True


@pytest.mark.parametrize('endpoint', PROTECTED_ENDPOINTS)
def test_protected_endpoints_require_api_key(endpoint):
    r = client.get(endpoint)
    assert r.status_code == 401
    assert r.json()['detail'] == 'Missing API key'


@pytest.mark.parametrize('endpoint', PROTECTED_ENDPOINTS)
def test_protected_endpoints_reject_wrong_api_key(endpoint):
    r = client.get(endpoint, headers={'x-api-key': 'wrong'})
    assert r.status_code == 401
    assert r.json()['detail'] == 'Invalid API key'


def test_quote_accepts_database_backed_api_key(monkeypatch):
    from app.db import SessionLocal
    from app.models import APIKey, Subscription, User
    from app.security import hash_api_key
    import app.routes.market as market

    class DummyTicker:
        def __init__(self, symbol: str):
            self.symbol = symbol

        @property
        def fast_info(self):
            return {'lastPrice': 123.45}

    monkeypatch.setattr(market.yf, 'Ticker', DummyTicker)

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == 'test-auth@yfapi.local').first()
        if user is None:
            user = User(email='test-auth@yfapi.local', hashed_password='!')
            db.add(user)
            db.flush()

        key_hash = hash_api_key('beta')
        existing = db.query(APIKey).filter(APIKey.key_hash == key_hash).first()
        if existing is None:
            db.add(APIKey(key_hash=key_hash, user_id=user.id, name='test-beta', status='active'))

        has_subscription = db.query(Subscription).filter(Subscription.user_id == user.id).first()
        if has_subscription is None:
            db.add(
                Subscription(
                    user_id=user.id,
                    stripe_subscription_id=f'sub_test_{user.id}',
                    status='active',
                    plan='starter-monthly',
                )
            )

        db.commit()

    r = client.get('/v1/quote/AAPL', headers={'x-api-key': 'beta'})
    assert r.status_code == 200


def test_quote_rejects_customer_key_without_active_subscription(monkeypatch):
    from app.db import SessionLocal
    from app.models import APIKey, Subscription, User
    from app.security import hash_api_key
    import app.routes.market as market

    class DummyTicker:
        def __init__(self, symbol: str):
            self.symbol = symbol

        @property
        def fast_info(self):
            return {'lastPrice': 123.45}

    monkeypatch.setattr(market.yf, 'Ticker', DummyTicker)

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == 'test-no-sub@yfapi.local').first()
        if user is None:
            user = User(email='test-no-sub@yfapi.local', hashed_password='!')
            db.add(user)
            db.flush()

        key_hash = hash_api_key('gamma')
        existing = db.query(APIKey).filter(APIKey.key_hash == key_hash).first()
        if existing is None:
            db.add(APIKey(key_hash=key_hash, user_id=user.id, name='test-gamma', status='active'))

        db.query(Subscription).filter(Subscription.user_id == user.id).delete()
        db.commit()

    r = client.get('/v1/quote/AAPL', headers={'x-api-key': 'gamma'})
    assert r.status_code == 403
    assert r.json()['detail'] == 'Subscription inactive'
