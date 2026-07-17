-- ============================================================
-- 用户模块 DDL: users + refresh_tokens
-- 生成时间: 2025-01
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

-- ------------------------------------------------------------
-- 1. 用户核心表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `users` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `mobile` VARCHAR(11) NOT NULL UNIQUE COMMENT '手机号，登录凭证，11位数字',
  `password_hash` VARCHAR(255) NOT NULL COMMENT 'bcrypt哈希密码，saltRounds=10',
  `nickname` VARCHAR(64) NOT NULL COMMENT '用户昵称，展示用',
  `avatar` VARCHAR(255) NULL COMMENT '头像URL',
  `role` ENUM('user','merchant','admin') NOT NULL DEFAULT 'user' COMMENT '角色：user=买家, merchant=商家, admin=平台管理员',
  `status` ENUM('active','disabled') NOT NULL DEFAULT 'active' COMMENT '账号状态：active=正常, disabled=已禁用',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_mobile` (`mobile`),
  INDEX `idx_role_status` (`role`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户核心表：记录所有平台用户（买家/商家/管理员）的基本身份信息与登录凭据';

-- ------------------------------------------------------------
-- 2. 刷新令牌表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `refresh_tokens` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `user_id` INT NOT NULL COMMENT '用户ID',
  `token_hash` VARCHAR(255) NOT NULL UNIQUE COMMENT 'refresh token的SHA256哈希值',
  `expires_at` TIMESTAMP NOT NULL COMMENT '过期时间',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_token_hash` (`token_hash`),
  INDEX `idx_user_id` (`user_id`),
  INDEX `idx_expires_at` (`expires_at`),
  CONSTRAINT `fk_refresh_tokens_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='刷新令牌表：存储JWT refresh token的哈希值，用于安全刷新access token';

SET FOREIGN_KEY_CHECKS = 1;
