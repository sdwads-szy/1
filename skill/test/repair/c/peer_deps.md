# peer_deps 层源码修复 (C步骤)

C 修改 require/import 语句。修复目标: 引用目标存在，exportStyle 匹配。

## 典型 ban → 修复动作

```
MISSING_MODULE:
  require('./xxx') 目标不存在 → 检查文件系统确认实际路径
  → 修正为正确路径，或创建桩文件（仅当该模块被剪枝导致时）

MISSING_IMPORT:
  from '@/pages/Xxx' 目标不存在 → 检查 src/ 下的实际文件位置
  → 修正路径: @/pages/auth/Login.vue → @/pages/Login.vue (如果文件在根目录)
  → 或创建缺失文件（如果该任务被剪枝）

EXPORT_MISMATCH:
  目标 module.exports = X (default导出) 但消费方 const { X } = require()
  → 改消费方为 const X = require() (不解构)
  目标 module.exports.xxx (named导出) 但消费方 const x = require()
  → 改消费方为 const { xxx } = require() (解构)

CIRCULAR_DEP:
  A→B→A 循环引用 → 提取公共部分到第三个文件
  → 或将 B 中对 A 的引用改为延迟 require (不推荐，治标不治本)
```

## 修复方式
- 路径错误 → edit_batch 替换路径字符串
- exportStyle 不匹配 → 统一消费方的 require/import 写法
- 桩文件 → create_files 创建最小占位模块
