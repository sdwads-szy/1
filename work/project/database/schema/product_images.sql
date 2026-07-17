-- ============================================================
-- 商品图片表: product_images
-- SPU的多图轮播资源，支持排序
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `product_images`;

CREATE TABLE IF NOT EXISTS `product_images` (
  `id`         INT           NOT NULL AUTO_INCREMENT  COMMENT '自增主键',
  `spu_id`     INT           NOT NULL                 COMMENT '所属SPU ID',
  `url`        VARCHAR(255)  NOT NULL                 COMMENT '图片URL',
  `sort`       INT           NOT NULL DEFAULT 0       COMMENT '排序权重，数值越小越靠前',
  `created_at` TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  INDEX `idx_spu_id` (`spu_id`),
  INDEX `idx_spu_sort` (`spu_id`, `sort`),
  CONSTRAINT `fk_product_images_spu` FOREIGN KEY (`spu_id`) REFERENCES `spu` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='商品图片表：SPU的多图轮播资源，支持排序';

SET FOREIGN_KEY_CHECKS = 1;
