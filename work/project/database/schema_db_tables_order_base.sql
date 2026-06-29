-- ============================================
-- Order Core Tables: orders + order_items
-- Task: db_tables_order_base
-- ============================================

SET FOREIGN_KEY_CHECKS = 0;

-- DROP child tables first (FK dependency order)
DROP TABLE IF EXISTS `order_items`;
DROP TABLE IF EXISTS `orders`;

-- CREATE parent tables first
CREATE TABLE IF NOT EXISTS `orders` (
  `id` INT AUTO_INCREMENT,
  `order_no` VARCHAR(32) NOT NULL COMMENT '雪花ID订单号',
  `user_id` INT NOT NULL,
  `shop_id` INT NOT NULL,
  `total_amount` DECIMAL(10,2) NOT NULL COMMENT '原价总金额',
  `discount_amount` DECIMAL(10,2) DEFAULT 0.00 COMMENT '优惠券抵扣金额',
  `pay_amount` DECIMAL(10,2) NOT NULL COMMENT '实付金额',
  `status` ENUM('pending_pay','paid','shipped','received','completed','cancelled','refunding') NOT NULL DEFAULT 'pending_pay' COMMENT '状态: pending_pay→paid→shipped→received→completed; pending_pay→cancelled(终态); paid→refunding→cancelled(终态)',
  `pay_method` VARCHAR(20) NULL COMMENT '支付渠道 wxpay/alipay',
  `pay_time` TIMESTAMP NULL,
  `ship_time` TIMESTAMP NULL,
  `receive_time` TIMESTAMP NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `uk_order_no` (`order_no`),
  INDEX `idx_user_status` (`user_id`, `status`),
  INDEX `idx_shop_status` (`shop_id`, `status`),
  INDEX `idx_created_at` (`created_at`),
  CONSTRAINT `fk_orders_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_orders_shop` FOREIGN KEY (`shop_id`) REFERENCES `shops`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='订单主表';

CREATE TABLE IF NOT EXISTS `order_items` (
  `id` INT AUTO_INCREMENT,
  `order_id` INT NOT NULL,
  `sku_id` INT NOT NULL,
  `sku_snapshot` JSON NOT NULL COMMENT '下单时SKU快照JSON(价格/规格/图片)，后续商品变更不影响历史订单',
  `quantity` INT NOT NULL,
  `unit_price` DECIMAL(10,2) NOT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_order_id` (`order_id`),
  CONSTRAINT `fk_order_items_order` FOREIGN KEY (`order_id`) REFERENCES `orders`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='订单商品快照表';

SET FOREIGN_KEY_CHECKS = 1;
