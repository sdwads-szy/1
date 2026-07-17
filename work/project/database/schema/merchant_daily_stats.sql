-- ============================================================
-- 商家日统计表
-- 描述: 记录每个商家每日的经营指标（GMV/订单数）
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS `merchant_daily_stats` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `merchant_id` INT NOT NULL COMMENT '商家ID',
  `stat_date` DATE NOT NULL COMMENT '统计日期',
  `gmv` DECIMAL(10,2) NOT NULL DEFAULT '0.00' COMMENT '当日GMV',
  `order_count` INT NOT NULL DEFAULT 0 COMMENT '当日订单数',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_merchant_date` (`merchant_id`, `stat_date`),
  INDEX `idx_stat_date` (`stat_date`),
  CONSTRAINT `fk_merchant_daily_stats_merchant` FOREIGN KEY (`merchant_id`) REFERENCES `merchants`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='商家日统计表：记录每个商家每日的经营指标';

SET FOREIGN_KEY_CHECKS = 1;
