-- shipments: 物流发货表
-- 记录商家发货信息（物流单号/承运商/状态），关联子订单

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `shipments`;

CREATE TABLE IF NOT EXISTS `shipments` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `sub_order_id` INT NOT NULL COMMENT '子订单ID（一个子订单一次发货）',
  `tracking_no` VARCHAR(64) NOT NULL COMMENT '物流运单号',
  `carrier_code` VARCHAR(32) NOT NULL COMMENT '物流商代码：SF=顺丰, ZTO=中通, YTO=圆通等',
  `status` ENUM('pending_pickup','in_transit','delivered','returned') NOT NULL DEFAULT 'pending_pickup' COMMENT '物流状态：pending_pickup=待揽收, in_transit=运输中, delivered=已签收, returned=已退回',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '发货时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  PRIMARY KEY (`id`),
  INDEX `idx_sub_order_id` (`sub_order_id`),
  INDEX `idx_tracking_no` (`tracking_no`),
  CONSTRAINT `fk_shipments_sub_order` FOREIGN KEY (`sub_order_id`) REFERENCES `sub_orders` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='物流发货表：记录商家发货信息，关联子订单';

SET FOREIGN_KEY_CHECKS = 1;
