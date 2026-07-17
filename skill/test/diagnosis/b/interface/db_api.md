# B: db_api — 测试代码诊断

🛑 通用规则见 [../interface.md](../interface.md)。

## 角色

B 评估 db_api 层**测试代码**写对了没有。db_api 是接口层的静态子类型——测试用 `mysql2` 连接真实数据库 + `SHOW COLUMNS FROM table`，不调 HTTP，不解析 DDL 文本。

- 测试代码有 bug → `fix_target=test`
- 测试代码干净但测试失败 → `fix_target=source` → 加载 D

🛑 **真理绝对权威**: prompt 中的 `## 🛑 下层真理` 列出了依赖工程师已验证的 DDL 表名+列名。**真理中的列名绝对正确**，优先级高于测试代码的断言。

## 输入

| 输入 | B 怎么用 |
|------|---------|
| `test_file` | 审查对象——mysql2 SHOW COLUMNS + toContain 测试 |
| `testScenarios` | 对照标准——input(表名+期望列名)/output(列名存在/不存在) |
| `raw_result` | Jest JSON |

## 逐项检查

### 1. DB 连接失败

🛑 测试连接真实数据库，连接失败 = 环境问题，非代码 bug。

| 常见错误 | 子类型 |
|---------|--------|
| ECONNREFUSED — 数据库未启动 | DB_CONNECTION |
| ER_ACCESS_DENIED — 用户名/密码错 | DB_CONNECTION |
| ER_BAD_DB — 数据库名错 | DB_CONNECTION |

→ 子类型: DB_CONNECTION，fix_target=source（需要初始化数据库）

### 2. 表名拼写

🛑 SHOW COLUMNS FROM 的表名必须与真理 JSON 完全一致。

| 常见错误 | 子类型 |
|---------|--------|
| 表名拼写错（`user` vs `users`） | TABLE_NAME_ERR |
| 编造的表名 | TABLE_NAME_ERR |

### 3. 列名拼写

🛑 toContain 的列名必须与真理 `tables[].fields[].name` 逐字符一致。

| 常见错误 | 子类型 |
|---------|--------|
| 拼写错（`create_at` vs `created_at`） | COLUMN_SPELLING_ERR |
| 下划线遗漏或多余 | COLUMN_SPELLING_ERR |

### 4. 场景覆盖

db_api 至少需要 correct + error + boundary：

| 场景 | 内容 |
|------|------|
| correct | 每个列名在 SHOW COLUMNS 结果中存在 |
| boundary | NOT NULL / PRIMARY KEY / AUTO_INCREMENT |
| error | 不存在的列名 not.toContain |
| error | Service INSERT 列数 = VALUES 占位符数 |
| error | 事务内是否误用 db.query() 而非 conn.query() |

→ 子类型: MISSING_CATEGORY

### 5. 不验证 db 真理

🛑 db 层已验证 FOREIGN KEY/ENGINE/CHARSET，db_api 不应重复断言。

→ 子类型: VERIFIED_TRUTH

---

## 判定

### total=0 → fix_target=test

```
SyntaxError    → test_file:行号 | SYNTAX
DB_CONNECTION  → test_file      | DB_CONNECTION → fix_target=source（需初始化DB）
```

### total>0 && failed>0

**先查上面 5 项。** 查到 → fix_target=test。全部通过 → fix_target=source → 加载 D。

---

## Ban 格式

```
f=db_api|test|{test_file}:{行号}|{子类型}
b=DON'T: testScenario "{场景名}" {哪里错了} — {为什么}
| fix: {测试文件}:{行号} {完整修正代码}
| target=test
```
