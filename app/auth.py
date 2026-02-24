import hmac

from fastapi import Header, HTTPException, status
from .config import settings


def _allowed_keys() -> list[str]:
    keys = [settings.api_master_key]
    if settings.api_valid_keys.strip():
        keys.extend([k.strip() for k in settings.api_valid_keys.split(",") if k.strip()])
    # de-duplicate while preserving order
    out: list[str] = []
    seen: set[str] = set()
    for k in keys:
        if k not in seen:
            out.append(k)
            seen.add(k)
    return out


async def require_api_key(x_api_key: str | None = Header(default=None)) -> str:
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")

    # Constant-time compare against allowed keys.
    for key in _allowed_keys():
        if hmac.compare_digest(x_api_key, key):
            return x_api_key

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
