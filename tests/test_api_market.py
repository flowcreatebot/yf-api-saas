from datetime import datetime

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings


client = TestClient(app)
pytestmark = [pytest.mark.integration, pytest.mark.critical]


class DummyTicker:
    def __init__(self, symbol: str):
        self.symbol = symbol

    @property
    def fast_info(self):
        if self.symbol == 'BAD':
            return {}
        return {
            'currency': 'USD',
            'exchange': 'NMS',
            'lastPrice': 123.45,
            'open': 120.0,
            'dayHigh': 124.0,
            'dayLow': 119.5,
            'previousClose': 121.0,
            'lastVolume': 1000000,
            'marketCap': 1000000000,
        }

    def history(self, **kwargs):
        idx = pd.to_datetime([datetime(2026, 1, 1), datetime(2026, 1, 2)])
        return pd.DataFrame(
            {
                'Open': [100.0, 101.0],
                'High': [102.0, 103.0],
                'Low': [99.0, 100.0],
                'Close': [101.0, 102.0],
                'Volume': [1000, 2000],
            },
            index=idx,
        )

    @property
    def info(self):
        return {
            'longName': 'Example Corp',
            'sector': 'Technology',
            'industry': 'Software',
            'website': 'https://example.com',
            'trailingPE': 20.5,
            'forwardPE': 18.1,
            'priceToBook': 4.2,
            'dividendYield': 0.01,
            'beta': 1.1,
            'fiftyTwoWeekHigh': 150,
            'fiftyTwoWeekLow': 90,
        }


class FlakyTicker:
    fail_mode = False

    def __init__(self, symbol: str):
        self.symbol = symbol

    @property
    def fast_info(self):
        if FlakyTicker.fail_mode:
            raise RuntimeError('upstream down')
        return {
            'currency': 'USD',
            'exchange': 'NMS',
            'lastPrice': 200.0,
            'open': 199.0,
            'dayHigh': 201.0,
            'dayLow': 198.0,
            'previousClose': 198.5,
            'lastVolume': 500,
            'marketCap': 50,
        }

    @property
    def info(self):
        if FlakyTicker.fail_mode:
            raise RuntimeError('upstream down')
        return {
            'longName': 'Flaky Inc',
            'sector': 'Tech',
            'industry': 'Infra',
            'website': 'https://example.org',
            'trailingPE': 10,
            'forwardPE': 9,
            'priceToBook': 2,
            'dividendYield': 0,
            'beta': 1,
            'fiftyTwoWeekHigh': 20,
            'fiftyTwoWeekLow': 10,
        }


class NonFiniteTicker:
    def __init__(self, symbol: str):
        self.symbol = symbol

    @property
    def fast_info(self):
        return {
            'currency': 'USD',
            'exchange': 'NMS',
            'lastPrice': float('nan'),
            'open': float('inf'),
            'dayHigh': 201.0,
            'dayLow': float('-inf'),
            'previousClose': 198.5,
            'lastVolume': float('nan'),
            'marketCap': float('inf'),
        }

    @property
    def info(self):
        return {
            'longName': 'Sanitized Inc',
            'sector': 'Tech',
            'industry': 'Infra',
            'website': 'https://example.org',
            'trailingPE': float('nan'),
            'forwardPE': float('inf'),
            'priceToBook': 2,
            'dividendYield': float('-inf'),
            'beta': 1,
            'fiftyTwoWeekHigh': float('nan'),
            'fiftyTwoWeekLow': 10,
        }


class GetExplodes:
    def get(self, _key):
        raise RuntimeError('rate limited on field read')


class InfoGetExplodesTicker:
    def __init__(self, symbol: str):
        self.symbol = symbol

    @property
    def fast_info(self):
        return GetExplodes()

    @property
    def info(self):
        return GetExplodes()


def _auth_headers():
    return {'x-api-key': settings.api_master_key}


def test_quote_ok(monkeypatch):
    import app.routes.market as market
    monkeypatch.setattr(market.yf, 'Ticker', DummyTicker)

    r = client.get('/v1/quote/AAPL', headers=_auth_headers())
    assert r.status_code == 200
    body = r.json()
    assert body['symbol'] == 'AAPL'
    assert body['last_price'] == 123.45
    assert body['stale'] is False


def test_quotes_batch_mixed(monkeypatch):
    import app.routes.market as market
    monkeypatch.setattr(market.yf, 'Ticker', DummyTicker)

    r = client.get('/v1/quotes?symbols=AAPL,BAD,MSFT', headers=_auth_headers())
    assert r.status_code == 200
    body = r.json()
    assert body['count'] == 3
    assert any(not item['ok'] for item in body['data'])


def test_history_ok(monkeypatch):
    import app.routes.market as market
    monkeypatch.setattr(market.yf, 'Ticker', DummyTicker)

    r = client.get('/v1/history/AAPL?period=1mo&interval=1d', headers=_auth_headers())
    assert r.status_code == 200
    body = r.json()
    assert body['count'] == 2
    assert len(body['data']) == 2


def test_fundamentals_ok(monkeypatch):
    import app.routes.market as market
    monkeypatch.setattr(market.yf, 'Ticker', DummyTicker)

    r = client.get('/v1/fundamentals/AAPL', headers=_auth_headers())
    assert r.status_code == 200
    body = r.json()
    assert body['symbol'] == 'AAPL'
    assert body['sector'] == 'Technology'
    assert body['stale'] is False


def test_history_invalid_period_400(monkeypatch):
    import app.routes.market as market
    monkeypatch.setattr(market.yf, 'Ticker', DummyTicker)

    r = client.get('/v1/history/AAPL?period=13mo&interval=1d', headers=_auth_headers())
    assert r.status_code == 400
    assert r.json()['detail'] == 'Invalid period'


def test_history_invalid_interval_400(monkeypatch):
    import app.routes.market as market
    monkeypatch.setattr(market.yf, 'Ticker', DummyTicker)

    r = client.get('/v1/history/AAPL?period=1mo&interval=2h', headers=_auth_headers())
    assert r.status_code == 400
    assert r.json()['detail'] == 'Invalid interval'


def test_history_start_gt_end_400(monkeypatch):
    import app.routes.market as market
    monkeypatch.setattr(market.yf, 'Ticker', DummyTicker)

    r = client.get('/v1/history/AAPL?period=1mo&interval=1d&start=2026-02-01&end=2026-01-01', headers=_auth_headers())
    assert r.status_code == 400
    assert r.json()['detail'] == 'start must be <= end'


def test_quote_sanitizes_non_finite_numbers_to_null(monkeypatch):
    import app.routes.market as market
    monkeypatch.setattr(market.yf, 'Ticker', NonFiniteTicker)

    r = client.get('/v1/quote/AAPL', headers=_auth_headers())
    assert r.status_code == 200
    body = r.json()
    assert body['last_price'] is None
    assert body['open'] is None
    assert body['day_low'] is None
    assert body['volume'] is None
    assert body['market_cap'] is None


def test_quotes_batch_sanitizes_non_finite_numbers_to_null(monkeypatch):
    import app.routes.market as market
    monkeypatch.setattr(market.yf, 'Ticker', NonFiniteTicker)

    r = client.get('/v1/quotes?symbols=AAPL,MSFT', headers=_auth_headers())
    assert r.status_code == 200
    body = r.json()
    assert body['count'] == 2
    for row in body['data']:
        assert row['ok'] is True
        assert row['last_price'] is None
        assert row['open'] is None
        assert row['day_low'] is None
        assert row['volume'] is None
        assert row['market_cap'] is None


def test_fundamentals_sanitizes_non_finite_numbers_to_null(monkeypatch):
    import app.routes.market as market
    monkeypatch.setattr(market.yf, 'Ticker', NonFiniteTicker)

    r = client.get('/v1/fundamentals/AAPL', headers=_auth_headers())
    assert r.status_code == 200
    body = r.json()
    assert body['trailing_pe'] is None
    assert body['forward_pe'] is None
    assert body['dividend_yield'] is None
    assert body['fifty_two_week_high'] is None


def test_quote_uses_stale_cache_on_upstream_failure(monkeypatch):
    import app.routes.market as market

    market._CACHE.clear()
    monkeypatch.setattr(market, 'time', type('T', (), {'time': staticmethod(lambda: 1000.0)}))
    FlakyTicker.fail_mode = False
    monkeypatch.setattr(market.yf, 'Ticker', FlakyTicker)

    warm = client.get('/v1/quote/AAPL', headers=_auth_headers())
    assert warm.status_code == 200
    assert warm.json()['stale'] is False

    monkeypatch.setattr(market, 'time', type('T', (), {'time': staticmethod(lambda: 1040.0)}))
    FlakyTicker.fail_mode = True
    stale = client.get('/v1/quote/AAPL', headers=_auth_headers())
    assert stale.status_code == 200
    assert stale.json()['stale'] is True


def test_fundamentals_uses_stale_cache_on_upstream_failure(monkeypatch):
    import app.routes.market as market

    market._CACHE.clear()
    monkeypatch.setattr(market, 'time', type('T', (), {'time': staticmethod(lambda: 2000.0)}))
    FlakyTicker.fail_mode = False
    monkeypatch.setattr(market.yf, 'Ticker', FlakyTicker)

    warm = client.get('/v1/fundamentals/AAPL', headers=_auth_headers())
    assert warm.status_code == 200
    assert warm.json()['stale'] is False

    monkeypatch.setattr(market, 'time', type('T', (), {'time': staticmethod(lambda: 2040.0)}))
    FlakyTicker.fail_mode = True
    stale = client.get('/v1/fundamentals/AAPL', headers=_auth_headers())
    assert stale.status_code == 200
    assert stale.json()['stale'] is True


def test_quote_field_read_failure_maps_to_502(monkeypatch):
    import app.routes.market as market

    monkeypatch.setattr(market.yf, 'Ticker', InfoGetExplodesTicker)
    r = client.get('/v1/quote/AAPL', headers=_auth_headers())
    assert r.status_code == 502


def test_fundamentals_field_read_failure_maps_to_502(monkeypatch):
    import app.routes.market as market

    monkeypatch.setattr(market.yf, 'Ticker', InfoGetExplodesTicker)
    r = client.get('/v1/fundamentals/AAPL', headers=_auth_headers())
    assert r.status_code == 502


def test_quotes_field_read_failure_maps_to_upstream_error(monkeypatch):
    import app.routes.market as market

    monkeypatch.setattr(market.yf, 'Ticker', InfoGetExplodesTicker)
    r = client.get('/v1/quotes?symbols=AAPL,MSFT', headers=_auth_headers())
    assert r.status_code == 200
    body = r.json()
    assert body['count'] == 2
    assert all(item['ok'] is False and item['error'] == 'upstream_error' for item in body['data'])
