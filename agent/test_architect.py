# agent/test_architect.py
"""
TestArchitect Agent — 分层测试任务生成流水线。

PRD + 场景树 + 业务契约 + 任务骨架 → 测试场景树 → 逐层生成 → 合并输出

Step 0: plan_tree 从上往下想（保证覆盖率），产出完整映射表+依赖链
Step 1-4: 从下往上生成（保证依赖就绪），每步引用前序已生成的 task ID

流水线:
  Step 0: 全量输入 → _test_plan_tree.md（从上往下，覆盖全部）
  Step 1: 静态层 + 鉴权（从下往上，无依赖）
  Step 2: 接口层 api/db_api/navigation（依赖静态层）
  Step 3: 逻辑层 backend_proc/logic/scenario（依赖接口层）
  Step 4: 质量层 nfr（依赖全部）
  Step 5: Python 合并 → test_tasks_<ts>.json
"""

import asyncio, json, os, sys
from pathlib import Path
from datetime import datetime

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from picoagents import Agent, OpenAIChatCompletionClient
from Tools.coding.create_file import create_file
from utils.token import wrap_agent_stream

load_dotenv("./.env.example")
model_client = OpenAIChatCompletionClient(model=os.getenv("OPENAI_MODEL"))

# ── 路径常量 ──
SKILL_DIR = project_root / "skill" / "test" / "architect"
TASK_DIR = project_root / "work" / "project" / "task"
DOC_DIR = project_root / "work" / "project" / "doc"
TEST_DIR = project_root / "work" / "project" / "test"
MEMORY_ARCHITECT = project_root / "Memory" / "architect"
MEMORY_TEST = project_root / "Memory" / "test_architect"
AGENT_LOG_DIR = project_root / "Memory" / "agent_logs" / "test_architect"

SKILL_DIR.mkdir(parents=True, exist_ok=True)
TEST_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_TEST.mkdir(parents=True, exist_ok=True)
AGENT_LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── Skill 映射 ──
COMMON_SKILL = SKILL_DIR / "common.md"
STEP_SKILLS = {
    "plan_tree":    SKILL_DIR / "plan_tree.md",
    "logic":        SKILL_DIR / "logic.md",
    "interface":    SKILL_DIR / "interface.md",
    "static.md":  SKILL_DIR / "static.md",
    "quality":      SKILL_DIR / "quality.md",
}

SCENE_TREE = TASK_DIR / "_scene_tree.md"
BIZ_CONTRACTS = MEMORY_ARCHITECT / "_contracts_business.json"
DATA_CONTRACTS = MEMORY_ARCHITECT / "_contracts_data.json"  # model 契约含 seedData


# ═══════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════

def load_skill(path: Path) -> str:
    if path.exists():
        return path.read_text("utf-8")
    return ""

def load_step_skill(step_name: str) -> str:
    return load_skill(STEP_SKILLS.get(step_name, COMMON_SKILL))

def find_latest_task() -> Path:
    files = sorted(TASK_DIR.glob("task_*.json"))
    if not files:
        raise FileNotFoundError(f"No task files in {TASK_DIR}")
    return max(files, key=lambda p: p.stat().st_mtime)

def find_latest_prd() -> Path:
    files = sorted(DOC_DIR.glob("requirement_report_*.md"))
    if not files:
        raise FileNotFoundError(f"No PRD files in {DOC_DIR}")
    return max(files, key=lambda p: p.stat().st_mtime)

def _read_file_content(path: Path) -> str:
    if path.exists():
        return path.read_text("utf-8")
    return "(file not found)"

def _step_needed(file: Path, min_bytes: int = 100) -> bool:
    return not file.exists() or file.stat().st_size < min_bytes


def _list_ui_styles() -> str:
    """列出 Memory/ui_styles/ 下所有可用 UI 文档（不含 _global/_components）。"""
    ui_dir = project_root / "Memory" / "ui_styles"
    if not ui_dir.exists():
        return "(目录不存在)"
    files = sorted(f.stem for f in ui_dir.glob("*.md") if not f.name.startswith("_"))
    return "\n".join(f"- {name}" for name in files) if files else "(无)"

def _extract_task_skeletons(task_content: str) -> str:
    """从 task JSON 提取任务骨架（仅 taskId/type/dependencies/outputFiles/usesContracts）。"""
    try:
        data = json.loads(task_content) if isinstance(task_content, str) else task_content
        tasks = data.get("tasks", [])
        skeletons = []
        for t in tasks:
            skeletons.append({
                "taskId": t.get("taskId", ""),
                "type": t.get("type", ""),
                "dependencies": t.get("dependencies", []),
                "outputFiles": t.get("outputFiles") or t.get("files") or [],
                "usesContracts": t.get("usesContracts") or [],
            })
        return json.dumps(skeletons, indent=2, ensure_ascii=False)
    except Exception:
        return task_content


# ═══════════════════════════════════════
# Agent 执行器
# ═══════════════════════════════════════

async def _run_step(name: str, instructions: str, task_prompt: str,
                    common: str, max_iter: int = 3, tools: list = None,
                    run_id: str = "") -> bool:
    if tools is None:
        tools = [create_file]
    agent = Agent(name=name, description=f"TestArchitect {name}",
                  instructions=f"{common}\n\n{instructions}",
                  model_client=model_client,
                  tools=tools, max_iterations=max_iter)

    log_dir = AGENT_LOG_DIR / run_id if run_id else AGENT_LOG_DIR
    save_filename = name

    try:
        async for _ in wrap_agent_stream(
            agent, task_prompt, "test_architect",
            model=os.getenv("OPENAI_MODEL", "unknown"),
            task_id=name,
            save_dir=str(log_dir), save_filename=f"{save_filename}_token",
        ):
            pass
        return True
    except Exception as e:
        print(f"[test_architect] [{name}] Error: {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()
        return False


# ═══════════════════════════════════════
# 主入口
# ═══════════════════════════════════════

async def run_test_architect(task_path: str = None, prd_path: str = None) -> dict:
    from utils.token_tracker import record_stage
    record_stage("测试任务生成", phase="start")
    if task_path:
        task_path = Path(task_path)
    else:
        task_path = find_latest_task()
    if prd_path:
        prd_path = Path(prd_path)
    else:
        prd_path = find_latest_prd()

    if not task_path.exists():
        return {"success": False, "error": f"Task not found: {task_path}"}
    if not prd_path.exists():
        return {"success": False, "error": f"PRD not found: {prd_path}"}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = TEST_DIR / f"test_tasks_{timestamp}.json"

    # 预加载所有输入
    task_content = task_path.read_text("utf-8")
    prd_content = prd_path.read_text("utf-8")
    scene_content = _read_file_content(SCENE_TREE)
    biz_content = _read_file_content(BIZ_CONTRACTS)
    task_skeletons = _extract_task_skeletons(task_content)

    # 通用 skill 只加载一次
    common_skill = load_skill(COMMON_SKILL)

    print(f"[test_architect] Task: {task_path.name}")
    print(f"[test_architect] PRD: {prd_path.name}")

    # ── Step 0: 测试场景树 ──
    plan_tree_file = TEST_DIR / "_test_plan_tree.md"
    plan_tree_file_abs = str(plan_tree_file)

    if _step_needed(plan_tree_file):
        print("[test_architect] === Step 0/5: Test Plan Tree ===")
        plan_skill = load_step_skill("plan_tree")
        instructions = f"""{plan_skill}

## 输入文件内容

### 1. PRD 需求报告
{prd_content}

### 2. 场景树
{scene_content}

### 3. 业务契约 (scenario + logic)
```json
{biz_content}
```

### 4. 任务骨架 (taskId/type/dependencies/outputFiles/usesContracts)
```json
{task_skeletons}
```

### 5. 🆕 可用 UI 设计文档（Memory/ui_styles/，§2 静态层 frontend 行的 ui_style 只能填此列表中的值，不存在就填 `?`）
{_list_ui_styles()}

## 任务
一次性消化全部输入，生成 `_test_plan_tree.md`。
🛑 唯一产物: {plan_tree_file_abs}
🛑 使用 create_file 工具写入。
"""
        ok = await _run_step("plan_tree", instructions,
                             "Read all inputs and create _test_plan_tree.md.",
                             common_skill, max_iter=4, run_id=timestamp)
        if not ok or not plan_tree_file.exists():
            return {"success": False, "error": "Step 0: plan tree not created"}
    else:
        print("[test_architect] Step 0/5: Test Plan Tree (skip, exists)")

    plan_tree_content = _read_file_content(plan_tree_file)

    # ── Step 1: 静态层（从下往上，无依赖）──
    # 🛑 只生成静态层（infra/db/frontend/peer_deps/integ）。auth 由 Step 2a 接口层单独生成。
    static_file = MEMORY_TEST / "_test_static.md.json"
    static_file_abs = str(static_file)

    if _step_needed(static_file):
        print("[test_architect] === Step 1/5: Static ===")
        step_skill = load_step_skill("static.md")
        instructions = f"""{step_skill}

## 测试场景树（唯一基准）
{plan_tree_content}

## model 契约 (含 seedData — db 任务的 checkPoints 必须引用其中的具体种子数据)
```json
{_read_file_content(DATA_CONTRACTS)}
```

## 任务
对照测试场景树 §2「静态层」映射表，逐条目生成完整 test task JSON。
🛑 唯一产物: {static_file_abs}
🛑 只生成 layer=infra/db/frontend/peer_deps/integ 的任务。不要生成 auth（鉴权层由接口层 Step 2a 单独处理）。
🛑 静态层无 testScenarios，用 checkPoints 数组代替
🛑 同层依赖（FK链/配置链）直接写在 dependencies 中（plan_tree 的依赖链已给出 task ID）
🛑 db 任务的 checkPoints 必须引用 model 契约中 seedData.purpose 和 seedData.rows 的具体数据
🛑 使用 create_file 工具写入。
"""
        await _run_step("static.md", instructions,
                        "Read the plan tree and generate static test tasks (no auth).",
                        common_skill, max_iter=4, run_id=timestamp)
    else:
        print("[test_architect] Step 1/5: Static (skip, exists)")

    static_content = _read_file_content(static_file)

    # ── Step 2a: auth 层（接口层第1个子层，无同层依赖）──
    iface_auth_file = MEMORY_TEST / "_test_interface_auth.json"
    iface_auth_abs = str(iface_auth_file)

    if _step_needed(iface_auth_file):
        print("[test_architect] === Step 2a/6: Interface — auth ===")
        step_skill = load_step_skill("interface")
        instructions = f"""{step_skill}

## 测试场景树（唯一基准）
{plan_tree_content}

## 前序产出 — 静态层 test tasks（已生成，不可修改）
```json
{static_content}
```

## 任务
🛑 本次只生成 **auth 层**（JWT 鉴权）test tasks。不要生成 api/db_api/navigation。
🛑 对照测试场景树 §2「接口层」映射表中 layer=auth 的条目生成。
🛑 唯一产物: {iface_auth_abs}
🛑 使用 create_file 工具写入。
"""
        await _run_step("interface_auth", instructions,
                        "Generate auth test tasks only.", common_skill, max_iter=1, run_id=timestamp)
    else:
        print("[test_architect] Step 2a/6: Interface auth (skip, exists)")

    auth_content = _read_file_content(iface_auth_file)

    # ── Step 2b: db_api（接口层第2个子层，依赖 auth → 先行）──
    iface_dbapi_file = MEMORY_TEST / "_test_interface_dbapi.json"
    iface_dbapi_abs = str(iface_dbapi_file)

    if _step_needed(iface_dbapi_file):
        print("[test_architect] === Step 2b/6: Interface — db_api ===")
        step_skill = load_step_skill("interface")
        instructions = f"""{step_skill}

## 测试场景树（唯一基准）
{plan_tree_content}

## 前序产出 — 静态层 + auth 层 test tasks（已生成，不可修改）
```json
{static_content}
```
```json
{auth_content}
```

## 任务
🛑 本次只生成 **db_api** test tasks。不要生成 api/navigation。
🛑 对照测试场景树 §2「接口层」映射表中 layer=db_api 的条目生成。
🛑 唯一产物: {iface_dbapi_abs}
🛑 使用 create_file 工具写入。
"""
        await _run_step("interface_dbapi", instructions,
                        "Generate db_api test tasks only.", common_skill, max_iter=1, run_id=timestamp)
    else:
        print("[test_architect] Step 2b/6: Interface db_api (skip, exists)")

    dbapi_content = _read_file_content(iface_dbapi_file)

    # ── Step 2c: api + navigation（接口层第3步子层，依赖 db_api → 并发）──
    iface_api_file = MEMORY_TEST / "_test_interface_api.json"
    iface_nav_file = MEMORY_TEST / "_test_interface_nav.json"

    async def _run_iface_sub(name, focus, out_file, out_abs):
        if _step_needed(out_file):
            step_skill = load_step_skill("interface")
            instructions = f"""{step_skill}

## 测试场景树（唯一基准）
{plan_tree_content}

## 前序产出 — 静态层 + auth + db_api 层 test tasks（已生成，不可修改）
```json
{static_content}
```
```json
{auth_content}
```
```json
{dbapi_content}
```

## 任务
🛑 本次只生成 **{focus}** test tasks。不要生成其他接口层类型。
🛑 对照测试场景树 §2「接口层」映射表中 layer={focus} 的条目生成。
🛑 api 任务 dependencies 纵向引用 db_api + 静态层的 task id。
🛑 唯一产物: {out_abs}
🛑 使用 create_file 工具写入。
"""
            return await _run_step(f"interface_{focus}", instructions,
                f"Generate {focus} test tasks only.", common_skill, max_iter=1, run_id=timestamp,
                tools=[create_file])
        return True  # skipped, _run_step returns bool not tuple

    step2c_ok, step2d_ok = await asyncio.gather(
        _run_iface_sub("interface_api", "api", iface_api_file, str(iface_api_file)),
        _run_iface_sub("interface_nav", "navigation", iface_nav_file, str(iface_nav_file)),
    )

    # ── 合并接口层 4 个文件供 Step 3 使用 ──
    iface_tasks = []
    for f in [iface_auth_file, iface_api_file, iface_dbapi_file, iface_nav_file]:
        c = _read_file_content(f)
        if c:
            try:
                arr = json.loads(c)
                if isinstance(arr, list):
                    iface_tasks.extend(arr)
            except (json.JSONDecodeError, TypeError):
                pass
    iface_content = json.dumps(iface_tasks, indent=2, ensure_ascii=False) if iface_tasks else "[]"

    # ── Step 3: 逻辑层（依赖接口层）──
    logic_file = MEMORY_TEST / "_test_logic.json"
    logic_file_abs = str(logic_file)

    if _step_needed(logic_file):
        print("[test_architect] === Step 3/4: Logic (backend_proc + logic + scenario) ===")
        step_skill = load_step_skill("logic")
        instructions = f"""{step_skill}

## 测试场景树（唯一基准）
{plan_tree_content}

## 前序产出 — 静态层+鉴权 test tasks（已生成，不可修改）
```json
{static_content}
```

## 前序产出 — 接口层 test tasks（已生成，不可修改）
```json
{iface_content}
```

## 任务
对照测试场景树 §2「逻辑层」映射表，逐条目生成完整 test task JSON。
🛑 唯一产物: {logic_file_abs}
🛑 backend_proc vs logic 按事务边界判定（1个事务 vs ≥2个事务/补偿）
🛑 scenario 无 sourceTask，targetFiles = 所有依赖 task 的 targetFiles 并集
🛑 dependencies 纵向引用接口层的 task id，横向引用业务流程前驱
🛑 使用 create_file 工具写入。
"""
        await _run_step("logic", instructions,
                        "Read the plan tree + static + interface output and generate logic test tasks.",
                        common_skill, max_iter=4, run_id=timestamp)
    else:
        print("[test_architect] Step 3/4: Logic (skip, exists)")

    logic_content = _read_file_content(logic_file)

    # ── Step 4: 质量层（依赖全部前序）──
    quality_file = MEMORY_TEST / "_test_quality.json"
    quality_file_abs = str(quality_file)

    if _step_needed(quality_file):
        print("[test_architect] === Step 4/4: Quality (nfr) ===")
        step_skill = load_step_skill("quality")
        instructions = f"""{step_skill}

## 测试场景树（唯一基准）
{plan_tree_content}

## 前序产出 — 静态+鉴权 test tasks
```json
{static_content}
```

## 前序产出 — 接口层 test tasks
```json
{iface_content}
```

## 前序产出 — 逻辑层 test tasks
```json
{logic_content}
```

## 任务
对照测试场景树 §2「质量层」映射表，逐条目生成完整 test task JSON。
🛑 唯一产物: {quality_file_abs}
🛑 nfr 无 sourceTask（来自 PRD NFR 维度）
🛑 nfr 的 dependencies 引用全部前序层已生成的 task id
🛑 使用 create_file 工具写入。
"""
        await _run_step("quality", instructions,
                        "Read the plan tree + all prev layers and generate quality test tasks.",
                        common_skill, max_iter=3, run_id=timestamp)
    else:
        print("[test_architect] Step 4/4: Quality (skip, exists)")

    # ════ Step 5: Python 合并 → test_tasks_<ts>.json ════
    print("[test_architect] === Merge (Step 5) ===")

    # 🛑 硬编码修复层占位任务（调度器自动最先执行，读取 .meta/failed_tasks.json 重跑失败工程师任务）
    repair_task = {
        "id": "t_repair_failed",
        "layer": "repair",
        "testType": "static",
        "sourceTask": None,
        "targetFiles": [],
        "dependencies": [],
        "testFramework": None,
        "description": "修复工程师阶段生成失败的文件（读取 .meta/failed_tasks.json 重跑对应 agent）",
        "note": "硬编码占位任务，由调度器 _handle_repair_task 处理，无需 checkPoints",
        "checkPoints": [],
    }
    all_test_tasks = [repair_task]
    seen_ids = {"t_repair_failed"}  # 去重：防止 auth 残留导致重复

    for f in [logic_file, iface_auth_file, iface_api_file, iface_dbapi_file, iface_nav_file, static_file, quality_file]:
        if f.exists():
            try:
                data = json.loads(f.read_text("utf-8"))
                # 兼容三种格式: 纯数组 [{...}] / {"testTasks": [...]} / {"tasks": [...]}
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    items = data.get("testTasks") or data.get("tasks") or []
                else:
                    items = []
                if isinstance(items, list):
                    deduped = []
                    dup_count = 0
                    for item in items:
                        tid = item.get("id", "") if isinstance(item, dict) else ""
                        if tid and tid in seen_ids:
                            dup_count += 1
                            continue
                        if tid:
                            seen_ids.add(tid)
                        deduped.append(item)
                    all_test_tasks.extend(deduped)
                    dup_info = f" ({dup_count} dup skipped)" if dup_count > 0 else ""
                    print(f"[test_architect]   {f.name}: {len(deduped)} tasks{dup_info}")
            except json.JSONDecodeError:
                print(f"[test_architect] [WARN] Invalid JSON: {f.name}")

    # 输出
    output = {
        "meta": {
            "generatedAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "prdSource": prd_path.name,
            "taskSource": task_path.name,
            "pipeline": "plan_tree->static.md->interface->logic->quality",
        },
        "summary": {
            "total": len(all_test_tasks),
        },
        "testTasks": all_test_tasks,
    }
    output_file.write_text(json.dumps(output, indent=2, ensure_ascii=False), "utf-8")

    task_count = len(all_test_tasks)
    print(f"[test_architect] === Done: {task_count} test tasks ===")

    # 记录 Token 消耗
    try:
        balance = record_stage("测试任务生成", phase="end", extra={"task_count": task_count})
        print(f"[token] 测试任务生成 消耗: {balance.get('cost', '?')} CNY (余额: {balance.get('total', '?')})")
    except Exception as e:
        print(f"[token] 记录失败: {e}")

    return {
        "success": task_count > 0,
        "output": str(output_file),
        "task_count": task_count,
    }


# ═══════════════════════════════════════
# CLI
# ═══════════════════════════════════════

async def main():
    result = await run_test_architect()
    print(f"\nResult: {result.get('task_count', 0)} test tasks")
    if not result.get("success"):
        print(f"Error: {result.get('error', 'unknown')}")


if __name__ == "__main__":
    asyncio.run(main())
