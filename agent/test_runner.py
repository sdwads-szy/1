# agent/test_runner.py
"""
测试运行 Agent —— 精加工层。
B 步骤: 诊断测试失败，产出带指纹的 ban
D 步骤: 验证源码修复，产出带指纹的 ban
"""

import asyncio, json, os, sys, re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from picoagents import Agent
from dotenv import load_dotenv
from Tools.testing import agent_run_test
from Tools.skill.load_skill import load_skill
from Tools.memory.ban_memory import get_bans, format_history_for_runner
from utils.json_extractor import extract_json_dict
from utils.token import wrap_agent_stream

load_dotenv('./.env.example')
ROLE_B_PATH = parent_dir / "skill" / "test" / "roles" / "b_test_runner.md"
ROLE_D_PATH = parent_dir / "skill" / "test" / "roles" / "d_test_runner.md"

_B_ROLE_MAP = {
    "infra": "b_static_diag", "db": "b_static_diag", "frontend_static": "b_static_diag", "peer_deps": "b_static_diag",
    "auth": "b_interface_diag", "api": "b_interface_diag", "db_api": "b_interface_diag", "navigation": "b_interface_diag",
    "backend_proc": "b_logic_diag", "logic": "b_logic_diag", "scenario": "b_logic_diag", "nfr": "b_logic_diag",
}

_D_ROLE_MAP = {
    "infra": "d_static_verify", "db": "d_static_verify", "frontend_static": "d_static_verify", "peer_deps": "d_static_verify",
    "auth": "d_interface_verify", "api": "d_interface_verify", "db_api": "d_interface_verify", "navigation": "d_interface_verify",
    "backend_proc": "d_logic_verify", "logic": "d_logic_verify", "scenario": "d_logic_verify", "nfr": "d_logic_verify",
}

def load_role(step: str = "b", layer: str = "") -> str:
    role_dir = parent_dir / "skill" / "test" / "roles"
    # B步骤: 层专精诊断
    if step == "b":
        role_file = _B_ROLE_MAP.get(layer, "b_static_diag")
        path = role_dir / f"{role_file}.md"
        if path.exists():
            return load_skill(str(path))
    # D步骤: 层专精验证
    if step == "d":
        role_file = _D_ROLE_MAP.get(layer, "d_static_verify")
        path = role_dir / f"{role_file}.md"
        if path.exists():
            return load_skill(str(path))
    return ""


def _build_source_context(src_refs: dict, workspace_root: str) -> str:
    """读取错误位置的源码，附到 prompt 中供 B 准确引用变量名/API。"""
    if not src_refs:
        return ""
    ws = Path(workspace_root).resolve()
    blocks = []
    for file_path, lines in src_refs.items():
        abs_path = Path(file_path) if Path(file_path).is_absolute() else ws / file_path
        if not abs_path.exists():
            continue
        try:
            all_lines = abs_path.read_text("utf-8").split("\n")
        except (UnicodeDecodeError, OSError) as e:
            from utils.logger import log_warning
            log_warning("failed to read source context", file=str(abs_path), error=str(e)[:100])
            continue
        display = str(abs_path.relative_to(ws)).replace("\\", "/") if abs_path.is_relative_to(ws) else str(abs_path)
        blocks.append(f"### 错误位置的源码: {display}")
        for ln in sorted(lines)[:3]:
            start = max(0, ln - 4)
            end = min(len(all_lines), ln + 3)
            blocks.append(f"```")
            for i in range(start, end):
                marker = ">>>" if i + 1 == ln else "   "
                line_text = all_lines[i] if i < len(all_lines) else ""
                blocks.append(f"{marker} {i+1:>4}| {line_text}")
            blocks.append("```")
        if len(lines) > 3:
            blocks.append(f"（还有 {len(lines) - 3} 个错误位置未展示）")
    if blocks:
        blocks.insert(0, "## 错误位置的源码（禁止编造不存在的变量名/API，必须引用下面真实的代码）")
    return "\n".join(blocks)


def _build_test_context(test_file_path: str, workspace_root: str) -> str:
    """读取完整测试文件，供 B 诊断测试自身是否有 mock 问题。"""
    ws = Path(workspace_root).resolve()
    abs_path = Path(test_file_path) if Path(test_file_path).is_absolute() else ws / test_file_path
    if not abs_path.exists():
        return ""
    try:
        content = abs_path.read_text("utf-8")
    except Exception:
        return ""
    lines = content.split("\n")
    blocks = ["## 测试文件完整代码（用于诊断测试自身是否有 mock 问题）"]
    blocks.append(f"### {abs_path.name} ({len(lines)} 行)")
    blocks.append("```")
    for i, line in enumerate(lines):
        blocks.append(f"  {i+1:>4}| {line}")
    blocks.append("```")
    return "\n".join(blocks)


def _build_full_source_section(source_contents: dict) -> str:
    """构建完整源码片段，供 D 诊断 C 的修改是否正确。"""
    if not source_contents:
        return ""
    blocks = ["## 当前源码完整代码（C 修改后的版本，用于判断 C 改对了还是改错了）"]
    for file_name, content in sorted(source_contents.items()):
        lines = content.split("\n") if content else []
        blocks.append(f"### {file_name} ({len(lines)} 行)")
        blocks.append("```")
        for i, line in enumerate(lines):
            blocks.append(f"  {i+1:>4}| {line}")
        blocks.append("```")
    return "\n".join(blocks)


def _detect_test_type(source_contents: dict, layer: str = "") -> str:
    """根据 task.layer 检测测试类型，回退到内容检测。"""
    # 新层名直接映射到诊断文件名
    if layer in ("infra", "db", "frontend_static", "auth", "db_api", "peer_deps",
                 "api", "backend_proc", "navigation", "logic", "scenario", "nfr"):
        return layer
    # 旧层名兼容
    if layer == "repair":
        return "infra"
    # 回退: 内容检测
    all_sources = " ".join(source_contents.keys())
    if ".sql" in all_sources:
        return "db"
    if "middleware/" in all_sources:
        return "infra"
    if ".vue" in all_sources or "src/pages/" in all_sources:
        return "frontend_static"
    if "routes/" in all_sources or "services/" in all_sources:
        return "backend_proc"
    return "infra"


def _load_type_diag(test_type: str) -> str:
    """加载测试类型专属诊断文件（B 步骤）。"""
    diag_dir = Path(__file__).parent.parent / "skill" / "test" / "diagnosis" / "b"
    diag_file = diag_dir / f"{test_type}.md"
    if diag_file.exists():
        content = load_skill(str(diag_file))
        return f"\n## 类型专属诊断（{test_type}）\n{content}\n"
    return ""


def _detect_source_type(source_contents: dict, layer: str = "") -> str:
    """根据 task.layer 检测源码类型（D 步骤），回退到内容检测。"""
    if layer in ("infra", "db", "frontend_static", "auth", "db_api", "peer_deps",
                 "api", "backend_proc", "navigation", "logic", "scenario", "nfr"):
        return layer
    # 回退: 内容检测
    all_sources = " ".join(source_contents.keys())
    if ".vue" in all_sources or "src/pages/" in all_sources:
        return "frontend_static"
    if "services/" in all_sources:
        return "backend_proc"
    if "middleware/" in all_sources:
        return "infra"
    if "routes/" in all_sources:
        return "backend_proc"
    if "config/" in all_sources or "utils/" in all_sources:
        return "infra"
    return "backend_proc"


def _load_source_diag(source_type: str) -> str:
    """加载源码类型专属诊断文件（D 步骤）。"""
    diag_dir = Path(__file__).parent.parent / "skill" / "test" / "diagnosis" / "d"
    diag_file = diag_dir / f"{source_type}.md"
    if diag_file.exists():
        content = load_skill(str(diag_file))
        return f"\n## 源码类型专属诊断（{source_type}）\n{content}\n"
    return ""


# ═══════════════════════════════════════════════════════
# 真理输出 —— B/D 通过后生成结构化真理块
# ═══════════════════════════════════════════════════════

_TRUTH_EXTRACTS = {
    "infra": lambda t: _extract_infra_truth(t),
    "db": lambda t: _extract_db_truth(t),
    "backend": lambda t: _extract_backend_truth(t),
    "frontend": lambda t: _extract_frontend_truth(t),
    "api": lambda t: _extract_api_truth(t),
    "db-api": lambda t: _extract_dbapi_truth(t),
    "navigation": lambda t: _extract_nav_truth(t),
    "auth": lambda t: _extract_auth_truth(t),
    "logic": lambda t: _extract_logic_truth(t),
    "scenario": lambda t: _extract_scenario_truth(t),
    "nfr": lambda t: _extract_nfr_truth(t),
}


def _build_truth(task: dict) -> str:
    """根据任务 layer 构建结构化的真理输出块。"""
    layer = task.get("layer", "")
    extractor = _TRUTH_EXTRACTS.get(layer)
    body = extractor(task) if extractor else ""

    # 附上目标文件路径（同层 C 需要知道 import 的文件在哪）
    target_files = task.get("targetFiles", task.get("path", []))
    if target_files:
        body += f"\n### Target Files:\n" + "\n".join(f"- {f}" for f in target_files) + "\n"

    return body


def _truth_header(t: dict, label: str, consumer: str) -> list:
    tid, desc = t.get("id", ""), t.get("description", "")
    return [
        f"// @truth {tid} — verified interface for: {consumer}",
        f"// {desc}",
        "",
    ]


def _extract_infra_truth(t: dict) -> str:
    lines = _truth_header(t, "INFRA", "all upper layers")
    for s in t.get("testScenarios", []):
        then = s.get("then", "")
        if any(kw in then for kw in ("导出", "返回", "success", "error", "query", "sign", "verify", "encrypt", "PING", "PONG", "端口", "localhost")):
            lines.append(f"// {then}")
    return "\n".join(lines)


def _extract_db_truth(t: dict) -> str:
    lines = _truth_header(t, "DB", "backend SQL alignment")
    for s in t.get("testScenarios", []):
        then = s.get("then", "")
        if any(kw in then for kw in ("字段", "ENUM", "UNIQUE", "FK", "INDEX", "索引", "DEFAULT", "nullable", "NOT NULL", "int", "varchar", "PRIMARY")):
            lines.append(f"// schema: {then}")
    return "\n".join(lines)


def _extract_backend_truth(t: dict) -> str:
    lines = _truth_header(t, "BACKEND", "api route mounting")
    for s in t.get("testScenarios", []):
        then = s.get("then", "")
        if any(kw in then for kw in ("导出", "export", "调用链", "中间件", "req.", "middleware", "步骤", "函数", "签名")):
            lines.append(f"// exports: {then}")
    return "\n".join(lines)


def _extract_frontend_truth(t: dict) -> str:
    lines = _truth_header(t, "FRONTEND", "navigation + api alignment")
    for s in t.get("testScenarios", []):
        then = s.get("then", "")
        if any(kw in then for kw in ("渲染", "router.push", "存在", "exists", "导出", "wrapper", "store", "路由")):
            lines.append(f"// interface: {then}")
    return "\n".join(lines)


def _extract_api_truth(t: dict) -> str:
    lines = _truth_header(t, "API", "logic + auth + scenario callers")
    for s in t.get("testScenarios", []):
        then = s.get("then", "")
        when = s.get("when", "")
        if any(kw in then for kw in ("response.status", "response.body", "res.status", "res.body")) or any(kw in when for kw in ("POST", "GET", "PUT", "DELETE")):
            lines.append(f"// {when} → {then}")
    return "\n".join(lines)


def _extract_dbapi_truth(t: dict) -> str:
    lines = _truth_header(t, "DB-API", "backend DAO callers")
    for s in t.get("testScenarios", []):
        then = s.get("then", "")
        if any(kw in then for kw in ("SQL", "参数", "签名", "乐观锁", "INSERT", "UPDATE", "DELETE", "SELECT")):
            lines.append(f"// signature: {then}")
    return "\n".join(lines)


def _extract_nav_truth(t: dict) -> str:
    lines = _truth_header(t, "NAVIGATION", "scenario flow")
    for s in t.get("testScenarios", []):
        then = s.get("then", "")
        if any(kw in then for kw in ("router.push", "跳转", "路由")):
            lines.append(f"// {then}")
    return "\n".join(lines)


def _extract_auth_truth(t: dict) -> str:
    lines = _truth_header(t, "AUTH", "all authenticated layers")
    for s in t.get("testScenarios", []):
        then = s.get("then", "")
        if any(kw in then for kw in ("payload", "Token", "JWT", "Bearer", "401", "403", "role")):
            lines.append(f"// {then}")
    return "\n".join(lines)


def _extract_logic_truth(t: dict) -> str:
    lines = _truth_header(t, "LOGIC", "scenario orchestration")
    for s in t.get("testScenarios", []):
        then = s.get("then", "")
        if any(kw in then for kw in ("步骤", "链", "事务", "回滚", "补偿", "乐观锁", "重试", "边界", "顺序")):
            lines.append(f"// steps: {then}")
    return "\n".join(lines)


def _extract_scenario_truth(t: dict) -> str:
    lines = _truth_header(t, "SCENARIO", "branch scenarios + NFR")
    produces = t.get("produces", {})
    if produces:
        lines.append(f"// produces: {produces}")
    return "\n".join(lines)


def _extract_nfr_truth(t: dict) -> str:
    lines = _truth_header(t, "NFR", "(top layer, no consumers)")
    return "\n".join(lines)


async def run_test_runner(
    test_file_path: str,
    test_framework: str = "jest",
    workspace_root: str = "./work/project",
    step: str = "b",
    model_client=None,
    task_id: str = "",
    attempt: int = 0,
    bans: list = None,
    source_contents: dict = None,
    save_dir: str = "",
    save_filename: str = "",
    task: dict = None,
) -> Dict[str, Any]:
    t0 = datetime.now()
    root = str(Path(workspace_root).resolve())
    test_path = Path(test_file_path)

    if not test_path.exists():
        return {
            "total": 0, "passed": 0, "failed": 0,
            "error_type": "missing_file", "fix_target": "none",
            "bans": [{"f": "missing_file", "b": "DON'T: 测试文件不存在，需重新生成 | fix: test"}],
            "step": step,
            "raw_output": "", "elapsed": (datetime.now() - t0).total_seconds(),
        }

    raw_result = await agent_run_test(file_path=str(test_path), framework=test_framework, timeout_seconds=120)

    total = raw_result.get("total", 0)
    passed = raw_result.get("passed", 0)
    failed = raw_result.get("failed", 0)

    if total > 0 and failed == 0:
        result = {
            "total": total, "passed": passed, "failed": 0,
            "error_type": "none", "fix_target": "none",
            "bans": [],
            "step": step,
            "elapsed": (datetime.now() - t0).total_seconds(),
        }
        if task:
            truth = _build_truth(task)
            if truth:
                result["truth"] = truth
        return result

    # 从 error 堆栈中提取真实的源文件行号
    _SRC_FILE_RE = re.compile(r'\bat\s+\S+?\s+\(?(.+?\.js):(\d+):(\d+)\)?', re.MULTILINE)

    failures_preview = []
    src_refs: dict[str, set] = {}
    test_file_errors = []  # total=0 时收集测试文件自身的错误，用于诊断
    for f in raw_result.get("failures", [])[:15]:
        err_text = (f.get("error_message", "") or "")[:500]
        src_file, src_line = "", ""
        is_test_error = False
        for m in _SRC_FILE_RE.finditer(err_text):
            fp_match = m.group(1).replace("\\", "/")
            if "node_modules" in fp_match:
                continue
            if "/test/" in fp_match or fp_match.endswith(".test.js") or fp_match.endswith(".spec.js"):
                is_test_error = True
                if total == 0:
                    src_file = fp_match
                    src_line = m.group(2)
                continue
            src_file = fp_match
            src_line = m.group(2)
            break
        # total=0 且无堆栈文件时，从 raw error 中提取测试文件路径
        if total == 0 and not src_file and not is_test_error:
            raw_err_text = raw_result.get("stderr", "") or raw_result.get("error", "") or ""
            test_file_match = re.search(r'(?:in|at|file)\s+(\S+\.test\.\w{2,4})', raw_err_text)
            if test_file_match:
                src_file = test_file_match.group(1)
                is_test_error = True
        if src_file and src_line:
            resolved = str((Path(root) / src_file).resolve()) if not Path(src_file).is_absolute() else src_file
            src_refs.setdefault(resolved, set()).add(int(src_line))
        if is_test_error:
            test_file_errors.append({
                "test_name": f.get("test_name", ""),
                "error_summary": err_text,
                "test_file_path": str(test_file_path),
            })
        resolved_file = str((Path(root) / src_file).resolve()) if (src_file and not Path(src_file).is_absolute()) else src_file
        try:
            display_file = str(Path(resolved_file).relative_to(root)).replace("\\", "/") if resolved_file else ""
        except ValueError:
            display_file = resolved_file.replace("\\", "/") if resolved_file else ""
        failures_preview.append({
            "test_name": f.get("test_name", ""),
            "error_summary": err_text,
            "src_file": resolved_file or "",
            "src_line": src_line,
            "display_file": display_file,
            "is_test_error": is_test_error,
        })

    source_context = _build_source_context(src_refs, root)
    # D 步骤不需要完整测试文件（决策卡聚焦源码），省 token
    test_context = _build_test_context(test_file_path, root) if step == "b" else ""

    by_file: dict[str, list] = {}
    for fp in failures_preview:
        src = fp["display_file"] or fp["src_file"] or "unknown"
        by_file.setdefault(src, []).append(fp)

    grouped = []
    for src, items in by_file.items():
        label = src if src != "unknown" else "未定位到源文件（检查 error 堆栈）"
        grouped.append(f"### 需修复的源文件: {label} ({len(items)} 个失败)")
        for item in items:
            loc = f" (行{item['src_line']})" if item["src_line"] else ""
            grouped.append(f"- [{item['test_name']}]{loc}")
            grouped.append(f"  error: {item['error_summary'][:300]}")

    raw_error_section = ""
    if total == 0:
        raw_error = raw_result.get("stderr", "") or raw_result.get("error", "") or ""
        if raw_error:
            framework_label = test_framework.capitalize()
            raw_error_section = f"\n## {framework_label} 原始错误输出（测试文件加载失败）\n```\n{raw_error[:2000]}\n```"
        # 标记 total=0 时可能有测试文件格式问题
        if test_file_errors:
            raw_error_section += "\n## ⚠️ 测试文件自身加载失败（排查测试文件格式 CJS/ESM 是否正确）\n"
            for te in test_file_errors:
                raw_error_section += f"- {te['error_summary'][:200]}\n"

    # 加载历史 ban 并格式化
    target_memory = "test_failure" if step == "b" else "source_failure"
    history_bans = bans if bans is not None else get_bans(task_id, target_memory)
    history_section = format_history_for_runner(history_bans)

    # B 不需要源码——只从 testScenarios/testFile 诊断测试代码。D 才需要源码验证 C 的修改。
    full_source_section = ""
    type_diag_text = ""
    if step == "d":
        if source_contents:
            full_source_section = _build_full_source_section(source_contents)
            source_type = _detect_source_type(source_contents, layer=(task or {}).get("layer", ""))
            type_diag_text = _load_source_diag(source_type)
    else:
        # B: 用 task.layer 确定诊断类型，不依赖源码内容
        test_layer = (task or {}).get("layer", "")
        if test_layer:
            type_diag_text = _load_type_diag(test_layer)

    layer = (task or {}).get("layer", "")
    instructions = f"""{load_role(step, layer=layer)}

{type_diag_text}
## 工作区: {root}
"""

    step_desc = { "b": "首次测试——只判测试代码质量，不看源码", "d": "C 修复后的验证——判 C 的修改是否有效" }
    # B: 只看测试文件+失败详情; D: 看源码+失败详情
    extra_sections = f"{full_source_section}\n{source_context}" if step == "d" else test_context
    user_prompt = f"""
## 当前步骤: {step} ({step_desc.get(step, "")})

## 测试摘要
- 文件: {test_file_path}  |  用例: {total} 通过/{passed} 失败/{failed}
{raw_error_section}
{history_section}
{extra_sections}
## 失败详情
{chr(10).join(grouped) if grouped else "（见上方 error）"}
"""

    if model_client is None:
        from utils.model_client import get_model_client
        model_client = get_model_client()
    model = model_client

    # B 的测试侧诊断干净 → 调用此工具加载源码 + 层专精 D 角色，转为源码诊断
    async def load_d_card():
        """转为 D 模式：加载层专精 D 角色 + 源码 + diagnosis/d/{layer}.md。"""
        parts = []
        # 加载层专精 D 角色 (d_static_verify / d_interface_verify / d_logic_verify)
        test_layer = (task or {}).get("layer", "")
        d_role_file = _D_ROLE_MAP.get(test_layer, "d_static_verify")
        role_d = parent_dir / "skill" / "test" / "roles" / f"{d_role_file}.md"
        if role_d.exists():
            parts.append(load_skill(str(role_d)))
        # 加载源码 + D 诊断
        if source_contents:
            parts.append(_build_full_source_section(source_contents))
            s_type = _detect_source_type(source_contents, layer=test_layer)
            diag = _load_source_diag(s_type)
            if diag:
                parts.append(diag)
        return "\n".join(parts) if parts else ""

    agent = Agent(
        name=f"test_runner_{test_path.stem}_{step}",
        description="测试结果精加工工程师",
        instructions=instructions,
        model_client=model,
        tools=[load_d_card] if step == "b" else [],
        max_iterations=2,
    )

    collected = []
    try:
        async for event in wrap_agent_stream(
            agent, user_prompt, "test_runner",
            model=model.model, task_id=task_id or "runner",
            save_dir=save_dir, save_filename=save_filename,
        ):
            collected.append(str(event))
    except Exception as e:
        return _fallback_result(raw_result, step, t0, str(e), "\n".join(collected))

    full_text = "\n".join(collected)
    llm_output = extract_json_dict(full_text)
    if llm_output is None:
        result = _fallback_result(raw_result, step, t0, "JSON parse failed")
        result["raw_output"] = full_text
        return result

    fix_target = llm_output.get("fix_target", "test")

    # 提取 bans（新格式优先 bans 数组，兼容旧格式单 ban）
    bans_raw = llm_output.get("bans", None)
    if bans_raw and isinstance(bans_raw, list):
        bans = bans_raw
    else:
        # 兼容旧格式：单 ban → 包装为数组
        ban_raw = llm_output.get("ban", "")
        if isinstance(ban_raw, dict):
            bans = [ban_raw]
        elif isinstance(ban_raw, str) and ban_raw.strip():
            bans = [{"f": "", "b": ban_raw.strip()}]
        else:
            bans = []

    return {
        "total": raw_result.get("total", 0),
        "passed": raw_result.get("passed", 0),
        "failed": raw_result.get("failed", 0),
        "error_type": llm_output.get("error_type", raw_result.get("error_type", "test_bug")),
        "fix_target": fix_target,
        "bans": bans,
        "step": step,
        "raw_output": full_text,
        "elapsed": (datetime.now() - t0).total_seconds(),
    }


def _fallback_result(raw_result: dict, step: str, t0, reason: str, raw_output: str = "") -> dict:
    total = raw_result.get("total", 0)
    failed = raw_result.get("failed", 0)
    if total > 0 and failed == 0:
        return {
            "total": total, "passed": raw_result.get("passed", 0), "failed": 0,
            "error_type": "none", "fix_target": "none",
            "bans": [],
            "step": step,
            "raw_output": raw_output, "elapsed": (datetime.now() - t0).total_seconds(),
        }
    # total==0: 测试文件损坏，需修测试
    # total>0 && failed>0: 测试能跑但有失败，LLM 未产出分析 → 保守判定源码问题
    fix_target = "test" if total == 0 else "source"
    error_type = raw_result.get("error_type", "test_bug")
    return {
        "total": total, "passed": raw_result.get("passed", 0), "failed": failed,
        "error_type": error_type, "fix_target": fix_target,
        "bans": [{"f": "fallback", "b": f"LLM JSON parse failed ({reason[:100]}). total={total} failed={failed}"}],
        "step": step,
        "raw_output": raw_output, "elapsed": (datetime.now() - t0).total_seconds(),
    }
