# c: infra 层 — 源码修复

## 下层真理（不可质疑 — 来自 bans_text）
- infra 是最底层，无下层真理。问题一定在本层配置/源码。

## 输入输出对齐
```
infra 输出 → 上层输入:
  config/db.js → db 层连接 MySQL
  utils/response.js → 所有层统一响应格式
  utils/encryption.js → backend 层加密手机号
  .env 四件套 → 所有层读取环境变量
```

## 修复策略

### 缺 npm 依赖
- 症状: `Cannot find module 'express'` / `MODULE_NOT_FOUND`
- 治法: `npm install {package}` 或补 package.json dependencies

### ECONNREFUSED
- 症状: `ECONNREFUSED 127.0.0.1:3306` 或 `6379`
- 查 .env 中 DB_HOST/DB_PORT/REDIS_URL 是否正确

### utils/response.js 函数签名错（最高频）
- 症状: 测试断言 `expect(res.json).toHaveBeenCalledWith(...)` 不匹配
- 🛑 **函数签名来自测试场景，不是自己编的**：
  - `success(res, data, message)` → 返回 `{success:true, data, message}`
  - `error(res, code, message)` → 返回 `{success:false, code, message, data:null}`
- 🛑 **禁止新增测试未要求的函数**：只实现 success/error，不写 fail/unauthorized/forbidden
- 🛑 **禁止修改参数顺序**：测试定了 `(res, data, message)` 就照这个写，不能自己改成 `(res, message, data)`
- 治: 对照 testScenarios.then 逐行写函数体，测试说什么就写什么

### db.query 不是函数
- 症状: `TypeError: db.query is not a function`
- 原因: config/db.js 未导出 query
- 治: 补全 `module.exports = { pool, query, beginTransaction, commit, rollback }`

### .env 变量集不一致
- .env / .env.example / .env.development / .env.production 四文件 key 集合必须一致
- 治: 以 .env.example 为基准，补齐缺失变量

## 工具选择
- 整个文件多处错 → `create_file` 重写
- 单行配置错 → `edit_batch`
