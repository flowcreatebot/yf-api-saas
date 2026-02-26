from __future__ import annotations

import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, EmailStr, HttpUrl, field_validator
from sqlalchemy.orm import Session
import stripe

from ..config import settings
from ..db import get_db
from ..models import APIKey, Subscription, User
from ..security import hash_api_key
from .customer_dashboard import CustomerSessionContext, get_customer_session_optional

router = APIRouter(prefix="/v1/billing", tags=["billing"])

_ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing"}


class CheckoutSessionRequest(BaseModel):
    email: EmailStr
    success_url: HttpUrl
    cancel_url: HttpUrl

    @staticmethod
    def _allowed_redirect_hosts() -> set[str]:
        return {
            host.strip().lower()
            for host in settings.billing_allowed_redirect_hosts.split(",")
            if host.strip()
        }

    @field_validator("success_url", "cancel_url")
    @classmethod
    def validate_redirect_url(cls, v: HttpUrl) -> HttpUrl:
        host = (v.host or "").lower()
        if not (v.scheme == "https" or host in {"localhost", "127.0.0.1"}):
            raise ValueError("Redirect URLs must use https (localhost allowed for development)")

        allowed_hosts = cls._allowed_redirect_hosts()
        if allowed_hosts and host not in allowed_hosts:
            raise ValueError(f"Redirect URL host '{host}' is not in BILLING_ALLOWED_REDIRECT_HOSTS")

        return v


def _utc_from_epoch(value: object) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=UTC)
    except (TypeError, ValueError, OSError):
        return None


def _starter_plan_payload() -> dict:
    return {
        "id": settings.billing_starter_plan_id,
        "name": settings.billing_starter_plan_name,
        "price_usd": settings.billing_starter_plan_price_usd,
        "interval": settings.billing_starter_plan_interval,
        "description": settings.billing_starter_plan_description,
    }


def _find_user_for_checkout_completed(checkout_session: dict, db: Session) -> User | None:
    metadata = checkout_session.get("metadata") or {}
    user_id_raw = metadata.get("user_id")

    user: User | None = None
    if user_id_raw:
        try:
            user = db.query(User).filter(User.id == int(user_id_raw)).first()
        except (TypeError, ValueError):
            user = None

    customer_id = checkout_session.get("customer")
    if user is None and customer_id:
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()

    customer_email = checkout_session.get("customer_email")
    if user is None and customer_email:
        user = db.query(User).filter(User.email == str(customer_email).lower()).first()

    return user


def _provision_first_api_key(user: User, db: Session) -> bool:
    existing_active_key = (
        db.query(APIKey)
        .filter(APIKey.user_id == user.id, APIKey.status == "active")
        .first()
    )
    if existing_active_key is not None:
        return False

    raw_key = f"yf_live_{secrets.token_urlsafe(24)}"
    db.add(
        APIKey(
            key_hash=hash_api_key(raw_key),
            user_id=user.id,
            name="Primary live key",
            status="active",
        )
    )
    return True


def _upsert_subscription_for_user(
    *,
    user: User,
    stripe_subscription_id: str | None,
    status: str,
    current_period_end: datetime | None,
    db: Session,
) -> Subscription:
    subscription: Subscription | None = None

    if stripe_subscription_id:
        subscription = (
            db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == stripe_subscription_id)
            .first()
        )

    if subscription is None:
        subscription = (
            db.query(Subscription)
            .filter(Subscription.user_id == user.id)
            .order_by(Subscription.id.desc())
            .first()
        )

    if subscription is None:
        subscription = Subscription(
            user_id=user.id,
            stripe_subscription_id=stripe_subscription_id,
            status=status,
            plan=settings.billing_starter_plan_id,
            current_period_end=current_period_end,
        )
        db.add(subscription)
    else:
        if stripe_subscription_id:
            subscription.stripe_subscription_id = stripe_subscription_id
        subscription.status = status
        subscription.plan = settings.billing_starter_plan_id
        subscription.current_period_end = current_period_end

    return subscription


def _mark_customer_subscription_event(
    subscription_payload: dict,
    db: Session,
    *,
    provision_key_on_active_status: bool = False,
) -> tuple[bool, bool]:
    stripe_subscription_id = subscription_payload.get("id")
    if not stripe_subscription_id:
        return False, False

    subscription = (
        db.query(Subscription)
        .filter(Subscription.stripe_subscription_id == stripe_subscription_id)
        .first()
    )

    status = str(subscription_payload.get("status") or "incomplete")

    if subscription is None:
        customer_id = subscription_payload.get("customer")
        if not customer_id:
            return False, False

        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user is None:
            return False, False

        subscription = Subscription(
            user_id=user.id,
            stripe_subscription_id=stripe_subscription_id,
            status=status,
            plan=settings.billing_starter_plan_id,
            current_period_end=_utc_from_epoch(subscription_payload.get("current_period_end")),
        )
        db.add(subscription)
    else:
        subscription.status = status
        subscription.current_period_end = _utc_from_epoch(subscription_payload.get("current_period_end"))
        if not subscription.plan:
            subscription.plan = settings.billing_starter_plan_id

    provisioned_key = False
    if provision_key_on_active_status and status in _ACTIVE_SUBSCRIPTION_STATUSES:
        user = db.query(User).filter(User.id == subscription.user_id).first()
        if user is not None:
            provisioned_key = _provision_first_api_key(user, db)

    return True, provisioned_key


@router.get("/plans")
def plans():
    return {"plans": [_starter_plan_payload()]}


@router.post("/checkout/session")
def create_checkout_session(
    payload: CheckoutSessionRequest,
    db: Session = Depends(get_db),
    customer_session: CustomerSessionContext | None = Depends(get_customer_session_optional),
):
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe secret key not configured")
    if not settings.stripe_price_id_monthly:
        raise HTTPException(status_code=503, detail="Stripe monthly price id not configured")

    stripe.api_key = settings.stripe_secret_key

    checkout_kwargs = {
        "mode": "subscription",
        "line_items": [{"price": settings.stripe_price_id_monthly, "quantity": 1}],
        "success_url": str(payload.success_url),
        "cancel_url": str(payload.cancel_url),
        "allow_promotion_codes": True,
    }

    if customer_session is not None:
        user = db.query(User).filter(User.id == customer_session.user_id).first()
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid customer session")

        if user.email != payload.email.lower():
            raise HTTPException(status_code=403, detail="Checkout email must match authenticated account")

        if not user.stripe_customer_id:
            try:
                customer = stripe.Customer.create(
                    email=user.email,
                    metadata={"user_id": str(user.id), "email": user.email},
                )
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"Stripe customer creation failed: {exc}")

            customer_id = customer.get("id")
            if not customer_id:
                raise HTTPException(status_code=502, detail="Stripe customer creation did not return an id")

            user.stripe_customer_id = str(customer_id)
            db.commit()

        checkout_kwargs["customer"] = user.stripe_customer_id
        checkout_kwargs["client_reference_id"] = str(user.id)
        checkout_kwargs["metadata"] = {
            "user_id": str(user.id),
            "email": user.email,
            "plan_id": settings.billing_starter_plan_id,
        }
    else:
        checkout_kwargs["customer_email"] = payload.email.lower()

    try:
        session = stripe.checkout.Session.create(**checkout_kwargs)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Stripe checkout session failed: {exc}")

    return {
        "id": session.get("id"),
        "url": session.get("url"),
        "status": session.get("status"),
    }


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request, stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"), db: Session = Depends(get_db)):
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhook secret not configured")
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(payload=payload, sig_header=stripe_signature, secret=settings.stripe_webhook_secret)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid webhook: {exc}")

    event_type = event.get("type", "")
    event_object = (event.get("data") or {}).get("object") or {}

    handled = False
    provisioned_key = False

    if event_type == "checkout.session.completed":
        user = _find_user_for_checkout_completed(event_object, db)
        stripe_subscription_id = event_object.get("subscription")
        status = "active" if event_object.get("payment_status") == "paid" else "incomplete"

        if user is not None:
            customer_id = event_object.get("customer")
            if customer_id and user.stripe_customer_id != customer_id:
                user.stripe_customer_id = str(customer_id)

            _upsert_subscription_for_user(
                user=user,
                stripe_subscription_id=str(stripe_subscription_id) if stripe_subscription_id else None,
                status=status,
                current_period_end=None,
                db=db,
            )
            if status in _ACTIVE_SUBSCRIPTION_STATUSES:
                provisioned_key = _provision_first_api_key(user, db)
            handled = True

    elif event_type in {"customer.subscription.updated", "customer.subscription.deleted"}:
        handled, provisioned_key = _mark_customer_subscription_event(
            event_object,
            db,
            provision_key_on_active_status=event_type == "customer.subscription.updated",
        )

    db.commit()

    return {
        "received": True,
        "type": event_type,
        "handled": handled,
        "provisioned_key": provisioned_key,
    }
