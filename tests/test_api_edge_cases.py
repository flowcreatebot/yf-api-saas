import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings

client = TestClient(app)
pytestmark = [pytest.mark.integration, pytest.mark.critical]


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
    body = r.json()
    assert body['detail'] == 'Validation failed'
    assert isinstance(body['errors'], list)


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
    assert r.json()['detail'] == 'Maximum 25 symbols per request'


def test_quotes_reject_invalid_symbol_in_batch():
    r = client.get('/v1/quotes?symbols=AAPL,MSFT$,TSLA', headers=_auth_headers())
    assert r.status_code == 400
    assert r.json()['detail'] == 'Invalid symbol format'


def test_history_rejects_start_after_end():
    r = client.get('/v1/history/AAPL?period=1mo&interval=1d&start=2026-01-10&end=2026-01-01', headers=_auth_headers())
    assert r.status_code == 400
    assert r.json()['detail'] == 'start must be <= end'


@pytest.mark.parametrize(
    ('endpoint', 'expected_status'),
    [
        ('/v1/history/AAPL?period=13mo&interval=1d', 400),
        ('/v1/history/AAPL?period=1mo&interval=2h', 400),
        ('/v1/history/AAPL?period=1mo&interval=1d&start=not-a-date', 422),
        ('/v1/history/AAPL?period=1mo&interval=1d&end=2026-13-40', 422),
        ('/v1/quotes?symbols=,,,', 400),
    ],
)
def test_market_data_malformed_query_params_return_4xx(endpoint, expected_status):
    r = client.get(endpoint, headers=_auth_headers())
    assert r.status_code == expected_status


@pytest.mark.parametrize('endpoint', ['/v1/history/AAPL$BAD', '/v1/fundamentals/AAPL$BAD'])
def test_market_data_rejects_malformed_symbol_shape(endpoint):
    r = client.get(endpoint, headers=_auth_headers())
    assert r.status_code == 400


@pytest.mark.parametrize(
    'endpoint',
    [
        '/v1/history/AAPL?period=13mo&interval=1d',
        '/v1/history/AAPL?period=1mo&interval=2h',
        '/v1/history/AAPL?period=1mo&interval=1d&start=2026-01-10&end=2026-01-01',
        '/v1/quote/AAPL$BAD',
        '/v1/fundamentals/AAPL$BAD',
        '/v1/quotes?symbols=,,,',
    ],
)
def test_malformed_market_queries_still_require_auth_when_key_missing(endpoint):
    r = client.get(endpoint)
    assert r.status_code == 401
    assert r.json()['detail'] == 'Missing API key'


@pytest.mark.parametrize(
    'endpoint',
    [
        '/v1/history/AAPL?period=13mo&interval=1d',
        '/v1/history/AAPL?period=1mo&interval=2h',
        '/v1/history/AAPL?period=1mo&interval=1d&start=2026-01-10&end=2026-01-01',
        '/v1/quote/AAPL$BAD',
        '/v1/fundamentals/AAPL$BAD',
        '/v1/quotes?symbols=,,,',
    ],
)
def test_malformed_market_queries_still_require_auth_when_key_invalid(endpoint):
    r = client.get(endpoint, headers={'x-api-key': 'not-valid'})
    assert r.status_code == 401
    assert r.json()['detail'] == 'Invalid API key'
