# A: api — 前端↔后端接口契约验证

🛑 **禁止 supertest、禁止 require('../../app')、禁止数据库连接**。
🛑 代码模板见 [templates/interface/api.md](../../../templates/interface/api.md)。

继承 [interface.md](../interface.md) 通用规则。

## 工作流

场景定方向（测哪些端点、什么 category），**模板定参数提取方式**。

🛑 参数提取规则全部在模板中——包括从哪种真理取、取哪个字段、fallback 规则。这里不重复。

1. 读场景 → 确定测试范围（scenario 名 → it() 描述，category → 启用维度）
2. 按模板提取参数 → 填入骨架
3. create_files 输出

## 验证维度

| 维度 | category | 验证内容 | 期望值来源 |
|------|:---:|------|------|
| 路由匹配 | correct | path 在 routeSrc 中 | 模板参数提取 |
| handler 存在 | correct | handler 名在 ctrlSrc 中 | 模板参数提取 |
| 字段一致 | correct | controller 接收了预期字段 | 模板参数提取 |
| 中间件链 | auth | route 挂载了正确中间件 | 模板参数提取 |
| 错误码映射 | error | controller 的错误码与契约一致 | 🛑 模板参数提取。禁止编造错误码名 |
| 响应格式 | correct | controller 使用规范响应 | `includes('response.success')` 等 |

## 🛑 断言原则

| ❌ 错误 | ✅ 正确 |
|--------|--------|
| 写正则 `toMatch(/regex/)` | `toContain(path)` / `includes('str')` |
| 用 `escapeRegex()` + `new RegExp()` | 模板给的精确值，`toContain` 即可 |
| 担心引号/空格格式 | `toContain` 做子串匹配，不关心格式 |

## 禁止的反模式

```
❌ 写正则匹配路由/handler/中间件 → 模板给精确值，toContain 即可
❌ 只用场景不用模板参数提取规则 → 断言值不精确
❌ 场景有但真理没有的端点 → 功能未实现，跳过不测
```

## 特有规则

- 🛑 绝对不用 supertest、不用 require('../../app')、不用任何 HTTP 库
- 🛑 只写测试文件，不改任何源码
- 🛑 workspace 路径铁律: `path.resolve(__dirname, '..')`

## 自我修复

B 判定 `fix_target=test` → 加载 [repair/a/interface/api.md](../../../repair/a/interface/api.md)。
