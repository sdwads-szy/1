const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

describe('t_api_refunds', () => {
  const routeSrc = fs.readFileSync(path.join(workspace, 'routes/refunds.js'), 'utf-8');
  const ctrlSrc  = fs.readFileSync(path.join(workspace, 'controllers/refundController.js'), 'utf-8');
  const frontSrc = fs.readFileSync(path.join(workspace, 'src/api/refunds.js'), 'utf-8');

  // ==== 维度1: 路由匹配 ====
  describe('路由匹配', () => {
    it("POST / → handler: applyRefund", () => {
      const hasPostRoot = routeSrc.includes("post('/'") || routeSrc.includes('post("/"');
      expect(hasPostRoot).toBe(true);
      expect(ctrlSrc).toContain('applyRefund');
    });

    it("GET /:id → handler: getRefundDetail", () => {
      const hasGetId = routeSrc.includes("get('/:id'") || routeSrc.includes('get("/:id"');
      expect(hasGetId).toBe(true);
      expect(ctrlSrc).toContain('getRefundDetail');
    });
  });

  // ==== 维度2: 字段一致 ====
  describe('字段一致', () => {
    it("applyRefund 接收了预期字段: subOrderId, type, reason, amount, evidenceImages", () => {
      ['subOrderId', 'type', 'reason', 'amount', 'evidenceImages'].forEach(f => {
        expect(ctrlSrc).toContain(f);
      });
    });

    it("getRefundDetail 使用了 req.params.id", () => {
      expect(ctrlSrc).toContain('req.params.id');
    });
  });

  // ==== 维度3: 中间件链（auth category）====
  describe('中间件链', () => {
    it("POST / 路由挂载了 authenticate 中间件", () => {
      expect(routeSrc).toContain('authenticate');
    });

    it("GET /:id 路由挂载了 authenticate 中间件", () => {
      const authenticateCount = (routeSrc.match(/authenticate/g) || []).length;
      expect(authenticateCount).toBeGreaterThanOrEqual(2);
    });
  });

  // ==== 维度4: 错误码映射（error category）====
  describe('错误码映射', () => {
    it('controller 包含所有契约错误码', () => {
      const codes = ['DUPLICATE_REFUND', 'AMOUNT_EXCEEDS_PAID', 'REFUND_NOT_FOUND'];
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
      // POST /refunds
      expect(frontSrc).toContain("'/refunds'");
      expect(frontSrc).toContain("method: 'post'");
      // GET /refunds/:id
      expect(frontSrc).toContain('/refunds/');
      expect(frontSrc).toContain("method: 'get'");
    });
  });

  // ==== 边界条件 ====
  describe('边界条件', () => {
    it('applyRefund 校验退款金额不能超过实付金额 → 422', () => {
      expect(ctrlSrc).toContain('退款金额不能超过实付金额');
      expect(ctrlSrc).toContain('422');
    });

    it('重复申请校验返回 DUPLICATE_REFUND', () => {
      expect(ctrlSrc).toContain('DUPLICATE_REFUND');
    });
  });
});
