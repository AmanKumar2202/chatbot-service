import json

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestContextMiddleware:
    """Enforce body size and expose JSON user_id before endpoint rate limiting."""

    def __init__(self, app: ASGIApp, max_body_bytes: int):
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        declared_length = headers.get("content-length")
        if declared_length:
            try:
                if int(declared_length) > self.max_body_bytes:
                    await self._reject(send)
                    return
            except ValueError:
                await self._reject(send, status=400, detail="Invalid Content-Length")
                return

        messages: list[Message] = []
        body = bytearray()
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] == "http.disconnect":
                break
            body.extend(message.get("body", b""))
            if len(body) > self.max_body_bytes:
                await self._reject(send)
                return
            if not message.get("more_body", False):
                break

        state = scope.setdefault("state", {})
        state["rate_limit_user_id"] = self._user_id(bytes(body), scope, headers)
        message_index = 0

        async def replay() -> Message:
            nonlocal message_index
            if message_index < len(messages):
                message = messages[message_index]
                message_index += 1
                return message
            return await receive()

        await self.app(scope, replay, send)

    @staticmethod
    def _user_id(body: bytes, scope: Scope, headers: Headers) -> str:
        value = None
        try:
            if body:
                value = json.loads(body).get("user_id")
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            pass
        if not value:
            from urllib.parse import parse_qs

            query = parse_qs(scope.get("query_string", b"").decode(errors="ignore"))
            value = (query.get("user_id") or [None])[0]
        if not value:
            value = headers.get("X-User-Id", "anonymous")
        value = str(value).strip()
        return value[:128] if value else "anonymous"

    @staticmethod
    async def _reject(
        send: Send,
        status: int = 413,
        detail: str = "Request body too large",
    ) -> None:
        payload = json.dumps({"detail": detail}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(payload)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": payload})
