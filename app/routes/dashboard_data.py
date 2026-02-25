from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models import APIKey
from app.security import hash_api_key

OverviewRange = Literal["24h", "7d", "30d"]
MetricsRange = Literal["24h", "7d", "30d"]
ActivityStatus = Literal["success", "info", "error"]

_OVERVIEW_BY_RANGE: dict[OverviewRange, dict] = {
    "24h": {
        "requests": 12842,
        "errorRatePct": 0.62,
        "p95LatencyMs": 184,
        "fiveXx": 9,
        "topEndpoints": [
            {"path": "/v1/quote/{symbol}", "requests": 8120, "errorPct": 0.41, "p95Ms": 142},
            {"path": "/v1/history/{symbol}", "requests": 2990, "errorPct": 0.95, "p95Ms": 246},
            {"path": "/v1/quotes", "requests": 1732, "errorPct": 0.78, "p95Ms": 201},
        ],
    },
    "7d": {
        "requests": 90587,
        "errorRatePct": 0.58,
        "p95LatencyMs": 191,
        "fiveXx": 55,
        "topEndpoints": [
            {"path": "/v1/quote/{symbol}", "requests": 58130, "errorPct": 0.39, "p95Ms": 151},
            {"path": "/v1/history/{symbol}", "requests": 20077, "errorPct": 0.81, "p95Ms": 252},
            {"path": "/v1/quotes", "requests": 12380, "errorPct": 0.66, "p95Ms": 209},
        ],
    },
    "30d": {
        "requests": 381204,
        "errorRatePct": 0.71,
        "p95LatencyMs": 203,
        "fiveXx": 320,
        "topEndpoints": [
            {"path": "/v1/quote/{symbol}", "requests": 243872, "errorPct": 0.48, "p95Ms": 159},
            {"path": "/v1/history/{symbol}", "requests": 86241, "errorPct": 1.02, "p95Ms": 266},
            {"path": "/v1/quotes", "requests": 51091, "errorPct": 0.84, "p95Ms": 216},
        ],
    },
}

_METRICS_BY_RANGE: dict[MetricsRange, dict] = {
    "24h": {
        "summary": {"requests": 12842, "errorRatePct": 0.62, "p95LatencyMs": 184, "fiveXx": 9},
        "requestTrend": [
            {"bucket": "00:00", "requests": 1804},
            {"bucket": "04:00", "requests": 1980},
            {"bucket": "08:00", "requests": 2231},
            {"bucket": "12:00", "requests": 2410},
            {"bucket": "16:00", "requests": 2312},
            {"bucket": "20:00", "requests": 2105},
        ],
        "statusBreakdown": [
            {"status": "2xx", "requests": 12542, "pct": 97.66},
            {"status": "4xx", "requests": 291, "pct": 2.27},
            {"status": "5xx", "requests": 9, "pct": 0.07},
        ],
        "latencyBuckets": [
            {"bucket": "0-100ms", "requests": 6010, "pct": 46.80},
            {"bucket": "101-250ms", "requests": 5010, "pct": 39.01},
            {"bucket": "251-500ms", "requests": 1512, "pct": 11.77},
            {"bucket": ">500ms", "requests": 310, "pct": 2.42},
        ],
        "topEndpoints": [
            {"method": "GET", "path": "/v1/quote/{symbol}", "requests": 8120, "errorPct": 0.41, "p95Ms": 142},
            {"method": "GET", "path": "/v1/history/{symbol}", "requests": 2990, "errorPct": 0.95, "p95Ms": 246},
            {"method": "GET", "path": "/v1/quotes", "requests": 1732, "errorPct": 0.78, "p95Ms": 201},
        ],
    },
    "7d": {
        "summary": {"requests": 90587, "errorRatePct": 0.58, "p95LatencyMs": 191, "fiveXx": 55},
        "requestTrend": [
            {"bucket": "Mon", "requests": 12441},
            {"bucket": "Tue", "requests": 12703},
            {"bucket": "Wed", "requests": 12922},
            {"bucket": "Thu", "requests": 13110},
            {"bucket": "Fri", "requests": 13744},
            {"bucket": "Sat", "requests": 13270},
            {"bucket": "Sun", "requests": 12397},
        ],
        "statusBreakdown": [
            {"status": "2xx", "requests": 88432, "pct": 97.62},
            {"status": "4xx", "requests": 2100, "pct": 2.32},
            {"status": "5xx", "requests": 55, "pct": 0.06},
        ],
        "latencyBuckets": [
            {"bucket": "0-100ms", "requests": 40522, "pct": 44.73},
            {"bucket": "101-250ms", "requests": 36780, "pct": 40.60},
            {"bucket": "251-500ms", "requests": 11412, "pct": 12.60},
            {"bucket": ">500ms", "requests": 1873, "pct": 2.07},
        ],
        "topEndpoints": [
            {"method": "GET", "path": "/v1/quote/{symbol}", "requests": 58130, "errorPct": 0.39, "p95Ms": 151},
            {"method": "GET", "path": "/v1/history/{symbol}", "requests": 20077, "errorPct": 0.81, "p95Ms": 252},
            {"method": "GET", "path": "/v1/quotes", "requests": 12380, "errorPct": 0.66, "p95Ms": 209},
        ],
    },
    "30d": {
        "summary": {"requests": 381204, "errorRatePct": 0.71, "p95LatencyMs": 203, "fiveXx": 320},
        "requestTrend": [
            {"bucket": "Week 1", "requests": 90812},
            {"bucket": "Week 2", "requests": 93442},
            {"bucket": "Week 3", "requests": 96551},
            {"bucket": "Week 4", "requests": 100399},
        ],
        "statusBreakdown": [
            {"status": "2xx", "requests": 371420, "pct": 97.43},
            {"status": "4xx", "requests": 9464, "pct": 2.48},
            {"status": "5xx", "requests": 320, "pct": 0.09},
        ],
        "latencyBuckets": [
            {"bucket": "0-100ms", "requests": 163903, "pct": 42.99},
            {"bucket": "101-250ms", "requests": 157004, "pct": 41.18},
            {"bucket": "251-500ms", "requests": 50781, "pct": 13.32},
            {"bucket": ">500ms", "requests": 9516, "pct": 2.50},
        ],
        "topEndpoints": [
            {"method": "GET", "path": "/v1/quote/{symbol}", "requests": 243872, "errorPct": 0.48, "p95Ms": 159},
            {"method": "GET", "path": "/v1/history/{symbol}", "requests": 86241, "errorPct": 1.02, "p95Ms": 266},
            {"method": "GET", "path": "/v1/quotes", "requests": 51091, "errorPct": 0.84, "p95Ms": 216},
        ],
    },
}


class DashboardKey(BaseModel):
    id: str
    label: str
    prefix: str
    env: Literal["live", "test"]
    active: bool
    lastUsed: str


class CreateKeyRequest(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    env: Literal["live", "test"] = "test"


def _key_env(api_key: APIKey) -> Literal["live", "test"]:
    if api_key.name.lower().startswith("test:"):
        return "test"
    return "live"


def _humanize_last_used(value: datetime | None) -> str:
    if value is None:
        return "never"

    now = datetime.now(UTC)
    normalized = value if value.tzinfo else value.replace(tzinfo=UTC)
    delta = now - normalized

    if delta < timedelta(minutes=1):
        return "just now"
    if delta < timedelta(hours=1):
        return f"{int(delta.total_seconds() // 60)}m ago"
    if delta < timedelta(days=1):
        return f"{int(delta.total_seconds() // 3600)}h ago"
    return f"{delta.days}d ago"


def _masked_prefix(api_key: APIKey) -> str:
    env = _key_env(api_key)
    return f"yf_{env}_••{api_key.id:04d}"


def _dashboard_key(api_key: APIKey) -> DashboardKey:
    env = _key_env(api_key)
    label = api_key.name
    if label.lower().startswith(("test:", "live:")):
        label = label.split(":", 1)[1].strip() or label

    return DashboardKey(
        id=str(api_key.id),
        label=label,
        prefix=_masked_prefix(api_key),
        env=env,
        active=api_key.status == "active",
        lastUsed=_humanize_last_used(api_key.last_used_at),
    )


def _key_list(db: Session, user_id: int) -> list[dict]:
    rows = (
        db.query(APIKey)
        .filter(APIKey.user_id == user_id)
        .order_by(APIKey.id.desc())
        .all()
    )
    return [_dashboard_key(row).model_dump() for row in rows]


def _success(action: str, db: Session, user_id: int, key: DashboardKey | None = None, raw_key: str | None = None) -> dict:
    payload: dict = {
        "ok": True,
        "source": "db-store",
        "action": action,
        "data": {
            "key": key.model_dump() if key else None,
            "keys": _key_list(db, user_id),
        },
        "error": None,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if raw_key is not None:
        payload["data"]["rawKey"] = raw_key
    return payload


def _missing_key_error(action: str, key_id: str, db: Session, user_id: int) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={
            "ok": False,
            "source": "db-store",
            "action": action,
            "data": {"key": None, "keys": _key_list(db, user_id)},
            "error": {
                "code": "KEY_NOT_FOUND",
                "message": f"Key '{key_id}' was not found.",
            },
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def _find_user_key(db: Session, user_id: int, key_id: str) -> APIKey | None:
    try:
        key_pk = int(key_id)
    except ValueError:
        return None

    return (
        db.query(APIKey)
        .filter(APIKey.id == key_pk, APIKey.user_id == user_id)
        .first()
    )


def get_dashboard_overview(range: OverviewRange):
    selected = _OVERVIEW_BY_RANGE[range]
    return {
        "requests24h": selected["requests"],
        "fiveXx24h": selected["fiveXx"],
        "range": range,
        "requests": selected["requests"],
        "fiveXx": selected["fiveXx"],
        "errorRatePct": selected["errorRatePct"],
        "p95LatencyMs": selected["p95LatencyMs"],
        "topEndpoints": selected["topEndpoints"],
        "source": "placeholder",
    }


def get_dashboard_metrics(range: MetricsRange):
    selected = _METRICS_BY_RANGE[range]
    return {
        "range": range,
        "source": "placeholder",
        **selected,
    }


def get_dashboard_activity(
    tenant_id: str,
    actor_email: str,
    status: ActivityStatus | None = None,
    action: str | None = None,
    limit: int = 25,
):
    tenant_fragment = "".join(ch if ch.isalnum() else "-" for ch in tenant_id.lower()).strip("-") or "tenant"
    events = [
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "actor": "system",
            "action": "key.rotate",
            "status": "success",
            "target": f"key_{tenant_fragment}_live_primary",
        },
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "actor": actor_email,
            "action": "key.create",
            "status": "success",
            "target": f"{tenant_fragment}-zapier-sandbox",
        },
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "actor": "system",
            "action": "usage.alert",
            "status": "info",
            "target": f"{tenant_fragment}:p95-latency-spike",
        },
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "actor": "system",
            "action": "key.rotate",
            "status": "error",
            "target": f"key_{tenant_fragment}_test_zapier",
        },
    ]

    if status:
        events = [event for event in events if event["status"] == status]

    if action:
        action_query = action.lower()
        events = [event for event in events if action_query in event["action"].lower()]

    return {"source": "placeholder", "events": events[:limit]}


def get_dashboard_keys(db: Session, user_id: int):
    return {"keys": _key_list(db, user_id), "source": "db-store"}


def create_dashboard_key(db: Session, user_id: int, payload: CreateKeyRequest):
    raw_key = f"yf_{payload.env}_{secrets.token_urlsafe(24)}"
    label = payload.label.strip()

    api_key = APIKey(
        key_hash=hash_api_key(raw_key),
        user_id=user_id,
        name=f"{payload.env}:{label}",
        status="active",
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return _success("create", db, user_id, _dashboard_key(api_key), raw_key=raw_key)


def rotate_dashboard_key(db: Session, user_id: int, key_id: str):
    api_key = _find_user_key(db, user_id, key_id)
    if not api_key:
        raise _missing_key_error("rotate", key_id, db, user_id)

    env = _key_env(api_key)
    raw_key = f"yf_{env}_{secrets.token_urlsafe(24)}"
    api_key.key_hash = hash_api_key(raw_key)
    api_key.status = "active"
    api_key.last_used_at = datetime.now(UTC)

    db.commit()
    db.refresh(api_key)

    return _success("rotate", db, user_id, _dashboard_key(api_key), raw_key=raw_key)


def revoke_dashboard_key(db: Session, user_id: int, key_id: str):
    api_key = _find_user_key(db, user_id, key_id)
    if not api_key:
        raise _missing_key_error("revoke", key_id, db, user_id)

    api_key.status = "revoked"
    api_key.last_used_at = datetime.now(UTC)
    db.commit()
    db.refresh(api_key)

    return _success("revoke", db, user_id, _dashboard_key(api_key))


def activate_dashboard_key(db: Session, user_id: int, key_id: str):
    api_key = _find_user_key(db, user_id, key_id)
    if not api_key:
        raise _missing_key_error("activate", key_id, db, user_id)

    api_key.status = "active"
    api_key.last_used_at = datetime.now(UTC)
    db.commit()
    db.refresh(api_key)

    return _success("activate", db, user_id, _dashboard_key(api_key))
