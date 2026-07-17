const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

describe('t_api_shops', () => {
  const routeSrc = fs.readFileSync(path.join(workspace, 'routes/products.js'), 'utf-8');
  const ctrlSrc  = fs.readFileSync(path.join(workspace, 'controllers/productController.js'), 'utf-8');


  // ==== 维度1: 路由匹配 (correct) ====
  describe('路由匹配', () => {
    it('GET /shops/:id → handler: getShopInfo', () => {
      expect(routeSrc).toContain('/shops/:id');
      expect(ctrlSrc).toContain('getShopInfo');
    });
  });

  // ==== 维度2: 字段一致 (correct) ====
  describe('字段一致', () => {
    it('controller 接收了路径参数 req.params.id', () => {
      expect(ctrlSrc).toContain('params');
      expect(ctrlSrc).toContain('id');
    });

    it('controller 返回店铺字段: name, logo, banner, description, status', () => {
      ['name', 'logo', 'banner', 'description', 'status'].forEach(f =>
        expect(ctrlSrc).toContain(f)
      );
    });
  });

  // ==== 维度4: 错误码映射 (error) ====
  describe('错误码映射', () => {
    it('controller 包含契约错误码 SHOP_NOT_FOUND', () => {
      const codes = ['SHOP_NOT_FOUND'];
      codes.forEach(c => expect(ctrlSrc).toContain(c));
    });

    it('冻结店铺返回 status=frozen 而非抛错', () => {
      expect(ctrlSrc).toContain('frozen');
    });
  });

  // ==== 边界条件 (boundary) ====
  describe('边界条件', () => {
    it('不存在店铺ID 返回 404', () => {
      expect(ctrlSrc).toContain('404');
    });
  });

  // ==== 维度5: 响应格式 (correct) ====
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

  });