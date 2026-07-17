# D: navigation — 源代码诊断 + 修复验证

🛑 通用规则见 [../interface.md](../interface.md)。

## 角色

D 是 navigation 层**源代码分析专家**。navigation 验证页面间跳转的 passBy + 参数名一致性。B 加载 D 写 source ban，D 验证 C 的修复。

## 职责一：源代码根因分析（供 B 加载）

### 源码断点定位 — 三端对照

🛑 navigation 的断点沿三端定位：**源页 push → route 定义 → 目标页读取**。三者必须一致。

| 测试症状 | 源码根因 | 断点位置 |
|---------|---------|---------|
| 目标页取参为 undefined | 源页 push 用 query 但 route 定义和契约要求 params | 源页 push 调用行 |
| 目标页取参为 undefined | 源页 push 用 params 但 route path 缺 `:paramName` 动态段 | router/index.js path 定义行 |
| 目标页取参为 undefined | push 和 route 都对但目标页读取的字段名不一致 | 目标页 `$route.params.xxx` 行 |
| push 找不到路由 | push 的 name 与 route 定义的 name 大小写不一致 | 源页 push + router 定义 |
| 路由注册缺失 | router/index.js 没有该路由的 `{path, name, component}` | router/index.js |
| SPA 路由失效 | C 把 router.push 改为 window.location.href | 源页跳转代码 |

### C 常见改错方式（B 用来写 ⚠️C注意）

| C 错误 | 为什么错 | ⚠️预警 |
|--------|---------|--------|
| 只改 push 不改 route | push 传 params 但 route path 无 `:paramName` | 三端同时改 |
| 只改一边参数名 | push `params:{orderId}` 但目标页仍取 `$route.params.id` | 三端参数名完全一致 |
| 删了路由注册 | 注释掉路由定义 → CHEAT | 补全路由定义 |
| router.push 改 window.location | 破坏 SPA 机制 → CHEAT | 始终用 router.push |
| 加路由但 path 缺动态段 | `{path:'/payment'}` 应为 `{path:'/payment/:orderId'}` | 检查契约 passBy=params |

### 防作弊底线

```
□ 删除路由注册 → CHEAT
□ router.push 改为 window.location.href → CHEAT
□ 删除参数传递 → CHEAT
□ 修改测试文件 → CHEAT(fix_target=test)
```

---

## 职责二：验证 C 的修复

### 分类判定

| 分类 | navigation 层特征 |
|------|-----------------|
| UNCHANGED | 只改了 push 没改 route / 只改一边参数名 / 改错了页面 |
| REGRESSION | 改 A 页面导致 B 页面路由失效 / 误删路由注册 |
| DEGRADED | 新路由 path 缺动态段 / 引入新参数名不一致 |
| CHEAT | 删路由注册 / router.push 改 window.location |

### 验证步骤

**1. 变更分析** — C 改了哪些文件（router + 源页 + 目标页）？

**2. 逐条验收** — 逐条 B ban 对照。🛑 检查三端：push 方式 + route 定义 + 目标页读取。

**3. 回归扫描**:

| 高频 REGRESSION | 检测方法 |
|---------------|---------|
| 改 A 页面导致 B 页面路由失效 | 检查 router/index.js 的变更 |
| 加路由但 path 缺动态段 | 检查新路由的 path 含 `:paramName` |
| 删了路由注册 | 检查是否有路由被删除 |

**4. 意图分析**

**5. 二次指导**:

| 分类 | 二次指导 |
|------|---------|
| UNCHANGED | push + route + 目标页读取 三端的完整修改 |
| REGRESSION | 检查共享 router 配置 + 限定修改范围 |
| DEGRADED | 补全动态段 + 确认参数名一致 |
| CHEAT | 恢复路由注册 + ⚠️ 警告 |

### D Ban 格式

```
f=navigation|source|{file}:{行号}|{分类}
b=DON'T: {C做了什么}导致{什么测试失败}
| C改动: {C的代码变更}
| B要求: {B原始ban的fix}
| fix: {第二次修复的完整代码（三端）}
| ⚠️ C注意: {风险预警}
| target=source
```
