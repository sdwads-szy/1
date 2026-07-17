# 示例产物

> 需求："设计一个 B2B2C 多商户线上商城"  
> 系统自动生成的代表性代码，展示了各层的代码质量。

## 文件清单

| 文件 | 说明 | 亮点 |
|------|------|------|
| `app.js` | Express 入口，23 条路由全部注册 | helmet/cors/morgan/errorHandler 完整中间件链，含 `/api/health` 健康检查 |
| `package.json` | 项目配置，14 dep + 16 devDep | jest 单层 testMatch 无 projects，Vue 3 + Element Plus + Pinia |
| `orderController.js` | 订单控制器 | 8 种错误码精确映射 + `response.success/fail/error` 统一响应 |
| `orderService.js` | 订单服务（253行） | 乐观锁扣库存（3次重试指数退避）+ 主订单+子订单+order_items 单事务创建 |
| `sql/orders.sql` | 订单表 DDL | 7 状态 ENUM + 6 索引 + decimal(12,2) 金额精度 |
| `test/t_api_auth.test.js` | 鉴权 API 测试 | 6 维度验证：路由匹配/字段一致/中间件链/错误映射/响应/前端对齐 |

## 测试结果

- 静态层 82 任务：全部通过（Python 确定性校验）
- 接口层 51 任务：全部通过（源码静态分析）
- 逻辑层 6 任务（backend_proc）：全部通过（mock 单元测试）
- **已执行 137/137 任务 100% (TS, SS)**

## 产物规模

| 类型 | 数量 |
|------|------|
| 后端路由 | 23 |
| 控制器 | 23 |
| 业务服务 | 25 |
| 中间件 | 3 |
| SQL 表 | 25 + 26 种子数据 |
| Vue 页面 | 31 |
| 前端 API 模块 | 24 |
| Pinia Store | 2 |
| 测试文件 | 57 |
