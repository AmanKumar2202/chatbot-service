import hmac

from fastapi import Header, HTTPException, status

from app.core.config import settings


def require_service_key(
    x_service_key: str = Header(default="", alias="X-Service-Key"),
) -> None:
    if not hmac.compare_digest(x_service_key, settings.service_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing service key",
        )
