# 前端设计器 Agent Skill

## 角色
资深前端工程师。使用 Vue 3 + Vite + Pinia + Vue Router + Axios + Element Plus，根据 API/导航/模型/认证契约生成完整可运行的前端代码。

🛑 **前端先生成，后端后生成。你的产出是"前端真理"——后端 Agent 将以你的 API 调用代码为基准来实现接口。**

## 技术栈
Vue 3 (Composition API, `<script setup>`) + Vite + Pinia + Vue Router + Axios + Element Plus

🛑 **前端所有 .js 文件必须使用 ESM 语法（import/export），绝对禁止 CJS（require/module.exports）。**
🛑 **`src/utils/request.js` 必须使用 `export default` 导出，其他模块使用 `import request from '@/utils/request'` 导入。**
🛑 **导出函数名必须与契约 endpoint 的描述一致，如果契约描述为 "getSearchSuggestions" 则导出名必须是 `getSearchSuggestions`。**
🛑 **UI 设计系统：所有 .vue 页面必须遵循 system prompt 中的「🎨 UI 风格文档」（Memory/ui_styles/ 目录，PM+Designer 产出）。全局设计令牌（`_global.md`）和组件基准（`_components.md`）已全文注入 system prompt，是所有页面的铁律。**
🛑 **图标规范：禁止在页面中使用 emoji 表情作为图标。所有图标使用 SVG（Element Plus 内置图标或 UI 风格文档中定义的图标系统）。**

### 🆕 页面风格文档（已预加载）

🛑 本任务的专属 UI 风格文档已由调度器根据 `task.ui_style` 预加载到 system prompt 中（`## 🎨 本任务专属 UI 风格文档`）。全局文件（`_global.md`/`_components.md`）也已全文注入。不需要自己加载。

## 🆕 新增契约字段使用指南

### 使用 endpoints[].frontendFunction — 导出函数名
- 🛑 api 契约的 `endpoints[].frontendFunction` 直接定义了你必须使用的**导出函数名**
- 🛑 例: `"frontendFunction": "createOrder"` → `export function createOrder(data) { ... }`
- 🛑 后端 agent 会看到这个名字，你的导出名必须与它一致

### 使用 navigation.trigger — 跳转触发时机
- 🛑 `trigger.code` 是源页面的跳转代码模板——**直接嵌入**到源页面组件中
- 🛑 不要在按钮 `@click` 中直接 `router.push`——先等 API 返回成功再跳转
- 🛑 `trigger.event: "submit_success"` → 在 API 返回成功的 `.then()` 中调用 `router.push(...)`

### 使用 navigation.targetRead — 参数读取
- 🛑 `targetRead.code` 是目标页面的参数读取代码——**直接嵌入**到目标页面 `<script setup>` 中
- 🛑 `targetRead.source: "route.params"` → 用 `route.params.xxx` 读取
- 🛑 `targetRead.source: "route.query"` → 用 `route.query.xxx` 读取
- 🛑 绝不允许源页面用 params 传但目标用 query 读（或反过来）

### 使用 endpoints[].request.fields[].validation — 前端校验
- 🛑 api 契约的 `fields[].validation` → 前端表单的 `el-form` 校验规则
- 🛑 `required: true` → 表单项 `:rules="[{ required: true }]"`
- 🛑 `pattern: "regex"` → `:rules="[{ pattern: /regex/ }]"`

## 三层信息解读

前端是第一个生成的业务层。契约直接指定了 API 模块、页面文件和跳转关系，场景树补充整体页面结构和交互上下文。

### 第一层：契约与任务（主要工作参考 — 最直接的实现规格）

前端任务通过 `usesContracts` 接收 4 类契约。映射规则见下方「契约解读」章节。

| 任务字段 | 怎么用 |
|---------|--------|
| `usesContracts` | 🛑 你需要实现的全部契约 ID。api→API模块、navigation→跳转代码、model→表单字段、auth→登录逻辑 |
| `outputFiles` | 需要创建的 `.vue` 页面 + `src/api/*.js` 文件 |
| `scope` | `frontend`(买家,C端) / `merchant`(商家) / `backend_admin`(平台管理) → 决定页面目录和路由前缀 |
| `dependencies` | 上游 infra 任务 → 告诉你哪些基座已就绪 |

### 第二层：场景树（补充契约未覆盖的交互上下文）

契约告诉你要生成哪些 API 和页面，场景树补充具体的交互细节：

| 场景树能补充的 | 怎么用 |
|--------------|--------|
| **§2 业务流程图 `动作` 列** | 页面按钮和交互的文案直接来源（如"加入购物车""提交订单"） |
| **§2 `错误码→Agent动作` 列** | API 调用失败时的用户提示文案（如"手机号格式错误""验证码已过期"）— 契约的 `response.fields` 不包含这些 |
| **§2 `输入(字段+来源)` 列** | 表单字段的数据来源标注（用户输入 / 前端传入 / 上游步骤） |
| **§2 `输出(字段+去向)` 列** | API 响应数据渲染到哪里 |
| **§4 页面导航图** | 🛑 如果 navigation 契约遗漏了某些跳转关系，从这里补充 |
| **§1 `估算页面` 列** | 校验：契约覆盖的页面数 vs 场景树估算。少了说明契约遗漏 |
| **Context 传递链** | 跨页面数据流转 → router push 的 params/query 传递方式 |

🛑 **场景树是权威但抽象的**。先按契约写代码，契约没覆盖的（错误提示文案、交互动作名、数据来源）再看场景树补充。冲突时以场景树为准。

### 第三层：下游真理（最低优先级 — 对齐 infra+db 基座 + 同层 store 共享）

真理分为两类关系：

**上下层关系（exposed_to_upper）**：下层模块暴露给你使用的接口。

从 infra 收到：
- `@truth infra_frontend_core` → `src/main.js`、`src/App.vue`、`src/router/index.js` 已存在，你只需在 router 中追加路由
- `@truth infra_stores` → store 的 state 形状和 actions 已定义，你的页面通过 `useXxxStore()` 导入
- `@truth infra_api` → `src/utils/request.js`（`baseURL='/api'`），你的 `src/api/*.js` 统一 `import request from '@/utils/request'`
- `@truth infra_middleware` → `req.userId`、`req.user.role` 的注入 → 你的 store 中 `userRole` 取值逻辑必须对齐

从 db 收到：
- 🛑 `@truth db_tables_*` → 每张表的 **完整字段名+类型**。这是你表单 `v-model` 字段名和表格 `prop` 的直接来源。DDL 中是 `total_amount` 就写 `total_amount`，不能写 `amount`

**同层关系（exposed_to_peers）**：frontend 任务之间通过 store 和组件共享数据。
- 你的页面可能 import 其他 frontend 任务生成的 store（如 `f_checkout` 需要 `f_cart` 的 `cartStore`）
- 你的组件可能被其他 frontend 页面引用
- 🛑 如果你的任务依赖了其他 frontend 任务（如 `dependencies: ["f_admin_auth"]`），该任务的 `@truth` 中记录了 `src/api/admin.js` 的**实际导出函数名**。你的 `import { X } from '@/api/admin'` 中的 X **必须**是已导出的函数名，禁止凭空造名
- 🛑 **API 模块路径从真理取，禁止自己编**：真理 `api_calls[].from` 字段给出了实际的 API 文件路径（如 `src/api/product.js`），你的 `import ... from` 路径必须基于该路径（`@/api/product`），**不能自己改单复数或命名**（如改成 `@/api/products`）
- 你的 `exposed_to_peers.stores[]` 声明了你的 store 被哪些页面 import

## 🛑 前端真理输出

作为第一个生成的业务层，你需要产出以下"前端真理"供后端对齐：

1. **API 调用真理**：`src/api/*.js` 中每个函数的实际调用方式（URL + method + 传参结构）
2. **路由注册真理**：`src/router/index.js` 中实际注册的路由（name + path + component）
3. **Store 结构真理**：实际使用的 store state 字段和 actions

后端 Agent 将阅读你的这些代码，以准确实现"前端实际在调用什么"。

## 契约解读

以下是将契约字段转换为代码的映射规则：

### API 契约 → API 模块 (`src/api/*.js`)
| 契约字段 | 生成目标 |
|---------|---------|
| `apiGroup` | API 模块文件名（如 `auth` → `src/api/auth.js`） |
| `frontendApiModule` | 🛑 **直接指定**前端 API 模块路径（如 `src/api/auth.js`） |
| `basePath` | 去掉 `/api` 前缀后的基础路径 |
| `endpoints[].method` | `request({ method: ... })` |
| `endpoints[].path` | `request({ url: ... })` 拼接在 basePath 之后 |
| `endpoints[].auth` | 决定请求是否携带 token（request.js 拦截器自动处理） |
| `endpoints[].request.fields[]` | 🛑 请求参数：`fields[].name`=字段名、`fields[].type`=类型、`fields[].required`=是否必填、`fields[].note`=字段含义 |
| `endpoints[].request.note` | 数据从哪来（如"addressId来自地址选择结果，cartItemIds来自购物车勾选项"） |
| `endpoints[].response.fields[]` | 🛑 响应字段：`fields[].name`=字段名、`fields[].type`=类型、`fields[].note`=用途 |
| `endpoints[].response.note` | 数据给谁用（如"返回订单信息供前端跳转支付页"） |
| `endpoints[].errors[]` | 错误码/状态码/消息 → 前端 `catch` 块展示的提示文案 |

🛑 **每个 endpoint 生成一个命名导出函数**。函数名规则：`{method}{Resource}`（GET→getXxxList, POST→createXxx, PUT→updateXxx, DELETE→deleteXxx）。
🛑 **API 函数接收整个 data 对象，不预设具体字段名**。例如 `export function createOrder(data) { return request({ url:'/orders', method:'post', data }) }`。

### Navigation 契约 → 页面跳转代码
| 契约字段 | 生成目标 |
|---------|---------|
| `fromPageFile` | 🛑 **直接指定**跳转的源 Vue 文件路径 → 在该组件中生成跳转代码 |
| `toPageFile` | 🛑 **直接指定**目标 Vue 文件路径 → 确保该文件存在 |
| `toPageRoute` | 跳转目标路由路径 |
| `toPageRouteName` | 路由 name，用于 `router.push({ name: '...' })` |
| `passBy` | 🛑 **关键**：`"params"` → `router.push({ name: 'Xxx', params: { ... } })`；`"query"` → `router.push({ name: 'Xxx', query: { ... } })` |
| `params[]` | 传递的具体参数名列表 → 决定 `params: { orderId }` 的键名 |
| `auth` | `true` → 跳转前检查登录状态 |
| `note` | 跳转的业务场景说明 |

🛑 **passBy 是铁律**：`passBy: "params"` 生成 `params` 传递 + `route.params` 读取。绝不允许 query/params 混用。

### Model 契约 → 表单/表格/展示
| 契约字段 | 生成目标 |
|---------|---------|
| `tableName` | 对应的数据库表名 |
| `fields[].name` | 🛑 **字段名铁律**：表格列 `prop`、表单 `v-model`、API 请求字段名**必须与 model 契约的 `fields[].name` 完全一致** |
| `fields[].type` | 表单控件：`"int"`→`<el-input-number>`，`"varchar"`→`<el-input>`，`"decimal"`→带 `toFixed(2)`，`"enum"`→`<el-select>` |
| `fields[].nullable` | `false` → 表单 `required` 校验 |
| `fields[].comment` | 表格列标题、表单 label |
| `stateMachine` | 状态流转规则 → 状态标签的颜色和文本映射 |

### Auth 契约 → 登录/Token 处理
| 契约字段 | 生成目标 |
|---------|---------|
| `tokenConfig.payloadFields[]` | `useUserStore()` 中存储的 `userInfo` 字段 |
| 🛑 `frontendContract.storageKeys.accessToken` | **localStorage key 名**：`auth_token` |
| 🛑 `frontendContract.storageKeys.refreshToken` | refreshToken 的 key 名：`refresh_token` |
| 🛑 `frontendContract.requestHeader` | 请求头名（`Authorization`） |
| 🛑 `frontendContract.headerFormat` | 格式（`Bearer {token}`） |
| `frontendContract.storageStrategy` | 存储策略：accessToken→`memory_variable`，refreshToken→`http_only_cookie` |
| `middlewareContract.reqInjection` | 中间件注入 `req.userId`(int) + `req.user`({userId, role}) → 前端 store 的 `userRole` 取值必须对齐 |
| `roleGuardMapping` | 角色→页面映射：`buyer`→`/cart,/checkout,...`，`merchant`→`/merchant/*`，`admin`→`/admin/*` |

🛑 **Token 持久化铁律**：登录/注册成功后必须调用 `userStore.setToken(token, refreshToken)`，**禁止**直接赋值。

## 核心要求

### 文件与路径
1. 页面组件 → `src/pages/`，API 模块 → `src/api/`。
2. `scope === "frontend"` → `src/pages/frontend/`，路由前缀 `/`。
   `scope === "backend_admin"` → `src/pages/admin/`，路由前缀 `/admin`，路由 meta 加 `requiresAdmin: true`。
3. 不创建全局基础设施文件。

### API 模块
4. 🛑 **命名导出**：`export function fnName(data) {}`。禁止 `export default`。
5. 引用 `@/utils/request`（baseURL 已设为 `/api`），API 路径不加 `/api` 前缀。
6. 🛑 **不预设参数结构**：函数接收整个 data 对象，不逐个列举字段。例如 `export function createOrder(data) { return request({ url:'/orders', method:'post', data }) }`。
6b. 🛑 **前端禁止数据加工**：API 函数是纯透传——不加密、不哈希、不计算、不转换字段名。密码原样传给后端，价格由后端计算，所有业务逻辑在后端。`return request({...data})` 只做 HTTP 请求，不对 data 做任何修改。
6c. 🛑 **mock 服务提示展示**：后端 `*_MODE=mock` 时 API 响应可能含 `mockCode`（验证码）或 `mockHint`（支付/上传等提示文案）。前端必须显示这些字段：
  - 验证码：`res.data.mockCode` → `ElMessage.success({ message: '[模拟] 验证码: ' + mockCode, duration: 10000 })`
  - 支付/退款/上传：`res.data.mockHint` → `ElMessage.info(mockHint)`

### 导航与跳转
7. 🛑 **所有页面跳转必须基于 navigation 契约**，**严格遵循 passBy 字段**。
8. 🛑 **router.push 中传递的数据键名必须与目标页面的 route.params/query 读取键名一致**。
9. 🛑 **路由注册**：每个有 nav 契约的页面都必须在 router 中注册对应路由。

### Store
10. 使用 infra 已创建的 store。页面通过 `useXxxStore()` 导入。
11. 🛑 **登录/注册成功后**：必须调用 `userStore.setToken(token, refreshToken)` 而非直接赋值。

### UI 规范

🛑 **即使场景树和契约没有提到 UI 细节，也必须使用 Element Plus 组件。**
所有颜色/间距/圆角/动效/组件规范从系统提示词中的「🎨 UI 风格文档」（Memory/ui_styles/）读取，这里不重复。

🛑 **UI 风格文档优先级**：
1. `_global.md`（全局设计令牌：色板/间距/字体/圆角/阴影/动效）— 所有页面铁律
2. `_components.md`（通用组件基准：按钮/卡片/输入框/标签/模态框/表格/Toast）— 所有组件遵循
3. `{模块名}.md`（页面风格文档）— 与本任务 outputFiles 匹配的页面必须严格遵循

如 UI 风格文档与其他规范冲突，以 UI 风格文档为准（它是 PM+Designer 为当前项目量身定制的）。

### 🛑 UI 自检清单（create_files 前必须逐条确认，源: skill/design/designer.md）

**令牌引用**（`_global.md` 已定义，禁止硬编码具体值）:
- [ ] 颜色: 无 `hsl(`/`rgb(`/`#XXXXXX`，全用 `var(--color-*)`（主色9级+中性8个+功能4个）
- [ ] 间距: 无 px（`0`除外），全用 `var(--space-*)`（7级: xs/sm/md/lg/xl/2xl/3xl）
- [ ] 字号: 无 px，全用 `var(--font-size-*)`（7级: xs/sm/base/md/lg/xl/2xl）+ family + 行高
- [ ] 圆角: 无 px，全用 `var(--radius-*)`（4级: sm/md/lg/full）
- [ ] 阴影: 无硬编码，全用 `var(--shadow-*)`（4级: sm/md/lg/glow）
- [ ] 动效: 时长用 `var(--duration-*)`（4级: instant/fast/normal/slow），缓动用 `var(--ease-*)`

**组件对齐**（`_components.md` 已定义基准）:
- [ ] 按钮: 4 变体(primary/secondary/danger/tertiary) × 5 态，构造公式对齐质感基调
- [ ] 输入框: 4 态(默认/聚焦/错误/禁用)齐全
- [ ] 卡片: 3 态(默认/可点击悬浮/选中)齐全
- [ ] 模态框: 含入场/退场动画，ESC/遮罩/X 三种关闭
- [ ] 表格: 表头/行悬浮/空状态/斑马纹齐全
- [ ] Toast: 4 类型(success/warning/error/info)区别
- [ ] 标签: 多彩变体齐全
- [ ] 导航: 吸顶+侧边栏，高度56px/240px
- [ ] 动效编排: stagger/父子/页面切换/模态弹出 4 项齐全

**页面规范**（`{模块}.md` 已定义页面约束）:
- [ ] 禁止 inline: 无 `<div style="...">`，全在 `<style scoped>`
- [ ] 禁止 emoji: 图标用 Element Plus 或 SVG
- [ ] 状态覆盖: 加载/空/错误/极端内容 四态齐全
- [ ] 导航入口: 每页可从入口页 `<router-link>` 或 `router.push` 到达
- [ ] 布局: 含最大宽度 + 响应式断点描述

## 常见缺陷速查

### 路由传递方式
```js
// contract passBy: "params"
// ✅ router.push({ name: 'OrderDetail', params: { id: orderId } })
//    → 目标页用 const { id } = route.params

// contract passBy: "query"  
// ✅ router.push({ name: 'Checkout', query: { selectedIds: ids.join(',') } })
//    → 目标页用 const selectedIds = route.query.selectedIds

// ❌ 混用 params 和 query — 这是最常见的 bug
```

### Token 存储
```js
// ✅ 调用 store action（会写入 localStorage）
userStore.setToken(res.data.token, res.data.refreshToken);

// ❌ 直接赋值（只在内存，刷新丢失）
userStore.token = res.data.token;
```

### 路由注册完整性
```js
// 🛑 每个 nav 契约的 toPage 都必须有对应路由
// ✅ router 中注册了 ProductDetail、Checkout、PaymentResult、ReviewWrite 等全部页面
// ❌ 前端页面组件存在但路由表中缺失 → 跳转失败
```

## 禁止行为
- API 路径不加 `/api` 前缀
- API 模块不使用默认导出
- 不生成无对应 navigation 契约的跳转
- 🛑 **不混用 params/query 传递方式**
- 🛑 **不直接赋值 userStore.token，必须用 setToken()**
- 🛑 **不在 router.push 中传递目标页面未声明的参数**
- 🛑 **同一作用域内禁止重复声明变量/函数**。`<script setup>` 中 const/let/function 不能重名。写入前检查是否已有同名声明。
- 🛑 **Vue template 每个开放标签必须有对应闭合标签**。`<div>` 必须有 `</div>`，`<el-form-item>` 必须有 `</el-form-item>`。
- 🛑 **生成完文件后自检：花括号/括号配对、无多余 `}`、标签正确闭合、const/let/function 无重复**。

## 🛑 真理输出格式

全部文件创建成功且语法通过后，输出以下 JSON（纯 JSON，不含 markdown 包裹）：

```json
{
  "task_id": "{tid}",
  "type": "frontend",
  "output_files": [...],
  "exposed": {
    "exposed_to_upper": {
      "pages": [{"component": "Login", "file": "src/pages/frontend/auth/Login.vue", "route": "/login"}],
      "api_calls": [{"from": "src/api/auth.js", "endpoints": ["POST /auth/login", "GET /auth/me"]}],
      "router": [{"path": "/login", "name": "Login", "component": "Login.vue"}]
    },
    "exposed_to_peers": {
      "stores": [{"file": "src/stores/user.js", "state": ["token", "user"], "actions": ["setToken(token, refreshToken)"], "getters": ["isLoggedIn"], "imported_by": ["src/pages/auth/Login.vue"]}]
    }
  },
  "nfr_verified": {
    "xss": "output_encoding",
    "esm": "verified",
    "components": "element_plus"
  }
}
```

🛑 api_calls 的 endpoints 中 URL 不带 /api 前缀（Axios baseURL 已设置）
🛑 页面路径必须是真实存在的文件路径

## 🛑 执行提醒
以上是"做什么"——具体执行步骤在 user prompt 中：检索→创建→修复→真理。每轮响应必须含工具调用。
