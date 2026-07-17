# 项目二：星链商城 — Agent 系统自动生成的产物

> 由 [Agent 多智能体代码生成系统](../README.md) 全自动生成，未经过人工编写或修改。

## 需求输入

```
设计一个 B2B2C 多商户线上商城
```

## 生成流程

| 阶段 | 产物 | 耗时 |
|------|------|------|
| 需求分析 | PM + 10 角色 5 轮讨论 → 27KB PRD | ~30min |
| 架构设计 | 209 契约 + 81 工程任务 | ~20min |
| 代码生成 | 5 类工程师分层并发 → 完整源码 | ~2h |
| 测试架构 | 173 个分层测试任务 | ~30min |
| ABCD 修复 | 写测试→诊断→修复→验证，多轮收敛 | ~1h |

## 生成物规模

| 类型 | 数量 | 说明 |
|------|------|------|
| PRD 文档 | 1 份 (27KB) | 7 章完整需求文档 |
| 架构契约 | 209 个 | 7 类契约覆盖全栈 |
| 后端路由 | 23 个 | Express + @mount 注释 |
| 控制器 | 23 个 | 统一响应格式 + 错误码映射 |
| 业务服务 | 25 个 | 乐观锁 + 事务管理 + 指数退避重试 |
| SQL 表 | 25 张 + 26 种子 | DDL 与契约逐字段一致 |
| Vue 页面 | 31 个 | 路由懒加载 + 角色守卫 + Token 过期处理 |
| API 模块 | 24 个 | 端点与后端路由对齐 |
| Pinia Store | 2 个 | 购物车 + 用户状态 |
| 测试文件 | 57 个 | 含 94 断言的 DB-API 测试 |
| UI 设计文档 | 10 个 | 含完整设计令牌系统 + 暗色模式 |

## 技术栈

| 层 | 技术 |
|------|------|
| 后端 | Node.js + Express + mysql2 |
| 数据库 | MySQL（25 张表） |
| 认证 | JWT（jsonwebtoken + bcrypt） |
| 前端 | Vue 3 + Vite + Pinia + Element Plus |
| 测试 | Jest + supertest |

## 功能覆盖

| 模块 | 消费者端 | 商家端 | 平台端 |
|------|:---:|:---:|:---:|
| 商品浏览 | 首页/搜索/分类/详情 | — | — |
| 商品管理 | — | 发布/编辑/下架 | 审核/上下架 |
| 购物车 | 添加/修改/勾选/结算 | — | — |
| 订单 | 下单/支付/物流跟踪/确认收货 | 发货/批量处理 | 全局查询/异常处理 |
| 用户 | 登录/注册/个人中心/地址 | — | — |
| 商家入驻 | — | 分步表单/资质上传 | 审核/通过/驳回 |
| 售后 | 申请退款/退货 | 审批/协商 | 仲裁/强制退款 |
| 钱包结算 | — | 余额/结算单/提现 | 审核/打款/追索 |
| 物流 | — | 录入单号/发货 | 物流商配置/监控 |
| 数据看板 | — | 经营数据/趋势图 | 平台 GMV/订单量/退款率 |

## 代码质量

### 后端

```javascript
// controllers/orderController.js — 8 种错误码精确映射
const errorMapping = {
  'MISSING_ADDRESS':  { status: 400, message: '请选择收货地址' },
  'EMPTY_CART':       { status: 400, message: '请选择商品' },
  'STOCK_INSUFFICIENT': { status: 422, message: `仅剩 ${e.availableStock} 件` },
  'SHOP_FROZEN':      { status: 422, message: '店铺已暂停营业' },
  // ...
};

// services/orderService.js — 乐观锁 + 指数退避
async function deductStock(conn, skuId, shopId, quantity) {
  for (let retry = 0; retry < 3; retry++) {
    const [result] = await conn.execute(
      'UPDATE inventories SET stock = stock - ?, version = version + 1
       WHERE sku_id = ? AND shop_id = ? AND version = ? AND stock >= ?',
      [quantity, skuId, shopId, version, quantity]
    );
    if (result.affectedRows > 0) return;
    await new Promise(r => setTimeout(r, Math.pow(2, retry) * 100));
  }
  throw new Error('INSUFFICIENT_STOCK');
}
```

### 测试

```javascript
// test/t_dbapi_order.test.js — 94 个断言
correct:  orders 表 8 个字段全部存在
correct:  sub_orders 表各字段
          ...
boundary: NOT NULL × 6, UNIQUE × 2, PRIMARY KEY × 3, FK × 4
boundary: status ENUM 含 7 个值 (pending/paid/shipped/...)
error:    假字段 xyz_not_a_column 不存在于任何表
error:    truth 声明 vs 实际 DDL 逐列对比
```

## 测试结果

| 层 | 任务 | 通过 | 通过率 |
|------|:---:|:---:|:---:|
| 静态层 (infra/db/frontend/peer_deps/integ) | 82 | 82 | 100% |
| 接口层 (api) | 26 | 26 | 100% |
| 接口层 (db_api) | 16 | 16 | 100% |
| 接口层 (navigation) | 8 | 8 | 100% |
| 接口层 (auth) | 1 | 1 | 100% |
| 逻辑层 (backend_proc) | 4 | 4 | 100% |
| **合计** | **137** | **137** | **100%** |
| 后端语法 (node --check) | 78 文件 | 78 | 100% |

## 关键设计决策（系统自动完成）

- 库存扣减使用**乐观锁 + 指数退避 3 次重试**，version 字段兜底
- 订单支付超时 **30 分钟自动取消**，释放库存预占
- 退款时**佣金同步追索**，从商家钱包可用余额扣除
- JWT 双 Token 机制（access 15min + refresh 7 天），HttpOnly Secure SameSite
- 全局配置常量热更新（抽佣率、超时时间、审核 SLA）
- 第三方服务全 mock 模式，通过 `*_MODE` 环境变量一键切换 real

## 源码

完整项目源码位于 [work/project/](../work/project/)。

## License

MIT
