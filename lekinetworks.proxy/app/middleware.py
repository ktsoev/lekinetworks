from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response


class MaxRequestBodySizeMiddleware(BaseHTTPMiddleware):
    """Отклоняет запросы с Content-Length больше лимита (до чтения тела)."""

    def __init__(self, app, max_bytes: int):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            raw = request.headers.get("content-length")
            if raw is not None:
                try:
                    if int(raw) > self.max_bytes:
                        return PlainTextResponse("Payload Too Large", status_code=413)
                except ValueError:
                    pass
        return await call_next(request)
