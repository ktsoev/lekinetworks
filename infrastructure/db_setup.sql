-- LEKI Networks — Database setup
-- Run once on MySQL 8+

CREATE DATABASE IF NOT EXISTS leki_vpn_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'leki_vpn_user'@'localhost' IDENTIFIED BY 'REPLACE_WITH_STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON leki_vpn_db.* TO 'leki_vpn_user'@'localhost';
FLUSH PRIVILEGES;

-- After this, run migrations in order:
-- mysql -u leki_vpn_user -p leki_vpn_db < lekinetworks.server/migrations/001_promocode_activations.sql
-- mysql -u leki_vpn_user -p leki_vpn_db < lekinetworks.server/migrations/002_users_utf8mb4_telegram_name.sql
-- mysql -u leki_vpn_user -p leki_vpn_db < lekinetworks.server/migrations/003_payments.sql
-- mysql -u leki_vpn_user -p leki_vpn_db < lekinetworks.server/migrations/004_users_site.sql
-- mysql -u leki_vpn_user -p leki_vpn_db < lekinetworks.server/migrations/005_payments_site.sql
-- mysql -u leki_vpn_user -p leki_vpn_db < lekinetworks.server/migrations/006_site_tariffs.sql
-- mysql -u leki_vpn_user -p leki_vpn_db < lekinetworks.server/migrations/007_site_payment_checkout.sql
-- mysql -u leki_vpn_user -p leki_vpn_db < lekinetworks.server/migrations/008_fix_site_tariffs_text.sql
-- mysql -u leki_vpn_user -p leki_vpn_db < lekinetworks.server/migrations/009_site_checkout_extend.sql
