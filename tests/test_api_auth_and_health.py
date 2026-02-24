from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get('/v1/health')
    assert r.status_code == 200
    assert r.json().get('ok') is True


def test_quote_requires_api_key():
    r = client.get('/v1/quote/AAPL')
    assert r.status_code == 401


def test_quote_rejects_wrong_api_key(monkeypatch):
    r = client.get('/v1/quote/AAPL', headers={'x-api-key': 'wrong'})
    assert r.status_code == 401


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
