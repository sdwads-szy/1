# A: logic — 单模块业务流

继承 [logic.md](../logic.md) 通用规则。代码模板见 [templates/logic/logic.md](../../../templates/logic/logic.md)。

🛑 **logic 层只依赖 backend_proc 真理**（`services[].functions[]`），不依赖 api/db_api 真理。backend_proc 已封装全部接口层验证结果。

## 工作流

1. **读 testScenarios** → 步骤链：每步 method + path + 做什么
2. **读 backend_proc 真理** → 函数签名 + 错误码 + 返回值 + SQL 细节（全部信息在此）
3. 场景 + 真理对齐 → create_files 输出

## 场景→骨架映射

logic 的场景来自 `testScenarios`，每步对应一个 HTTP 请求：

| scenario.category | 骨架 |
|:---:|------|
| correct | 串联所有步骤，每步验证 status + 提取变量传递 |
| error | 中间断点，验证前面步骤数据未污染 |
| boundary | 错 role/空token/过期token → 403 |
| compensation | 逆流程（退款→恢复→状态回退） |

### process 格式解析
```
用户注册 → 登录获取token → 下单（带token）→ 查询订单
→ it('步骤1: 注册', ...) + it('步骤2: 登录获取token', ...) + it('步骤3: 下单', ...) + it('步骤4: 查询验证', ...)
  步骤间: 从上一步 res.body.data 提取 token/orderId 传给下一步
```

## 🛑 测试点

| 测试点 | 来源 | 断言方式 |
|--------|:---:|---------|
| 正向正常: process 每步 1 个 it() | scenario | `expect(res.status).toBe(200/201)` + `toMatchObject` |
| 跨步数据一致性 | scenario output | `expect(orderData.quantity).toEqual(payData.amount)` |
| 正向异常: 中间断点 | scenario | 前面步骤数据仍正确，断点后未执行 |
| 错 role 操作 → 403 | **A 自动补** | `expect(res.status).toBe(403)` |
| 补偿操作 | **A 自动补** | 逐步验证补偿成功 |
| 重复补偿被拒 → 409 | **A 自动补** | `expect(res.status).toBe(409)` |

🛑 **最少 it() 数**: process 步骤数 + 3。
🛑 步骤间变量传递: `const token = res.body.data.token` → `set('Authorization', \`Bearer ${token}\`)`。

## 独有规则

- supertest HTTP 串联，每步发请求
- 变量传递: 从上一步 `res.body.data` 提取
- 不同 role 不能互相操作
- 每一步必验证 status + body.data 关键字段
- 🛑 **所有字段名从 backend_proc 真理取**，不编造

## 自检清单（create_files 前逐条确认）

- [ ] 函数名 = 真理 `services[].functions[].name`？
- [ ] 错误码 = 真理 `services[].functions[].throws[]`（🛑 精确名）？
- [ ] 返回值字段 = 真理 `services[].functions[].returns`（展开到叶子字段）？
- [ ] 步骤间变量提取字段名与真理 returns 一致？
- [ ] SQL 验证字段 = 真理 `sql_queries[].columns[]`？
- [ ] 事务边界 = 真理 `functions[].transaction` + `sql_queries[].connection`？

## 自我修复

B 判定 `fix_target=test` → 加载 [repair/a/logic/logic.md](../../../repair/a/logic/logic.md)。
