-- ============================================================
-- 优惠券模块 DDL
-- Task: db_tables_coupon
-- Tables: coupons (券定义), user_coupons (用户领券记录)
-- Dependencies: db_tables_user (users 表)
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

-- DROP 先子表后主表
DROP TABLE IF EXISTS `user_coupons`;
DROP TABLE IF EXISTS `coupons`;

-- ============================================================
-- 主表: coupons (券定义)
-- ============================================================
CREATE TABLE IF NOT EXISTS `coupons` (
    `id`         INT           NOT NULL AUTO_INCREMENT,
    `title`      VARCHAR(100)  NOT NULL              COMMENT '券标题',
    `amount`     DECIMAL(10,2) NOT NULL              COMMENT '优惠金额',
    `min_order`  DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '最低订单金额门槛',
    `valid_from` TIMESTAMP     NOT NULL              COMMENT '有效期起始',
    `valid_to`   TIMESTAMP     NOT NULL              COMMENT '有效期截止',
    `status`     ENUM('active','disabled')           NOT NULL DEFAULT 'active' COMMENT '状态: active(启用), disabled(禁用); active→disabled; disabled→active',
    `created_at` TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='优惠券定义表';

-- ============================================================
-- 子表: user_coupons (用户领券记录)
-- ============================================================
CREATE TABLE IF NOT EXISTS `user_coupons` (
    `id`         INT          NOT NULL AUTO_INCREMENT,
    `user_id`    INT          NOT NULL              COMMENT '用户ID',
    `coupon_id`  INT          NOT NULL              COMMENT '优惠券ID',
    `status`     ENUM('available','used','expired') NOT NULL DEFAULT 'available' COMMENT '状态: available(可用)→used(已用/终态); available→expired(已过期/终态)',
    `used_at`    TIMESTAMP    NULL                  COMMENT '使用时间',
    `order_id`   INT          NULL                  COMMENT '使用订单ID',
    `created_at` TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '领取时间',
    PRIMARY KEY (`id`),
    INDEX        `idx_user_id`     (`user_id`),
    UNIQUE INDEX `uk_user_coupon`  (`user_id`, `coupon_id`),
    CONSTRAINT   `fk_user_coupons_user`   FOREIGN KEY (`user_id`)   REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT   `fk_user_coupons_coupon` FOREIGN KEY (`coupon_id`) REFERENCES `coupons` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户领券记录表';

SET FOREIGN_KEY_CHECKS = 1;
