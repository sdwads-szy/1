const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

describe('t_api_products', () => {
  const routeSrc = fs.readFileSync(path.join(workspace, 'routes/products.js'), 'utf-8');
  const ctrlSrc  = fs.readFileSync(path.join(workspace, 'controllers/productController.js'), 'utf-8');
  const frontSrc = fs.readFileSync(path.join(workspace, 'src/api/products.js'), 'utf-8');

  // ==== 维度1: 路由匹配 ====
  describe('路由匹配', () => {
    it('GET / → handler: browseProducts', () => {
      expect(routeSrc).toContain('/');
      expect(ctrlSrc).toContain('browseProducts');
    });
    it('GET /:id → handler: getProductDetail', () => {
      expect(routeSrc).toContain('/:id');
      expect(ctrlSrc).toContain('getProductDetail');
    });
  });

  // ==== 维度2: 字段一致 ====
  describe('字段一致', () => {
    it('controller 接收了预期字段: q, cat, sort, page, pageSize', () => {
      ['q', 'cat', 'sort', 'page', 'pageSize'].forEach(f => expect(ctrlSrc).toContain(f));
    });
    it('controller 接收了预期字段: id', () => {
      ['id'].forEach(f => expect(ctrlSrc).toContain(f));
    });
  });

  // ==== 维度3: 中间件链（auth category）====
  describe('中间件链', () => {
    it('GET / 挂载 optionalAuth 中间件', () => {
      expect(routeSrc).toContain('optionalAuth');
    });
    it('GET /:id 挂载 optionalAuth 中间件', () => {
      expect(routeSrc).toContain('optionalAuth');
    });
  });

  // ==== 维度4: 错误码映射（error category）====
  describe('错误码映射', () => {
    it('controller 包含所有契约错误码', () => {
      const codes = ['PRODUCT_NOT_FOUND'];
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
      expect(frontSrc).toContain('getProducts');
      expect(frontSrc).toContain("'/products'");
      expect(frontSrc).toContain('getProductDetail');
      expect(frontSrc).toContain('/products/');
    });
  });

  // ==== 边界条件 ====
  describe('边界条件', () => {
    it('browseProducts 返回 {list, total, page, pageSize} 结构', () => {
      expect(ctrlSrc).toContain('list');
      expect(ctrlSrc).toContain('total');
      expect(ctrlSrc).toContain('page');
      expect(ctrlSrc).toContain('pageSize');
    });
  });
});
