# vpn server
SERVER_PORT = 443

# Example: https://panel.example.com
PANEL_URL = "https://panel.example.com"

FLOW = "xtls-rprx-vision"

# database
DATABASE_IP = "192.168.0.5"
DATABASE_PORT = 3306
DATABASE_CHARSET = "utf8mb4"

USERS_TABLE = "users"
USERS_SITE_TABLE = "users_site"
SITE_EMAIL_OTP_TABLE = "site_email_otp"
SERVERS_TABLE = "servers"
PROMOCODES_TABLE = "promocodes"
PROMOCODE_ACTIVATIONS_TABLE = "promocode_activations"
PAYMENTS_TABLE = "payments"
PAYMENTS_SITE_TABLE = "payments_site"
SITE_TARIFFS_TABLE = "site_tariffs"
SITE_CHECKOUT_PENDING_TABLE = "site_checkout_pending"
SITE_PAYMENT_IDEMPOTENCY_TABLE = "site_payment_idempotency"


SITE_PANEL_TELEGRAM_ID_BASE = 8_000_000_000_000_000

# other
DATE_FORMAT = "%Y-%m-%d"

# expiry
HOUR_IN_SECONDS = 3600
VPN_EXPIRY_CHECK_DURATION = HOUR_IN_SECONDS * 6  # Every 6 hours check expiry vpn keys
