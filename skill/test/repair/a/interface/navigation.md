# A repair: navigation

A 的测试代码被 B 判定 `fix_target=test` → A 自我修复。

## 判定：删了重写 vs 修补

| 情况 | 动作 | 工具 |
|------|------|------|
| 检查了 .vue 文件是否存在（frontend 真理） | **重写** | `create_files` 加载 [模板](../../../templates/interface/navigation.md) 全新生成 |
| 检查了 router 注册（integ 已验证） | **重写** | 同上 |
| error it() 只有注释没有断言代码 | **重写** | 同上 |
| fs.readFileSync 路径错（fromPage/toPage） | **修补** | `edit_batch` 改路径 |
| 用了正则而非 `toContain`/`includes` | **修补** | `edit_batch` 改为 `includes('params:')` / `toContain(routeName)` |
| 只测了正跳转忘了返回跳转 | **修补** | `edit_batch` 补 describe |
| passBy 检查用了正则 | **修补** | `edit_batch` 改为 `fromPage.includes('params:')` 等 |
| 参数名用 `id` 而非契约名 `orderId` | **修补** | `edit_batch` 对齐 _trace.dataTransfer 中的名字 |

🛑 修复后对照 [测试点表](../../roles/a/interface/navigation.md) 确认 correct>=2 + error>=1。
🛑 断言全部用 `toContain` / `includes`，不用正则。
