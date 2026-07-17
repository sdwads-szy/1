# 项目二：星链商城 — Agent 系统自动生成产物

> 本项目由 [Agent 多智能体代码生成系统](https://github.com/sdwads-szy/1) 全自动生成，未经人工编写或修改。

## 项目背景

输入一句话需求"设计一个 B2B2C 多商户线上商城"，系统经过需求分析→架构设计→代码生成→测试架构→ABCD 测试修复五个阶段，全自动产出包含前端、后端及数据库的完整可运行全栈项目，验证了契约驱动多智能体协作在自动化代码生成中的可行性。

## 系统做了什么

### 1. 需求分析与 UI 设计

PM Agent 联合 10 个角色子Agent（客户/用户/运营/创新/行业/质量/数据/架构/安全/设计）进行 5 轮讨论，产出 27KB 完整 PRD。

- 识别出 5 个主干模块（商品浏览、商家管理、订单履约、用户鉴权、平台运营）和 5 个枝干模块（购物车、售后仲裁、钱包结算、平台审核、物流）
- 将核心交易闭环拆解为 9 步消费者购物链路 + 逆向退款链路 + 商家入驻链路
- 定义 17 个数据实体及关系（users→orders→sub_orders→order_items→payments→refund_requests→settlement_orders→merchant_wallets→withdrawal_requests）
- 5 条关键异常分支（支付超时自动取消/库存不足并发/支付回调丢失/发货后退款/超额提现），含超时标注和降级策略
- Designer Agent 产出完整设计令牌系统：10 级色板（含推导公式 + 暗色模式映射）、4 级阴影、7 级 Z-Index、动效缓动函数、无障碍基线

### 2. 架构设计

架构师 Agent 先构建场景树作为中间产物，再分 5 步生成 209 个结构化契约和 81 个工程任务。

- 场景树覆盖 PRD 全部模块和实体，含 §7 计数校验表强制补全遗漏项
- 7 类契约：model(26) + auth(1) + api(26) + db-api(80) + navigation(45) + scenario(5) + logic(26)，0 个关键字段缺失
- model 契约含完整字段名/类型/NOT NULL/DEFAULT/UNIQUE/PRIMARY KEY/FOREIGN KEY/indexes/seedData
- api 契约含 method/path/request fields/response/errors/中间件链
- logic 契约含 serviceSignature/input/output/process 步骤/transactionBoundary/apiMapping/dbApiMapping/nfr 约束
- 81 个工程任务按类型分层：infra(10) → db(25) → frontend(21) → backend(24) → integration(1)，显式声明依赖链

### 3. 源代码生成

5 类工程师 Agent 按依赖拓扑排序分层并发执行，通过真理传递机制保证跨模块接口一致。

- infra：package.json 含 14 个生产依赖 + 16 个开发依赖，jest 单层 testMatch 无 projects 配置，3 个中间件 + 3 个配置模块 + 统一响应工具
- db：25 张 SQL 表全部通过语法检查（括号配对/尾随逗号/重复索引名/重复列名/AUTO_INCREMENT 缺 PRIMARY KEY），26 个种子数据文件 FK 引用一致性通过
- frontend：31 个 Vue 页面含路由懒加载 + 角色守卫 + Token 过期自动跳转，24 个 API 模块端点与后端路由对齐
- backend：23 个控制器全部使用统一响应格式（response.success/fail/error）+ 错误码精确映射，25 个服务含乐观锁扣库存（3 次重试指数退避）、主订单+子订单+order_items 单事务创建
- 真理传递：每个 Agent 完成后输出结构化真理 JSON（exposed_to_upper + exposed_to_peers），下游 Agent 通过依赖链加载上游接口签名，字段名/路径/签名不可偏离
- 代码质量：78 个后端 JS 文件 node --check 0 语法错误

### 4. 测试任务生成

测试架构师 Agent 先构建测试场景树，再分层生成 173 个测试任务。

- 静态层 82 个任务：全部含 checkPoints（确定性检查点），如"package.json 可解析为合法 JSON""AUTO_INCREMENT 列必须有 PRIMARY KEY""src/ 下禁止 require/module.exports"
- 接口层 51 个任务：含 testScenarios（场景化验证集），覆盖正向/异常/边界/鉴权四个维度，如"有效 token→200""过期 token→401""无 token→401"
- DB-API 测试 t_dbapi_order：单个测试文件 94 个断言，逐字段/逐约束/逐 FK/逐 ENUM 值对比 DDL 与契约
- 逻辑层 31 个任务：验证多步 DB 操作顺序 + 事务边界 + 错误回滚 + 跨步数据传递
- 场景层 5 个任务：验证端到端数据交接（浏览→加购→结算→下单→支付→发货→确认收货全链路参数不丢失）
- 质量层 9 个任务：SQL 注入/XSS/Token 安全/限流/并发/可用性/HTTPS

### 5. 测试与修复

ABCD 闭环多轮迭代，137 个已执行测试任务全部收敛至 (TS,SS)。

- 静态层直通：Python 确定性校验（node --check/esbuild/DDL vs 契约对比/种子数据 FK 引用/路由双向验证/死路由清理/env 变量对齐），无需进入 ABCD 循环
- 接口层：平均 1.4 轮收敛，大部分 1 轮直接通过。测试验证的是路由注册正确性、字段名一致性、中间件链完整性、错误码映射完整性、前后端端点对齐
- 逻辑层（backend_proc）：mock 数据库验证多步操作顺序 + 事务 commit/rollback + 返回值结构，复杂任务如 t_bp_add_cart 3 轮收敛
- Ban 记忆：21 条 test_failure + 12 条 source_failure 持久化，每轮末自动清理已通过任务的无效 Ban
- 最终状态：137/137 (TS,SS)，78/78 语法通过，无死循环或无法收敛的任务

## 项目成果

| 类型 | 数量 | 质量指标 |
|------|------|------|
| PRD 文档 | 1 份 (27KB) | 7 章完整，5 主干+5 枝干，17 实体关系 |
| UI 设计文档 | 10 个 | 完整设计令牌 + 暗色模式 + 无障碍 |
| 架构契约 | 209 个 | 7 类，0 关键字段缺失 |
| 工程任务 | 81 个 | 5 类，全部含 outputFiles + dependencies |
| 后端路由 | 23 个 | 与磁盘文件双向对齐 |
| 控制器 + 服务 | 48 个 | 统一响应格式 + 错误码映射 |
| SQL 表 + 种子 | 51 个 | DDL 与契约逐字段一致 |
| Vue 页面 | 31 个 | 路由懒加载 + 角色守卫 |
| API 模块 | 24 个 | 端点与后端对齐 |
| 测试文件 | 57 个 | 通过率 100% |
| 后端语法 | 78 文件 | 0 错误 |

## 源码

完整项目源码位于 [work/project/](../work/project/)。

## License

MIT
