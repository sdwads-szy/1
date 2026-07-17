-- ══ 支付记录表: payments ══
-- 记录每笔支付流水（交易号/渠道/金额/回调日志），关联子订单

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `payments`;

CREATE TABLE IF NOT EXISTS `payments` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `transaction_no` VARCHAR(64) NOT NULL UNIQUE COMMENT '支付网关交易流水号，全局唯一',
  `sub_order_id` INT NOT NULL COMMENT '子订单ID',
  `channel` ENUM('wechat','alipay','unionpay') NOT NULL COMMENT '支付渠道：wechat=微信, alipay=支付宝, unionpay=银联',
  `amount` DECIMAL(10,2) NOT NULL COMMENT '支付金额',
  `status` ENUM('pending','success','failed','refunded') NOT NULL DEFAULT 'pending' COMMENT '支付状态：pending=待支付, success=已支付, failed=支付失败, refunded=已退款',
  `callback_log` JSON NULL COMMENT '支付网关回调原始日志JSON',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  PRIMARY KEY (`id`),
  INDEX `idx_transaction_no` (`transaction_no`),
  INDEX `idx_sub_order_id` (`sub_order_id`),
  INDEX `idx_status_created` (`status`, `created_at`),
  CONSTRAINT `fk_payments_sub_order` FOREIGN KEY (`sub_order_id`) REFERENCES `sub_orders` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='支付记录表：记录每笔支付流水（交易号/渠道/金额/回调日志），关联子订单';

SET FOREIGN_KEY_CHECKS = 1;
