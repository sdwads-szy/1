# C repair: 静态层

D 判定分类后 C 的二次修复策略。适用于 db / frontend / infra / peer_deps / integ。

🆕 **范围铁律**: 构建命令（vite build / node app.js）的错误如果不在 targetFiles 内，不是你的问题。只修本任务管辖的文件。

## UNCHANGED — 同 ban 再命中

| 层 | C 常见失误 | 纠正 |
|----|----------|------|
| db | 改错 DDL 文件/表 | 确认 B ban 指向的表文件 |
| frontend | vite build 报错但文件不在 targetFiles | 🆕 忽略，那是其他任务的文件 |
| frontend | import 路径仍错 | 确认 @/ 别名解析正确 |
| infra | 导出签名仍缺 | 确认 module.exports.xxx 完整 |
| infra | .env 不同步 | 以 .env.example 为准同步四文件 |
| peer_deps | node app.js 报错但文件不在 targetFiles | 🆕 忽略 |
| peer_deps | require 路径仍错 | 确认相对路径层级 |
| integ | app.use 仍漏路由 | 逐条检查 app.js |
| integ | .env *_MODE 值为占位符 | 改为 mock（代码默认 mock 兜底） |
| integ | .env 四文件变量集不一致 | 以 .env.example 为准同步 |
| integ | process.env.X 引用缺 env 配置 | 扫描代码补全变量 |
| db | database/seed/*.json 列名与 DDL 不一致 | 对照 t_db_* 真理修正 seed JSON 列名 |
| db | init-db.js --seed-only 失败 | 检查 seed JSON 的 INSERT IGNORE 列名/值格式 |

## REGRESSION — 原来 PASS 现在 FAIL

| 层 | C 常见失误 | 纠正 |
|----|----------|------|
| db | 修 A 表误改 B 表 DDL | 只改 B ban 指定的文件 |
| frontend | 修 A 组件导致 B 组件 import 失败 | 检查共享模块 |
| infra | 改 config 导出导致所有引用失效 | 保持向后兼容 |
| peer_deps | 修 A 文件 require 导致循环依赖 | 提取公共到第三个文件 |

## DEGRADED — 新错误

| 层 | C 常见失误 | 纠正 |
|----|----------|------|
| db | FK 引用目标表不存在 | 先确保父表已创建 |
| frontend | 🆕 vite build 新错误不在本任务文件 | 可能是其他任务改动导致，输出 ban 说明根因 |
| infra | 新加的 config 导出未测试 | 检查所有引用处 |
| peer_deps | 🆕 node app.js 新错误不在本任务文件 | 输出 ban，标记为其他任务问题 |

## CHEAT

| 层 | 常见作弊 | 纠正 |
|----|---------|------|
| db | 删 NOT NULL/FK/UNIQUE 约束 | 恢复 |
| db | 所有列改 TEXT | 按契约恢复正确类型 |
| frontend | 删 import / 清空 <script> | 恢复 |
| frontend | 🆕 改 vite.config.js 跳过编译 | 恢复 |
| infra | 把 pool 改 {} 空对象 | 恢复正确实现 |
| infra | 给 package.json 加 "type": "module" | 🛑 严禁 |
| peer_deps | 删 require 来"解决"引用错误 | 正确修复引用 |
