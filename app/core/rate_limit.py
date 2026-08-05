import hashlib

from limits import parse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.metrics import RATE_LIMIT_REJECTIONS


def _service_hash(service_key: str) -> str:
    return hashlib.sha256(service_key.encode()).hexdigest()


def service_and_user_key(request):
    service_key = request.headers.get("X-Service-Key")
    if service_key:
        user_id = getattr(request.state, "rate_limit_user_id", "anonymous")
        return f"service:{_service_hash(service_key)}:user:{user_id}"
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=service_and_user_key,
    storage_uri=settings.rate_limit_storage_uri,
)


def websocket_key(service_key: str, user_id: str) -> str:
    normalized_user = user_id.strip()[:128] or "anonymous"
    return f"service:{_service_hash(service_key)}:user:{normalized_user}"


def allow_websocket(key: str, limit_value: str) -> bool:
    allowed = limiter._limiter.hit(parse(limit_value), key)
    if not allowed:
        RATE_LIMIT_REJECTIONS.labels("websocket").inc()
    return allowed
