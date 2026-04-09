CREATE TABLE IF NOT EXISTS payments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  telegram_id VARCHAR(32) NOT NULL,
  amount_kopecks INT NOT NULL,
  currency VARCHAR(8) NOT NULL,
  product_id VARCHAR(32) NOT NULL,
  device_id INT NOT NULL,
  payment_type VARCHAR(16) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_telegram (telegram_id),
  INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
