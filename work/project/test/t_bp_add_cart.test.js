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
const service = require('../services/cartService');

describe('t_bp_add_cart', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ════════════════════════════════════════════
  // Scenario 1: 正常加购（新SKU，购物车无同款）
  // ════════════════════════════════════════════
  describe('correct — 正常加购（新SKU）', () => {
    let result;

    beforeEach(async () => {
      mockBeginTransaction.mockResolvedValue(mockConnection);

      // mysql2: connection.execute() returns [rows, fields]
      // Step 1: SELECT sku — 验证 SKU 存在
      mockQuery.mockResolvedValueOnce([
        [{ id: 1, spu_id: 100, spec_name: 'Red/XL', price: 99.0, image: 'sku1.jpg' }],
        []
      ]);
      // Step 2: SELECT spu — 验证 SPU 已上架 (status='listed')
      mockQuery.mockResolvedValueOnce([
        [{ id: 100, name: 'T-Shirt', status: 'listed', default_image: 'spu1.jpg', shop_id: 1 }],
        []
      ]);
      // Step 3: SELECT shops — 验证店铺营业中 (status='open')
      mockQuery.mockResolvedValueOnce([
        [{ id: 1, status: 'open' }],
        []
      ]);
      // Step 4: SELECT inventories — stock - frozen_stock >= quantity
      mockQuery.mockResolvedValueOnce([
        [{ stock: 500, frozen_stock: 0 }],
        []
      ]);
      // Step 5: SELECT cart_items — 无已有记录
      mockQuery.mockResolvedValueOnce([[], []]);
      // Step 6: INSERT cart_items
      mockQuery.mockResolvedValueOnce([{ affectedRows: 1, insertId: 100 }, []]);

      result = await service.addToCart(1, 1, 2, 1);
    });

    it('步骤1: 查询 SKU 信息', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        1,
        expect.stringContaining('sku'),
        expect.any(Array)
      );
    });

    it('步骤2: 查询 SPU 信息（含上架状态校验）', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        2,
        expect.stringContaining('spu'),
        expect.any(Array)
      );
    });

    it('步骤3: 查询店铺营业状态', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        3,
        expect.stringContaining('shops'),
        expect.any(Array)
      );
    });

    it('步骤4: 查询库存（stock - frozen_stock >= quantity）', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        4,
        expect.stringContaining('inventories'),
        expect.any(Array)
      );
    });

    it('步骤5: 查询已有购物车项 — 无记录', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        5,
        expect.stringContaining('cart_items'),
        expect.any(Array)
      );
    });

    it('步骤6: INSERT 新购物车项', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        6,
        expect.stringContaining('INSERT'),
        expect.any(Array)
      );
    });

    it('COMMIT 被调用，rollback 未调用', () => {
      expect(mockCommit).toHaveBeenCalled();
      expect(mockRollback).not.toHaveBeenCalled();
    });

    it('返回值匹配：cartItem={id:100, skuId:1, shopId:1, quantity:2, checked:true}', () => {
      expect(result).toMatchObject({
        cartItem: {
          id: 100,
          skuId: 1,
          shopId: 1,
          quantity: 2,
          checked: true,
        },
      });
    });
  });

  // ════════════════════════════════════════════
  // Scenario 2: 库存不足 → STOCK_INSUFFICIENT
  // ════════════════════════════════════════════
  describe('error — 库存不足', () => {
    it('STOCK_INSUFFICIENT 被抛出 + 事务回滚 + 断点前步骤已执行', async () => {
      mockBeginTransaction.mockResolvedValue(mockConnection);

      // Steps 1-3: 前置校验全部通过
      mockQuery.mockResolvedValueOnce([
        [{ id: 1, spu_id: 100, spec_name: 'Red/XL', price: 99.0, image: 'sku1.jpg' }],
        []
      ]);
      mockQuery.mockResolvedValueOnce([
        [{ id: 100, name: 'T-Shirt', status: 'listed', default_image: 'spu1.jpg', shop_id: 1 }],
        []
      ]);
      mockQuery.mockResolvedValueOnce([
        [{ id: 1, status: 'open' }],
        []
      ]);
      // Step 4: 库存不足 — stock=500, 需求量=99999
      mockQuery.mockResolvedValueOnce([
        [{ stock: 500, frozen_stock: 0 }],
        []
      ]);
      // Step 5: SELECT cart_items — 无已有记录（库存检查在 SELECT 之后）
      mockQuery.mockResolvedValueOnce([[], []]);

      await expect(
        service.addToCart(1, 1, 99999, 1)
      ).rejects.toThrow(/STOCK_INSUFFICIENT/i);

      // 断点前 5 步已执行（sku, spu, shops, inventories, cart_items）
      expect(mockQuery).toHaveBeenCalledTimes(5);
      // 事务回滚（catch 块中调用）
      expect(mockRollback).toHaveBeenCalled();
      expect(mockCommit).not.toHaveBeenCalled();
    });
  });

  // ════════════════════════════════════════════
  // Scenario 3: 已存在同SKU购物车项 → 累加
  // ════════════════════════════════════════════
  describe('correct — 已存在同SKU购物车项（累加）', () => {
    let result;

    beforeEach(async () => {
      mockBeginTransaction.mockResolvedValue(mockConnection);

      // Steps 1-4: 同 Scenario 1 的前置校验
      mockQuery.mockResolvedValueOnce([
        [{ id: 1, spu_id: 100, spec_name: 'Red/XL', price: 99.0, image: 'sku1.jpg' }],
        []
      ]);
      mockQuery.mockResolvedValueOnce([
        [{ id: 100, name: 'T-Shirt', status: 'listed', default_image: 'spu1.jpg', shop_id: 1 }],
        []
      ]);
      mockQuery.mockResolvedValueOnce([
        [{ id: 1, status: 'open' }],
        []
      ]);
      mockQuery.mockResolvedValueOnce([
        [{ stock: 500, frozen_stock: 0 }],
        []
      ]);
      // Step 5: 已有购物车记录 — id=50, quantity=2
      mockQuery.mockResolvedValueOnce([
        [{ id: 50, quantity: 2 }],
        []
      ]);
      // Step 6: UPDATE 累加（非 INSERT）
      mockQuery.mockResolvedValueOnce([{ affectedRows: 1 }, []]);

      result = await service.addToCart(1, 1, 1, 1);
    });

    it('步骤5: 查询到已有购物车项（id=50, quantity=2）', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        5,
        expect.stringContaining('cart_items'),
        expect.any(Array)
      );
    });

    it('步骤6: UPDATE 累加（非 INSERT）', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        6,
        expect.stringContaining('UPDATE'),
        expect.any(Array)
      );
    });

    it('COMMIT 被调用，rollback 未调用', () => {
      expect(mockCommit).toHaveBeenCalled();
      expect(mockRollback).not.toHaveBeenCalled();
    });

    it('返回值 quantity=3（累加 2+1，非覆盖）', () => {
      expect(result).toMatchObject({
        cartItem: {
          id: 50,
          skuId: 1,
          shopId: 1,
          quantity: 3,
          checked: true,
        },
      });
    });
  });
});
