SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `shops`;

CREATE TABLE IF NOT EXISTS `shops` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `merchant_id` INT NOT NULL UNIQUE COMMENT '商家ID，一商一店',
  `name` VARCHAR(64) NOT NULL UNIQUE COMMENT '店铺名称，全局唯一',
  `logo` VARCHAR(255) DEFAULT NULL COMMENT '店铺Logo图片URL',
  `banner` VARCHAR(255) DEFAULT NULL COMMENT '店铺横幅图片URL',
  `description` VARCHAR(500) DEFAULT NULL COMMENT '店铺简介',
  `status` ENUM('open','closed','frozen') NOT NULL DEFAULT 'open' COMMENT '营业状态：open=营业中, closed=已打烊, frozen=已冻结（平台强制）',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '开店时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  PRIMARY KEY (`id`),

  INDEX `idx_status` (`status`),
  INDEX `idx_merchant_id` (`merchant_id`),
  INDEX `idx_name` (`name`),

  CONSTRAINT `fk_shops_merchant` FOREIGN KEY (`merchant_id`) REFERENCES `merchants`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='店铺表：每个商家拥有一个店铺，记录店铺展示信息与营业状态';

SET FOREIGN_KEY_CHECKS = 1;
