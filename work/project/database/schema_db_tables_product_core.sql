-- ============================================================
-- 商品核心表：products(商品主表) + skus(SKU规格库存)
-- taskId: db_tables_product_core
-- 依赖: shops(id), categories(id)
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

-- 先删子表再删主表
DROP TABLE IF EXISTS `skus`;
DROP TABLE IF EXISTS `products`;

-- 先建主表再建子表
CREATE TABLE IF NOT EXISTS `products` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '商品ID',
  `shop_id` INT NOT NULL COMMENT '所属店铺ID',
  `category_id` INT NOT NULL COMMENT '所属分类ID',
  `title` VARCHAR(200) NOT NULL COMMENT '商品标题',
  `description` TEXT COMMENT '商品描述富文本',
  `status` ENUM('draft','pending_review','approved','rejected','listed','delisted') NOT NULL DEFAULT 'draft' COMMENT '商品状态: draft=草稿,pending_review=待审核,approved=已通过,rejected=已驳回,listed=已上架,delisted=已下架',
  `main_image` VARCHAR(255) DEFAULT '' COMMENT '商品主图URL',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX `idx_category_status` (`category_id`, `status`) COMMENT '分类+状态联合索引',
  INDEX `idx_shop_id` (`shop_id`) COMMENT '店铺索引',
  CONSTRAINT `fk_products_shop` FOREIGN KEY (`shop_id`) REFERENCES `shops`(`id`),
  CONSTRAINT `fk_products_category` FOREIGN KEY (`category_id`) REFERENCES `categories`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='商品主表';

CREATE TABLE IF NOT EXISTS `skus` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT 'SKU ID',
  `product_id` INT NOT NULL COMMENT '所属商品ID',
  `spec_combo` VARCHAR(255) NOT NULL COMMENT '规格组合JSON: {"颜色":"红色","尺寸":"L"}',
  `price` DECIMAL(10,2) NOT NULL COMMENT '价格',
  `stock` INT NOT NULL DEFAULT 0 COMMENT '库存数量',
  `image` VARCHAR(255) DEFAULT '' COMMENT 'SKU图片URL',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  INDEX `idx_product_id` (`product_id`) COMMENT '商品ID索引',
  CONSTRAINT `fk_skus_product` FOREIGN KEY (`product_id`) REFERENCES `products`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='SKU规格库存表';

SET FOREIGN_KEY_CHECKS = 1;
