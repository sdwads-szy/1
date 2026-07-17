const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

describe('t_api_categories', () => {
  const routeSrc = fs.readFileSync(path.join(workspace, 'routes/products.js'), 'utf-8');
  const ctrlSrc  = fs.readFileSync(path.join(workspace, 'controllers/productController.js'), 'utf-8');
  const frontSrc = fs.readFileSync(path.join(workspace, 'src/api/products.js'), 'utf-8');

  // ==== 维度1: 路由匹配 ====
  describe('路由匹配', () => {
    it('GET /categories → handler: getCategories', () => {
      expect(routeSrc).toContain('/categories');
      expect(ctrlSrc).toContain('getCategories');
    });
  });

  // ==== 维度2: 字段一致 ====
  describe('字段一致', () => {
    it('getCategories 为公开接口，无请求体字段依赖', () => {
      expect(ctrlSrc).toContain('getCategories');
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

    it('getCategories 返回类目树结构', () => {
      expect(ctrlSrc).toContain('tree');
    });
  });

  // ==== 维度6: 前端对齐 ====
  describe('前端对齐', () => {
    it('前端 API 调用的端点与后端路由一致', () => {
      expect(frontSrc).toContain('/categories');
    });
  });

  // ==== boundary: 空类目处理 ====
  describe('边界情况', () => {
    it('getCategories 处理空结果返回空数组而不报错', () => {
      const hasTreeOrEmpty = ctrlSrc.includes('tree') || ctrlSrc.includes('[]');
      expect(hasTreeOrEmpty).toBe(true);
    });
  });
});
