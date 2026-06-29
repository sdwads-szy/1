-- ============================================================
-- Task: db_tables_payment
-- Description: 支付流水表
-- Version: 1.0.0
-- Compatibility: backward
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

-- ------------------------------------------------------------
-- Table: payments (支付流水)
-- 状态流转: pending → paid → refunding → refunded
--           pending → closed (终态，超时取消)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `payments` (
  `id` INT AUTO_INCREMENT COMMENT '主键ID',
  `order_id` INT NOT NULL COMMENT '订单ID，关联orders表',
  `user_id` INT NOT NULL COMMENT '用户ID',
  `amount` DECIMAL(10,2) NOT NULL COMMENT '支付金额',
  `channel` ENUM('wxpay','alipay') NOT NULL COMMENT '支付渠道: wxpay=微信支付, alipay=支付宝',
  `trade_no` VARCHAR(64) DEFAULT '' COMMENT '第三方交易流水号',
  `status` ENUM('pending','paid','refunding','refunded','closed') NOT NULL DEFAULT 'pending' COMMENT '状态: pending=待支付, paid=已支付, refunding=退款中, refunded=已退款, closed=已关闭(终态)',
  `paid_at` TIMESTAMP NULL DEFAULT NULL COMMENT '支付完成时间',
  `refund_amount` DECIMAL(10,2) DEFAULT 0.00 COMMENT '退款金额',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  INDEX `idx_user_created` (`user_id`, `created_at`),
  INDEX `idx_order_status` (`order_id`, `status`),
  CONSTRAINT `fk_payments_order` FOREIGN KEY (`order_id`) REFERENCES `orders`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='支付流水表';

SET FOREIGN_KEY_CHECKS = 1;
