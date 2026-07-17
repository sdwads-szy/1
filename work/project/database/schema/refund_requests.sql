SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `refund_requests`;

CREATE TABLE IF NOT EXISTS `refund_requests` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `request_no` VARCHAR(32) NOT NULL UNIQUE COMMENT '售后单号，全局唯一',
  `sub_order_id` INT NOT NULL COMMENT '关联子订单ID',
  `user_id` INT NOT NULL COMMENT '申请人用户ID',
  `type` ENUM('only_refund','return_refund') NOT NULL COMMENT '售后类型：only_refund=仅退款, return_refund=退货退款',
  `reason` VARCHAR(500) NOT NULL COMMENT '申请原因',
  `amount` DECIMAL(10,2) NOT NULL COMMENT '申请退款金额',
  `evidence_images` JSON NULL COMMENT '凭证图片URL数组JSON',
  `status` ENUM('pending','awaiting_return','awaiting_merchant_receive','refunding','completed','rejected','arbitrating','closed','retry') NOT NULL DEFAULT 'pending' COMMENT '售后状态：pending=待审核, awaiting_return=待退货, awaiting_merchant_receive=待商家收货, refunding=退款中, completed=已完成, rejected=已拒绝, arbitrating=仲裁中, closed=已关闭, retry=退款重试',
  `merchant_review_reason` VARCHAR(500) NULL COMMENT '商家审核意见',
  `arbitration_ruling` VARCHAR(500) NULL COMMENT '平台仲裁裁决',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '申请时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_request_no` (`request_no`),
  INDEX `idx_sub_order_id` (`sub_order_id`),
  INDEX `idx_user_id` (`user_id`),
  INDEX `idx_status` (`status`),
  CONSTRAINT `fk_refund_requests_sub_order` FOREIGN KEY (`sub_order_id`) REFERENCES `sub_orders`(`id`),
  CONSTRAINT `fk_refund_requests_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='售后申请表：记录消费者的退款/退货退款申请及其审核流转状态';

SET FOREIGN_KEY_CHECKS = 1;
