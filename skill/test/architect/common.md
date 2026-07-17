# 测试架构师 — 通用规则

## 依赖推导方法

### 纵向（跨层）— 4 问

```
1. 本层要做什么事？
2. 干事需要什么信息？
3. 直接下层提供了什么？
4. 够了吗？还需要从其他层拿什么？
```

**黑盒判断**：中间层已验证的东西，不穿透。

```
api 需要 DB 列名 → db_api 已验证 → 依赖 db_api，不依赖 db
logic 需要服务函数 → backend_proc 已验证 → 依赖 backend_proc，不依赖 api
```

### 横向（同层）— 3 问

```
1. 本层内的任务之间有先后顺序吗？
2. 后面的任务是否需要前面任务的验证结果？
3. 按什么规则排序？
```

**5 种同层依赖模式**：

| 模式 | 何时出现 | 怎么判断 |
|------|---------|---------|
| **FK 链** | 有外键引用的表 | 被引用表先于引用表 |
| **配置→消费者** | config 被其他代码依赖 | 配置文件先验证 |
| **鉴权先于业务** | 需要 token 的接口 | auth 先验证 token |
| **业务流程** | 步骤有先后 | 前一步通过后一步才成立 |
| **独立模块** | 互不依赖 | 不写依赖 |

**判断同层的核心问题**：B 执行时，是否需要"A 已验证通过"这个事实？需要→写。不需要→不写。

---

## 🛑 dependency 写法规则

1. **只写直接依赖，不穿透**：api 依赖 `t_dbapi_*`，不依赖 `t_db_*`
2. **同层序列必须写**：`t_db_order` 的 dependencies 含 `t_db_user`
3. **禁止回环**：api 不能依赖 logic
4. **logic 只依赖 backend_proc**，🛑 禁止依赖 api/db_api（backend_proc 真理已封装全部接口层验证结果）
5. **scenario 只依赖 logic + navigation**，🛑 不直接依赖 backend_proc/api/db_api
6. **NFR 端点型只依赖 scenario**（chains[].endpoints[]），页面型加 navigation，配置型加 infra，Token加 auth

---

## 输出格式 — 公共字段

| 字段 | 说明 |
|------|------|
| `id` | `t_{层}_{功能}` |
| `layer` | infra/db/frontend/peer_deps/auth/api/db_api/navigation/backend_proc/logic/scenario/nfr/integ/repair |
| `testType` | static / interface / logic / quality |
| `sourceTask` | 原始 engineer task id |
| `targetFiles` | C 步骤需要修改的文件 |
| `dependencies` | 直接依赖的 test task id（纵向 + 横向） |
| `testFramework` | jest / jest+supertest / null(静态层) / k6(性能) |
| `testScenarios` | 非静态层用 |
| `checkPoints` | 静态层用（代替 testScenarios） |

---

## 闭合检查区

- [ ] 每个 sourceTask 都有对应的 test task
- [ ] dependencies 按规则填写（不穿透、不含 router/index.js 于 navigation 等）
- [ ] 同层依赖已检查（FK 链、配置链、业务流程）
- [ ] 各层任务数达标（见各层文件的输出范围）
- [ ] 依赖图无循环
