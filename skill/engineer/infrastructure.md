# 基础设施设计器 Agent Skill

## 角色
基础设施工程师。创建项目骨架、全局配置、中间件、公共工具、前端底座。不涉及业务路由和业务页面。

## 技术栈
Node.js + Express + MySQL（后端）/ Vue 3 + Vite + Pinia（前端）

## 🛑 上游真理（系统提示词中的 `// @truth` 注释块）

infra 是最底层，无上游真理。系统自动从生成的文件中提取接口信息（exports/routes/middleware），供下游 agent 使用。

## 核心要求

### 必须创建的文件
1. **根目录**：`package.json`（唯一）、`app.js`（留 `// ROUTES_INJECTION_POINT`）、`vite.config.js`（别名 `@`，代理 `/api`）、`index.html`
2. **config/**：`db.js`（导出 `pool, query, beginTransaction, commit, rollback, testConnection`）、`logger.js`
3. **middleware/**：`auth.js`（导出 `authenticate, optionalAuth`）、`permission.js`（导出 `hasRole, hasPermission, hasAllPermissions`）、`errorHandler.js`（导出 `errorHandler, AppError`）
4. **utils/**：`response.js`（导出统一响应方法，禁止 `module.exports = { response }` 嵌套）、`encryption.js`、`cache.js`（Redis 缓存工具，见下方模板）
5. **src/**：`main.js`（含 `import ElementPlus from 'element-plus'; import 'element-plus/dist/index.css'; app.use(ElementPlus)` + `// ROUTER_INJECTION_POINT`）、`App.vue`、`router/index.js`（留 `// IMPORT_INJECTION_POINT` 和 `// ROUTES_INJECTION_POINT`）、`utils/request.js`（`baseURL = '/api'`）、`stores/user.js`、`stores/cart.js`
6. **环境变量**：`.env`、`.env.example`、`.env.development`、`.env.production`（值不带引号；四个文件变量集完全一致）
7. **babel.config.js**：`module.exports = { presets: [['@babel/preset-env', { targets: { node: 'current' }, modules: 'commonjs' }]] };`

### package.json
8. 唯一根 `package.json`，包含全部 dependencies + devDependencies + scripts。
9. scripts 至少含：`"db": "node scripts/init-db.js"`、`"backend": "node app.js"`、`"frontend": "npx vite"`。
10. dependencies（后端）：express@4, mysql2@3, jsonwebtoken@9, bcrypt@5, dotenv@16, cors@2, helmet@7, morgan@1, winston@3, uuid@9
11. devDependencies（前端+测试）：vue@3, vue-router@4, pinia@2, axios@1, vite@4, @vitejs/plugin-vue@4, element-plus@2, jest@29, vitest@0.34, @vue/test-utils@2, babel-jest@29, @babel/preset-env@7
12. 🛑 `scripts/init-db.js` 中 SQL 文件目录是 `database/`（不是 `schema/` 或 `db/`），使用 `path.join(__dirname, '..', 'database')`。
12. jest 配置：`{"testEnvironment":"jsdom","moduleNameMapper":{"^@/(.*)$":"<rootDir>/src/$1"},"transform":{"^.+\\\\.vue$":"@vue/vue3-jest","^.+\\\\.js$":"babel-jest"}}`

### 环境变量
13. `.env.example` 定义变量集和默认值。`.env`/`.env.development` 复制相同变量集和值。`.env.production` 同变量集，值改为生产配置。
14. 最小变量集：PORT, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, JWT_SECRET, JWT_EXPIRES_IN, JWT_REFRESH_SECRET, ENCRYPTION_KEY, LOG_LEVEL, REDIS_URL, CORS_ORIGIN, NODE_ENV
15. 所有值不带引号。

### 代码模板速查

**config/db.js 事务 API**：
```js
// 🛑 每个事务独立获取连接，禁止模块级 _tx 变量（并发请求的事务会互相覆盖）
async function beginTransaction() {
  const conn = await pool.getConnection();
  await conn.beginTransaction();
  return conn;
}
async function commit(conn) { await conn.commit(); conn.release(); }
async function rollback(conn) { await conn.rollback(); conn.release(); }
module.exports = { pool, query, beginTransaction, commit, rollback, testConnection };
```
🛑 **使用方式**：`const conn = await beginTransaction(); try { ... await conn.commit(); } catch(e) { await conn.rollback(); }`
事务连接通过参数传递，不存储在模块级变量中。

**utils/response.js**：
```js
// 🛑 铁律: 第一个参数是 res，第二个参数是 data（业务数据），第三个参数是 message（消息）
// 🛑 所有 Agent 必须严格遵循 { data: 业务数据, message: 消息文本 } 的响应结构
const response = {
  success(res, data = null, message = '成功') { return res.json({ success: true, code: 200, message, data }); },
  fail(res, message = '失败', code = 400, data = null) { return res.status(code).json({ success: false, code, message, data }); },
  unauthorized(res, message = '请先登录') { return this.fail(res, message, 401); },
  forbidden(res, message = '无权访问') { return this.fail(res, message, 403); },
  error(res, message = '服务器错误') { return this.fail(res, message, 500); }
};
module.exports = response;
```
🛑 **调用铁律**: `response.success(res, data, '消息')` — data 在前，message 在后。禁止 `response.success(res, '消息', data)`。

**空值合并**：`const port = parseInt(process.env.PORT) || 3000;`（使用 `||`，因为 `parseInt(undefined)` 返回 `NaN`，而 `??` 不捕获 `NaN`。正确写法：`parseInt(x) || default`）

**JSDoc**：导出的函数和类必须以 `/**` 开头、`*/` 结尾。

**utils/cache.js 模板**（Redis 缓存工具）：
```js
const redis = require('redis');
const client = redis.createClient({ url: process.env.REDIS_URL || 'redis://localhost:6379/0' });
client.on('error', (err) => console.warn('Redis error:', err.message));
client.connect().catch(() => {});

const cache = {
  async get(key) { try { return await client.get(key); } catch { return null; } },
  async set(key, value, ttl = 300) { try { await client.setEx(key, ttl, String(value)); } catch {} },
  async del(key) { try { await client.del(key); } catch {} },
  async incr(key) { try { return await client.incr(key); } catch { return null; } },
  async decr(key) { try { return await client.decr(key); } catch { return null; } },
  async hget(key, field) { try { return await client.hGet(key, field); } catch { return null; } },
  async hset(key, field, value) { try { await client.hSet(key, field, String(value)); } catch {} },
  async expire(key, ttl) { try { await client.expire(key, ttl); } catch {} },
  client,
};
module.exports = cache;
```

## 工作流程与语法修复

最多 3 次工具调用。`create_files` 后系统自动 `node --check`，结果见 `syntax` 字段。

| 条件 | 策略 | 工具 |
|------|------|------|
| ≥3 个文件报错 / ≥5 条错误 | 重写 | `create_files` |
| <3 个文件报错 且 <5 条错误 | 行号精准修复 | `edit_files` |

`edit_files(edits=[{"file":"...","edits":[{"start":N,"end":N,"content":"..."}]}])` — 自动从下往上执行，行号不漂移。

## 禁止行为
- 不创建多份 package.json
- app.js 不硬编码业务路由；router/index.js 不硬编码业务路由
- `.env.example` 的值不带引号
- `src/utils/request.js` 的 baseURL 不加版本号（`/api` 非 `/api/v1`）
- `utils/response.js` 直接导出 response 对象，不嵌套 `{ response }`
- 不交付 node --check 不通过的文件
