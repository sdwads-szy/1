# A: backend_proc — 单功能处理链

继承 [logic.md](../logic.md) 通用规则。代码模板见 [templates/logic/backend_proc.md](../../../templates/logic/backend_proc.md)。

## 工作流

1. **读 testScenarios** → 业务流骨架：函数名、SQL 步骤顺序、返回值形状、错误码
2. **读 api 真理** (`routes[].handlers[]`) → 合约校验：handler 名、request_fields、error_codes（🛑 错误码精确名）
3. **读 db_api 真理** (`sql_columns_verified[]`) → 列名校验：每个函数的 table、operation、columns
4. 场景 + api 真理 + db_api 真理 三者对齐 → create_files 输出

🛑 **不需要读源码。真理就是从源码提取的接口，场景描述业务流程，两者结合足够写测试。**

## 第一步：从 testScenarios 提取骨架

| 提取项 | 场景位置 | 填入 |
|--------|---------|------|
| 函数签名 | `process[]` 中 `{Service}.{fn}(args...)` | `{FN_NAME}`, `{FN_ARGS}`, `{FN_CALL}` |
| SQL 步骤 | `process[]` 中 `SELECT/INSERT/UPDATE FROM {table}` | mock 顺序 = `process[]` 中 SQL 出现顺序 |
| 返回值形状 | `output` 字段 | `{FN_RETURN}` |
| 错误码 | `output` 或 `throw {CODE}` | `{ERROR_CODES}` |
| 归属层 | `process[]` 中 `controller:` 前缀 | 🛑 跳过不测 |

🛑 **`process[]` 标注了 `controller:` 的场景 → 删除整段 describe**（api 层职责，不在 service 单测范围）。

## 第二步：从 api 真理校验合约

在 `## 🥇 下层真理` 的 api 真理中，找到对应 handler：

| 校验项 | api 真理路径 | 用法 |
|--------|------------|------|
| 函数名 | `routes[].handlers[].handler` | 与场景匹配，确认 handler 名 |
| 参数列表 | `routes[].handlers[].request_fields[]` | mock 调用时的参数名 |
| 错误码精确名 | `routes[].handlers[].error_codes[]` | 🛑 断言必须用这个精确值，禁止编造 |
| 返回值类型 | `routes[].handlers[].response` | 断言方向参考 |

🛑 **参数顺序**：`request_fields[]` 的顺序 = controller 解构顺序 = service 函数参数顺序。

## 第三步：从 db_api 真理取实现细节

在 `## 🥇 下层真理` 的 db_api 真理中，**所有 mock 参数从真理提取，不需要读源码**：

| 提取项 | db_api 真理路径 | 用途 |
|--------|---------------|------|
| mock 顺序 | `sql_columns_verified[].query_order` | 🛑 `mockResolvedValueOnce` 链的第 N 次，直接按数字排 |
| mock 列名 | `sql_columns_verified[].columns[]` | 🛑 mock 返回值只含这些列 |
| 操作类型 | `sql_columns_verified[].operation` | SELECT→返回数组，INSERT/UPDATE→返回 `{affectedRows}` |
| **连接模式** | `sql_columns_verified[].connection` | 🛑 `"pool"`→`jest.mock('../config/db')` 直调；`"connection"`→需 mock `getConnection`；`"transaction"`→需 mock `beginTransaction/commit/rollback` |
| **SQL 参数** | `sql_columns_verified[].sql_params[]` | 🛑 `toHaveBeenNthCalledWith` 的 param count。空数组=SQL 无 `?` 占位符（如 `CURDATE()` 内联），只断 1 个参数(sql) |
| **SQL 特征** | `sql_columns_verified[].sql_features[]` | `"JOIN"`→一次查询涉及多表；`"CURDATE"`→无 params；`"ON DUPLICATE KEY"`→INSERT 可能变 UPDATE |

🛑 **`query_order` = mockResolvedValueOnce 的顺序号**。一个 function 有 N 条记录→N 个 mock 按 `query_order` 排。
🛑 **`connection` 决定 mock 结构**:
  - `"pool"`: `jest.mock('../config/db')` + `mockQuery.mockResolvedValueOnce(...)`
  - `"connection"`: 需额外 `mockGetConnection.mockResolvedValue({ query: mockQuery, ... })`
  - `"transaction"`: 需额外 `mockBeginTransaction` + `mockCommit` + `mockRollback`
🛑 **`sql_params` 长度 = `toHaveBeenNthCalledWith` 的额外参数个数**。长度 0→`toHaveBeenNthCalledWith(n, expect.stringContaining('table'))`不传 params 数组。

## 第四步：场景→骨架映射

| scenario.category | 骨架 |
|:---:|------|
| correct | [SKELETON_CORRECT] — mock 按 `query_order` 顺序 + 断言 output |
| error | [SKELETON_ERROR] — mock 到断点前（`query_order` 截断）+ 断言 throw 真理 error_codes |
| boundary — controller | 🛑 **跳过**（`process[]` 标注 `controller:`） |

## 独有规则

- 测试方式: `jest.mock('../config/db')` → require service 函数直调，不走 HTTP
- Mock 按 `query_order` 用 `mockResolvedValueOnce` 串链，**步数 = 真理记录数**
- `toHaveBeenNthCalledWith` 参数个数 = 1(sql) + `sql_params.length`
- 🛑 **事务断言**：`connection: "transaction"` 才 mock commit/rollback；`"pool"` 或 `"connection"` 不测事务
- 🛑 **COUNT 别名**：columns 中的别名（如 `total`）→ mock 返回 `{[alias]: N}`
- 🛑 **返回值断言**：testScenarios `output` 字段定方向，api 真理 `response` 字段定字段名
- 🛑 **controller 层场景跳过**：`process[]` 标注了 `controller:` 的 scenario → 删除整段 describe
- affectedRows=0 → 源码必须 throw
- 🛑 加密工具（encryptPhone 等）需额外 mock: `jest.mock('../utils/encryption', () => ({ encryptPhone: (p) => p }))`

## 自检清单（create_files 前逐条确认）

- [ ] 函数名 = api 真理 `routes[].handlers[].handler`？
- [ ] 参数列表 = api 真理 `routes[].handlers[].request_fields[]`（顺序一致）？
- [ ] 错误码 = api 真理 `routes[].handlers[].error_codes[]`（🛑 精确名）？
- [ ] 返回值方向 = api 真理 `routes[].handlers[].response`？
- [ ] mock 步数 = db_api 真理 `sql_columns_verified[]` 记录数？
- [ ] mock 顺序 = db_api 真理 `sql_columns_verified[].query_order`？
- [ ] mock 列名 = db_api 真理 `sql_columns_verified[].columns[]`？
- [ ] 连接模式 = db_api 真理 `sql_columns_verified[].connection`？
- [ ] SQL 参数数 = db_api 真理 `sql_columns_verified[].sql_params[]` 长度？
- [ ] 事务断言 = `connection: "transaction"` 才测 commit/rollback？
- [ ] Redis key = backend_proc 已有真理 `redis_ops[]`（如有）？
- [ ] `process[]` 标注 `controller:` 的场景已跳过？

## 自我修复

B 判定 `fix_target=test` → 加载 [repair/a/logic/backend_proc.md](../../../repair/a/logic/backend_proc.md)。
