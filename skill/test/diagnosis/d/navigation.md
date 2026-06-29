# d: navigation 层 — 源码验证

C 修改了页面跳转代码或 router 配置后，验证修复是否有效。

## 验证步骤

1. **passBy 一致性**
   - 契约 passBy=params → 源页用 `router.push({ params: {...} })`？目标页用 `route.params.xxx`？
   - 契约 passBy=query → 源页用 `router.push({ query: {...} })`？目标页用 `route.query.xxx`？
   - 不一致 → C 改错了方向 → ban 标记 PASSBY_MISMATCH

2. **参数名一致性**
   - 源页传 `router.push({ params: { orderId } })` → 目标页读 `route.params.orderId`
   - 参数名是否一致（不能是 `id` vs `orderId`）？
   - 不一致 → ban 标记 PARAM_NAME_MISMATCH

3. **路由存在性**
   - 源页 `router.push({ name: 'Xxx' })` 的 Xxx 在 router 中是否注册？
   - 未注册 → C 漏了注册路由 → ban 标记 ROUTE_MISSING

4. **动态段匹配**
   - passBy=params 时，路由路径 `/payment/:id` 是否有对应的 `:paramName` 段？
   - 没有 → 路由定义不完整 → ban 标记 DYNAMIC_SEGMENT_MISSING

## ban 指纹格式

f = navigation|source|{页面}|{子类型}

子类型: PASSBY_MISMATCH / PARAM_NAME_MISMATCH / ROUTE_MISSING / DYNAMIC_SEGMENT_MISSING
