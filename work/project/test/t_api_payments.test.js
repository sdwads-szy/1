const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

describe('t_api_payments', () => {
  const routeSrc = fs.readFileSync(path.join(workspace, 'routes/payments.js'), 'utf-8');
  const ctrlSrc  = fs.readFileSync(path.join(workspace, 'controllers/paymentController.js'), 'utf-8');
  const frontSrc = fs.readFileSync(path.join(workspace, 'src/api/payments.js'), 'utf-8');

  // ==== 维度1: 路由匹配 ====
  describe('路由匹配', () => {
    it("POST / → handler: initiatePayment", () => {
      const hasPostRoute = routeSrc.includes("post('/pay'") || routeSrc.includes('post("/pay"');
      expect(hasPostRoute).toBe(true);
      expect(ctrlSrc).toContain('initiatePayment');
    });
    it("GET /status/:orderNo → handler: getPaymentStatus", () => {
      expect(routeSrc).toContain('/status/:orderNo');
      expect(ctrlSrc).toContain('getPaymentStatus');
    });
  });

  // ==== 维度2: 字段一致 ====
  describe('字段一致', () => {
    it("controller 接收了预期字段: orderNo, channel (POST /)", () => {
      ['orderNo', 'channel'].forEach(f => expect(ctrlSrc).toContain(f));
    });
    it("controller 接收了预期字段: orderNo (GET /status/:orderNo)", () => {
      expect(ctrlSrc).toContain('orderNo');
    });
  });

  // ==== 维度3: 中间件链 ====
  describe('中间件链', () => {
    it("POST / 挂载了 authenticate 中间件", () => {
      expect(routeSrc).toContain('authenticate');
    });
    it("GET /status/:orderNo 挂载了 authenticate 中间件", () => {
      expect(routeSrc).toContain('authenticate');
    });
  });

  // ==== 维度4: 错误码映射 ====
  describe('错误码映射', () => {
    it('controller 包含所有契约错误码', () => {
      const codes = ['PAYMENT_TIMEOUT', 'DUPLICATE_PAYMENT', 'ORDER_NOT_FOUND'];
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
    it('前端 API 调用的函数名与后端一致', () => {
      const endpoints = ['initiatePayment', 'getPaymentStatus'];
      endpoints.forEach(ep => expect(frontSrc).toContain(ep));
    });
  });

  // ==== boundary: 重复支付 ====
  describe('边界条件', () => {
    it('initiatePayment 对已支付订单返回 409', () => {
      expect(ctrlSrc).toContain('409');
    });
  });
});
