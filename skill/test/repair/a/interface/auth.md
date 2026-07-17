# A repair: auth

A 的测试代码被 B 判定 `fix_target=test` → A 自我修复。

## 判定：删了重写 vs 修补

| 情况 | 动作 | 工具 |
|------|------|------|
| 用了 supertest / require('../../app') | **重写** | `create_files` 加载 [模板](../../../templates/interface/auth.md) 全新生成 |
| mock 了 JWT 库（必须真实 jwt.sign/verify） | **重写** | 同上 |
| jwt.sign payload 缺 userId 或 role | **修补** | `edit_batch` 补字段 |
| expiresIn 写错（如 `expiresIn:'0s'` 写成 setTimeout） | **修补** | `edit_batch` 改过期方式 |
| fs.readFileSync 路径错 | **修补** | `edit_batch` 改路径 |
| toContain/toMatch 断言太弱 | **修补** | `edit_batch` 改为具体正则 |
| 缺某个维度（mw/store/guard） | **修补** | `edit_batch` 补对应 describe 块 |
| parts.forEach → parts 未定义（token.split 缺赋值） | **修补** | `edit_batch` 补 `const parts = token.split('.')` |

🛑 修复后对照 [测试点表](../../roles/a/interface/auth.md) 确认 4 个维度覆盖完整。
