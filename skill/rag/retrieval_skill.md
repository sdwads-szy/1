# 历史经验检索（Brain Agent Retrieval）

## 角色
你是历史经验检索的消费者。在执行开发/测试任务前，调用知识库检索接口，获取相关历史经验（DO/DONT），注入到你的工作上下文中以避免重蹈覆辙。

## 何时使用
- 收到新的代码生成、测试生成、测试修复任务时，**优先检索相关历史经验**
- 用户询问"之前有没有类似的问题"时
- 需要对复杂业务逻辑做出实现决策时

## 检索接口

### Python API

```python
from brainAgent.retrieval_scheduler import retrieval_scheduler, get_prompt_injection

# 方式一：完整检索（推荐，拿到结构化结果）
result = await retrieval_scheduler(
    task_id="b_order",                              # 当前任务 ID（必填）
    query="创建订单时如何扣减库存才能防止超卖？",      # 自然语言查询（必填）
    agent_type="code_generator",                    # Agent 类型（必填）
    top_k_per_angle=3,                              # 每角度取几条（可选，默认 3）
    min_similarity=0.55,                            # 噪音阈值（可选，默认 0.55）
)

# result 结构：
# {
#   "success": True,
#   "summary": "基于3个角度检索到4条相关经验，主要建议：...",
#   "raw_results": [
#     {
#       "id": "exp_xxx",
#       "do": "正确做法",
#       "dont": "错误做法",
#       "context": "场景说明",
#       "similarity": 0.68,
#       "angle_name": "业务流程",
#       "severity": "high",
#       "category": "database_operations",
#       "trigger_contracts": [...],
#       "trigger_tags": [...],
#     },
#     ...
#   ],
#   "delivery": { ... },         # 按 agent_type 格式化
#   "suggestions": [...],        # LLM 给出的建议
# }

# 方式二：直接拿 prompt 注入文本
prompt_text = await get_prompt_injection(
    task_id="b_order",
    query="如何防止并发超卖？",
    agent_type="code_generator",
)
# 返回一段可直接拼入 System Prompt 的文本
```

### agent_type 可选值

| agent_type | 用途 | delivery 格式 |
|------------|------|--------------|
| `code_generator` | 代码生成 | prompt_injection 文本 |
| `test_generator` | 测试生成 | prompt_injection 文本 |
| `test_repair` | 测试修复 | structured JSON |
| `architect` | 架构设计 | structured JSON |
| `requirement` | 需求分析 | structured JSON |

### task_id 说明

`task_id` 会被用于构建图约束过滤（只检索关联合约范围内的经验），常见前缀：
- `b_*` — 后端业务任务（如 `b_order`、`b_payment`）
- `t_*` — 测试任务（如 `t_ut_service_order`）
- `db_*` — 数据库任务（如 `db_sp_create_order`）
- `infra_*` — 基础设施任务
- `f_*` — 前端任务

## 检索原理（简要）

1. **角度分析**：LLM 将用户查询拆解为 3 个检索角度（业务流程、数据一致性、异常与边界）
2. **3×3 扩散检索**：每个角度独立检索 top-3，通过 `exclude_ids` 避免重复
3. **去重 + 噪音过滤**：ID 去重后，低于 `min_similarity` 阈值的丢弃
4. **结果交付**：LLM 将结果整理为适合目标 Agent 消费的格式

知识库当前包含 ~23 条高价值经验，覆盖订单、支付、优惠券、售后等电商核心领域。

## 约束
- 不需要手动调用 `init_retrieval()`，内部自动初始化
- 检索结果数量 = 3~9 条（去重后），取决于知识库覆盖面和噪音阈值
- 相似度范围为 0.0~1.0，中-中同语言匹配 Top-1 通常 0.65~0.70
- `raw_results` 中的 `do`/`dont` 字段是核心经验内容，应优先关注
