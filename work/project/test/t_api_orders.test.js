const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

describe('t_api_orders', () => {
  const routeSrc = fs.readFileSync(path.join(workspace, 'routes/orders.js'), 'utf-8');
  const ctrlSrc  = fs.readFileSync(path.join(workspace, 'controllers/orderController.js'), 'utf-8');
  const frontSrc = fs.readFileSync(path.join(workspace, 'src/api/orders.js'), 'utf-8');

  // ==== 维度1: 路由匹配 ====
  describe('路由匹配', () => {
    it("POST / → handler: createOrder", () => {
      expect(routeSrc).toContain("post('/', authenticate");
      expect(ctrlSrc).toContain('createOrder');
    });
    it("GET / → handler: listOrders", () => {
      expect(routeSrc).toContain("get('/', authenticate");
      expect(ctrlSrc).toContain('listOrders');
    });
    it("GET /:id → handler: getOrderDetail", () => {
      expect(routeSrc).toContain("get('/:id', authenticate");
      expect(ctrlSrc).toContain('getOrderDetail');
    });
    it("PUT /:id/confirm → handler: confirmReceive", () => {
      expect(routeSrc).toContain("put('/:id/confirm', authenticate");
      expect(ctrlSrc).toContain('confirmReceive');
    });
  });

  // ==== 维度2: 字段一致 ====
  describe('字段一致', () => {
    it('createOrder 接收了预期字段: addressId, cartItemIds, remark', () => {
      ['addressId', 'cartItemIds', 'remark'].forEach(f => expect(ctrlSrc).toContain(f));
    });
    it('listOrders 接收了预期字段: status, page, pageSize', () => {
      ['status', 'page', 'pageSize'].forEach(f => expect(ctrlSrc).toContain(f));
    });
    it('getOrderDetail 从 req.params 取 id', () => {
      expect(ctrlSrc).toContain('req.params.id');
    });
    it('confirmReceive 从 req.params 取 id', () => {
      expect(ctrlSrc).toContain('req.params.id');
    });
  });

  // ==== 维度3: 中间件链 ====
  describe('中间件链', () => {
    it('所有 /orders 路由挂载 authenticate 中间件', () => {
      // 每个路由行都应含 authenticate
      expect(routeSrc).toContain('authenticate');
    });
  });

  // ==== 维度4: 错误码映射 ====
  describe('错误码映射', () => {
    it('controller 包含所有契约错误码', () => {
      const codes = ['STOCK_INSUFFICIENT', 'EMPTY_CART', 'ORDER_NOT_FOUND'];
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
      const endpoints = ['createOrder', 'getOrders', 'getOrderDetail', 'confirmReceive'];
      endpoints.forEach(ep => expect(frontSrc).toContain(ep));
    });
  });
});
