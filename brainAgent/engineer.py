# brainAgent/engineer.py
"""
工程调度器 —— 读取 architecture_plan.json，按严格类型分层执行所有任务。

分层规则（由 utils/dependency_graph.build_layered 保证）:
  - 同层内任务类型相同 → system prompt 前缀一致 → 缓存命中
  - 不同类型任务绝不同层 → 避免 prompt 切换
  - 层间按 (拓扑深度, 类型优先级) 排序: infra → db → backend → frontend → integration
"""

import asyncio
import json
import sys
import shutil
from pathlib import Path
from typing import List, Dict, Any

from datetime import datetime

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from agent.backend_designer import run_backend_task
from agent.frontend_designer import run_frontend_task
from agent.infrastructure_designer import run_infrastructure_task
from agent.integrator import run_integration_task
from agent.database_designer import run_database_task
from agent.prompt_builder import build_system_prompt, build_user_prompt, build_integration_user_prompt
from utils.dependency_graph import build_layered, print_layers, build_full, _get_tid, _get_type

TASK_DIR = project_root / "work" / "project" / "task"
REPORT_DIR = project_root / "work" / "project" / "report"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
PROJECT_WORKSPACE = project_root / "work" / "project"
AGENT_LOG_DIR = project_root / "Memory" / "agent_logs" / "engineer"
TRUTH_DIR_ENGINEER = project_root / "Memory" / "truths" / "engineer"
ENGINEER_STATE_DIR = project_root / "Memory" / "agent_logs" / "engineer" / "states"
AGENT_LOG_DIR.mkdir(parents=True, exist_ok=True)
TRUTH_DIR_ENGINEER.mkdir(parents=True, exist_ok=True)
ENGINEER_STATE_DIR.mkdir(parents=True, exist_ok=True)
MAX_CONCURRENT_TASKS = 100


# ═══════════════════════════════════════════════════════
# 任务状态 — 支持跳过已成功生成的代码
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
    """加载任务状态。"""
    f = ENGINEER_STATE_DIR / f"{task_id}.json"
    if f.exists():
        try:
            return EngineerTaskState.from_dict(json.loads(f.read_text("utf-8")))
        except Exception:
            pass
    return EngineerTaskState(task_id)


def _save_engineer_state(state: EngineerTaskState):
    """保存任务状态。"""
    f = ENGINEER_STATE_DIR / f"{state.task_id}.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(state.to_dict(), indent=2, ensure_ascii=False), "utf-8")


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


def _save_engineer_truth(task_id: str, task: Dict, result: Dict):
    """工程师任务成功后，写入真理到 Memory/truths/engineer/{task_id}.json。

    优先使用 LLM 生成的 interface（BaseDesigner._extract_exposed_interface 产出），
    包含完整的函数签名/表结构/路由/middleware 等对外暴露面。
    """
    import json
    output_files = task.get("outputFiles") or task.get("files") or []
    meta = result.get("metadata", {}) or {}
    interface = result.get("interface") or meta.get("interface") or {}

    truth = {
        "task_id": task_id,
        "type": task.get("type", ""),
        "output_files": output_files,
        "description": task.get("description", ""),
        "exposed": interface,  # LLM 生成的完整接口
    }
    fp = TRUTH_DIR_ENGINEER / f"{task_id}.json"
    fp.write_text(json.dumps(truth, indent=2, ensure_ascii=False), "utf-8")


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


async def execute_task(task: Dict, contracts: List[Dict],
                       agent_type: str, workspace: str,
                       resume: bool = False) -> Dict[str, Any]:
    """执行单个任务。resume=True 时跳过已成功的任务。"""
    tid = _get_tid(task)
    workspace_path = Path(workspace)

    # 统一 path/files → outputFiles（不修改原 task，下游 _get_target_files 已兼容所有字段名）
    output_files = task.get("outputFiles") or task.get("files") or task.get("path") or []

    # ── 跳过已成功的任务 ──
    if resume:
        state = _load_engineer_state(tid)
        if state.is_done and _all_output_files_exist(task, workspace_path):
            print(f"  ⏭ [{agent_type}] {tid}: SKIP (already done, {len(output_files)} files)")
            return {
                "task_id": tid,
                "type": agent_type,
                "success": True,
                "duration_seconds": 0,
                "error": None,
                "metadata": {"skipped": True, "reason": "already completed"},
            }
        elif state.is_done:
            # 状态标记成功但文件缺失 → 清除过期状态，重新执行
            print(f"  🔄 [{agent_type}] {tid}: state says done but files missing, re-running")
            _clear_engineer_state(tid)

    print(f"  [{agent_type}] {tid}: {task.get('description', '')[:60]}...")

    # 筛选关联契约
    relevant = filter_contracts_by_uses(contracts, task)

    # 统一提示词
    extra = ""  # 架构师 envConstraints 等注入
    env_constraints = task.get("envConstraints", {})
    if env_constraints:
        extra += "\n## 环境变量约束\n" + "\n".join(
            f"- {k}: {v}" for k, v in env_constraints.items()
        )

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
        if success:
            _save_engineer_truth(tid, task, result)
            # 持久化成功状态，供后续 resume 使用
            _save_engineer_state(EngineerTaskState.from_dict({
                "task_id": tid,
                "success": True,
                "output_files": output_files,
                "timestamp": datetime.now().isoformat(),
                "error": "",
            }))
        return {
            "task_id": tid,
            "type": agent_type,
            "success": success,
            "duration_seconds": duration,
            "error": result.get("error"),
            "metadata": result.get("metadata"),
        }
    except Exception as e:
        duration = (datetime.now() - start).total_seconds() if 'start' in dir() else 0
        return {
            "task_id": tid,
            "type": agent_type,
            "success": False,
            "duration_seconds": duration,
            "error": str(e)[:300],
            "metadata": None,
        }


def _clear_engineer_state(task_id: str):
    """清除过期的任务状态（文件已丢失但状态标记为成功）。"""
    f = ENGINEER_STATE_DIR / f"{task_id}.json"
    if f.exists():
        try:
            f.unlink()
        except OSError:
            pass


async def run_engineer(task_file_path: Path = None, resume: bool = False):
    """主入口：加载架构计划 → 分层 → 逐层并发执行 → 集成 → 报告。

    Args:
        task_file_path: 架构计划 JSON 文件路径，None 则自动找最新
        resume: True 则跳过已成功生成且文件仍存在的任务
    """
    if task_file_path is None:
        task_file_path = find_latest_task_file()

    print(f"\n{'='*60}")
    print(f"加载: {task_file_path}")
    if resume:
        print(f"模式: RESUME（跳过已成功任务）")
    tasks, contracts = load_architecture_plan(task_file_path)
    print(f"任务: {len(tasks)}  契约: {len(contracts)}")

    # ── 契约轻量校验 ──
    _validate_contracts(contracts)

    # ── 文件冲突检测 ──
    file_owners = {}
    for t in tasks:
        for f in (t.get("outputFiles") or t.get("files") or []):
            if f in file_owners and file_owners[f] != _get_tid(t):
                print(f"  ⚠️ 文件冲突: {f} (被 {file_owners[f]} 和 {_get_tid(t)} 同时声明)")
            file_owners[f] = _get_tid(t)

    # ── 分层 ──
    layers = build_layered(tasks)
    print(f"\n执行计划: {len(layers)} 层")
    print_layers(layers)

    # ── 分离集成任务 ──
    non_integration_layers = []
    integration_task = None
    for layer in layers:
        if layer and _get_type(layer[0]) == "integration":
            integration_task = layer[0]  # 只有一个集成任务
        else:
            non_integration_layers.append(layer)

    # ── 清理旧元数据（resume 模式下保留 .meta，仅清理过期的）──
    workspace = str(PROJECT_WORKSPACE)
    meta_dir = PROJECT_WORKSPACE / ".meta"
    if resume:
        # 只清理 failed_tasks.json（上次的失败记录），保留其他
        old_failed = meta_dir / "failed_tasks.json"
        if old_failed.exists():
            old_failed.unlink()
    else:
        if meta_dir.exists():
            shutil.rmtree(meta_dir)
    meta_dir.mkdir(parents=True)

    # ── 元数据收集（传递给集成任务）──
    metadata_memory = {
        "backend_routes": [],
        "frontend_pages": [],
    }

    # ── 逐层执行（带剪枝 + 跳过已完成任务）──
    results = []
    failed_ids = set()
    pruned_ids = set()
    skipped_count = 0

    for i, layer in enumerate(non_integration_layers):
        agent_type = _get_type(layer[0])
        print(f"\n--- Layer {i}: {len(layer)} {agent_type} tasks ---")

        # ── 剪枝：依赖链上任何节点失败 → 裁剪该节点及全部后代 ──
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

        # ── 并发执行未被剪枝的任务 ──
        print(f"  执行 {len(runnable)}/{len(layer)} 个任务 ({len(layer) - len(runnable)} 被剪枝)")
        coros = [execute_task(t, contracts, agent_type, workspace, resume=resume) for t in runnable]
        batch_results = await asyncio.gather(*coros)

        for res in batch_results:
            results.append(res)
            tid = res["task_id"]
            meta = res.get("metadata", {}) or {}
            if meta.get("skipped"):
                skipped_count += 1
                status = "⏭"
            elif res["success"]:
                status = "✅"
            else:
                status = "❌"
                failed_ids.add(tid)
            print(f"  {status} {tid} ({res['duration_seconds']:.1f}s)")

            # 收集元数据（仅成功任务）
            meta = res.get("metadata")
            if meta:
                if meta.get("type") == "backend" and "routes" in meta:
                    metadata_memory["backend_routes"].extend(meta["routes"])
                elif meta.get("type") == "frontend" and "pages" in meta:
                    metadata_memory["frontend_pages"].extend(meta["pages"])

    # ── 执行集成任务 ──
    if integration_task:
        print(f"\n--- Integration ---")
        start = datetime.now()
        try:
            result = await run_integration_task(
                integration_task,
                workspace_root=workspace,
                metadata_memory=metadata_memory,
            )
            duration = (datetime.now() - start).total_seconds()
            results.append({
                "task_id": _get_tid(integration_task),
                "type": "integration",
                "success": result.get("success", False),
                "duration_seconds": duration,
                "error": result.get("error"),
                "metadata": None,
            })
            print(f"  {'✅' if result.get('success') else '❌'} integration ({duration:.1f}s)")
        except Exception as e:
            import traceback
            results.append({
                "task_id": _get_tid(integration_task),
                "type": "integration",
                "success": False,
                "duration_seconds": (datetime.now() - start).total_seconds(),
                "error": f"{e}\n{traceback.format_exc()}"[:500],
                "metadata": None,
            })

    # ── 失败 + 剪枝任务收集 ──
    # failed: 实际执行失败（根因）；pruned: 依赖链被剪（后代节点，未执行）
    # 修复顺序: 先修根因 → 根因修复后剪枝节点自动解除 → 重跑剪枝节点
    failed_or_pruned = [r for r in results if r and not r.get("success", True)]
    if failed_or_pruned:
        task_map = {_get_tid(t): t for t in tasks}
        failed_list = []
        pruned_list = []
        for f in failed_or_pruned:
            if not f: continue
            tid = f["task_id"]
            orig = task_map.get(tid, {})
            entry = {
                "task_id": tid,
                "type": f["type"],
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

        # 修复顺序: 先 failed（根因），后 pruned（根因修好后解除）
        ordered = failed_list + pruned_list

        failed_file = PROJECT_WORKSPACE / ".meta" / "failed_tasks.json"
        failed_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "source": str(task_file_path),
            "failed": failed_list,
            "pruned": pruned_list,
            "repair_order": [e["task_id"] for e in ordered],
        }
        failed_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), "utf-8")
        print(f"\n任务结果: {len(failed_list)} 失败, {len(pruned_list)} 被剪枝 → {failed_file}")
        for f in failed_list:
            print(f"  ❌ {f['task_id']} ({f['type']}): {(f.get('error') or '(无详情)')[:120]}")
        for p in pruned_list:
            print(f"  ✂ {p['task_id']} ({p['type']}): 剪枝")

    # ── 报告 ──
    # 清理 workspace 内残留的 Memory/ 目录（真理已搬运到项目根）
    _cleanup_workspace_memory(PROJECT_WORKSPACE)
    return generate_report(task_file_path, results, layers, skipped_count)


def _cleanup_workspace_memory(workspace_path: Path):
    """清理 workspace 内残留的 Memory/ 目录，避免 work/project/Memory/ 膨胀。"""
    ws_memory = workspace_path / "Memory"
    if ws_memory.exists():
        try:
            shutil.rmtree(str(ws_memory))
        except OSError:
            pass


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


def generate_report(task_file_path: Path, results: list, layers: list = None, skipped_count: int = 0) -> dict:
    """生成执行报告。"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"execution_report_{timestamp}.json"

    summary = {
        "total": len(results),
        "success": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"] and not r.get("pruned")),
        "pruned": sum(1 for r in results if r.get("pruned")),
        "skipped": skipped_count,
        "total_duration": sum(r["duration_seconds"] for r in results),
        "layers": len(layers) if layers else 0,
    }

    report = {
        "task_file": str(task_file_path),
        "timestamp": datetime.now().isoformat(),
        "summary": summary,
        "results": results,
    }

    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), "utf-8")
    print(f"\n报告: {report_path}")
    skip_info = f"  跳过: {skipped_count}" if skipped_count > 0 else ""
    print(f"结果: {summary['success']}/{summary['total']} 成功  "
          f"失败: {summary['failed']}  剪枝: {summary['pruned']}{skip_info}  耗时: {summary['total_duration']:.1f}s  "
          f"分层: {summary['layers']}")

    return report


async def main():
    resume = "--resume" in sys.argv
    # 过滤掉标志参数，剩余第一个非标志参数为 task_file
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
