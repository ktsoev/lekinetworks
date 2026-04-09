import logging
from typing import Mapping

import httpx
from starlette.requests import Request
from starlette.responses import Response

from app import config

logger = logging.getLogger(__name__)

_HOP_BY_HOP = frozenset({
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "proxy-connection",
    "te",
    "trailer",
    "trailers",
    "transfer-encoding",
    "upgrade",
})

_WEBHOOK_INCOMING_HEADER_DROP = _HOP_BY_HOP | frozenset({
    "host",
    "content-length",
    "x-forwarded-for",
    "x-real-ip",
})
# Остальное (Content-Type, Crypto-Pay-API-Signature, Idempotency-Key, …) копируется как есть.

_RESPONSE_HEADER_DROP = _HOP_BY_HOP | frozenset({"content-length"})

_WEBHOOK_NAMES = frozenset({"yookassa", "cryptobot", "oxprocessing"})


def _filter_response_headers(src: Mapping[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in src.items():
        if k.lower() in _RESPONSE_HEADER_DROP:
            continue
        out[k] = v
    return out


def _xff_first_hop(value: str) -> str:
    if not value:
        return ""
    return value.split(",")[0].strip()


def _webhook_incoming_headers(request: Request) -> dict[str, str]:
    # XFF: при доверенном edge цепочка не затирается — бэкенд читает первый хоп для ЮKassa.
    # Нет XFF — одно звено с TCP-клиентом прокси (напрямую провайдер).
    hdrs: dict[str, str] = {}
    for k, v in request.headers.items():
        lk = k.lower()
        if lk in _WEBHOOK_INCOMING_HEADER_DROP:
            continue
        hdrs[k] = v
    xff_raw = (request.headers.get("x-forwarded-for") or "").strip()
    if xff_raw:
        hdrs["X-Forwarded-For"] = xff_raw
        first = _xff_first_hop(xff_raw)
        if first:
            hdrs["X-Real-IP"] = first
    elif request.client and request.client.host:
        hdrs["X-Forwarded-For"] = request.client.host
        hdrs["X-Real-IP"] = request.client.host
    return hdrs


def _headers_no_api_key(request: Request) -> dict[str, str]:
    hdrs: dict[str, str] = {}
    for k, v in request.headers.items():
        lk = k.lower()
        if lk in ("host", "content-length"):
            continue
        hdrs[k] = v
    return hdrs


async def forward_site(request: Request, subpath: str, body: bytes | None = None) -> Response:
    body_from_client = body is None
    if body is None:
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            body = await request.body()
        else:
            body = b""
    base = config.backend_base_url()
    url = f"{base}/site/{subpath}"
    if request.query_params:
        url = f"{url}?{request.query_params}"
    hdrs = _headers_no_api_key(request)
    if not body_from_client:
        hdrs["Content-Type"] = "application/json"
    hdrs["X-API-Key"] = config.server_api_key()
    req: dict = {"method": request.method, "url": url, "headers": hdrs}
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        req["content"] = body
    r = await request.app.state.http.request(**req)
    return Response(
        content=r.content,
        status_code=r.status_code,
        headers=_filter_response_headers(r.headers),
    )


async def forward_site_webhook(request: Request, name: str) -> Response:
    if name not in _WEBHOOK_NAMES:
        logger.error("webhook forward rejected unknown name=%r", name)
        return Response(status_code=404, content=b"Not Found")

    body = await request.body()
    base = config.backend_base_url()
    url = f"{base}/site/webhook/{name}"
    hdrs = _webhook_incoming_headers(request)
    timeout = config.webhook_http_timeout()
    try:
        r = await request.app.state.http.post(
            url,
            headers=hdrs,
            content=body,
            timeout=timeout,
        )
    except httpx.TimeoutException:
        logger.exception("webhook forward timeout name=%s url=%s", name, url)
        return Response(status_code=504, content=b"Gateway Timeout")
    except httpx.RequestError:
        logger.exception("webhook forward upstream error name=%s url=%s", name, url)
        return Response(status_code=502, content=b"Bad Gateway")

    return Response(
        content=r.content,
        status_code=r.status_code,
        headers=_filter_response_headers(r.headers),
    )
