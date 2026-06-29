-- ============================================================
-- 退款表 DDL
-- 任务: db_tables_refund
-- 契约: model_refund v1.0.0 (backward compatible)
-- 依赖: db_tables_order_base (orders), db_tables_payment (payments)
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

-- ------------------------------------------------------------
-- 退款申请/审核/执行记录
-- 状态机: applied → approved → processing → completed
--         applied → rejected (终态)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `refunds` (
  `id`              INT AUTO_INCREMENT PRIMARY KEY COMMENT '退款ID',
  `order_id`        INT              NOT NULL COMMENT '关联订单ID',
  `payment_id`      INT              NOT NULL COMMENT '关联支付ID',
  `user_id`         INT              NOT NULL COMMENT '申请退款用户ID',
  `merchant_id`     INT              NOT NULL COMMENT '商户ID',
  `reason`          VARCHAR(500)     NOT NULL COMMENT '退款原因',
  `amount`          DECIMAL(10,2)    NOT NULL COMMENT '退款金额，不可超过原支付金额',
  `evidence_images` JSON             NULL     COMMENT '凭证图片URL数组',
  `status`          ENUM('applied','approved','rejected','processing','completed')
                                     NOT NULL DEFAULT 'applied'
                                     COMMENT '状态: applied→approved→processing→completed; applied→rejected(终态)',
  `apply_at`        TIMESTAMP        NULL     DEFAULT CURRENT_TIMESTAMP COMMENT '申请时间',
  `processed_at`    TIMESTAMP        NULL     DEFAULT NULL COMMENT '审核处理时间',
  `completed_at`    TIMESTAMP        NULL     DEFAULT NULL COMMENT '退款完成时间',
  `created_at`      TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  `updated_at`      TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',

  INDEX `idx_merchant_id_status` (`merchant_id`, `status`),
  INDEX `idx_order_id_status`   (`order_id`, `status`),

  CONSTRAINT `fk_refunds_order_id`
    FOREIGN KEY (`order_id`) REFERENCES `orders`(`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_refunds_payment_id`
    FOREIGN KEY (`payment_id`) REFERENCES `payments`(`id`)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='退款申请/审核/执行记录';

SET FOREIGN_KEY_CHECKS = 1;
