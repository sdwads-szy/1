# agent/prompt_builder.py
"""
统一提示词组装器 —— 所有 5 类 Agent 共用。

固定顺序（保证跨 task 的缓存命中率）:
  1. skill/engineer/{type}.md       — Agent 专属 skill
  2. 上游真理                         — 已生成模块的对外接口（LLM 提取，非文件列表）
  3. skill/code/quality.md          — 代码质量 + 运行时三端规范（所有 Agent）
  4. skill/code/readability.md      — 可读性（所有 Agent）
  5. skill/code/ui.md               — 前端设计（仅 frontend）
"""

from pathlib import Path
from typing import Optional

_PROJECT_ROOT = Path(__file__).parent.parent

_SKILL_PATHS = {
    "quality":      _PROJECT_ROOT / "skill" / "code" / "quality.md",
    "readability":  _PROJECT_ROOT / "skill" / "code" / "readability.md",
    "ui":           _PROJECT_ROOT / "skill" / "code" / "ui.md",
    "infra":        _PROJECT_ROOT / "skill" / "engineer" / "infrastructure.md",
    "db":           _PROJECT_ROOT / "skill" / "engineer" / "database.md",
    "backend":      _PROJECT_ROOT / "skill" / "engineer" / "backend.md",
    "frontend":     _PROJECT_ROOT / "skill" / "engineer" / "frontend.md",
    "integration":  _PROJECT_ROOT / "skill" / "engineer" / "integrator.md",
}

_cache: dict = {}


def _load(name: str) -> str:
    """带缓存的 skill 文件加载。"""
    if name in _cache:
        return _cache[name]
    path = _SKILL_PATHS.get(name)
    if path and path.exists():
        content = path.read_text("utf-8")
        _cache[name] = content
        return content
    return ""


def _load_upstream_truths(agent_type: str, task: dict = None) -> str:
    """加载上游 engineer 真理，按同层/上层分类格式化。

    规则：
    - 下层真理 (truth.type != agent_type) → 展示 exposed_to_upper（上层需要知道的接口）
    - 同层真理 (truth.type == agent_type) → 展示 exposed_to_peers（同层 import 依赖）
    """
    import json
    truth_dir = _PROJECT_ROOT / "Memory" / "truths" / "engineer"
    if not truth_dir.exists():
        return ""

    # 本 agent 需要的上游类型白名单
    # 🛑 frontend 先生成 (Layer 1), backend 后生成 (Layer 2)
    allowed_types = {
        "infra": set(),
        "db": {"infra"},
        "frontend": {"infra", "db"},                    # 前端: 看 infra + db
        "backend": {"infra", "db", "frontend"},          # 后端: 看 infra + db + 前端真理
        "integration": {"infra", "db", "frontend", "backend"},  # 集成: 看全部
    }

    allowed = allowed_types.get(agent_type, set())
    upper_blocks = []  # 下层 → 本层的接口
    peer_blocks = []   # 同层 → 同层的接口

    for fp in sorted(truth_dir.glob("*.json")):
        try:
            t = json.loads(fp.read_text("utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            from utils.logger import log_warning
            log_warning("failed to load truth file", file=str(fp), error=str(e)[:100])
            continue

        tid = t.get("task_id", fp.stem)
        ttype = t.get("type", "")
        if ttype not in allowed:
            continue

        exposed = t.get("exposed", {})
        if not exposed or not isinstance(exposed, dict):
            continue

        desc = t.get("description", "")
        is_peer = (ttype == agent_type)

        if is_peer:
            # 同层：展示 exposed_to_peers（本层其他文件的 import 依赖）
            data = exposed.get("exposed_to_peers") or exposed.get("services") or exposed
            block = _format_exposed_full(ttype, data, "同层")
            if block:
                peer_blocks.append(f"#### @truth {tid} [{ttype}] — {desc}\n{block}")
        else:
            # 下层 → 上层：展示 exposed_to_upper
            data = exposed.get("exposed_to_upper", exposed)  # 兼容旧格式（无 exposed_to_upper 包裹）
            block = _format_exposed_full(ttype, data, "上层")
            if block:
                upper_blocks.append(f"#### @truth {tid} [{ttype}] — {desc}\n{block}")

    if not upper_blocks and not peer_blocks:
        return ""

    parts = ["\n## 🛑 上游真理（已生成的模块暴露面，必须对齐，不可质疑）",
             "以下接口已被测试验证为正确，如果出现字段不匹配/类型错误/参数顺序错，",
             "错在本层代码，下层的函数签名/表结构/接口格式是绝对正确的。"]

    if upper_blocks:
        parts.append(f"\n### ⬆ 上层接口（{', '.join(sorted(allowed - {agent_type}))} → {agent_type}）")
        parts.extend(upper_blocks)

    if peer_blocks:
        parts.append(f"\n### ↔ 同层接口（{agent_type} 内部 import 依赖）")
        parts.extend(peer_blocks)

    return "\n".join(parts) + "\n"


def _format_exposed_full(ttype: str, exposed: dict, category: str) -> str:
    """完整展示接口细节。category 为 "上层" 或 "同层"。"""
    lines = []

    if ttype == "db":
        for tbl in exposed.get("tables", []):
            tname = tbl.get("name", "?")
            lines.append(f"**表 `{tname}`**")
            for fld in tbl.get("fields", []):
                lines.append(f"- `{fld['name']}` {fld.get('type','')} {fld.get('constraints','')}".rstrip())
            for idx in tbl.get("indexes", []):
                lines.append(f"- INDEX {idx.get('name','')} ({', '.join(idx.get('columns',[]))})")
            for fk in tbl.get("foreignKeys", []):
                lines.append(f"- FK ({', '.join(fk.get('columns',[]))}) -> {fk.get('references','')}")

    elif ttype == "infra":
        mw_list = exposed.get("middleware", [])
        for mw in mw_list:
            lines.append(f"- middleware `{mw['name']}`: {mw.get('signature','')}")
        util_list = exposed.get("utils_exports") or exposed.get("utils", [])
        for util in util_list:
            exps = util.get("exports", [])
            if exps:
                lines.append(f"- `{util.get('file','')}` exports: {', '.join(exps)}")
        cfg_list = exposed.get("config_exports") or exposed.get("config", [])
        for cfg in cfg_list:
            exps = cfg.get("exports", [])
            if exps:
                lines.append(f"- `{cfg.get('file','')}` exports: {', '.join(exps)}")
        if exposed.get("env_vars_used"):
            lines.append(f"- env vars: {', '.join(exposed['env_vars_used'])}")
        internal = exposed.get("internal_exports", [])
        for ie in internal:
            exps = ie.get("exports", [])
            by = ie.get("imported_by", [])
            if exps:
                lines.append(f"- `{ie.get('file','')}` exports: {', '.join(exps)} (imported by: {', '.join(by)})")

    elif ttype == "backend":
        if category == "同层":
            for svc in exposed.get("services", []):
                for fn in svc.get("functions", []):
                    lines.append(f"- `{fn['name']}({', '.join(fn.get('params',[]))})` -> {fn.get('returns','?')}")
            for ci in exposed.get("cross_task_imports", []):
                lines.append(f"- `{ci.get('file','')}` imports: {', '.join(ci.get('imports',[]))}")
        else:
            for route in exposed.get("routes", []):
                bp = route.get("basePath", "")
                for h in route.get("handlers", []):
                    mw = f" [{', '.join(h.get('middleware',[]))}]" if h.get("middleware") else ""
                    req = f" req={h.get('request','?')}" if h.get("request") else ""
                    res = f" res={h.get('response','?')}" if h.get("response") else ""
                    lines.append(f"- {h.get('method','?')} `{bp}{h.get('path','')}` -> `{h.get('handler','?')}`{mw}{req}{res}")

    elif ttype == "frontend":
        for page in exposed.get("pages", []):
            lines.append(f"- page `{page.get('file','?')}` route={page.get('route','?')}")
        for store in exposed.get("stores", []):
            by = f" (used by: {', '.join(store.get('imported_by',[]))})" if store.get("imported_by") else ""
            lines.append(f"- store `{store.get('file','?')}`: actions=[{', '.join(store.get('actions',[]))}]{by}")
        for r in exposed.get("router", []):
            lines.append(f"- route `{r.get('path','?')}` -> {r.get('component','?')}")
        for ac in exposed.get("api_calls", []):
            lines.append(f"- API calls from `{ac.get('from','?')}`: {', '.join(ac.get('endpoints',[]))}")

    return "\n".join(lines) if lines else ""
def _format_exposed_summary(exposed: dict, ttype: str) -> str:
    """精简展示：只列文件名和导出数量（供间接下游参考）。"""
    lines = []
    if ttype == "backend":
        routes = exposed.get("routes", [])
        if routes:
            handler_count = sum(len(r.get("handlers", [])) for r in routes)
            route_files = [r.get("file", "?") for r in routes]
            lines.append(f"- {len(route_files)} 个路由文件, {handler_count} 个 handler: {', '.join(route_files)}")
        svcs = exposed.get("services", [])
        if svcs:
            fn_count = sum(len(s.get("functions", [])) for s in svcs)
            lines.append(f"- {len(svcs)} 个 service, {fn_count} 个函数")
    elif ttype == "frontend":
        lines.append(f"- {len(exposed.get('pages',[]))} 个页面, {len(exposed.get('stores',[]))} 个 store")
    elif ttype == "infra":
        lines.append(f"- {len(exposed.get('middleware',[]))} 个中间件, {len(exposed.get('utils',[]))} 个工具模块")
    elif ttype == "db":
        lines.append(f"- {len(exposed.get('tables',[]))} 张表")
    return "\n".join(lines) if lines else ""


def build_system_prompt(agent_type: str, workspace: str = "",
                        extra_instructions: str = "", task: dict = None) -> str:
    """构建 Agent 系统提示词（固定顺序）。

    Args:
        agent_type: "infra" | "db" | "backend" | "frontend" | "integration"
        workspace: 工作区绝对路径
        extra_instructions: 额外注入的指令（如架构师 envConstraints）
        task: 当前任务 dict（用于加载上游真理）
    """
    agent_type = _normalize_type(agent_type)

    parts = []

    # 1. Agent 专属 Skill（放最前面，作为角色定义）
    agent_skill = _load(agent_type)
    if agent_skill:
        parts.append(agent_skill)

    # 2. 上游真理（已生成模块的对外接口 —— LLM 提取的完整签名/字段）
    upstream = _load_upstream_truths(agent_type, task)
    if upstream:
        parts.append(upstream)

    # 3. 代码质量 + 三端运行时规范
    quality = _load("quality")
    if quality:
        parts.append("\n## 通用代码质量规范（必须遵守）\n" + quality)

    # 4. 可读性
    readability = _load("readability")
    if readability:
        parts.append("\n## 代码可读性规范（必须遵守）\n" + readability)

    # 5. 前端设计规范（仅 frontend）
    if agent_type == "frontend":
        ui = _load("ui")
        if ui:
            parts.append("\n## UI 设计规范\n" + ui)

    # 6. 工作区
    if workspace:
        parts.insert(1, f"\n## 工作区: {workspace}\n直接按契约创建完整文件，不要读取其他模块的文件（它们正在并行生成中）")

    # 7. 额外指令
    if extra_instructions:
        parts.append("\n" + extra_instructions)

    # 8. 输出铁律（所有 Agent 共用）
    parts.append(_SYSTEM_PROMPT_SUFFIX)

    return "\n".join(parts)


# ── 提示词模板（使用 {placeholder} 标记，format() 替换）──

_USER_PROMPT_TEMPLATE = """一次性创建所有完整文件（含真理文件）。最多3次工具调用。

## ⚠️ 动手前先检索：如有不确定的模式或业务场景，用 search_rag 查历史经验，用 search_code 查参考实现。

## 执行计划（严格遵守顺序）
第1次: search_rag + search_code 并行检索（如无需检索则跳过） → 获取参考
第2次: create_files(files=[{{"path":"...", "content":"完整代码..."}}, ...]) 一次性创建所有文件 → 立即停止

**一次 create_files 传入所有文件数组，不要分多次。每个文件内容完整，不留 TODO。**

## 🛑 真理文件（必须与源码同时在 create_files 中生成）
create_files 的 files 数组中额外包含一个真理 JSON 文件:
  路径: "Memory/truths/engineer/{task_id}.json"  (workspace 内, 后续自动搬到项目根)
  内容: 见下方按 Agent 类型的格式模板。声明你生成的所有导出接口，供下游 Agent 使用。

{truth_template}

## 铁律：create_files 调用成功后立即停止，严禁输出任何总结！检索不是必须的。

## 任务
{task_json}

## 契约
{contract_text}"""

_INTEGRATION_USER_PROMPT_TEMPLATE = """基于元数据完成集成。最多4次工具调用。

## 执行计划（严格遵守顺序）
第1次: read_files() 读取 app.js、src/router/index.js、src/main.js（一次读完）
第2次: edit_batch() 注入后端路由到 app.js + 前端路由到 src/router/index.js
第3次: 补充修改（src/main.js 缺 router、.env 不存在等）
第4次: 强制校验 + 环境收尾 → 停止

## 铁律：工具调用成功后立即停止，严禁输出任何总结！

## 当前任务
{task_json}

## 元数据
{meta_json}"""

_SYSTEM_PROMPT_SUFFIX = """
## ⚠️ 输出铁律（违者视为任务失败）
- 每次响应只能输出: 工具调用参数，或完成消息
- 严禁输出任何总结、描述、解释、表格、Markdown 汇报
- 工具调用成功后直接停止，不要追加任何评论
- 严禁"文件已创建""覆盖情况"等汇报性文字"""


_TRUTH_TEMPLATES = {
    "infra": """```json
{
  "task_id": "{tid}",
  "type": "infra",
  "output_files": [...],
  "exposed": {
    "exposed_to_upper": { /* 上层需要知道的全部接口 */
      "middleware": [{"name": "authenticate", "signature": "(req, res, next) => Promise<void>", "reqInjection": "req.userId=int, req.user={userId,role}"}],
      "utils_exports": [{"file": "utils/response.js", "exports": ["success(res, data, message)", "fail(res, message, code, data)"], "exportStyle": "named"}],
      "config_exports": [{"file": "config/db.js", "exports": ["pool", "query", "beginTransaction", "commit", "rollback", "testConnection"], "exportStyle": "named"}],
      "env_vars_used": ["DB_HOST", "JWT_SECRET"]
    },
    "exposed_to_peers": { /* 同层 import 依赖 */ }
  }
}
```
## 🛑 强制字段（缺一不可，否则下游 Agent 无法正确 require/import 你的导出）
1. middleware 每个条目必须含 "reqInjection": 声明向 req 注入了什么（如 "req.userId=int, req.user={userId,role}"），无注入则写 "reqInjection": "none"
2. utils_exports 和 config_exports 每个条目必须含 "exportStyle": "named"(module.exports.xxx=) / "default"(module.exports=X) / "object"(module.exports={...})""",

    "db": """```json
{
  "task_id": "{tid}",
  "type": "db",
  "output_files": [...],
  "exposed": {
    "exposed_to_upper": {
      "tables": [{"name": "users", "fields": [{"name": "id", "type": "INT", "constraints": "PK AUTO_INCREMENT"}], "indexes": [...], "foreignKeys": [...]}]
    },
    "exposed_to_peers": { "cross_table_refs": ["shops.user_id -> users.id"] }
  }
}
```""",

    "frontend": """```json
{
  "task_id": "{tid}",
  "type": "frontend",
  "output_files": [...],
  "exposed": {
    "exposed_to_upper": {
      "pages": [{"component": "Login", "file": "src/pages/frontend/auth/Login.vue", "route": "/login"}],
      "api_calls": [{"from": "src/api/auth.js", "endpoints": ["POST /auth/login", "GET /auth/me"]}],
      "router": {"names": ["Login", "Home"], "paths": ["/login", "/"]}
    },
    "exposed_to_peers": {
      "stores": [{"file": "src/stores/user.js", "state": ["token", "user"], "actions": ["setToken(token, refreshToken)"]}]
    }
  }
}
```
🛑 api_calls 的 endpoints 中 URL 不带 /api 前缀（Axios baseURL 已设置）
🛑 页面路径必须是真实存在的文件路径""",

    "backend": """```json
{
  "task_id": "{tid}",
  "type": "backend",
  "output_files": [...],
  "exposed": {
    "exposed_to_upper": {
      "routes": [{"file": "routes/order.js", "basePath": "/api/orders", "handlers": [{"method": "POST", "path": "/", "handler": "createOrder", "middleware": ["authenticate"]}]}]
    },
    "exposed_to_peers": {
      "services": [{"file": "services/orderService.js", "functions": [{"name": "createOrder", "params": ["userId", "items"], "returns": "{orderId, orderNo}"}]}]
    }
  }
}
```""",

    "integration": """```json
{
  "task_id": "{tid}",
  "type": "integration",
  "output_files": [...],
  "exposed": {}
}
```""",
}


def _build_truth_template(agent_type: str, task: dict) -> str:
    """生成真理文件格式模板，注入到 user prompt 中。"""
    tid = task.get("taskId") or task.get("id", "unknown")
    template = _TRUTH_TEMPLATES.get(agent_type, _TRUTH_TEMPLATES.get("backend", ""))
    return template.replace("{tid}", tid)


def build_user_prompt(task: dict, relevant_contracts: list = None,
                      agent_type: str = "") -> str:
    """构建 Agent 用户提示词（动态部分 —— 每 task 不同）。"""
    task_json = _serialize(task)
    contract_text = _format_contracts(relevant_contracts or [], agent_type)
    tid = task.get("taskId") or task.get("id", "unknown")
    truth_template = _build_truth_template(agent_type, task)

    return _USER_PROMPT_TEMPLATE.format(
        task_json=task_json,
        contract_text=contract_text,
        task_id=tid,
        truth_template=truth_template,
    )


def build_integration_user_prompt(task: dict, metadata_memory: dict) -> str:
    """集成任务专用用户提示词。"""
    task_json = _serialize(task)
    meta_json = _serialize(metadata_memory)

    return _INTEGRATION_USER_PROMPT_TEMPLATE.format(
        task_json=task_json,
        meta_json=meta_json,
    )


# ── 内部辅助 ──

def _normalize_type(t: str) -> str:
    t = t.lower()
    if t in ("infrastructure",):
        return "infra"
    if t in ("database",):
        return "db"
    return t


def _serialize(obj) -> str:
    import json
    return json.dumps(obj, indent=2, ensure_ascii=False)


def _format_contracts(contracts: list, agent_type: str) -> str:
    """按类型分段格式化契约，各 Agent 只看到自己需要的类型。"""
    if not contracts:
        return "无"

    type_labels = {
        "infra":       [],
        "db":          [("model", "Model"), ("db-api", "DB-API")],
        "backend":     [("api", "API"), ("logic", "Logic"), ("db-api", "DB-API"),
                        ("model", "Model"), ("auth", "Auth")],
        "frontend":    [("api", "API"), ("navigation", "Navigation"),
                        ("model", "Model"), ("auth", "Auth")],
        "integration": [],
    }

    labels = type_labels.get(agent_type, [("api", "API"), ("logic", "Logic"), ("model", "Model")])

    grouped: dict = {}
    for c in contracts:
        ctype = c.get("type", "")
        grouped.setdefault(ctype, []).append(c)

    parts = []
    for ctype, label in labels:
        items = grouped.get(ctype, [])
        if items:
            truncated = _truncate_contracts(items, ctype, max_count=5)
            parts.append(f"### {label}\n{_serialize(truncated)}")
        else:
            parts.append(f"### {label}\n无")

    return "\n".join(parts) if parts else "无"


def _truncate_contracts(contracts: list, ctype: str, max_count: int = 5) -> list:
    """契约列表超 max_count 条时保留核心字段以控制 token。"""
    essential_fields = {
        "model":      ("contractId", "tableName", "fields", "indexes", "constraints"),
        "logic":      ("contractId", "type", "steps", "errorMapping", "transactionBoundary",
                       "concurrencyControl", "inputs", "outputs", "settlementDimension",
                       "requiredInfra"),
        "api":        ("contractId", "basePath", "endpoints", "apiGroup"),
        "db-api":     ("contractId", "sqlTemplate", "params", "returns"),
        "navigation": ("contractId", "fromPage", "toPage", "toPageRoute", "action", "dataTransfer"),
        "auth":       ("contractId", "tokenConfig", "loginEndpoint", "logoutEndpoint", "refreshStrategy"),
    }

    fields = essential_fields.get(ctype)
    if not fields or len(contracts) <= max_count:
        return contracts

    return [{k: c.get(k) for k in fields if k in c} for c in contracts[:max_count]]
