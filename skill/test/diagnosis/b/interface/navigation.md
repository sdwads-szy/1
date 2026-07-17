# B: navigation — 测试代码诊断

🛑 通用规则见 [../interface.md](../interface.md)。

## 角色

B 评估 navigation 层**测试代码**写对了没有。navigation 验证页面间跳转的 passBy 方式 + 参数名一致性，用 `fs.readFileSync` + `toContain`/`includes` 静态检查。

🛑 **navigation 不验证 .vue 文件存在和 router 注册**——那是 frontend 真理。

- 测试代码有 bug → `fix_target=test`
- 测试代码干净但测试失败 → `fix_target=source` → 加载 D

## 输入

| 输入 | B 怎么用 |
|------|---------|
| `test_file` | 审查对象——fs.readFileSync + toContain/includes 检查 |
| `testScenarios` | 对照标准——fromPage/toPage/passBy/dataTransfer |
| `raw_result` | Jest JSON |

## 逐项检查

### 1. 真理边界

🛑 **以下内容 frontend 已验证，navigation 测试不应重复验证：**

| 不应验证 | 原因 | 子类型 |
|---------|------|--------|
| .vue 文件是否存在 | frontend 真理 | VERIFIED_TRUTH |
| router 是否注册了该路由 | frontend 真理 | VERIFIED_TRUTH |
| .vue 文件的 template/style | 不是 navigation 职责 | OFF_TOPIC |

### 2. 文件路径

| 常见错误 | 子类型 |
|---------|--------|
| 页面 .vue 路径编造 | WRONG_SRC_PATH |
| 路径层级错（少/多了一层 `../`） | WRONG_SRC_PATH |

### 3. passBy 验证覆盖

对照 testScenarios，检查测试是否正确验证了跳转逻辑：

🛑 **两段式检查**: 源页传参方式 + 参数名一致性，两段都对才算通过。

| 检查项 | 测试应该验证 | 子类型 |
|--------|------------|--------|
| 源页传参方式 | `includes('params:')` 还是 `includes('query:')` | INCOMPLETE_CHECK |
| 参数名一致 | 源页 `toContain(paramName)` + 目标页 `toContain(paramName)` | INCOMPLETE_CHECK |

→ 只查了一个、漏了另一个 = INCOMPLETE_CHECK

### 4. 参数名一致性

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| 源页传参名 vs 目标页取参名 | 源页传 orderId 但测试只验证了目标页读 id | INCOMPLETE_CHECK |
| 参数名与 dataTransfer 一致 | 测试用的参数名与 testScenario.dataTransfer 不同 | PARAM_NAME_MISMATCH_IN_TEST |

### 5. 场景覆盖

navigation 至少 correct + error：

| 场景 | 内容 |
|------|------|
| correct | passBy + 参数名正确 → 参数能传递 |
| error | passBy 不匹配或参数名不一致 → 取不到值 |

→ 子类型: MISSING_ERROR_CASE

---

## 判定

### total=0 → fix_target=test

```
SyntaxError        → test_file:行号 | SYNTAX
MODULE_NOT_FOUND   → test_file:行号 | MISSING_MODULE
```

### total>0 && failed>0

**先查上面 5 项。** 查到测试自身错误 → fix_target=test。

🛑 **参数名/passBy 不匹配判定铁律**：真理/合约是权威。测试的 passBy 方式（params/query）和参数名来自 testScenarios → 若源码使用了不同的传参方式或参数名 → **fix_target=source**（源码应修改以匹配合约）。只有当测试自己编造了不存在于 testScenarios 中的值时，才判 fix_target=test。

全部通过 → fix_target=source → 加载 D。

---

## Ban 格式

```
f=navigation|test|{test_file}:{行号}|{子类型}
b=DON'T: testScenario "{场景名}" {哪里错了} — {为什么}
| fix: {测试文件}:{行号} {完整修正代码}
| target=test
```

🛑 f 前缀用 `navigation` 不用 `nav`。
