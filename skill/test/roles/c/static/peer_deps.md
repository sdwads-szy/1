# C: peer_deps — 同层引用修复

继承 [static.md](../static.md) 通用规则。

## 🛑 工作流程

1. **先读 prompt 中的「任务检查点」**：peer_deps 的 checkPoints 指定了必须验证的同层引用关系
   - `A 文件 require/import B → B 确实导出被引用的名称` → 提取 B 的导出，核对 A 的导入
   - `require 路径文件存在` → 确认目标文件在磁盘上
   - `exportStyle 与下游 require 方式一致` → named/default/object 匹配
2. **对照 checkPoints 逐条验证**，不匹配的修正引用路径或导出风格

## 修复策略

```
🛑 CJS require 链断裂（node app.js 启动不了的第一原因）:
  - routes/auth.js require('./controllers/authController') → 确保 controllers/authController.js 存在
  - controllers/authController.js require('../services/authService') → 确保 services/authService.js 存在
  - 文件不存在 → create_files 创建；路径层级错了 → edit_batch 修正

ESM import 目标不存在:
  - import {X} from '@/api/auth' → 确保 src/api/auth.js 存在且导出 X

exportStyle 不匹配:
  - 目标 module.exports = X(default) → 消费方 const X = require()（不能解构）
  - 目标 module.exports.xxx(named) → 消费方可 const {xxx} = require()
  - 目标 export default → 消费方 import X from（不能 import {X}）

循环依赖 A→B→A → 提取公共依赖到第三个文件或重构
```

## 反作弊

```
□ 不能删 require 来"解决"引用错误 → CHEAT
□ 不能把 named export 全改 default export → CHEAT
```
