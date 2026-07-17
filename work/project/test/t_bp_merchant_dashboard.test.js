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
const service = require('../services/merchantDashboardService');

describe('t_bp_merchant_dashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── correct: 商家看板正常查询 ──
  describe('correct — 商家看板正常查询', () => {
    let result;

    const todayRow = {
      gmv: '8200.00',
      order_count: 15,
      stat_date: '2025-01-15',
      merchant_id: 1,
    };

    const trendRows = [
      { stat_date: '2025-01-09', gmv: '4100.00', order_count: 8, merchant_id: 1 },
      { stat_date: '2025-01-10', gmv: '5200.00', order_count: 10, merchant_id: 1 },
      { stat_date: '2025-01-11', gmv: '3800.00', order_count: 7, merchant_id: 1 },
    ];

    beforeEach(async () => {
      mockQuery
        .mockResolvedValueOnce([todayRow])
        .mockResolvedValueOnce(trendRows);

      result = await service.getMerchantDashboard(1);
    });

    it('步骤1: 查询今日GMV和订单数', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        1,
        expect.stringContaining('merchant_daily_stats'),
        expect.arrayContaining([1])
      );
    });

    it('步骤2: 查询近7天趋势数据', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        2,
        expect.stringContaining('merchant_daily_stats'),
        expect.arrayContaining([1])
      );
    });

    it('返回值包含今日GMV和订单数', () => {
      expect(result).toBeDefined();
      expect(typeof result).toBe('object');
      expect(result).toHaveProperty('todayGmv');
      expect(result).toHaveProperty('todayOrders');
    });

    it('返回值包含近7天趋势数组', () => {
      expect(result).toHaveProperty('trend');
      expect(Array.isArray(result.trend)).toBe(true);
      expect(result.trend.length).toBeGreaterThan(0);
    });
  });

  // ── boundary: 新商家无数据 ──
  describe('boundary — 新商家无数据', () => {
    it('查询返回空结果时不报错', async () => {
      mockQuery
        .mockResolvedValueOnce([])
        .mockResolvedValueOnce([]);

      const result = await service.getMerchantDashboard(999);

      expect(result).toBeDefined();
      expect(typeof result).toBe('object');
      expect(result).toHaveProperty('todayGmv');
      expect(result).toHaveProperty('todayOrders');
      expect(result).toHaveProperty('trend');
      expect(Array.isArray(result.trend)).toBe(true);
      expect(result.trend).toHaveLength(0);
    });

    it('两次查询均使用正确的 merchantId', async () => {
      mockQuery
        .mockResolvedValueOnce([])
        .mockResolvedValueOnce([]);

      await service.getMerchantDashboard(999);

      expect(mockQuery).toHaveBeenNthCalledWith(
        1,
        expect.stringContaining('merchant_daily_stats'),
        expect.arrayContaining([999])
      );
      expect(mockQuery).toHaveBeenNthCalledWith(
        2,
        expect.stringContaining('merchant_daily_stats'),
        expect.arrayContaining([999])
      );
    });
  });
});
