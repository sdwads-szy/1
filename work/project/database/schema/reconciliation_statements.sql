-- =====================================================
-- 对账差异表 (reconciliation_statements)
-- 审计/历史类表 — 仅 CREATE IF NOT EXISTS，不 DROP
-- =====================================================

SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS `reconciliation_statements` (
  `id`          INT            NOT NULL AUTO_INCREMENT  COMMENT '自增主键',
  `merchant_id` INT            NOT NULL                 COMMENT '商家ID',
  `date`        DATE           NOT NULL                 COMMENT '对账日期',
  `diff`        DECIMAL(10,2)  NOT NULL DEFAULT 0.00    COMMENT '差异金额（系统金额-商家申报金额），正=系统多，负=商家多',
  `status`      ENUM('pending','resolved','ignored')    NOT NULL DEFAULT 'pending'
                                                         COMMENT '处理状态：pending=待处理, resolved=已解决, ignored=已忽略',
  `note`        VARCHAR(500)   DEFAULT NULL             COMMENT '备注说明',
  `created_at`  TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP
                                                         COMMENT '创建时间',
  `updated_at`  TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                                                         COMMENT '最后更新时间',

  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_merchant_date` (`merchant_id`, `date`),
  INDEX `idx_status` (`status`),
  CONSTRAINT `fk_rc_merchant_id` FOREIGN KEY (`merchant_id`) REFERENCES `merchants` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对账差异表：记录每日商家对账产生的差异项，用于财务核对';

