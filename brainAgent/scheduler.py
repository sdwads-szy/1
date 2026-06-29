# brainAgent/scheduler.py
"""
测试调度器 —— 适配新测试架构 (13层: 静态层直通 + 动态层ABCD)
"""

import asyncio, json, os, sys, hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

import redis.asyncio as aioredis

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from picoagents import Agent, OpenAIChatCompletionClient
from dotenv import load_dotenv

from agent.test_writer import run_test_writer
from agent.test_runner import run_test_runner
from agent.source_fixer import run_source_fixer
from Tools.memory.ban_memory import get_bans, store_bans, format_bans_for_agent, clear_bans
from utils.dependency_graph import build as build_dependency_graph, print_levels
from utils.json_extractor import extract_json

load_dotenv('./.env.example')

MEMORY_DIR = project_root / "Memory" / "test_logs"
AGENT_LOG_DIR = project_root / "Memory" / "agent_logs" / "test"
TRUTH_DIR_ENGINEER = project_root / "Memory" / "truths" / "engineer"
TRUTH_DIR_TEST = project_root / "Memory" / "truths" / "test"

for d in [MEMORY_DIR, AGENT_LOG_DIR, TRUTH_DIR_TEST]:
    d.mkdir(parents=True, exist_ok=True)

MAX_CONCURRENT = 100
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_redis_client: Optional[aioredis.Redis] = None

# ═══════════════════════════════════════════════
# 新测试架构: 13层, 静态层直通不经过ABCD
# ═══════════════════════════════════════════════

LAYER_ORDER = [
    "repair",          # -1: 修复层 (直接调 engineer)
    "infra",           #  0: 基础设施 (静态检查)
    "db",              #  1: 数据库 (静态对照)
    "frontend_static", #  1.5: 前端静态 (静态检查)
    "auth",            #  2: Auth (混合: Token链HTTP + middleware/frontend静态)
    "db_api",          #  3: db-api (动态)
    "peer_deps",       #  3.5: 同层依赖 (静态检查)
    "api",             #  4: api (动态)
    "backend_proc",    #  4.5: 后端处理 (动态)
    "navigation",      #  5: navigation (动态)
    "logic",           #  6: logic (动态)
    "scenario",        #  7: scenario (动态)
    "nfr",             #  8: NFR (动态)
]

# 所有层统一走 ABCD 循环。静态/动态的区别在测试模板里, 不在调度器里。
# repair 层例外: 直接调 engineer agent, 不写测试代码。


# ═══════════════════════════════════════════════
# Truth 加载 (Agent生成主数据源 + 正则验证回退)
# ═══════════════════════════════════════════════

def _load_engineer_truths() -> Dict[str, dict]:
    """从 Memory/truths/engineer/ 加载 Agent 生成的真理 (主数据源)。"""
    truths = {}
    if TRUTH_DIR_ENGINEER.exists():
        for fp in sorted(TRUTH_DIR_ENGINEER.glob("*.json")):
            try:
                data = json.loads(fp.read_text("utf-8"))
                exposed = data.get("exposed", {})
                if exposed and isinstance(exposed, dict):
                    truths[fp.stem] = exposed
            except (json.JSONDecodeError, OSError):
                pass
    return truths


def _load_test_truths() -> Dict[str, dict]:
    """从 Memory/truths/test/ 加载测试阶段真理 (覆盖 engineer)。"""
    truths = {}
    if TRUTH_DIR_TEST.exists():
        for fp in sorted(TRUTH_DIR_TEST.glob("*.json")):
            try:
                truths[fp.stem] = json.loads(fp.read_text("utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
    return truths


def _resolve_truth(task: dict, engineer_truths: dict, test_truths: dict) -> dict:
    """解析任务需要的真理: test truth > engineer truth。"""
    tid = task.get("sourceTask") or task.get("id", "")
    # 先查 test truth (测试阶段产出, 更精确)
    if tid in test_truths:
        return test_truths[tid]
    # 再查 engineer truth (代码生成阶段产出)
    if tid in engineer_truths:
        return engineer_truths[tid]
    # 尝试模糊匹配 (sourceTask 可能包含多个 task 的引用)
    # 优先精确子串匹配（tid 作为独立 token 出现在 key 中），避免 "order" 误匹配 "order_item"
    for key in engineer_truths:
        # 检查 key 是否包含 tid 作为完整路径段（以 _ 或 - 分隔）
        key_segments = key.replace("-", "_").split("_")
        tid_segments = tid.replace("-", "_").split("_")
        # 所有 tid 的 segment 都在 key 中出现 → 认为匹配
        if all(seg in key_segments for seg in tid_segments):
            return engineer_truths[key]
    return {}


# ═══════════════════════════════════════════════
# Redis 缓存 (保留, 不变)
# ═══════════════════════════════════════════════

class RedisCache:
    _redis_available: Optional[bool] = None
    _snapshot_dir = project_root / "Memory" / "snapshots"

    @classmethod
    async def _ensure_available(cls) -> bool:
        if cls._redis_available is not None:
            return cls._redis_available
        global _redis_client
        try:
            _redis_client = await aioredis.from_url(REDIS_URL, decode_responses=True)
            await _redis_client.ping()
            cls._redis_available = True
        except Exception as e:
            cls._redis_available = False
            _redis_client = None
            cls._snapshot_dir.mkdir(parents=True, exist_ok=True)
            print(f"[scheduler] Redis 不可用({e})，降级到文件快照")
        return cls._redis_available

    @staticmethod
    def compute_source_hash(target_files: List[str], workspace: str) -> str:
        hasher = hashlib.md5(usedforsecurity=False)
        ws = Path(workspace).resolve()
        for tf in sorted(target_files):
            src = ws / tf
            if src.is_file():
                hasher.update(src.read_bytes())
        return hasher.hexdigest()[:16]

    @classmethod
    def _best_file(cls, task_id: str) -> Path:
        return cls._snapshot_dir / f"best_{task_id}.json"

    @classmethod
    def _snap_file(cls, task_id: str, source_hash: str) -> Path:
        return cls._snapshot_dir / f"snap_{task_id}_{source_hash}.json"

    @classmethod
    async def get_best(cls, task_id: str) -> Optional[Dict[str, Any]]:
        fp = cls._best_file(task_id)
        if fp.exists():
            try:
                return json.loads(fp.read_text("utf-8"))
            except Exception:
                pass
        if await cls._ensure_available():
            try:
                data = await _redis_client.hgetall(f"test_scheduler:best:{task_id}")
                if data:
                    return {
                        "best_score": float(data.get("best_score", 0)),
                        "best_attempt": int(data.get("best_attempt", 0)),
                        "source_hash": data.get("source_hash", ""),
                    }
            except Exception:
                pass
        return None

    @classmethod
    async def set_best(cls, task_id: str, attempt: int, score: float,
                       source_hash: str, test_result: dict):
        data = {"best_score": score, "best_attempt": attempt, "source_hash": source_hash, "test_result": test_result}
        fp = cls._best_file(task_id)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
        if await cls._ensure_available():
            try:
                await _redis_client.hset(f"test_scheduler:best:{task_id}", mapping={
                    "best_score": score, "best_attempt": attempt,
                    "source_hash": source_hash,
                    "test_result": json.dumps(test_result, ensure_ascii=False),
                })
            except Exception:
                pass

    @classmethod
    async def save_source_snapshot(cls, task_id: str, source_hash: str,
                                   target_files: List[str], workspace: str):
        if not target_files:
            return
        ws = Path(workspace).resolve()
        snap = {}
        for tf in target_files:
            src = ws / tf
            if src.exists():
                snap[tf] = src.read_text("utf-8")
        if snap:
            fp = cls._snap_file(task_id, source_hash)
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(json.dumps(snap, indent=2, ensure_ascii=False), "utf-8")

    @classmethod
    async def restore_source_snapshot(cls, task_id: str, source_hash: str,
                                      target_files: List[str], workspace: str) -> int:
        fp = cls._snap_file(task_id, source_hash)
        if not fp.exists():
            return 0
        try:
            snap = json.loads(fp.read_text("utf-8"))
        except Exception:
            return 0
        ws = Path(workspace).resolve()
        restored = 0
        for tf, content in snap.items():
            dst = ws / tf
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(content, "utf-8")
            restored += 1
        return restored

    @classmethod
    async def rollback_to_best(cls, task_id: str, target_files: List[str],
                               workspace: str) -> Tuple[int, float, int]:
        best = await cls.get_best(task_id)
        if not best or not best.get("source_hash"):
            return (0, 0, 0)
        restored = await cls.restore_source_snapshot(
            task_id, best["source_hash"], target_files, workspace)
        return (best["best_attempt"], best["best_score"], restored)


# ═══════════════════════════════════════════════
# 任务状态 (保留, 不变)
# ═══════════════════════════════════════════════

class TaskTestState:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.test_success = False
        self.source_success = False
        self.test_file_path: Optional[str] = None
        self.attempt = 0
        self.done = False
        self.best_score: float = 0.0
        self.best_attempt: int = 0
        self.source_hash: str = ""
        self.truth: str = ""

    @property
    def state_label(self) -> str:
        return f"({'TS' if self.test_success else 'TF'}, {'SS' if self.source_success else 'SF'})"

    @property
    def is_ts_ss(self) -> bool:
        return self.test_success and self.source_success

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id, "test_success": self.test_success,
            "source_success": self.source_success, "test_file_path": self.test_file_path,
            "attempt": self.attempt, "done": self.done,
            "best_score": self.best_score, "best_attempt": self.best_attempt,
            "source_hash": self.source_hash, "state": self.state_label, "truth": self.truth,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TaskTestState":
        s = cls(d["task_id"])
        s.test_success = d.get("test_success", False)
        s.source_success = d.get("source_success", False)
        s.test_file_path = d.get("test_file_path")
        s.attempt = d.get("attempt", 0)
        s.done = d.get("done", False)
        s.best_score = d.get("best_score", 0.0)
        s.best_attempt = d.get("best_attempt", 0)
        s.source_hash = d.get("source_hash", "")
        s.truth = d.get("truth", "")
        return s


def _load_state(task_id: str) -> TaskTestState:
    f = MEMORY_DIR / f"{task_id}.json"
    if f.exists():
        try:
            return TaskTestState.from_dict(json.loads(f.read_text("utf-8")))
        except Exception:
            pass
    return TaskTestState(task_id)


def _save_state(state: TaskTestState):
    f = MEMORY_DIR / f"{state.task_id}.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(state.to_dict(), indent=2, ensure_ascii=False), "utf-8")


# ═══════════════════════════════════════════════
# 调试日志
# ═══════════════════════════════════════════════

class DebugLogger:
    @staticmethod
    def _dir(task_id: str, attempt: int) -> Path:
        d = AGENT_LOG_DIR / task_id / f"attempt_{attempt}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @classmethod
    def save_raw(cls, task_id: str, attempt: int, step: str, agent_name: str, raw_output: str):
        d = cls._dir(task_id, attempt)
        (d / f"{step}_{agent_name}.md").write_text(raw_output, "utf-8")


# ═══════════════════════════════════════════════
# Layer -1: 修复层 — 直接调 engineer agent
# ═══════════════════════════════════════════════

async def _handle_repair_task(task: dict, workspace: str) -> TaskTestState:
    """修复层: 直接调用对应 engineer agent 重新生成缺失源文件。不走ABCD。"""
    task_id = task.get("id", "unknown")
    target_task_id = task.get("targetTaskId", "")
    agent_type = task.get("agentType", "")
    missing_files = task.get("missingFiles", [])

    print(f"  [{task_id}] REPAIR: re-running {agent_type} agent for {target_task_id}")

    ws_path = Path(workspace)
    all_exist = all((ws_path / f).exists() and (ws_path / f).stat().st_size > 0 for f in missing_files)
    if all_exist:
        state = TaskTestState(task_id)
        state.test_success = True
        state.source_success = True
        state.done = True
        _save_state(state)
        return state

    try:
        if agent_type == "infra":
            from agent.infrastructure_designer import run_infrastructure_task
            result = await run_infrastructure_task(
                {"taskId": target_task_id, "outputFiles": missing_files}, workspace_root=workspace)
        elif agent_type == "db":
            from agent.database_designer import run_database_task
            result = await run_database_task(
                {"taskId": target_task_id, "outputFiles": missing_files}, workspace_root=workspace)
        elif agent_type == "backend":
            from agent.backend_designer import run_backend_task
            result = await run_backend_task(
                {"taskId": target_task_id, "outputFiles": missing_files}, workspace_root=workspace)
        elif agent_type == "frontend":
            from agent.frontend_designer import run_frontend_task
            result = await run_frontend_task(
                {"taskId": target_task_id, "outputFiles": missing_files}, workspace_root=workspace)
        elif agent_type == "integration":
            from agent.integrator import run_integration_task
            result = await run_integration_task(
                {"taskId": target_task_id}, workspace_root=workspace)
        else:
            result = {"success": False, "error": f"Unknown agent type: {agent_type}"}
    except Exception as e:
        result = {"success": False, "error": str(e)}

    all_exist = all((ws_path / f).exists() and (ws_path / f).stat().st_size > 0 for f in missing_files)
    state = TaskTestState(task_id)
    if all_exist or result.get("success"):
        state.test_success = True
        state.source_success = True
        state.done = True
    _save_state(state)
    return state


# ═══════════════════════════════════════════════
# 主调度器
# ═══════════════════════════════════════════════

async def run_scheduler(
    workspace: str = "./work/project",
    test_tasks_file: str = "./work/project/test/test_tasks.json",
    fast: bool = False,
    max_total_attempts: int = 3,
    max_concurrent: int = MAX_CONCURRENT,
    model_client=None,
) -> Dict[str, Any]:
    t0 = datetime.now()
    ws_path = Path(workspace).resolve()
    tasks_file = Path(test_tasks_file)
    if not tasks_file.exists():
        return {"error": f"test_tasks.json not found: {test_tasks_file}"}
    tasks_data = json.loads(tasks_file.read_text("utf-8"))
    all_tasks = tasks_data.get("testTasks", [])
    if not all_tasks:
        return {"error": "No test tasks found"}
    print(f"[scheduler] Loaded {len(all_tasks)} test tasks")

    _inject_jest_module_name_mapper(ws_path)
    _ensure_npm_install(ws_path, all_tasks)
    _check_frontend_test_infra(ws_path, all_tasks)
    _init_database(ws_path, all_tasks)

    if model_client is None:
        from utils.model_client import get_model_client
        model_client = get_model_client()
    model = model_client

    if fast:
        await _fast_jest_sweep(ws_path)

    # ── 加载全部 engineer truth (Agent生成, 主数据源) ──
    engineer_truths = _load_engineer_truths()
    print(f"[scheduler] Loaded {len(engineer_truths)} engineer truths")

    # ── 预过滤: 移除 targetFiles 中不存在的文件（防止 test_architect 编造的文件名导致死循环）──
    for t in all_tasks:
        tfs = t.get("targetFiles", [])
        if tfs:
            existing = [tf for tf in tfs if (ws_path / tf).exists()]
            removed = len(tfs) - len(existing)
            if removed:
                print(f"  [prune-targetFiles] {t['id']}: removed {removed} non-existent files from targetFiles: {set(tfs) - set(existing)}")
                t["targetFiles"] = existing
                # 同步移除对应 scenarios
                removed_files = set(tfs) - set(existing)
                t["testScenarios"] = [s for s in t.get("testScenarios", [])
                                      if not any(rf in s.get("given", "") + s.get("when", "") for rf in removed_files)]

    # ── 依赖图 ──
    task_map, levels = build_dependency_graph(all_tasks)
    print(f"\n[scheduler] Dependency graph: {len(levels)} levels")
    print_levels(levels)

    completed: Dict[str, TaskTestState] = {}
    failed_task_ids: set = set()
    layer_truths: Dict[str, dict] = {}
    test_truths = _load_test_truths()
    for tid, truth_entry in test_truths.items():
        task_layer = task_map.get(tid, {}).get("layer", "")
        if task_layer:
            layer_truths.setdefault(task_layer, {})[tid] = truth_entry

    all_results = []
    summary = {"total": len(all_tasks), "passed": 0, "failed": 0, "blocked": 0, "manual_needed": 0}
    global_blocked = False

    for level_idx, level in enumerate(levels):
        if global_blocked:
            summary["blocked"] += len(level)
            continue

        layer_name = level[0].get("layer", "?") if level else "?"
        print(f"\n{'='*50}\n Level {level_idx}: {len(level)} tasks [{layer_name}]\n{'='*50}")

        runnable = []
        for task in level:
            deps_ok = all(dep in completed and completed[dep].is_ts_ss for dep in task.get("dependencies", []))
            if deps_ok:
                runnable.append(task)
            else:
                summary["blocked"] += 1

        if not runnable:
            continue

        sem = asyncio.Semaphore(max_concurrent)

        async def run_one(t):
            async with sem:
                if t.get("layer") == "repair":
                    return await _handle_repair_task(t, str(ws_path))
                else:
                    return await _execute_single_task(t, str(ws_path), max_total_attempts, model, layer_truths, LAYER_ORDER, task_map)

        level_results = await asyncio.gather(*[run_one(t) for t in runnable], return_exceptions=True)

        level_all_passed = True
        for task, result in zip(runnable, level_results):
            tid = task["id"]
            if isinstance(result, Exception):
                print(f"  [{tid}] EXCEPTION: {result}")
                summary["failed"] += 1
                failed_task_ids.add(tid)
                level_all_passed = False
                continue

            state = result
            completed[tid] = state
            status = "passed" if state.is_ts_ss else "failed"
            if state.is_ts_ss:
                summary["passed"] += 1
                task_layer = task.get("layer", "")
                if task_layer and state.truth:
                    truth_entry = task.get("produces", {})
                    truth_entry["_truth"] = state.truth
                    layer_truths.setdefault(task_layer, {})[tid] = truth_entry
                    _save_truth(tid, truth_entry)
            else:
                summary["failed"] += 1
                failed_task_ids.add(tid)
                level_all_passed = False
            all_results.append({"task_id": tid, "status": status, "attempts": state.attempt})
            print(f"  [{tid}] {status} ({state.state_label})")

        if level_all_passed:
            print(f"  OK Level {level_idx}: all {len(runnable)} passed")
        else:
            global_blocked = True
            n_failed = sum(1 for t in runnable if t["id"] in failed_task_ids)
            print(f"  FAIL Level {level_idx}: {n_failed}/{len(runnable)} failed. downstream blocked.")

    if _redis_client:
        await _redis_client.close()

    elapsed = (datetime.now() - t0).total_seconds()
    print(f"\n[scheduler] {summary['passed']} passed, {summary['failed']} failed, "
          f"{summary['blocked']} blocked ({elapsed:.0f}s)")

    result = {"summary": {**summary, "elapsed_seconds": elapsed}, "results": all_results}
    return result


# ═══════════════════════════════════════════════
# 动态层 ABCD 循环 (保留核心逻辑, 适配新层)
# ═══════════════════════════════════════════════

async def _execute_single_task(
    task: dict, workspace: str, max_attempts: int, model,
    layer_truths: dict = None, layer_order: list = None,
    task_map: dict = None,
) -> TaskTestState:
    task_id = task.get("id", "unknown")
    state = _load_state(task_id)

    for attempt in range(1, max_attempts + 1):
        state.attempt = attempt
        print(f"\n  [{task_id}] Attempt {attempt}/{max_attempts}, state={state.state_label}")
        try:
            return_val = await _attempt_once(task, state, attempt, max_attempts, workspace, model, layer_truths, layer_order, task_map)
            if return_val is not None:
                return return_val
        except Exception as exc:
            print(f"    [!] {exc}")
            state.test_success = False
            state.source_success = False
            _save_state(state)
            continue

    if not state.test_success and state.test_file_path:
        tp = Path(state.test_file_path)
        if tp.exists():
            tp.unlink()

    best_att, best_score, restored = await RedisCache.rollback_to_best(
        task_id, task.get("targetFiles", []), workspace)
    if restored > 0:
        state.best_score, state.best_attempt = best_score, best_att
    state.done = True
    _save_state(state)
    return state


async def _attempt_once(
    task: dict, state: TaskTestState, attempt: int,
    max_attempts: int, workspace: str, model,
    layer_truths: dict = None, layer_order: list = None,
    task_map: dict = None,
):
    task_id = task.get("id", "unknown")
    layer = task.get("layer", "")

    if state.is_ts_ss:
        return state

    fw = task.get("testFramework", "jest")
    target_files = task.get("targetFiles", task.get("path", []))
    ws = Path(workspace).resolve()
    current_source_hash = RedisCache.compute_source_hash(target_files, workspace)

    _SKIP_READ = {'package-lock.json', 'node_modules', '.git'}
    source_contents = {}
    for tf in target_files:
        if any(s in tf for s in _SKIP_READ):
            continue
        p = ws / tf
        if p.exists():
            try:
                source_contents[tf] = p.read_text(encoding='utf-8')
            except Exception as e:
                source_contents[tf] = f"[读取失败: {e}]"

    if state.test_file_path:
        tp = Path(state.test_file_path)
        if tp.exists():
            try:
                source_contents[f"__TEST_FILE__:{state.test_file_path}"] = tp.read_text(encoding='utf-8')
            except Exception:
                pass

    test_bans = get_bans(task_id, "test_failure")
    source_bans = get_bans(task_id, "source_failure")

    # ── 注入下层真理 ──
    lower_truths_text = _collect_dep_truths(task, task_map or {}, layer_truths or {})

    if attempt == 1:
        task_log_dir = AGENT_LOG_DIR / task_id
        if task_log_dir.exists():
            import shutil
            shutil.rmtree(str(task_log_dir))
    log_dir = str(AGENT_LOG_DIR / task_id / f"attempt_{attempt}")

    # ── 根据 layer 调整 ABCD 行为 ──
    bans_text = format_bans_for_agent(test_bans)
    if lower_truths_text:
        bans_text = lower_truths_text + bans_text

    # ── A: 写测试 ──
    test_subdir_map = {"unit": "test/unit", "business": "test/business", "joint": "test/joint", "special": "test/special"}
    test_subdir = test_subdir_map.get(task.get("category", "unit"), "test/unit")
    test_file_expected = ws / test_subdir / f"{task_id}.test.js"
    pre_written_exists = test_file_expected.exists()
    if pre_written_exists and not state.test_file_path:
        state.test_file_path = str(test_file_expected)
    skip_a = (state.test_success and state.test_file_path and Path(state.test_file_path).exists())

    if skip_a:
        print(f"    [a] SKIP")
    else:
        print(f"    [{task_id}] [a] Writing test...")
        wr = await run_test_writer(
            task=task, workspace_root=workspace, source_contents=source_contents,
            model_client=model, task_id=task_id, attempt=attempt,
            bans_text=bans_text, save_dir=log_dir + "/", save_filename="a_test_writer_token",
        )
        DebugLogger.save_raw(task_id, attempt, "a", "test_writer", wr.get("raw_output", ""))
        state.test_file_path = wr.get("test_file")

        validation_errors = wr.get("validation_errors", [])
        if validation_errors:
            for err in validation_errors:
                err_msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                store_bans(task_id, "test_failure", [{
                    "f": f"{layer}|test_writer|generate|{err.get('type', 'syntax') if isinstance(err, dict) else 'syntax'}",
                    "b": f"DON'T: {err_msg} | fix: 按对应模板规范修复 | test/unit"
                }])
            state.test_success = False
            _save_state(state)

        if not wr["success"] and not validation_errors:
            state.test_success = False
            _save_state(state)
            if not state.test_file_path:
                return None
        if not validation_errors:
            state.test_success = True

    # ── B: 运行测试 ──
    if not state.test_file_path:
        return None
    if state.is_ts_ss:
        return state

    run_b = not state.test_success or not skip_a
    if not run_b:
        print(f"    [b] SKIP")
    else:
        print(f"    [{task_id}] [b] Running test...")
        br = await run_test_runner(
            test_file_path=state.test_file_path, test_framework=fw, workspace_root=workspace,
            step="b", model_client=model, task_id=task_id, attempt=attempt,
            bans=test_bans, source_contents=source_contents, task=task,
            save_dir=log_dir + "/", save_filename="b_test_runner_token",
        )
        total, failed = br.get("total", 0), br.get("failed", 0)
        DebugLogger.save_raw(task_id, attempt, "b", "test_runner", br.get("raw_output", ""))

        if total == 0:
            bans = br.get("bans", [])
            has_l0_source = any(
                b.get("f", "").startswith("L0|") or
                (len(b.get("f", "").split("|")) >= 2 and b.get("f", "").split("|")[1] == "source")
                for b in bans
            ) or br.get("fix_target") == "source"
            if has_l0_source:
                store_bans(task_id, "source_failure", bans)
                state.test_success = True
                state.source_success = False
                _save_state(state)
                # 直接跳到 C
            else:
                state.test_success = False
                state.source_success = False
                store_bans(task_id, "test_failure", bans)
                _save_state(state)
                return None

        if failed == 0 and total > 0:
            state.test_success = True
            state.source_success = True
            state.done = True
            # 提取真理 + 评分入库 (total>0 & failed==0: B步骤首次全部通过)
            interface = await _extract_test_interface(task, source_contents, workspace, task_id, model)
            if interface:
                state.truth = json.dumps(interface, ensure_ascii=False)
            await _score_and_store(task, br, workspace, task_id, attempt, log_dir, state.test_file_path)
            _save_state(state)
            return state

        if failed > 0:
            fix_target = br.get("fix_target", "source")
            store_bans(task_id, "test_failure" if fix_target == "test" else "source_failure", br.get("bans", []))
            if fix_target == "test":
                state.test_success = False
                state.source_success = False
                _save_state(state)
                return None
            state.test_success = True
            state.source_success = False

    # ── C: 修复源码 ──
    if not state.test_success and not state.source_success:
        return None  # 测试有问题, 下一轮A重写

    if state.source_success:
        return state

    print(f"    [{task_id}] [c] Fixing source...")
    _save_state(state)
    await RedisCache.save_source_snapshot(task_id, current_source_hash, target_files, workspace)

    current_source_contents = {}
    for tf in target_files:
        if any(s in tf for s in _SKIP_READ):
            continue
        p = ws / tf
        if p.exists():
            try:
                current_source_contents[tf] = p.read_text(encoding='utf-8')
            except Exception:
                pass

    source_bans_text = format_bans_for_agent(source_bans)
    if lower_truths_text:
        source_bans_text = lower_truths_text + source_bans_text

    cr = await run_source_fixer(
        task=task, test_file_path=state.test_file_path, workspace_root=workspace,
        source_contents=current_source_contents, model_client=model, task_id=task_id,
        attempt=attempt, bans_text=source_bans_text,
        save_dir=log_dir + "/", save_filename="c_source_fixer_token",
    )
    DebugLogger.save_raw(task_id, attempt, "c", "source_fixer", cr.get("raw_output", ""))
    if not cr["success"]:
        state.test_success = False
        state.source_success = False
        _save_state(state)
        return None

    new_source_hash = RedisCache.compute_source_hash(target_files, workspace)
    post_c_source = {}
    for tf in target_files:
        p = ws / tf
        if p.exists():
            try:
                post_c_source[tf] = p.read_text(encoding='utf-8')
            except Exception:
                pass

    # ── D: 验证修复 ──
    print(f"    [{task_id}] [d] Verifying fix...")
    dr = await run_test_runner(
        test_file_path=state.test_file_path, test_framework=fw, workspace_root=workspace,
        step="d", model_client=model, task_id=task_id, attempt=attempt,
        bans=source_bans, source_contents=post_c_source, task=task,
        save_dir=log_dir + "/", save_filename="d_test_runner_token",
    )
    d_total, d_failed = dr.get("total", 0), dr.get("failed", 0)
    DebugLogger.save_raw(task_id, attempt, "d", "test_runner", dr.get("raw_output", ""))

    if d_total == 0 or d_failed > 0:
        store_bans(task_id, "source_failure", dr.get("bans", []))
        state.test_success = True
        state.source_success = False
        _save_state(state)
        return None

    state.test_success = True
    state.source_success = True
    state.done = True
    state.source_hash = new_source_hash

    interface = await _extract_test_interface(task, post_c_source, workspace, task_id, model)
    if interface:
        state.truth = json.dumps(interface, ensure_ascii=False)

    # D步骤通过: 评分 + 入库 (修复后的代码已验证正确)
    await _score_and_store(task, dr, workspace, task_id, attempt, log_dir, state.test_file_path)

    clear_bans(task_id, "source_failure")
    _save_state(state)
    return state


async def _score_and_store(task, test_result, workspace, task_id, attempt, log_dir, test_file_path):
    """评分 + 高分自动入库 (左脑数据来源)。"""
    try:
        from Tools.scoring.code_scorer import score_code, score_test_code, format_score_report
        from Tools.memory.ban_memory import get_bans as _get_bans

        target_files = task.get("targetFiles", [])
        ws = Path(workspace).resolve()
        source_files = {}
        for tf in target_files:
            fp = ws / tf
            if fp.exists():
                source_files[tf] = fp.read_text("utf-8")

        if not source_files:
            return

        src_mem = _get_bans(task_id, "source_failure")
        test_mem = _get_bans(task_id, "test_failure")
        jest_output = {"numTotalTests": test_result.get("total", 0), "numPassedTests": test_result.get("passed", 0)}

        result = score_code(source_files=source_files, engineer_tasks=[task], test_tasks=None,
                           source_memory=src_mem, test_memory=test_mem, test_output=jest_output)

        # 源码 >= 90 入库
        if result.total >= 90:
            try:
                from Tools.rag.code_retrieval.code_store import store_code
                store_code(code_files=source_files, task_id=task_id, task_type=task.get("layer", "backend_proc"),
                          contracts=task.get("usesContracts", []), code_score=result.total, code_level=result.level)
                print(f"    [score] 源码入库: {len(source_files)} files (score={result.total:.0f})")
            except Exception:
                pass

        # 测试代码 >= 90 入库
        if test_file_path and Path(test_file_path).exists():
            test_code = Path(test_file_path).read_text("utf-8")
            test_result_obj = score_test_code(test_content=test_code, task=task,
                                              test_output=jest_output, test_bans=test_mem)
            if test_result_obj.total >= 90:
                try:
                    from Tools.rag.code_retrieval.code_store import store_test_code
                    store_test_code(code_files={Path(test_file_path).name: test_code}, task_id=task_id,
                                   test_layer=task.get("layer", ""), test_framework=task.get("testFramework", "jest"),
                                   test_score=test_result_obj.total, test_level=test_result_obj.level)
                    print(f"    [score] 测试入库: {Path(test_file_path).name} (score={test_result_obj.total:.0f})")
                except Exception:
                    pass

        # 保存评分报告
        if log_dir:
            import os as _os
            _os.makedirs(log_dir, exist_ok=True)
            from datetime import datetime
            score_log = {"task_id": task_id, "attempt": attempt, "total": result.total, "level": result.level,
                        "timestamp": datetime.now().isoformat(), "source_files": list(source_files.keys())}
            with open(_os.path.join(log_dir, "code_score.json"), "w", encoding="utf-8") as f:
                json.dump(score_log, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# ═══════════════════════════════════════════════
# 辅助函数 (保留核心, 精简)
# ═══════════════════════════════════════════════

async def _extract_test_interface(task, source_contents, workspace, task_id, model) -> dict:
    """测试通过后提取对外接口。Agent 主生成 + Python 验证回退。"""
    layer = task.get("layer", "")
    target_files = task.get("targetFiles", [])
    ws = Path(workspace).resolve()

    # ── 1. 读取 Agent 生成的 engineer truth (代码生成阶段产出) ──
    engineer_truth = {}
    source_tid = task.get("sourceTask", "")
    if source_tid:
        tf = TRUTH_DIR_ENGINEER / f"{source_tid}.json"
        if tf.exists():
            try:
                engineer_truth = json.loads(tf.read_text("utf-8")).get("exposed", {})
            except Exception:
                pass

    # ── 2. 读取实际生成的文件内容 ──
    file_contents = {}
    for tf_path in target_files:
        fp = ws / tf_path
        if fp.exists():
            try:
                file_contents[tf_path] = fp.read_text("utf-8")[:8000]
            except Exception:
                pass

    if not file_contents:
        return task.get("produces", {})

    # ── 3. Agent 主生成: LLM 精读源码 + truth → 结构化接口 ──
    prompt = _TRUTH_EXTRACT_PROMPTS.get(layer, _TRUTH_EXTRACT_PROMPTS["_default"])
    context = f"任务: {task.get('description', '')}\n测试层: {layer}\n测试场景: {json.dumps(task.get('testScenarios', []), ensure_ascii=False)[:2000]}"
    files_block = "\n\n".join(f"### {p}\n```\n{c}\n```" for p, c in file_contents.items())
    instructions = prompt.replace("{context}", context).replace("{files}", files_block)

    extract_agent = Agent(
        name=f"truth_extractor_{task_id}",
        description="接口提取器 — 只读不写",
        instructions=instructions,
        model_client=model,
        tools=[],
        max_iterations=1,
    )

    collected = ""
    try:
        async for event in extract_agent.run_stream("提取对外暴露接口，输出 JSON。", stream_tokens=False):
            collected += str(event)
    except Exception:
        pass

    interface = extract_json(collected)
    if isinstance(interface, dict) and interface:
        return interface

    # ── 4. Python 回退: Agent 失败时用正则扫描 ──
    return _scan_interface_from_files(layer, file_contents, target_files, engineer_truth)


def _scan_interface_from_files(layer: str, file_contents: dict, target_files: list, engineer_truth: dict) -> dict:
    """Python 正则回退: 从生成文件中扫描接口。"""
    import re
    result = {"exposed_to_upper": {}, "exposed_to_peers": {}}

    for tf, content in file_contents.items():
        if layer in ("infra", "peer_deps"):
            exports = re.findall(r'module\.exports\.(\w+)\s*=', content)
            if not exports:
                m = re.search(r'module\.exports\s*=\s*\{([^}]+)\}', content)
                if m:
                    exports = re.findall(r'(\w+)', m.group(1))
            if not exports:
                m = re.search(r'module\.exports\s*=\s*(\w+)', content)
                if m:
                    exports = [m.group(1)]
            if exports:
                result["exposed_to_upper"]["exports"] = exports

        elif layer == "db":
            tables = re.findall(r'CREATE\s+TABLE.*?`(\w+)`', content, re.IGNORECASE)
            if tables:
                result["exposed_to_upper"]["tables"] = tables

        elif layer in ("backend_proc", "db_api"):
            routes = re.findall(r'router\.(get|post|put|delete)\s*\(\s*[\'\"]([^\'\"]+)', content)
            if routes:
                result["exposed_to_upper"]["routes"] = [{"method": m.upper(), "path": p} for m, p in routes]
            svc_fns = re.findall(r'async\s+function\s+(\w+)', content)
            if svc_fns:
                result["exposed_to_peers"]["services"] = svc_fns

        elif layer == "frontend_static":
            pages = [tf for tf in target_files if tf.endswith('.vue')]
            api_calls = re.findall(r"""url:\s*['\"]([^'\"]+)['\"]\s*,\s*method:\s*['\"]([^'\"]+)['\"]""", content)
            if pages:
                result["exposed_to_upper"]["pages"] = pages
            if api_calls:
                result["exposed_to_upper"]["api_calls"] = [{"url": u, "method": m.upper()} for u, m in api_calls]

    return result


_TRUTH_EXTRACT_PROMPTS = {
    "infra": """你是接口提取器。综合测试场景和源码，提取该 infra 模块的对外暴露接口。

{context}

代码:
{files}

输出 JSON:
{{
  "exposed_to_upper": {{
    "middleware": [{{"name": "...", "signature": "...", "reqInjection": "..."}}],
    "utils_exports": [{{"file": "...", "exports": [...], "exportStyle": "named|default|object"}}],
    "config_exports": [{{"file": "...", "exports": [...], "exportStyle": "..."}}]
  }},
  "exposed_to_peers": {{}}
}}""",

    "db": """你是接口提取器。综合测试场景和源码，提取数据库表结构。

{context}

代码:
{files}

输出 JSON:
{{
  "exposed_to_upper": {{
    "tables": [{{"name": "...", "fields": [{{"name": "...", "type": "...", "constraints": "..."}}], "indexes": [...], "foreignKeys": [...]}}]
  }}
}}""",

    "frontend_static": """你是接口提取器。综合测试场景和源码，提取前端模块的对外接口。

{context}

代码:
{files}

输出 JSON:
{{
  "exposed_to_upper": {{
    "pages": [{{"component": "...", "file": "...", "route": "..."}}],
    "api_calls": [{{"from": "...", "endpoints": ["GET /xxx", "POST /xxx"]}}]
  }},
  "exposed_to_peers": {{
    "stores": [{{"file": "...", "state": [...], "actions": [...]}}]
  }}
}}""",

    "backend_proc": """你是接口提取器。综合测试场景和源码，提取后端服务的数据处理接口。

{context}

代码:
{files}

输出 JSON:
{{
  "exposed_to_upper": {{
    "routes": [{{"file": "...", "basePath": "...", "handlers": [{{"method": "...", "path": "...", "handler": "...", "request": "...", "response": "..."}}]}}]
  }},
  "exposed_to_peers": {{
    "services": [{{"file": "...", "functions": [{{"name": "...", "params": [...], "returns": "..."}}]}}]
  }}
}}""",

    "_default": """你是接口提取器。综合测试场景和源码，提取对外暴露接口。输出 JSON:
{{"exposed_to_upper": {{...}}, "exposed_to_peers": {{...}}}}

{context}

代码:
{files}""",
}


def _collect_dep_truths(task: dict, task_map: dict, layer_truths: dict) -> str:
    """沿依赖链收集下层真理。"""
    if not layer_truths:
        return ""
    flat = {}
    for _, tasks in layer_truths.items():
        for tid, entry in tasks.items():
            if entry:
                flat[tid] = entry
    visited = set()
    queue = list(task.get("dependencies", []))
    parts = []
    while queue:
        dep_id = queue.pop(0)
        if dep_id in visited:
            continue
        visited.add(dep_id)
        entry = flat.get(dep_id, {})
        if entry.get("_truth"):
            parts.append(entry["_truth"])
        dep_task = task_map.get(dep_id, {})
        for d in dep_task.get("dependencies", []):
            if d not in visited:
                queue.append(d)
    if not parts:
        return ""
    return "\n## 🛑 下层真理 (已通过测试验证)\n" + "\n---\n".join(parts)


def _save_truth(task_id: str, truth_entry: dict):
    fp = TRUTH_DIR_TEST / f"{task_id}.json"
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(truth_entry, indent=2, ensure_ascii=False), "utf-8")


# ═══════════════════════════════════════════════
# 静态检查函数 (从 Python 硬编码辅助 → 逐步替换为 Agent 驱动)
# ═══════════════════════════════════════════════

def _check_env_consistency(ws: Path) -> bool:
    import re
    env_files = [".env", ".env.example", ".env.development", ".env.production"]
    var_sets = {}
    for name in env_files:
        fp = ws / name
        if not fp.exists():
            continue
        keys = set()
        for line in fp.read_text("utf-8").split("\n"):
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                keys.add(s.split("=", 1)[0].strip())
        var_sets[name] = keys
    if len(var_sets) < 2:
        return True
    ref = var_sets.get(".env.example", next(iter(var_sets.values())))
    for name, keys in var_sets.items():
        if keys != ref:
            return False
    return True


def _check_middleware_exports(ws: Path, truth: dict, task_id: str) -> bool:
    """检查中间件文件导出与 truth 声明一致。"""
    all_ok = True
    middleware_files = [
        ("middleware/auth.js", ["authenticate", "optionalAuth"]),
        ("middleware/permission.js", ["hasRole"]),
        ("middleware/errorHandler.js", ["errorHandler"]),
    ]
    for filepath, expected in middleware_files:
        fp = ws / filepath
        if not fp.exists():
            store_bans(task_id, "test_failure", [{"f": f"infra|middleware|{filepath}|MISSING", "b": f"{filepath} 不存在"}])
            all_ok = False
            continue
        content = fp.read_text("utf-8")
        for exp in expected:
            if f"module.exports.{exp}" not in content and f"exports.{exp}" not in content and exp not in content:
                store_bans(task_id, "test_failure", [{"f": f"infra|middleware|{filepath}|EXPORT", "b": f"{filepath} 未导出 {exp}"}])
                all_ok = False
    return all_ok


def _check_response_format(ws: Path, task_id: str) -> bool:
    fp = ws / "utils" / "response.js"
    if not fp.exists():
        return False
    content = fp.read_text("utf-8")
    if "success(res, data" not in content:
        store_bans(task_id, "test_failure", [{"f": "infra|response|format|SIGNATURE", "b": "response.success 签名非 (res, data, message)"}])
        return False
    return True


def _check_config_exports(ws: Path, truth: dict, task_id: str) -> bool:
    fp = ws / "config" / "db.js"
    if not fp.exists():
        return False
    content = fp.read_text("utf-8")
    for exp in ["pool", "query", "beginTransaction", "commit", "rollback"]:
        if exp not in content:
            store_bans(task_id, "test_failure", [{"f": f"infra|config|db.js|EXPORT", "b": f"config/db.js 未导出 {exp}"}])
            return False
    return True


def _check_store_basics(ws: Path, task_id: str) -> bool:
    fp = ws / "src" / "stores" / "user.js"
    if not fp.exists():
        return False
    content = fp.read_text("utf-8")
    if "auth_token" not in content:
        store_bans(task_id, "test_failure", [{"f": "infra|store|user.js|TOKEN_KEY", "b": "user store 未使用 auth_token 作为 localStorage key"}])
        return False
    return True


def _check_seed_data(ws: Path, task_id: str) -> bool:
    fp = ws / "scripts" / "init-db.js"
    if not fp.exists():
        return False
    content = fp.read_text("utf-8")
    if "database" not in content:
        store_bans(task_id, "test_failure", [{"f": "infra|scripts|init-db|PATH", "b": "init-db.js SQL目录不是 database/"}])
        return False
    return True


def _check_ddl_vs_model(ws: Path, task: dict, truth: dict, task_id: str) -> bool:
    """对照 DDL 与 model truth 的列名/类型一致性。"""
    target_files = task.get("targetFiles", [])
    if not target_files or not truth:
        return True  # 无法对照, 交给后续层
    # 简化: 检查 DDL 文件存在且有 CREATE TABLE
    all_ok = True
    for tf in target_files:
        fp = ws / tf
        if not fp.exists():
            store_bans(task_id, "test_failure", [{"f": f"db|ddl|{tf}|MISSING", "b": f"DDL文件不存在: {tf}"}])
            all_ok = False
    return all_ok


def _check_sfc_syntax(ws: Path, task: dict, task_id: str) -> bool:
    import subprocess
    target_files = task.get("targetFiles", [])
    all_ok = True
    for tf in target_files:
        if not tf.endswith(".vue"):
            continue
        fp = ws / tf
        if not fp.exists():
            continue
        # 提取 <script> 块
        content = fp.read_text("utf-8", errors="replace")
        script_match = __import__('re').search(r'<script[^>]*>([\s\S]*?)</script>', content)
        if script_match:
            r = subprocess.run(["node", "--check", "-"], input=script_match.group(1),
                             capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace")
            if r.returncode != 0:
                store_bans(task_id, "test_failure", [{"f": f"frontend_static|sfc|{tf}|syntax", "b": f"SFC语法错误: {(r.stderr or '')[:120]}"}])
                all_ok = False
    return all_ok


def _check_frontend_fields(ws: Path, task: dict, truth: dict, task_id: str) -> bool:
    """简化: 检查 .vue 文件存在性。字段名对照留给后续迭代加强。"""
    target_files = task.get("targetFiles", [])
    all_ok = True
    for tf in target_files:
        if not (ws / tf).exists():
            store_bans(task_id, "test_failure", [{"f": f"frontend_static|file|{tf}|MISSING", "b": f"文件不存在: {tf}"}])
            all_ok = False
    return all_ok


def _check_store_refs(ws: Path, task: dict, truth: dict, task_id: str) -> bool:
    return True  # 简化, 后续迭代加强


def _check_import_paths(ws: Path, task: dict, task_id: str) -> bool:
    import re
    target_files = task.get("targetFiles", [])
    all_ok = True
    for tf in target_files:
        fp = ws / tf
        if not fp.exists():
            continue
        content = fp.read_text("utf-8", errors="replace")
        for m in re.finditer(r"""from\s+['\"]@/([^'\"]+)['\"]""", content):
            resolved = ws / "src" / m.group(1)
            if not resolved.exists():
                for ext in ["", ".js", ".vue", "/index.js"]:
                    if (Path(str(resolved) + ext)).exists():
                        break
                else:
                    store_bans(task_id, "test_failure", [{"f": f"frontend_static|import|{tf}|MISSING", "b": f"import 路径不存在: @/{m.group(1)}"}])
                    all_ok = False
    return all_ok


def _check_named_exports(ws: Path, task: dict, task_id: str) -> bool:
    target_files = task.get("targetFiles", [])
    all_ok = True
    for tf in target_files:
        if "api" not in tf.lower():
            continue
        fp = ws / tf
        if not fp.exists():
            continue
        content = fp.read_text("utf-8", errors="replace")
        if "export default" in content:
            store_bans(task_id, "test_failure", [{"f": f"frontend_static|export|{tf}|DEFAULT", "b": f"{tf} 使用了 export default, 应改为命名导出"}])
            all_ok = False
    return all_ok


def _check_response_unwrap(ws: Path, task: dict, truth: dict, task_id: str) -> bool:
    return True  # 简化, 后续迭代加强


def _check_peer_deps(ws: Path, task: dict, truth: dict, all_truths: dict, task_id: str) -> bool:
    return True  # 简化, 后续迭代加强


# ═══════════════════════════════════════════════
# 基础设施辅助 (保留)
# ═══════════════════════════════════════════════

def _inject_jest_module_name_mapper(ws_path: Path):
    import re, json
    package_json = ws_path / "package.json"
    vite_config = ws_path / "vite.config.js"
    if not package_json.exists() or not vite_config.exists():
        return
    try:
        pkg = json.loads(package_json.read_text("utf-8"))
    except Exception:
        return
    jest_config = pkg.get("jest", {})
    if jest_config.get("moduleNameMapper"):
        return
    vite_src = vite_config.read_text("utf-8")
    aliases = {}
    for m in re.finditer(r"""['\"](@[^'\"]*)['\"]\s*:\s*path\.resolve\(__dirname,\s*['\"]([^'\"]+)['\"]""", vite_src):
        aliases[m.group(1)] = m.group(2)
    if not aliases:
        return
    mapper = {}
    for key, path in aliases.items():
        mapper[f"^{key}/(.*)$"] = f"<rootDir>/{path}/$1"
    pkg.setdefault("jest", {})["moduleNameMapper"] = mapper
    package_json.write_text(json.dumps(pkg, indent=2, ensure_ascii=False) + "\n", "utf-8")


def _ensure_npm_install(ws_path: Path, all_tasks: list):
    import subprocess
    needs = []
    if not (ws_path / "node_modules").exists() or not (ws_path / "node_modules" / "jest").exists():
        needs.append("jest")
    if not (ws_path / "node_modules" / "jest-environment-jsdom").exists():
        needs.append("jest-environment-jsdom")
    if not (ws_path / "node_modules" / "jest-environment-node").exists():
        needs.append("jest-environment-node")
    if needs:
        pkgs = " ".join(needs)
        print(f"[scheduler] 安装缺失包: {pkgs}")
        subprocess.run(f"npm install --save-dev {pkgs} --no-audit --no-fund", shell=True, capture_output=True, text=True,
                      cwd=str(ws_path), timeout=180, encoding="utf-8", errors="replace")


def _check_frontend_test_infra(ws_path: Path, all_tasks: list):
    has_vue = any(any(tf.endswith('.vue') for tf in t.get('targetFiles', [])) for t in all_tasks)
    if not has_vue:
        return
    if not (ws_path / "node_modules" / "@vue" / "vue3-jest").exists():
        import subprocess
        print("[scheduler] 安装 @vue/vue3-jest...")
        subprocess.run("npm install --save-dev @vue/vue3-jest", shell=True, capture_output=True, text=True,
                      cwd=str(ws_path), timeout=120, encoding="utf-8", errors="replace")


def _init_database(ws_path: Path, all_tasks: list):
    has_db = any(t.get("layer") == "db" for t in all_tasks)
    if not has_db:
        return
    import subprocess
    init_script = ws_path / "scripts" / "init-db.js"
    if init_script.exists():
        print("[scheduler] 运行 init-db.js...")
        subprocess.run(f"node {init_script}", shell=True, capture_output=True, text=True,
                      cwd=str(ws_path), timeout=60, encoding="utf-8", errors="replace")


async def _fast_jest_sweep(ws_path: Path):
    import subprocess
    print("[scheduler] Fast mode: running full jest suite...")
    subprocess.run("npx jest --json --forceExit 2>&1", shell=True, capture_output=True, text=True,
                  cwd=str(ws_path), timeout=300, encoding="utf-8", errors="replace")


# ═══════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════

async def main():
    import sys, glob
    ws = sys.argv[1] if len(sys.argv) > 1 else "./work/project"
    pattern = f"{ws}/test/test_tasks_*.json"
    files = sorted(glob.glob(pattern))
    tf = files[-1] if files else f"{ws}/test/test_tasks.json"
    fast = "--fast" in sys.argv

    max_rounds = 10
    prev_passed = 0
    for rnd in range(1, max_rounds + 1):
        r = await run_scheduler(workspace=ws, test_tasks_file=tf, fast=fast)
        if "error" in r:
            print(f"Error: {r['error']}")
            break
        s = r["summary"]
        print(f"\nRound {rnd}: {s['passed']} passed, {s['failed']} failed, {s['blocked']} blocked")
        if s["passed"] == s["total"]:
            print("All passed!")
            break
        if s["passed"] > prev_passed:
            prev_passed = s["passed"]
            continue
        print("No progress. Manual review needed.")
        break


if __name__ == "__main__":
    asyncio.run(main())
