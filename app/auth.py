from datetime import UTC, datetime

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from .db import get_db, initialize_database, sync_configured_api_keys
from .models import APIKey, Subscription
from .security import hash_api_key

_ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing"}
_BOOTSTRAP_USER_EMAIL = "system@yfapi.local"


def _has_active_subscription(db: Session, user_id: int) -> bool:
    active_subscription = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user_id,
            Subscription.status.in_(_ACTIVE_SUBSCRIPTION_STATUSES),
        )
        .first()
    )
    return active_subscription is not None


def require_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> str:
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")

    key_hash = hash_api_key(x_api_key)
    try:
        api_key = (
            db.query(APIKey)
            .filter(APIKey.key_hash == key_hash, APIKey.status == "active")
            .first()
        )
    except OperationalError:
        initialize_database()
        sync_configured_api_keys()
        api_key = (
            db.query(APIKey)
            .filter(APIKey.key_hash == key_hash, APIKey.status == "active")
            .first()
        )

    if api_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    if api_key.user and api_key.user.email != _BOOTSTRAP_USER_EMAIL:
        if not _has_active_subscription(db, api_key.user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Subscription inactive")

    api_key.last_used_at = datetime.now(UTC)
    db.commit()

    request.state.authenticated_api_key_id = api_key.id

    return x_api_key
