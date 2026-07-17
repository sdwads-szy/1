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
mockBeginTransaction.mockResolvedValue(mockConnection);


// ==== Require ====
const paymentService = require('../services/paymentService');

describe('t_bp_pay_status', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── Scenario 1: correct — 支付成功 ──
  describe('correct — 支付成功', () => {
    let result;

    beforeEach(async () => {
      mockQuery
        .mockResolvedValueOnce([{ id: 1, user_id: 1, status: 'pending' }])
        .mockResolvedValueOnce([{ id: 100, transaction_no: 'TXN-001', status: 'success' }])
        .mockResolvedValueOnce({ affectedRows: 1 })
        .mockResolvedValueOnce({ affectedRows: 1 });

      result = await paymentService.getPaymentStatus(1, 'ORD-SEED-00000001');
    });

    it('步骤1: 查询 orders 校验归属', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        1,
        expect.stringContaining('SELECT'),
        expect.any(Array)
      );
    });

    it('步骤2: 查询 payments 获取状态', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        2,
        expect.stringContaining('SELECT'),
        expect.any(Array)
      );
    });

    it('步骤3: 更新 payments 状态', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        3,
        expect.stringContaining('UPDATE'),
        expect.any(Array)
      );
    });
    it('步骤4: 更新 orders 状态', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        4,
        expect.stringContaining('UPDATE'),
        expect.any(Array)
      );
    });



    it('返回值 status 为 success', () => {
      expect(result).toMatchObject({ status: 'success' });
    });
  });

  // ── Scenario 2: error — 订单不属于当前用户 ──
  describe('error — 订单不属于当前用户', () => {
    it('FORBIDDEN 被抛出', async () => {
      mockQuery.mockResolvedValueOnce([{ id: 1, user_id: 1 }]);

      await expect(
        paymentService.getPaymentStatus(2, 'ORD-SEED-00000001')
      ).rejects.toThrow(/FORBIDDEN/i);
    });

    it('归属校验失败后不执行后续查询', async () => {
      mockQuery.mockResolvedValueOnce([{ id: 1, user_id: 1 }]);

      await expect(
        paymentService.getPaymentStatus(2, 'ORD-SEED-00000001')
      ).rejects.toThrow(/FORBIDDEN/i);

      expect(mockQuery).toHaveBeenCalledTimes(1);
    });
  });

  // ── Scenario 3: error — 订单不存在 ──
  describe('error — 订单不存在', () => {
    it('ORDER_NOT_FOUND 被抛出', async () => {
      mockQuery.mockResolvedValueOnce([]);

      await expect(
        paymentService.getPaymentStatus(1, 'ORD-NONEXISTENT')
      ).rejects.toThrow(/ORDER_NOT_FOUND/i);
    });

    it('订单不存在时仅执行一次查询', async () => {
      mockQuery.mockResolvedValueOnce([]);

      await expect(
        paymentService.getPaymentStatus(1, 'ORD-NONEXISTENT')
      ).rejects.toThrow(/ORDER_NOT_FOUND/i);

      expect(mockQuery).toHaveBeenCalledTimes(1);
    });
  });

  // ── Scenario 4: correct — 支付处理中 ──
  describe('correct — 支付处理中', () => {
    let result;

    beforeEach(async () => {
      mockQuery
        .mockResolvedValueOnce([{ id: 2, user_id: 1, status: 'pending' }])
        .mockResolvedValueOnce([{ id: 101, transaction_no: 'TXN-002', status: 'pending' }])
        .mockResolvedValueOnce({ affectedRows: 1 })
        .mockResolvedValueOnce({ affectedRows: 1 })
        .mockResolvedValueOnce({ affectedRows: 1 });

      result = await paymentService.getPaymentStatus(1, 'ORD-PENDING-PAY');
    });

    it('步骤1: 归属校验通过', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        1,
        expect.stringContaining('SELECT'),
        expect.any(Array)
      );
    });

    it('步骤2: 查询 payments 获取 pending 状态', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        2,
        expect.stringContaining('SELECT'),
        expect.any(Array)
      );
    });

    it('步骤3: 更新 payments 状态', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        3,
        expect.stringContaining('UPDATE'),
        expect.any(Array)
      );
    });
    it('步骤4: 更新子订单状态', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        4,
        expect.stringContaining('UPDATE'),
        expect.any(Array)
      );
    });

    it('步骤5: 更新订单状态', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        5,
        expect.stringContaining('UPDATE'),
        expect.any(Array)
      );
    });



    it('返回值 status 为 pending', () => {
      expect(result).toMatchObject({ status: 'pending' });
    });
  });
});
