-- ============================================================
-- 订单主表 (orders)
-- 记录每笔交易的汇总信息（金额/状态/买家）
-- 一个主订单包含多个子订单（按店铺拆分）
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS `orders` (
  `id` INT AUTO_INCREMENT COMMENT '自增主键',
  PRIMARY KEY (`id`),
  `order_no` VARCHAR(32) NOT NULL UNIQUE COMMENT '雪花算法生成的订单号，全局唯一',
  `user_id` INT NOT NULL COMMENT '买家用户ID',
  `total_amount` DECIMAL(10,2) NOT NULL COMMENT '订单总金额（所有子订单金额之和）',
  `status` ENUM('pending','paid','shipped','completed','cancelled','refunding','refunded') NOT NULL DEFAULT 'pending' COMMENT '订单状态：pending=待付款, paid=已付款, shipped=已发货, completed=已完成, cancelled=已取消, refunding=退款中, refunded=已退款',
  `paid_at` TIMESTAMP NULL COMMENT '支付完成时间',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '下单时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  UNIQUE INDEX `idx_order_no` (`order_no`),
  INDEX `idx_user_status` (`user_id`, `status`),
  INDEX `idx_created_at` (`created_at`),
  CONSTRAINT `fk_orders_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='订单主表';

SET FOREIGN_KEY_CHECKS = 1;

