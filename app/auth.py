from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from .db import get_db, initialize_database, sync_configured_api_keys
from .models import APIKey
from .security import hash_api_key


def require_api_key(
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

    return x_api_key
