# peer_deps 层诊断 (B步骤)

诊断范围限定: require/import 目标是否存在，exportStyle 是否匹配。

## 判定规则

```
total=0 + Cannot find module './xxx' → fix_target=source, 子类型=MISSING_MODULE
total=0 + xxx is not a function → fix_target=source, 子类型=EXPORT_MISMATCH
total>0 + 模块加载成功但导出名不对 → fix_target=source, 子类型=WRONG_EXPORT_NAME
```

## 常见失败模式

1. `Error: Cannot find module '../utils/hash'` → 文件不存在 → MISSING_MODULE
2. `TypeError: redis.client.get is not a function` → config/redis.js 是 `module.exports = client`(default导出)，但消费方写了 `redis.client.get()` → EXPORT_MISMATCH
3. `TypeError: logger.info is not a function` → config/logger.js 是 `module.exports = logger`(default导出)，但消费方写了 `const { logger } = require()`(解构) → EXPORT_MISMATCH

## 禁止扩大到
- 文件内部逻辑 (infra/backend_proc层)
- 接口路径 (api层)
