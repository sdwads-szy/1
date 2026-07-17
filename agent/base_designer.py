# agent/base_designer.py
"""
设计器基类 — 消除 backend/frontend/database/infrastructure designer 的重复代码。
"""

# ═══════════════════════════════════════════════════════
# SECTION 1: 导入
# ═══════════════════════════════════════════════════════

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from picoagents import Agent

current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from Tools.coding.create_files import create_files as _create_files
from Tools.coding.edit_lines import edit_batch as _edit_batch
from Tools.coding.quick_check import quick_check as _quick_check
from utils.token import wrap_agent_stream
from utils.logger import log_warning, log_error
from utils.model_client import get_model_client
from agent.prompt_builder import build_system_prompt, build_user_prompt, _format_nfr

load_dotenv("./.env.example")
model_client = get_model_client()


# ═══════════════════════════════════════════════════════
# SECTION 2: 常量
# ═══════════════════════════════════════════════════════

_DESCRIPTIONS = {
    "infra":    "基础设施工程师",
    "db":       "数据库设计师",
    "backend":  "后端开发工程师（Node.js + Express + MySQL）",
    "frontend": "前端开发工程师（Vue 3 + Vite + Pinia）",
}


def _calc_iterations(task: dict, agent_type: str) -> int:
    return 7 if agent_type == "integration" else 6


# ═══════════════════════════════════════════════════════
# SECTION 3: BaseDesigner
# ═══════════════════════════════════════════════════════

class BaseDesigner:
    """通用设计器 — 封装 Agent 创建/流处理/重试/日志等公共逻辑。"""

    def __init__(self, agent_type: str, description: str = ""):
        self.agent_type = agent_type
        self.description = description or _DESCRIPTIONS.get(agent_type, f"{agent_type}工程师")

    @staticmethod
    def _tid(task: dict) -> str:
        return task.get("taskId") or task.get("id", f"unknown_{task.get('type', 'task')}")

    def _get_target_files(self, task: dict) -> List[str]:
        return task.get("path") or task.get("outputFiles") or task.get("files") or []

    def _build_result(self, task: dict, workspace_path: Path,
                      target_files: List[str], extra: dict = None) -> dict:
        """校验：真理文件 + 产出文件存在且非空。"""
        tid = self._tid(task)
        truth_dir = parent_dir / "Memory" / "truths" / "engineer"
        errors = []

        truth_path = truth_dir / f"{tid}.json"
        if not truth_path.exists() or truth_path.stat().st_size == 0:
            errors.append("真理文件缺失或为空")

        if target_files:
            missing = [f for f in target_files
                       if not (workspace_path / f).exists() or (workspace_path / f).stat().st_size == 0]
            if missing:
                errors.append(f"文件缺失: {', '.join(missing[:5])}")
        else:
            errors.append("无 target_files")

        success = len(errors) == 0
        error = "; ".join(errors[:3]) if errors else None
        result = {"task_id": tid, "success": success, "error": error}
        if extra:
            result.update(extra)
        return result

    # ── 主流程 ──

    async def run(self, task: dict, workspace_root: str = "./project",
                  relevant_contracts: list = None,
                  extra_instructions: str = "") -> dict:
        tid = self._tid(task)
        workspace_path = Path(workspace_root).resolve()
        workspace_path.mkdir(parents=True, exist_ok=True)
        abs_workspace = str(workspace_path).replace("\\", "/")
        (workspace_path / ".meta").mkdir(exist_ok=True)
        (parent_dir / "Memory" / "truths" / "engineer").mkdir(parents=True, exist_ok=True)

        target_files = self._get_target_files(task)

        # ── 工具函数 ──
        step1_open = True
        _file_tool_calls = [0]  # create_files + edit_files 合计计数，超限强制 Step 4

        def _close_step1():
            nonlocal step1_open
            step1_open = False

        def _check_step1(tool_name: str):
            if not step1_open:
                return {"ok": False,
                        "error": f"Step 1 已关闭——{tool_name} 必须在进入创建/编辑步骤之前调用",
                        "🛑_NEXT": "搜索已完成。现在必须调用 create_files 或 edit_files！"}
            return None

        search_rag = _make_search_rag(tid, _check_step1)
        search_code = _make_search_code(tid, _check_step1)
        create_files = _make_create_files_wrapper(
            target_files, abs_workspace, workspace_path, _close_step1, _file_tool_calls)
        edit_files = _make_edit_files_wrapper(
            target_files, abs_workspace, workspace_path, _close_step1, _file_tool_calls)

        tools = [create_files, edit_files, search_rag, search_code]

        # ── 提示词 ──
        nfr_extra = ""
        task_nfr = task.get("nfr", None)
        if task_nfr:
            nfr_extra = _format_nfr(task_nfr, self.agent_type)
            if nfr_extra:
                extra_instructions = (extra_instructions or "") + nfr_extra

        instructions = build_system_prompt(self.agent_type, abs_workspace, extra_instructions, task=task)
        user_prompt = build_user_prompt(task, relevant_contracts, self.agent_type)

        # ── 日志目录 ──
        agent_log_dir = parent_dir / "Memory" / "agent_logs" / "engineer" / tid
        agent_log_dir.mkdir(parents=True, exist_ok=True)

        # ── Agent 执行 ──
        max_iter = _calc_iterations(task, self.agent_type)
        agent = Agent(
            name=f"{self.agent_type}_worker_{tid}",
            description=self.description,
            instructions=instructions,
            model_client=model_client,
            tools=tools,
            max_iterations=max_iter,
        )

        collected_messages = await self._stream_agent(
            agent, user_prompt, tid, agent_log_dir, f"{self.agent_type}_token"
        )
        full_text = "".join(collected_messages)

        # API 错误重试
        if _is_api_error(full_text):
            log_warning("API error detected, retrying", agent=self.agent_type, task=tid)
            agent2 = Agent(name=f"{self.agent_type}_worker_{tid}_rty", description=self.description,
                          instructions=instructions, model_client=model_client, tools=tools,
                          max_iterations=max_iter)
            collected_messages = await self._stream_agent(
                agent2, user_prompt, tid, agent_log_dir, f"{self.agent_type}_token_retry"
            )

        # ── 保存 + 提取真理 ──
        full_output = "\n".join(collected_messages)
        (agent_log_dir / f"{self.agent_type}_raw.md").write_text(full_output, encoding="utf-8")

        interface = _extract_truth_from_response(full_output, tid, agent_log_dir)
        if interface:
            _save_truth_to_root(tid, self.agent_type, task, interface)

        return self._build_result(task, workspace_path, target_files,
                                   extra={"interface": interface or {}})

    async def _stream_agent(self, agent, user_prompt, tid, log_dir, filename) -> List[str]:
        from picoagents.types import ErrorEvent, FatalErrorEvent
        collected = []
        try:
            async for event in wrap_agent_stream(
                agent, user_prompt, self.agent_type,
                model=model_client.model, task_id=tid,
                save_dir=str(log_dir), save_filename=filename,
            ):
                if isinstance(event, ErrorEvent):
                    collected.append(f"[ERROR] {event.error_type}: {event.error_message}")
                elif isinstance(event, FatalErrorEvent):
                    collected.append(f"[FATAL] {event.error_type}: {event.error_message}")
                else:
                    collected.append(str(event))
        except Exception as e:
            log_error("agent stream failed", exc_info=True,
                      agent=self.agent_type, task=tid, error=str(e)[:200])
        return collected


# ═══════════════════════════════════════════════════════
# SECTION 4: 工具包装器
# ═══════════════════════════════════════════════════════

def _make_search_rag(tid: str, _check_step1):
    from Tools.rag.search_rag import make_search_rag
    _raw = make_search_rag(tid, "code_generator")
    _round = 0
    _called = False

    async def search_rag(query: str):
        nonlocal _round, _called
        reject = _check_step1("search_rag")
        if reject:
            return reject
        if _called:
            _round += 1
        _called = True
        if _round > 0:
            return {"ok": False, "error": "搜索已调用过，不允许重复搜索",
                    "🛑_NEXT": "搜索已完成。现在必须调用 create_files 创建 outputFiles 中的所有文件！"}
        try:
            r = await _raw(query)
        except Exception as e:
            r = {"ok": False, "error": str(e)[:200]}
        r["🛑_NEXT"] = "检索完成 → 立即调用 create_files 创建 outputFiles 中的所有文件（禁止再次搜索！）"
        return r
    return search_rag


def _make_search_code(tid: str, _check_step1):
    from Tools.rag.search_code import make_search_code
    _raw = make_search_code(tid)
    _round = 0
    _called = False

    async def search_code(query: str):
        nonlocal _round, _called
        reject = _check_step1("search_code")
        if reject:
            return reject
        if _called:
            _round += 1
        _called = True
        if _round > 0:
            return {"ok": False, "error": "搜索已调用过，不允许重复搜索",
                    "🛑_NEXT": "搜索已完成。现在必须调用 create_files 创建 outputFiles 中的所有文件！"}
        try:
            r = await _raw(query)
        except Exception as e:
            r = {"ok": False, "error": str(e)[:200]}
        r["🛑_NEXT"] = "检索完成 → 立即调用 create_files 创建 outputFiles 中的所有文件（禁止再次搜索！）"
        return r
    return search_code


def _make_create_files_wrapper(target_files: list, abs_workspace: str,
                                workspace_path: Path, _close_step1,
                                _file_tool_calls: list = None):
    _allowed = set(tf.replace("\\", "/") for tf in target_files)
    MAX_FILE_CALLS = 2  # create + edit 合计上限，超限直接失败

    async def create_files(files, metadata=None):
        _close_step1()
        if _file_tool_calls:
            _file_tool_calls[0] += 1
        force_step4 = _file_tool_calls and _file_tool_calls[0] >= MAX_FILE_CALLS

        if isinstance(files, list):
            for f in files:
                if isinstance(f, str):
                    p = f
                elif isinstance(f, dict):
                    p = f.get("path", f.get("file", ""))
                else:
                    continue
                p = p.replace("\\", "/")
                ws_prefix = abs_workspace.replace("\\", "/") + "/"
                if p.startswith(ws_prefix):
                    p = p[len(ws_prefix):]
                for prefix in ("work/project/", "project/"):
                    if p.startswith(prefix):
                        p = p[len(prefix):]
                        break
                if isinstance(f, dict):
                    f["path"] = p
                if p not in _allowed:
                        return {
                            "error": f"禁止创建 '{p}' — 不在 outputFiles 白名单中",
                            "allowed": sorted(_allowed),
                            "🛑_NEXT": f"只创建 outputFiles 中的文件: {sorted(_allowed)}"
                        }
        result = await _create_files(files, overwrite=True, workspace=abs_workspace, metadata=metadata)
        created = [f["path"] if isinstance(f, dict) else f for f in files] if isinstance(files, list) else []
        if created:
            try:
                qc = await _quick_check(created, workspace=abs_workspace)
                result["quick_check"] = qc
            except Exception:
                pass
        still_missing = [tf for tf in target_files
                         if not (workspace_path / tf).exists() or (workspace_path / tf).stat().st_size == 0]
        if still_missing:
            result["missing"] = still_missing
        qc_ok = result.get("quick_check", {}).get("ok", True)
        if force_step4 and still_missing:
            result["🛑_NEXT"] = f"已达修改上限（{_file_tool_calls[0]}/{MAX_FILE_CALLS}次）且文件缺失 → 任务失败，不要输出真理"
        elif force_step4:
            result["🛑_NEXT"] = f"已达修改上限（{_file_tool_calls[0]}/{MAX_FILE_CALLS}次）→ 文件已落盘，输出真理 JSON"
        elif still_missing:
            result["🛑_NEXT"] = f"还有 {len(still_missing)} 个文件未创建 → 调用 create_files 补建: {still_missing}"
        elif qc_ok:
            result["🛑_NEXT"] = "全部完成！按照 user prompt 中的真理格式输出 JSON（不要任何其他文字）"
        else:
            qc_issues = result.get("quick_check", {}).get("issues", [])
            qc_summary = "; ".join(f"{i['file']}:{i['line']} {i['msg']}" for i in qc_issues[:3])
            result["🛑_NEXT"] = f"文件已落盘但有语法问题 → 调用 edit_files **修 1 次**（仅 1 次！）: {qc_summary}"
        return result
    return create_files


def _make_edit_files_wrapper(target_files: list, abs_workspace: str,
                              workspace_path: Path, _close_step1,
                              _file_tool_calls: list = None):
    MAX_FILE_CALLS = 2

    async def edit_files(edits):
        _close_step1()
        if _file_tool_calls:
            _file_tool_calls[0] += 1
        force_step4 = _file_tool_calls and _file_tool_calls[0] >= MAX_FILE_CALLS

        result = await _edit_batch(edits, workspace=abs_workspace)
        if isinstance(edits, list) and edits:
            edited_paths = [e.get("path", e.get("file", "")) for e in edits if isinstance(e, dict)]
            if edited_paths:
                try:
                    qc = await _quick_check(edited_paths, workspace=abs_workspace)
                    result["quick_check"] = qc
                except Exception:
                    pass
        still_missing = [tf for tf in target_files
                         if not (workspace_path / tf).exists() or (workspace_path / tf).stat().st_size == 0]
        qc_ok = result.get("quick_check", {}).get("ok", True)
        if force_step4 and still_missing:
            result["🛑_NEXT"] = f"已达修改上限（{_file_tool_calls[0]}/{MAX_FILE_CALLS}次）且文件缺失 → 任务失败，不要输出真理"
        elif force_step4:
            result["🛑_NEXT"] = f"已达修改上限（{_file_tool_calls[0]}/{MAX_FILE_CALLS}次）→ 文件已落盘，输出真理 JSON"
        elif still_missing:
            result["🛑_NEXT"] = f"还有文件缺失: {still_missing} → 调用 create_files 补建"
        elif qc_ok:
            result["🛑_NEXT"] = "全部完成！按照 user prompt 中的真理格式输出 JSON（不要任何其他文字）"
        else:
            result["🛑_NEXT"] = "语法有提示但文件已落盘 → 输出真理 JSON 即可（测试阶段会修复语法问题）"
        return result
    return edit_files


# ═══════════════════════════════════════════════════════
# SECTION 5: 真理提取与保存
# ═══════════════════════════════════════════════════════

def _extract_truth_from_response(full_output: str, tid: str, log_dir: Path) -> dict:
    """从 Agent 最终响应中提取真理 JSON。"""
    import re as _re

    # 策略 1: 最后的 ```json 块
    json_blocks = list(_re.finditer(r'```(?:json)?\s*([\s\S]*?)```', full_output))
    if json_blocks:
        last = json_blocks[-1].group(1).strip()
        try:
            parsed = json.loads(last)
            if isinstance(parsed, dict) and "exposed" in parsed:
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

    # 策略 2: 反向扫描找含 exposed 的 {...}
    for marker in ('"exposed"', '"task_id"'):
        idx = full_output.rfind(marker)
        if idx < 0:
            continue
        depth = 0
        start = -1
        for i in range(idx, -1, -1):
            if full_output[i] == '}':
                depth += 1
            elif full_output[i] == '{':
                if depth == 0:
                    start = i; break
                depth -= 1
        if start < 0:
            continue
        depth = 0
        end = -1
        for i in range(start, len(full_output)):
            if full_output[i] == '{':
                depth += 1
            elif full_output[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i; break
        if end < 0:
            continue
        try:
            obj = json.loads(full_output[start:end + 1])
            if isinstance(obj, dict) and "exposed" in obj and "task_id" in obj:
                return obj
        except (json.JSONDecodeError, TypeError):
            continue

    return None


def _is_api_error(text: str) -> bool:
    """检测 LLM API 层 JSON 错误（非 Agent 行为错误）。"""
    markers = ("Invalid \\escape", "Invalid \\u", "Extra data:", "I encountered an error")
    return any(m in text for m in markers) and "create_files" not in text


def _save_truth_to_root(tid: str, agent_type: str, task: dict, truth: dict):
    """将 Agent 输出的真理保存到项目根 Memory/truths/engineer/。"""
    truth_dir = Path(__file__).parent.parent / "Memory" / "truths" / "engineer"
    truth_dir.mkdir(parents=True, exist_ok=True)

    if "task_id" not in truth:
        truth["task_id"] = tid
    if "type" not in truth:
        truth["type"] = agent_type
    if "output_files" not in truth:
        truth["output_files"] = task.get("outputFiles") or task.get("files") or []
    if "description" not in truth:
        truth["description"] = task.get("description", "")

    (truth_dir / f"{tid}.json").write_text(
        json.dumps(truth, indent=2, ensure_ascii=False), "utf-8")


# ═══════════════════════════════════════════════════════
# SECTION 6: 子类（Infra / Database Designer）
# ═══════════════════════════════════════════════════════

_SYSTEM_ENV_EXAMPLE = parent_dir / ".env.example"


def _load_env_template() -> str:
    if not _SYSTEM_ENV_EXAMPLE.exists():
        return ""
    lines = []
    for line in _SYSTEM_ENV_EXAMPLE.read_text("utf-8").strip().split("\n"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            lines.append(s)
    return "\n".join(lines) if lines else ""


class InfraDesigner(BaseDesigner):
    """基础设施工程师 — .env 模板注入。"""

    def __init__(self):
        super().__init__(agent_type="infra", description="基础设施工程师")

    async def run(self, task, workspace_root="./project",
                  relevant_contracts=None, extra_instructions="") -> dict:
        env_template = _load_env_template()
        env_extra = ""
        if env_template:
            env_extra = f"\n## 环境变量模板（从项目根 .env.example 读取）\n```\n{env_template}\n```\n"
        arch = task.get("envConstraints", {})
        if arch:
            effective = {k: v for k, v in arch.items() if v not in ("", None)}
            if effective:
                env_extra += "\n## env 约束\n" + "\n".join(f"- {k}: {v}" for k, v in effective.items())
        return await super().run(task, workspace_root=workspace_root,
                                 relevant_contracts=relevant_contracts,
                                 extra_instructions=env_extra + (extra_instructions or ""))


class DatabaseDesigner(BaseDesigner):
    """数据库设计师 — 确保输出目录存在。"""

    def __init__(self):
        super().__init__(agent_type="db", description="数据库设计师")

    def _build_result(self, task, workspace_path, target_files, extra=None):
        result = super()._build_result(task, workspace_path, target_files, extra=extra)
        sql_files = [f for f in target_files if f.endswith(".sql")]
        if sql_files:
            missing = [f for f in sql_files if not (workspace_path / f).exists()]
            if missing:
                result["success"] = False
                result["error"] = f"SQL files not found: {', '.join(missing)}"
        return result

    async def run(self, task, workspace_root="./project",
                  relevant_contracts=None, extra_instructions="") -> dict:
        workspace_path = Path(workspace_root).resolve()
        for tf in self._get_target_files(task):
            (workspace_path / tf).parent.mkdir(parents=True, exist_ok=True)
        return await super().run(task, workspace_root=workspace_root,
                                 relevant_contracts=relevant_contracts,
                                 extra_instructions=extra_instructions)


# ═══════════════════════════════════════════════════════
# SECTION 7: 入口函数（供 engineer.py 调用）
# ═══════════════════════════════════════════════════════

_infra = InfraDesigner()
_db = DatabaseDesigner()
_backend = BaseDesigner(agent_type="backend", description="后端开发工程师（Node.js + Express + MySQL）")
_frontend = BaseDesigner(agent_type="frontend", description="前端开发工程师（Vue 3 + Vite + Pinia）")


async def run_infrastructure_task(task: dict, workspace_root: str = "./project",
                                  extra_instructions: str = "") -> dict:
    return await _infra.run(task, workspace_root=workspace_root, extra_instructions=extra_instructions)


async def run_database_task(task: dict, workspace_root: str = "./project",
                            relevant_contracts: list = None, extra_instructions: str = "") -> dict:
    return await _db.run(task, workspace_root=workspace_root,
                         relevant_contracts=relevant_contracts, extra_instructions=extra_instructions)


async def run_backend_task(task: dict, workspace_root: str = "./project",
                           relevant_contracts: list = None, extra_instructions: str = "") -> dict:
    return await _backend.run(task, workspace_root=workspace_root,
                              relevant_contracts=relevant_contracts, extra_instructions=extra_instructions)


async def run_frontend_task(task: dict, workspace_root: str = "./project",
                            relevant_contracts: list = None, extra_instructions: str = "") -> dict:
    return await _frontend.run(task, workspace_root=workspace_root,
                               relevant_contracts=relevant_contracts, extra_instructions=extra_instructions)
