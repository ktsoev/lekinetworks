# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Development Commands

### lekinetworks.react (Vite + React 19 + TypeScript)

```bash
cd lekinetworks.react
npm install
npm run dev       # Dev server
npm run build     # tsc -b && vite build → dist/
npm run lint      # ESLint
npm run preview   # Preview production build
```

### lekinetworks.server (FastAPI backend)

```bash
cd lekinetworks.server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in secrets
python start.py        # runs uvicorn on 127.0.0.1:8000
```

### lekinetworks.proxy (FastAPI security gateway)

```bash
cd lekinetworks.proxy
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

### lekinetworks.bot (Aiogram Telegram bot)

```bash
cd lekinetworks.bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in BOT_TOKEN, YOOKASSA_TOKEN, SERVER_API_KEY
python start.py        # long-polling, no port
```

### Database setup & migrations

```bash
# One-time setup:
mysql -u root -p < infrastructure/db_setup.sql

# Migrations (run in order):
mysql -u leki_vpn_user -p leki_vpn_db < lekinetworks.server/migrations/001_promocode_activations.sql
# ... through 009_site_checkout_extend.sql
```

---

## Architecture

Full system diagram and data flow are in the parent directory's `CLAUDE.md` (`../CLAUDE.md`). Key layout of this repo:

```
lekinetworks.server/   FastAPI backend (127.0.0.1:8000)
lekinetworks.proxy/    FastAPI security gateway (127.0.0.1:8001)
lekinetworks.bot/      Aiogram Telegram bot (long-polling)
lekinetworks.react/    React 19 SPA (Vite)
infrastructure/        systemd units, nginx config, db_setup.sql
```

### Backend (`lekinetworks.server`)

Package is `lekivpn/`. Entry point is `start.py` which configures logging then imports `lekivpn.main.app`.

- `lekivpn/main.py` — app factory; lifespan connects DB pool, initializes RemnawaveSDK, starts VPN expiry background task
- `lekivpn/routers/telegram_api.py` — bot-only endpoints (no `/site` prefix); protected by `X-API-Key` only
- `lekivpn/routers/site_api.py` — all `/site/*` endpoints; protected by `X-API-Key` + JWT (`Authorization: Bearer`)
- `lekivpn/routers/deps.py` — `require_api_key` dependency reads `SERVER_API_KEY` from env
- `lekivpn/services/` — one file per concern: `vpn.py`, `site_server.py`, `site_checkout.py`, `site_payment_fulfill.py`, `site_payment_providers.py`, `site_email_otp.py`, `site_jwt.py`, `site_tariffs_database.py`, `user_site_database.py`, `user_database.py`, `servers_database.py`, `vpn_expiry.py`
- `lekivpn/core/db.py` — aiomysql connection pool (`init_pool` / `close_pool`)
- `lekivpn/core/config.py` — static constants (table names, panel URL default, expiry interval)
- `lekivpn/schemas/` — Pydantic models split into `telegram.py` and `site.py`
- `migrations/` — numbered SQL files applied manually in sequence

Webhook handlers for all three payment providers live in `site_api.py` under `/site/webhook/{provider}`.

### Proxy (`lekinetworks.proxy`)

Thin FastAPI app that is the only internet-facing Python process. Every route is explicit (whitelist model). `app/forward.py` injects `X-API-Key` and proxies the request to the backend. `app/webhooks.py` handles webhook forwarding with provider-specific timeouts. Rate limits, CORS origins, and body size are all configurable via `.env`.

### Bot (`lekinetworks.bot`)

Flat layout (no package). `start.py` wires all Aiogram handlers. Commands live in `Commands/`. `network_helper.py` wraps HTTP calls to the backend. `payment_handler.py` handles Yookassa invoice creation and the `successful_payment` event. The bot communicates directly with the backend at `127.0.0.1:8000`, bypassing nginx and the proxy entirely.

### Frontend (`lekinetworks.react`)

React 19 SPA. Key patterns:

- `src/api/` — API layer using `wretch`; swap implementations here without touching components
- `src/context/` — React Context + useReducer for auth and subscription state
- `src/hooks/` — custom hooks consuming context and React Query
- `src/pages/` — one file (+ CSS Module) per route
- `src/i18n/` — i18next localization
- Route layout: `/` landing → `/auth/login` → `/auth/verify` → `/dashboard/*`
- Protected routes redirect to `/auth/login` when unauthenticated
- Design: dark theme (`#0A0A0F` base), CSS Modules, mobile-first

---

## Key Patterns & Non-Obvious Details

- **`SITE_PANEL_TELEGRAM_ID_BASE`** (default `8_000_000_000_000_000`): site users are mapped to synthetic Telegram IDs in Remnawave as `BASE + users_site.id`. **Never change this after users exist in the panel.**
- **Payment idempotency**: all three webhook handlers check `site_payment_idempotency` before fulfilling to prevent double-processing.
- **Checkout pending table**: `site_checkout_pending` stores `extend_subscription` + `extend_device_id` so webhooks can reconstruct intent even if metadata is absent.
- **OTP**: 6-digit code, SHA256+pepper stored, max 5 attempts, 15-min TTL, timing-safe comparison.
- **JWT**: HS256, default 7-day expiry, `site_user_id` as subject.
- **VPN expiry cleaner**: `vpn_expiry.py` runs as a background `asyncio.Task` every 6 hours, checking and disabling expired VPN users in Remnawave.
- **Yookassa IP check**: skipped when `YOOKASSA_SKIP_IP_CHECK=true` (needed behind a reverse proxy without trusted IP passthrough).
- **0xProcessing checkout** (`create_oxprocessing_checkout`) is synchronous — no `await`.
- The proxy's `app/webhooks.py` uses a longer read timeout (`WEBHOOK_FORWARD_TIMEOUT_READ`, default 120 s) because fulfillment (Remnawave API call) can be slow.
