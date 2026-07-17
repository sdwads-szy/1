# backend_proc 测试模板 — 参数化骨架

🛑 不调 HTTP，直接 require service 函数。jest.mock DB/Redis 隔离。
🛑 你的任务不是"写测试"，而是 **从真理提取参数 → 填入骨架 → 输出**。

## 🛑 mock/real 双模式

部分 service 函数含第三方服务调用（支付/短信/OSS），通过 `*_MODE` 环境变量切换：

```javascript
const PAYMENT_MODE = process.env.PAYMENT_MODE || 'mock';
async function createPayment(order) {
  if (PAYMENT_MODE === 'mock') return { mockHint: '模拟支付成功', ... };
  return realCreatePayment(order);  // 调微信支付 API
}
```

**测试策略**：
- 测试环境 `*_MODE=mock`（`.env` 默认值）→ 函数走 mock 路径返回假数据
- 测试验证 mock 路径返回的 `mockHint` 字段存在 + 业务字段正确
- **不要 mock 第三方 API 模块**（如 `jest.mock('wechat-pay')`）——mock 路径不调它们
- real 路径只验证结构：源码用 `process.env.XXX` 引用密钥（不硬编码）

**mock 断言示例**：
```javascript
// mock 模式下的正常响应
it('返回 mockHint 标记', () => {
  expect(result.mockHint).toBeDefined();
  expect(result.mockHint).toContain('模拟');
});
it('业务字段不受 mock 影响', () => {
  expect(result.orderNo).toEqual(expect.any(String));
  expect(result.totalAmount).toEqual(expect.any(Number));
});
```

---

## 第一步：从真理提取参数

在 prompt 的 `## 🥇 下层真理` 中找到被测服务。对 `exposed_apis[]` 中每个函数提取以下参数：

```
参数                 来源                                        示例值
──────────────────  ──────────────────────────────────────────  ────────────────────────────
{SERVICE_PATH}      真理 targetFiles 或 prompt 中的 targetFiles  ../services/authService
{FN_NAME}           exposed_apis[].name                          sendSmsCode
{FN_ARGS}           exposed_apis[].parameters[].name 按顺序      phone
{FN_CALL}           根据参数类型生成调用                           sendSmsCode('13800138000')
{FN_RETURN}         exposed_apis[].returns.type                   { success: true, mockCode? }
{ERROR_CODES}       exposed_apis[].errors[].code 用 | 分隔        INVALID_PHONE | SMS_RATE_LIMIT | SMS_SEND_FAILED
{HAS_TRANSACTION}   是否有 beginTransaction/commit/rollback       true / false
{HAS_REDIS}         internal_helpers 中有 redis 相关操作          true / false
{REDIS_METHODS}     从真理服务描述推导 (get/set/incr/expire/del)  get, set, incr, expire, del
```

### 参数类型→示例值映射

| 真理 type | 示例值 |
|-----------|--------|
| string | `'example_value'` |
| int / number | `0` |
| boolean | `true` |
| 可选参数 (? / required:false) | `null` |

### 🛑 调用方式铁律

- **参数个数 === 真理 parameters 数组长度**（可选参数传 null）
- **永远不接受对象 `{key: value}`**，除非真理明确标注参数是 object 类型
- **参数顺序 === 真理 parameters 数组顺序**

---

## 第二步：按场景选骨架

| 场景 category | 使用骨架 |
|:---:|---------|
| correct | [SKELETON_CORRECT] |
| error — 参数校验 / 前置条件不满足 | [SKELETON_EARLY_REJECT] |
| error — 事务回滚 | [SKELETON_TX_ROLLBACK] |
| error — 外部服务异常 | [SKELETON_EXTERNAL_FAIL] |

---

## 第三步：填入骨架

### [SKELETON_CORRECT] 正向处理链

```javascript
describe('correct — {SCENARIO_NAME}', () => {
  let result;

  beforeEach(async () => {
    // 🛑 按源码步骤顺序设置 mock 返回值
    // Redis（如有）: 模拟正常值
    // DB（如有）: 按 SQL 执行顺序 mockResolvedValueOnce
    {MOCK_SETUP}

    // 🛑 调用: 参数从真理提取，禁止对象包装
    result = await service.{FN_NAME}({FN_ARGS_WITH_VALUES});
  });

  // 🛑 每步 1 个 it()，按场景描述的步骤顺序
  {STEP_ASSERTIONS}

  it('COMMIT 被调用，rollback 未调用', () => {
    // 仅 {HAS_TRANSACTION}=true 时保留
    expect(mockCommit).toHaveBeenCalled();
    expect(mockRollback).not.toHaveBeenCalled();
  });

  it('返回值匹配 output', () => {
    expect(result).toMatchObject({
      // 从 {FN_RETURN} 提取字段，如 { success: true }
    });
  });
});
```

**{MOCK_SETUP} 填充规则**:
- DB SELECT → `mockQuery.mockResolvedValueOnce([{...}])`
- DB INSERT/UPDATE → `mockQuery.mockResolvedValueOnce({ affectedRows: 1, insertId: 100 })`
- Redis GET → `mockRedisGet.mockResolvedValue('value')`
- Redis SET → `mockRedisSet.mockResolvedValue('OK')`
- Redis INCR → `mockRedisIncr.mockResolvedValue(1)`
- Transaction → `mockBeginTransaction.mockResolvedValue(mockConnection)`
- 🛑 SELECT COUNT(1) 始终返回 `[{cnt: N}]`，不会返回空数组

**{STEP_ASSERTIONS} 填充规则**:
- 每步 1 个 `it('步骤N: 描述', () => { ... })`
- DB 调用用 `toHaveBeenNthCalledWith(n, expect.stringContaining('SQL关键词'), [...])`
- Redis 调用用 `toHaveBeenCalledWith('key', ...)`
- n 从 1 开始

---

### [SKELETON_EARLY_REJECT] 早期校验拒绝

```javascript
describe('error — {SCENARIO_NAME}', () => {
  it('{ERROR_CODE} 被抛出', async () => {
    // 只 mock 触发校验所需的最小依赖
    {MINIMAL_MOCK}

    await expect(
      service.{FN_NAME}({INVALID_ARGS})
    ).rejects.toThrow(/{ERROR_CODE}/i);

    // 校验失败后不应有任何 DB/Redis 操作
    // expect(mockQuery).not.toHaveBeenCalled();
  });
});
```

**{MINIMAL_MOCK}** — 只设置让代码跑到校验点所需的值。

---

### [SKELETON_TX_ROLLBACK] 事务回滚

```javascript
describe('error — {SCENARIO_NAME}', () => {
  it('事务回滚 + {ERROR_CODE} 被抛出', async () => {
    mockBeginTransaction.mockResolvedValue(mockConnection);
    // 前面的步骤正常返回
    mockQuery
      .mockResolvedValueOnce({/* 步骤1 正常 */})
      .mockRejectedValueOnce(new Error('{ERROR_CODE}'));  // 断点

    await expect(
      service.{FN_NAME}({FN_ARGS_WITH_VALUES})
    ).rejects.toThrow(/{ERROR_CODE}/i);

    expect(mockRollback).toHaveBeenCalled();
    expect(mockCommit).not.toHaveBeenCalled();
  });
});
```

---

### [SKELETON_EXTERNAL_FAIL] 外部服务异常（Redis/SMS/等）

```javascript
describe('error — {SCENARIO_NAME}', () => {
  it('外部服务失败 → {ERROR_CODE} 被抛出', async () => {
    // 前置步骤正常
    {PRE_MOCK}
    // 外部服务失败
    {EXTERNAL_MOCK_FAIL}

    await expect(
      service.{FN_NAME}({FN_ARGS_WITH_VALUES})
    ).rejects.toThrow(/{ERROR_CODE}/i);

    // 验证回滚/清理逻辑
    {CLEANUP_ASSERT}
  });
});
```

**{EXTERNAL_MOCK_FAIL}** — Redis SET 返回非 OK / SMS 抛异常 / 等，取决于具体服务的依赖。

---

## Mock 结构（固定，直接复制）

```javascript
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

// ==== Mock Redis（仅 {HAS_REDIS}=true 时）====
const mockRedisGet = jest.fn();
const mockRedisSet = jest.fn();
const mockRedisIncr = jest.fn();
const mockRedisExpire = jest.fn();
const mockRedisDel = jest.fn();
const mockRedisDecr = jest.fn();

jest.mock('../config/redis', () => ({
  get: mockRedisGet,
  set: mockRedisSet,
  incr: mockRedisIncr,
  expire: mockRedisExpire,
  del: mockRedisDel,
  decr: mockRedisDecr,
}));

// ==== Require ====
const service = require('{SERVICE_PATH}');

describe('{TASK_ID}', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── 骨架填入处 ──
});
```

---

## 🛑 禁止事项

| ❌ 禁止 | ✅ 正确 |
|---------|--------|
| `service.fn({phone: '138'})` — 对象参数 | `service.fn('138')` — 位置参数 |
| `mockRedisGet.mockResolvedValue('2')` 然后断言 `incr` 被调用 — mock 了不存在的调用 | 严格按真理中的服务描述设置 mock，不猜测 |
| `jest.mock('../utils/smsSender')` — mock 不存在的模块 | 内部函数不需要单独 mock |
| 断言错误码 `TOO_MANY_SMS` 而真理是 `SMS_RATE_LIMIT` | 断言错误码 = 真理 errors[].code |
| `expect.any(String)` 匹配 `undefined` — JWT_SECRET 未设置 | 在文件顶部设置 `process.env.JWT_SECRET = 'test-secret'` |

---

## 🛑 A 自动补规则（场景没写但测试必须覆盖的实现细节）

**这些规则是后端测试的"肌肉记忆"——不管 testScenarios 有没有提到，A 必须自动补充。**

### 通用规则（所有 backend_proc 适用）

| # | 规则 | 代码 |
|---|------|------|
| 1 | `SELECT COUNT(1)` 永远返回 `[{cnt: N}]` | `mockQuery.mockResolvedValueOnce([{ cnt: 0 }])` |
| 2 | `mockConnection` 必须有 `execute` 映射到 `mockQuery` | `const mockConnection = { query: mockQuery, execute: mockQuery, commit: mockCommit, rollback: mockRollback }` |
| 3 | INSERT/UPDATE 返回 `{ affectedRows, insertId }` | `mockQuery.mockResolvedValueOnce({ affectedRows: 1, insertId: 100 })` |
| 4 | `affectedRows=0` 时源码必须 throw | `await expect(service.fn(...)).rejects.toThrow()` |

### 条件规则（按服务依赖触发）

| 触发条件 | 规则 | 代码 |
|---------|------|------|
| 真理有 bcrypt/jwt | `process.env.JWT_SECRET` 在 `jest.mock('jsonwebtoken')` **之前**设置 | `process.env.JWT_SECRET = 'test-secret';` |
| 真理有 encryptPhone | mock `../utils/encryption`，直通返回原值 | `jest.mock('../utils/encryption', () => ({ encryptPhone: (p) => p }))` |
| 真理有 Redis SET | SET 失败也会抛异常（即使契约 step 没写 onFail） | `mockRedisSet.mockResolvedValue(null)` → `expect(...).rejects.toThrow()` |
| 真理有 Redis INCR 做频率检查 | 首次 INCR 返回 1（触发 EXPIRE），非首次返回 2/3/4 | `mockRedisIncr.mockResolvedValue(1)` 为首次 |
| 真理有 Redis EXPIRE | 只在 `current===1` 时调用 | 断言中区分首次/非首次的 EXPIRE 调用次数 |
| 真理有 bcrypt | mock `hash` 和 `compare` | `bcrypt.hash.mockResolvedValue('$2b$10$...')` |
| 真理有 jwt | access + refresh 两个 token，注意调用顺序 | `jwt.sign.mockReturnValueOnce('token1').mockReturnValueOnce('token2')` |

### 异常补充规则

| 规则 | 说明 |
|------|------|
| 每个 error scenario 额外加 1 个 it()：断点前的步骤已执行，断点后的步骤未执行 | 验证"部分执行+回滚"的原子性 |
| 事务类 error：`expect(mockRollback).toHaveBeenCalled()` + `expect(mockCommit).not.toHaveBeenCalled()` | 每个事务回滚场景必须断言 |
| 外部服务异常：验证清理逻辑（Redis DEL / 配额回滚） | 从真理接口描述推导清理行为 |
