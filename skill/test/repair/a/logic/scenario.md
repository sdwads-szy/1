# A repair: scenario

A 的测试代码被 B 判定 `fix_target=test` → A 自我修复。

## 判定：删了重写 vs 修补

| 情况 | 动作 | 工具 |
|------|------|------|
| 步数 >5（scenario 短链 ≤5） | **重写** | `create_files` 加载 [模板](../../../templates/logic/scenario.md) 拆分 |
| 重新验证了单步逻辑（backend_proc 真理） | **重写** | 同上 |
| mock 了 DB | **重写** | 同上 |
| 交接字段提取错（步骤A输出→步骤B输入字段不匹配） | **修补** | `edit_batch` 对齐字段名 |
| 交接失败后缺副作用检查 | **修补** | `edit_batch` 补 GET 验证上游数据未被污染 |
| beforeAll 前置状态准备不完整 | **修补** | `edit_batch` 补种子用户登录逻辑（从 t_db_user 真理的 seed 数据取 phone/password，不调 register） |

🛑 修复后对照 [测试点表](../../roles/a/logic/scenario.md) 确认每个交接点 ≥2 it()（correct+error）。
