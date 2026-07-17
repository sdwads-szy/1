# A repair: api

A 的测试代码被 B 判定 `fix_target=test` → A 自我修复。B 的 ban 含文件:行号 + 错误描述。

## 判定：删了重写 vs 修补

| 情况 | 动作 | 工具 |
|------|------|------|
| 用了 supertest / require('../../app') | **重写** | `create_files` 加载模板全新生成 |
| 用了 import/vi.mock 而非 require | **重写** | 同上 |
| workspace 路径层级错（多/少 `..`） | **修补** | `edit_batch` 改正 `path.resolve(__dirname, '..')` |
| fs.readFileSync 路径错（文件不存在） | **修补** | `edit_batch` 改为 targetFiles 中的正确路径 |
| toContain 用的值不对（path/handler/字段名/中间件名） | **修补** | `edit_batch` 改为真理中的精确值（从 prompt 的 @truth 块找） |
| 缺某个验证维度 | **修补** | `edit_batch` 补对应 describe 块 |
| 编造了不存在的 handler/路由/错误码 | **重写** | `create_files` 加载模板，只用真理中的值 |
| 重复断言（同样的检查写了两遍） | **修补** | `edit_batch` 去重 |

🛑 修复后对照 [验证维度表](../../roles/a/interface/api.md) 逐条确认 4 个维度覆盖完整。
🛑 **绝对不要改回 supertest 模式**——fs.readFileSync 是 api 层的正确方式。
🛑 断言用 `toContain` / `includes`，不用正则。
