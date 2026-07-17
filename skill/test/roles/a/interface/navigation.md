# A: navigation — 页面跳转参数传递

继承 [interface.md](../interface.md) 通用规则。代码模板见 [templates/interface/navigation.md](../../../templates/interface/navigation.md)。

🛑 **router/index.js 只读参考，不对其做断言。路由注册由 integ 层验证，navigation 只验证源页→目标页的跳转逻辑。**

## 工作流

场景定方向，**模板定参数提取方式**。

🛑 参数提取规则全部在模板中。这里不重复。

1. 读场景 → 确定测试范围
2. 判断 category:
   - `correct` / `error` → 普通静态跳转 → 模板第三步（静态骨架）
   - `auth-flow` → 🆕 登录重定向 → 模板 auth-flow 骨架（含 store 检查）
3. 按模板提取参数 → 填入骨架
4. create_files 输出

## 🛑 断言原则

| ❌ 错误做法 | ✅ 正确做法 |
|------------|-----------|
| 写正则匹配所有导航写法 | `expect(fromPage).toContain(routeName)` — 路由名出现在页面里就算 |
| 用 `new RegExp()` 动态拼接复杂转义 | 用 `toContain` / `includes()` |
| 一个 it() 塞 4 个 expect | 拆成多个 it()，每个只验证一件事 |
| `toMatch(/params\s*:\s*\{/)` 正则 | `fromPage.includes('params:')` |

## 独有规则

- 🛑 `readPageSafe()` 先 `fs.existsSync` 再 `readFileSync`
- 🛑 页面路径从模板参数提取规则获取
- 🛑 不编造不存在的页面跳转（如 Register→Home）
- 🛑 不用正则，全部 `toContain` / `includes`
- 🛑 **全局入口完整性**：每个角色可见页面必须从至少一个入口页 `<router-link>` 或 `router.push` 到达。首页缺 Profile/Orders 入口 → checkPoints 列出缺失项 → C 步补建

## 自我修复

B 判定 `fix_target=test` → 加载 [repair/a/interface/navigation.md](../../../repair/a/interface/navigation.md)。
