# C: db — DDL修复

继承 [static.md](../static.md) 通用规则。

## 🛑 工作流程

1. **先读 prompt 中的「任务检查点」**：每条 checkPoint 定义了 DDL 必须满足的约束
   - `表名与 model 契约一致` → 核对 CREATE TABLE 表名
   - `字段名/类型 vs model 契约一致` → 逐列核对 name + type
   - `NOT NULL/DEFAULT/UNIQUE 约束` → 逐约束核对
   - `FK 引用目标表存在` → 确认被引用的表已在其他 DDL 中定义
2. **对照 checkPoints 逐条验证**，缺失/不匹配的用 edit_batch 修复

## 修复策略

```
表名不对 → CREATE TABLE 表名对齐 model 契约 tableName
字段名/类型错 → ALTER TABLE CHANGE 或修改 CREATE TABLE
缺约束 → 加 NOT NULL / DEFAULT / UNIQUE
FK目标表不存在 → 先确保父表 DDL 存在且被执行
INDEX缺失 → ALTER TABLE ADD INDEX 或 CREATE INDEX
ENUM取值不符 → ALTER TABLE MODIFY COLUMN ... ENUM(...)
SQL语法错 → node --check 或 sql-parser 验证后修正
```

## 🆕 种子数据修复（各 t_db_* 任务自带 seed 检查）

```
seed JSON 列名与 DDL 不一致 → 对照 DDL 真理（t_db_* 产出）修正 JSON key
seed JSON 缺文件 → create_files 从 seedData 契约生成
seed JSON FK 引用不可解析 → 确认被引用表的 seed 中存在对应 id（如 products.merchant_id=1 → merchants.json 有 id=1）
init-db.js --seed-only 执行失败 → 检查 INSERT IGNORE 列名/值格式 → edit_batch 修正 seed JSON
```

## 反作弊

```
□ 不能删 NOT NULL/UNIQUE/FK → CHEAT
□ 不能把所有列改 TEXT → CHEAT
□ 不能改 ENUM 为 VARCHAR → CHEAT（丢失约束）
□ 🆕 不能改 seed JSON 列名来"匹配"错误的 DDL → 修 DDL 而非修 seed
```
