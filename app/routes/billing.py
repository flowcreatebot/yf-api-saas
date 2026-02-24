from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, EmailStr, HttpUrl, field_validator
import stripe

from ..config import settings

router = APIRouter(prefix="/v1/billing", tags=["billing"])


class CheckoutSessionRequest(BaseModel):
    email: EmailStr
    success_url: HttpUrl
    cancel_url: HttpUrl

    @field_validator("success_url", "cancel_url")
    @classmethod
    def validate_redirect_url(cls, v: HttpUrl) -> HttpUrl:
        host = (v.host or "").lower()
        if v.scheme == "https" or host in {"localhost", "127.0.0.1"}:
            return v
        raise ValueError("Redirect URLs must use https (localhost allowed for development)")


@router.get("/plans")
def plans():
    return {
        "plans": [
            {
                "id": "starter-monthly",
                "name": "Starter",
                "price_usd": 4.99,
                "interval": "month",
                "description": "Yahoo Finance API access for no-code workflows",
            }
        ]
    }


@router.post("/checkout/session")
def create_checkout_session(payload: CheckoutSessionRequest):
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe secret key not configured")
    if not settings.stripe_price_id_monthly:
        raise HTTPException(status_code=503, detail="Stripe monthly price id not configured")

    stripe.api_key = settings.stripe_secret_key

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer_email=payload.email,
            line_items=[{"price": settings.stripe_price_id_monthly, "quantity": 1}],
            success_url=str(payload.success_url),
            cancel_url=str(payload.cancel_url),
            allow_promotion_codes=True,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Stripe checkout session failed: {exc}")

    return {
        "id": session.get("id"),
        "url": session.get("url"),
        "status": session.get("status"),
    }


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request, stripe_signature: str | None = Header(default=None, alias="Stripe-Signature")):
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
    supported_prefixes = ("customer.subscription.", "invoice.payment_")
    handled = event_type.startswith(supported_prefixes)

    return {"received": True, "type": event_type, "handled": handled}
