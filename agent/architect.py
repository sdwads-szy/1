# agent/architect.py
"""
架构师 Agent — 先规划后生成流水线（参考 test_architect.py 的验证模式）。

流水线:
  Step 0: plan_tree（自上而下 — 全局规划 + §7 覆盖计数表）
  Step 1: data 层（自下而上第1层 — model + auth，无契约依赖）
  Step 2: interfaces 层（自下而上第2层 — api + db-api + navigation，引用 model 字段）
  Step 3: business 层（自下而上第3层 — scenario + logic，编排 api 调用链）
  Step 4: tasks（自下而上第4层 — 5类任务分配 + 显式依赖链）

核心机制（从 test_architect.py 移植）:
  - §7 计数校验: 每层生成前强制计数，❌则补全
  - 参数提取表: 写 JSON 前先枚举全部应生成项
  - "从 plan_tree 原文复制"铁律: 禁止重新表述
  - max_iter=3~4: 给模型自我纠错空间

每层完成即落盘，下一层读取 plan_tree + 全部前序产出作为上下文。
"""

import asyncio, json, os, sys, re, time
from pathlib import Path
from datetime import datetime

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from picoagents import Agent, OpenAIChatCompletionClient
from picoagents.tools import FunctionTool
from Tools.coding.create_file import create_file
from Tools.coding.edit_lines import edit_batch
from utils.token import wrap_agent_stream

# ── Monkey-patch: 修复 FunctionTool schema 中的 null description ──
# DeepSeek API 不兼容 JSON Schema 的 "description": null，必须过滤掉
_orig_build_params = FunctionTool._build_parameters_schema

def _patched_build_params(self) -> dict:
    schema = _orig_build_params(self)
    for prop in schema.get("properties", {}).values():
        # 删除值为 None 的字段（如 description: null）
        for key in list(prop.keys()):
            if prop[key] is None:
                del prop[key]
    return schema

FunctionTool._build_parameters_schema = _patched_build_params

load_dotenv("./.env.example")
model_client = OpenAIChatCompletionClient(model=os.getenv("OPENAI_MODEL"))

# ── 路径常量 ──
REPORT_DIR = project_root / "work" / "project" / "doc"
TASK_DIR = project_root / "work" / "project" / "task"
SKILL_DIR = project_root / "skill" / "engineer" / "architect"
MEMORY_DIR = project_root / "Memory" / "architect"

AGENT_LOG_DIR = project_root / "Memory" / "agent_logs" / "architect"

TASK_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
AGENT_LOG_DIR.mkdir(parents=True, exist_ok=True)

COMMON_SKILL = SKILL_DIR / "common.md"
STEP_SKILLS = {
    "plan_tree": SKILL_DIR / "scene_tree.md",   # plan_tree 复用 scene_tree.md skill
    "data": SKILL_DIR / "data.md",
    "business": SKILL_DIR / "business.md",
    "interfaces": SKILL_DIR / "interfaces.md",
    "tasks": SKILL_DIR / "tasks.md",
}

# ═══════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════

def load_skill(path: Path) -> str:
    if path.exists():
        return path.read_text("utf-8")
    return ""

def load_step_skill(step_name: str) -> str:
    """只加载步骤专用 skill（common.md 在顶层统一加载）。"""
    return load_skill(STEP_SKILLS.get(step_name, COMMON_SKILL))

def find_latest_report() -> Path:
    reports = sorted(REPORT_DIR.glob("requirement_report_*.md"))
    if not reports:
        raise FileNotFoundError(f"No report in {REPORT_DIR}")
    return max(reports, key=lambda p: p.stat().st_mtime)

def _read_file_content(path: Path) -> str:
    if path.exists():
        return path.read_text("utf-8")
    return "(file not found)"


def _normalize_json_file(file: Path):
    """解析并重新格式化 JSON 文件（indent=2），防止 LLM 输出挤在一行。"""
    if not file.exists():
        return
    try:
        data = json.loads(file.read_text("utf-8"))
        file.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
    except (json.JSONDecodeError, Exception):
        pass  # 非 JSON 文件（如 plan_tree .md）跳过


# ═══════════════════════════════════════
# 运行日志（移植自 engineer.py 模式）
# ═══════════════════════════════════════

def _save_step_log(run_id: str, step_index, step_name: str, raw_output: str):
    """保存 agent 对话实录到 Memory/agent_logs/architect/{run_id}/{idx}_{name}.md。"""
    d = AGENT_LOG_DIR / run_id
    d.mkdir(parents=True, exist_ok=True)
    idx_str = f"{step_index:02d}" if isinstance(step_index, int) else str(step_index)
    fp = d / f"{idx_str}_{step_name}.md"
    fp.write_text(raw_output, "utf-8")



# ═══════════════════════════════════════
# PRD 指标解析
# ═══════════════════════════════════════

def _parse_prd_metrics(prd_text: str) -> dict:
    metrics = {"module_count": 0, "modules": [], "entity_names": [],
               "nfr_dimensions": [], "flow_main_nodes": 0, "vue_page_count": 0}

    in_module_table = False
    for line in prd_text.split("\n"):
        if "| 编号 | 模块 | 定义" in line:
            in_module_table = True; continue
        if in_module_table:
            if not line.strip().startswith("| M"):
                if not line.strip().startswith("|"): in_module_table = False
                continue
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if len(cells) >= 8:
                mid, mname = cells[0], cells[1]
                is_p1 = "一期" in cells[3] if len(cells) > 3 else False
                if is_p1 and mid.startswith("M"):
                    entities = []
                    d_field = cells[7] if len(cells) > 7 else ""
                    for m in re.finditer(r'(\w+)表\s*:', d_field):
                        entities.append(m.group(1))
                    f_count = len([x for x in (cells[5] if len(cells)>5 else "").split(",") if x.strip()])
                    b_count = len([x for x in (cells[6] if len(cells)>6 else "").split(",") if x.strip()])
                    est_pages = (max(2, f_count) if f_count > 0 else 0) + (max(1, b_count) if b_count > 0 else 0)
                    metrics["modules"].append({"id": mid, "name": mname, "entities": entities,
                        "frontend_abilities": f_count, "backend_abilities": b_count, "est_pages": est_pages})
                    metrics["module_count"] += 1
                    metrics["vue_page_count"] += est_pages

    in_entity = False
    for line in prd_text.split("\n"):
        if "实体关系总览" in line: in_entity = True; continue
        if in_entity:
            if line.strip().startswith("###") and "实体" not in line: in_entity = False; continue
            if not line.strip() or line.strip().startswith("---"): continue
            for m in re.finditer(r'\b([a-z][a-z_]+)\s*\(', line):
                name = m.group(1)
                if name not in metrics["entity_names"] and not name.isdigit():
                    metrics["entity_names"].append(name)

    in_nfr = False
    for line in prd_text.split("\n"):
        if "非功能性需求" in line and line.startswith("##"): in_nfr = True; continue
        if in_nfr:
            if line.startswith("##") and "非功能" not in line: in_nfr = False; continue
            nfr_match = re.match(r'\|\s*\*\*(.+?)\*\*\s*\|', line)
            if nfr_match:
                dim = nfr_match.group(1).strip()
                if dim not in ("维度", "月运营成本汇总"): metrics["nfr_dimensions"].append(dim)

    for line in prd_text.split("\n"):
        if "→" in line and not line.strip().startswith("|") and not line.strip().startswith("```"):
            nodes = [n.strip() for n in line.split("→") if len(n.strip()) >= 2]
            if len(nodes) > metrics["flow_main_nodes"]: metrics["flow_main_nodes"] = len(nodes)

    return metrics


# ═══════════════════════════════════════
# 流水线 Step 指令构建（只注入动态内容，静态规则由 skill/*.md 统一管理）
# ═══════════════════════════════════════

def _instructions_step0(prd_metrics: dict, prd_content: str) -> str:
    """plan_tree: 注入 PRD 全文 + 动态指标。skill 文件包含所有执行规则。"""
    skill = load_step_skill("plan_tree")
    # 🆕 读取 UI 文档列表，供 §4 页面导航的 ui_style 列匹配
    ui_dir = project_root / "Memory" / "ui_styles"
    ui_docs_list = "\n".join(f"- {f.stem}" for f in sorted(ui_dir.glob("*.md")) if not f.name.startswith("_")) if ui_dir.exists() else "(无)"

    return f"""## 动态上下文

### PRD 全文
{prd_content}

### 🆕 可用 UI 设计文档（Memory/ui_styles/，§4 ui_style 列只能填此列表中的值）
{ui_docs_list}

### PRD 硬约束

### §7 计数目标
| 维度 | 应有数量 |
|------|:---:|
| 模块(主干) | {prd_metrics['module_count']} |
| 数据实体 | {len(prd_metrics['entity_names'])}: {', '.join(prd_metrics['entity_names'])} |
| 业务链路 | ≥{max(2, prd_metrics['module_count'])} |
| 流程节点(logic候选) | ~{prd_metrics['flow_main_nodes']} |
| API候选 | ≥{sum(1 for m in prd_metrics['modules'] if m['frontend_abilities']>0 or m['backend_abilities']>0)} |
| 页面 | ~{prd_metrics['vue_page_count']} |
| NFR维度 | {len(prd_metrics['nfr_dimensions'])}: {', '.join(prd_metrics['nfr_dimensions'])} |
| model 预估 | ≥{len(prd_metrics['entity_names'])} |
| logic 预估 | ≥{max(3, prd_metrics['flow_main_nodes']//2)} |

### 产物
🛑 唯一产物: __SCENE__

---

{skill}
"""


def _instructions_step1(plan_tree_content: str) -> str:
    """data 层: 注入 plan_tree。skill 文件包含所有执行规则。PRD 信息已全部在 plan_tree 中。"""
    skill = load_step_skill("data")
    return f"""## 动态上下文

### 场景树（全局规划，唯一基准，含 §3 数据实体地图 + §5 鉴权需求）
{plan_tree_content}

### 产物
🛑 唯一产物: __DATA__

---

{skill}
"""


def _instructions_step2(plan_tree_content: str, data_content: str, focus: str = "api") -> str:
    """interfaces 子层: focus='api'|'db-api'|'navigation'。每次只生成一种类型。"""
    skill = load_step_skill("interfaces")
    focus_map = {
        "api": "🛑 本次只生成 api 契约（HTTP 接口）。每个 api 端点含 method/path/request/response/errors。",
        "db-api": "🛑 本次只生成 db-api 契约（数据库操作 CRUD）。列名必须与 data 契约 model.fields 一致。",
        "navigation": "🛑 本次只生成 navigation 契约（页面跳转）。每对相邻页面一个契约。",
    }
    return f"""## 动态上下文

### 场景树（全局规划，唯一基准）
{plan_tree_content}

### 前序产出 — data 契约 (model + auth) 全文（已生成，不可修改）
```json
{data_content}
```

{focus_map.get(focus, "")}

### 产物
🛑 本次只生成 **{focus}** 契约 → 用 `create_file` 一次写入，输出量可控。

---

{skill}
"""


def _instructions_step3(plan_tree_content: str, data_content: str, iface_content: str) -> str:
    """business 层: 注入 plan_tree + data + interfaces。skill 文件包含所有执行规则。"""
    skill = load_step_skill("business")
    return f"""## 动态上下文

### 场景树（全局规划，唯一基准）
{plan_tree_content}

### 前序产出 — data 契约 (model + auth) 全文（已生成，不可修改）
```json
{data_content}
```

### 前序产出 — interfaces 契约 (api + db-api + navigation) 全文（已生成，不可修改）
```json
{iface_content}
```

### PRD 硬约束

### 产物
🛑 唯一产物: __BIZ__

---

{skill}
"""


def _instructions_step4(plan_tree_content: str, all_contracts: list) -> str:
    """tasks: 注入 plan_tree + 全部契约 ID + 计数。skill 文件包含所有执行规则。"""
    skill = load_step_skill("tasks")

    # 按类型分组统计
    contract_stats = {}
    for ct in ["scenario", "logic", "api", "db-api", "navigation", "model", "auth"]:
        items = [c for c in all_contracts if c.get("type") == ct]
        contract_stats[ct] = items

    id_lists = []
    for ct in ["scenario", "logic", "api", "db-api", "navigation", "model", "auth"]:
        items = contract_stats[ct]
        id_lists.append(f"### {ct} ({len(items)} IDs)")
        for c in items:
            cid = c.get("contractId", "?")
            if ct == "model": id_lists.append(f"  {cid} (table={c.get('tableName','?')})")
            elif ct == "api": id_lists.append(f"  {cid} (basePath={c.get('basePath','?')})")
            elif ct == "db-api": id_lists.append(f"  {cid} ({c.get('operation','?')} {c.get('tableName','?')})")
            elif ct == "navigation": id_lists.append(f"  {cid} ({c.get('fromPage','?')}->{c.get('toPage','?')})")
            else: id_lists.append(f"  {cid}")
    id_summary = "\n".join(id_lists)

    model_count = len(contract_stats.get("model", []))
    api_count = len(contract_stats.get("api", []))

    return f"""## 动态上下文

### 场景树（全局规划，唯一基准）
{plan_tree_content}

### 全部契约 ID 清单（🛑 只能使用这些 ID，禁止编造）
{id_summary}

### PRD 硬约束

### 任务数目标
| 类型 | 数量 |
|------|:---:|
| infra | 10 |
| db | {model_count} |
| frontend | {api_count} |
| backend | {api_count} |
| integration | 1 |
| **总计** | **{10 + model_count + api_count * 2 + 1}** |

### 产物
🛑 唯一产物: __TASKS__

---

{skill}
"""




# ═══════════════════════════════════════
# 流水线执行器
# ═══════════════════════════════════════

def _step_needed(file: Path, min_bytes: int = 100) -> bool:
    """中间文件不存在或太小 → 需要执行该步骤。"""
    return not file.exists() or file.stat().st_size < min_bytes


def _interfaces_types_ok(file: Path) -> bool:
    """检查 interfaces 文件是否包含全部 3 种契约类型（api + db-api + navigation）。
    缺少任一种 → 文件不完整，需要重新生成。"""
    if not file.exists():
        return False
    try:
        data = json.loads(file.read_text("utf-8"))
        items = data.get("contracts", data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            return False
        types = {c.get("type") for c in items if isinstance(c, dict)}
        required = {"api", "db-api", "navigation"}
        missing = required - types
        if missing:
            print(f"[architect] [WARN] {file.name} 缺少契约类型: {missing}，需重新生成")
            return False
        return True
    except Exception:
        return False


def _business_types_ok(file: Path) -> bool:
    """检查 business 文件是否包含全部 2 种契约类型（scenario + logic）。
    缺少任一种 → 文件不完整，需要重新生成。"""
    if not file.exists():
        return False
    try:
        data = json.loads(file.read_text("utf-8"))
        items = data.get("contracts", data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            return False
        types = {c.get("type") for c in items if isinstance(c, dict)}
        required = {"scenario", "logic"}
        missing = required - types
        if missing:
            print(f"[architect] [WARN] {file.name} 缺少契约类型: {missing}，需重新生成")
            return False
        return True
    except Exception:
        return False


def _merge_contract_files(*paths: Path) -> list:
    """从每层唯一的 JSON 文件读取契约。格式: {"contracts": [...]} 或 [...]

    🛑 自动展开嵌套包裹: 当 contracts 数组中出现 {"navigations": [...]} 等
       多一层包裹的项时，自动提取内层数组并扁平化。
    """
    all_c = []
    for p in paths:
        if not p.exists():
            print(f"[architect] [WARN] Missing file: {p.name}")
            continue
        try:
            data = json.loads(p.read_text("utf-8"))
        except json.JSONDecodeError as e:
            print(f"[architect] [WARN] Invalid JSON in {p.name}: {e}")
            continue
        except Exception as e:
            print(f"[architect] [WARN] Failed to read {p.name}: {e}")
            continue

        # 格式 1: {"contracts": [...]} 或 {"contracts": {"model": [...], ...}}
        if isinstance(data, dict) and "contracts" in data:
            items = data["contracts"]
        # 格式 2: {"tasks": [...]} — 不是契约文件，跳过
        elif isinstance(data, dict) and "tasks" in data:
            print(f"[architect] [WARN] {p.name} looks like a task file, skipping")
            continue
        # 格式 3: [...] 纯数组
        elif isinstance(data, list):
            items = data
        # 格式 4: 未知格式
        else:
            print(f"[architect] [WARN] Unknown format in {p.name}: {type(data).__name__}")
            continue

        if isinstance(items, list):
            all_c.extend(_flatten_contract_items(items))
        elif isinstance(items, dict):
            # {"model": [...], "api": [...], ...} — 按类型分组
            for v in items.values():
                if isinstance(v, list):
                    all_c.extend(_flatten_contract_items(v))
        else:
            print(f"[architect] [WARN] Unexpected contracts type in {p.name}: {type(items).__name__}")
    return all_c


def _flatten_contract_items(items: list) -> list:
    """展开 contracts 数组中多一层嵌套的项。

    例如 [{"type":"api",...}, {"navigations":[{"type":"navigation",...}]}]
    → [{"type":"api",...}, {"type":"navigation",...}]
    """
    flat = []
    unwrapped = 0
    known_wrappers = {"navigations", "apis", "db_apis", "db-api", "models", "auths", "contracts"}
    for item in items:
        if isinstance(item, dict):
            # 检查是否是多一层包裹: {key: [...]} 其中 key 是已知容器名且 value 是列表
            keys = list(item.keys())
            if len(keys) == 1 and keys[0] in known_wrappers:
                inner = item[keys[0]]
                if isinstance(inner, list):
                    flat.extend(_flatten_contract_items(inner))
                    unwrapped += len(inner)
                    continue
                elif isinstance(inner, dict):
                    flat.append(inner)
                    continue
        flat.append(item)
    if unwrapped > 0:
        print(f"[architect] 自动展开 {unwrapped} 个被 '{list(known_wrappers)}' 嵌套包裹的契约项")
    return flat

def _merge_task_files() -> list:
    """从 _tasks.json 读取任务。格式: {"tasks": [...]} 或 [...]"""
    tf = MEMORY_DIR / "_tasks.json"
    if not tf.exists():
        print(f"[architect] [WARN] Missing file: _tasks.json")
        return []
    try:
        data = json.loads(tf.read_text("utf-8"))
        items = data.get("tasks", data) if isinstance(data, dict) else data
        if isinstance(items, list):
            return items
        elif isinstance(items, dict):
            merged = []
            for v in items.values():
                if isinstance(v, list): merged.extend(v)
            return merged
    except json.JSONDecodeError as e:
        print(f"[architect] [WARN] Invalid JSON in _tasks.json: {e}")
    except Exception as e:
        print(f"[architect] [WARN] Failed to read _tasks.json: {e}")
    return []

async def _run_step(name: str, instructions: str, task_prompt: str,
                    common: str, max_iter: int = 3,
                    tools: list = None, run_id: str = "") -> tuple:
    """执行一个步骤，返回 (ok, raw_output)。raw_output 是 agent 对话实录。"""
    if tools is None:
        tools = [create_file]
    agent = Agent(name=name, description=f"Architect {name}",
                  instructions=f"{common}\n\n{instructions}",
                  model_client=model_client,
                  tools=tools, max_iterations=max_iter)

    log_dir = AGENT_LOG_DIR / run_id if run_id else AGENT_LOG_DIR
    save_filename = name  # plan_tree / data / interfaces / business / tasks

    collected = []
    try:
        async for event in wrap_agent_stream(
            agent, task_prompt, "architect",
            model=os.getenv("OPENAI_MODEL", "unknown"),
            task_id=name,
            save_dir=str(log_dir), save_filename=f"{save_filename}_token",
        ):
            collected.append(str(event))
        return True, "\n".join(collected)
    except Exception as e:
        print(f"[architect] [{name}] Error: {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()
        return False, "\n".join(collected) + f"\n\n[ERROR] {type(e).__name__}: {e}"


# ═══════════════════════════════════════
# 主入口
# ═══════════════════════════════════════

async def run_architect_agent(report_path: str = None) -> dict:
    from utils.token_tracker import record_stage
    record_stage("架构任务生成", phase="start")
    if report_path:
        report_path = Path(report_path)
        if not report_path.exists():
            return {"success": False, "error": f"Report not found: {report_path}"}
    else:
        report_path = find_latest_report()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    task_filepath = TASK_DIR / f"task_{timestamp}.json"

    prd_content = report_path.read_text("utf-8")
    prd_metrics = _parse_prd_metrics(prd_content)

    print(f"[architect] Report: {report_path.name}")
    print(f"[architect] Modules={prd_metrics['module_count']}, Entities={len(prd_metrics['entity_names'])}")

    # ── 运行日志初始化 ──
    run_id = timestamp
    pipeline_start = time.time()

    # 系统提示词只加载一次
    common_skill = load_skill(COMMON_SKILL)

    scene_file = TASK_DIR / "_scene_tree.md"      # 保留旧文件名兼容下游
    biz_file = MEMORY_DIR / "_contracts_business.json"
    data_file = MEMORY_DIR / "_contracts_data.json"
    tasks_file = MEMORY_DIR / "_tasks.json"
    plan_file_abs = str(scene_file)
    biz_file_abs, data_file_abs = str(biz_file), str(data_file)
    tasks_file_abs = str(tasks_file)

    # ── Step 0: plan_tree（自上而下全局规划）──
    t0 = time.time()
    step0_ok, step0_raw = True, "(skipped)"
    if _step_needed(scene_file):
        print("[architect] === Step 0/5: Plan Tree (top-down) ===")
        try:
            instructions = _instructions_step0(prd_metrics, prd_content).replace("__SCENE__", plan_file_abs)
            step0_ok, step0_raw = await _run_step("plan_tree", instructions,
                             "Read the PRD and create plan tree with §7 coverage counting.",
                             common_skill, max_iter=4, run_id=run_id)
        except Exception as e:
            print(f"[architect] Step 0 crashed: {e}")
            import traceback; traceback.print_exc()
            step0_ok, step0_raw = False, f"CRASH: {e}\n{traceback.format_exc()}"
        if not scene_file.exists():
            step0_ok = False
    else:
        print("[architect] Step 0/5: Plan Tree (skip, exists)")
    _save_step_log(run_id, 0, "plan_tree", step0_raw)
    if not step0_ok:
        return {"success": False, "error": "Step 0: plan tree not created"}
    plan_tree_content = _read_file_content(scene_file)

    # ── Step 1: data 层（自下而上第1层 — 无契约依赖）──
    t0 = time.time()
    step1_ok, step1_raw = True, "(skipped)"
    if _step_needed(data_file):
        print("[architect] === Step 1/5: Data (model + auth, bottom-up) ===")
        step1_ok, step1_raw = await _run_step("data",
            _instructions_step1(plan_tree_content).replace("__DATA__", data_file_abs),
            "Read plan tree §3+§5, generate model+auth contracts.", common_skill, max_iter=4, run_id=run_id)
    else:
        print("[architect] Step 1/5: Data (skip, exists)")
    _normalize_json_file(data_file)
    data_contracts = _merge_contract_files(data_file)
    _save_step_log(run_id, 1, "data", step1_raw)
    print(f"[architect] Data: {len(data_contracts)} contracts")

    # ── Step 2: interfaces 子层（api/db-api/nav 互相独立 → 并发）──
    t0 = time.time()
    print("[architect] === Step 2/7: Interfaces (api + db-api + nav, concurrent) ===")
    data_content = _read_file_content(data_file)

    iface_api_file = MEMORY_DIR / "_contracts_interfaces_api.json"
    iface_dbapi_file = MEMORY_DIR / "_contracts_interfaces_dbapi.json"
    iface_nav_file = MEMORY_DIR / "_contracts_interfaces_nav.json"

    async def _run_iface_sub(name, focus, out_file):
        if _step_needed(out_file):
            instructions = _instructions_step2(plan_tree_content, data_content, focus=focus)
            instructions += f"\n\n🛑 唯一产物: {out_file}"
            return await _run_step(name, instructions,
                f"Generate {focus} contracts only.", common_skill, max_iter=1, run_id=run_id,
                tools=[create_file])
        return True, "(skipped)"

    (step2a_ok, step2a_raw), (step2b_ok, step2b_raw), (step2c_ok, step2c_raw) = await asyncio.gather(
        _run_iface_sub("interfaces_api", "api", iface_api_file),
        _run_iface_sub("interfaces_dbapi", "db-api", iface_dbapi_file),
        _run_iface_sub("interfaces_nav", "navigation", iface_nav_file),
    )

    for f, name in [(iface_api_file, "interfaces_api"), (iface_dbapi_file, "interfaces_dbapi"), (iface_nav_file, "interfaces_nav")]:
        _normalize_json_file(f)

    _save_step_log(run_id, "2a", "interfaces_api", step2a_raw)
    _save_step_log(run_id, "2b", "interfaces_dbapi", step2b_raw)
    _save_step_log(run_id, "2c", "interfaces_nav", step2c_raw)

    # ── 合并接口层 3 个文件 ──
    iface_files = sorted(MEMORY_DIR.glob("_contracts_interfaces*.json"))
    iface_contracts = _merge_contract_files(*iface_files)
    iface_types = {}
    for c in iface_contracts:
        iface_types.setdefault(c.get("type", "unknown"), 0)
        iface_types[c.get("type", "unknown")] += 1
    print(f"[architect] Interfaces: {len(iface_contracts)} contracts (api={iface_types.get('api',0)}, db-api={iface_types.get('db-api',0)}, navigation={iface_types.get('navigation',0)}) from {len(iface_files)} files")

    # ── Step 3: business 层（自下而上第3层 — 依赖 data + interfaces）──
    t0 = time.time()
    step3_ok, step3_raw = True, "(skipped)"
    if _step_needed(biz_file) or not _business_types_ok(biz_file):
        print("[architect] === Step 3/7: Business (scenario + logic, bottom-up) ===")
        data_content = _read_file_content(data_file)
        iface_content = json.dumps(iface_contracts, indent=2, ensure_ascii=False)
        step3_ok, step3_raw = await _run_step("business",
            _instructions_step3(plan_tree_content, data_content, iface_content).replace("__BIZ__", biz_file_abs),
            "Read plan_tree + data + interfaces, generate scenario+logic.", common_skill, max_iter=2, run_id=run_id,
            tools=[create_file, edit_batch])
    else:
        print("[architect] Step 3/7: Business (skip, exists)")
    _normalize_json_file(biz_file)
    biz_contracts = _merge_contract_files(biz_file)
    biz_types = {}
    for c in biz_contracts:
        biz_types.setdefault(c.get("type", "unknown"), 0)
        biz_types[c.get("type", "unknown")] += 1
    _save_step_log(run_id, 3, "business", step3_raw)
    print(f"[architect] Business: {len(biz_contracts)} contracts (scenario={biz_types.get('scenario',0)}, logic={biz_types.get('logic',0)})")

    # ── 合并所有契约（Step 4 和 Step 5 共用，只算一次）──
    all_contracts = data_contracts + iface_contracts + biz_contracts

    # ── Step 4: tasks（自下而上第4层 — 依赖全部契约）──
    t0 = time.time()
    step4_ok, step4_raw = True, "(skipped)"
    if _step_needed(tasks_file):
        print("[architect] === Step 4/5: Task Assignment ===")
        step4_ok, step4_raw = await _run_step("tasks",
            _instructions_step4(plan_tree_content, all_contracts).replace("__TASKS__", tasks_file_abs),
            "Read all contract IDs, assign 5 task types.", common_skill, max_iter=2, run_id=run_id,
            tools=[create_file, edit_batch])
    else:
        print("[architect] Step 4/5: Task Assignment (skip, exists)")
    _normalize_json_file(tasks_file)
    tasks = _merge_task_files()
    _save_step_log(run_id, 4, "tasks", step4_raw)
    print(f"[architect] Tasks: {len(tasks)}")

    # ════ Step 5: 合并 → 校验 → 输出 task_<ts>.json ════
    print("[architect] === Step 5/5: Merge & Validate ===")

    # ── 按类型分组 ──
    contracts_by_type = {}
    for c in all_contracts:
        ct = c.get("type", "unknown")
        contracts_by_type.setdefault(ct, []).append(c)

    # ── 🛑 防御性校验：检查各类型契约数量是否达标 ──
    model_count = len(contracts_by_type.get("model", []))
    api_count = len(contracts_by_type.get("api", []))
    dbapi_count = len(contracts_by_type.get("db-api", []))
    nav_count = len(contracts_by_type.get("navigation", []))
    scenario_count = len(contracts_by_type.get("scenario", []))
    logic_count = len(contracts_by_type.get("logic", []))
    entity_count = len(prd_metrics['entity_names'])
    expected_min_tasks = 10 + model_count + api_count * 2 + 1  # infra + db + frontend + backend + integ
    task_count = len(tasks)

    # ── 先输出按类型分布的明细（方便排查）──
    print(f"[architect] Contract types: model={model_count}, api={api_count}, db-api={dbapi_count}, navigation={nav_count}, scenario={scenario_count}, logic={logic_count}")

    validation_warnings = []
    if model_count < entity_count:
        validation_warnings.append(f"model 契约不足: {model_count} < {entity_count} (plan_tree 实体数)")
    if api_count == 0:
        validation_warnings.append("interfaces 层 api 契约缺失: api=0")
    if dbapi_count == 0:
        validation_warnings.append("interfaces 层 db-api 契约缺失: db-api=0")
    if nav_count == 0:
        validation_warnings.append("interfaces 层 navigation 契约缺失: navigation=0")
    if api_count < sum(1 for m in prd_metrics['modules'] if m['frontend_abilities'] > 0 or m['backend_abilities'] > 0):
        validation_warnings.append(f"api 契约可能不足: {api_count}")
    if scenario_count == 0:
        validation_warnings.append("business 层 scenario 契约缺失: scenario=0")
    if logic_count == 0:
        validation_warnings.append("business 层 logic 契约缺失: logic=0")
    if task_count < expected_min_tasks:
        validation_warnings.append(f"任务数不足: {task_count} < {expected_min_tasks} (预期 infra=10 + db={model_count} + frontend={api_count} + backend={api_count} + integ=1)")

    if validation_warnings:
        print("[architect] ⚠️  合并校验警告:")
        for w in validation_warnings:
            print(f"  ⚠️  {w}")
    else:
        print(f"[architect] ✅ 合并校验通过: {len(all_contracts)} contracts, {task_count} tasks")

    # ── 输出 ──
    output = {"meta": {"generatedAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                       "prdSource": report_path.name,
                       "pipeline": "plan_tree->data->interfaces->business->tasks"},
              "contracts": contracts_by_type, "tasks": tasks}
    task_filepath.write_text(json.dumps(output, indent=2, ensure_ascii=False), "utf-8")

    contract_count = len(all_contracts)
    total_duration = time.time() - pipeline_start
    print(f"[architect] Output: {contract_count} contracts + {task_count} tasks -> {task_filepath.name}")
    print(f"[architect] === Done ({total_duration:.1f}s) ===")

    # 记录 Token 消耗
    try:
        from utils.token_tracker import record_stage
        balance = record_stage("架构任务生成", phase="end", extra={"task_count": task_count, "contract_count": contract_count})
        print(f"[token] 架构任务生成 消耗: {balance.get('cost', '?')} CNY (余额: {balance.get('total', '?')})")
    except Exception as e:
        print(f"[token] 记录失败: {e}")

    return {
        "success": task_count > 0 and contract_count > 0,
        "task_file": str(task_filepath),
        "task_count": task_count, "contract_count": contract_count,
        "prd_metrics": {"modules": prd_metrics["module_count"],
                        "entities": len(prd_metrics["entity_names"]),
                        "nfr_dimensions": len(prd_metrics["nfr_dimensions"])},
    }

async def main():
    result = await run_architect_agent()
    print(f"\nResult: {result.get('task_count',0)} tasks, {result.get('contract_count',0)} contracts")
    if not result.get("success"):
        print(f"Error: {result.get('error', 'unknown')}")

if __name__ == "__main__":
    asyncio.run(main())
