# 场景树制作 — Agent 可执行规范

## 角色
从 PRD 提取结构化信息，输出**Agent 可直接执行的规范**——不是设计文档，而是"伪代码+状态机+API Schema"的混合体。

## 三大原则

1. **只写"是什么"和"怎么做"，不写"为什么"** — Agent 不需要知道"为什么选 JWT"，只需要知道 payload 有哪些字段、过期多长
2. **每个错误码配决策树** — 不只写 `422 INSUFFICIENT_STOCK`，要写 Agent 收到后该做什么（提示用户？重试？切换流程？）
3. **所有定义可执行** — 状态机是代码、补偿是步骤清单、数据流是字段传递链

---

## 🛑 场景树 6 章节

### §1 模块清单
表格: 编号/名称/主干枝干/前台能力(API列表)/后台能力(API列表)/数据实体(表名)/估算页面数
🛑 能力列直接写 API 候选名，不是能力描述。

### §2 业务流程图 — Agent 决策树

每条业务链路一个表格。列:

| 步骤 | 动作 | logic | api | 输入(字段+来源) | 输出(字段+去向) | 校验规则 | 错误码→Agent动作 | 事务边界 | 补偿路径 | 基础设施 |
|------|------|-------|-----|----------------|----------------|---------|-----------------|---------|---------|---------|

**错误码→Agent动作 格式**:
```
401 UNAUTHORIZED → redirect(/auth/login), preserve_state=true
422 INSUFFICIENT_STOCK → 读取 available_stock, >0则提示"仅剩N件"允许修改数量, ==0则标记SKU不可选
409 CONCURRENCY → 提示"库存紧张请重试", 不自动重试, 保留购物车状态
```

**补偿路径 格式**（步骤清单而非文字描述）:
```
order_timeout_cancel:
  触发: BullMQ延迟任务(order.created_at + 30min)
  1. SELECT status WHERE id=? → 如果不是pending则终止(幂等)
  2. BEGIN TX: UPDATE status='cancelled' → UPDATE skus SET stock=stock+? → 退券 → COMMIT
  3. affected_rows==0 → ROLLBACK, 重试3次(间隔5s), 仍失败→告警
  4. 发送通知(失败不影响主流程, 记retry_queue)
```

🛑 校验规则/补偿路径：只在 PRD 明确提到时补充。
🛑 **基础设施列必填**：只要步骤涉及外部服务（支付/短信/物流/OAuth/邮件/OSS/搜索/队列），必须标注。不能留 `—`。
   - `POST /payments/mock` → 基础设施: 微信支付/支付宝SDK
   - `sendSms/sms/短信` → 基础设施: 短信通道API
   - `物流/tracking/logistics` → 基础设施: 物流查询API
   - `微信登录/OAuth` → 基础设施: 微信开放平台
   - `搜索/ES` → 基础设施: Elasticsearch
   - `队列/BullMQ` → 基础设施: Redis + BullMQ

**§2 附加: 上下文传递链**

在流程表格之后列出跨步骤共享字段:

```
Context:
  userId, token, role: S1 → 全链路 (token过期→调refresh, 失败→回退S1)
  productId: S4 → S5, S8
  cartItemIds: S6 → S7, S8 (S7时过滤下架商品并提示用户)
  orderId, orderNo: S8 → S9, S10, S11, S12
  paymentId: S9 → S10, S12
```

🛑 只列跨≥2步传递的字段，标注过期/异常处理。

### §3 数据实体地图

- **§3.1 实体关系**: `表A (1) ──< 表B (N)` 格式
- **§3.2 实体摘要**: 每表 表名 + 2~4个关键字段 + FK + 状态机，≤5行
- **§3.3 关键约束**: UNIQUE/FK/加密
- **§3.4 状态机矩阵（可执行格式）**:

```
orders.status:
  pending  → pay_success: paid
  pending  → cancel: cancelled (用户主动)
  pending  → timeout: cancelled (30min超时)
  paid     → ship: shipped
  paid     → refund_full: refunded
  shipped  → receive: completed
  shipped  → auto_receive: completed (7天自动)
  cancelled, completed, refunded → 终态(不可变更)
```

🛑 每行 `当前状态 → 事件: 新状态 (触发条件)`。Agent 可直接翻译为代码。

- **§3.5 并发策略**: 只写 PRD 提到的。`扣库存: SELECT FOR UPDATE(悲观锁, 等锁3s)` 或 `领券: WHERE claimed<total(乐观锁CAS, 重试3次指数退避)`

### §4 页面导航图

表格: 文件路径/路由/说明/scope/从哪来→到哪去/ui_style/性能要求

🛑 **文件路径必须以 `src/` 开头**（如 `src/pages/index.vue`，不是 `pages/index.vue`）。
🛑 **`ui_style` 列必填**：先读取 `Memory/ui_styles/` 目录获取实际存在的 UI 文档列表，然后将每个页面匹配到最接近的文档，文件名就代表了当前文档是给什么场景用的。**只填实际存在的文档名**（不含 .md 后缀）。没有匹配的填 `?` 并标注缺失。
🛑 性能要求只在 PRD 提到时标注。`列表>50条→虚拟滚动` `SKU矩阵<50ms`

### §5 鉴权需求

| 维度 | 值 |
|------|----|
| Token | JWT, payload: {userId:int, role:string, iat, exp}, access 2h, refresh 7d |
| 传输 | Authorization: Bearer {token}, 全站HTTPS |
| 存储 | access_token 内存, refresh_token HttpOnly Cookie SameSite=Strict |
| 中间件 | authenticate(401→redirect /login), requireRole(403→提示无权) |
| 守卫 | /cart, /checkout, /orders/* → requiresAuth; /merchant/* → requiresMerchant; /admin/* → requiresAdmin |
| 敏感操作 | 换绑手机→短信验证, 支付回调→RSA验签 |
| 刷新 | token过期→POST /auth/refresh {refresh_token}, 成功→更新内存token, 失败→回退S1 |

### §6 契约预估

🛑 model≥PRD实体数, api≥有能力模块数, logic≥流程节点/2, scenario=链路数(~3-6)

---

## 外部依赖降级策略（PRD 提到才写）

| 依赖 | 正常路径 | 降级路径 | Agent 处理 |
|------|---------|---------|-----------|
| 微信OAuth | 跳转授权 | 不可用 | 切换到手机号登录, 提示"微信登录暂不可用" |
| OCR识别 | 识别营业执照 | 超时/失败 | 标记"人工审核", 不阻塞提交 |
| 图片审核 | API检测违规 | 服务超时 | 标记"机审跳过", 进入人工队列 |
| 支付回调 | 异步通知 | 通知丢失 | 定时主动查单(每5min, 最多12次) |
| 物流API | 查询轨迹 | 查询失败 | 显示"物流信息更新中", 不阻塞确认收货 |

🛑 PRD 提到哪个写哪个，没提到的跳过整节。

---

### §7 覆盖计数表（强制自检 — 先算后写）

🛑 生成完 6 章节后，必须逐项计数并填写下表。任何 ❌ → 补全对应条目后再输出 `[场景树完成]`。

```markdown
| 维度 | 应有数量 | 实际数量 | 覆盖? |
|------|:---:|:---:|:---:|
| 模块(主干) | PRD一期模块数 | ? | ✅/❌ |
| 数据实体 | PRD实体数 | ? | ✅/❌ |
| 业务链路 | ≥主干模块数 | ? | ✅/❌ |
| 流程节点(logic候选) | PRD流程节点数 | ? | ✅/❌ |
| API候选 | 有能力模块数 | ? | ✅/❌ |
| 页面 | PRD估算页面数 | ? | ✅/❌ |
| NFR维度 | PRD NFR维度数 | ? | ✅/❌ |
| ── 接口层预估（Step 2 自检用）── | | | |
| api 契约数 | ≥ §1 模块表中所有能力列的去重 api 候选数 | ? | ✅/❌ |
| db-api 契约数 | ≥ §2 流程中所有涉及 DB 操作的去重数 | ? | ✅/❌ |
| navigation 契约数 | ≥ §4 页面导航中所有相邻页面对数 | ? | ✅/❌ |
| auth 契约数 | 1（有鉴权需求就有） | ? | ✅/❌ |
```

🛑 每一个 ❌ 都必须有对应补全动作。不允许 "TODO" 或 "待补充"。
🛑 接口层 4 行是 Step 2 生成契约时的**数量底线**——少于此数说明遗漏了模块能力或页面跳转。

---

## 构建规则

🛑 场景树 = Agent 可执行规范。状态机可翻译为代码，错误码配有决策树，补偿路径是步骤清单。
🛑 核心 6 章节 + §7 覆盖计数表 必填。外部依赖降级策略仅当 PRD 提到时写。
🛑 不写"为什么"（设计哲学），只写"是什么"和"如果A则B"（可执行规则）。

---

## 执行指令

### 任务
制作场景树（全局规划）。**自上而下**，一次性消化 PRD 全文，产出结构化规划树。

### 生成顺序（铁律）
1. 先写完 §1-§6 全部内容
2. 再逐项填写 §7 计数表
3. 发现 ❌ 则回头补全对应章节
4. 全部 ✅ 后才 create_file

### 写入策略（最多3次）
- 第1次: create_file → 完整场景树 + §7 计数表
- 第2次: 对照 §7 逐项检查，有 ❌ 则补全 → 更新文件
- 第3次: 最终确认 §7 全部 ✅ → 输出 `[场景树完成]`

### 禁止行为
- 禁止写多个文件或摘要文件（只有一个 `_scene_tree.md`）
- 禁止跳过 §7 计数校验（任何 ❌ 必须补全）
- 禁止 "TODO" 或 "待补充" 占位

### 产物
🛑 唯一产物由动态上下文中的文件路径指定。用 `create_file` 写入。
🛑 完成后输出 `[场景树完成]`。
