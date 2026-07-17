# brainAgent/engineer.py
"""
工程调度器 —— 读取 architecture_plan.json，按严格类型分层执行所有任务。

分层规则（由 build_engineer_layers 保证）:
  - 同层内任务类型相同 → system prompt 前缀一致 → 缓存命中
  - 不同类型任务绝不同层 → 避免 prompt 切换
  - 层间按 (拓扑深度, 类型优先级) 排序: infra → db → frontend → backend → integration

真理传递:
  - 上游真理由 prompt_builder._load_upstream_truths 统一注入 system prompt
  - 此处只注入 env_constraints，不重复传递真理
"""

# ═══════════════════════════════════════════════════════
# SECTION 1: 导入
# ═══════════════════════════════════════════════════════

import asyncio
import json
import re
import shutil
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from agent.base_designer import run_backend_task, run_frontend_task, run_infrastructure_task, run_database_task
from agent.integrator import run_integration_task
from utils.dependency_graph import print_layers, _get_tid


# ═══════════════════════════════════════════════════════
# SECTION 2: 常量与路径
# ═══════════════════════════════════════════════════════

TASK_DIR = project_root / "work" / "project" / "task"
PROJECT_WORKSPACE = project_root / "work" / "project"
AGENT_LOG_DIR = project_root / "Memory" / "agent_logs" / "engineer"
TRUTH_DIR_ENGINEER = project_root / "Memory" / "truths" / "engineer"
ENGINEER_STATE_DIR = project_root / "Memory" / "agent_logs" / "engineer" / "states"

AGENT_LOG_DIR.mkdir(parents=True, exist_ok=True)
TRUTH_DIR_ENGINEER.mkdir(parents=True, exist_ok=True)
ENGINEER_STATE_DIR.mkdir(parents=True, exist_ok=True)

MAX_CONCURRENT_TASKS = 100

# 工程师任务类型别名
_ENGINEER_ALIASES = {"infrastructure": "infra", "database": "db"}

# 执行优先级: infra → db → frontend → backend → integration
ENGINEER_TYPE_ORDER = ["infra", "db", "frontend", "backend", "integration"]
_ENGINEER_TYPE_RANK = {t: i for i, t in enumerate(ENGINEER_TYPE_ORDER)}


# ═══════════════════════════════════════════════════════
# SECTION 3: 任务状态管理
# ═══════════════════════════════════════════════════════

class EngineerTaskState:
    """工程师任务状态 — 持久化到 Memory/agent_logs/engineer/states/{task_id}.json。"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.success = False
        self.output_files: list = []
        self.timestamp: str = ""
        self.error: str = ""

    @property
    def is_done(self) -> bool:
        return self.success

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "success": self.success,
            "output_files": self.output_files,
            "timestamp": self.timestamp,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EngineerTaskState":
        s = cls(d.get("task_id", ""))
        s.success = d.get("success", False)
        s.output_files = d.get("output_files", [])
        s.timestamp = d.get("timestamp", "")
        s.error = d.get("error", "")
        return s


def _load_engineer_state(task_id: str) -> EngineerTaskState:
    f = ENGINEER_STATE_DIR / f"{task_id}.json"
    if f.exists():
        try:
            return EngineerTaskState.from_dict(json.loads(f.read_text("utf-8")))
        except Exception:
            pass
    return EngineerTaskState(task_id)


def _save_engineer_state(state: EngineerTaskState):
    f = ENGINEER_STATE_DIR / f"{state.task_id}.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(state.to_dict(), indent=2, ensure_ascii=False), "utf-8")


def _clear_engineer_state(task_id: str):
    """清除过期的任务状态（文件已丢失但状态标记为成功）。"""
    f = ENGINEER_STATE_DIR / f"{task_id}.json"
    if f.exists():
        try:
            f.unlink()
        except OSError:
            pass


def _all_output_files_exist(task: dict, workspace_path: Path) -> bool:
    """检查任务的所有输出文件是否都存在且非空。"""
    output_files = task.get("outputFiles") or task.get("files") or task.get("path") or []
    if not output_files:
        return False
    for f in output_files:
        fp = workspace_path / f
        if not fp.exists() or fp.stat().st_size == 0:
            return False
    return True


# ═══════════════════════════════════════════════════════
# SECTION 4: 文件加载与契约工具
# ═══════════════════════════════════════════════════════

def find_latest_task_file() -> Path:
    task_files = list(TASK_DIR.glob("task_*.json"))
    if not task_files:
        raise FileNotFoundError(f"未找到任务文件，目录: {TASK_DIR}")
    latest = max(task_files, key=lambda p: p.stat().st_mtime)
    print(f"使用任务文件: {latest}")
    return latest


def load_architecture_plan(file_path: Path) -> tuple:
    """加载 architecture_plan.json，兼容新旧格式。"""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data, []

    tasks = data.get("tasks", [])
    contracts_raw = data.get("contracts", {})

    # 兼容旧格式（contracts 为数组）和新格式（contracts 按类型分组为 dict）
    if isinstance(contracts_raw, dict):
        contracts = []
        for clist in contracts_raw.values():
            if isinstance(clist, list):
                contracts.extend(clist)
    else:
        contracts = contracts_raw

    return tasks, contracts


def filter_contracts_by_uses(contracts: List[Dict], task: Dict) -> List[Dict]:
    """从 task.usesContracts / task.requiredContracts 筛选关联契约。"""
    refs = task.get("usesContracts") or task.get("requiredContracts") or []
    if not refs:
        return []
    ref_set = set(refs)
    return [c for c in contracts if c.get("contractId") in ref_set]


def _validate_contracts(contracts: list) -> None:
    """契约关键字段检查。缺失关键字段时阻断执行。"""
    critical = []
    for c in contracts:
        cid = c.get("contractId", "?")
        ctype = c.get("type", "")
        if ctype == "model" and not c.get("tableName"):
            critical.append(f"{cid}: model 缺 tableName")
        if ctype == "api" and not c.get("basePath"):
            critical.append(f"{cid}: api 缺 basePath")
    if critical:
        print(f"  🛑 {len(critical)} 个关键字段缺失:")
        for m in critical:
            print(f"    - {m}")
        raise ValueError("契约关键字段缺失，请修复 architecture_plan.json 后重试")


# ═══════════════════════════════════════════════════════
# SECTION 5: DAG 分层
# ═══════════════════════════════════════════════════════

def _engineer_type(t: dict) -> str:
    """从 task 提取工程师类型。只做别名归一化，不经过测试系统的 _LAYER_TO_TYPE 映射。"""
    raw = t.get("type", "")
    return _ENGINEER_ALIASES.get(raw, raw)


def build_engineer_layers(tasks: list) -> list:
    """构建工程师任务分层，按类型分组。

    算法:
      1. 拓扑排序计算每个任务的深度
      2. 按 (type_rank, depth) 全局排序
      3. 相邻同类型无内部依赖的任务合并为一层

    返回: [[task_dict, ...], ...]  每层为同类型任务列表
    """
    if not tasks:
        return []

    # ── Step 1: 拓扑深度 ──
    depth: dict = {_get_tid(t): 0 for t in tasks}
    changed = True
    iteration = 0
    max_iterations = len(tasks) * 10
    while changed and iteration < max_iterations:
        changed = False
        iteration += 1
        for t in tasks:
            tid = _get_tid(t)
            deps = t.get("dependencies", [])
            if deps:
                max_dep = max(depth.get(d, 0) for d in deps)
                new_d = max_dep + 1
                if new_d > depth[tid]:
                    depth[tid] = new_d
                    changed = True
    if iteration >= max_iterations:
        cyclic = [tid for tid, d in depth.items() if d >= max_iterations // 2]
        raise ValueError(f"Circular dependency detected among tasks: {cyclic[:10]}")

    # ── Step 2: 按 (type_rank, depth) 排序 ──
    sorted_tasks = sorted(tasks, key=lambda t: (
        _ENGINEER_TYPE_RANK.get(_engineer_type(t), 99),
        depth.get(_get_tid(t), 999),
    ))

    # ── Step 3: 按类型分组，同类型内有内部依赖时再拆 ──
    layers = []
    current_type = None
    current_layer = []

    for t in sorted_tasks:
        ttype = _engineer_type(t)
        tid = _get_tid(t)
        deps = set(t.get("dependencies", []))
        layer_ids = {_get_tid(x) for x in current_layer}

        if ttype != current_type or (deps & layer_ids):
            if current_layer:
                layers.append(current_layer)
            current_type = ttype
            current_layer = [t]
        else:
            current_layer.append(t)

    if current_layer:
        layers.append(current_layer)

    return layers


# ═══════════════════════════════════════════════════════
# SECTION 6: 任务执行
# ═══════════════════════════════════════════════════════

async def execute_task(task: Dict, contracts: List[Dict],
                       agent_type: str, workspace: str,
                       resume: bool = False) -> Dict[str, Any]:
    """执行单个任务。resume=True 时跳过已成功的任务。"""
    tid = _get_tid(task)
    workspace_path = Path(workspace)

    # 统一 path/files → outputFiles
    output_files = task.get("outputFiles") or task.get("files") or task.get("path") or []

    # ── 跳过已成功的任务 ──
    if resume:
        state = _load_engineer_state(tid)
        if state.is_done and _all_output_files_exist(task, workspace_path):
            print(f"  ⏭ [{agent_type}] {tid}: SKIP (already done, {len(output_files)} files)")
            return {
                "task_id": tid, "type": agent_type, "success": True,
                "duration_seconds": 0, "error": None,
                "metadata": {"skipped": True, "reason": "already completed"},
            }
        elif state.is_done:
            print(f"  🔄 [{agent_type}] {tid}: state says done but files missing, re-running")
            _clear_engineer_state(tid)

    print(f"  [{agent_type}] {tid}: {task.get('description', '')[:60]}...")

    # 筛选关联契约 + 构建额外指令
    relevant = filter_contracts_by_uses(contracts, task)
    extra = _build_extra_instructions(task)

    try:
        start = datetime.now()

        if agent_type in ("infra",):
            result = await run_infrastructure_task(task, workspace_root=workspace, extra_instructions=extra)
        elif agent_type in ("db",):
            result = await run_database_task(task, workspace_root=workspace, relevant_contracts=relevant, extra_instructions=extra)
        elif agent_type in ("backend", "backend_proc"):
            result = await run_backend_task(task, workspace_root=workspace, relevant_contracts=relevant, extra_instructions=extra)
        elif agent_type in ("frontend", "frontend_static"):
            result = await run_frontend_task(task, workspace_root=workspace, relevant_contracts=relevant, extra_instructions=extra)
        else:
            raise ValueError(f"未知任务类型: {agent_type}")

        duration = (datetime.now() - start).total_seconds()
        success = result.get("success", False)

        # 前端文件硬校验
        if success and agent_type in ("frontend", "frontend_static"):
            validation_issues = _validate_frontend_output(workspace_path, output_files)
            if validation_issues:
                success = False
                result["error"] = "; ".join(validation_issues[:3])
                print(f"    ⚠️ 前端校验失败: {result['error'][:120]}")

        if success:
            _save_engineer_state(EngineerTaskState.from_dict({
                "task_id": tid, "success": True,
                "output_files": output_files,
                "timestamp": datetime.now().isoformat(),
                "error": "",
            }))

        return {
            "task_id": tid, "type": agent_type,
            "success": success, "duration_seconds": duration,
            "error": result.get("error"), "metadata": result.get("metadata"),
        }
    except Exception as e:
        duration = (datetime.now() - start).total_seconds() if 'start' in dir() else 0
        return {
            "task_id": tid, "type": agent_type,
            "success": False, "duration_seconds": duration,
            "error": str(e)[:300], "metadata": None,
        }


def _build_extra_instructions(task: dict) -> str:
    """构建 Agent 额外指令（env 约束等）。不包含真理——真理由 prompt_builder 统一注入。"""
    extra = ""
    env_constraints = task.get("envConstraints", {})
    if env_constraints:
        extra += "\n## 环境变量约束\n" + "\n".join(
            f"- {k}: {v}" for k, v in env_constraints.items()
        )
    return extra


# ═══════════════════════════════════════════════════════
# SECTION 7: 后校验
# ═══════════════════════════════════════════════════════

def _validate_frontend_output(workspace_path: Path, output_files: list) -> list:
    """前端代码生成后硬校验。返回问题列表，空列表 = 通过。"""
    issues = []
    ws = workspace_path

    esbuild = ws / "node_modules" / "esbuild" / "bin" / "esbuild"
    if not esbuild.exists():
        esbuild = ws / "node_modules" / ".bin" / "esbuild"
    esbuild_cmd = str(esbuild) if esbuild.exists() else "npx"
    esbuild_args = [] if esbuild.exists() else ["esbuild"]

    for tf in output_files:
        fp = ws / tf
        if not fp.exists() or not tf.endswith(".js"):
            continue
        try:
            content = fp.read_text("utf-8", errors="replace")
        except Exception:
            continue

        # 1. 前端 src/ 下禁止 CJS
        if "src/" in tf:
            if "module.exports" in content or "require(" in content:
                issues.append(f"{tf}: CJS 语法 (require/module.exports)，前端必须使用 ESM (import/export)")

        # 2. ESM 语法检查
        if re.search(r'(?:^|\n)\s*(?:import\s+|export\s+)', content):
            cmd = [esbuild_cmd] + esbuild_args + [str(fp), "--format=esm", "--log-level=error",
                   "--outfile=" + str(ws / ".esbuild-tmp.js")]
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                                   cwd=str(ws), encoding="utf-8", errors="replace")
                if r.returncode != 0:
                    err = (r.stderr or "").strip()[:200].replace('\n', ' | ')
                    issues.append(f"{tf}: ESM 语法错误 ({err})")
            except Exception:
                pass

    # 清理临时文件
    tmp = ws / ".esbuild-tmp.js"
    if tmp.exists():
        try:
            tmp.unlink()
        except OSError:
            pass

    return issues


def _verify_all_output_files(tasks: list, workspace_path: Path) -> list:
    """工程师阶段收尾检查: 遍历所有任务，验证每个 outputFiles 在磁盘上存在且非空。"""
    missing_list = []
    for t in tasks:
        tid = _get_tid(t)
        output_files = t.get("outputFiles") or t.get("files") or t.get("path") or []
        missing = []
        for f in output_files:
            fp = workspace_path / f
            if not fp.exists():
                missing.append(f"{f} (不存在)")
            elif fp.stat().st_size == 0:
                missing.append(f"{f} (空文件)")
        if missing:
            missing_list.append({
                "task_id": tid, "type": t.get("type", ""),
                "missing": missing, "outputFiles": output_files,
                "description": t.get("description", "")[:100],
            })
    if missing_list:
        print(f"\n  🛑 文件存在性检查: {len(missing_list)} 个任务有文件缺失")
        for m in missing_list:
            print(f"    {m['task_id']} ({m['type']}): {', '.join(m['missing'])}")
    return missing_list


# ═══════════════════════════════════════════════════════
# SECTION 8: 报告
# ═══════════════════════════════════════════════════════

def generate_report(task_file_path: Path, results: list,
                    layers: list = None, skipped_count: int = 0) -> dict:
    """生成执行摘要。"""
    summary = {
        "total": len(results),
        "success": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"] and not r.get("pruned")),
        "pruned": sum(1 for r in results if r.get("pruned")),
        "skipped": skipped_count,
        "total_duration": sum(r["duration_seconds"] for r in results),
        "layers": len(layers) if layers else 0,
    }

    skip_info = f"  跳过: {skipped_count}" if skipped_count > 0 else ""
    print(f"\n结果: {summary['success']}/{summary['total']} 成功  "
          f"失败: {summary['failed']}  剪枝: {summary['pruned']}{skip_info}  "
          f"耗时: {summary['total_duration']:.1f}s  分层: {summary['layers']}")

    return {
        "task_file": str(task_file_path),
        "timestamp": datetime.now().isoformat(),
        "summary": summary,
        "results": results,
    }


# ═══════════════════════════════════════════════════════
# SECTION 9: 调度主流程
# ═══════════════════════════════════════════════════════

async def run_engineer(task_file_path: Path = None, resume: bool = False):
    """主入口：加载架构计划 → 分层 → 逐层并发执行 → 集成 → 报告。"""
    from utils.token_tracker import record_stage
    record_stage("源代码生成", phase="start")

    if task_file_path is None:
        task_file_path = find_latest_task_file()

    print(f"\n{'='*60}")
    print(f"加载: {task_file_path}")
    if resume:
        print(f"模式: RESUME（跳过已成功任务）")
    tasks, contracts = load_architecture_plan(task_file_path)
    print(f"任务: {len(tasks)}  契约: {len(contracts)}")

    # ── 契约校验 ──
    _validate_contracts(contracts)

    # ── 文件冲突检测 ──
    _report_file_conflicts(tasks)

    # ── 分层 ──
    layers = build_engineer_layers(tasks)
    print(f"\n执行计划: {len(layers)} 层")
    print_layers(layers)

    # ── 分离集成任务 ──
    non_integration_layers, integration_task = _split_integration(layers)

    # ── 清理旧数据 ──
    _clean_workspace(resume)

    # ── 逐层执行 ──
    results, failed_ids, skipped_count = await _run_layers(
        non_integration_layers, contracts, workspace=str(PROJECT_WORKSPACE), resume=resume)

    # ── 集成任务 ──
    if integration_task:
        await _run_integration(integration_task, str(PROJECT_WORKSPACE), results)

    # ── 文件存在性校验 ──
    _verify_and_fix_results(tasks, results)

    # ── 失败任务持久化 ──
    _save_failed_tasks(tasks, results, task_file_path)

    # ── Token 记录 ──
    try:
        succeeded = sum(1 for r in results if r.get("success"))
        balance = record_stage("源代码生成", phase="end",
                               extra={"total_tasks": len(results), "succeeded": succeeded})
        print(f"[token] 源代码生成 消耗: {balance.get('cost', '?')} CNY (余额: {balance.get('total', '?')})")
    except Exception as e:
        print(f"[token] 记录失败: {e}")

    return generate_report(task_file_path, results, layers, skipped_count)


# ── 调度子步骤 ──

def _report_file_conflicts(tasks: list):
    """文件冲突检测: 同类型重叠用文件锁，跨类型重叠允许（不同层顺序执行）。"""
    file_owners = {}
    same_type_conflicts = []
    cross_type_info = []
    for t in tasks:
        tid = _get_tid(t)
        ttype = _engineer_type(t)
        for f in (t.get("outputFiles") or t.get("files") or []):
            if f in file_owners:
                prev_tid, prev_type = file_owners[f]
                if prev_type == ttype:
                    same_type_conflicts.append(
                        f"{f} (同类型: {prev_tid}[{prev_type}] vs {tid}[{ttype}]，文件锁控制)")
                else:
                    cross_type_info.append(
                        f"{f} (跨类型: {prev_tid}[{prev_type}] 创建 → {tid}[{ttype}] 修改)")
            else:
                file_owners[f] = (tid, ttype)
    if same_type_conflicts:
        print(f"  ⚠️ 同类型文件重叠 {len(same_type_conflicts)} 处（文件锁控制）:")
        for c in same_type_conflicts:
            print(f"    - {c}")
    if cross_type_info:
        print(f"  ✅ 跨类型文件传递 {len(cross_type_info)} 处:")
        for c in cross_type_info:
            print(f"    - {c}")


def _split_integration(layers: list) -> tuple:
    """分离集成任务和普通层。"""
    non_integration = []
    integration = None
    for layer in layers:
        if layer and _engineer_type(layer[0]) == "integration":
            integration = layer[0]
        else:
            non_integration.append(layer)
    return non_integration, integration


def _clean_workspace(resume: bool):
    """清理上次残留的元数据。"""
    meta_dir = PROJECT_WORKSPACE / ".meta"
    ws_memory = PROJECT_WORKSPACE / "Memory"
    if ws_memory.exists():
        shutil.rmtree(str(ws_memory), ignore_errors=True)
    if resume:
        old_failed = meta_dir / "failed_tasks.json"
        if old_failed.exists():
            old_failed.unlink()
    else:
        if meta_dir.exists():
            shutil.rmtree(meta_dir)
    meta_dir.mkdir(parents=True)


async def _run_layers(layers: list, contracts: list,
                      workspace: str, resume: bool) -> tuple:
    """逐层并发执行任务，带剪枝。"""
    results = []
    failed_ids = set()
    pruned_ids = set()
    skipped_count = 0

    for i, layer in enumerate(layers):
        agent_type = _engineer_type(layer[0])
        print(f"\n--- Layer {i}: {len(layer)} {agent_type} tasks ---")

        # 剪枝
        runnable = []
        for t in layer:
            tid = _get_tid(t)
            deps = set(t.get("dependencies", []))
            blocking = deps & (failed_ids | pruned_ids)
            if blocking:
                print(f"  ✂ {tid}: PRUNED (root cause: {', '.join(sorted(blocking))})")
                pruned_ids.add(tid)
                results.append({
                    "task_id": tid, "type": agent_type, "success": False,
                    "duration_seconds": 0,
                    "error": f"Pruned — upstream failed/pruned: {', '.join(sorted(blocking))}",
                    "metadata": None, "pruned": True,
                })
            else:
                runnable.append(t)

        if not runnable:
            print(f"  (所有 {len(layer)} 个任务被剪枝)")
            continue

        # 并发执行
        print(f"  执行 {len(runnable)}/{len(layer)} 个任务 ({len(layer) - len(runnable)} 被剪枝)")
        coros = [execute_task(t, contracts, agent_type, workspace, resume=resume) for t in runnable]
        batch_results = await asyncio.gather(*coros, return_exceptions=True)

        for task, res in zip(runnable, batch_results):
            tid = _get_tid(task)
            if isinstance(res, Exception):
                print(f"  💥 {tid}: {res}")
                results.append({"task_id": tid, "type": agent_type, "success": False,
                               "duration_seconds": 0, "error": str(res)[:200], "metadata": None})
                failed_ids.add(tid)
                continue
            results.append(res)
            if res.get("skipped"):
                skipped_count += 1
                status = "⏭"
            elif res["success"]:
                status = "✅"
            else:
                status = "❌"
                failed_ids.add(tid)
            print(f"  {status} {tid} ({res['duration_seconds']:.1f}s)")

    return results, failed_ids, skipped_count


async def _run_integration(integration_task: dict, workspace: str, results: list):
    """执行集成任务。"""
    print(f"\n--- Integration ---")

    # Python 预生成 init-db.js + seed-users.js + 占位图
    from brainAgent.scheduler import _compute_fk_order
    from utils._gen_db_scripts import generate as _gen_db_scripts
    _gen_db_scripts(workspace, json.dumps(_compute_fk_order(PROJECT_WORKSPACE)))
    from utils.placeholder_files import ensure as _ensure_placeholders
    _ensure_placeholders(PROJECT_WORKSPACE)

    start = datetime.now()
    try:
        result = await run_integration_task(integration_task, workspace_root=workspace)
        duration = (datetime.now() - start).total_seconds()
        results.append({
            "task_id": _get_tid(integration_task), "type": "integration",
            "success": result.get("success", False), "duration_seconds": duration,
            "error": result.get("error"), "metadata": None,
        })
        print(f"  {'✅' if result.get('success') else '❌'} integration ({duration:.1f}s)")
    except Exception as e:
        results.append({
            "task_id": _get_tid(integration_task), "type": "integration",
            "success": False, "duration_seconds": (datetime.now() - start).total_seconds(),
            "error": f"{e}\n{traceback.format_exc()}"[:500], "metadata": None,
        })


def _verify_and_fix_results(tasks: list, results: list):
    """文件存在性校验 — 标记成功但文件缺失 → 修正为失败。"""
    missing_files = _verify_all_output_files(tasks, PROJECT_WORKSPACE)
    for mf in missing_files:
        tid = mf["task_id"]
        for r in results:
            if r and r.get("task_id") == tid and r.get("success"):
                r["success"] = False
                r["error"] = f"文件缺失: {', '.join(mf['missing'])}"
                print(f"  ⚠️ {tid}: 标记为成功但以下文件缺失 — {', '.join(mf['missing'])}")
                break


def _save_failed_tasks(tasks: list, results: list, task_file_path: Path):
    """失败 + 剪枝任务持久化到 .meta/failed_tasks.json。"""
    failed_or_pruned = [r for r in results if r and not r.get("success", True)]
    if not failed_or_pruned:
        return

    task_map = {_get_tid(t): t for t in tasks}
    failed_list = []
    pruned_list = []
    for f in failed_or_pruned:
        if not f:
            continue
        tid = f["task_id"]
        orig = task_map.get(tid, {})
        entry = {
            "task_id": tid, "type": f["type"],
            "error": (f.get("error") or "")[:200],
            "description": orig.get("description", ""),
            "outputFiles": orig.get("outputFiles") or orig.get("files") or [],
            "dependencies": orig.get("dependencies", []),
            "usesContracts": orig.get("usesContracts") or orig.get("requiredContracts", []),
        }
        if f.get("pruned"):
            pruned_list.append(entry)
        else:
            failed_list.append(entry)

    failed_file = PROJECT_WORKSPACE / ".meta" / "failed_tasks.json"
    failed_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": str(task_file_path),
        "failed": failed_list,
        "pruned": pruned_list,
        "repair_order": [e["task_id"] for e in failed_list + pruned_list],
    }
    failed_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), "utf-8")

    print(f"\n任务结果: {len(failed_list)} 失败, {len(pruned_list)} 被剪枝 → {failed_file}")
    for f in failed_list:
        print(f"  ❌ {f['task_id']} ({f['type']}): {(f.get('error') or '(无详情)')[:120]}")
    for p in pruned_list:
        print(f"  ✂ {p['task_id']} ({p['type']}): 剪枝")


# ═══════════════════════════════════════════════════════
# SECTION 10: CLI 入口
# ═══════════════════════════════════════════════════════

async def main():
    resume = "--resume" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        task_path = Path(args[0])
        if not task_path.exists():
            print(f"错误: 任务文件不存在 - {task_path}")
            return
        report = await run_engineer(task_path, resume=resume)
    else:
        report = await run_engineer(resume=resume)

    failed = [r for r in report["results"] if isinstance(r, dict) and not r.get("success", True)]
    if failed:
        print(f"\n失败任务 ({len(failed)}):")
        for f in failed:
            print(f"  - {f.get('task_id', '?')}: {(f.get('error') or '(无详情)')[:200]}")

    return report


if __name__ == "__main__":
    asyncio.run(main())
