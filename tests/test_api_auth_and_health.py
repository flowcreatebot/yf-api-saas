import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


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


def test_quote_accepts_additional_valid_key(monkeypatch):
    from app.config import settings
    import app.routes.market as market

    class DummyTicker:
        def __init__(self, symbol: str):
            self.symbol = symbol

        @property
        def fast_info(self):
            return {'lastPrice': 123.45}

    monkeypatch.setattr(settings, 'api_valid_keys', 'alpha,beta,gamma')
    monkeypatch.setattr(market.yf, 'Ticker', DummyTicker)

    r = client.get('/v1/quote/AAPL', headers={'x-api-key': 'beta'})
    assert r.status_code == 200

    # reset for test isolation
    monkeypatch.setattr(settings, 'api_valid_keys', '')
