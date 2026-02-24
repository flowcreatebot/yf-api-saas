from datetime import datetime
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings


client = TestClient(app)


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


def test_history_invalid_period_400(monkeypatch):
    import app.routes.market as market
    monkeypatch.setattr(market.yf, 'Ticker', DummyTicker)

    r = client.get('/v1/history/AAPL?period=13mo&interval=1d', headers=_auth_headers())
    assert r.status_code == 400


def test_history_invalid_interval_400(monkeypatch):
    import app.routes.market as market
    monkeypatch.setattr(market.yf, 'Ticker', DummyTicker)

    r = client.get('/v1/history/AAPL?period=1mo&interval=2h', headers=_auth_headers())
    assert r.status_code == 400


def test_history_start_gt_end_400(monkeypatch):
    import app.routes.market as market
    monkeypatch.setattr(market.yf, 'Ticker', DummyTicker)

    r = client.get('/v1/history/AAPL?period=1mo&interval=1d&start=2026-02-01&end=2026-01-01', headers=_auth_headers())
    assert r.status_code == 400
    assert r.json()['detail'] == 'start must be <= end'
