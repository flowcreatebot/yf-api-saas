from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import settings


def rate_limit_key(request: Request) -> str:
    api_key = request.headers.get("x-api-key")
    if api_key:
        return f"api-key:{api_key}"
    return f"ip:{get_remote_address(request)}"


def default_market_rate_limit() -> str:
    return settings.default_rate_limit


limiter = Limiter(key_func=rate_limit_key, default_limits=[])
