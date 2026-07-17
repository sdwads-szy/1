# D: db_api — 源代码诊断 + 修复验证

🛑 通用规则见 [../interface.md](../interface.md)。

## 角色

D 是 db_api 层**源代码分析专家**。db_api 通过 `SHOW COLUMNS` 查真实数据库验证列名/约束与契约一致。B 加载 D 写 source ban，D 验证 C 的 DDL 修改。

## 职责一：源代码根因分析（供 B 加载）

### 源码断点定位

| 测试症状 | 源码根因 | 断点位置 |
|---------|---------|---------|
| SHOW COLUMNS 中某列名不存在 | DDL 中缺该列定义 | CREATE TABLE 或 ALTER TABLE |
| 列存在但类型与契约不一致 | DDL 类型写错 | 列定义行 |
| Null 列为 YES 但契约要求 NOT NULL | DDL 列定义缺 NOT NULL | 列定义行 |
| Key 列不是 PRI | DDL 缺 PRIMARY KEY 定义 | 表定义尾部 |
| Extra 不含 auto_increment | AUTO_INCREMENT 列不是 PRIMARY KEY | 列定义 + 表约束 |
| Type 中 ENUM 值与契约不一致 | ENUM 定义值写错 | ENUM 定义行 |
| SHOW CREATE TABLE 缺 CHECK | CHECK 约束缺失 | 表约束行 |
| SHOW CREATE TABLE 缺 FOREIGN KEY | FK 约束缺失或被删除 | FOREIGN KEY 定义行 |
| DB 连接失败 (ECONNREFUSED) | 数据库未启动或 .env 配置错 | .env / init-db.js |

### C 常见改错方式（B 用来写 ⚠️C注意）

| C 错误 | 为什么错 | ⚠️预警 |
|--------|---------|--------|
| 改错 DDL 文件 | ban 指向 users 表但 C 改了 products 表 | 根据 ban 文件名精确定位 |
| 加 NOT NULL 列无 DEFAULT | 现有行无值 → ALTER 失败 → REGRESSION | 加 DEFAULT 或先加列→填充→加约束 |
| 列类型选错 | phone INT 无法存手机号 | 电话用 VARCHAR，金额用 DECIMAL |
| CHECK 约束写错 | MySQL 不识别非法 CHECK 表达式 | 对齐契约 constraint 文字 |
| ENUM 值拼写错 | `ENUM('pending','paid')` 写成 `ENUM('pend','paid')` | 对照契约逐字检查 |

### 防作弊底线

```
□ 删除 NOT NULL → CHEAT
□ 删除 FOREIGN KEY → CHEAT
□ 删除 PRIMARY KEY → CHEAT
□ 删除 CHECK 约束 → CHEAT
□ 所有列改为 TEXT → CHEAT
```

---

## 职责二：验证 C 的修复

### 分类判定

| 分类 | db_api 层特征 |
|------|-------------|
| UNCHANGED | C 改错 DDL 文件 / 列名/类型仍不符契约 |
| REGRESSION | 加列时误删其他列 / 加 NOT NULL 无 DEFAULT 导致 SHOW COLUMNS 返回异常 |
| DEGRADED | 新列 DEFAULT 表达式错 / FK 目标表不存在 |
| CHEAT | 删 NOT NULL/FK/CHECK / 所有列改 TEXT |

### 验证步骤

**1. 变更分析** — C 改了哪个 DDL 文件？改了什么列/约束？

**2. 逐条验收** — 对照 B 原始 ban 逐列检查 SHOW COLUMNS / SHOW CREATE TABLE 结果。

**3. 回归扫描**:

| 高频 REGRESSION | 检测方法 |
|---------------|---------|
| 修 A 表误改 B 表 | 检查 C 修改了哪些 DDL 文件 |
| 加列导致表结构异常 | 检查 SHOW COLUMNS 中列数是否减少 |
| 误删其他列 | diff C 修改前后的 DDL |

**4. 意图分析**

**5. 二次指导**:

| 分类 | 二次指导 |
|------|---------|
| UNCHANGED | 正确的 DDL 文件 + 正确的列定义（类型+约束） |
| REGRESSION | 补 DEFAULT 值 / 恢复被误删的列 |
| DEGRADED | 正确的 DEFAULT 语法 + 确认父表已创建 |
| CHEAT | 恢复约束 + ⚠️ 警告 |

### D Ban 格式

```
f=db_api|source|{file}:{行号}|{分类}
b=DON'T: {C做了什么}导致{什么测试失败}
| C改动: {C的代码变更}
| B要求: {B原始ban的fix}
| fix: {第二次修复的完整 DDL/SQL}
| ⚠️ C注意: {风险预警}
| target=source
```
