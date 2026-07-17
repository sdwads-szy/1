SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `merchant_wallets`;

CREATE TABLE IF NOT EXISTS `merchant_wallets` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `merchant_id` INT NOT NULL UNIQUE COMMENT '商家ID，一商一钱包',
  `balance` DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '可提现余额',
  `frozen_balance` DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '冻结余额（提现处理中）',
  `total_earned` DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '累计收入',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_merchant_id` (`merchant_id`),
  CONSTRAINT `fk_merchant_wallets_merchant` FOREIGN KEY (`merchant_id`) REFERENCES `merchants` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='商家钱包表：记录每个商家的可提现余额与冻结余额，使用乐观锁防并发';
SET FOREIGN_KEY_CHECKS = 1;
