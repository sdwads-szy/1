# D: backend_proc — 源代码诊断 + 修复验证

🛑 通用规则见 [../logic.md](../logic.md)。

## 角色

D 是 backend_proc 层**源代码分析专家**。B 加载 D 写 source ban，D 验证 C 的修复。

## 职责一：源代码根因分析（供 B 加载）

### 源码断点定位

🛑 按 **process 步骤序号** 定位源码断点：

| 测试症状 | 源码根因 | 断点位置 |
|---------|---------|---------|
| beginTransaction 未被 mock 调用 | service 开头缺 `const conn = await db.beginTransaction()` | service 第1行 |
| commit 未被 mock 调用 | try 块末尾缺 `await conn.commit()` | try 块末尾 |
| rollback 未被 mock 调用 | catch 块缺 `await conn.rollback()` | catch 块 |
| SELECT 非 FOR UPDATE | SQL 缺 `FOR UPDATE` | SELECT 语句末尾 |
| mock 第N次调用参数不匹配 | SQL 语句或参数与 process 定义不一致 | 对应步骤的 conn.execute 行 |
| affectedRows=0 未 throw | UPDATE 后缺 `if (affectedRows===0) throw` | UPDATE 下一行 |
| 返回字段缺失 | return 语句字段与 output 不一致 | service 的 return 行 |
| 关联表未插入 | 缺某步骤的 INSERT | 两个 SQL 操作之间 |
| catch 吞异常 | rollback 后缺 `throw err` | catch 块末尾 |

### C 常见改错方式（B 用来写 ⚠️C注意）

| C 错误 | 为什么错 | ⚠️预警 |
|--------|---------|--------|
| 加 beginTransaction 忘 commit | 事务永不提交 | try 块完整性 |
| 事务内用 db.query() | 不走事务连接 | 全部用 conn.execute |
| 补 INSERT 列名写错 | order_id vs orderId | 对照 DDL truth |
| 加步骤不更新 mock 序号 | toHaveBeenNthCalledWith 全偏移 | 重算所有序号 |
| catch 只有 rollback 没 throw | 异常被吞 | catch 块必须 throw |

### 防作弊底线

```
□ beginTransaction/commit/rollback 被删除 → CHEAT
□ FOR UPDATE 被去掉 → CHEAT
□ 异常处理被删除只留成功路径 → CHEAT
□ affectedRows 检查被删除 → CHEAT
□ 整个 service 函数替换为 return 硬编码 → CHEAT
```

---

## 职责二：验证 C 的修复

### 分类判定

| 分类 | backend_proc 层特征 |
|------|-------------------|
| UNCHANGED | C 加了 beginTransaction 忘 commit / 改错步骤序号 |
| REGRESSION | 改步骤N SQL 改变 mock 参数顺序 / 加 INSERT 导致序号偏移 / 加字段导致 toMatchObject 失败 |
| DEGRADED | C 加 INSERT 列名写错 / DEFAULT 值不对 |
| CHEAT | 删事务/锁/异常处理 / return 硬编码 |

### 验证步骤

**1. 变更分析** — C 改了哪些 service/controller 文件？

**2. 逐条验收** — 按 process 步骤逐条验证。

**3. 回归扫描**:

| 高频 REGRESSION | 检测方法 |
|---------------|---------|
| 改步骤N SQL 改变参数顺序 | 对比 B/D 的 mock.calls 顺序 |
| 添加 INSERT 改变调用次数 | 检查 toHaveBeenNthCalledWith 的 n |
| 加字段后 toMatchObject 失败 | 检查 return vs 原有断言 |

**4. 意图分析** — 三要素：动机+影响+替代。

**5. 二次指导**:

| 分类 | 二次指导 |
|------|---------|
| UNCHANGED | C 的代码 vs process 差异 + 正确事务结构 |
| REGRESSION | 完整 mock 调用顺序（所有 NthCalledWith 参数） |
| DEGRADED | 对照 DDL truth 给出正确列名和约束 |
| CHEAT | 回滚 + 正确事务实现 + ⚠️ 警告 |

### D Ban 格式

```
f=backend_proc|source|{file}:{行号}|{分类}
b=DON'T: {C做了什么}导致{什么测试失败}
| C改动: {C的代码变更}
| B要求: {B原始ban的fix}
| fix: {第二次修复的完整代码}
| ⚠️ C注意: {风险预警}
| target=source
```
