SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `sub_orders`;

CREATE TABLE IF NOT EXISTS `sub_orders` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `sub_order_no` VARCHAR(32) NOT NULL UNIQUE COMMENT '子订单号，全局唯一',
  `order_id` INT NOT NULL COMMENT '主订单ID',
  `shop_id` INT NOT NULL COMMENT '店铺ID',
  `amount` DECIMAL(10,2) NOT NULL COMMENT '子订单金额',
  `status` ENUM('pending','paid','shipped','completed','cancelled','refunding','refunded') NOT NULL DEFAULT 'pending' COMMENT '子订单状态: pending=待支付, paid=已支付, shipped=已发货, completed=已完成, cancelled=已取消, refunding=退款中, refunded=已退款',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  PRIMARY KEY (`id`),
  INDEX `idx_sub_order_no` (`sub_order_no`),
  INDEX `idx_order_id` (`order_id`),
  INDEX `idx_shop_id` (`shop_id`),
  INDEX `idx_shop_status` (`shop_id`, `status`),
  CONSTRAINT `fk_sub_orders_order` FOREIGN KEY (`order_id`) REFERENCES `orders`(`id`),
  CONSTRAINT `fk_sub_orders_shop` FOREIGN KEY (`shop_id`) REFERENCES `shops`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='子订单表：按店铺拆分订单，每个子订单对应一个店铺的购买明细';

SET FOREIGN_KEY_CHECKS = 1;
