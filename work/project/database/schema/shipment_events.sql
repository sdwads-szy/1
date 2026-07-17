SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS `shipment_events` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `shipment_id` INT NOT NULL COMMENT '物流记录ID',
  `event` VARCHAR(128) NOT NULL COMMENT '事件描述，如''快件已揽收''',
  `timestamp` TIMESTAMP NOT NULL COMMENT '事件发生时间',
  `location` VARCHAR(255) NULL COMMENT '事件发生地点',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  PRIMARY KEY (`id`),
  INDEX `idx_shipment_id` (`shipment_id`),
  INDEX `idx_shipment_timestamp` (`shipment_id`, `timestamp`),
  CONSTRAINT `fk_shipment_events_shipment` FOREIGN KEY (`shipment_id`) REFERENCES `shipments`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='物流轨迹表：记录每个包裹的物流节点事件（揽收/运输/派送/签收）';
SET FOREIGN_KEY_CHECKS = 1;



