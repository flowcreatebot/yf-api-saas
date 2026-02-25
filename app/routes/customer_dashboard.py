from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

from .dashboard_data import (
    ActivityStatus,
    CreateKeyRequest,
    MetricsRange,
    OverviewRange,
    activate_dashboard_key,
    create_dashboard_key,
    get_dashboard_activity,
    get_dashboard_keys,
    get_dashboard_metrics,
    get_dashboard_overview,
    revoke_dashboard_key,
    rotate_dashboard_key,
)

router = APIRouter(prefix="/dashboard/api", tags=["customer-dashboard"])


class CustomerSessionLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    tenantId: str = Field(min_length=2, max_length=80)


@dataclass
class CustomerSessionContext:
    token: str
    email: str
    tenant_id: str
    expires_at: datetime


_SESSION_TTL_HOURS = 8
_session_lock = Lock()
_session_store: dict[str, CustomerSessionContext] = {}


def _session_payload(session: CustomerSessionContext) -> dict:
    return {
        "token": session.token,
        "email": session.email,
        "tenantId": session.tenant_id,
        "expiresAt": session.expires_at.isoformat(),
    }


def _extract_session_token(
    authorization: str | None,
    x_customer_session: str | None,
) -> str | None:
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token.strip():
            return token.strip()

    if x_customer_session:
        token = x_customer_session.strip()
        if token:
            return token

    return None


def require_customer_session(
    authorization: str | None = Header(default=None),
    x_customer_session: str | None = Header(default=None, alias="X-Customer-Session"),
) -> CustomerSessionContext:
    token = _extract_session_token(authorization=authorization, x_customer_session=x_customer_session)
    if not token:
        raise HTTPException(status_code=401, detail="Customer session required")

    with _session_lock:
        session = _session_store.get(token)
        if not session:
            raise HTTPException(status_code=401, detail="Invalid customer session")

        if session.expires_at <= datetime.now(UTC):
            del _session_store[token]
            raise HTTPException(status_code=401, detail="Customer session expired")

    return session


@router.post("/session/login")
def customer_dashboard_login(payload: CustomerSessionLoginRequest):
    token = secrets.token_urlsafe(24)
    expires_at = datetime.now(UTC) + timedelta(hours=_SESSION_TTL_HOURS)

    session = CustomerSessionContext(
        token=token,
        email=payload.email.strip().lower(),
        tenant_id=payload.tenantId.strip(),
        expires_at=expires_at,
    )

    with _session_lock:
        _session_store[token] = session

    return {
        "ok": True,
        "source": "customer-session-store",
        "session": _session_payload(session),
    }


@router.post("/session/logout")
def customer_dashboard_logout(session: CustomerSessionContext = Depends(require_customer_session)):
    with _session_lock:
        _session_store.pop(session.token, None)

    return {
        "ok": True,
        "source": "customer-session-store",
    }


@router.get("/session/me")
def customer_dashboard_me(session: CustomerSessionContext = Depends(require_customer_session)):
    return {
        "ok": True,
        "source": "customer-session-store",
        "session": _session_payload(session),
    }


@router.get("/overview")
def get_customer_dashboard_overview(
    range: OverviewRange = Query(default="24h"),
    session: CustomerSessionContext = Depends(require_customer_session),
):
    payload = get_dashboard_overview(range)
    return {
        **payload,
        "source": "customer-placeholder",
        "scope": {
            "tenantId": session.tenant_id,
            "email": session.email,
        },
    }


@router.get("/metrics")
def get_customer_dashboard_metrics(
    range: MetricsRange = Query(default="24h"),
    session: CustomerSessionContext = Depends(require_customer_session),
):
    payload = get_dashboard_metrics(range)
    return {
        **payload,
        "source": "customer-placeholder",
        "scope": {
            "tenantId": session.tenant_id,
            "email": session.email,
        },
    }


@router.get("/activity")
def get_customer_dashboard_activity(
    status: ActivityStatus | None = Query(default=None),
    action: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    session: CustomerSessionContext = Depends(require_customer_session),
):
    payload = get_dashboard_activity(status=status, action=action, limit=limit)
    return {
        **payload,
        "source": "customer-placeholder",
        "scope": {
            "tenantId": session.tenant_id,
            "email": session.email,
        },
    }


@router.get("/keys")
def get_customer_dashboard_keys(session: CustomerSessionContext = Depends(require_customer_session)):
    payload = get_dashboard_keys()
    return {
        **payload,
        "source": "customer-mock-store",
        "scope": {
            "tenantId": session.tenant_id,
            "email": session.email,
        },
    }


@router.post("/keys/create")
def create_customer_dashboard_key(
    payload: CreateKeyRequest,
    session: CustomerSessionContext = Depends(require_customer_session),
):
    response = create_dashboard_key(payload)
    response["source"] = "customer-mock-store"
    response["scope"] = {
        "tenantId": session.tenant_id,
        "email": session.email,
    }
    return response


@router.post("/keys/{key_id}/rotate")
def rotate_customer_dashboard_key(
    key_id: str,
    session: CustomerSessionContext = Depends(require_customer_session),
):
    response = rotate_dashboard_key(key_id)
    response["source"] = "customer-mock-store"
    response["scope"] = {
        "tenantId": session.tenant_id,
        "email": session.email,
    }
    return response


@router.post("/keys/{key_id}/revoke")
def revoke_customer_dashboard_key(
    key_id: str,
    session: CustomerSessionContext = Depends(require_customer_session),
):
    response = revoke_dashboard_key(key_id)
    response["source"] = "customer-mock-store"
    response["scope"] = {
        "tenantId": session.tenant_id,
        "email": session.email,
    }
    return response


@router.post("/keys/{key_id}/activate")
def activate_customer_dashboard_key(
    key_id: str,
    session: CustomerSessionContext = Depends(require_customer_session),
):
    response = activate_dashboard_key(key_id)
    response["source"] = "customer-mock-store"
    response["scope"] = {
        "tenantId": session.tenant_id,
        "email": session.email,
    }
    return response
