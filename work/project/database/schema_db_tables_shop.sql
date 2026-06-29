SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `merchant_qualifications`;
DROP TABLE IF EXISTS `shops`;

CREATE TABLE IF NOT EXISTS `shops` (
  `id` INT AUTO_INCREMENT COMMENT '主键',
  `user_id` INT NOT NULL COMMENT '关联商家用户',
  `name` VARCHAR(100) NOT NULL COMMENT '店铺名称',
  `logo` VARCHAR(255) DEFAULT '' COMMENT '店铺Logo URL',
  `description` TEXT COMMENT '店铺简介',
  `status` ENUM('pending','active','frozen','cleared') NOT NULL DEFAULT 'pending' COMMENT '状态: pending→active→frozen→cleared(终态); pending→frozen; active→cleared(终态)',
  `commission_rate` DECIMAL(4,2) DEFAULT 5.00 COMMENT '佣金比例%',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  INDEX `idx_user_id` (`user_id`),
  INDEX `idx_status` (`status`),
  CONSTRAINT `fk_shops_user_id` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='店铺表';

CREATE TABLE IF NOT EXISTS `merchant_qualifications` (
  `id` INT AUTO_INCREMENT COMMENT '主键',
  `shop_id` INT NOT NULL COMMENT '关联店铺ID',
  `business_license` VARCHAR(255) NOT NULL COMMENT '营业执照图片URL',
  `legal_person_id` VARCHAR(255) NOT NULL COMMENT '法人身份证图片URL',
  `bank_account` VARCHAR(255) NOT NULL COMMENT '银行账户 AES-256加密',
  `status` ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending' COMMENT '状态: pending→approved(终态); pending→rejected(终态)',
  `reviewer_id` INT COMMENT '审核管理员ID',
  `review_note` TEXT COMMENT '审核备注',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  INDEX `idx_shop_id` (`shop_id`),
  CONSTRAINT `fk_merchant_qualifications_shop_id` FOREIGN KEY (`shop_id`) REFERENCES `shops`(`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='商家资质表';

SET FOREIGN_KEY_CHECKS = 1;
