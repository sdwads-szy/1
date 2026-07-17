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

// ==== Require ====
const service = require('../services/adminDashboardService');

describe('t_bp_admin_dashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── correct: 平台看板正常查询 ──
  describe('correct — 平台看板正常查询', () => {
    let result;

    const todayRow = {
      gmv: 18950.0,
      order_count: 42,
      paid_order_count: 38,
      refund_rate: 0.023,
      commission: 948.5
    };

    const trendRows = [
      { stat_date: '2025-01-08', gmv: 12000.0, order_count: 30, refund_rate: 0.018 },
      { stat_date: '2025-01-09', gmv: 13500.0, order_count: 33, refund_rate: 0.02 },
      { stat_date: '2025-01-10', gmv: 14100.0, order_count: 36, refund_rate: 0.021 },
      { stat_date: '2025-01-11', gmv: 12800.0, order_count: 31, refund_rate: 0.019 },
      { stat_date: '2025-01-12', gmv: 15500.0, order_count: 38, refund_rate: 0.022 },
      { stat_date: '2025-01-13', gmv: 16200.0, order_count: 40, refund_rate: 0.024 },
      { stat_date: '2025-01-14', gmv: 18950.0, order_count: 42, refund_rate: 0.023 }
    ];

    beforeEach(async () => {
      mockQuery
        .mockResolvedValueOnce([todayRow])
        .mockResolvedValueOnce(trendRows);

      result = await service.getAdminDashboard();
    });

    it('步骤1: 查询今日平台数据 — platform_daily_stats WHERE stat_date=CURDATE()', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        1,
        expect.stringContaining('platform_daily_stats')
      );
    });

    it('步骤2: 查询近7天趋势 — platform_daily_stats ORDER BY stat_date', () => {
      expect(mockQuery).toHaveBeenNthCalledWith(
        2,
        expect.stringContaining('platform_daily_stats')
      );
    });

    it('返回值包含今日看板字段，与真理 t_api_admin_dashboard 一致', () => {
      expect(result).toMatchObject({
        todayGmv: expect.any(Number),
        todayOrders: expect.any(Number),
        todayPaidOrders: expect.any(Number),
        refundRate: expect.any(Number),
        trend: expect.any(Array)
      });
    });

    it('返回值包含 trend 数组，长度为近7天记录数', () => {
      expect(result).toHaveProperty('trend');
      expect(Array.isArray(result.trend)).toBe(true);
      expect(result.trend.length).toBe(trendRows.length);
      expect(result.trend[0]).toMatchObject({
        statDate: expect.any(String),
        gmv: expect.any(Number),
        orderCount: expect.any(Number),
        refundRate: expect.any(Number)
      });
    });

    it('只读查询不触发事务', () => {
      expect(mockBeginTransaction).not.toHaveBeenCalled();
      expect(mockCommit).not.toHaveBeenCalled();
      expect(mockRollback).not.toHaveBeenCalled();
    });
  });

  // ── error 场景「非管理员调用」属于 middleware/controller 层，跳过 ──
  // requireRole(['admin']) 在 controller 层执行，不在 service 单测范围
});
