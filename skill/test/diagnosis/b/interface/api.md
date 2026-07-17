# B: api — 接口契约诊断

🛑 通用规则见 [../interface.md](../interface.md)。

## 角色

B 评估 api 层**测试代码**写对了没有。A 生成的是 fs.readFileSync 静态契约验证代码，用 `toContain` 而非正则。

- 测试代码有 bug → `fix_target=test`
- 测试代码干净但测试失败 → `fix_target=source` → 加载 D

## 输入

| 输入 | B 怎么用 |
|------|---------|
| `test_file` | 审查对象——fs.readFileSync 契约验证代码 |
| `testScenarios` | 对照标准——input(METHOD path + body)/output(期望格式)/category |
| `raw_result` | Jest JSON——哪个 it() 过了、哪个没过 |

## 逐项检查

### 1. 禁止模式检测

```
□ 测试文件中有 supertest/require('../../app')? → CHEAT — 删了重写
□ 测试文件中有 import/vi.mock?                 → 语法错 — 改 require
□ 测试文件中有 fs.existsSync(.vue)?            → 验证了 frontend 真理 — 删掉
```

### 2. 路径读取正确性

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| workspace 路径 | `path.resolve(__dirname, '..')` 多/少一层 | WRONG_WORKSPACE |
| targetFiles 路径 | 拼写错、多/少 `../` | WRONG_SRC_PATH |
| fs.readFileSync 路径 | 与 targetFiles 不一致 | WRONG_SRC_PATH |

### 3. 前端 API 调用提取

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| endpoint 字符串 | 测试用的 path 与前端真理不一致 | WRONG_PATH |
| method 方式 | 测试断言了 POST 但真理是 GET | WRONG_METHOD |

### 4. 后端路由匹配

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| 路由定义存在 | routeSrc 中找不到 path | ROUTE_NOT_FOUND |
| 中间件挂载 | auth 场景没检查 authenticate | MISSING_AUTH_CHECK |

### 5. Controller 验证

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| handler 函数存在 | 函数名拼写错 | HANDLER_NOT_FOUND |
| response 格式 | 没检查 response.success/res.json | MISSING_RESPONSE_CHECK |
| 字段解构 | req.body.xxx 字段检查不完整 | MISSING_FIELD |

---

## 🛑 字段名/错误码/函数名不一致的判定铁律

**真理/合约是权威来源。** 当测试断言的字段名、错误码、函数名来自真理/合约，但源码使用了不同的命名时：

| 场景 | 测试断言 | 源码实际 | 正确判定 |
|------|---------|---------|---------|
| 字段名不匹配 | `toContain('smsCode')` | 源码解构 `code` | **fix_target=source** — 源码应改为 `smsCode` |
| 错误码不匹配 | `toContain('PHONE_REGISTERED')` | 源码抛 `PHONE_EXISTS` | **fix_target=source** — 源码应改为 `PHONE_REGISTERED` |
| handler 名不匹配 | `toContain('register')` | 源码函数 `doRegister` | **fix_target=source** — 源码应改为 `register` |

🛑 **判定方法**：
1. 查看 B 输入中的 `testScenarios` / 下层真理 → 获取合约规定的字段名/错误码/函数名
2. 对比测试断言 → 如果测试用了真理值 → 测试正确
3. 对比源码实际 → 如果源码用了不同值 → **源码错误，fix_target=source**
4. 🛑 只有当测试**没有依据**（测试自己编造的值，不是来自真理/合约）时，才判 fix_target=test

### total=0 — 测试没跑起来 → fix_target=test

```
SyntaxError / MODULE_NOT_FOUND → test_file:行号 | SYNTAX / MISSING_MODULE
```

### failed>0

逐项检查上面 5 类。查到问题 → fix_target=test。全部通过 → fix_target=source → 加载 D。

🛑 **如果 failed 的原因是后端源码真的缺路由/缺 handler/缺中间件** → 测试代码是正确的，`fix_target=source`。

---

## Ban 格式

```
f=api|test|{test_file}:{行号}|{子类型}
b=DON'T: {哪里错了} — {为什么}
| fix: {测试文件}:{行号} {完整修正代码}
| target=test
```
