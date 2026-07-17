# C: frontend — 前端修复

继承 [static.md](../static.md) 通用规则。

## 模块系统

🛑 `package.json` **没有** `"type": "module"` — 项目使用混合 CJS/ESM 架构:
- `src/` 下 `.js` 文件: ESM（`import`/`export`），由 Vite/esbuild 编译
- 后端文件（`config/`, `middleware/`, `utils/` 等）: CJS（`require`/`module.exports`）
- 🛑 不要试图给 `package.json` 添加 `"type": "module"` — 会破坏所有后端代码

## 🛑 工作流程（前端特有）

1. **先读 UI 设计系统**：查看 prompt 中的「🎨 UI 风格文档」（Memory/ui_styles/），记住色板/间距/圆角/动效 Token
2. **再读 prompt 中的「任务检查点」**：每条 checkPoint 是必须满足的规范
   - `导出 login(phone, password) → POST /admin/login` → 文件中必须有 `export function login(phone, password)`
   - `import request from '@/utils/request'` → 文件第一行必须匹配
3. **对照 checkPoints 逐条验证**，缺失的导出立即用 edit_batch 补充
4. **修改 .vue 时**：对照 Memory/ui_styles/ 的 Token 值，确保颜色/间距/圆角与设计系统一致

## 修复策略

```
checkPoint要求导出X但文件缺X → 按 checkPoint 指定的签名 + URL + method 补充 export function
ESM语法错 → esbuild 验证 + 修正 import/export 语法（src/ 下文件用 esbuild 而非 node --check）
SFC语法错 → node --input-type=module --check <script>块，修正 JS 语法（Vue SFC 是 ESM 模块）
require/module.exports → 改为 import/export（src/下禁止CJS）
import '@/...' 路径不存在 → 修正路径或创建缺失文件
export函数名 vs import {X} 不匹配 → 统一命名
src/utils/request.js 非 export default → 改为 export default
v-model 字段名 vs model 不一致 → 对齐 model truth 字段名
Store state/actions 引用错 → 对齐 store 导出
```

## 🛑 UI 设计一致性

🛑 修改 .vue 前查看 prompt 中「🎨 UI 风格文档」（Memory/ui_styles/）。设计论见 `skill/design/designer.md`。

### 修复自检清单（edit_batch 提交前逐条确认）,一下清单必须检查，全部通过后才允许判断正确

**令牌引用**（禁止硬编码，全部替换为 CSS 变量）:
- [ ] 颜色: 无 `hsl(`/`rgb(`/`#XXXXXX` → `var(--color-*)`（主色9级+中性8个+功能4个）
- [ ] 间距: 无 px（`0`除外）→ `var(--space-*)`（7级: xs/sm/md/lg/xl/2xl/3xl）
- [ ] 字号: 无 px → `var(--font-size-*)`（7级: xs/sm/base/md/lg/xl/2xl）
- [ ] 圆角: 无 px → `var(--radius-*)`（4级: sm/md/lg/full）
- [ ] 阴影: 无硬编码 → `var(--shadow-*)`（4级: sm/md/lg/glow）
- [ ] 动效: 时长 → `var(--duration-*)`，缓动 → `var(--ease-*)`

**组件对齐**（对齐 `_components.md` 基准）:
- [ ] 按钮: 4 变体 × 5 态
- [ ] 输入框: 4 态齐全
- [ ] 卡片: 3 态齐全
- [ ] 模态框: 入场/退场动画
- [ ] 表格: 表头/行悬浮/空状态
- [ ] Toast: 4 类型区别
- [ ] 标签: 多彩变体
- [ ] 导航: 吸顶+侧边栏

**页面规范**:
- [ ] 禁止 inline: 无 `<div style="...">` → 移入 `<style scoped>`
- [ ] 禁止 emoji: 替换为 Element Plus 图标或 SVG
- [ ] 状态覆盖: 加载/空/错误/极端 四态齐全

### 🛑 导航入口补建（checkPoints 列出缺失项时执行）

checkPoints 中 `导航入口: {页面}.vue 含 <router-link> 或 router.push 指向 {路由名}` 若未通过 → **在源页补建导航元素**。

**读取信息**:
1. 从 prompt 源码或 `read_files` 读目标页面，确认实际 `<router-link>` / `router.push` 情况
2. 从 `src/router/index.js` 确认目标路由的 `name`（用于 `router.push({name:'X'})`）
3. 从 `_components.md` §导航 确认导航栏规范（吸顶高度56px / 侧边栏240px / 菜单项样式）

**补建规则**（🛑 必须按对应 UI 设计布局调整，禁止随意插入）:

1. **读设计文档定布局**：查看 prompt 中本页面的专属 UI 风格文档（`{模块}.md`）→ 确认「布局」章节的骨架类型（单列流/侧边栏+内容区/卡片网格/列表+详情）和「组件覆盖」章节的导航微调
2. **读 `_components.md` §导航**：确认导航组件基准（吸顶高度56px、侧边栏宽度240px、菜单项默认/悬浮/选中三态）
3. **读目标页面现有布局**：`read_files` 当前页面 → 找到导航区域（`<header>`/`<nav>`/`<el-menu>`/`<el-tabs>`）→ 确定插入位置
4. **插入导航元素**：在现有导航区域追加，不在内容区随意塞按钮

| 页面骨架 | 导航区域 | 入口补建位置 |
|---------|---------|-------------|
| 吸顶导航 + 内容区 | `<header>` 顶栏右侧操作区 | 追加 `<router-link :to="{name:'X'}">` + Element Plus 图标 |
| 侧边栏 + 内容区 | `<el-menu>` 菜单项列表 | 追加 `<el-menu-item>` 或 `<router-link>` |
| 底部 Tab 栏 | `<el-tabs>` 或自定义 tab-bar | 追加 tab 项 |
| 单列流（无导航区） | 页面顶部/底部操作区 | 追加 `<router-link>` 按钮组，`var(--space-md)` 间距 |

**补建后自检**:
- [ ] 新增元素在页面现有导航区域内，未破坏布局骨架
- [ ] 路由 name 与 `router/index.js` 一致
- [ ] 颜色/间距/字号/圆角全用 `var(--xxx-*)`，与同导航区现有元素风格一致
- [ ] 菜单项三态（默认/悬浮/选中）与 `_components.md` §导航一致
- [ ] 吸顶导航中元素高度不超过 56px

## 反作弊

```
□ 不能删 import → CHEAT
□ 不能把所有 .vue 的 <script> 块清空 → CHEAT
□ 不能给页面加 inline style → CHEAT
```
