# navigation 层诊断 (B步骤)

诊断范围限定: 页面跳转参数传递（passBy + 参数名）。

## 判定规则

```
total=0 + route.name 'Xxx' not found → fix_target=source, 子类型=ROUTE_MISSING
total=0 + route.params.xxx is undefined → fix_target=source, 子类型=PASSBY_MISMATCH
total>0 + 参数名不匹配 (传 orderId 读 id) → fix_target=source, 子类型=PARAM_NAME_MISMATCH
total>0 + 路由路径无动态段但用了 params → fix_target=source, 子类型=DYNAMIC_SEGMENT_MISSING
```

## 常见失败模式

1. passBy=params 但源页 `router.push({ query: { orderId } })` → 目标页 `route.params.orderId = undefined` → PASSBY_MISMATCH
2. passBy=query 但源页 `router.push({ params: { orderId } })` → 目标页 `route.query.orderId = undefined` → PASSBY_MISMATCH
3. 源页传 `{ params: { id: orderId } }`，目标页读 `route.params.orderId` → 参数名不一致 → PARAM_NAME_MISMATCH

## 禁止扩大到
- 页面内部渲染逻辑 (frontend_static层)
- 后端 API 路径 (api层)
- 业务流程 (logic/scenario层)
