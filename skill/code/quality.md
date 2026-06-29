# 通用代码质量规范（Code Quality Standards）

本规范适用于所有代码生成任务，无论语言/框架/模块类型。RAG 检索提供领域专项经验，本文档提供普适质量标准。

---

## 一、输入验证与净化（Input Validation）

### 1.1 永远不信任外部输入
- 所有来自 HTTP 请求、消息队列、文件读取、环境变量的数据必须验证
- 类型检查: `typeof` / `Number.isFinite` / `Array.isArray` / 正则匹配
- 范围检查: 数值上下限、字符串长度、数组大小
- 格式检查: email / phone / URL / ISO date 等标准格式

### 1.2 空值与缺失处理
- 必填参数缺失 → 立即返回明确错误（含字段名）
- 可选参数未传 → 使用安全默认值（`??` 而非 `||`）
- 布尔字段未传 → 默认为最安全的选项（通常为 `false` 或最严格限制）

### 1.3 SQL/命令注入防护
- 数据库查询一律使用参数化（`?` 占位符 + 参数数组），禁止字符串拼接 SQL
- 动态表名/列名/ORDER BY 必须使用白名单校验，禁止直接拼入查询
- shell 命令参数化，禁止拼接用户输入到命令字符串

---

## 二、错误处理（Error Handling）

### 2.1 错误传播
- 禁止空 catch 块（`catch(e) {}`）—— 每条异常路径必须有处理动作
- 捕获后至少记录日志 + 返回错误响应或重抛
- 代码层抛出的错误标识使用英文大写常量（`throw new Error('INSUFFICIENT_STOCK')`），禁止中文异常名
  — 这与 HTTP 响应层的用户可见消息不同：controller 捕获后通过 errorMapping 映射为中文 `response.fail(res, '库存不足', 422)`

### 2.2 错误分类
| 错误类型 | HTTP 码 | 处理方式 |
|---------|--------|---------|
| 参数校验失败 | 400 | 返回具体字段和原因 |
| 认证失败 | 401 | 提示登录 |
| 权限不足 | 403 | 提示无权限 |
| 资源不存在 | 404 | 返回资源标识 |
| 业务规则冲突 | 409/422 | 返回冲突原因和解决建议 |
| 系统内部错误 | 500 | 记录完整堆栈，返回通用错误消息 |

### 2.3 Try-Catch 粒度
- 事务边界处必须 try-catch（用于回滚）
- 外部 API 调用处必须 try-catch（超时/网络错误）
- 文件 I/O 处必须 try-catch（权限/不存在/磁盘满）
- 纯计算逻辑不需要 try-catch（让异常自然传播）

---

## 三、空值与边界安全（Null Safety & Edge Cases）

### 3.1 空值合并
```javascript
// ✅ parseInt 返回 NaN 时用 ||（?? 不捕获 NaN）
const port = parseInt(process.env.PORT) || 3000;

// ✅ 对象属性访问用 ??（只有 null/undefined 才用默认值）
const name = obj?.name ?? '默认名称';

// ❌ parseInt(x) ?? default — parseInt(undefined) 返回 NaN，?? 不捕获 NaN
const port = parseInt(process.env.PORT) ?? 3000;
```

### 3.2 边界检查清单
生成代码前逐项确认:
- [ ] 空数组/空字符串/空对象 → 不崩溃，返回合理默认值
- [ ] 数值上限（如库存扣减后为负）→ 拒绝操作，返回明确错误
- [ ] 数值下限（如分页 page < 1）→ 自动修正为安全值
- [ ] 集合大小限制（如批量操作超过最大允许数）→ 拒绝或分批
- [ ] 字符串长度超限（如用户名超过字段定义长度）→ 截断或拒绝
- [ ] 并发重复操作（如同一个订单支付两次）→ 幂等检查

### 3.3 可选链与安全访问
- 嵌套对象访问使用可选链: `obj?.prop?.nested ?? default`
- 数组索引访问先检查长度: `arr.length > 0 ? arr[0] : null`

---

## 四、异步与并发（Async & Concurrency）

### 4.1 Promise 处理
- 所有 async 函数调用必须 `await`（除非明确需要并行）
- Promise.all 用于无依赖的并行操作
- Promise.allSettled 用于部分失败可接受的场景
- 禁止 `new Promise()` 包裹已有 Promise（反模式）

### 4.2 竞态条件防护
- 读-改-写操作: 使用原子条件 UPDATE（`WHERE stock >= ? AND stock - ? >= 0`）或 `SELECT ... FOR UPDATE`
- 计数器增减: 使用 `UPDATE SET count = count + ?` 而非 `SELECT + UPDATE`
- 唯一性约束: 依赖数据库 UNIQUE 约束兜底，而非应用层先查后插

### 4.3 超时与重试
- 外部调用设置合理超时（网络请求 ≤30s，数据库查询 ≤60s）
- 重试仅用于幂等操作（GET、PUT），非幂等操作（POST）重试前检查是否已执行
- 重试使用指数退避，最大重试次数 ≤3

---

## 五、状态一致性与事务（State Consistency & Transactions）

### 5.1 事务边界
- 多表写操作必须在同一事务内
- 事务模板:
  ```
  BEGIN TRANSACTION → 业务操作 → COMMIT
  任一步失败 → ROLLBACK → 返回错误
  ```
- 事务内不要有外部 API 调用（网络 I/O 会导致长事务）

### 5.2 状态机完整性
- 状态变更前检查当前状态是否合法（如订单只能从 PENDING 变为 PAID）
- 终态不可再变更（如 CANCELLED/REFUNDED 状态不可再修改）
- 状态变更记录操作日志（谁、何时、从什么状态变到什么状态）

### 5.3 数据一致性
- 关联数据同步更新（如订单状态变更 → 同步更新库存/积分/优惠券）
- 反规范化的冗余字段保持一致（如订单表的用户昵称与用户表同步）
- 缓存与数据库保持一致（写操作后使失效或更新缓存）

---

## 六、资源管理（Resource Management）

### 6.1 连接与句柄
- 数据库连接使用连接池，不每次手动创建/销毁
- 文件操作后确保关闭句柄（使用 `finally` 或 `try-with-resources`）
- 定时器/监听器在组件销毁时清除（`clearInterval` / `removeEventListener`）

### 6.2 内存
- 大文件/大列表分页或流式处理，禁止一次性加载到内存
- 循环中避免创建大量临时对象（复用或使用对象池）
- 闭包注意引用释放（不再使用的变量置 null）

---

## 七、安全性基础（Security Essentials）

### 7.1 敏感数据
- 密码使用 bcrypt/argon2 哈希，禁止明文存储
- 密钥/Token 从环境变量读取，禁止硬编码
- 日志中禁止输出密码、Token、身份证号等敏感信息

### 7.2 访问控制
- 需要认证的接口必须验证 token 有效性（未过期、未篡改）
- 管理类接口必须校验角色权限（admin）
- 用户只能访问自己的数据（owner check: `req.user.id === resource.userId`）

### 7.2b 中间件契约（Middleware Contract）
🛑 **auth 中间件注入 req 的字段是所有 controller 读取的唯一来源。不匹配 = 全系统鉴权失效。**

auth 中间件 (`middleware/auth.js`) 必须同时设置以下字段：
```js
// JWT 解码后:
req.user = decoded;          // { userId, role, iat, exp }
req.userId = decoded.userId; // 🛑 别名，所有 controller 从 req.userId 读取用户 ID
```

🛑 **所有 controller 统一从 `req.userId` 读取用户 ID，从 `req.user.role` 读取角色。**
禁止 controller 中混用 `req.user.userId` 和 `req.userId`，统一使用 `req.userId`。

### 7.2c 前端认证契约（Frontend Auth Contract）
🛑 **前端 token 存储和读取必须使用统一的 key 名：**
- token 存储 key: `auth_token`（`localStorage.setItem('auth_token', token)`）
- refreshToken 存储 key: `refresh_token`
- 请求头: `Authorization: Bearer {token}`
- 路由守卫从 `localStorage.getItem('auth_token')` 读取
- store 中的 `setToken()` action 负责写入 localStorage，页面禁止直接操作 localStorage

### 7.3 输出编码
- 返回给前端的数据中对 HTML 特殊字符编码（防 XSS）
- JSON 响应使用标准序列化，禁止拼接字符串构造 JSON

---

## 八、代码完整性（Code Completeness）

### 8.1 禁止交付不完整代码
- 禁止 `// TODO` 注释 —— 要么实现，要么明确标记为预留扩展点
- 禁止空函数体（`function foo() {}`）—— 至少抛出 `new Error('Not implemented')`
- 禁止占位返回（`return null` / `return {}`）—— 返回真实数据或错误
- 禁止注释掉的代码块 —— 删除或用版本管理回溯

### 8.2 函数完整性
- 每个导出函数必须有明确的输入 → 处理 → 输出（或错误）
- 正常路径和异常路径都必须有返回语句
- 无副作用的纯函数优先，有副作用的函数在命名上体现（如 `updateAndNotify`）

---

## 九、性能意识（Performance Awareness）

### 9.1 数据库查询
- 避免 N+1 查询: 批量查询用 `WHERE id IN (?)` 替代循环单条查询
- 使用合适的索引（WHERE / JOIN / ORDER BY 的列）
- SELECT 只取需要的列，避免 `SELECT *`
- 分页查询必须带 LIMIT，禁止全表返回

### 9.2 前端性能
- 大列表使用虚拟滚动或分页，禁止一次性渲染上千条
- 图片懒加载（`loading="lazy"`）
- 搜索输入使用防抖（debounce 300ms）
- 路由使用懒加载（`() => import()`）

---

## 十、自检清单（Self-Review Checklist）

代码生成完成后逐项确认。发现任一项未满足 → 修复后重新确认。

| # | 检查项 | 判定 |
|---|--------|------|
| 1 | 所有外部输入都经过验证和净化 | |
| 2 | 所有错误路径都有处理（无空 catch） | |
| 3 | 空值/边界值不会导致崩溃 | |
| 4 | 所有 Promise 都正确 await | |
| 5 | 多表写操作有事务保护 | |
| 6 | 没有硬编码的密钥/密码/Token | |
| 7 | 没有 TODO 或空函数体 | |
| 8 | 没有 `console.log` 用于业务日志（用 logger） | |
| 9 | 函数签名与调用处参数顺序一致 | |
| 10 | 数据库查询使用参数化（无 SQL 拼接） | |
| 11 | 认证接口有 token 校验，管理接口有权限校验 | |
| 12 | 分页查询有 LIMIT，大列表不一次性加载 | |

---

## 十一、三端运行时规范（Runtime Contracts）

以下运行时规范对所有 Agent 具有同等约束力。

### 11.1 通用响应结构
所有 HTTP API 必须返回：
```json
{ "success": true, "code": 200, "message": "操作成功", "data": {} }
```
- 成功统一用 code=200（不用 201/204）
- 后端用 `utils/response.js` 统一方法，禁止直接 `res.status().json()`
- 🛑 **response.success(res, data, message) — data 第二个参数，message 第三个参数**
- 🛑 **绝不允许 `response.success(res, '消息', data)` — 数据被放入 message 字段，客户端收不到业务数据**

### 11.2 状态码
| code | 含义 | 场景 |
|------|------|------|
| 200 | 成功 | 所有成功（含创建/更新/删除） |
| 400 | 参数错误 | 缺失/格式错/校验不通过 |
| 401 | 未认证 | token 无效/过期 |
| 403 | 无权限 | 已认证但权限不足 |
| 404 | 资源不存在 | 查询/更新不存在的记录 |
| 409 | 冲突 | 重复数据/乐观锁冲突 → frontend 用 `reload_data` |
| 422 | 业务错误 | 库存不足/状态不允许 |
| 500 | 服务器错误 | 未知异常 |

### 11.3 分页响应
列表接口 data 含 `{ list, total, page, pageSize }`。`page` 默认 1，`pageSize` 默认 20。

### 11.4 数据类型映射
| 数据库 | 后端 | JSON | 前端 |
|--------|------|------|------|
| DECIMAL(M,D) | string | 字符串 | `parseFloat` 后使用 |
| TINYINT(1) | boolean | true/false | boolean |
| INT/BIGINT | number | 数字 | number |
| TIMESTAMP | string(ISO 8601) | 同左 | `new Date()` |

🛑 **后端返回 DECIMAL 时必须转字符串**，防止精度丢失。

### 11.5 db.query 返回值
`config/db.js` 的 `query()` 已解构 `pool.execute`，调用方**不能再解构**：
```js
// ❌ const [rows] = await db.query(...)
// ✅ const rows = await db.query(...)
// rows 是数组，单行也是 [{...}]。写操作返回 ResultSetHeader { affectedRows, insertId }
```

### 11.6 envDependencies 白名单
只有代码中实际 `process.env.X` 引用了的第三方服务变量才写入 `envDependencies`：
| 服务 | 变量 | 触发条件 |
|------|------|---------|
| 短信 | `SMS_API_KEY`, `SMS_API_SECRET`, `SMS_TEMPLATE_ID` | 代码中发送了短信 |
| 微信支付 | `WECHAT_PAY_*` | 代码中调用了微信支付 API |
| 支付宝 | `ALIPAY_*` | 代码中调用了支付宝 API |
| 微信OAuth | `WECHAT_APP_ID`, `WECHAT_APP_SECRET` | 代码中调用了微信登录 |
| OSS | `OSS_*` | 代码中上传了文件 |
| ES | `ELASTICSEARCH_HOST` | 代码中连接了 ES |

基础设施变量（`PORT`, `DB_*`, `JWT_*`, `ENCRYPTION_KEY`, `LOG_LEVEL`, `REDIS_URL`）由 integrator 自动处理，不写入 envDependencies。
