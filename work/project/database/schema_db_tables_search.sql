SET FOREIGN_KEY_CHECKS = 0;

-- 搜索日志表：记录用户搜索行为（含匿名搜索）
CREATE TABLE IF NOT EXISTS `search_logs` (
  `id` INT AUTO_INCREMENT COMMENT '日志ID',
  `user_id` INT DEFAULT NULL COMMENT '用户ID，可为NULL(匿名搜索)',
  `query` VARCHAR(200) NOT NULL COMMENT '搜索关键词',
  `filters` JSON DEFAULT NULL COMMENT '筛选条件JSON',
  `result_count` INT DEFAULT 0 COMMENT '搜索结果数量',
  `clicked_product_ids` JSON DEFAULT NULL COMMENT '点击商品ID列表',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '搜索时间',
  PRIMARY KEY (`id`),
  INDEX `idx_query_created_at` (`query`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户搜索行为记录表';

SET FOREIGN_KEY_CHECKS = 1;
