# c: auth 层 — 源码修复

## 下层真理（不可质疑 — 来自 bans_text）
- **infra**: JWT 库已安装，ENCRYPTION_KEY 可用
- **api**: 认证端点 `POST /api/auth/login` 请求/响应格式已锁定

## 输入输出对齐
```
api 输出 → auth 输入:
  POST /api/auth/login → IN:{phone,password} → 对齐 login 函数参数
  Response → OUT:{userId,accessToken,refreshToken,role} → auth 返回对齐
infra 输出 → auth 输入:
  JWT_SECRET 已加载 → jwt.sign/verify 直接用 process.env.JWT_SECRET
```

## 修复策略

### Token payload 缺字段
- auth 契约 tokenConfig.payload: {userId, role} → jwt.sign 必须包含
- 治: `jwt.sign({ userId: user.id, role: user.role }, JWT_SECRET, { expiresIn: '1h' })`

### 中间件未挂载
- hasRole('admin') / authenticate 未在路由前声明
- 治: `router.put('/:id', authenticate, hasRole('admin'), controller.xxx)`

### owner 校验缺失
- 用户可以操作不属于自己的资源
- 治: `if (req.user.id !== resource.userId) return response.forbidden(res)`

### refresh 失败
- refreshToken 过期/存储丢失/验证失败
- 治: 检查 refreshToken TTL(24h) + verify 逻辑

## 工具选择
- JWT 配置/中间件链重构 → `create_file`
- 单路由补中间件 → `edit_batch`
