-- ============================================================
-- 购物车表: cart_items
-- 记录用户加入购物车的商品及数量，按店铺分组展示，勾选后进入结算
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `cart_items`;

CREATE TABLE IF NOT EXISTS `cart_items` (
  `id`         INT           NOT NULL AUTO_INCREMENT              COMMENT '自增主键',
  `user_id`    INT           NOT NULL                             COMMENT '用户ID',
  `sku_id`     INT           NOT NULL                             COMMENT 'SKU ID',
  `shop_id`    INT           NOT NULL                             COMMENT '店铺ID（冗余，便于按店铺分组）',
  `quantity`   INT           NOT NULL DEFAULT 1                   COMMENT '购买数量',
  `checked`    TINYINT(1)    NOT NULL DEFAULT 1                   COMMENT '是否勾选：0=未勾选, 1=已勾选',
  `created_at` TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP   COMMENT '加入时间',
  `updated_at` TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',

  PRIMARY KEY (`id`),

  INDEX `idx_user_id` (`user_id`),
  UNIQUE INDEX `idx_user_sku_shop` (`user_id`, `sku_id`, `shop_id`),

  CONSTRAINT `fk_cart_items_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_cart_items_sku`  FOREIGN KEY (`sku_id`)  REFERENCES `sku` (`id`),
  CONSTRAINT `fk_cart_items_shop` FOREIGN KEY (`shop_id`) REFERENCES `shops` (`id`)
)
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='购物车表：记录用户加入购物车的商品及数量，按店铺分组展示，勾选后进入结算';
SET FOREIGN_KEY_CHECKS = 1;
