# navigation 层源码修复 (C步骤)

C 修改 .vue 页面的 router.push 调用或 router/index.js 路由配置。修复目标: passBy 方式一致，参数名一致。

## 典型 ban → 修复动作

```
PASSBY_MISMATCH:
  passBy=params 但用了 query → 改源页 router.push({ query: {...} }) 为 params
  → 改目标页 route.query.xxx 为 route.params.xxx
  passBy=query 但用了 params → 反向操作

PARAM_NAME_MISMATCH:
  源页传 orderId，目标页读 id → 统一参数名
  → 优先以 navigation truth 的 dataTransfer 字段名为准

ROUTE_MISSING:
  路由名未在 router 中注册 → 在 router/index.js 中添加路由条目
  → 路径必须与 navigation truth 的 toPageRoute 一致
  → 动态段必须匹配: passBy=params 时路径要有 :paramName

DYNAMIC_SEGMENT_MISSING:
  用 params 传递但路由路径无动态段 → 在 router 中添加 /:id 等段
  → 或改用 passBy=query (如果契约允许)
```

## 修复方式
- 单参数名错误 → edit_batch 精准替换
- 路由缺失 → create_files 重写 router/index.js 或 edit_batch 插入路由条目
- 批量 passBy 不一致 → create_files 重写相关 .vue 页面
