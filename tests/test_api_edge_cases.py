import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings

client = TestClient(app)


def _auth_headers():
    return {"x-api-key": settings.api_master_key}


class EmptyHistoryTicker:
    def __init__(self, symbol: str):
        self.symbol = symbol

    @property
    def fast_info(self):
        return {"lastPrice": 1}

    def history(self, **kwargs):
        return pd.DataFrame()

    @property
    def info(self):
        return {}


class CrashTicker:
    def __init__(self, symbol: str):
        raise RuntimeError("upstream failure")


def test_quotes_requires_symbols_param():
    r = client.get('/v1/quotes', headers=_auth_headers())
    assert r.status_code == 422


def test_history_empty_returns_404(monkeypatch):
    import app.routes.market as market

    monkeypatch.setattr(market.yf, 'Ticker', EmptyHistoryTicker)
    r = client.get('/v1/history/AAPL', headers=_auth_headers())
    assert r.status_code == 404


def test_fundamentals_empty_returns_404(monkeypatch):
    import app.routes.market as market

    monkeypatch.setattr(market.yf, 'Ticker', EmptyHistoryTicker)
    r = client.get('/v1/fundamentals/AAPL', headers=_auth_headers())
    assert r.status_code == 404


def test_upstream_crash_is_bad_gateway(monkeypatch):
    import app.routes.market as market

    monkeypatch.setattr(market.yf, 'Ticker', CrashTicker)
    r = client.get('/v1/quote/AAPL', headers=_auth_headers())
    assert r.status_code == 502


def test_invalid_symbol_rejected_early():
    r = client.get('/v1/quote/AAPL$BAD', headers=_auth_headers())
    assert r.status_code == 400


def test_quotes_reject_more_than_25_symbols():
    symbols = ','.join([f'S{i}' for i in range(26)])
    r = client.get(f'/v1/quotes?symbols={symbols}', headers=_auth_headers())
    assert r.status_code == 400
