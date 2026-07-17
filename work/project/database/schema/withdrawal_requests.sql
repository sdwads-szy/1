-- ============================================================
-- 提现申请表 DDL
-- 依赖: merchants (FK: merchant_id → merchants.id)
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS `withdrawal_requests` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `request_no` VARCHAR(32) NOT NULL COMMENT '提现单号，全局唯一',
  `merchant_id` INT NOT NULL COMMENT '商家ID',
  `amount` DECIMAL(10,2) NOT NULL COMMENT '提现金额',
  `bank_account` VARCHAR(255) NOT NULL COMMENT '银行账号（加密存储）',
  `status` ENUM('pending','approved','paid','rejected') NOT NULL DEFAULT 'pending' COMMENT '提现状态：pending=待审核, approved=已通过, paid=已打款, rejected=已驳回',
  `review_reason` VARCHAR(500) NULL COMMENT '审核意见/驳回原因',
  `paid_at` TIMESTAMP NULL COMMENT '打款时间',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '申请时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_request_no` (`request_no`),
  INDEX `idx_merchant_id` (`merchant_id`),
  INDEX `idx_status` (`status`),
  CONSTRAINT `fk_withdrawal_requests_merchant` FOREIGN KEY (`merchant_id`) REFERENCES `merchants` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='提现申请表';

SET FOREIGN_KEY_CHECKS = 1;
