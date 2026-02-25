from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db import get_db, initialize_database
from app.models import DashboardSession, User
from app.security import hash_session_token, hash_password, verify_password

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


class CustomerRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class CustomerSessionLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


@dataclass
class CustomerSessionContext:
    token: str
    email: str
    tenant_id: str
    user_id: int
    expires_at: datetime


_SESSION_TTL_HOURS = 8


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


def _customer_tenant_id(user_id: int) -> str:
    return f"user-{user_id}"


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _revoke_expired_sessions(db: Session, *, user_id: int | None = None) -> None:
    now = datetime.now(UTC)
    query = db.query(DashboardSession).filter(
        DashboardSession.revoked_at.is_(None),
        DashboardSession.expires_at <= now,
    )
    if user_id is not None:
        query = query.filter(DashboardSession.user_id == user_id)

    for record in query.all():
        record.revoked_at = now



def _issue_session(db: Session, user: User) -> CustomerSessionContext:
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_session_token(raw_token)
    expires_at = datetime.now(UTC) + timedelta(hours=_SESSION_TTL_HOURS)

    _revoke_expired_sessions(db, user_id=user.id)

    session_record = DashboardSession(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )

    db.add(session_record)
    try:
        db.commit()
    except OperationalError:
        db.rollback()
        initialize_database()
        db.add(session_record)
        db.commit()

    return CustomerSessionContext(
        token=raw_token,
        email=user.email,
        tenant_id=_customer_tenant_id(user.id),
        user_id=user.id,
        expires_at=expires_at,
    )


def require_customer_session(
    authorization: str | None = Header(default=None),
    x_customer_session: str | None = Header(default=None, alias="X-Customer-Session"),
    db: Session = Depends(get_db),
) -> CustomerSessionContext:
    token = _extract_session_token(authorization=authorization, x_customer_session=x_customer_session)
    if not token:
        raise HTTPException(status_code=401, detail="Customer session required")

    token_hash = hash_session_token(token)
    try:
        lookup = (
            db.query(DashboardSession, User)
            .join(User, User.id == DashboardSession.user_id)
            .filter(
                DashboardSession.token_hash == token_hash,
                DashboardSession.revoked_at.is_(None),
            )
            .first()
        )
    except OperationalError:
        initialize_database()
        lookup = None

    if not lookup:
        raise HTTPException(status_code=401, detail="Invalid customer session")

    session, user = lookup
    expires_at = _normalize_utc(session.expires_at)
    if expires_at <= datetime.now(UTC):
        session.revoked_at = datetime.now(UTC)
        db.commit()
        raise HTTPException(status_code=401, detail="Customer session expired")

    return CustomerSessionContext(
        token=token,
        email=user.email,
        tenant_id=_customer_tenant_id(user.id),
        user_id=user.id,
        expires_at=expires_at,
    )


def get_customer_session_optional(
    authorization: str | None = Header(default=None),
    x_customer_session: str | None = Header(default=None, alias="X-Customer-Session"),
    db: Session = Depends(get_db),
) -> CustomerSessionContext | None:
    token = _extract_session_token(authorization=authorization, x_customer_session=x_customer_session)
    if not token:
        return None

    try:
        return require_customer_session(
            authorization=authorization,
            x_customer_session=x_customer_session,
            db=db,
        )
    except HTTPException:
        return None


@router.post("/auth/register")
def customer_register(payload: CustomerRegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    session = _issue_session(db, user)
    return {
        "ok": True,
        "source": "customer-db-session",
        "session": _session_payload(session),
    }


@router.post("/session/login")
def customer_dashboard_login(payload: CustomerSessionLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    session = _issue_session(db, user)
    return {
        "ok": True,
        "source": "customer-db-session",
        "session": _session_payload(session),
    }


@router.post("/session/logout")
def customer_dashboard_logout(
    session: CustomerSessionContext = Depends(require_customer_session),
    db: Session = Depends(get_db),
):
    token_hash = hash_session_token(session.token)
    record = db.query(DashboardSession).filter(DashboardSession.token_hash == token_hash).first()
    if record and record.revoked_at is None:
        record.revoked_at = datetime.now(UTC)
        db.commit()

    return {
        "ok": True,
        "source": "customer-db-session",
    }


@router.get("/session/me")
def customer_dashboard_me(session: CustomerSessionContext = Depends(require_customer_session)):
    return {
        "ok": True,
        "source": "customer-db-session",
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
    payload = get_dashboard_activity(
        tenant_id=session.tenant_id,
        actor_email=session.email,
        status=status,
        action=action,
        limit=limit,
    )
    return {
        **payload,
        "source": "customer-placeholder",
        "scope": {
            "tenantId": session.tenant_id,
            "email": session.email,
        },
    }


@router.get("/keys")
def get_customer_dashboard_keys(
    session: CustomerSessionContext = Depends(require_customer_session),
    db: Session = Depends(get_db),
):
    payload = get_dashboard_keys(db, session.user_id)
    return {
        **payload,
        "source": "customer-db-store",
        "scope": {
            "tenantId": session.tenant_id,
            "email": session.email,
        },
    }


@router.post("/keys/create")
def create_customer_dashboard_key(
    payload: CreateKeyRequest,
    session: CustomerSessionContext = Depends(require_customer_session),
    db: Session = Depends(get_db),
):
    response = create_dashboard_key(db, session.user_id, payload)
    response["source"] = "customer-db-store"
    response["scope"] = {
        "tenantId": session.tenant_id,
        "email": session.email,
    }
    return response


@router.post("/keys/{key_id}/rotate")
def rotate_customer_dashboard_key(
    key_id: str,
    session: CustomerSessionContext = Depends(require_customer_session),
    db: Session = Depends(get_db),
):
    response = rotate_dashboard_key(db, session.user_id, key_id)
    response["source"] = "customer-db-store"
    response["scope"] = {
        "tenantId": session.tenant_id,
        "email": session.email,
    }
    return response


@router.post("/keys/{key_id}/revoke")
def revoke_customer_dashboard_key(
    key_id: str,
    session: CustomerSessionContext = Depends(require_customer_session),
    db: Session = Depends(get_db),
):
    response = revoke_dashboard_key(db, session.user_id, key_id)
    response["source"] = "customer-db-store"
    response["scope"] = {
        "tenantId": session.tenant_id,
        "email": session.email,
    }
    return response


@router.post("/keys/{key_id}/activate")
def activate_customer_dashboard_key(
    key_id: str,
    session: CustomerSessionContext = Depends(require_customer_session),
    db: Session = Depends(get_db),
):
    response = activate_dashboard_key(db, session.user_id, key_id)
    response["source"] = "customer-db-store"
    response["scope"] = {
        "tenantId": session.tenant_id,
        "email": session.email,
    }
    return response
