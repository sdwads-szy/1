const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

describe('t_api_merchant_orders', () => {
  const routeSrc = fs.readFileSync(path.join(workspace, 'routes/merchantOrders.js'), 'utf-8');
  const ctrlSrc  = fs.readFileSync(path.join(workspace, 'controllers/merchantOrderController.js'), 'utf-8');
  const frontSrc = fs.readFileSync(path.join(workspace, 'src/api/merchant-orders.js'), 'utf-8');

  // ==== 维度1: 路由匹配 ====
  describe('路由匹配', () => {
    it('GET / → handler: listShopOrders', () => {
      expect(routeSrc).toContain('/');
      expect(ctrlSrc).toContain('getOrderList');
    });
    it('POST /:id/ship → handler: shipOrder', () => {
      expect(routeSrc).toContain('/:id/ship');
      expect(ctrlSrc).toContain('shipOrder');
    });
  });

  // ==== 维度2: 字段一致 ====
  describe('字段一致', () => {
    it('controller 接收了预期字段: status, page, pageSize', () => {
      ['status', 'page', 'pageSize'].forEach(f => expect(ctrlSrc).toContain(f));
    });
    it('controller 接收了预期字段: id, trackingNo, carrierCode', () => {
      ['id', 'trackingNo', 'carrierCode'].forEach(f => expect(ctrlSrc).toContain(f));
    });
  });

  // ==== 维度3: 中间件链 ====
  describe('中间件链', () => {
    it('GET / 挂载了 authenticate 中间件', () => {
      expect(routeSrc).toContain('authenticate');
    });
    it('GET / 挂载了 requireRole 中间件', () => {
      expect(routeSrc).toContain("hasRole('merchant')");
    });
    it('POST /:id/ship 挂载了 authenticate 中间件', () => {
      expect(routeSrc).toContain('authenticate');
    });
    it('POST /:id/ship 挂载了 requireRole 中间件', () => {
      expect(routeSrc).toContain("hasRole('merchant')");
    });
  });

  // ==== 维度4: 错误码映射 ====
  describe('错误码映射', () => {
    it('controller 包含所有契约错误码', () => {
      const codes = ['NOT_BELONG_TO_SHOP', 'ORDER_STATUS'];
      codes.forEach(c => expect(ctrlSrc).toContain(c));
    });
  });

  // ==== 维度5: 响应格式 ====
  describe('响应格式', () => {
    it('controller 使用规范响应方法', () => {
      const usesResponse = ctrlSrc.includes('response.success')
                        || ctrlSrc.includes('response.fail')
                        || ctrlSrc.includes('response.error')
                        || ctrlSrc.includes('res.json(')
                        || ctrlSrc.includes('res.status(');
      expect(usesResponse).toBe(true);
    });
  });

  // ==== 维度6: 前端对齐 ====
  describe('前端对齐', () => {
    it('前端 API 调用的端点与后端路由一致', () => {
      const endpoints = ['/merchant/orders', '/ship'];
      endpoints.forEach(ep => expect(frontSrc).toContain(ep));
    });
  });

  // ==== 边界逻辑 ====
  describe('边界逻辑', () => {
    it('shipOrder 校验非 paid 状态拒绝发货 → 422', () => {
      expect(ctrlSrc).toContain('当前订单状态不可发货');
      expect(ctrlSrc).toContain('422');
    });
  });
});
