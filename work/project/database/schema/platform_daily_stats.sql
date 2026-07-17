SET FOREIGN_KEY_CHECKS = 0;

-- 平台日统计表
CREATE TABLE IF NOT EXISTS `platform_daily_stats` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `stat_date` DATE NOT NULL UNIQUE COMMENT '统计日期',
  `gmv` DECIMAL(12,2) NOT NULL DEFAULT 0.00 COMMENT '当日GMV',
  `order_count` INT NOT NULL DEFAULT 0 COMMENT '当日订单数',
  `paid_order_count` INT NOT NULL DEFAULT 0 COMMENT '当日支付订单数',
  `refund_rate` DECIMAL(5,4) NOT NULL DEFAULT 0.0000 COMMENT '退款率（小数，如0.0523=5.23%）',
  `commission` DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '当日平台佣金',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_stat_date` (`stat_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='平台日统计表：记录每日平台级运营指标（GMV/订单量/退款率/佣金）';

SET FOREIGN_KEY_CHECKS = 1;
