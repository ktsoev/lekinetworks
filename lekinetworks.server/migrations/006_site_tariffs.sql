CREATE TABLE IF NOT EXISTS site_tariffs (
  plan_key VARCHAR(32) NOT NULL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description VARCHAR(512) NOT NULL,
  amount INT NOT NULL COMMENT 'рубли',
  amount_usdt DECIMAL(14, 6) NOT NULL COMMENT 'USDT по курсу миграции',
  duration_days INT NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_active_sort (is_active, sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Клиент mysql должен отдавать строки в utf8mb4 (иначе кракозябры в name/description)
SET NAMES utf8mb4;
SET CHARACTER_SET_CLIENT = utf8mb4;
SET CHARACTER_SET_CONNECTION = utf8mb4;

-- курс: 1 USDT = 80.30 RUB (при смене курса — UPDATE amount_usdt)
INSERT INTO site_tariffs (plan_key, name, description, amount, amount_usdt, duration_days, sort_order) VALUES
('1_month', '⭐ 1 Месяц - 129₽', '🔒 Доступ к VPN на 30 дней', 129, ROUND(129 / 80.30, 6), 30, 10),
('3_month', '⭐ 3 Месяца - 349₽', '🔒 Доступ к VPN на 90 дней', 349, ROUND(349 / 80.30, 6), 90, 20),
('6_month', '⭐ 6 Месяцев - 649₽', '🔒 Доступ к VPN на 180 дней', 649, ROUND(649 / 80.30, 6), 180, 30),
('12_month', '🔥 Выгодно / 12 месяцев - 1199₽', '🔒 Доступ к VPN на 365 дней', 1199, ROUND(1199 / 80.30, 6), 365, 40);
