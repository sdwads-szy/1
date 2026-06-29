# agent/source_fixer.py
"""
源码修复 Agent —— 从 Memory/source_failure/<id>.json 加载完整历史记忆。
"""

import json, os, sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from picoagents import Agent
from dotenv import load_dotenv
from Tools.coding.create_files import create_files as _create_files
from Tools.coding.edit_lines import edit_batch as _edit_batch
from Tools.skill.load_skill import load_skill
from Tools.testing.npm_install import npm_install
from Tools.memory.ban_memory import get_bans, format_bans_for_agent
from utils.token import wrap_agent_stream

load_dotenv('./.env.example')
ROLE_PATH = parent_dir / "skill" / "test" / "roles" / "c_source_fixer.md"

_C_ROLE_MAP = {
    "infra": "c_static_fix", "db": "c_static_fix", "frontend_static": "c_static_fix", "peer_deps": "c_static_fix",
    "auth": "c_interface_fix", "api": "c_interface_fix", "db_api": "c_interface_fix", "navigation": "c_interface_fix",
    "backend_proc": "c_logic_fix", "logic": "c_logic_fix", "scenario": "c_logic_fix", "nfr": "c_logic_fix",
}

def load_role(source_type: str = "") -> str:
    role_dir = parent_dir / "skill" / "test" / "roles"
    role_file = _C_ROLE_MAP.get(source_type, "c_static_fix")
    path = role_dir / f"{role_file}.md"
    if path.exists():
        role = load_skill(str(path))
    elif ROLE_PATH.exists():
        role = load_skill(str(ROLE_PATH))
    else:
        role = ""

    quality_path = parent_dir / "skill" / "code" / "quality.md"
    if quality_path.exists():
        role += "\n\n## 通用代码质量规范\n" + load_skill(str(quality_path))

    if source_type == "frontend":
        ui_path = parent_dir / "skill" / "code" / "ui.md"
        if ui_path.exists():
            role += "\n\n## UI 设计规范\n" + load_skill(str(ui_path))
    return role

def _detect_source_type_from_targets(target_files: list, category: str = "unit") -> str:
    """根据 targetFiles 和 category 检测源码类型。
    category=business → 返回 'business'，加载对应的 business 修复策略。
    """
    if category == "business":
        return "business"
    if category == "joint":
        return "joint"
    targets = " ".join(target_files)
    if any(k in targets for k in (".vue", "src/pages/", "src/stores/", "src/router/", "src/api/")):
        return "frontend"
    if "services/" in targets:
        return "service"
    if "middleware/" in targets:
        return "middleware"
    if "routes/" in targets:
        return "route"
    if "config/" in targets:
        return "config"
    if "utils/" in targets:
        return "utils"
    return "service"


def _load_source_repair(source_type: str) -> str:
    """加载层专属源码修复策略。"""
    repair_dir = Path(__file__).parent.parent / "skill" / "test" / "repair" / "c"
    type_file = repair_dir / f"{source_type}.md"
    if type_file.exists():
        return f"\n## 源码修复策略（{source_type} 类型）\n{load_skill(str(type_file))}\n"
    return ""


def _validate_syntax(workspace: str, file_path: str) -> tuple:
    """运行 node --check 校验单个文件的语法。返回 (ok: bool, error_msg: str)。
    .vue 文件和 vitest ESM 测试文件跳过 node --check（node 不支持 SFC/ESM 语法）。"""
    import subprocess
    p = Path(workspace) / file_path
    if not p.exists():
        return False, "文件不存在"
    # .vue 文件不是纯 JS，node --check 不支持
    if file_path.endswith(".vue"):
        return True, ""
    # test/business/ 下的 vitest 测试使用 ESM import，node --check 会误报
    if "/test/business/" in file_path or "\\test\\business\\" in file_path:
        return True, ""
    try:
        r = subprocess.run(
            ["node", "--check", str(p)],
            capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace",
        )
        if r.returncode == 0:
            return True, ""
        err = (r.stderr or "")[:200].replace('\n', ' ')
        return False, err
    except Exception as e:
        return False, str(e)[:200]


def _build_toolkit(workspace_root: str, write_files: list, task_id: str = "", layer: str = ""):
    abs_workspace = str(Path(workspace_root).resolve())

    # ── 白名单拆分: 写白名单 (只能改 targetFiles) vs 读白名单 (可读同层参考文件) ──
    _write_whitelist = set(Path(f).as_posix() for f in write_files)

    # 读白名单: 写白名单 + 同层参考文件 (从 ban 中提取的缺失文件路径)
    _read_whitelist = set(_write_whitelist)

    def _can_write(fp: str) -> bool:
        p = Path(fp).as_posix()
        return any(p == w or p.endswith("/" + w) for w in _write_whitelist)

    def _add_read_access(fp: str):
        _read_whitelist.add(Path(fp).as_posix())

    async def read_files():
        """读取白名单内的所有文件。写白名单 + 额外参考文件。"""
        from Tools.coding.read_file import read_file as _read_file
        result = {}
        _skip = {'package-lock.json', 'node_modules'}
        for f in sorted(_read_whitelist):
            if any(s in f for s in _skip):
                continue
            r = await _read_file(f, workspace=abs_workspace)
            content = r.get("content", "")
            result[f] = {"content": content, "lines": content.count(chr(10)) + 1 if content else 0}
        return result

    async def edit_batch(files: list):
        """批量修改文件。只能修改写白名单内的文件。

参数格式:
files = [{"file": "services/orderService.js", "edits": [{"start":N,"end":N,"content":"..."}]}]
规则: start/end 为 1-indexed 行号。end<start=插入, end=start=替换, end>start=替换范围, content=""=删除
"""
        for fe in files:
            fp = fe.get("file", "")
            if not _can_write(fp):
                return {"error": f"[WHITELIST] 禁止修改 '{fp}'。写白名单: {sorted(_write_whitelist)}"}
        result = await _edit_batch(files, workspace=abs_workspace)
        if result.get("ok"):
            for fe in files:
                fp = fe.get("file", "")
                if fp.endswith(".js") and not fp.endswith(".vue"):
                    syntax_ok, syntax_err = _validate_syntax(abs_workspace, fp)
                    if not syntax_ok:
                        return {"error": f"WRITE REJECTED: {fp} 语法错误: {syntax_err}。请修正后重试。"}
        return result

    async def install(packages: str = ""):
        return await npm_install(packages, workspace=abs_workspace)

    async def create_files(files):
        """批量创建/重写文件。只能创建写白名单内的文件。"""
        for fe in files:
            fp = fe.get("path", "")
            if not _can_write(fp):
                return {"error": f"[WHITELIST] 禁止创建 '{fp}'。写白名单: {sorted(_write_whitelist)}"}
        result = await _create_files(files, overwrite=True, workspace=abs_workspace)
        if result.get("success"):
            for fe in files:
                fp = fe.get("path", "")
                if fp.endswith(".js") and not fp.endswith(".vue"):
                    syntax_ok, syntax_err = _validate_syntax(abs_workspace, fp)
                    if not syntax_ok:
                        return {"error": f"WRITE REJECTED: {fp} 语法错误: {syntax_err}。请修正后重试。"}
        return result

    # 知识库工具 — 查历史修复经验 + 优秀代码参考
    from Tools.rag.search_rag import make_search_rag
    from Tools.rag.search_code import make_search_code
    search_rag = make_search_rag(task_id, "source_fixer")
    search_code = make_search_code(task_id, "source_fixer")

    tools = [read_files, edit_batch, create_files, install, search_rag, search_code]
    return tools, abs_workspace, _add_read_access

async def run_source_fixer(
    task: dict,
    test_file_path: str,
    workspace_root: str = "./work/project",
    source_contents: dict = None,
    model_client=None,
    task_id: str = "",
    attempt: int = 0,
    bans_text: str = "",
    save_dir: str = "",
    save_filename: str = "",
) -> Dict[str, Any]:
    t0 = datetime.now()
    task_id = task.get("id", "unknown") if not task_id else task_id
    target_files = list(task.get("targetFiles", task.get("path", [])))

    # 用 task.layer 确定源码类型（与 repair/c/{layer}.md 对应）
    source_type = (task.get("layer") or _detect_source_type_from_targets(target_files, task.get("category", "unit")))
    role = load_role(source_type)

    # 加载源码修复记忆（scheduler 传入的 bans_text 优先，否则从磁盘加载）
    if bans_text:
        memory_text = bans_text
    else:
        memories = get_bans(task_id)
        memory_text = format_bans_for_agent(memories)

    # 从 bans 中提取缺失文件路径，加入白名单（C 可以直接创建）
    import re
    _ban_text = bans_text or memory_text
    new_files = []
    for m in re.finditer(r'(?:create|missing|不存在)[^.]*?([\w/-]+\.\w{2,5})', _ban_text, re.IGNORECASE):
        missing_file = m.group(1)
        if missing_file not in target_files:
            target_files.append(missing_file)
            new_files.append(missing_file)

    # 为缺失文件找同级参考文件（同目录下已存在的文件作为模板）
    sibling_refs = {}
    ws_path = Path(workspace_root)
    for nf in new_files:
        nf_dir = (ws_path / nf).parent
        if nf_dir.exists():
            siblings = [str(p.relative_to(ws_path)).replace('\\', '/')
                       for p in nf_dir.iterdir() if p.is_file() and p.suffix in ('.js', '.json')]
            for sib in siblings[:2]:  # 最多取2个同级文件
                if sib not in target_files:
                    target_files.append(sib)  # 加入可读列表
                    sibling_refs[sib] = f"（{nf} 的同级参考文件）"

    source_type = (task.get("layer") or _detect_source_type_from_targets(target_files, task.get("category", "unit")))
    tools, abs_ws, add_read = _build_toolkit(workspace_root, target_files, task_id, source_type)

    # ── 将缺失文件路径加入读白名单（C 需要读取同级参考文件）──
    for nf in new_files:
        add_read(nf)
    for sib in sibling_refs.keys():
        add_read(sib)

    # 将预读的源码注入 prompt，C 无需再调 read_files
    source_section = ""
    if source_contents:
        lines = []
        for fp, content in source_contents.items():
            file_lines = content.split('\n')
            lines.append(f"### {fp} ({len(file_lines)} 行)")
            lines.append("```")
            for i, l in enumerate(file_lines):
                lines.append(f"  {i+1:>4}| {l}")
            lines.append("```")
        source_section = "## 当前源码（已在 prompt 中，无需 read_files）\n" + "\n".join(lines)

    # 按源码类型加载修复策略
    repair_text = _load_source_repair(source_type)

    instructions = f"""{role}

{repair_text}
## 源码类型: {source_type}

## 工作区: {abs_ws}

## 可修改的文件
{json.dumps(sorted(target_files), ensure_ascii=False)}

{memory_text}
"""

    # 如果需要创建新文件，附上测试场景作为行为规格
    create_context = ""
    if new_files:
        scenarios = task.get("testScenarios", [])
        if scenarios:
            create_context = "\n## 需要创建的文件及预期行为（来自测试场景）\n"
            for s in scenarios:
                create_context += f"- {s.get('scenario', '')}: {s.get('expectedBehavior', '')}\n"
        if sibling_refs:
            create_context += "\n## 同级参考文件（可作为模板）\n"
            for sib, note in sibling_refs.items():
                create_context += f"- {sib} {note}\n"

    user_prompt = f"""{create_context}
{source_section}"""


    if model_client is None:
        from utils.model_client import get_model_client
        model_client = get_model_client()
    model = model_client

    agent = Agent(
        name=f"source_fixer_{task_id}",
        description="源码修复工程师",
        instructions=instructions,
        model_client=model,
        tools=tools,
        max_iterations=3,
    )

    collected, tool_calls_made = [], 0
    try:
        async for event in wrap_agent_stream(
            agent, user_prompt, "source_fixer",
            model=model.model, task_id=task_id,
            save_dir=save_dir, save_filename=save_filename,
        ):
            collected.append(str(event))
            if "tool_call" in str(event).lower():
                tool_calls_made += 1
    except Exception as e:
        return {"success": False, "files_modified": [], "message": f"Agent error: {e}", "strategy": "", "elapsed": (datetime.now() - t0).total_seconds()}

    full_text = "\n".join(collected)
    skipped = ("FIX_SKIP" in full_text and tool_calls_made == 0)
    # 从 LLM 回复中提取修复描述（跳过用户 prompt）
    strategy = f"modified {tool_calls_made} location(s)" if tool_calls_made > 0 else "未找到修复方案"
    if tool_calls_made > 0:
        for line in reversed(collected):
            s = str(line)
            if s.startswith("[user]") or s.startswith("[system]"):
                continue  # 跳过 prompt
            if "修复" in s or "修改" in s or "添加" in s or "安装" in s or "modified" in s.lower():
                strategy = s[:200]
                break
    return {
        "success": not skipped,
        "files_modified": target_files if tool_calls_made > 0 else [],
        "message": "Fix completed" if not skipped else "Agent declined",
        "strategy": strategy,
        "elapsed": (datetime.now() - t0).total_seconds(),
        "raw_output": full_text,
    }