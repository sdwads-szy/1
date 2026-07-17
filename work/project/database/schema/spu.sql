-- ═══════════════════════════════════════════
-- SPU 商品表
-- 标准化产品单元，定义商品的基本信息和状态
-- 一个 SPU 包含多个 SKU
-- ═══════════════════════════════════════════

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `spu`;

CREATE TABLE IF NOT EXISTS `spu` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `shop_id` INT NOT NULL COMMENT '所属店铺ID',
  `category_id` INT NOT NULL COMMENT '所属类目ID',
  `name` VARCHAR(128) NOT NULL COMMENT '商品名称',
  `description` TEXT NULL COMMENT '商品详情描述（富文本）',
  `default_image` VARCHAR(255) NULL COMMENT '默认主图URL，列表展示用',
  `status` ENUM('draft','listed','delisted') NOT NULL DEFAULT 'draft' COMMENT '商品状态：draft=草稿, listed=已上架, delisted=已下架',
  `sales` INT NOT NULL DEFAULT 0 COMMENT '累计销量',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  PRIMARY KEY (`id`),
  INDEX `idx_shop_id` (`shop_id`),
  INDEX `idx_category_id` (`category_id`),
  INDEX `idx_status` (`status`),
  INDEX `idx_shop_status` (`shop_id`, `status`),
  CONSTRAINT `fk_spu_shop_id` FOREIGN KEY (`shop_id`) REFERENCES `shops` (`id`),
  CONSTRAINT `fk_spu_category_id` FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='商品SPU表：标准化产品单元，定义商品的基本信息和状态，一个SPU包含多个SKU';

SET FOREIGN_KEY_CHECKS = 1;
