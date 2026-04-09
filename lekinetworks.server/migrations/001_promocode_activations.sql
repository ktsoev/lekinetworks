CREATE TABLE IF NOT EXISTS promocode_activations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  telegram_id VARCHAR(32) NOT NULL,
  promocode_word VARCHAR(64) NOT NULL,
  activated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_telegram (telegram_id),
  INDEX idx_activated_at (activated_at),
  INDEX idx_promocode (promocode_word)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
