# A repair: db_api

A 的测试代码被 B 判定 `fix_target=test` → A 自我修复。

## 判定：删了重写 vs 修补

| 情况 | 动作 | 工具 |
|------|------|------|
| 表名拼写错 / 编造表名 | **修补** | `edit_batch` 改正表名（对齐真理） |
| 列名拼写错（如 `phone` 写成 `phone_num`） | **修补** | `edit_batch` 改正列名 |
| `toContain` 列名写成了不存在的列 | **修补** | `edit_batch` 改为真实列名 |
| 缺 boundary 检查（NOT NULL / PK / AUTO_INCREMENT） | **修补** | `edit_batch` 补 describe |
| 缺事务误用检查 | **修补** | `edit_batch` 补 describe |
| 测试完全不匹配新模板格式 | **重写** | `create_files` 加载 [模板](../../../templates/interface/db_api.md) 全新生成 |
| DB 连接参数错误 | **修补** | `edit_batch` 修正连接参数 |

🛑 修复后对照模板确认 correct + error + boundary(NOT NULL/PK/AUTO_INC) + 事务误用 齐全。列名和表名必须从真理取。
🛑 测试用 `SHOW COLUMNS` 查真实数据库，不用 `fs.readFileSync` 解析 DDL 文本。
