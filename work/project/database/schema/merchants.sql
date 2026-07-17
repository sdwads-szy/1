-- ============================================================================
-- 商家入驻表: merchants
-- 依赖: users (FK: user_id -> users.id)
-- ============================================================================

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `merchants`;

CREATE TABLE IF NOT EXISTS `merchants` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `user_id` INT NOT NULL COMMENT '关联用户ID',
  `credit_code` VARCHAR(18) NOT NULL UNIQUE COMMENT '统一社会信用代码，18位，全局唯一',
  `biz_license` VARCHAR(255) NOT NULL COMMENT '营业执照图片URL',
  `contact_name` VARCHAR(32) NOT NULL COMMENT '联系人姓名',
  `contact_mobile` VARCHAR(11) NOT NULL COMMENT '联系人手机号',
  `status` ENUM('pending_review','approved','disabled') NOT NULL DEFAULT 'pending_review' COMMENT '审核状态：pending_review=待审核, approved=已开通, disabled=已禁用',
  `review_reason` VARCHAR(500) NULL COMMENT '审核意见/驳回原因',
  `reviewed_at` TIMESTAMP NULL COMMENT '审核时间',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '申请时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  PRIMARY KEY (`id`),

  INDEX `idx_credit_code` (`credit_code`),

  INDEX `idx_status` (`status`),
  INDEX `idx_user_id` (`user_id`),
  CONSTRAINT `fk_merchants_user_id` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='商家入驻表：记录商家的企业资质信息与审核状态，一个商家对应一个用户账号和一个店铺';

SET FOREIGN_KEY_CHECKS = 1;
