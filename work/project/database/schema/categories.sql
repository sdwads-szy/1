-- ============================================================
-- 商品类目表: categories（自引用树）
-- 支持三级类目，用于商品分类浏览与筛选
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `categories`;

CREATE TABLE IF NOT EXISTS `categories` (
  `id`         INT          NOT NULL AUTO_INCREMENT  COMMENT '自增主键',
  `parent_id`  INT          NULL                     COMMENT '父类目ID，NULL=顶级类目',
  `name`       VARCHAR(32)  NOT NULL                 COMMENT '类目名称',
  `level`      TINYINT(2)   NOT NULL                 COMMENT '层级：1=一级类目, 2=二级类目, 3=三级类目',
  `sort`       INT          NOT NULL DEFAULT 0       COMMENT '排序权重，数值越小越靠前',
  `icon`       VARCHAR(255) NULL                     COMMENT '类目图标URL',
  `created_at` TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  INDEX `idx_parent_id` (`parent_id`),
  INDEX `idx_level_sort` (`level`, `sort`),
  CONSTRAINT `fk_categories_parent` FOREIGN KEY (`parent_id`) REFERENCES `categories` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='商品类目表：树形结构，支持多级类目，用于商品分类浏览与筛选';


