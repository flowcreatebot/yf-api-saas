from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/internal/api", tags=["internal-dashboard"])


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


_store_lock = Lock()
_key_store: dict[str, DashboardKey] = {
    "key_live_primary": DashboardKey(
        id="key_live_primary",
        label="Primary production",
        prefix="yf_live_••••",
        env="live",
        active=True,
        lastUsed="5m ago",
    ),
    "key_test_zapier": DashboardKey(
        id="key_test_zapier",
        label="Zapier trial",
        prefix="yf_test_••••",
        env="test",
        active=True,
        lastUsed="42m ago",
    ),
}


def _masked_prefix(env: Literal["live", "test"]) -> str:
    tag = "live" if env == "live" else "test"
    # Placeholder-safe mask only; no secret tokens are ever generated or exposed.
    return f"yf_{tag}_••{uuid4().hex[:4]}"


def _key_list() -> list[dict]:
    return [k.model_dump() for k in _key_store.values()]


def _success(action: str, key: DashboardKey | None = None) -> dict:
    payload = {
        "ok": True,
        "source": "mock-store",
        "action": action,
        "data": {
            "key": key.model_dump() if key else None,
            "keys": _key_list(),
        },
        "error": None,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    return payload


def _missing_key_error(action: str, key_id: str) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={
            "ok": False,
            "source": "mock-store",
            "action": action,
            "data": {"key": None, "keys": _key_list()},
            "error": {
                "code": "KEY_NOT_FOUND",
                "message": f"Key '{key_id}' was not found.",
            },
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@router.get("/overview")
def get_dashboard_overview():
    """Placeholder dashboard payload until real analytics pipeline is wired."""
    return {
        "requests24h": 12842,
        "errorRatePct": 0.62,
        "p95LatencyMs": 184,
        "fiveXx24h": 9,
        "topEndpoints": [
            {"path": "/v1/quote/{symbol}", "requests": 8120, "errorPct": 0.41, "p95Ms": 142},
            {"path": "/v1/history/{symbol}", "requests": 2990, "errorPct": 0.95, "p95Ms": 246},
            {"path": "/v1/quotes", "requests": 1732, "errorPct": 0.78, "p95Ms": 201},
        ],
        "source": "placeholder",
    }


@router.get("/keys")
def get_dashboard_keys():
    """Mock key inventory payload for dashboard API key management."""
    with _store_lock:
        return {
            "keys": _key_list(),
            "source": "mock-store",
        }


@router.post("/keys/create")
def create_dashboard_key(payload: CreateKeyRequest):
    with _store_lock:
        key_id = f"key_{uuid4().hex[:10]}"
        key = DashboardKey(
            id=key_id,
            label=payload.label.strip(),
            env=payload.env,
            prefix=_masked_prefix(payload.env),
            active=True,
            lastUsed="just now",
        )
        _key_store[key_id] = key
        return _success(action="create", key=key)


@router.post("/keys/{key_id}/rotate")
def rotate_dashboard_key(key_id: str):
    with _store_lock:
        key = _key_store.get(key_id)
        if not key:
            raise _missing_key_error("rotate", key_id)

        updated = key.model_copy(update={"prefix": _masked_prefix(key.env), "lastUsed": "rotated now"})
        _key_store[key_id] = updated
        return _success(action="rotate", key=updated)


@router.post("/keys/{key_id}/revoke")
def revoke_dashboard_key(key_id: str):
    with _store_lock:
        key = _key_store.get(key_id)
        if not key:
            raise _missing_key_error("revoke", key_id)

        updated = key.model_copy(update={"active": False, "lastUsed": "revoked now"})
        _key_store[key_id] = updated
        return _success(action="revoke", key=updated)


@router.post("/keys/{key_id}/activate")
def activate_dashboard_key(key_id: str):
    with _store_lock:
        key = _key_store.get(key_id)
        if not key:
            raise _missing_key_error("activate", key_id)

        updated = key.model_copy(update={"active": True, "lastUsed": "activated now"})
        _key_store[key_id] = updated
        return _success(action="activate", key=updated)
