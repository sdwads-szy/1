# d: peer_deps 层 — 源码验证

C 修改了 require/import 语句后，验证修复是否有效。

## 验证步骤

1. **require 目标存在性**
   - 扫描修改后文件中所有 `require('./...')` 
   - 每个目标文件是否存在（加 .js / .vue / /index.js 扩展名试）
   - 不存在 → C 引入了新的错误路径 → ban 标记 MISSING_MODULE

2. **import 目标存在性**
   - 扫描 `from '@/...'` 和 `import('@/...')`
   - 解析 @/ → src/，检查文件存在
   - 不存在 → ban 标记 MISSING_IMPORT

3. **exportStyle 消费匹配**
   - 目标文件是 `module.exports = X`（default导出）→ 消费方不能 `const { X } = require()`
   - 目标文件是 `module.exports.xxx`（named导出）→ 消费方可以解构
   - 不匹配 → ban 标记 EXPORT_MISMATCH

4. **无循环依赖**
   - 修改后的文件是否形成了 A→B→A 的循环引用？
   - 有 → ban 标记 CIRCULAR_DEP

## ban 指纹格式

f = peer_deps|source|{文件}|{子类型}

子类型: MISSING_MODULE / MISSING_IMPORT / EXPORT_MISMATCH / CIRCULAR_DEP
