SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS `refund_logs` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `refund_request_id` INT NOT NULL COMMENT '售后申请ID',
  `operator_id` INT NOT NULL COMMENT '操作人用户ID',
  `action` VARCHAR(64) NOT NULL COMMENT '操作类型：apply/merchant_approve/merchant_reject/user_ship/merchant_confirm_receive/refund_success/refund_fail/arbitrate_force_refund/arbitrate_dismiss',
  `detail` VARCHAR(1000) NULL COMMENT '操作详情/备注',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
  PRIMARY KEY (`id`),
  INDEX `idx_refund_request_id` (`refund_request_id`),
  INDEX `idx_operator_id` (`operator_id`),
  CONSTRAINT `fk_refund_logs_request` FOREIGN KEY (`refund_request_id`) REFERENCES `refund_requests`(`id`),
  CONSTRAINT `fk_refund_logs_operator` FOREIGN KEY (`operator_id`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='售后操作日志表：记录售后单的每一步操作（申请/审核/仲裁/退款），用于追溯审计';

SET FOREIGN_KEY_CHECKS = 1;
