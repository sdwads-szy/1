SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `settlement_orders`;

CREATE TABLE IF NOT EXISTS `settlement_orders` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `merchant_id` INT NOT NULL COMMENT '商家ID',
  `period` VARCHAR(7) NOT NULL COMMENT '结算周期，格式YYYY-MM',
  `amount` DECIMAL(10,2) NOT NULL COMMENT '结算金额',
  `status` ENUM('pending','confirmed','paid','completed','clawed_back') NOT NULL DEFAULT 'pending' COMMENT '结算状态：pending=待确认, confirmed=已确认, paid=已打款, completed=已完成, clawed_back=已追索',
  `paid_at` TIMESTAMP NULL COMMENT '打款时间',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_merchant_period` (`merchant_id`, `period`),
  INDEX `idx_status` (`status`),
  CONSTRAINT `fk_settlement_orders_merchant` FOREIGN KEY (`merchant_id`) REFERENCES `merchants`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='结算单表：记录每期商家结算的金额和状态，按商家+结算周期唯一';

SET FOREIGN_KEY_CHECKS = 1;
