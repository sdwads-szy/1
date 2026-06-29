# 数据库检查模板 (Layer 1: db)

## 🛑 禁用铁律
- **禁止 `jest.mock()` / `jsdom`** — 纯文件内容对比
- **禁止正则匹配** — 用 `expect(src).toContain('列名')` 逐列检查
- **禁止 HTTP 调用** — 不连数据库, 只读 .sql 文件

## 正确写法

```javascript
const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '../..');

describe('{task_id}', () => {
  const ddl = fs.readFileSync(path.join(workspace, '{targetFile}'), 'utf-8');

  it('表名存在', () => {
    expect(ddl).toContain('CREATE TABLE');
    expect(ddl).toContain('{tableName}');
  });

  it('列 {fieldName} {fieldType} 存在', () => {
    expect(ddl).toContain('{fieldName}');
  });

  it('日志表无 DROP TABLE', () => {
    expect(ddl).not.toMatch(/DROP\s+TABLE/i);
  });
});
```
