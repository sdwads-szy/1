# db_api 测试模板 — 数据库列名验证

🛑 **连接真实数据库，用 `SHOW COLUMNS` 验证列名，不用正则匹配 DDL 文本。**

## 第一步：从真理提取参数

在 `## 🥇 下层真理` 的 `@truth t_db_*` 中找到 `tables`，提取：

```
{TABLE_NAME}    ← tables[].name                    如 "users", "login_logs"
{COLUMNS}       ← tables[].fields[].name            如 ["id","phone","password_hash"]
{NOT_NULL_COLS} ← fields[] constraints 含 NOT NULL  如 ["phone","password_hash"]
{PK_COL}        ← fields[] constraints 含 PK        如 "id"
{AUTO_INC_COL}  ← fields[] constraints 含 AUTO_INC  如 "id"
{SERVICE_FILE}  ← targetFiles[0]                    如 "services/authService.js"
```

🛑 **铁律：上面每个值都从真理 JSON 中逐字抄。真理写 `login_logs` 就写 `login_logs`。**

## 第二步：填入骨架

```javascript
/** @jest-environment node */
require('dotenv').config();
const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');
const workspace = path.resolve(__dirname, '..');

describe('{TASK_ID}', () => {
  let conn;
  beforeAll(async () => {
    conn = await mysql.createConnection({
      host: process.env.DB_HOST || 'localhost',
      port: parseInt(process.env.DB_PORT || '3306'),
      user: process.env.DB_USER || 'root',
      password: process.env.DB_PASSWORD || '',
      database: process.env.DB_NAME || 'testdb',
    });
  });
  afterAll(async () => { if (conn) await conn.end(); });

  // ══ correct: 列名存在（SHOW COLUMNS 查真实数据库）══
  describe('correct — {TABLE_NAME} 列名存在', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `{TABLE_NAME}`');
      columns = rows.map(r => r.Field);
    });

    // 🛑 每个字段一个 it()
    {COLUMN_ITEMS}
  });

  // ══ boundary: NOT NULL / PK / AUTO_INCREMENT 约束 ══
  describe('boundary — {TABLE_NAME} 约束', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `{TABLE_NAME}`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    {NOT_NULL_ITEMS}

    it('PRIMARY KEY {PK_COL} 已定义', () => {
      expect(colMap['{PK_COL}'].Key).toBe('PRI');
    });

    it('AUTO_INCREMENT {AUTO_INC_COL}', () => {
      expect(colMap['{AUTO_INC_COL}'].Extra).toContain('auto_increment');
    });
  });

  // ══ boundary: CHECK / FULLTEXT / 复合约束 ══
  // SHOW COLUMNS 看不到 CHECK 约束和 FULLTEXT 索引，用 SHOW CREATE TABLE
  describe('boundary — {TABLE_NAME} 表级约束', () => {
    let createTable;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `{TABLE_NAME}`');
      createTable = rows[0]['Create Table'];
    });

    {TABLE_CONSTRAINT_ITEMS}
  });

  // ══ error: 列名不存在 ══
  describe('error — 列名缺失', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `{TABLE_NAME}`');
      columns = rows.map(r => r.Field);
    });

    it('不存在的列名 not.toContain', () => {
      expect(columns).not.toContain('xyz_not_a_column');
    });
  });

  // ══ error: truth 中声明的列在数据库中真实存在 ══
  describe('error — truth 列 vs 真实 DB', () => {
    let allColumns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `{TABLE_NAME}`');
      allColumns = new Set(rows.map(r => r.Field));
    });

    // 从下游真理 `sql_columns_verified` 中提取本表相关的列名，验证在 DB 中存在
    {TRUTH_COLUMN_ITEMS}
  });

});
```

**{TRUTH_COLUMN_ITEMS} 填充规则：**

从下游真理的 `sql_columns_verified[]` 中找到本表（`table: "{TABLE_NAME}"`）的条目，提取 `columns` 数组，逐个验证：

```javascript
it('service.{function} 引用列 phone 在 DB 中存在', () => {
  expect(allColumns.has('phone')).toBe(true);
});
it('service.{function} 引用列 password_hash 在 DB 中存在', () => {
  expect(allColumns.has('password_hash')).toBe(true);
});
```

🛑 列名从真理取，不需要解析 service 源码。真理写什么就验证什么。
🛑 如果 service 操作了多个表（如 users + login_logs），每个表一个 describe 块。

**{COLUMN_ITEMS} 填充规则：**
```javascript
// 真理列名: ["id", "phone", "password_hash", "nickname"]
it.each(columns)('列 %s 在 {TABLE_NAME} 表中存在', (col) => {
  expect(allColumns).toContain(col);
});
```
🛑 或逐个写 `it('列 phone 在表中存在', () => { expect(columns).toContain('phone'); });`

**{NOT_NULL_ITEMS} 填充规则：**
```javascript
it('phone 为 NOT NULL', () => {
  expect(colMap['phone'].Null).toBe('NO');
});
```

**{TABLE_CONSTRAINT_ITEMS} 填充规则：**

根据场景的 boundary 要求，用 `toContain` 检查 `SHOW CREATE TABLE` 输出：

```javascript
// CHECK 约束 — 场景要求 CHECK stock >= 0
it('CHECK stock >= 0', () => {
  expect(createTable).toContain('CHECK');
});

// FULLTEXT 索引 — 场景要求 products 有 FULLTEXT
it('FULLTEXT 索引存在', () => {
  expect(createTable).toContain('FULLTEXT');
});

// 复合 UNIQUE — 场景要求 UNIQUE(user_id, order_item_id)
it('UNIQUE 约束存在', () => {
  expect(createTable).toContain('UNIQUE');
});

// ENUM 值 — SHOW COLUMNS Type 字段已包含枚举值
it('status ENUM 值正确', () => {
  expect(colMap['status'].Type).toContain('enum');
  expect(colMap['status'].Type).toContain('PENDING_PAYMENT');
});

// FK — SHOW CREATE TABLE 含 FOREIGN KEY 和 REFERENCES
it('FK 约束存在', () => {
  expect(createTable).toContain('FOREIGN KEY');
  expect(createTable).toContain('REFERENCES');
});

// DEFAULT 值
it('status DEFAULT ACTIVE', () => {
  expect(colMap['status'].Default).toBe('ACTIVE');
});
```

🛑 **SHOW COLUMNS 返回结构**：`{ Field, Type, Null('YES'/'NO'), Key('PRI'/'UNI'/'MUL'/''), Default, Extra }`
🛑 **SHOW CREATE TABLE 返回**：`rows[0]['Create Table']` — 完整建表语句，用 `toContain` 检查关键字
🛑 用 `toContain` 验证列名/约束存在，用 `toBe('NO')` 验证 NOT NULL，用 `toBe('PRI')` 验证主键
🛑 列名用反引号包裹传给 MySQL
🛑 同一个 task 操作多个表 → 每个表一个 describe 块，各带自己的 SHOW COLUMNS + SHOW CREATE TABLE
