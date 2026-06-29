-- ============================================================
-- 商品审计模块 DDL
-- 表: product_snapshots (编辑快照) + audit_logs (审核日志)
-- 依赖: products 表 (db_tables_product_core)
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

-- ------------------------------------------------------------
-- CREATE: 先主表后子表
-- products 由 db_tables_product_core 管理，此处不重复创建
-- ------------------------------------------------------------

-- 商品快照表（历史数据，禁止 DROP）
CREATE TABLE IF NOT EXISTS `product_snapshots` (
  `id` INT AUTO_INCREMENT COMMENT '快照ID',
  `product_id` INT NOT NULL COMMENT '商品ID',
  `snapshot` JSON NOT NULL COMMENT '商品完整快照JSON',
  `version` INT NOT NULL DEFAULT 1 COMMENT '快照版本号',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  INDEX `idx_product_id` (`product_id`),
  CONSTRAINT `fk_product_snapshots_product` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='商品编辑快照表';

-- 审核日志表（审计数据，禁止 DROP）
CREATE TABLE IF NOT EXISTS `audit_logs` (
  `id` INT AUTO_INCREMENT COMMENT '日志ID',
  `product_id` INT NOT NULL COMMENT '商品ID',
  `auditor_id` INT NOT NULL COMMENT '审核人ID',
  `result` ENUM('approved','rejected') NOT NULL COMMENT '审核结果: approved=通过, rejected=驳回',
  `reason` TEXT COMMENT '审核意见',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  INDEX `idx_product_id` (`product_id`),
  CONSTRAINT `fk_audit_logs_product` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='商品审核日志表';

SET FOREIGN_KEY_CHECKS = 1;
