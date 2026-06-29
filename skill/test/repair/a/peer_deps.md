# 同层依赖层修复策略 (A步骤)
- 修复范围: require/import 目标不存在、exportStyle 消费不匹配
- require 目标不存在 → 创建桩文件或修正路径
- exportStyle default vs named 不匹配 → 统一导出/消费格式
