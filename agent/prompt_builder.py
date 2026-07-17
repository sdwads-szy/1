# agent/prompt_builder.py
"""
统一提示词组装器 —— 所有 5 类 Agent 共用。

固定顺序（保证跨 task 的缓存命中率）:
  1. skill/code/quality.md          — 通用代码质量规范（所有 Agent）
  2. skill/code/readability.md      — 可读性（所有 Agent）
  3. skill/code/workflow.md         — 工具表 + 执行流程 + 死循环防护（所有 Agent，唯一权威来源）
  4. 场景树 (_scene_tree.md)         — 业务上下文
  5. Memory/ui_styles/*.md          — 动态 UI 风格文档（仅 frontend）
  6. skill/engineer/{type}.md       — Agent 专属 skill
  7. 上游真理                         — 依赖任务的对外接口（优先级最低）

真理传递:
  - _load_upstream_truths 是上游真理的**唯一加载点**
  - 按 task.dependencies 过滤，只传直接依赖
  - 下层真理 → exposed_to_upper，同层真理 → exposed_to_peers
"""

# ═══════════════════════════════════════════════════════
# SECTION 1: 导入与路径
# ═══════════════════════════════════════════════════════

import json as _json
import re as _re
from pathlib import Path
from typing import Optional

_PROJECT_ROOT = Path(__file__).parent.parent

_SKILL_PATHS = {
    "quality":      _PROJECT_ROOT / "skill" / "code" / "quality.md",
    "readability":  _PROJECT_ROOT / "skill" / "code" / "readability.md",
    "file_uploads": _PROJECT_ROOT / "skill" / "code" / "file_uploads.md",
    "workflow":     _PROJECT_ROOT / "skill" / "code" / "workflow.md",
    "infra":        _PROJECT_ROOT / "skill" / "engineer" / "code_generation" / "infrastructure.md",
    "db":           _PROJECT_ROOT / "skill" / "engineer" / "code_generation" / "database.md",
    "backend":      _PROJECT_ROOT / "skill" / "engineer" / "code_generation" / "backend.md",
    "frontend":     _PROJECT_ROOT / "skill" / "engineer" / "code_generation" / "frontend.md",
    "integration":  _PROJECT_ROOT / "skill" / "engineer" / "code_generation" / "integrator.md",
}

_SCENE_TREE_PATH = _PROJECT_ROOT / "work" / "project" / "task" / "_scene_tree.md"
_UI_STYLES_DIR = _PROJECT_ROOT / "Memory" / "ui_styles"

_cache: dict = {}


# ═══════════════════════════════════════════════════════
# SECTION 2: 内部工具函数
# ═══════════════════════════════════════════════════════

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


def _build_dir_summary(ws: Path) -> str:
    """生成工作区目录结构摘要（两层深度），替代 list_dir 工具。"""
    lines = ["```"]
    try:
        for item in sorted(ws.iterdir()):
            if item.name.startswith('.') or item.name == 'node_modules':
                continue
            if item.is_dir():
                lines.append(f"{item.name}/")
                try:
                    for sub in sorted(item.iterdir()):
                        if sub.name.startswith('.'):
                            continue
                        prefix = "  ├── " if sub.is_dir() else "  └── "
                        suffix = "/" if sub.is_dir() else ""
                        lines.append(f"{prefix}{sub.name}{suffix}")
                except PermissionError:
                    pass
            else:
                lines.append(f"{item.name}")
    except PermissionError:
        pass
    lines.append("```")
    return "\n".join(lines)


def _normalize_type(t: str) -> str:
    t = t.lower()
    if t in ("infrastructure",):
        return "infra"
    if t in ("database",):
        return "db"
    return t


def _serialize(obj) -> str:
    return _json.dumps(obj, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════════════════
# SECTION 3: 场景树 & UI 风格加载
# ═══════════════════════════════════════════════════════

def _load_scene_tree() -> str:
    """加载场景树全文（架构师 Step 0 产物）。"""
    if _SCENE_TREE_PATH.exists():
        return _SCENE_TREE_PATH.read_text("utf-8")
    return ""


def _load_global_ui_styles() -> str:
    """加载全局 UI 文档（_global.md + _components.md），所有前端 Agent 共享。"""
    if not _UI_STYLES_DIR.exists():
        return ""
    parts = []
    for name in ("_global", "_components"):
        fp = _UI_STYLES_DIR / f"{name}.md"
        if fp.exists():
            try:
                parts.append(f"### {name}\n{fp.read_text('utf-8')}")
            except Exception:
                pass
    if parts:
        return "\n---\n## 🎨 全局 UI 设计规范（Memory/ui_styles/ — 所有页面铁律）\n\n" + "\n\n".join(parts)
    return ""


def _load_ui_style_by_name(name: str) -> str:
    """按名称加载单个 UI 风格文档。"""
    safe = Path(name).name.replace("\\", "/").split("/")[-1]
    fp = _UI_STYLES_DIR / f"{safe}.md"
    if fp.exists():
        try:
            return fp.read_text('utf-8')
        except Exception:
            pass
    return ""


# ═══════════════════════════════════════════════════════
# SECTION 4: 上游真理加载（唯一真理加载点）
# ═══════════════════════════════════════════════════════

def _load_upstream_truths(agent_type: str, task: dict = None) -> str:
    """加载上游 engineer 真理，按直接依赖过滤。

    规则：
    - 只加载 task.dependencies 中声明的任务产生的真理
    - 下层真理 (truth.type != agent_type) → 展示 exposed_to_upper
    - 同层真理 (truth.type == agent_type) → 展示 exposed_to_peers
    - 如果 task 无 dependencies，回退到类型白名单（兼容旧任务）
    """
    truth_dir = _PROJECT_ROOT / "Memory" / "truths" / "engineer"
    if not truth_dir.exists():
        return ""

    dep_ids = set(task.get("dependencies", [])) if task else set()

    if not dep_ids:
        allowed_types = {
            "infra": set(),
            "db": {"infra"},
            "frontend": {"infra", "db"},
            "backend": {"infra", "db", "frontend"},
            "integration": {"infra", "db", "frontend", "backend"},
        }
        allowed = allowed_types.get(agent_type, set())
    else:
        allowed = None

    upper_blocks = []
    peer_blocks = []

    for fp in sorted(truth_dir.glob("*.json")):
        try:
            t = _json.loads(fp.read_text("utf-8"))
        except (_json.JSONDecodeError, OSError):
            continue

        tid = t.get("task_id", fp.stem)
        ttype = t.get("type", "")

        if dep_ids:
            if tid not in dep_ids:
                continue
        elif ttype not in allowed:
            continue

        exposed = t.get("exposed", {})
        if not exposed or not isinstance(exposed, dict):
            continue

        desc = t.get("description", "")
        is_peer = (ttype == agent_type)

        if is_peer:
            data = exposed.get("exposed_to_peers") or exposed.get("services") or exposed
            block = _format_exposed(data)
            api_exports = t.get("metadata", {}).get("api_exports", {})
            if api_exports:
                api_lines = ["\n**🛑 API 导出清单（import 必须从这里取）**"]
                for fname, names in api_exports.items():
                    api_lines.append(f"- `{fname}`: {', '.join(names)}")
                block = (block or "") + "\n".join(api_lines)
            if block:
                peer_blocks.append(f"#### @truth {tid} [{ttype}] — {desc}\n{block}")
        else:
            data = exposed.get("exposed_to_upper", exposed)
            block = _format_exposed(data)
            if block:
                upper_blocks.append(f"#### @truth {tid} [{ttype}] — {desc}\n{block}")

    if not upper_blocks and not peer_blocks:
        return ""

    parts = ["\n## 🛑 上游真理（直接依赖，已通过测试验证，接口不可质疑）",
             "以下接口来自 dependencies 中声明的上游任务。字段名/函数签名/表结构是绝对正确的，",
             "如果出现不匹配，错在本层代码。"]

    if upper_blocks:
        parts.append("\n### ⬆ 上层接口")
        parts.extend(upper_blocks)
    if peer_blocks:
        parts.append("\n### ↔ 同层接口")
        parts.extend(peer_blocks)

    return "\n".join(parts) + "\n"


def _format_exposed(exposed: dict) -> str:
    """完整展示接口细节 — 直接 dump JSON。"""
    return "```json\n" + _json.dumps(exposed, indent=2, ensure_ascii=False) + "\n```"


# ═══════════════════════════════════════════════════════
# SECTION 5: NFR 格式化
# ═══════════════════════════════════════════════════════

def _format_nfr(nfr: dict, agent_type: str = "") -> str:
    """格式化 NFR 字段为 Agent 可直接转译的代码规则。"""
    if not nfr or not isinstance(nfr, dict):
        return ""
    lines = ["\n## 🛑 非功能约束 (NFR — 直接转译为代码)"]

    if nfr.get("concurrency"):
        c = nfr["concurrency"]
        strategy = c.get("strategy", "")
        if strategy == "pessimistic_lock":
            lines.append("- 🛑 事务内SELECT用 FOR UPDATE 行锁（悲观锁）")
        elif strategy == "optimistic_lock":
            lines.append("- 🛑 UPDATE用 WHERE version=? 乐观锁，affectedRows=0→throw CONFLICT(409)，重试3次指数退避")

    if nfr.get("rateLimit"):
        r = nfr["rateLimit"]
        lines.append(f"- 🛑 限流: {r.get('window','1m')}内最多{r.get('max','20')}次，按{r.get('keyBy','ip')}区分")

    if nfr.get("idempotency"):
        i = nfr["idempotency"]
        kf = i.get("keyField", "id")
        st = i.get("strategy", "UNIQUE_CONSTRAINT")
        if st == "INSERT_IGNORE":
            lines.append(f"- 🛑 幂等: 按 {kf} 去重，INSERT 失败(SQL错误) → SELECT 已存在记录返回")
        elif st == "UNIQUE_CONSTRAINT":
            lines.append(f"- 🛑 幂等: 依赖DB唯一约束({kf})兜底，catch ER_DUP_ENTRY 返回已有记录")

    if nfr.get("audit"):
        a = nfr["audit"]
        lines.append(f"- 🛑 审计日志: 记录 action={a.get('logAction','?')}, userId={a.get('logUserId',True)}")

    if nfr.get("sqlInjection"):
        lines.append("- 🛑 SQL使用参数化查询(?)占位符，禁止字符串拼接SQL")

    if nfr.get("password"):
        p = nfr["password"]
        lines.append(f"- 🛑 密码: {p.get('hashAlgo','bcrypt')}(saltRounds={p.get('saltRounds',10)})")

    if nfr.get("performance"):
        perf = nfr["performance"]
        if perf.get("expectIndexUsage"):
            lines.append(f"- 🛑 期望使用索引: {', '.join(perf['expectIndexUsage'])}")
        if perf.get("targetMs"):
            lines.append(f"- 🛑 目标响应时间: <{perf['targetMs']}ms")

    return "\n".join(lines) if len(lines) > 1 else ""


# ═══════════════════════════════════════════════════════
# SECTION 6: 契约格式化
# ═══════════════════════════════════════════════════════

def _format_contracts(contracts: list, agent_type: str) -> str:
    """按类型分段格式化契约，各 Agent 只看到自己需要的类型。"""
    if not contracts:
        return "无"

    type_labels = {
        "infra":       [],
        "db":          [("model", "Model 数据表")],
        "frontend":    [("api", "API 接口"), ("navigation", "Navigation 页面跳转"),
                        ("model", "Model 数据字段"), ("auth", "Auth 认证配置")],
        "backend":     [("api", "API 接口"), ("logic", "Logic 业务逻辑"),
                        ("db-api", "DB-API 数据库操作"), ("model", "Model 数据字段"),
                        ("auth", "Auth 认证配置")],
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

    # 追加 NFR 约束（从第一个有此字段的契约中提取）
    for ctype, label in labels:
        items = grouped.get(ctype, [])
        for item in items:
            if item.get("nfr"):
                nfr_block = _format_nfr(item["nfr"], agent_type)
                if nfr_block:
                    parts.append(nfr_block)
                break

    return "\n".join(parts) if parts else "无"


def _truncate_contracts(contracts: list, ctype: str, max_count: int = 5) -> list:
    """契约列表超 max_count 条时保留核心字段以控制 token。"""
    essential_fields = {
        "scenario":   ("contractId", "description", "chain", "priority", "finalState"),
        "model":      ("contractId", "tableName", "fields", "indexes", "foreignKeys", "seedData"),
        "logic":      ("contractId", "description", "serviceSignature", "input", "output", "process",
                       "errorMapping", "transactionBoundary", "apiMapping", "dbApiMapping",
                       "idempotency", "nfr"),
        "api":        ("contractId", "basePath", "endpoints", "apiGroup",
                       "frontendApiModule", "backendRouteFile", "nfr"),
        "db-api":     ("contractId", "operation", "tableName", "input", "output",
                       "usesTransaction", "implicitConditions", "nfr"),
        "navigation": ("contractId", "fromPageFile", "toPageFile", "toPageRoute",
                       "toPageRouteName", "passBy", "params", "trigger", "targetRead", "auth", "note"),
        "auth":       ("contractId", "tokenConfig", "loginEndpoint", "registerEndpoint",
                       "refreshEndpoint", "errorMapping", "frontendContract",
                       "middlewareContract", "nfr"),
    }

    fields = essential_fields.get(ctype)
    if not fields or len(contracts) <= max_count:
        return contracts

    return [{k: c.get(k) for k in fields if k in c} for c in contracts[:max_count]]


# ═══════════════════════════════════════════════════════
# SECTION 7: 真理模板
# ═══════════════════════════════════════════════════════

def _load_truth_template(agent_type: str) -> str:
    """从 skill 文件加载真理输出格式模板。"""
    skill_path = _SKILL_PATHS.get(agent_type)
    if not skill_path or not skill_path.exists():
        return ""
    content = skill_path.read_text("utf-8")

    idx = content.find("## 🛑 真理输出格式")
    if idx < 0:
        return ""

    after = content[idx:]
    m = _re.search(r'```json\s*([\s\S]*?)```', after)
    if not m:
        return ""

    return "```json\n" + m.group(1).strip() + "\n```"


def _build_truth_template(agent_type: str, task: dict) -> str:
    """生成真理文件格式模板，注入到 user prompt 中。"""
    tid = task.get("taskId") or task.get("id", "unknown")
    template = _load_truth_template(agent_type)
    if template:
        return template.replace("{tid}", tid)
    return f'```json\n{{"task_id": "{tid}", "type": "{agent_type}", "output_files": [...], "exposed": {{...}}, "nfr_verified": {{...}}}}\n```'


# ═══════════════════════════════════════════════════════
# SECTION 8: System Prompt 构建
# ═══════════════════════════════════════════════════════

def build_system_prompt(agent_type: str, workspace: str = "",
                        extra_instructions: str = "", task: dict = None) -> str:
    """构建 Agent 系统提示词（固定顺序，最大化缓存命中）。

    顺序原则: 5 种 Agent 共享的放最前面 → 某类型专属的 → 本任务专属的。
    """
    agent_type = _normalize_type(agent_type)

    # ═══ 第 1 段: 5 种 Agent 完全共享 ═══
    shared = []

    quality = _load("quality")
    if quality:
        shared.append("## 通用代码质量规范\n" + quality)

    readability = _load("readability")
    if readability:
        shared.append("## 代码可读性规范\n" + readability)

    file_uploads = _load("file_uploads")
    if file_uploads:
        shared.append("## 🛑 文件上传与静态资源规范\n" + file_uploads)

    scene = _load_scene_tree()
    if scene:
        shared.append("\n---\n## 🛑 场景树（补充参考 — 契约未覆盖时以此为权威）\n"
                      "契约和任务是你的主要工作参考。场景树用于填补契约中缺失的信息：\n"
                      "- 校验规则、错误提示文案 → 契约通常只有类型，场景树 §2 有完整规则\n"
                      "- 数据来源和去向 → 契约的 request/response 不标注「从哪来/到哪去」\n"
                      "- 交互动作名、按钮文案 → 场景树 §2 `动作` 列\n"
                      "- 基础设施依赖 → 场景树 §2 `基础设施` 列（SMS/Redis/ES/BullMQ）\n"
                      "🛑 契约与场景树冲突时，以场景树为准。\n\n" + scene)

    workflow = _load("workflow")
    if workflow:
        shared.append("\n---\n## 🛑 工具调用与执行流程（skill/code/workflow.md — 唯一权威来源）\n" + workflow)

    # ═══ 第 2 段: 某类型专属 ═══
    typed = []

    if agent_type == "frontend":
        # 全局 UI 文档（_global.md + _components.md）全文注入
        global_ui = _load_global_ui_styles()
        if global_ui:
            typed.append(global_ui)
        # 🆕 任务专属 UI 文档：由架构师在 task.ui_style 中预先分配，直接注入全文
        ui_style_name = (task or {}).get("ui_style", "")
        if ui_style_name:
            ui_doc = _load_ui_style_by_name(ui_style_name)
            if ui_doc:
                typed.append(f"## 🎨 本任务专属 UI 风格文档（已预加载，不需要 read_ui_style）\n\n### {ui_style_name}\n{ui_doc}")

    if workspace:
        typed.append(f"## 工作区: {workspace}\n直接按契约创建完整文件，不要读取其他模块的文件（它们正在并行生成中）")

    proj_tree = _build_dir_summary(_PROJECT_ROOT)
    typed.append(f"## 项目目录结构（已注入，不需要 list_dir）\n{proj_tree}")

    agent_skill = _load(agent_type)
    if agent_skill:
        typed.append("\n---\n" + agent_skill)

    # ═══ 第 3 段: 本任务专属 ═══
    task_parts = []

    upstream = _load_upstream_truths(agent_type, task)
    if upstream:
        task_parts.append(upstream)

    if extra_instructions:
        task_parts.append("\n" + extra_instructions)

    return "\n".join(shared + typed + task_parts)


# ═══════════════════════════════════════════════════════
# SECTION 9: User Prompt 构建
# ═══════════════════════════════════════════════════════

_USER_PROMPT_TEMPLATE = """## 🛑 工具与流程

工具表、使用详解、Step 1-4 执行流程、跳过规则、死循环防护 — 全部在 system prompt 的 **skill/code/workflow.md** 中，此处不重复。

## 真理格式
{truth_template}

## 任务
{task_json}

## 契约
{contract_text}"""

_INTEGRATION_USER_PROMPT_TEMPLATE = """## 🛑 工具调用规则

工具表、edit_batch/create_files 详解、执行流程 Step 1-3、跳过规则、死循环防护 — 全部在 system prompt 的 **skill/engineer/code_generation/integrator.md** 中，此处不重复。

## 当前任务
{task_json}

## 元数据
{meta_json}"""


def build_user_prompt(task: dict, relevant_contracts: list = None,
                      agent_type: str = "") -> str:
    """构建 Agent 用户提示词（动态部分 —— 每 task 不同）。"""
    task_json = _serialize(task)
    contract_text = _format_contracts(relevant_contracts or [], agent_type)
    truth_template = _build_truth_template(agent_type, task)

    return _USER_PROMPT_TEMPLATE.format(
        task_json=task_json,
        contract_text=contract_text,
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
