-- ============================================================
-- 库存表: inventories
-- 记录每个店铺下每个SKU的可售库存、冻结库存
-- 使用乐观锁 version 字段防并发超卖
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `inventories`;

CREATE TABLE IF NOT EXISTS `inventories` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `sku_id` INT NOT NULL COMMENT 'SKU ID',
  `shop_id` INT NOT NULL COMMENT '店铺ID',
  `stock` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '可售库存数量',
  `frozen_stock` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '冻结库存（下单预占、售后冻结等）',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号，每次修改+1',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_sku_shop` (`sku_id`, `shop_id`),
  INDEX `idx_shop_id` (`shop_id`),
  CONSTRAINT `fk_inventories_sku` FOREIGN KEY (`sku_id`) REFERENCES `sku` (`id`),
  CONSTRAINT `fk_inventories_shop` FOREIGN KEY (`shop_id`) REFERENCES `shops` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='库存表：记录每个店铺下每个SKU的可售库存、冻结库存，使用乐观锁version字段防并发超卖';


SET FOREIGN_KEY_CHECKS = 1;
