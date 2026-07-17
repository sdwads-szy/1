const db = require('../config/db');

/**
 * 按子订单ID查询物流记录 — 订单详情页展示物流信息
 * @param {number} subOrderId 子订单ID
 * @returns {object|null} 物流记录或null（尚未发货）
 */
async function getShipmentBySubOrder(subOrderId) {
  const rows = await db.query(
    'SELECT id, sub_order_id, tracking_no, carrier_code, status, created_at, updated_at FROM shipments WHERE sub_order_id = ? ORDER BY created_at DESC LIMIT 1',
    [subOrderId]
  );
  return rows.length ? rows[0] : null;
}

/**
 * 按物流记录ID查轨迹 — 订单详情页物流时间线
 * @param {number} shipmentId 物流记录ID
 * @returns {Array} 物流轨迹事件数组，按时间升序
 */
async function getShipmentEvents(shipmentId) {
  return await db.query(
    'SELECT id, event, timestamp, location FROM shipment_events WHERE shipment_id = ? ORDER BY timestamp ASC',
    [shipmentId]
  );
}

/**
 * 物流监控总览 — 平台物流管理页
 * 统计异常物流单数、监控超时查询次数、最近异常记录
 * @returns {object} { abnormalShipments, timeoutQueries, recentErrors }
 */
async function getMonitor() {
  // 异常物流单数：已退回的包裹
  const abnormalRows = await db.query(
    'SELECT COUNT(*) AS count FROM shipments WHERE status = ?',
    ['returned']
  );

  // 超时查询：运输中 + 待揽收（物流API轮询中尚未完结的包裹）
  const timeoutRows = await db.query(
    'SELECT COUNT(*) AS count FROM shipments WHERE status IN (?, ?)',
    ['pending_pickup', 'in_transit']
  );

  const recentErrors = await db.query(
    'SELECT s.id AS shipmentId, s.tracking_no AS trackingNo, ' +
    '(SELECT se.event FROM shipment_events se WHERE se.shipment_id = s.id ORDER BY se.timestamp DESC LIMIT 1) AS error, ' +
    '(SELECT se.timestamp FROM shipment_events se WHERE se.shipment_id = s.id ORDER BY se.timestamp DESC LIMIT 1) AS time ' +
    'FROM shipments s ' +
    'WHERE s.status = ? ' +
    'ORDER BY s.updated_at DESC ' +
    'LIMIT 10',
    ['returned']
  );

  return {
    abnormalShipments: abnormalRows[0].count,
    timeoutQueries: timeoutRows[0].count,
    recentErrors
  };
}

module.exports = { getShipmentBySubOrder, getShipmentEvents, getMonitor };
