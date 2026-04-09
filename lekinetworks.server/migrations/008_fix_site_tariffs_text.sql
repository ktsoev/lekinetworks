-- Перезапись name/description в utf8mb4 (если 006 накатили с latin1/не тем SET NAMES).
-- Выполнить: mysql ... --default-character-set=utf8mb4 < migrations/008_fix_site_tariffs_text.sql

SET NAMES utf8mb4;
SET CHARACTER_SET_CLIENT = utf8mb4;
SET CHARACTER_SET_CONNECTION = utf8mb4;

UPDATE site_tariffs SET
  name = '⭐ 1 Месяц - 129₽',
  description = '🔒 Доступ к VPN на 30 дней'
WHERE plan_key = '1_month';

UPDATE site_tariffs SET
  name = '⭐ 3 Месяца - 349₽',
  description = '🔒 Доступ к VPN на 90 дней'
WHERE plan_key = '3_month';

UPDATE site_tariffs SET
  name = '⭐ 6 Месяцев - 649₽',
  description = '🔒 Доступ к VPN на 180 дней'
WHERE plan_key = '6_month';

UPDATE site_tariffs SET
  name = '🔥 Выгодно / 12 месяцев - 1199₽',
  description = '🔒 Доступ к VPN на 365 дней'
WHERE plan_key = '12_month';
