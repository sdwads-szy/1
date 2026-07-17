# 代码可读性规范

所有生成的代码必须遵循以下命名、结构、注释规范。

## 命名规范

| 类别 | 风格 | 示例 |
|------|------|------|
| 后端 route | camelCase | `routes/auth.js`, `routes/order.js` |
| 后端 controller | camelCase | `controllers/authController.js` |
| 后端 service | camelCase | `services/authService.js` |
| 前端页面 | PascalCase | `Login.vue`, `ProductDetail.vue` |
| 前端 API 模块 | camelCase | `src/api/auth.js`, `src/api/order.js` |
| 前端 store | camelCase | `src/stores/user.js` |
| SQL 文件 | snake_case | `database/schema/users.sql` |
| JS 变量/函数 | camelCase | `getOrderList`, `userId`, `payAmount` |
| 数据库字段 | snake_case | `order_id`, `created_at`, `pay_amount` |
| 数据库表名 | 复数 snake_case | `users`, `order_items`, `payment_logs` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT`, `DEFAULT_PAGE_SIZE` |
| Vue 组件 | PascalCase | `ProductList`, `OrderDetail` |
| 路由路径 | kebab-case | `/product-detail`, `/order-list` |

## 代码结构

### 后端文件
```js
// 1. 核心模块 → npm 包 → 项目模块
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const db = require('../config/db');
const response = require('../utils/response');

// 2. 常量
const MAX_RETRY = 3;

// 3. 私有函数
function validate(data) { ... }

// 4. 公开导出
module.exports = { createOrder, getOrderList };
```

### 前端 Vue SFC
```html
<template><!-- 模板 --></template>
<script setup>
// 1. imports  2. props/emits  3. composables
// 4. state  5. computed  6. methods  7. lifecycle
</script>
<style scoped>/* 样式 */</style>
```

### import 排序
核心模块 → npm 包 → 项目模块（`@/`）→ 相对路径。不同类型间空一行。

## 注释规范

### 后端
- 每个导出函数必须有 JSDoc（`/**` 开头，`@param`/`@returns`）
- 事务/锁操作必须有行内注释说明意图
- 路由文件头部 `// @mount /api/模块名`

### 数据库
- 每张表 `COMMENT='表描述'`
- 每个字段 `COMMENT '描述'`，ENUM 字段注释取值含义
- 复杂查询注释业务意图和索引策略

### 前端
- 组件 `<script setup>` 顶部注释用途
- Props/Emits 注释类型和含义
- API 模块 `// @api 模块描述` + 每个函数注释

### 配置文件
- `.env.example` 每个变量注释用途和格式约束
- `package.json` scripts 注释用途
