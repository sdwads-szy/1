# 基础设施检查模板 (Layer 0: infra)

## 🛑 禁用铁律
- **禁止 `jest.mock()`** — infra 测试不需要 mock 任何模块
- **禁止 `jsdom`** — testEnvironment 必须是 `node`（默认），不是 `jsdom`
- **禁止 `supertest` / `axios` / HTTP 调用** — 这是纯文件静态验证
- **禁止复杂正则** — 用 `expect(src).toContain('字符串')` 替代正则匹配（正则容易写错导致语法错误）
- **禁止多行 expect 链** — 每个 it() 只做 one thing，用完就关括号

## 正确写法（直接照抄结构，替换括号内容）

```javascript
/** @jest-environment node */
const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '../..');

describe('{task_id}', () => {
  it('{scenario}', () => {
    const src = fs.readFileSync(path.join(workspace, '{targetFile}'), 'utf-8');
    expect(src).toContain('{then_clause_keyword}');
  });
});
```

示例:
```javascript
it('success(res, data, message) 签名正确', () => {
  const src = fs.readFileSync(path.join(workspace, 'utils/response.js'), 'utf-8');
  expect(src).toContain('success(res, data, message)');
});

it('中间件注入 req.userId', () => {
  const src = fs.readFileSync(path.join(workspace, 'middleware/auth.js'), 'utf-8');
  expect(src).toContain('req.userId');
});

it('init-db.js 使用 database/ 目录', () => {
  const src = fs.readFileSync(path.join(workspace, 'scripts/init-db.js'), 'utf-8');
  expect(src).toContain('database');
});

it('env 文件变量集一致', () => {
  const envFiles = ['.env', '.env.example', '.env.development', '.env.production'];
  const keys = envFiles.map(f => {
    const c = fs.readFileSync(path.join(workspace, f), 'utf-8');
    return c.split('\n').filter(l => l.trim() && !l.startsWith('#')).map(l => l.split('=')[0].trim()).sort().join(',');
  });
  keys.forEach(k => expect(k).toEqual(keys[0]));
});

it('auth middleware 导出 authenticate', () => {
  const auth = require(path.join(workspace, 'middleware/auth'));
  expect(typeof auth.authenticate).toBe('function');
});
```

## 关键规则
1. 每个 it() 里最多 5 行代码, 只做一件事
2. 用 `expect(src).toContain('xxx')` 替代所有正则
3. `require` 用绝对路径 `path.join(workspace, 'xxx')`
4. 不需要 `beforeEach` / `afterEach` / `jest.clearAllMocks`
5. 从 testScenarios 的 `then` 字段提取关键词作为 `toContain` 的参数
