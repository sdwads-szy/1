# A: scenario — 跨模块数据交接

继承 [logic.md](../logic.md) 通用规则。代码模板见 [templates/logic/scenario.md](../../../templates/logic/scenario.md)。

🛑 **scenario 层只依赖 logic + navigation 真理**（`flows[].steps[]` + `jumps[]`），不依赖 api/db_api/backend_proc。

## 工作流

1. **读 testScenarios** → 交接点：A 模块产出什么 → B 模块接收什么
2. **读 logic 真理** → `flows[].steps[]`: 每步的 method/path/request_fields/returns
3. **读 navigation 真理** → `jumps[]`: 页面跳转的 passBy/params
4. 场景 + 真理对齐 → create_files 输出

## 场景→骨架映射

每个交接点 = 1 个 describe，含 correct + error 各 1 个 it()：

| category | 骨架 | 断言 |
|----------|------|------|
| correct | A模块产出 → 提取字段 → B模块接收 → 字段一致 | `expect(rB.body.data.{field}).toBe({field})` |
| error | A模块正常 → B模块传错 → 拒绝 + A数据未污染 | GET 验证原状态不变 |

## 🛑 测试点

| 来源 | 断言方式 |
|------|---------|
| logic 真理 `flows[].steps[].path` | 🛑 端点路径 |
| logic 真理 `flows[].steps[].method` | HTTP 方法 |
| logic 真理 `flows[].steps[].returns` | 交接字段名 |
| logic 真理 `flows[].steps[].handoff_fields[]` | 🛑 同层 peers 交接字段 |
| navigation 真理 `jumps[]` | 页面跳转 passBy/params |

🛑 步数 ≤5——每个 scenario 只测一个交接点，不是全链路。
🛑 beforeAll 从 logic 同层真理 `handoff_example` 取测试数据直接登录，不调 register 端点。

## 自检清单（create_files 前逐条确认）

- [ ] 端点路径 = logic 真理 `flows[].steps[].path`？
- [ ] HTTP 方法 = logic 真理 `flows[].steps[].method`？
- [ ] 交接字段名 = logic 真理 `flows[].steps[].returns`？
- [ ] 页面跳转 = navigation 真理 `jumps[]` passBy/params？
- [ ] 步数 ≤5？
- [ ] error 场景验证了 A 模块数据未被污染？

## 自我修复

B 判定 `fix_target=test` → 加载 [repair/a/logic/scenario.md](../../../repair/a/logic/scenario.md)。
