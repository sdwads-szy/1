SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `user_addresses`;

CREATE TABLE IF NOT EXISTS `user_addresses` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `user_id` INT NOT NULL COMMENT '用户ID，关联users表',
  `province` VARCHAR(32) NOT NULL COMMENT '省份',
  `city` VARCHAR(32) NOT NULL COMMENT '城市',
  `district` VARCHAR(32) NOT NULL COMMENT '区/县',
  `detail` VARCHAR(255) NOT NULL COMMENT '详细地址，传输加密存储',
  `phone` VARCHAR(11) NOT NULL COMMENT '收货人手机号，传输加密',
  `contact_name` VARCHAR(32) NOT NULL COMMENT '收货人姓名',
  `is_default` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否默认地址：0=否, 1=是',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  PRIMARY KEY (`id`),
  INDEX `idx_user_id` (`user_id`),
  INDEX `idx_user_default` (`user_id`, `is_default`),
  CONSTRAINT `fk_user_addresses_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户收货地址表：存储买家的配送地址信息，支持多地址与默认地址';

SET FOREIGN_KEY_CHECKS = 1;
