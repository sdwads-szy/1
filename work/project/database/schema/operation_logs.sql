-- ============================================================
-- 运营操作日志表 (operation_logs)
-- 描述: 记录平台管理员的关键操作（审核/冻结/仲裁等），用于审计追溯
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;
CREATE TABLE IF NOT EXISTS `operation_logs` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `admin_id` INT NOT NULL COMMENT '管理员用户ID',
  `action` VARCHAR(64) NOT NULL COMMENT '操作类型：review_merchant/freeze_merchant/review_product/arbitrate_refund/settlement_pay/approve_withdrawal',
  `target_type` VARCHAR(32) NOT NULL COMMENT '操作目标类型：merchant/product/refund_request/settlement/withdrawal',
  `target_id` INT NOT NULL COMMENT '操作目标ID',
  `detail` JSON NULL COMMENT '操作详情JSON：{before, after, reason}',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
  PRIMARY KEY (`id`),
  INDEX `idx_admin_id` (`admin_id`),
  INDEX `idx_target` (`target_type`, `target_id`),
  INDEX `idx_created_at` (`created_at`),
  CONSTRAINT `fk_operation_logs_admin` FOREIGN KEY (`admin_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='运营操作日志表：记录平台管理员的关键操作（审核/冻结/仲裁等），用于审计追溯';
SET FOREIGN_KEY_CHECKS = 1;
