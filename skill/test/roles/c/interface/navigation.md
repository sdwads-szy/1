# C: navigation — 页面跳转路由修复

继承 [interface.md](../interface.md) 通用规则。navigation 验证三端一致性：源页 push → route 定义 → 目标页读取。

## 修复策略（按 B 子类型）

| 子类型 | 症状 | 修复 |
|--------|------|------|
| VERIFIED_TRUTH | 测试验证了 .vue 存在/router 注册 | 不改源码——测试代码问题（fix_target=test） |
| WRONG_SRC_PATH | fs.readFileSync 路径错 | 不改源码——测试代码问题 |
| INCOMPLETE_CHECK | 测试只验证了一端 | 不改源码——测试代码问题 |
| MISSING_ROUTE | 路由注册缺失（router 中确实没有这个页面） | `router/index.js` 补 `{ path, name, component }` 注册 |
| WRONG_ROUTE_NAME | router.push({name:'X'}) 但 router 中不存在 name='X' | 🛑 **不改 router**——找到 router 中该页面对应的正确 name，修改**调用方**的 name 引用为正确值。router 是静态层验证过的权威来源。 |
| WRONG_PASSBY | passBy 方式不匹配 | 源页 push 方式对齐契约：params→`router.push({name, params})`，query→`router.push({path, query})` |
| DYNAMIC_SEGMENT_MISSING | route path 缺动态段 | `path: '/payment/:orderId'` 加 `:paramName` |
| PARAM_NAME_MISMATCH | 源页传参名 ≠ 目标页取参名 | 🛑 三端同时改：源页 push + route 定义 + 目标页 `$route.params.xxx` |
| MISSING_RETURN_NAV | 目标页缺返回跳转 | 目标页加 `router.back()` 或 `router.push({name:'fromPage'})` |

### 🛑 三端同步修复原则

**路由定义 > 调用方引用。** 当调用方引用的路由名与 router 定义不一致时，修复调用方，不修改 router。

- `router.push({name:'Profile'})` 但 router 定义是 `{name:'UserProfile'}` → 改 Home.vue 的 `'Profile'` 为 `'UserProfile'`
- 禁止反向修复：把 router 的 `UserProfile` 改成 `Profile`（会炸掉其他正确引用的地方）

passBy=params 时三个位置必须同步：
```
1. 源页: router.push({name:'Target', params:{orderId}})
2. route: { path:'/target/:orderId', name:'Target', component: TargetPage }
3. 目标页: const { orderId } = route.params
```

修一个必须检查另外两个是否一致。

## 🛑 UI 一致性（新增 UI 元素时的强制规则）

**新增跳转入口（按钮/链接/面包屑）时，必须与当前页面已有的 UI 风格保持一致：**

1. **复用现有组件**：页面已有的 `<el-button>` / `<el-card>` 等，使用相同的 type/size 属性
2. **颜色从色板取**：新增元素的颜色（背景、文字、边框）必须在 UI 风格文档色板内（见 Memory/ui_styles/_global.md），禁止硬编码非品牌色
3. **间距对齐网格**：新增元素的 margin/padding 必须与同页面其他元素对齐（4px 倍数）
4. **不要随意写 inline style**：优先使用 Element Plus 组件属性 + scoped CSS class，禁止 `style="color: #ff0000; margin-top: 7px"` 这种随意写法
5. **新增按钮风格对齐**：如果页面用的是 `<el-button type="primary" size="small">`，新增的就不要写成 `<button class="my-custom-btn">`
6. **面包屑对齐**：新增面包屑项时，复用页面已有的 `<el-breadcrumb>` 结构，不要自己写 div+css 模拟

**违规示例 vs 合规示例：**

```
❌ <button style="background: #ff6600; padding: 5px 13px" @click="go">个人中心</button>
✅ <el-button type="primary" size="small" @click="goToProfile">个人中心</el-button>

❌ <div class="nav-link" @click="router.push({name:'Profile'})">我的</div>
✅ <el-breadcrumb-item :to="{ name: 'UserProfile' }">个人中心</el-breadcrumb-item>
```

## 反作弊底线

```
□ 不能删路由注册 → CHEAT
□ router.push 不能改为 window.location.href → CHEAT
□ 不能删参数传递 → CHEAT
```
