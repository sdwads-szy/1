# agent/test_runner.py
"""
测试运行 Agent —— B 步骤(诊断测试失败) / D 步骤(验证源码修复)。
核心: 跑测试 → 解析结果 → 加载 skill → agent 诊断 → 提取 ban(failed) 或 truth(passed)
"""

import sys, re, json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
project_root = parent_dir
sys.path.insert(0, str(parent_dir))

from picoagents import Agent
from dotenv import load_dotenv
from Tools.testing import agent_run_test
from Tools.skill.load_skill import load_skill
from Tools.memory.ban_memory import get_bans, format_history_for_runner
from utils.json_extractor import extract_json_dict
from utils.token import wrap_agent_stream

load_dotenv('./.env.example')

# 从 Jest error 堆栈提取源文件:行号
_SRC_FILE_RE = re.compile(r'\bat\s+\S+?\s+\(?(.+?\.(?:js|ts|vue|sql)):(\d+):(\d+)\)?', re.MULTILINE)


# ═══════════════════════════════════════════════
# Skill 加载
# ═══════════════════════════════════════════════

def load_role(step: str = "b", layer: str = "") -> str:
    """加载诊断角色：通用文件 + 子层特化文件。step='b'→B角色，step='d'→D角色。"""
    if not layer:
        return ""
    from utils.dependency_graph import _LAYER_TO_TYPE
    test_type = _LAYER_TO_TYPE.get(layer, "logic")
    role_dir = parent_dir / "skill" / "test" / "diagnosis" / step
    parts = []
    common = role_dir / f"{test_type}.md"
    if common.exists():
        parts.append(load_skill(str(common)))
    specific = role_dir / test_type / f"{layer}.md"
    if specific.exists():
        parts.append(load_skill(str(specific)))
    return "\n\n".join(parts) if parts else ""


# ═══════════════════════════════════════════════
# 上下文构建
# ═══════════════════════════════════════════════

def _build_source_context(src_refs: dict, workspace_root: str) -> str:
    """错误位置的源码片段（附行号），供 agent 准确引用变量名/API。"""
    if not src_refs:
        return ""
    ws = Path(workspace_root).resolve()
    blocks = ["## 错误位置的源码（禁止编造不存在的变量名/API，必须引用下面真实的代码）"]
    for file_path, lines in src_refs.items():
        abs_path = Path(file_path) if Path(file_path).is_absolute() else ws / file_path
        if not abs_path.exists():
            continue
        try:
            all_lines = abs_path.read_text("utf-8").split("\n")
        except Exception:
            continue
        display = str(abs_path.relative_to(ws)).replace("\\", "/") if abs_path.is_relative_to(ws) else str(abs_path)
        blocks.append(f"### {display}")
        for ln in sorted(lines)[:3]:
            start, end = max(0, ln - 4), min(len(all_lines), ln + 3)
            blocks.append("```")
            for i in range(start, end):
                marker = ">>>" if i + 1 == ln else "   "
                blocks.append(f"{marker} {i+1:>4}| {all_lines[i]}")
            blocks.append("```")
        if len(lines) > 3:
            blocks.append(f"（还有 {len(lines) - 3} 个错误位置未展示）")
    return "\n".join(blocks)


def _build_test_file_context(test_file_path: str, workspace_root: str) -> str:
    """完整测试文件（B 步骤用——诊断测试自身 mock/断言是否正确）。"""
    ws = Path(workspace_root).resolve()
    abs_path = Path(test_file_path) if Path(test_file_path).is_absolute() else ws / test_file_path
    if not abs_path.exists():
        return ""
    try:
        lines = abs_path.read_text("utf-8").split("\n")
    except Exception:
        return ""
    blocks = ["## 测试文件完整代码（用于诊断测试自身是否有 mock 问题）", f"### {abs_path.name} ({len(lines)} 行)", "```"]
    for i, line in enumerate(lines):
        blocks.append(f"  {i+1:>4}| {line}")
    blocks.append("```")
    return "\n".join(blocks)


def _build_full_source_section(source_contents: dict) -> str:
    """C 修改后的完整源码（D 步骤用——判断 C 改对了还是改错了）。"""
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


# ═══════════════════════════════════════════════
# Ban / Truth 提取（对齐 source_fixer.py 的 <!--FINAL--> 标记解析）
# ═══════════════════════════════════════════════

def _extract_structured(text: str) -> tuple:
    """从 Agent 响应提取真理或 ban。从尾部搜索，避免 skill 模板中的 <!--FINAL--> 干扰。
    Returns: (truth_dict|None, bans_list|None)
    """

    def _try_parse(json_str: str):
        try: return json.loads(json_str)
        except Exception: return None

    def _valid(data) -> bool:
        """过滤空数组/空对象的误匹配。"""
        return isinstance(data, dict) or (isinstance(data, list) and len(data) > 0)

    # ── 从尾部找最后一个 <!--FINAL--> 对，避免 skill 文件中的示例标记干扰 ──
    tail = text
    all_starts = [m.start() for m in re.finditer(r'<!--FINAL-->', text)]
    if len(all_starts) >= 2:
        tail = text[all_starts[-2]:]
    elif len(all_starts) == 1:
        tail = text[all_starts[0]:]

    # 1. 双标记 <!--FINAL-->[...]<!--FINAL--> 或 <!--FINAL-->{...}<!--FINAL-->
    for m in re.finditer(r'<!--FINAL-->\s*(\[.*?\]|\{.*?\})\s*<!--FINAL-->', tail, re.DOTALL):
        data = _try_parse(m.group(1))
        if _valid(data):
            return (None, data) if isinstance(data, list) else (data, None)

    # 2. 单标记 + 括号深度追踪
    for m2 in re.finditer(r'<!--FINAL-->\s*([\[\{])', tail):
        start = m2.end() - 1
        depth, i = 0, start
        while i < len(tail):
            ch = tail[i]
            if ch in '[{': depth += 1
            elif ch in ']}': depth -= 1
            if depth == 0:
                data = _try_parse(tail[start:i+1])
                if _valid(data):
                    return (None, data) if isinstance(data, list) else (data, None)
                break
            i += 1

    # 3. 双标记之间全文搜索 JSON
    for m3 in re.finditer(r'<!--FINAL-->(.*?)<!--FINAL-->', tail, re.DOTALL):
        inner = m3.group(1).strip()
        data = _try_parse(inner)
        if _valid(data):
            return (None, data) if isinstance(data, list) else (data, None)
        last_valid = None
        for sub_m in re.finditer(r'(\[.*?\]|\{.*?\})', inner, re.DOTALL):
            data = _try_parse(sub_m.group(1))
            if _valid(data):
                last_valid = data
        if last_valid is not None:
            return (None, last_valid) if isinstance(last_valid, list) else (last_valid, None)

    return None, None


def _extract_bans_from_text(raw_text: str) -> list:
    """从 LLM 文本中提取 f=... / b=... 格式的 ban（最终回退）。"""
    bans = []
    seen = set()
    for fm in re.finditer(r'[fF]\s*=\s*(.+?)\s*\|\s*[bB]\s*=\s*(.+?)(?:\n|$)', raw_text):
        f_val = fm.group(1).strip()
        b_val = fm.group(2).strip()
        key = (f_val, b_val)
        if key not in seen:
            seen.add(key)
            bans.append({"f": f_val, "b": b_val})
    return bans


def _fallback_result(raw_result: dict, step: str, t0, reason: str, raw_output: str = "") -> dict:
    """LLM 产出不可用时构造回退结果。total>0 && failed=0 视为通过，否则保守判定。"""
    total = raw_result.get("total", 0)
    failed = raw_result.get("failed", 0)
    if total > 0 and failed == 0:
        return {"total": total, "passed": raw_result.get("passed", 0), "failed": 0,
                "error_type": "none", "fix_target": "none", "bans": [], "step": step,
                "raw_output": raw_output, "elapsed": (datetime.now() - t0).total_seconds()}
    fix_target = "test" if total == 0 else "source"
    return {"total": total, "passed": raw_result.get("passed", 0), "failed": failed,
            "error_type": raw_result.get("error_type", "test_bug"), "fix_target": fix_target,
            "bans": [{"f": f"{raw_result.get('error_type', 'unknown')}|{fix_target}|fallback|{total}t{failed}f",
                      "b": f"DON'T: 测试失败 total={total} failed={failed} | B诊断: 测试代码问题→改测试, 源码问题→加载源码修源码 | 失败详情: {json.dumps(raw_result.get('diagnosis', raw_result.get('failures', [])), ensure_ascii=False)[:500]} | target={fix_target}"}],
            "step": step, "raw_output": raw_output, "elapsed": (datetime.now() - t0).total_seconds()}


# ═══════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════

async def run_test_runner(
    test_file_path: str,
    test_framework: str = "jest",
    workspace_root: str = "./work/project",
    step: str = "b",
    model_client=None,
    task_id: str = "",
    bans: list = None,
    source_contents: dict = None,
    save_dir: str = "",
    save_filename: str = "",
    task: dict = None,
    extra_context: str = "",
) -> Dict[str, Any]:
    t0 = datetime.now()
    root = str(Path(workspace_root).resolve())
    test_path = Path(test_file_path)

    # 测试文件不存在 → 直接回退
    if not test_path.exists():
        return {"total": 0, "passed": 0, "failed": 0, "error_type": "missing_file",
                "fix_target": "none",
                "bans": [{"f": "missing_file", "b": "DON'T: 测试文件不存在，需重新生成 | fix: test"}],
                "step": step, "raw_output": "", "elapsed": (datetime.now() - t0).total_seconds()}

    # ── 跑测试 ──
    raw_result = await agent_run_test(file_path=str(test_path), framework=test_framework,
                                       timeout_seconds=120, workspace=root)
    total = raw_result.get("total", 0)
    passed = raw_result.get("passed", 0)
    failed = raw_result.get("failed", 0)

    # 全部通过 → 返回空 ban（无问题）
    if total > 0 and failed == 0:
        return {"total": total, "passed": passed, "failed": 0, "error_type": "none",
                "fix_target": "none", "bans": [], "step": step,
                "elapsed": (datetime.now() - t0).total_seconds()}

    # ── 解析失败详情 ──
    src_refs: dict[str, set] = {}
    test_file_errors = []
    failures_preview = []

    for f in raw_result.get("failures", [])[:15]:
        err_text = (f.get("error_message", "") or "")[:500]
        src_file, src_line, is_test_error = "", "", False

        for m in _SRC_FILE_RE.finditer(err_text):
            fp_match = m.group(1).replace("\\", "/")
            if "node_modules" in fp_match:
                continue
            if "/test/" in fp_match or fp_match.endswith((".test.js", ".spec.js")):
                is_test_error = True
                if total == 0:
                    src_file, src_line = fp_match, m.group(2)
                continue
            src_file, src_line = fp_match, m.group(2)
            break

        if total == 0 and not src_file:
            raw_err = raw_result.get("stderr", "") or raw_result.get("error", "") or ""
            tf_match = re.search(r'(?:in|at|file)\s+(\S+\.test\.\w{2,4})', raw_err)
            if tf_match:
                src_file, is_test_error = tf_match.group(1), True

        resolved = ""
        if src_file:
            resolved = str((Path(root) / src_file).resolve()) if not Path(src_file).is_absolute() else src_file
        display = ""
        if resolved:
            try:
                display = str(Path(resolved).relative_to(root)).replace("\\", "/")
            except ValueError:
                display = resolved.replace("\\", "/")

        if src_file and src_line:
            src_refs.setdefault(resolved, set()).add(int(src_line))
        if is_test_error:
            test_file_errors.append({"test_name": f.get("test_name", ""),
                                     "error_summary": err_text, "test_file_path": str(test_file_path)})
        failures_preview.append({"test_name": f.get("test_name", ""), "error_summary": err_text,
                                 "src_file": resolved or "", "src_line": src_line,
                                 "display_file": display, "is_test_error": is_test_error})

    # ── 构建上下文 ──
    source_context = _build_source_context(src_refs, root)
    test_context = _build_test_file_context(test_file_path, root) if step == "b" else ""
    full_source_section = _build_full_source_section(source_contents) if step == "d" and source_contents else ""

    # 按源文件分组失败
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

    # total=0 时的原始错误
    raw_error_section = ""
    if total == 0:
        raw_error = raw_result.get("stderr", "") or raw_result.get("error", "") or ""
        if raw_error:
            raw_error_section = f"\n## {test_framework.capitalize()} 原始错误（测试加载失败）\n```\n{raw_error[:2000]}\n```"
        if test_file_errors:
            raw_error_section += "\n## ⚠️ 测试文件自身加载失败（检查 CJS/ESM 格式）\n"
            for te in test_file_errors:
                raw_error_section += f"- {te['error_summary'][:200]}\n"

    # 历史 ban
    history_bans = bans if bans is not None else get_bans(task_id, "test_failure" if step == "b" else "source_failure")
    history_section = format_history_for_runner(history_bans)

    # ── 组装 prompt（顺序：共享 skill → 真理/ban 记忆 → 任务上下文，越前越可缓存）──
    layer = (task or {}).get("layer", "")
    role = load_role(step, layer=layer)

    step_desc = {"b": "B 步骤: 先查测试代码质量；测试干净→加载 load_d_card() 获取源码+D角色知识",
                 "d": "D 步骤: 验证C修复 → 变更分析→对照验收→回归扫描→意图分析→二次指导"}

    # B: 测试文件 + 失败详情；D: 源码 + 失败详情
    extra_sections = test_context if step == "b" else f"{full_source_section}\n{source_context}"
    if extra_context:
        extra_sections = extra_context + "\n" + (extra_sections or "")

    # ── instructions: 共享内容（跨 task 缓存命中）──
    instructions = f"""{role}

## 工作区: {root}
"""

    # ── 场景数据（B 用 testScenarios 作为诊断标准，判断测试是否正确）──
    scenarios_text = ""
    if task:
        scs = task.get("testScenarios", [])
        if scs:
            scenarios_text = "\n## 🛑 测试场景（期望行为 — B 据此判断测试是否写对、源码是否缺功能）\n" + json.dumps(scs, indent=2, ensure_ascii=False)

    # ── user_prompt: 自上而下 真理→测试结果→ban→源码，越前越可缓存 ──
    user_prompt = f"""## 当前步骤: {step} ({step_desc.get(step, "")})

## 🛑 历史禁令（上轮诊断，逐条判断是否命中）
{history_section}

## 测试摘要
- 文件: {test_file_path}  |  用例: {total} 通过/{passed} 失败/{failed}
{raw_error_section}
{scenarios_text}

{extra_sections}
## 失败详情
{chr(10).join(grouped) if grouped else "（见上方 error）"}
"""

    # ── 注入真理格式到 user_prompt（动态内容，与 layer 绑定，不同 task 不同）──
    truth_format = ""
    if layer:
        truth_file = project_root / "skill" / "test" / "truths" / f"{layer}.md"
        if not truth_file.exists():
            truth_file = project_root / "skill" / "test" / "truths" / "_default.md"
        if truth_file.exists():
            try:
                truth_format = truth_file.read_text("utf-8")
                import re as _re
                m = _re.search(r'```json\s*(\{.*?\})\s*```', truth_format, _re.DOTALL)
                if m:
                    user_prompt += f"\n## 🛑 本层真理格式（通过后应产出的 JSON 结构）\n```json\n{m.group(1)}\n```"
            except Exception:
                pass

    # ── Agent ──
    if model_client is None:
        from utils.model_client import get_model_client
        model_client = get_model_client()
    model = model_client

    _load_d_card_called = False
    async def load_d_card():
        """B 步骤按需：加载 D 角色（通用+层专精）+ 源码。🛑 只能调 1 次。"""
        nonlocal _load_d_card_called
        if _load_d_card_called:
            return {"error": "load_d_card 已调用过，禁止重复调用", "🛑_NEXT": "根据已加载的 D 知识判断 fix_target，输出 ban 或 <!--FINAL-->"}
        _load_d_card_called = True
        layer = (task or {}).get("layer", "")
        from utils.dependency_graph import _LAYER_TO_TYPE
        test_type = _LAYER_TO_TYPE.get(layer, "logic")
        role_dir = parent_dir / "skill" / "test" / "diagnosis" / "d"
        parts = []
        d_common = role_dir / f"{test_type}.md"
        if d_common.exists():
            parts.append(load_skill(str(d_common)))
        d_specific = role_dir / test_type / f"{layer}.md"
        if d_specific.exists():
            parts.append(load_skill(str(d_specific)))
        if source_contents:
            parts.append(_build_full_source_section(source_contents))
        parts.append("🛑 以上是 D 角色的源码诊断知识。你在 B 步骤中输出 ban 时仍用 B 的指纹格式 f=layer|test|file:行号|SUBTYPE，不要用 D 的 f=layer|source 格式。")
        parts.append("🛑_NEXT: 根据以上 D 知识判断——测试代码有问题→输出完整 ban JSON 数组 target=test；源码有问题→输出完整 ban JSON 数组 target=source（必须含 file:行号 + fix 具体代码）。禁止只输出 fix_target=source。不要再调任何工具。")
        return "\n".join(parts) if parts else ""

    agent = Agent(
        name=f"test_runner_{test_path.stem}_{step}",
        description="测试结果精加工工程师",
        instructions=instructions,
        model_client=model,
        tools=[load_d_card] if step == "b" else [],
        max_iterations=3,
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

    # ── Step 1: <!--FINAL--> 标记提取（对齐 source_fixer.py）──
    truth, bans_from_final = _extract_structured(full_text)
    if truth is not None:
        # D 步骤真理: {"verified": true, "bans_resolved": [...], ...}
        return {"total": raw_result.get("total", 0), "passed": raw_result.get("passed", 0),
                "failed": raw_result.get("failed", 0), "error_type": "none",
                "fix_target": "none", "bans": [], "truth": truth,
                "step": step, "raw_output": full_text,
                "elapsed": (datetime.now() - t0).total_seconds()}
    if bans_from_final is not None:
        fix_target = bans_from_final[0].get("f", "").split("|")[1] if bans_from_final and "|" in bans_from_final[0].get("f", "") else "source"
        if fix_target not in ("test", "source"):
            fix_target = "source"
        return {"total": raw_result.get("total", 0), "passed": raw_result.get("passed", 0),
                "failed": raw_result.get("failed", 0), "error_type": raw_result.get("error_type", "test_bug"),
                "fix_target": fix_target, "bans": bans_from_final, "step": step,
                "raw_output": full_text, "elapsed": (datetime.now() - t0).total_seconds()}

    # ── Step 2: extract_json_dict 回退（兼容旧格式）──
    llm_output = extract_json_dict(full_text)

    # ── 提取 ban ──
    if llm_output is None or not isinstance(llm_output, dict):
        text_bans = _extract_bans_from_text(full_text)
        if text_bans:
            fix_target = text_bans[0].get("f", "").split("|")[1] if "|" in text_bans[0].get("f", "") else "source"
            if fix_target not in ("test", "source"):
                fix_target = "source"
            return {"total": raw_result.get("total", 0), "passed": raw_result.get("passed", 0),
                    "failed": raw_result.get("failed", 0), "error_type": raw_result.get("error_type", "test_bug"),
                    "fix_target": fix_target, "bans": text_bans, "step": step,
                    "raw_output": full_text, "elapsed": (datetime.now() - t0).total_seconds()}
        result = _fallback_result(raw_result, step, t0, "JSON+text parse failed", full_text)
        result["raw_output"] = full_text
        return result

    fix_target = llm_output.get("fix_target", "test")
    bans_raw = llm_output.get("bans", None)
    if bans_raw and isinstance(bans_raw, list):
        bans_out = bans_raw
    else:
        ban_raw = llm_output.get("ban", "")
        if isinstance(ban_raw, dict):
            bans_out = [ban_raw]
        elif isinstance(ban_raw, str) and ban_raw.strip():
            bans_out = [{"f": "", "b": ban_raw.strip()}]
        else:
            bans_out = []

    return {"total": raw_result.get("total", 0), "passed": raw_result.get("passed", 0),
            "failed": raw_result.get("failed", 0),
            "error_type": llm_output.get("error_type", raw_result.get("error_type", "test_bug")),
            "fix_target": fix_target, "bans": bans_out, "step": step,
            "raw_output": full_text, "elapsed": (datetime.now() - t0).total_seconds()}
