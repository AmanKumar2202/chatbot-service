from uvicorn.workers import UvicornWorker

from app.core.config import settings


class BoundedUvicornWorker(UvicornWorker):
    CONFIG_KWARGS = {
        **UvicornWorker.CONFIG_KWARGS,
        "limit_concurrency": settings.server_limit_concurrency,
        "timeout_keep_alive": 5,
        "ws_ping_interval": 20.0,
        "ws_ping_timeout": 20.0,
    }
