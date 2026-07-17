-- ============================================================
-- 订单明细表: order_items
-- 记录子订单中每个SKU的购买数量、成交价格及下单时刻的快照信息
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `order_items`;

CREATE TABLE IF NOT EXISTS `order_items` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `sub_order_id` INT NOT NULL COMMENT '子订单ID',
  `sku_id` INT NOT NULL COMMENT 'SKU ID',
  `quantity` INT NOT NULL COMMENT '购买数量',
  `price` DECIMAL(10,2) NOT NULL COMMENT '成交单价（下单时快照）',
  `snapshot` JSON NULL COMMENT '下单时刻的商品快照JSON：{spuName, specName, image}',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  INDEX `idx_sub_order_id` (`sub_order_id`),
  INDEX `idx_sku_id` (`sku_id`),
  CONSTRAINT `fk_order_items_sub_order` FOREIGN KEY (`sub_order_id`) REFERENCES `sub_orders`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='订单明细表：记录子订单中每个SKU的购买数量、成交价格及下单时刻的快照信息';

SET FOREIGN_KEY_CHECKS = 1;
