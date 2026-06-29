-- ============================================================
-- 商品类目表（3级自引用树）
-- ============================================================
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `categories`;

CREATE TABLE IF NOT EXISTS `categories` (
  `id` INT AUTO_INCREMENT COMMENT '类目ID',
  `name` VARCHAR(50) NOT NULL COMMENT '类目名称',
  `parent_id` INT DEFAULT 0 COMMENT '父类目ID，0=根节点',
  `sort` INT DEFAULT 0 COMMENT '排序权重，数值越小越靠前',
  `status` ENUM('active','disabled') NOT NULL DEFAULT 'active' COMMENT '状态: active=启用, disabled=禁用',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  INDEX `idx_parent_id` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='商品类目表（3级自引用树）';

SET FOREIGN_KEY_CHECKS = 1;
