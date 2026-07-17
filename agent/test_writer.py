# agent/test_writer.py
"""
测试编写 Agent (A step) —— 基于模板+场景+角色生成测试代码。
修复模式: 接收 B 的 ban → 定点修复测试代码。
"""

import asyncio, json, os, sys, subprocess
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
from Tools.coding.list_files import list_files as _list_files
from Tools.skill.load_skill import load_skill
from Tools.testing.npm_install import npm_install
from Tools.memory.ban_memory import get_bans, format_bans_for_agent
from utils.token import wrap_agent_stream

load_dotenv('./.env.example')


# ═══════════════════════════════════════════════
# Skill 加载
# ═══════════════════════════════════════════════

def load_role(task: dict) -> str:
    """A 角色：通用文件 + 子层特化文件"""
    layer, test_type = task.get("layer", ""), task.get("testType", "")
    if not test_type or not layer:
        return ""
    role_dir = parent_dir / "skill" / "test" / "roles" / "a"
    parts = []
    common = role_dir / f"{test_type}.md"
    if common.exists():
        parts.append(load_skill(str(common)))
    specific = role_dir / test_type / f"{layer}.md"
    if specific.exists():
        parts.append(load_skill(str(specific)))
    return "\n\n".join(parts) if parts else ""


def load_template(task: dict) -> str:
    """测试模板：templates/{testType}/{layer}.md。k6 性能测试用 nfr_k6.md。"""
    layer, test_type = task.get("layer", ""), task.get("testType", "")
    if not test_type or not layer:
        return ""
    fw = task.get("testFramework", "")
    if fw == "k6":
        path = parent_dir / "skill" / "test" / "templates" / test_type / "nfr_k6.md"
    else:
        path = parent_dir / "skill" / "test" / "templates" / test_type / f"{layer}.md"
    return load_skill(str(path)) if path.exists() else ""


def load_repair(task: dict) -> str:
    """A 修复策略：repair/a/{testType}/{layer}.md"""
    layer, test_type = task.get("layer", ""), task.get("testType", "")
    if not test_type or not layer:
        return ""
    path = parent_dir / "skill" / "test" / "repair" / "a" / test_type / f"{layer}.md"
    return load_skill(str(path)) if path.exists() else ""


# ═══════════════════════════════════════════════
# 校验
# ═══════════════════════════════════════════════

def _validate_test_file(file_path: str) -> list:
    """硬校验：语法 + mock 完整性 + 闭包完整性。"""
    errors = []
    p = Path(file_path)
    if not p.exists():
        return [{"type": "syntax", "message": "文件不存在"}]
    content = p.read_text("utf-8")

    # 语法
    r = subprocess.run(["node", "--check", str(p)], capture_output=True, text=True,
                        timeout=15, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        err = (r.stderr or "").strip()[:150].replace('\n', ' ')
        errors.append({"type": "syntax", "message": f"语法错误: {err}"})

    # 路径校验: test/ 往上一级即项目根，所有 require/mock 路径必须是 ../ 开头（不是 ../../）
    import re as _re
    wrong_paths = _re.findall(r"""(?:jest\.mock|require)\s*\(\s*['\"]\.\./\.\./""", content)
    if wrong_paths:
        errors.append({"type": "WRONG_PATH", "message": f"require/mock 路径层级错误: test/ 往上一级即项目根，应使用 ../ 而非 ../../（发现 {len(wrong_paths)} 处）"})

    # 禁止模式
    for pattern, msg in [("jest.isolateModules", "禁止 isolateModules"),
                          ("jest.resetModules", "禁止 resetModules"),
                          ("jest.doMock", "禁止 doMock"),
                          ("@jest/globals", "禁止 @jest/globals")]:
        if pattern in content:
            errors.append({"type": "BANNED_PATTERN", "message": msg})

    # beforeEach 缺 clearAllMocks
    if "beforeEach" in content and "jest.clearAllMocks()" not in content:
        errors.append({"type": "MISSING_CLEARALL", "message": "beforeEach 缺少 jest.clearAllMocks()"})

    # 闭包完整性
    depth, prev = 0, ""
    for i, line in enumerate(content.split('\n'), 1):
        s = line.strip()
        if s.startswith(("describe(", "it(", "test(", "beforeEach(", "afterEach(", "beforeAll(", "afterAll(")):
            depth += 1
        elif s == "});" and not prev.endswith(',') and not prev.endswith('{'):
            depth = max(0, depth - 1)
        prev = s
        if depth == 0 and s and "expect(" in s:
            errors.append({"type": "BLOCK_INTEGRITY", "message": f"行{i}: 断言在闭包外"})
    return errors


# ═══════════════════════════════════════════════
# 工具构建
# ═══════════════════════════════════════════════

def _syntax_check(workspace: str, fp: str) -> str:
    """node --check 校验，返回错误信息（空字符串=通过）。"""
    if not fp.endswith(".js"):
        return ""
    r = subprocess.run(["node", "--check", str(Path(workspace) / fp)], capture_output=True,
                        text=True, timeout=15, encoding="utf-8", errors="replace")
    return (r.stderr or "")[:120] if r.returncode != 0 else ""


# ═══════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════

async def run_test_writer(
    task: dict, workspace_root: str = "./work/project",
    source_contents: dict = None, model_client=None,
    task_id: str = "", attempt: int = 0,
    bans_text: str = "", save_dir: str = "", save_filename: str = "",
) -> Dict[str, Any]:
    t0 = datetime.now()
    task_id = task.get("id", task_id or "unknown")
    abs_workspace = str(Path(workspace_root).resolve())
    test_file_rel = f"test/{task_id}.test.js"
    test_exists = (Path(abs_workspace) / test_file_rel).exists()

    role = load_role(task)
    template = load_template(task)
    repair = load_repair(task)

    layer = task.get("layer", "")
    target_files = task.get("targetFiles", [])
    test_type = task.get("testType", "")

    # ── 场景 + 记忆 ──
    scenarios = task.get("testScenarios", [])
    sc_text = json.dumps(scenarios, indent=2, ensure_ascii=False)
    # bans_text 格式: "## 🛑 下层真理\n{json}\n\n## ⚠️ 历史 ban\n{ban_text}"
    # 调度器将 lower_truths_text + test_bans_text 合并传入
    memory_text = bans_text if bans_text else format_bans_for_agent(get_bans(task_id))

    desc = task.get("description", "")
    note = task.get("note", "")
    fw = task.get("testFramework", "jest")

    # 🛑 任务数据（含 _trace, sourceTask, dependencies, targetFiles）
    is_static = test_type == "static"
    full_fields = {
        "id": task_id,
        "layer": layer,
        "testType": test_type,
        "sourceTask": task.get("sourceTask", ""),
        "dependencies": task.get("dependencies", []),
        "targetFiles": target_files,
        "description": desc,
        "note": note,
        "_trace": task.get("_trace", {}),
    }
    if not is_static:
        full_fields["testScenarios_counts"] = (
            f"correct={sum(1 for s in scenarios if s.get('category')=='correct')}, "
            f"error={sum(1 for s in scenarios if s.get('category')=='error')}, "
            f"boundary={sum(1 for s in scenarios if s.get('category')=='boundary')}, "
            f"auth={sum(1 for s in scenarios if s.get('category')=='auth')}"
        )

    # ── 指令（4 层信息：真理 > 模板 > 任务 > 记忆）──
    instructions = f"""{role}

## 工作区: {abs_workspace}
## 测试文件: {test_file_rel}
## 类型: {test_type}/{layer} | 框架: jest

---

## 🥇 下层真理（已验证的接口，字段名/路径/签名绝对正确，优先使用）
{memory_text}

---

## 🥈 测试模板（严格遵循模板结构，占位符用真理和任务数据替换）
{template}

---

## 🥉 任务数据（完整字段）
{json.dumps(full_fields, indent=2, ensure_ascii=False)}
"""

    if test_exists:
        instructions += "\n## 🔧 修复模式\n🛑 B 的 ban 已含文件:行号 → 直接 edit_batch 定点改或 create_file 重写"
        instructions += "\n🛑 历史 ban（上面 🥇 真理部分）中有上一轮的具体错误和 fix 指令，必须参考！"
    if repair:
        instructions += f"\n\n{repair}"

    user_prompt = f"""## 测试场景（验证集 — 描述测什么、目的是什么）
{sc_text}

## 涉及文件（来自 targetFiles）
{', '.join(target_files)}

🛑 按模板 + 真理 + 任务数据生成测试文件: {test_file_rel}
🛑 真理中的字段名 > 模板示例 > testScenarios 描述文字
"""
    # ── 工具 ──
    async def install(packages: str = ""):
        return await npm_install(packages, workspace=abs_workspace)

    # Step 1 窗口：进入 Step 2（create/edit）后关闭，拒绝任何检索工具
    _step1_open = True

    def _close_step1():
        nonlocal _step1_open
        _step1_open = False

    def _check_step1(tool_name: str):
        if not _step1_open:
            return {"error": f"Step 1 已关闭——{tool_name} 必须在进入 Step 2 之前调用，且与其它检索工具在同一次响应中并行调用",
                    "🛑_NEXT": "继续当前步骤，不再调用检索工具"}
        return None

    from Tools.rag.search_rag import make_search_rag
    from Tools.rag.search_code import make_search_code
    _raw_sr = make_search_rag(task_id, "test_generator")
    _raw_sc = make_search_code(task_id, "test_writer")
    _sr_count = 0
    _sc_count = 0

    async def search_rag(query: str):
        """查历史经验。Step 1 限定：必须与 search_code 在同一次响应中一起调用。"""
        nonlocal _sr_count
        reject = _check_step1("search_rag")
        if reject: return reject
        _sr_count += 1
        if _sr_count > 1:
            return {"ok": False, "error": "search_rag 已调用过（Step 1 只能调 1 次，所有检索工具一次并行调完）",
                    "🛑_NEXT": "直接创建测试文件，不要重复搜索"}
        try: r = await _raw_sr(query)
        except Exception as e: r = {"ok": False, "error": str(e)[:200]}
        r["🛑_NEXT"] = "检索完成 → 立即调用 create_files 创建测试文件"
        return r

    async def search_code(query: str):
        """查参考实现。Step 1 限定：必须与 search_rag 在同一次响应中一起调用。"""
        nonlocal _sc_count
        reject = _check_step1("search_code")
        if reject: return reject
        _sc_count += 1
        if _sc_count > 1:
            return {"ok": False, "error": "search_code 已调用过（Step 1 只能调 1 次，所有检索工具一次并行调完）",
                    "🛑_NEXT": "直接创建测试文件，不要重复搜索"}
        try: r = await _raw_sc(query)
        except Exception as e: r = {"ok": False, "error": str(e)[:200]}
        r["🛑_NEXT"] = "检索完成 → 立即调用 create_files 创建测试文件"
        return r

    _create_count = 0

    async def create_files(files):
        nonlocal _create_count; _close_step1()
        _create_count += 1
        if _create_count > 2:
            return {"error": "create_files 只能调 2 次", "🛑_NEXT": "输出测试完成报告"}
        clean = [f for f in files if isinstance(f, dict)]
        if not clean:
            return {"error": "files 格式错误，需 [{path, content}]", "🛑_NEXT": "用正确格式重试"}
        for fe in clean:
            fp = fe.get("path", fe.get("file", ""))
            fp = fp.replace("\\", "/")
            for prefix in ("work/project/", "project/"):
                if fp.startswith(prefix):
                    fp = fp[len(prefix):]; fe["path"] = fp
                    break
            if not fp.startswith("test/") or not fp.endswith(".test.js"):
                return {"error": f"禁止写入 '{fp}'"}
        r = await _create_files(clean, overwrite=True, workspace=abs_workspace)
        if r.get("success"):
            for fe in clean:
                fp = fe.get("path", fe.get("file", ""))
                err = _syntax_check(abs_workspace, fp)
                if err:
                    return {"error": f"WRITE REJECTED: {err}"}
        r["🛑_NEXT"] = "测试文件已创建。输出测试完成报告。"
        return r

    async def edit_batch(files):
        _close_step1()
        clean = [f for f in files if isinstance(f, dict)]
        if not clean:
            return {"error": "files 格式错误", "🛑_NEXT": "用正确格式重试"}
        result = await _edit_batch(clean, workspace=abs_workspace)
        if result.get("ok"):
            for fe in clean:
                fp = fe.get("file", fe.get("path", ""))
                err = _syntax_check(abs_workspace, fp)
                if err:
                    return {"error": f"WRITE REJECTED: {err}"}
        result["🛑_NEXT"] = "修复完成。输出测试完成报告。"
        return result

    # 编写时不需要 read_files。修复模式（test_exists）才需要 read_files + edit_batch。
    tools = [create_files, search_rag, search_code, install]
    if test_exists:
        async def read_files():
            from Tools.coding.read_file import read_file as _rf
            result = {}
            # 🛑 修复模式只读测试文件，不读源码（A 不能读源码）
            for f in [test_file_rel]:
                r = await _rf(f, workspace=abs_workspace)
                content = r.get("content", "")
                if content:
                    result[f] = {"content": content, "lines": content.count(chr(10)) + 1}
            return result
        tools = [read_files, edit_batch, create_files, search_rag, search_code, install]

    # ── Agent ──
    from utils.model_client import get_model_client
    model = model_client or get_model_client()

    agent = Agent(
        name=f"test_writer_{task_id}",
        description="测试编写工程师",
        instructions=instructions,
        model_client=model,
        tools=tools,
        max_iterations=4,
    )

    collected = []
    try:
        async for event in wrap_agent_stream(
            agent, user_prompt, "test_writer",
            model=model.model, task_id=task_id,
            save_dir=save_dir, save_filename=save_filename,
        ):
            collected.append(str(event))
    except Exception as e:
        return {"success": False, "test_file": None, "validation_errors": [],
                "message": f"Agent error: {e}", "elapsed": (datetime.now() - t0).total_seconds()}

    # ── 结果 ──
    test_file = None
    for cand in [Path(abs_workspace) / "test" / f"{task_id}.test.js",
                 Path(abs_workspace) / "test" / f"{task_id}.spec.js"]:
        if cand.exists():
            test_file = str(cand)
            break

    validation_errors = _validate_test_file(test_file) if test_file else []
    elapsed = (datetime.now() - t0).total_seconds()

    return {"success": test_file is not None and len(validation_errors) == 0,
            "test_file": test_file, "validation_errors": validation_errors,
            "message": f"Test {'created' if test_file else 'NOT created'}: {test_file}"
                       + (" | VALIDATION FAILED" if validation_errors else ""),
            "elapsed": elapsed, "raw_output": "\n".join(collected)}
