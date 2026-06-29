# d: frontend_static 层 — 源码验证

C 修改了 .vue 文件或 API 模块或 router 后，验证修复是否有效。

## 验证步骤

1. **SFC 语法验证**
   - 对每个被修改的 .vue 文件，提取 `<script>` 块运行 `node --check`
   - 语法仍有错 → C 改坏了 → ban 标记 DEGRADED

2. **import 路径验证**
   - 扫描修改后的文件中所有 `from '@/...'` 和 `import('@/...')`
   - 解析每个路径 → 目标文件存在？
   - 不存在 → C 引入了新的错误路径 → ban 标记 MISSING_IMPORT

3. **Store 属性验证**
   - 对比修改前后的 store 引用
   - C 是否引入了 store truth 中不存在的属性名？
   - 是 → ban 标记 STORE_REF

4. **命名导出验证**
   - API 模块是否有 `export default`？
   - 有 → C 改错了导出格式 → ban 标记 DEFAULT_EXPORT

5. **响应解包验证**
   - 页面中 `res.xxx` 是否应为 `res.data.xxx`？
   - 对照 backend truth 的 response 结构判断

## ban 指纹格式

f = frontend_static|source|{文件}|{子类型}

子类型: syntax / MISSING_IMPORT / STORE_REF / DEFAULT_EXPORT / RESPONSE_UNWRAP
