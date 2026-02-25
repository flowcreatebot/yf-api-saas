from datetime import date
import math
import re
import threading
import time
from fastapi import APIRouter, Depends, HTTPException, Query, Request
import yfinance as yf

from ..auth import require_api_key
from ..config import settings
from ..rate_limit import default_market_rate_limit, limiter

router = APIRouter(prefix="/v1", tags=["market"])

SYMBOL_RE = re.compile(r"^[A-Z0-9.\-]{1,15}$")
ALLOWED_PERIODS = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}
ALLOWED_INTERVALS = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"}

_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, tuple[float, dict]] = {}


def _normalize_symbol(raw_symbol: str) -> str:
    symbol = raw_symbol.strip().upper()
    if not SYMBOL_RE.fullmatch(symbol):
        raise HTTPException(status_code=400, detail="Invalid symbol format")
    return symbol


def _cache_get(key: str) -> tuple[dict | None, bool]:
    now = time.time()
    with _CACHE_LOCK:
        entry = _CACHE.get(key)

    if entry is None:
        return None, False

    created_at, payload = entry
    age = now - created_at
    if age <= settings.market_cache_ttl_seconds:
        return payload, False
    if age <= settings.market_cache_stale_window_seconds:
        return payload, True
    return None, False


def _cache_set(key: str, payload: dict) -> None:
    with _CACHE_LOCK:
        _CACHE[key] = (time.time(), payload)


def _to_finite_float(value) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _to_finite_int(value) -> int | None:
    parsed = _to_finite_float(value)
    if parsed is None:
        return None
    return int(parsed)


def _safe_info_get(info, key: str):
    try:
        return info.get(key)
    except Exception as exc:
        raise RuntimeError(f"failed to read upstream field '{key}': {exc}") from exc


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/quote/{symbol}")
@limiter.limit(default_market_rate_limit)
def quote(request: Request, symbol: str, _: str = Depends(require_api_key)):
    symbol = _normalize_symbol(symbol)
    cache_key = f"quote:{symbol}"

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info or {}
    except Exception as exc:
        cached, is_stale = _cache_get(cache_key)
        if cached is not None and is_stale:
            return {**cached, "stale": True}
        raise HTTPException(status_code=502, detail=f"Upstream provider error: {exc}")

    if not info:
        raise HTTPException(status_code=404, detail="Symbol not found or unavailable")

    try:
        payload = {
            "symbol": symbol.upper(),
            "currency": _safe_info_get(info, "currency"),
            "exchange": _safe_info_get(info, "exchange"),
            "last_price": _to_finite_float(_safe_info_get(info, "lastPrice")),
            "open": _to_finite_float(_safe_info_get(info, "open")),
            "day_high": _to_finite_float(_safe_info_get(info, "dayHigh")),
            "day_low": _to_finite_float(_safe_info_get(info, "dayLow")),
            "previous_close": _to_finite_float(_safe_info_get(info, "previousClose")),
            "volume": _to_finite_int(_safe_info_get(info, "lastVolume")),
            "market_cap": _to_finite_int(_safe_info_get(info, "marketCap")),
        }
    except Exception as exc:
        cached, is_stale = _cache_get(cache_key)
        if cached is not None and is_stale:
            return {**cached, "stale": True}
        raise HTTPException(status_code=502, detail=f"Upstream provider error: {exc}")

    _cache_set(cache_key, payload)
    return {**payload, "stale": False}


@router.get("/history/{symbol}")
@limiter.limit(default_market_rate_limit)
def history(
    request: Request,
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
                "open": _to_finite_float(row.get("Open")),
                "high": _to_finite_float(row.get("High")),
                "low": _to_finite_float(row.get("Low")),
                "close": _to_finite_float(row.get("Close")),
                "volume": _to_finite_int(row.get("Volume")),
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
@limiter.limit(default_market_rate_limit)
def quotes(
    request: Request,
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
        cache_key = f"quote:{symbol}"
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info or {}
        except Exception:
            cached, is_stale = _cache_get(cache_key)
            if cached is not None and is_stale:
                results.append({**cached, "ok": True, "stale": True})
            else:
                results.append({"symbol": symbol, "ok": False, "error": "upstream_error"})
            continue

        if not info:
            results.append({"symbol": symbol, "ok": False, "error": "unavailable"})
            continue

        try:
            payload = {
                "symbol": symbol,
                "currency": _safe_info_get(info, "currency"),
                "last_price": _to_finite_float(_safe_info_get(info, "lastPrice")),
                "open": _to_finite_float(_safe_info_get(info, "open")),
                "day_high": _to_finite_float(_safe_info_get(info, "dayHigh")),
                "day_low": _to_finite_float(_safe_info_get(info, "dayLow")),
                "previous_close": _to_finite_float(_safe_info_get(info, "previousClose")),
                "volume": _to_finite_int(_safe_info_get(info, "lastVolume")),
                "market_cap": _to_finite_int(_safe_info_get(info, "marketCap")),
            }
        except Exception:
            cached, is_stale = _cache_get(cache_key)
            if cached is not None and is_stale:
                results.append({**cached, "ok": True, "stale": True})
            else:
                results.append({"symbol": symbol, "ok": False, "error": "upstream_error"})
            continue

        _cache_set(cache_key, payload)
        results.append({**payload, "ok": True, "stale": False})

    return {"count": len(results), "data": results}


@router.get("/fundamentals/{symbol}")
@limiter.limit(default_market_rate_limit)
def fundamentals(request: Request, symbol: str, _: str = Depends(require_api_key)):
    symbol = _normalize_symbol(symbol)
    cache_key = f"fundamentals:{symbol}"
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
    except Exception as exc:
        cached, is_stale = _cache_get(cache_key)
        if cached is not None and is_stale:
            return {**cached, "stale": True}
        raise HTTPException(status_code=502, detail=f"Upstream provider error: {exc}")

    if not info:
        raise HTTPException(status_code=404, detail="Fundamentals unavailable")

    try:
        payload = {
            "symbol": symbol.upper(),
            "long_name": _safe_info_get(info, "longName"),
            "sector": _safe_info_get(info, "sector"),
            "industry": _safe_info_get(info, "industry"),
            "website": _safe_info_get(info, "website"),
            "trailing_pe": _to_finite_float(_safe_info_get(info, "trailingPE")),
            "forward_pe": _to_finite_float(_safe_info_get(info, "forwardPE")),
            "price_to_book": _to_finite_float(_safe_info_get(info, "priceToBook")),
            "dividend_yield": _to_finite_float(_safe_info_get(info, "dividendYield")),
            "beta": _to_finite_float(_safe_info_get(info, "beta")),
            "fifty_two_week_high": _to_finite_float(_safe_info_get(info, "fiftyTwoWeekHigh")),
            "fifty_two_week_low": _to_finite_float(_safe_info_get(info, "fiftyTwoWeekLow")),
        }
    except Exception as exc:
        cached, is_stale = _cache_get(cache_key)
        if cached is not None and is_stale:
            return {**cached, "stale": True}
        raise HTTPException(status_code=502, detail=f"Upstream provider error: {exc}")

    _cache_set(cache_key, payload)

    return {**payload, "stale": False}
