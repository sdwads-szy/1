# A repair: logic

A 的测试代码被 B 判定 `fix_target=test` → A 自我修复。

## 判定：删了重写 vs 修补

| 情况 | 动作 | 工具 |
|------|------|------|
| 写了 jest.mock DB（logic 走 supertest HTTP） | **重写** | `create_files` 加载 [模板](../../../templates/logic/logic.md) 全新生成 |
| 只有正向正常没有异常/补偿 | **重写** | 同上 |
| beforeAll 没注册用户获取 token | **修补** | `edit_batch` 补注册逻辑 |
| token 硬编码 | **修补** | `edit_batch` 改为从 beforeAll 注册获取 |
| 步骤间变量传递断了 | **修补** | `edit_batch` 对齐 `const {xxx} = rN.body.data` |
| 中间断点后没验证前面副作用未被污染 | **修补** | `edit_batch` 补 GET 验证 |
| 忘了验证状态流转 | **修补** | `edit_batch` 最后一步 GET 确认 status |
| 补偿路径缺 | **修补** | `edit_batch` 补补偿 describe |

🛑 修复后对照 [测试点表](../../roles/a/logic/logic.md) 确认 步骤数 + 3 个 it() 最少。
