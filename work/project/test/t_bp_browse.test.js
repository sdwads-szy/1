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
const productService = require('../services/productService');

describe('t_bp_browse', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ═══════════════════════════════════════════════════
  // correct — 商品搜索：正常搜索
  // ═══════════════════════════════════════════════════
  describe('correct — 商品搜索：正常搜索', () => {
    let result;

    beforeEach(async () => {
      // Step 1: SELECT COUNT(1) FROM spu ...
      mockQuery.mockResolvedValueOnce([{ total: 2 }]);
      // Step 2: SELECT ... FROM spu JOIN shops LEFT JOIN sku ...
      mockQuery.mockResolvedValueOnce([
        { id: 1, name: '蓝牙耳机Pro', default_image: '/img/p1.jpg', sales: 500, shop_id: 10, shop_name: '数码旗舰店', min_price: 199.00 },
        { id: 2, name: '蓝牙耳机Lite', default_image: '/img/p2.jpg', sales: 300, shop_id: 10, shop_name: '数码旗舰店', min_price: 149.00 }
      ]);

      result = await productService.browseProducts('蓝牙耳机', 1, 'sales', 1, 20);
    });

    it('步骤1: COUNT 查询获取总数', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        1,
        expect.stringContaining('COUNT'),
        expect.any(Array)
      );
    });

    it('步骤2: JOIN 查询获取商品+店铺+最低价', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        2,
        expect.stringContaining('FROM spu'),
        expect.any(Array)
      );
    });

    it('返回值 list 包含聚合后的商品数据', () => {
      expect(result.list).toBeInstanceOf(Array);
      expect(result.list.length).toBe(2);
      expect(result.list[0]).toMatchObject({
        id: expect.any(Number),
        name: expect.any(String),
        default_image: expect.any(String),
        sales: expect.any(Number),
        shop_name: expect.any(String),
        min_price: expect.any(Number),
      });
    });

    it('total 和分页参数正确', () => {
      expect(result.total).toBe(2);
      expect(result.page).toBe(1);
      expect(result.pageSize).toBe(20);
    });

    it('不涉及事务，commit/rollback 均未调用', () => {
      expect(mockCommit).not.toHaveBeenCalled();
      expect(mockRollback).not.toHaveBeenCalled();
      expect(mockBeginTransaction).not.toHaveBeenCalled();
    });
  });

  // ═══════════════════════════════════════════════════
  // boundary — 商品搜索：空关键词（默认全量）
  // ═══════════════════════════════════════════════════
  describe('boundary — 商品搜索：空关键词（默认全量）', () => {
    let result;

    beforeEach(async () => {
      // Step 1: COUNT
      mockQuery.mockResolvedValueOnce([{ total: 2 }]);
      // Step 2: JOIN
      mockQuery.mockResolvedValueOnce([
        { id: 1, name: '蓝牙耳机Pro', default_image: '/img/p1.jpg', sales: 500, shop_id: 10, shop_name: '数码旗舰店', min_price: 199.00 },
        { id: 3, name: '运动耳机', default_image: '/img/p3.jpg', sales: 800, shop_id: 20, shop_name: '运动装备店', min_price: 299.00 }
      ]);

      result = await productService.browseProducts('', null, 'default', 1, 20);
    });

    it('空关键词不报错，正常返回结果', () => {
      expect(result).toBeDefined();
      expect(result.list).toBeInstanceOf(Array);
      expect(result.list.length).toBe(2);
    });

    it('执行 2 次 DB 查询：COUNT + JOIN', () => {
      expect(mockQuery).toHaveBeenCalledTimes(2);
      expect(mockQuery).toHaveBeenNthCalledWith(1, expect.stringContaining('COUNT'), expect.any(Array));
      expect(mockQuery).toHaveBeenNthCalledWith(2, expect.stringContaining('FROM spu'), expect.any(Array));
    });

    it('返回正确的 total', () => {
      expect(result.total).toBe(2);
    });
  });

  // ═══════════════════════════════════════════════════
  // error — 商品搜索：关键词超长（>128）
  // ═══════════════════════════════════════════════════
  describe('error — 商品搜索：关键词超长（>128）', () => {
    it('q 长度超过 128 应抛出 INVALID_KEYWORD_LENGTH', async () => {
      const longQ = 'x'.repeat(129);
      await expect(productService.browseProducts(longQ, null, 'default', 1, 20))
        .rejects.toThrow('INVALID_KEYWORD_LENGTH');
    });

    it('超长关键词不应执行任何 DB 查询', async () => {
      const longQ = 'x'.repeat(129);
      try { await productService.browseProducts(longQ, null, 'default', 1, 20); } catch (_) {}
      expect(mockQuery).not.toHaveBeenCalled();
    });
  });

  // ═══════════════════════════════════════════════════
  // error — 商品搜索：ES 不可用降级 MySQL LIKE
  // ═══════════════════════════════════════════════════
  describe('error — 商品搜索：ES 不可用降级 MySQL LIKE', () => {
    let result;

    beforeEach(async () => {
      // ES 降级后走 MySQL LIKE → COUNT + JOIN 两步
      mockQuery.mockResolvedValueOnce([{ total: 1 }]);
      mockQuery.mockResolvedValueOnce([
        { id: 1, name: '蓝牙耳机Pro', default_image: '/img/p1.jpg', sales: 500, shop_id: 10, shop_name: '数码旗舰店', min_price: 199.00 }
      ]);

      result = await productService.browseProducts('蓝牙耳机', 1, 'sales', 1, 20);
    });

    it('降级后 DB 查询正常执行，不抛异常', () => {
      expect(result).toBeDefined();
      expect(result.list).toBeInstanceOf(Array);
      expect(result.list.length).toBe(1);
    });

    it('执行 2 次 DB 查询：COUNT + JOIN（降级路径走 LIKE）', () => {
      expect(mockQuery).toHaveBeenCalledTimes(2);
      expect(mockQuery).toHaveBeenNthCalledWith(1, expect.stringContaining('COUNT'), expect.any(Array));
      expect(mockQuery).toHaveBeenNthCalledWith(2, expect.stringContaining('FROM spu'), expect.any(Array));
    });

    it('返回正确的 total', () => {
      expect(result.total).toBe(1);
    });
  });

  // ═══════════════════════════════════════════════════
  // boundary — 商品搜索：分页越界
  // ═══════════════════════════════════════════════════
  describe('boundary — 商品搜索：分页越界', () => {
    let result;

    beforeEach(async () => {
      // Step 1: COUNT 返回实际总数
      mockQuery.mockResolvedValueOnce([{ total: 0 }]);
      // Step 2: JOIN 查询 — LIMIT/OFFSET 超出返回空
      mockQuery.mockResolvedValueOnce([]);

      result = await productService.browseProducts('蓝牙耳机', 1, 'sales', 99999, 20);
    });

    it('返回空 list，不抛异常', () => {
      expect(result).toBeDefined();
      expect(result.list).toEqual([]);
    });

    it('total 反映实际总数', () => {
      expect(result.total).toBe(0);
    });

    it('执行 2 次 DB 查询：COUNT + JOIN', () => {
      expect(mockQuery).toHaveBeenCalledTimes(2);
      expect(mockQuery).toHaveBeenNthCalledWith(1, expect.stringContaining('COUNT'), expect.any(Array));
      expect(mockQuery).toHaveBeenNthCalledWith(2, expect.stringContaining('FROM spu'), expect.any(Array));
    });
  });
});
