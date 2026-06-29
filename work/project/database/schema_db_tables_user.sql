SET FOREIGN_KEY_CHECKS = 0;

-- DROP 先子表后主表（addresses 引用 users）
DROP TABLE IF EXISTS `addresses`;
DROP TABLE IF EXISTS `users`;

-- CREATE 先主表后子表
CREATE TABLE `users` (
  `id` INT AUTO_INCREMENT,
  `phone` VARCHAR(128) NOT NULL COMMENT 'AES-256加密存储，列表脱敏展示138****1234',
  `password` VARCHAR(255) NOT NULL COMMENT 'bcrypt哈希',
  `nickname` VARCHAR(50) DEFAULT '' COMMENT '用户昵称',
  `avatar` VARCHAR(255) DEFAULT '' COMMENT '头像URL',
  `role` ENUM('user','merchant','admin') NOT NULL DEFAULT 'user' COMMENT '角色: user(普通用户)/merchant(商家)/admin(管理员)',
  `status` ENUM('active','banned') NOT NULL DEFAULT 'active' COMMENT '状态: active→banned(封禁); banned→active(解封)',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `uk_phone` (`phone`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

CREATE TABLE `addresses` (
  `id` INT AUTO_INCREMENT,
  `user_id` INT NOT NULL COMMENT '用户ID',
  `province` VARCHAR(50) NOT NULL COMMENT '省',
  `city` VARCHAR(50) NOT NULL COMMENT '市',
  `district` VARCHAR(50) NOT NULL COMMENT '区/县',
  `detail` VARCHAR(255) NOT NULL COMMENT '详细地址',
  `phone` VARCHAR(20) NOT NULL COMMENT '收货电话',
  `name` VARCHAR(50) NOT NULL COMMENT '收货人姓名',
  `is_default` TINYINT(1) DEFAULT 0 COMMENT '是否默认地址: 0(否)/1(是)',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  INDEX `idx_user_id` (`user_id`),
  CONSTRAINT `fk_addresses_user_id` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='收货地址表';

SET FOREIGN_KEY_CHECKS = 1;
