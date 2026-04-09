CREATE TABLE IF NOT EXISTS payments_site (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  site_user_id BIGINT UNSIGNED NOT NULL,
  amount INT NOT NULL,
  currency VARCHAR(8) NOT NULL,
  product_id VARCHAR(64) NOT NULL,
  device_id INT NOT NULL,
  payment_type VARCHAR(32) NOT NULL,
  external_id VARCHAR(128) DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_site_user (site_user_id),
  INDEX idx_created_at (created_at),
  UNIQUE KEY uq_payments_site_external (external_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
