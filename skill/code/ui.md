# 通用 UI 设计规范（Universal UI Design System）

本规范适用于所有前端页面生成任务，覆盖 UI 风格、交互动画、布局三大维度。
具体项目风格通过 RAG 检索注入，本文档提供普适的设计基线和质量标准。

---

## 第一部分：UI 风格（Visual Design）

### 1.1 设计原则

| 原则 | 含义 | 实施 |
|------|------|------|
| 清晰 | 信息层次分明，用户一眼知道该看哪里 | 视觉权重：标题 > 操作按钮 > 正文 > 辅助信息 |
| 克制 | 颜色不超过 3 种主色，装饰不干扰内容 | 去冗余线条、去多余阴影、去过度渐变 |
| 一致 | 同类元素同样交互，同义文案统一措辞 | 按钮形状/颜色/位置全局统一 |
| 反馈 | 每次操作都有即时响应，不让用户猜 | 点击态/hover态/加载态/空态/错误态 五态必达 |
| 容错 | 误操作可撤销，危险操作有二次确认 | 删除弹窗、表单离开确认、操作后 toast |

### 1.2 色彩系统

#### 主色板（5 级梯度）

每种颜色覆盖 lightest / light / base / dark / darkest，按 10%/30%/100%/加深15%/加深30% 推导：

```
主色（Primary）:  主按钮、选中态、链接、品牌标识
   lightest: 主色 10% 透明度  — 选中背景
   light:    主色 30% 透明度  — hover 背景
   base:     主色 100%        — 按钮/图标/链接
   dark:     主色加深 15%     — hover 按钮
   darkest:  主色加深 30%     — 点击态

功能色（Functional）:
   success: #22c55e  — 成功/已完成/已支付
   warning: #f59e0b  — 警告/待处理/即将过期
   danger:  #ef4444  — 危险/删除/失败/已取消
   info:    #3b82f6  — 信息/提示/进行中
```

#### 中性色板

```
文字色:
   text-primary:    #1a1a2e  — 标题、正文
   text-regular:    #374151  — 常规文字
   text-secondary:  #6b7280  — 辅助说明、占位符
   text-disabled:   #b0b7c3  — 禁用态文字（更低对比度，与 border-dark 色值区分）

背景色:
   bg-page:         #f5f5f7  — 页面底色
   bg-container:    #ffffff  — 卡片/表格/弹窗背景
   bg-hover:        #f9fafb  — 表格行 hover、菜单项 hover
   bg-disabled:     #f3f4f6  — 禁用态背景

边框色:
   border-light:    #e5e7eb  — 卡片边框、分割线
   border-base:     #d1d5db  — 输入框默认边框、表格单元格边框
   border-dark:     #9ca3af  — 输入框 hover 边框、表头下划线
```

#### CSS 变量命名规范

所有设计 Token 使用 `--app-{category}-{name}` 命名模式，在 `:root` 中集中定义：

```css
:root {
  /* 主色 */
  --app-color-primary: #3b82f6;
  --app-color-primary-lightest: /* primary 10% opacity */;
  --app-color-primary-light: /* primary 30% opacity */;
  --app-color-primary-dark: /* primary 加深 15% */;
  --app-color-primary-darkest: /* primary 加深 30% */;

  /* 功能色 */
  --app-color-success: #22c55e;
  --app-color-warning: #f59e0b;
  --app-color-danger: #ef4444;
  --app-color-info: #3b82f6;

  /* 文字色 */
  --app-text-primary: #1a1a2e;
  --app-text-regular: #374151;
  --app-text-secondary: #6b7280;
  --app-text-disabled: #b0b7c3;

  /* 背景色 */
  --app-bg-page: #f5f5f7;
  --app-bg-container: #ffffff;
  --app-bg-hover: #f9fafb;
  --app-bg-disabled: #f3f4f6;

  /* 边框色 */
  --app-border-light: #e5e7eb;
  --app-border-base: #d1d5db;
  --app-border-dark: #9ca3af;

  /* 阴影 */
  --app-shadow-level-1: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
  --app-shadow-level-2: 0 4px 12px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04);
  --app-shadow-level-3: 0 12px 32px rgba(0,0,0,0.12), 0 4px 8px rgba(0,0,0,0.06);

  /* 间距（基准 4px） */
  --app-space-xs: 4px;
  --app-space-sm: 8px;
  --app-space-md: 12px;
  --app-space-base: 16px;
  --app-space-lg: 20px;
  --app-space-xl: 24px;
  --app-space-2xl: 32px;

  /* 圆角 */
  --app-radius-sm: 4px;
  --app-radius-base: 8px;
  --app-radius-md: 12px;
  --app-radius-lg: 16px;
  --app-radius-xl: 24px;
  --app-radius-full: 9999px;

  /* 字号 */
  --app-font-xs: 0.75rem;
  --app-font-sm: 0.8125rem;
  --app-font-base: 0.875rem;
  --app-font-md: 0.9375rem;
  --app-font-lg: 1rem;
  --app-font-xl: 1.125rem;
  --app-font-2xl: 1.25rem;
  --app-font-3xl: 1.5rem;

  /* 动画 */
  --app-ease-standard: cubic-bezier(0.4, 0, 0.2, 1);
  --app-ease-decelerate: cubic-bezier(0.0, 0, 0.2, 1);
  --app-ease-accelerate: cubic-bezier(0.4, 0, 1, 1);
  --app-ease-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55);
}
```

#### 色彩使用规则

- 一个页面主色出现不超过 3 处大面积区域
- 功能色仅用于状态标识，不用于装饰
- 文字与背景对比度 ≥ 4.5:1（正文）、≥ 3:1（18px+ 大文字）
- 所有颜色必须通过 CSS 变量引用，禁止散落硬编码色值

### 1.3 字体系统

```
字体族:
  系统字体栈（优先）: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                     "Helvetica Neue", Arial, "Noto Sans SC", sans-serif
  等宽字体: "JetBrains Mono", "Fira Code", "Consolas", monospace

字号梯度（10 级，使用 rem）:
  xs:   0.75rem  (12px) — 标签、角标、辅助信息
  sm:   0.8125rem(13px) — 表单提示、次要文字
  base: 0.875rem (14px) — 正文（默认）
  md:   0.9375rem(15px) — 表格内容、列表项
  lg:   1rem     (16px) — 卡片标题、菜单项
  xl:   1.125rem (18px) — 页面模块标题
  2xl:  1.25rem  (20px) — 弹窗标题、区块标题
  3xl:  1.5rem   (24px) — 页面标题
  4xl:  1.875rem (30px) — 主标题（Hero）
  5xl:  2.25rem  (36px) — 超大标题（登录页/首页）

字重（5 级）:
  light(300) / normal(400) / medium(500) / semibold(600) / bold(700)

行高:
  heading: 1.25  — 所有标题
  body:    1.6   — 正文段落
  compact: 1.4   — 表格、列表、表单项
```

### 1.4 圆角与阴影

```
圆角（统一梯度）:
  none:   0       — 表格、分割线
  sm:     4px     — 输入框、标签、角标
  base:   8px     — 按钮、下拉菜单、Tooltip（默认）
  md:     12px    — 卡片、弹窗
  lg:     16px    — 大卡片、抽屉
  xl:     24px    — 首页主卡片、Banner
  full:   9999px  — 胶囊按钮、头像

阴影（3 级深度，表达空间层次）:
  level-1: 0 1px 3px  rgba(0,0,0,0.06), 0 1px 2px  rgba(0,0,0,0.04)
           — 卡片默认态、下拉菜单
  level-2: 0 4px 12px rgba(0,0,0,0.08), 0 2px 4px  rgba(0,0,0,0.04)
           — 卡片 hover、Tooltip、Popover
  level-3: 0 12px 32px rgba(0,0,0,0.12), 0 4px 8px  rgba(0,0,0,0.06)
           — 弹窗、抽屉、通知中心
```

---

## 第二部分：布局系统（Layout）

### 2.1 全局容器

```
最大内容宽度:
  标准: 1200px  — 后台管理、列表页、表单页
  窄版: 800px   — 登录页、注册页、详情页（单列）
  宽版: 1440px  — 数据面板、大屏展示

水平居中: margin: 0 auto; 左右留白 min(24px, 4vw)
```

### 2.2 栅格系统

12 列栅格，间距 16px（gutter），按断点调整列数：

```
≥ 1440px: 12 列
≥ 1200px: 12 列
≥ 992px:   8 列
≥ 768px:   6 列
< 768px:   4 列（堆叠为单列）

卡片网格:
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
  — 自动计算列数，不写死
```

### 2.3 间距系统

所有间距使用 4px 基准单位，构成 12 级梯度：

```
间距梯度:
  xs:   4px   — 图标与文字间距、标签内边距
  sm:   8px   — 表单项之间、按钮组间距
  md:   12px  — 卡片内边距、列表项内边距
  base: 16px  — 标准内边距、元素间距（默认）
  lg:   20px  — 卡片之间、模块之间
  xl:   24px  — 页面内容区边距、区块之间
  2xl:  32px  — 大模块之间、页脚间距
  3xl:  40px  — 页面章节之间
  4xl:  48px  — 首页大区块
  5xl:  64px  — Hero 区域上下
  6xl:  80px  — 页面级大留白
  7xl:  96px  — 极少使用

垂直节奏（使用间距 Token）:
  页面顶部 → 标题区: var(--app-space-xl) 即 24px
  标题区 → 内容区: var(--app-space-lg) 即 20px
  内容区内子模块间: var(--app-space-xl) 即 24px
  内容区底部 → 页面底部: var(--app-space-xl) 即 24px
```

### 2.4 经典页面布局模板

```
后台管理布局:
┌──────────────────────────────────────┐
│  Header (sticky, h=56px)             │
├────┬─────────────────────────────────┤
│ 侧栏│  内容区                          │
│ 220 │  (面包屑 + 页面标题 + 主体内容)    │
│ px  │                                │
└────┴─────────────────────────────────┘

前台页面布局:
┌──────────────────────────────────────┐
│  Header (sticky, 半透明+模糊)          │
├──────────────────────────────────────┤
│  Hero / Banner (可选)                 │
├──────────────────────────────────────┤
│  卡片网格 (居中, max-width:1200px)      │
├──────────────────────────────────────┤
│  Footer                              │
└──────────────────────────────────────┘

表单页布局:
┌──────────────────────────────────────┐
│  页面标题                             │
├──────────────────────────────────────┤
│  ┌────────────────────────┐          │
│  │  表单卡片(max-w:640px)   │          │
│  │  标签宽 100-120px       │          │
│  │  上下排列(移动) 左右(桌面) │          │
│  │  ─────────────────────  │          │
│  │  [取消]         [保存]   │          │
│  └────────────────────────┘          │
└──────────────────────────────────────┘
```

### 2.5 响应式断点

| 断点 | 宽度 | 布局变化 |
|------|------|---------|
| xs | < 576px | 单列，侧栏隐藏，表格转卡片 |
| sm | ≥ 576px | 单列，汉堡菜单 |
| md | ≥ 768px | 2 列卡片，侧栏可折叠 |
| lg | ≥ 992px | 3 列卡片，侧栏常驻 |
| xl | ≥ 1200px | 3-4 列卡片，完整布局 |
| xxl | ≥ 1440px | 4-5 列卡片，宽屏优化 |

---

## 第三部分：核心组件规范（Component Specs）

### 3.1 按钮（Button）

```
尺寸:  sm(h=32px, fs=13px) | base(h=36px, fs=14px) | lg(h=40px, fs=15px)
变体:  primary(主色填充 var(--app-color-primary)) | default(白底+灰边框) | danger(红色) | text(纯文字) | link

形状:  默认 --app-radius-base(8px) | 胶囊 --app-radius-full(9999px)（CTA 按钮）
间距:  按钮组 gap:--app-space-sm(8px)，与表单/表格间距:--app-space-md(12px)

状态:
  hover:  背景加深(主色dark)，0.15s var(--app-ease-standard)
  active: 背景再深(主色darkest)，无过渡(即时按下感)
  disabled: 灰色背景 var(--app-bg-disabled)+灰色字 var(--app-text-disabled)，cursor:not-allowed
  loading: 文字前加旋转图标(spin)，按钮 disabled，文字保留不消失
```

### 3.2 输入框（Input）

```
尺寸:  sm(h=32px) | base(h=36px) | lg(h=40px)
状态:
  default:  灰色边框(--app-border-base)
  hover:    边框略深(--app-border-dark)
  focus:    主色边框 + 外发光(box-shadow: 0 0 0 3px rgba(主色RGB, 0.15))，0.15s
  error:    红色边框 + 红色提示文字 + 抖动动画(左右4px×3次，0.3s，必须)
  disabled: 灰色背景(--app-bg-disabled)+灰色文字(--app-text-disabled)

标签:  输入框上方 6px，必填项红色 * 星号
提示:  输入框下方 4px，error 红色，正常灰色
组合:  搜索框 = 输入框 + 按钮紧贴右侧；输入框 + 下拉 = 下拉按钮在右侧
```

### 3.3 表格（Table）

```
表头: 灰色背景(--app-bg-hover)，文字 semibold，字号 --app-font-sm，下边框 2px solid --app-border-dark，sticky top
行:   hover 浅色背景，行高 ≥ 48px，选中行主色浅背景+左侧 3px 主色竖条
单元格: padding --app-space-md(12px) --app-space-base(16px)，文字左对齐 / 数字金额右对齐

操作列: 固定右侧(sticky right:0)，按钮组 gap:--app-space-xs(4px)
分页:  表格下方 --app-space-md(12px)，"共X条 / 第Y页" [<] [1] [...] [5] [>]，每页 10/20/50/100

空态:  居中: 空态图标 + "暂无数据" + 可选[新建]按钮
加载态: 表格区半透明遮罩 + 居中旋转图标
```

### 3.4 卡片（Card）

```
结构:  overflow:hidden，圆角 12px，白色背景，阴影 level-1
       图片区(上) + 信息区(下 padding:16px)
       标题 16px semibold 最多 2 行截断(line-clamp:2)，辅助文字 sm 灰色

交互:  hover → translateY(-4px) + 阴影 level-2，transition 0.25s ease-standard
       整卡可点击 → cursor:pointer，图片微缩放 1.02（overflow:hidden 防止溢出）
       操作按钮在卡片底部或右上角

卡片组:
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
```

### 3.5 弹窗（Dialog / Modal）

```
遮罩:  rgba(0,0,0,0.45)，渐入 0.2s
弹窗:
  白色背景(--app-bg-container)，圆角 --app-radius-md(12px)，阴影 var(--app-shadow-level-3)
  最小宽度 360px，最大 560px（确认框 400px），最大高度 85vh
  标题栏(h=52px): 标题 --app-font-2xl semibold 左对齐，关闭按钮右上
  内容区: padding --app-space-xl(24px)，溢出内部滚动
  底部操作栏: padding --app-space-base(16px) --app-space-xl(24px)，按钮右对齐，主按钮在右

动画:
  打开: scale(0.95)→scale(1) + opacity 0→1，0.2s ease-decelerate
  关闭: 逆过程，0.15s ease-accelerate

下拉菜单:
  展开: scaleY(0)→scaleY(1) + opacity 0→1，transform-origin:top，0.15s
  收起: 逆过程，0.1s
```

### 3.6 导航（Navigation）

```
顶部导航:
  h=56px，sticky top，白色/半透明背景
  Logo(左) → 菜单项(中或左) → 操作区(右:搜索/通知/头像)
  菜单项: padding 8px 16px，圆角 8px，hover 浅色背景
  当前页: 主色文字 + 底部 3px 主色横条

侧栏导航:
  宽 220px(展开) / 64px(折叠)，高 100vh - 56px
  菜单项 icon + 文字，折叠时仅 icon + Tooltip
  当前项: 主色浅背景 + 左侧 3px 主色竖条

面包屑:
  字号 sm，灰色，分隔符 "/" 或 ">"
  最后一级为当前页(深色，不可点击)
```

### 3.7 标签与徽标（Tag & Badge）

```
标签(Tag):
  圆角 4px，padding 2px 8px，字号 xs
  变体: default(灰)/primary(主色浅)/success(绿浅)/warning(黄浅)/danger(红浅)
  可关闭标签: 右侧 × 按钮

徽标(Badge):
  圆角 full，最小宽 20px，高 20px，字号 xs
  红点: 8px 圆点，用于角标提示
  数字: 显示未读数，超过 99 显示 "99+"
  位置: 图标/头像右上角 -4px -4px
```

---

## 第四部分：交互动画（Interaction & Animation）

### 4.1 动画原则

| 原则 | 含义 | 实施参数 |
|------|------|---------|
| 快出慢进 | 出现快（用户等）、消失慢（可打断） | 出现 0.15-0.2s，消失 0.2-0.3s |
| 物理感 | 缓动模拟真实运动 | ease-standard: cubic-bezier(0.4,0,0.2,1) |
| 不超半秒 | 任何动画 ≤ 500ms | 超过 = "加载"而非"动画" |
| 距离对应时长 | 小位移短时长，大位移长时长 | 4px→0.15s，100px→0.3s |
| GPU 加速 | 优先用 transform/opacity | 避免 width/height/top/left 动画 |

### 4.2 标准缓动函数

```css
--ease-standard:   cubic-bezier(0.4, 0, 0.2, 1);   /* 最常用，默认 */
--ease-decelerate: cubic-bezier(0.0, 0, 0.2, 1);   /* 元素进入屏幕 */
--ease-accelerate: cubic-bezier(0.4, 0, 1, 1);     /* 元素离开屏幕 */
--ease-bounce:     cubic-bezier(0.68, -0.55, 0.265, 1.55); /* 强调弹性 */
```

### 4.3 页面级动画

```
页面切换（路由跳转）:
  淡入淡出 opacity 0→1，0.2s ease-standard
  不位移 — 页面切换不用滑动

首次加载:
  骨架屏: 灰色脉冲(pulse)，圆角与真实内容一致，1.5s infinite
  内容渐进: 从上到下逐块淡入，每块延迟 50ms(stagger)
  图片: 低分辨率占位 → 高斯模糊 → 清晰淡入，0.3s

数据刷新:
  下拉刷新: 顶部旋转图标 + "正在刷新"
  静默刷新: 旧数据保持，新数据到达后平滑替换(fade 0.15s)
  失败刷新: "加载失败" + [重试]按钮
```

### 4.4 组件级动画

```
按钮:
  hover:   背景色过渡 var(--app-ease-standard) 0.15s（无缩放）
  active:  瞬间变深无过渡（即时按下感）
  loading: 文字淡出 → 旋转图标淡入，0.15s

输入框:
  focus: 边框+外发光过渡 var(--app-ease-standard) 0.15s
  error: 边框变红 + 抖动 0.3s(左右 4px × 3 次，衰减)，必须

卡片:
  hover: translateY(-4px) + 阴影升至 var(--app-shadow-level-2)，0.25s var(--app-ease-standard)
  click: translateY(0) + 阴影回到 var(--app-shadow-level-1)，0.1s

弹窗:
  打开: scale(0.95)→scale(1) + opacity 0→1，0.2s var(--app-ease-decelerate)
  关闭: 逆过程，0.15s var(--app-ease-accelerate)

侧栏:
  展开/折叠: width 变化 0.25s var(--app-ease-standard)
  移动端: translateX(-100%)→translateX(0)，0.25s var(--app-ease-decelerate)

表格:
  新增行: 主色背景闪烁→透明，0.5s（提示插入位置）
  删除行: 高度缩小 + opacity 淡出，0.2s
  排序图标: 旋转 180°，0.15s

Toast/通知:
  入场: translateY(16px)→translateY(0) + opacity 0→1，0.25s var(--app-ease-bounce)
  出场: opacity 1→0 + translateY(-8px)，0.2s
  自动消失: 3s 后出场，hover 时计时暂停

Tooltip:
  出场: opacity 0→1 + translateY(4px)→translateY(0)，0.15s var(--app-ease-standard)
  消失: opacity 1→0，0.1s（不位移）

选项卡(Tab):
  下划线滑动: 0.2s var(--app-ease-standard)，宽度=新标签宽
  内容切换: 旧内容淡出 0.1s → 新内容淡入 0.15s

展开/折叠(Accordion):
  内容区: max-height 展开，0.25s var(--app-ease-standard)
  箭头: rotate 0→180°，0.2s

开关(Toggle):
  滑块平移: translateX，0.2s var(--app-ease-standard)
  背景色渐变: 0.2s
```

### 4.5 微交互（Micro-interactions）

```
点赞/收藏:
  图标放大 1.3× 再缩回，0.25s ease-bounce
  颜色从灰变红(心)/黄(星)，0.15s
  数字 +1 时短暂放大

加购:
  商品图缩小并向购物车图标抛物线移动，0.4s
  购物车角标数字弹跳 +1，0.3s ease-bounce

输入反馈:
  密码可见切换: 图标平滑切换，0.15s
  字数统计: 接近上限变黄 → 超过变红，0.2s

拖拽排序:
  拖拽项: 阴影 level-2 + scale(1.02)，0.15s
  其他项: 平滑让位 transition:transform 0.2s ease-standard
  释放: 弹回 scale(1)，0.2s ease-bounce
```

---

## 第五部分：图标与图片（Icons & Images）

```
图标:
  画布 24×24px，图形在 20×20px 内
  线框风格(outline)，线宽 1.5-2px
  颜色继承 currentColor，跟随文字色
  与文字混排: 右侧 gap 6px，对齐中线

图片:
  内容图: object-fit:cover，背景色占位
  头像: 圆形，姓名回退(首字母)
  加载: loading="lazy"，先 20px 模糊占位 → 加载完淡入 0.3s
  错误: 加载失败 → 默认占位图+图标
```

---

## 第六部分：可访问性（Accessibility）

| 要求 | 实施 |
|------|------|
| 键盘导航 | Tab 顺序合理，Enter/Space 激活按钮，Escape 关闭弹窗 |
| 焦点指示 | 所有可交互元素有可见 focus ring（2px 主色外发光） |
| 对比度 | 正文 4.5:1，大文字 3:1 |
| 屏幕阅读器 | 图标有 aria-label，图片有 alt，表单有 label |
| 跳过链接 | 页面顶部提供"跳到主内容"链接 |
| 动画控制 | 尊重 prefers-reduced-motion: reduce，禁用非必要动画 |

---

## 第七部分：生成自检清单

### UI 风格

- [ ] 颜色不超 3 种主色 + 4 种功能色，全部使用 CSS 变量
- [ ] 字号使用 10 级 rem 梯度，字重使用 5 级
- [ ] 圆角使用预设梯度（4/8/12/16/24px），不随意取随机值
- [ ] 阴影使用 3 级深度系统（level-1/2/3），不自创
- [ ] 间距使用 4px 基准单位，不出现 5px/7px/11px 等非标值
- [ ] 文字-背景对比度达标

### 布局

- [ ] 容器 max-width 合理（1200/800/1440px），内容居中
- [ ] 响应式至少处理 3 个断点（<768 / 768-1200 / >1200px）
- [ ] 卡片网格使用 grid + auto-fill + minmax，不写死列数
- [ ] 表格在移动端有横向滚动或转卡片布局
- [ ] 侧栏在移动端有折叠/隐藏机制

### 交互动画

- [ ] 按钮有 hover / active / disabled / loading 四态
- [ ] 输入框有 default / hover / focus / error / disabled 五态
- [ ] 弹窗/下拉/侧栏有打开和关闭动画
- [ ] 所有动画使用 GPU 加速属性（transform/opacity），避免 width/height 动画
- [ ] 动画时长 ≤ 300ms（特殊场景除外）
- [ ] 使用标准缓动函数，不随意自定义 cubic-bezier
- [ ] 骨架屏/加载态在数据到达前显示
- [ ] 空态有图标+文字+操作引导
- [ ] 错误态有具体错误信息和重试入口
