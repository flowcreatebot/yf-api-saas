from datetime import date
import re
import threading
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
import yfinance as yf

from ..auth import require_api_key
from ..config import settings

router = APIRouter(prefix="/v1", tags=["market"])

SYMBOL_RE = re.compile(r"^[A-Z0-9.\-]{1,15}$")
ALLOWED_PERIODS = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}
ALLOWED_INTERVALS = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"}


class _InMemoryTTLCache:
    def __init__(self, ttl_seconds: int, stale_window_seconds: int):
        self.ttl_seconds = max(1, int(ttl_seconds))
        self.stale_window_seconds = max(self.ttl_seconds, int(stale_window_seconds))
        self._items: dict[str, tuple[float, dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def get_fresh(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            item = self._items.get(key)
        if item is None:
            return None

        fetched_at, payload = item
        if (time.time() - fetched_at) <= self.ttl_seconds:
            return payload
        return None

    def get_stale(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            item = self._items.get(key)
        if item is None:
            return None

        fetched_at, payload = item
        if (time.time() - fetched_at) <= self.stale_window_seconds:
            return payload
        return None

    def set(self, key: str, payload: dict[str, Any]) -> None:
        with self._lock:
            self._items[key] = (time.time(), payload)


_market_cache = _InMemoryTTLCache(
    ttl_seconds=settings.market_cache_ttl_seconds,
    stale_window_seconds=settings.market_cache_stale_window_seconds,
)


def _cache_key(endpoint: str, symbol: str) -> str:
    return f"{endpoint}:{symbol}"


def _normalize_symbol(raw_symbol: str) -> str:
    symbol = raw_symbol.strip().upper()
    if not SYMBOL_RE.fullmatch(symbol):
        raise HTTPException(status_code=400, detail="Invalid symbol format")
    return symbol


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/quote/{symbol}")
def quote(symbol: str, _: str = Depends(require_api_key)):
    symbol = _normalize_symbol(symbol)
    key = _cache_key("quote", symbol)

    cached = _market_cache.get_fresh(key)
    if cached is not None:
        return {**cached, "stale": False}

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info or {}
    except Exception as exc:
        stale = _market_cache.get_stale(key)
        if stale is not None:
            return {**stale, "stale": True}
        raise HTTPException(status_code=502, detail=f"Upstream provider error: {exc}")

    if not info:
        raise HTTPException(status_code=404, detail="Symbol not found or unavailable")

    payload = {
        "symbol": symbol.upper(),
        "currency": info.get("currency"),
        "exchange": info.get("exchange"),
        "last_price": info.get("lastPrice"),
        "open": info.get("open"),
        "day_high": info.get("dayHigh"),
        "day_low": info.get("dayLow"),
        "previous_close": info.get("previousClose"),
        "volume": info.get("lastVolume"),
        "market_cap": info.get("marketCap"),
    }
    _market_cache.set(key, payload)
    return {**payload, "stale": False}


@router.get("/history/{symbol}")
def history(
    symbol: str,
    period: str = Query(default="1mo", description="e.g. 1d, 5d, 1mo, 3mo, 1y, 5y, max"),
    interval: str = Query(default="1d", description="e.g. 1m, 5m, 1h, 1d, 1wk"),
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    _: str = Depends(require_api_key),
):
    symbol = _normalize_symbol(symbol)
    period = period.strip().lower()
    interval = interval.strip().lower()

    if period not in ALLOWED_PERIODS:
        raise HTTPException(status_code=400, detail="Invalid period")
    if interval not in ALLOWED_INTERVALS:
        raise HTTPException(status_code=400, detail="Invalid interval")
    if start is not None and end is not None and start > end:
        raise HTTPException(status_code=400, detail="start must be <= end")

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval, start=start, end=end, auto_adjust=False)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstream provider error: {exc}")

    if df.empty:
        raise HTTPException(status_code=404, detail="No historical data found")

    rows = []
    for idx, row in df.iterrows():
        rows.append(
            {
                "ts": idx.isoformat(),
                "open": None if row.get("Open") is None else float(row["Open"]),
                "high": None if row.get("High") is None else float(row["High"]),
                "low": None if row.get("Low") is None else float(row["Low"]),
                "close": None if row.get("Close") is None else float(row["Close"]),
                "volume": None if row.get("Volume") is None else int(row["Volume"]),
            }
        )

    return {
        "symbol": symbol.upper(),
        "period": period,
        "interval": interval,
        "count": len(rows),
        "data": rows,
    }


@router.get("/quotes")
def quotes(
    symbols: str = Query(..., description="Comma-separated symbols, e.g. AAPL,MSFT,TSLA"),
    _: str = Depends(require_api_key),
):
    raw = [s.strip() for s in symbols.split(",") if s.strip()]
    if not raw:
        raise HTTPException(status_code=400, detail="No symbols provided")
    if len(raw) > 25:
        raise HTTPException(status_code=400, detail="Maximum 25 symbols per request")

    normalized_symbols = [_normalize_symbol(s) for s in raw]

    results = []
    for symbol in normalized_symbols:
        key = _cache_key("quote", symbol)
        cached = _market_cache.get_fresh(key)
        if cached is not None:
            results.append({**cached, "ok": True, "stale": False})
            continue

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info or {}
        except Exception:
            stale = _market_cache.get_stale(key)
            if stale is not None:
                results.append({**stale, "ok": True, "stale": True})
            else:
                results.append({"symbol": symbol, "ok": False, "error": "upstream_error"})
            continue

        if not info:
            results.append({"symbol": symbol, "ok": False, "error": "unavailable"})
            continue

        payload = {
            "symbol": symbol,
            "currency": info.get("currency"),
            "last_price": info.get("lastPrice"),
            "open": info.get("open"),
            "day_high": info.get("dayHigh"),
            "day_low": info.get("dayLow"),
            "previous_close": info.get("previousClose"),
            "volume": info.get("lastVolume"),
            "market_cap": info.get("marketCap"),
        }
        _market_cache.set(key, payload)
        results.append({**payload, "ok": True, "stale": False})

    return {"count": len(results), "data": results}


@router.get("/fundamentals/{symbol}")
def fundamentals(symbol: str, _: str = Depends(require_api_key)):
    symbol = _normalize_symbol(symbol)
    key = _cache_key("fundamentals", symbol)

    cached = _market_cache.get_fresh(key)
    if cached is not None:
        return {**cached, "stale": False}

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
    except Exception as exc:
        stale = _market_cache.get_stale(key)
        if stale is not None:
            return {**stale, "stale": True}
        raise HTTPException(status_code=502, detail=f"Upstream provider error: {exc}")

    if not info:
        raise HTTPException(status_code=404, detail="Fundamentals unavailable")

    payload = {
        "symbol": symbol.upper(),
        "long_name": info.get("longName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "website": info.get("website"),
        "trailing_pe": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "price_to_book": info.get("priceToBook"),
        "dividend_yield": info.get("dividendYield"),
        "beta": info.get("beta"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
    }
    _market_cache.set(key, payload)
    return {**payload, "stale": False}
