/** @jest-environment node */

// ==== Mock DB ====
jest.mock('../config/db', () => {
  const mockQuery = jest.fn();
  const mockBeginTransaction = jest.fn();
  const mockCommit = jest.fn();
  const mockRollback = jest.fn();
  return {
    query: mockQuery,
    beginTransaction: mockBeginTransaction,
    commit: mockCommit,
    rollback: mockRollback,
    __mocks: { mockQuery, mockBeginTransaction, mockCommit, mockRollback }
  };
});

const db = require('../config/db');
const { mockQuery, mockBeginTransaction, mockCommit, mockRollback } = db.__mocks;

const mockConnection = {
  query: mockQuery,
  execute: mockQuery,
  commit: mockCommit,
  rollback: mockRollback,
};

// ==== Require ====
const service = require('../services/productService');

describe('t_bp_product_detail', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── correct: 商品详情正常查询 ──
  describe('correct — 商品详情正常查询', () => {
    let result;
    const spuRow = {
      id: 1,
      shop_id: 10,
      category_id: 5,
      name: '蓝牙耳机',
      description: '高品质无线蓝牙耳机',
      default_image: '/img/bt-headphone.jpg',
      status: 'listed',
      sales: 100,
      created_at: '2024-01-01T00:00:00.000Z'
    };
    const skuRows = [
      { id: 101, spu_id: 1, spec_name: '黑色', price: 99.99, image: '/img/bt-black.jpg' },
      { id: 102, spu_id: 1, spec_name: '白色', price: 109.99, image: '/img/bt-white.jpg' }
    ];
    const inventoryRows = [
      { sku_id: 101, stock: 50 },
      { sku_id: 102, stock: 30 }
    ];
    const imageRows = [
      { url: '/img/bt-1.jpg' },
      { url: '/img/bt-2.jpg' },
      { url: '/img/bt-3.jpg' }
    ];
    const shopRow = {
      id: 10,
      name: '数码旗舰店',
      logo: '/img/shop-logo.png',
      banner: '/img/shop-banner.png',
      description: '专业数码产品旗舰店',
      status: 'active'
    };

    beforeEach(async () => {
      mockQuery
        .mockResolvedValueOnce([spuRow])
        .mockResolvedValueOnce(skuRows)
        .mockResolvedValueOnce(inventoryRows)
        .mockResolvedValueOnce(imageRows)
        .mockResolvedValueOnce([shopRow]);

      result = await service.getProductDetail(1);
    });

    it('步骤1: 查询 SPU（含 status=listed 过滤）', () => {
    it('步骤1: 查询 SPU（含 status=listed 过滤）', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        1,
        expect.any(String),
        [1, 'listed']
      );
    });
    });

    it('步骤2: 查询 SKU 列表', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        2,
        expect.stringContaining('sku'),
        [1]
      );
    });

    it('步骤3: 查询库存（SKU IN + shop_id）', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        3,
        expect.stringContaining('inventories'),
        expect.any(Array)
      );
    });

    it('步骤4: 查询轮播图', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        4,
        expect.stringContaining('product_images'),
        [1]
      );
    });

    it('步骤5: 查询店铺信息', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        5,
        expect.stringContaining('shops'),
        [10]
      );
    });

    it('返回值包含 spu、skus、images、shop', () => {
      expect(result).toMatchObject({
        spu: expect.any(Object),
        skus: expect.any(Array),
        images: expect.any(Array),
        shop: expect.any(Object)
      });
    });

    it('spu 字段完整', () => {
      expect(result.spu).toMatchObject({
        id: 1,
        name: '蓝牙耳机',
        description: '高品质无线蓝牙耳机',
        default_image: '/img/bt-headphone.jpg',
        sales: 100
      });
    });

    it('SKU 已合并库存 stock 字段', () => {
      expect(result.skus).toHaveLength(2);
      expect(result.skus[0]).toMatchObject({
        id: 101,
        spec_name: '黑色',
        price: 99.99,
        stock: 50
      });
      expect(result.skus[1]).toMatchObject({
        id: 102,
        spec_name: '白色',
        price: 109.99,
        stock: 30
      });
    });

    it('images 为 url 数组', () => {
      expect(result.images).toHaveLength(3);
      expect(result.images[0]).toMatchObject({ url: '/img/bt-1.jpg' });
    });

    it('shop 字段完整', () => {
      expect(result.shop).toMatchObject({
        name: '数码旗舰店',
        logo: '/img/shop-logo.png',
        status: 'active'
      });
    });

    it('只读操作，无事务调用', () => {
      expect(mockBeginTransaction).not.toHaveBeenCalled();
      expect(mockCommit).not.toHaveBeenCalled();
      expect(mockRollback).not.toHaveBeenCalled();
    });
  });

  // ── error: 商品不存在 ──
  describe('error — 商品不存在', () => {
    it('SPU 查询返回空 → 抛出 PRODUCT_NOT_FOUND', async () => {
      mockQuery.mockResolvedValueOnce([]);

      await expect(
        service.getProductDetail(99999)
      ).rejects.toThrow(/PRODUCT_NOT_FOUND/i);
    });

    it('SPU 未找到后不再查询后续表', async () => {
      mockQuery.mockResolvedValueOnce([]);

      try {
        await service.getProductDetail(99999);
      } catch (_) {
        // expected
      }

      expect(mockQuery).toHaveBeenCalledTimes(1);
    });
  });

  // ── error: 已下架商品 ──
  describe('error — 已下架商品', () => {
    it('status=delisted 被 WHERE 过滤 → 抛出 PRODUCT_NOT_FOUND', async () => {
      // WHERE id=? AND status='listed' 过滤掉 delisted 行，返回空
      mockQuery.mockResolvedValueOnce([]);

      await expect(
        service.getProductDetail(5)
      ).rejects.toThrow(/PRODUCT_NOT_FOUND/i);
    });

    it('下架商品同样不触发后续查询', async () => {
      mockQuery.mockResolvedValueOnce([]);

      try {
        await service.getProductDetail(5);
      } catch (_) {
        // expected
      }

      expect(mockQuery).toHaveBeenCalledTimes(1);
    });
  });

  // ── boundary: productId 非正整数 ──
  describe('boundary — productId 非正整数', () => {
    it('productId=0 → 抛出 INVALID_PRODUCT_ID', async () => {
      await expect(
        service.getProductDetail(0)
      ).rejects.toThrow(/INVALID_PRODUCT_ID/i);
    });

    it('productId=-1 → 抛出 INVALID_PRODUCT_ID', async () => {
      await expect(
        service.getProductDetail(-1)
      ).rejects.toThrow(/INVALID_PRODUCT_ID/i);
    });

    it('productId=NaN → 抛出 INVALID_PRODUCT_ID', async () => {
      await expect(
        service.getProductDetail(NaN)
      ).rejects.toThrow(/INVALID_PRODUCT_ID/i);
    });

    it('校验失败不触发任何 DB 查询', async () => {
      try {
        await service.getProductDetail(0);
      } catch (_) {
        // expected
      }
      expect(mockQuery).not.toHaveBeenCalled();
    });
  });

});
