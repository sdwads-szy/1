const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

describe('t_api_cart', () => {
  const routeSrc = fs.readFileSync(path.join(workspace, 'routes/cart.js'), 'utf-8');
  const ctrlSrc  = fs.readFileSync(path.join(workspace, 'controllers/cartController.js'), 'utf-8');
  const frontSrc = fs.readFileSync(path.join(workspace, 'src/api/cart.js'), 'utf-8');

  // ==== 维度1: 路由匹配 ====
  describe('路由匹配', () => {
    it('POST / → handler: addToCart', () => {
      expect(routeSrc).toContain('addToCart');
      expect(ctrlSrc).toContain('addToCart');
    });

    it('GET / → handler: getCart', () => {
      expect(routeSrc).toContain('getCart');
      expect(ctrlSrc).toContain('getCart');
    });

    it('PUT /:id → handler: updateCartItem', () => {
      expect(routeSrc).toContain('updateCartItem');
      expect(ctrlSrc).toContain('updateCartItem');
    });

    it('DELETE /:id → handler: removeCartItem', () => {
      expect(routeSrc).toContain('removeCartItem');
      expect(ctrlSrc).toContain('removeCartItem');
    });

    it('POST /select → handler: selectForCheckout', () => {
      expect(routeSrc).toContain('/select');
      expect(ctrlSrc).toContain('selectForCheckout');
    });



    it('PATCH /batch-check → handler: batchCheck', () => {
      expect(routeSrc).toContain('batchCheck');
      expect(ctrlSrc).toContain('batchCheck');
    });
  });

  // ==== 维度2: 字段一致 ====
  describe('字段一致', () => {
    it('addToCart controller 接收了预期字段: skuId, quantity, shopId', () => {
      ['skuId', 'quantity', 'shopId'].forEach(f => expect(ctrlSrc).toContain(f));
    });

    it('updateCartItem controller 接收了预期字段: id, quantity', () => {
      ['id', 'quantity'].forEach(f => expect(ctrlSrc).toContain(f));
    });

    it('removeCartItem controller 接收了预期字段: id', () => {
      expect(ctrlSrc).toContain('id');
    });

    it('selectForCheckout controller 接收了预期字段: cartItemIds', () => {
      expect(ctrlSrc).toContain('cartItemIds');
    });

    it('batchCheck controller 接收了预期字段: cartItemIds, checked', () => {
      ['cartItemIds', 'checked'].forEach(f => expect(ctrlSrc).toContain(f));
    });
  });

  // ==== 维度3: 中间件链（auth category）====
  describe('中间件链', () => {
    it('所有 cart 路由挂载 authenticate 中间件', () => {
      expect(routeSrc).toContain('authenticate');
    });
  });

  // ==== 维度4: 错误码映射（error category）====
  describe('错误码映射', () => {
    it('controller 包含所有契约错误码', () => {
      const codes = ['STOCK_INSUFFICIENT', 'UNAUTHORIZED'];
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
      const endpoints = ['/cart', '/cart/select', '/cart/batch-check'];
      endpoints.forEach(ep => expect(frontSrc).toContain(ep));
    });
  });
});
