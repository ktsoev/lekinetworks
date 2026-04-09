ALTER TABLE site_checkout_pending
  ADD COLUMN extend_subscription TINYINT(1) NOT NULL DEFAULT 0
    COMMENT '1 = продлить device_id, 0 = новая подписка (новый device)'
    AFTER plan_key,
  ADD COLUMN extend_device_id INT NULL
    COMMENT 'Номер устройства в панели при extend_subscription=1'
    AFTER extend_subscription;
