from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app import config
from app.forward import forward_site
from app.middleware import MaxRequestBodySizeMiddleware
from app.schemas import SiteCheckoutBody
from app.webhooks import router as webhook_router


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_client_ip)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=120.0)
    yield
    await app.state.http.aclose()


app = FastAPI(
    title="leki site proxy",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_origins = config.cors_origins()
if _origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        max_age=3600,
    )

app.add_middleware(MaxRequestBodySizeMiddleware, max_bytes=config.max_request_body_bytes())

app.include_router(webhook_router, prefix="/site/webhook")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/site/auth/request-code")
@limiter.limit(config.request_code_rate_limit())
async def site_auth_request_code(request: Request):
    return await forward_site(request, "auth/request-code")


@app.post("/site/auth/verify-code")
@limiter.limit(config.verify_code_rate_limit())
async def site_auth_verify_code(request: Request):
    return await forward_site(request, "auth/verify-code")


@app.get("/site/auth/me")
@limiter.limit(config.site_read_rate_limit())
async def site_auth_me(request: Request):
    return await forward_site(request, "auth/me")


@app.get("/site/plans")
@limiter.limit(config.site_read_rate_limit())
async def site_plans(request: Request):
    return await forward_site(request, "plans")


@app.post("/site/subscription/overview")
@limiter.limit(config.subscription_overview_rate_limit())
async def site_subscription_overview(request: Request):
    return await forward_site(request, "subscription/overview")


@app.post("/site/payment/checkout/yookassa")
@limiter.limit(config.checkout_rate_limit())
async def site_checkout_yookassa(request: Request, checkout: SiteCheckoutBody):
    payload = checkout.model_dump_json(exclude_none=True).encode()
    return await forward_site(request, "payment/checkout/yookassa", body=payload)


@app.post("/site/payment/checkout/cryptobot")
@limiter.limit(config.checkout_rate_limit())
async def site_checkout_cryptobot(request: Request, checkout: SiteCheckoutBody):
    payload = checkout.model_dump_json(exclude_none=True).encode()
    return await forward_site(request, "payment/checkout/cryptobot", body=payload)


@app.post("/site/payment/checkout/oxprocessing")
@limiter.limit(config.checkout_rate_limit())
async def site_checkout_oxprocessing(request: Request, checkout: SiteCheckoutBody):
    payload = checkout.model_dump_json(exclude_none=True).encode()
    return await forward_site(request, "payment/checkout/oxprocessing", body=payload)


@app.post("/site/vpn/get-key")
@limiter.limit(config.site_write_rate_limit())
async def site_vpn_get_key(request: Request):
    return await forward_site(request, "vpn/get-key")


@app.post("/site/promocode/activate")
@limiter.limit(config.site_write_rate_limit())
async def site_promocode_activate(request: Request):
    return await forward_site(request, "promocode/activate")
