from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from math import ceil
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import APIKey, UsageLog
from app.security import hash_api_key

OverviewRange = Literal["24h", "7d", "30d"]
MetricsRange = Literal["24h", "7d", "30d"]
ActivityStatus = Literal["success", "info", "error"]

_RANGE_WINDOWS: dict[OverviewRange, timedelta] = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
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


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _window_start(range_value: OverviewRange | MetricsRange) -> datetime:
    return datetime.now(UTC) - _RANGE_WINDOWS[range_value]


def _humanize_last_used(value: datetime | None) -> str:
    if value is None:
        return "never"

    now = datetime.now(UTC)
    normalized = _normalize_utc(value)
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


def _usage_rows(db: Session, user_id: int, range_value: OverviewRange | MetricsRange) -> list[UsageLog]:
    start_at = _window_start(range_value)
    return (
        db.query(UsageLog)
        .join(APIKey, APIKey.id == UsageLog.api_key_id)
        .filter(APIKey.user_id == user_id, UsageLog.created_at >= start_at)
        .all()
    )


def _safe_pct(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return round((part / whole) * 100, 2)


def _p95(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, ceil(0.95 * len(ordered)) - 1)
    return int(ordered[index])


def _top_endpoints(rows: list[UsageLog], *, include_method: bool) -> list[dict]:
    grouped: dict[str, dict[str, int | list[int]]] = {}

    for row in rows:
        entry = grouped.setdefault(
            row.endpoint,
            {"requests": 0, "errors": 0, "latencies": []},
        )
        entry["requests"] = int(entry["requests"]) + 1
        if row.status_code >= 400:
            entry["errors"] = int(entry["errors"]) + 1
        latencies = entry["latencies"]
        assert isinstance(latencies, list)
        latencies.append(int(row.response_ms))

    top = sorted(grouped.items(), key=lambda item: int(item[1]["requests"]), reverse=True)[:5]

    payload: list[dict] = []
    for endpoint, stats in top:
        requests = int(stats["requests"])
        errors = int(stats["errors"])
        latencies = stats["latencies"]
        assert isinstance(latencies, list)

        row = {
            "path": endpoint,
            "requests": requests,
            "errorPct": _safe_pct(errors, requests),
            "p95Ms": _p95(latencies),
        }
        if include_method:
            row = {"method": "GET", **row}
        payload.append(row)

    return payload


def get_dashboard_overview(db: Session, user_id: int, range: OverviewRange):
    rows = _usage_rows(db, user_id, range)
    total_requests = len(rows)
    five_xx = sum(1 for row in rows if 500 <= row.status_code < 600)
    errors = sum(1 for row in rows if row.status_code >= 400)
    p95_latency = _p95([int(row.response_ms) for row in rows])

    total_keys = int(
        db.query(func.count(APIKey.id))
        .filter(APIKey.user_id == user_id)
        .scalar()
        or 0
    )
    active_keys = int(
        db.query(func.count(APIKey.id))
        .filter(APIKey.user_id == user_id, APIKey.status == "active")
        .scalar()
        or 0
    )

    return {
        "requests24h": total_requests,
        "fiveXx24h": five_xx,
        "range": range,
        "requests": total_requests,
        "fiveXx": five_xx,
        "errorRatePct": _safe_pct(errors, total_requests),
        "p95LatencyMs": p95_latency,
        "totalKeys": total_keys,
        "activeKeys": active_keys,
        "topEndpoints": _top_endpoints(rows, include_method=False),
        "source": "db-store",
    }


def _request_trend(range_value: MetricsRange, rows: list[UsageLog], now: datetime) -> list[dict]:
    if range_value == "24h":
        bucket_hours = 4
        bucket_count = 6
        start_at = now - timedelta(hours=24)
        buckets = [start_at + timedelta(hours=bucket_hours * idx) for idx in range(bucket_count)]
        labels = [bucket.strftime("%H:%M") for bucket in buckets]
        counts = [0 for _ in labels]

        for row in rows:
            created_at = _normalize_utc(row.created_at)
            delta_hours = (created_at - start_at).total_seconds() / 3600
            index = int(delta_hours // bucket_hours)
            if 0 <= index < bucket_count:
                counts[index] += 1

        return [{"bucket": label, "requests": count} for label, count in zip(labels, counts, strict=False)]

    if range_value == "7d":
        start_day = (now - timedelta(days=6)).date()
        labels = []
        counts = []
        for idx in range(7):
            day = start_day + timedelta(days=idx)
            labels.append(day.strftime("%a"))
            counts.append(0)

        day_to_index = {((start_day + timedelta(days=i)).isoformat()): i for i in range(7)}
        for row in rows:
            day_key = _normalize_utc(row.created_at).date().isoformat()
            if day_key in day_to_index:
                counts[day_to_index[day_key]] += 1

        return [{"bucket": label, "requests": count} for label, count in zip(labels, counts, strict=False)]

    # 30d -> 4 weekly buckets
    start_at = now - timedelta(days=30)
    counts = [0, 0, 0, 0]
    for row in rows:
        delta_days = (_normalize_utc(row.created_at) - start_at).total_seconds() / 86400
        index = int(delta_days // 7)
        if 0 <= index <= 3:
            counts[index] += 1

    return [
        {"bucket": "Week 1", "requests": counts[0]},
        {"bucket": "Week 2", "requests": counts[1]},
        {"bucket": "Week 3", "requests": counts[2]},
        {"bucket": "Week 4", "requests": counts[3]},
    ]


def get_dashboard_metrics(db: Session, user_id: int, range: MetricsRange):
    rows = _usage_rows(db, user_id, range)
    total_requests = len(rows)
    five_xx = sum(1 for row in rows if 500 <= row.status_code < 600)
    all_errors = sum(1 for row in rows if row.status_code >= 400)
    p95_latency = _p95([int(row.response_ms) for row in rows])

    two_xx = sum(1 for row in rows if 200 <= row.status_code < 300)
    four_xx = sum(1 for row in rows if 400 <= row.status_code < 500)

    latency_0_100 = sum(1 for row in rows if row.response_ms <= 100)
    latency_101_250 = sum(1 for row in rows if 101 <= row.response_ms <= 250)
    latency_251_500 = sum(1 for row in rows if 251 <= row.response_ms <= 500)
    latency_500_plus = sum(1 for row in rows if row.response_ms > 500)

    now = datetime.now(UTC)
    return {
        "range": range,
        "source": "db-store",
        "summary": {
            "requests": total_requests,
            "errorRatePct": _safe_pct(all_errors, total_requests),
            "p95LatencyMs": p95_latency,
            "fiveXx": five_xx,
        },
        "requestTrend": _request_trend(range_value=range, rows=rows, now=now),
        "statusBreakdown": [
            {"status": "2xx", "requests": two_xx, "pct": _safe_pct(two_xx, total_requests)},
            {"status": "4xx", "requests": four_xx, "pct": _safe_pct(four_xx, total_requests)},
            {"status": "5xx", "requests": five_xx, "pct": _safe_pct(five_xx, total_requests)},
        ],
        "latencyBuckets": [
            {"bucket": "0-100ms", "requests": latency_0_100, "pct": _safe_pct(latency_0_100, total_requests)},
            {"bucket": "101-250ms", "requests": latency_101_250, "pct": _safe_pct(latency_101_250, total_requests)},
            {"bucket": "251-500ms", "requests": latency_251_500, "pct": _safe_pct(latency_251_500, total_requests)},
            {"bucket": ">500ms", "requests": latency_500_plus, "pct": _safe_pct(latency_500_plus, total_requests)},
        ],
        "topEndpoints": _top_endpoints(rows, include_method=True),
    }


def _activity_event_status(status_code: int) -> ActivityStatus:
    if status_code >= 500:
        return "error"
    if status_code >= 400:
        return "info"
    return "success"


def get_dashboard_activity(
    db: Session,
    user_id: int,
    actor_email: str,
    status: ActivityStatus | None = None,
    action: str | None = None,
    limit: int = 25,
):
    usage_rows = (
        db.query(UsageLog)
        .join(APIKey, APIKey.id == UsageLog.api_key_id)
        .filter(APIKey.user_id == user_id)
        .order_by(UsageLog.created_at.desc())
        .limit(max(limit * 4, 50))
        .all()
    )

    key_rows = (
        db.query(APIKey)
        .filter(APIKey.user_id == user_id)
        .order_by(APIKey.created_at.desc())
        .all()
    )

    events: list[dict] = []

    for row in usage_rows:
        created_at = _normalize_utc(row.created_at)
        events.append(
            {
                "timestamp": created_at.isoformat(),
                "actor": f"api-key:{row.api_key_id}",
                "action": "usage.request",
                "status": _activity_event_status(row.status_code),
                "target": row.endpoint,
            }
        )

    for key in key_rows:
        created_at = _normalize_utc(key.created_at)
        key_target = _masked_prefix(key)
        events.append(
            {
                "timestamp": created_at.isoformat(),
                "actor": actor_email,
                "action": "key.create",
                "status": "success",
                "target": key_target,
            }
        )

        if key.status == "revoked" and key.last_used_at is not None:
            revoked_at = _normalize_utc(key.last_used_at)
            events.append(
                {
                    "timestamp": revoked_at.isoformat(),
                    "actor": actor_email,
                    "action": "key.revoke",
                    "status": "info",
                    "target": key_target,
                }
            )

    if status:
        events = [event for event in events if event["status"] == status]

    if action:
        action_query = action.lower()
        events = [event for event in events if action_query in event["action"].lower()]

    events.sort(key=lambda event: event["timestamp"], reverse=True)

    return {"source": "db-store", "events": events[:limit]}


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
