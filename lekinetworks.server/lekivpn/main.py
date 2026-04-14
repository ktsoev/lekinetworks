import asyncio
import logging
import logging.handlers
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from remnawave import RemnawaveSDK
from starlette.middleware.base import BaseHTTPMiddleware

from lekivpn.core import config, db
from lekivpn.routers import site_api, telegram_api
from lekivpn.services import vpn_expiry

log = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            log.exception(
                "UNHANDLED %s %s — %.0fms",
                request.method, request.url.path, elapsed,
            )
            return JSONResponse(status_code=500, content={"detail": "Internal server error"})

        elapsed = (time.monotonic() - start) * 1000
        status = response.status_code
        if status >= 500:
            log.error(
                "%d %s %s — %.0fms",
                status, request.method, request.url.path, elapsed,
            )
        elif status >= 400:
            log.warning(
                "%d %s %s — %.0fms",
                status, request.method, request.url.path, elapsed,
            )
        else:
            log.info(
                "%d %s %s — %.0fms",
                status, request.method, request.url.path, elapsed,
            )
        return response

_project_root = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        env_path = _project_root / ".env"
        load_dotenv(dotenv_path=env_path)

        remnawave_token = os.getenv("PANEL_TOKEN")
        panel_url = (os.getenv("PANEL_URL") or "").strip() or config.PANEL_URL

        api = RemnawaveSDK(base_url=panel_url, token=remnawave_token)
        print("✅ Remnawave ready!")

        telegram_api.init(api)
        print("✅ API ready!")

        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_name = os.getenv("DB_NAME")

        await db.init_pool(db_user, db_password, db_name)
        print("✅ Database ready!")

        asyncio.create_task(vpn_expiry.start_vpn_cleaner())
        print("✅ Cleaner ready!")

        yield
    except Exception as e:
        log.exception("Initialize error: %s", e)
    finally:
        await db.close_pool()
        print("✅ Database closed")


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)
    app.include_router(telegram_api.router)
    app.include_router(site_api.router, prefix="/site")

    _cors = [o.strip() for o in os.getenv("SITE_CORS_ORIGINS", "").split(",") if o.strip()]
    if _cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=_cors,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.add_middleware(RequestLoggingMiddleware)
    return app


app = create_app()
