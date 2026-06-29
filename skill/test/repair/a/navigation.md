# Navigation层修复策略 (A步骤)
- 修复范围: 页面跳转 passBy、参数名、路由注册
- passBy=params 但用了 query → 统一为 params 传递
- 参数名不一致 (orderId vs id) → 统一参数名
- 路由未注册 → 在 router/index.js 中添加路由条目
