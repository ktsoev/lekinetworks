import asyncio
import logging
import logging.handlers
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from remnawave import RemnawaveSDK

from lekivpn.core import config, db
from lekivpn.routers import site_api, telegram_api
from lekivpn.services import vpn_expiry

log = logging.getLogger(__name__)

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
    return app


app = create_app()
