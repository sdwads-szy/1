# db-api 检查模板 (Layer 3: db_api) — SQL列名 vs DDL一致性

```javascript
const fs = require('fs');
const path = require('path');
const workspace = process.env.WORKSPACE || '../../';

describe('{task_id}', () => {
  // 读取目标 service 文件, 提取所有 SQL 列名
  const serviceFile = path.join(workspace, '{targetFile}');
  const serviceCode = fs.readFileSync(serviceFile, 'utf-8');
  
  // 读取 DDL 获取合法列名
  const ddlFiles = ['{related DDL files}'];
  const ddlColumns = new Map(); // tableName -> Set(columnNames)
  ddlFiles.forEach(f => {
    const ddl = fs.readFileSync(path.join(workspace, f), 'utf-8');
    const tableMatch = ddl.match(/CREATE TABLE.*?`(\w+)`/);
    if (tableMatch) {
      const cols = [...ddl.matchAll(/`(\w+)`\s+(VARCHAR|INT|DECIMAL|TEXT|JSON|TIMESTAMP|ENUM|TINYINT)/gi)];
      ddlColumns.set(tableMatch[1], new Set(cols.map(c => c[1])));
    }
  });

  it('所有 INSERT/SELECT 列名在 DDL 中存在', () => {
    // 提取 service 中的 SQL 列名
    const sqlColumns = [...serviceCode.matchAll(/(?:INSERT\s+INTO|SELECT)\s+`?(\w+)`?\s*\(([^)]+)\)/gi)];
    sqlColumns.forEach(match => {
      const tableName = match[1];
      const columns = match[2].split(',').map(c => c.trim().replace(/`/g, ''));
      const validCols = ddlColumns.get(tableName) || new Set();
      columns.forEach(col => {
        if (col && !col.includes('?') && !col.includes("'")) {
          expect(validCols.has(col)).toBe(true);
        }
      });
    });
  });

  it('事务体内使用 conn.execute() 非 db.query()', () => {
    // 找到 beginTransaction 和 commit 之间的代码块
    const txBlock = serviceCode.match(/beginTransaction\(\)[\s\S]*?commit\(/);
    if (txBlock) {
      expect(txBlock[0]).not.toMatch(/db\.query\(/);
    }
  });
});
```
