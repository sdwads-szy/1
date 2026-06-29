# d: api 层 — 源码验证

API 层核心规则：**请求字段 ↔ 响应字段 对齐**。不关心业务含义。

## 验证步骤
1. 跑测试 → 全过 → 完成
2. 仍有失败 → 看 HTTP status：404(路由) / 422(字段) / 500(错误码)
3. 检查 C 改了哪边：改前端还是改后端？改了字段名还是改了路由？

## C 常见错误
| 错误 | 检测方式 | ban 指向 |
|------|---------|---------|
| 只改了一个 controller，其他 controller 同样问题没改 | 不同路径同类失败 | 逐个对标 |
| 改了字段名但没对齐契约 | camelCase/snake_case 混用 | 对齐 api 契约 outputs |
| 改了后端返回没改前端接收 | 前端期望 `orderId` 收到 `order_id` | 两端都改或只改一边 |
| 补了路由挂载但路径写错 | `app.use('/api/oders', ...)` | 路径逐字对齐 |
| 改了错误码映射但忘记 import response 模块 | 500 Internal Error | 补 require |

## 反作弊
- C 改了测试文件中的断言字段名来"通过" → `fix_target=test` + CHEAT
- C 删了整个路由 `app.use(...)` 行 → `fix_target=source` + CHEAT
- C 把所有字段名都删了只留空对象 → `fix_target=source` + CHEAT

## 判定矩阵

| 失败 | 源码问题 | 修复 |
|------|---------|------|
| 字段名不匹配(camelCase↔snake_case) | 请求/响应字段未对齐 | **改任一边对齐即可** |
| expected 200 got 401 | Token 缺失或过期 | 检查 Authorization header |
| expected 200 got 404 | 路由未挂载 | app.js 补 `app.use` |
| expected 422 got 500 | 错误码映射错 | 对齐 logic 契约 errorMapping |
| 分页结构不对 | 响应格式未统一 `{list,total,page,pageSize}` | 统一分页格式 |
