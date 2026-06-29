SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `carts`;

CREATE TABLE IF NOT EXISTS `carts` (
  `id` INT AUTO_INCREMENT COMMENT '购物车记录ID',
  `user_id` INT NOT NULL COMMENT '用户ID',
  `sku_id` INT NOT NULL COMMENT 'SKU ID',
  `quantity` INT NOT NULL DEFAULT 1 COMMENT '数量，最大99',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  INDEX `idx_user_id` (`user_id`),
  UNIQUE INDEX `uk_user_sku` (`user_id`, `sku_id`),
  CONSTRAINT `fk_carts_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`),
  CONSTRAINT `fk_carts_sku` FOREIGN KEY (`sku_id`) REFERENCES `skus`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='购物车表';

SET FOREIGN_KEY_CHECKS = 1;
