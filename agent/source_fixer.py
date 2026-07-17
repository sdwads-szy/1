# agent/source_fixer.py
"""
源码修复 Agent (C step) —— 接收 B/D 的 ban → 修改源码。
支持: 静态层(DDL/前端/配置) + 接口层(路由/controller) + 逻辑层(service/事务)。
"""

import json, os, sys, re, subprocess
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
from Tools.memory.ban_memory import get_bans, store_bans, format_bans_for_agent
from utils.token import wrap_agent_stream

load_dotenv('./.env.example')


# ═══════════════════════════════════════════════
# Skill 加载
# ═══════════════════════════════════════════════

def _normalize_test_type(source_type: str) -> str:
    from utils.dependency_graph import _LAYER_TO_TYPE
    return _LAYER_TO_TYPE.get(source_type, source_type)


def load_role(source_type: str = "") -> str:
    """C 角色：通用文件 + 子层特化 + 二次修复策略 + 代码质量规范"""
    if not source_type:
        return ""
    test_type = _normalize_test_type(source_type)
    role_dir = parent_dir / "skill" / "test" / "roles" / "c"
    repair_dir = parent_dir / "skill" / "test" / "repair" / "c"
    parts = []
    # 通用 + 特化
    for p in [role_dir / f"{test_type}.md", role_dir / test_type / f"{source_type}.md"]:
        if p.exists():
            parts.append(load_skill(str(p)))
    # 二次修复策略（D 打回后使用）
    rp = repair_dir / f"{test_type}.md"
    if rp.exists():
        parts.append(load_skill(str(rp)))
    # 代码质量规范
    qp = parent_dir / "skill" / "code" / "quality.md"
    if qp.exists():
        parts.append(load_skill(str(qp)))
    # 前端 UI 规范（从 Memory/ui_styles/ 加载 PM+Designer 产出的动态文档）
    if source_type == "frontend":
        ui_styles_dir = parent_dir / "Memory" / "ui_styles"
        if ui_styles_dir.exists():
            for ui_file in sorted(ui_styles_dir.glob("*.md")):
                try:
                    parts.append(f"## UI 风格: {ui_file.stem}\n{ui_file.read_text('utf-8', errors='replace')}")
                except Exception:
                    pass
    return "\n\n".join(parts) if parts else ""


# ═══════════════════════════════════════════════
# 语法校验
# ═══════════════════════════════════════════════

def _validate_syntax(workspace: str, file_path: str) -> tuple:
    """node --check 校验。跳过 .vue、src/ ESM、test/ 文件。"""
    p = Path(workspace) / file_path
    if not p.exists():
        return False, "文件不存在"
    if file_path.endswith(".vue") or "/src/" in file_path or "/test/" in file_path:
        return True, ""
    try:
        r = subprocess.run(["node", "--check", str(p)], capture_output=True, text=True,
                            timeout=15, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            return True, ""
        return False, (r.stderr or "")[:200].replace('\n', ' ')
    except Exception as e:
        return False, str(e)[:200]


# ═══════════════════════════════════════════════
# 工具构建
# ═══════════════════════════════════════════════

def _build_toolkit(workspace_root: str, target_files: list, task_id: str = "", task: dict = None, is_static: bool = False):
    """构建 C Agent 的工具集。

    静态层 (is_static=True):  3 阶段锁 + 工具次数限制 (read→fix→verify)
    ABCD C步 (is_static=False): 无锁 + 无限次，简单读→写→输出
    """
    abs_workspace = str(Path(workspace_root).resolve())
    _task = task or {}
    # 白名单：本任务文件 + 直接依赖的文件（上游缺失时允许补建）
    write_whitelist = set(Path(f).as_posix() for f in target_files)
    if task:
        for dep_id in task.get("dependencies", []):
            # 这里无法获取依赖任务定义，chunk 提示中会列出
            pass
    read_whitelist = set(write_whitelist)

    def _can_write(fp: str) -> bool:
        p = Path(fp).as_posix()
        return any(p == w or p.endswith("/" + w) for w in write_whitelist)

    def _add_read(fp: str):
        read_whitelist.add(Path(fp).as_posix())

    # ══ 工具调用次数限制 ══
    _call_count = {"_fix": 0}
    _max_fix = 1 if is_static else 2

    def _check_limit(tool_name: str) -> str:
        if tool_name == "edit_batch" or tool_name == "create_files":
            cnt = _call_count.get("_fix", 0)
            if cnt >= _max_fix:
                return f"{tool_name} 只能调 {_max_fix} 次，已用完"
            _call_count["_fix"] = cnt + 1
        elif tool_name in ("read_files", "search_rag", "search_code"):
            pass  # 不限次数
        return ""

    def _remaining_hint() -> str:
        """生成剩余调用次数提示。"""
        parts = []
        fix_used = _call_count.get("_fix", 0)
        fix_left = _max_fix - fix_used
        parts.append(f"edit_batch/create_files: {fix_left}/{_max_fix} 次")
        for t in ("read_files", "search_rag", "search_code", "verify_checkpoints"):
            if _call_count.get(t, 0) > 0:
                parts.append(f"{t}: 已用完")
        return " | ".join(parts)

    async def scan_services():
        """收集原始环境数据：npm 包 + process.env 引用 + 当前 .env 变量 + mock 检测。
        Agent 根据这些事实自行推断需要哪些第三方服务配置，无需 Python 硬编码服务列表。"""
        import re as _re, json as _json, os as _os
        ws = Path(abs_workspace)
        result = {"npm_deps": [], "env_refs": [], "env_missing": [], "mock_hints": []}

        # npm 依赖
        pkg_json = ws / "package.json"
        if pkg_json.exists():
            try:
                pkg = _json.loads(pkg_json.read_text("utf-8"))
                deps = sorted(set(pkg.get("dependencies", {}).keys()) | set(pkg.get("devDependencies", {}).keys()))
                skip = ("@vitejs", "@vue", "vite", "vue", "pinia", "element-plus", "axios",
                       "jest", "eslint", "prettier", "postcss", "tailwind", "autoprefixer")
                result["npm_deps"] = [d for d in deps if not any(d.startswith(p) for p in skip)]
            except Exception:
                pass

        # process.env 引用
        code_vars = set()
        for root, dirs, files in _os.walk(str(ws)):
            dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", ".meta", "test")]
            for fn in files:
                if not fn.endswith((".js", ".vue")):
                    continue
                try:
                    c = Path(root, fn).read_text("utf-8", errors="replace")
                    code_vars.update(_re.findall(r"process\.env\.(\w+)", c))
                except Exception:
                    pass
        result["env_refs"] = sorted(code_vars)

        # 当前 .env 已有的 vs 缺失的
        env = ws / ".env"
        existing = set()
        if env.exists():
            for line in env.read_text("utf-8", errors="replace").split("\n"):
                s = line.strip()
                if s and not s.startswith("#") and "=" in s:
                    existing.add(s.split("=")[0].strip())
        result["env_missing"] = sorted(code_vars - existing)

        # mock 实现
        mock_hints = set()
        for root, dirs, files in _os.walk(str(ws)):
            dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", ".meta", "test")]
            for fn in files:
                if not fn.endswith((".js", ".vue")):
                    continue
                try:
                    c = Path(root, fn).read_text("utf-8", errors="replace")
                    for m in _re.finditer(r"(?:mock|Mock)([A-Z][a-zA-Z]+?)(?:\s*\(|Auth|Pay|SMS|Email|Upload)", c):
                        mock_hints.add(m.group(0)[:50])
                except Exception:
                    pass
        result["mock_hints"] = sorted(mock_hints)[:10]
        return result

    async def read_files():
        reject = _check_limit("read_files")
        if reject: return {"error": reject}
        from Tools.coding.read_file import read_file as _read_file
        result = {}
        for f in sorted(read_whitelist):
            if "node_modules" in f or "package-lock.json" in f:
                continue
            r = await _read_file(f, workspace=abs_workspace)
            content = r.get("content", "")
            result[f] = {"content": content, "lines": content.count(chr(10)) + 1 if content else 0}
        result["🛑_REMAINING"] = _remaining_hint()
        result["_hint"] = "已读取所有目标文件 → 调用 edit_batch(files=[{\"file\":\"路径\",\"edits\":[{\"start\":行号,\"end\":行号,\"content\":\"...\"}]}]) 修复；end<start=插入，end>=start=替换"
        return result

    async def edit_batch(files: list):
        _close_step1()
        reject = _check_limit("edit_batch")
        if reject: return {"error": reject}
        for fe in files:
            if not isinstance(fe, dict):
                continue
            fp = fe.get("file", fe.get("path", ""))
            if not fp or fp == "None":
                return {"error": f"[WHITELIST] 无效的文件路径 '{fp}'", "_hint": "传入正确的 file 字段"}
            if not _can_write(fp):
                return {"error": f"[WHITELIST] 禁止修改 '{fp}' — 不在本任务可写白名单中",
                        "_hint": f"可写文件: {sorted(write_whitelist)}。如需修改 '{fp}'，先通过 read_files 确认问题，然后在 ban 中输出 f=layer|source|{fp}:行号|TYPE 格式指明需修复的文件。"}
            # 🛑 预检查：start 参数缺失或为 0 → 参数格式错误
            for ed in fe.get("edits", []):
                if ed.get("start", 0) < 1:
                    return {"error": f"[FORMAT] 缺少 start 参数，正确格式: {{\"start\": 行号, \"end\": 行号-1, \"content\": \"...\"}}",
                            "_hint": "end<start=插入, end>=start=替换"}
        result = await _edit_batch(files, workspace=abs_workspace)
        if result.get("success"):
            for fe in files:
                if not isinstance(fe, dict):
                    continue
                fp = fe.get("file", fe.get("path", ""))
                ok, err = _validate_syntax(abs_workspace, fp)
                if not ok:
                    result["_hint"] = f"语法错误: {fp} → 修完重试"
                    return result
            # 检查 applied
            total = sum(r.get("applied", 0) for r in result.get("results", []))
            if total == 0:
                result["_hint"] = "⚠️ applied=0: 所有编辑都未生效，检查 start/end 行号是否正确（从1开始，插入=end<start）"
            else:
                result["🛑_REMAINING"] = _remaining_hint()
        result["_hint"] = f"已修改 {total} 处 → 调用 verify_checkpoints() 自检"
        return result

    async def create_files(files):
        _close_step1()
        for fe in files:
            if not isinstance(fe, dict):
                continue
            p = fe.get("path", fe.get("file", ""))
            p = p.replace("\\", "/")
            ws_prefix = abs_workspace.replace("\\", "/") + "/"
            if p.startswith(ws_prefix):
                p = p[len(ws_prefix):]
            for prefix in ("work/project/", "project/"):
                if p.startswith(prefix):
                    p = p[len(prefix):]
                    break
            fe["path"] = p
            if not p or p == "None":
                return {"error": f"[WHITELIST] 无效的文件路径 '{p}'", "_hint": "传入正确的 file/path 字段"}
            if not _can_write(p):
                return {"error": f"[WHITELIST] 禁止创建 '{p}'", "_hint": f"只能创建: {sorted(write_whitelist)[:5]}"}
        result = await _create_files(files, overwrite=True, workspace=abs_workspace)
        if result.get("success"):
            for fe in files:
                if not isinstance(fe, dict):
                    continue
                fp = fe.get("path", "")
                ok, err = _validate_syntax(abs_workspace, fp)
                if not ok:
                    result["_hint"] = f"语法错误: {fp} → 修正后重试"
                    return result
        result["🛑_REMAINING"] = _remaining_hint()
        result["_hint"] = "创建完成 → 调用 verify_checkpoints() 自检"
        return result

    async def install(packages: str = ""):
        return await npm_install(packages, workspace=abs_workspace)

    async def check_exports(file_paths=None):
        """检查文件的 export 函数名。无参数时自动检查白名单内所有 .js 文件。"""
        if file_paths is None:
            file_paths = [f for f in write_whitelist if f.endswith('.js')]
        if isinstance(file_paths, str):
            file_paths = [file_paths]
        results = {}
        for file_path in file_paths:
            p = Path(abs_workspace) / file_path
            if not p.exists():
                results[file_path] = {"error": f"文件不存在"}
                continue
            content = p.read_text("utf-8", errors="replace")
            names = re.findall(r'export (?:async\s+)?function\s+(\w+)', content)
            names += re.findall(r'export\s+const\s+(\w+)\s*=', content)
            results[file_path] = {"exports": sorted(set(names)), "count": len(set(names))}
        return results

    def _check_infra_file(tf: str, content: str, result: dict):
        """infra 层文件专有检查"""
        if tf == "package.json":
            try:
                pkg = json.loads(content)
                result["通用检查"]["passed"].append(f"{tf}: 合法 JSON")
                if "name" in pkg: result["通用检查"]["passed"].append(f"{tf}: name={pkg['name']}")
                else: result["通用检查"]["failed"].append(f"{tf}: 缺少 name")
                scripts = pkg.get("scripts", {})
                for s in ["db", "backend", "frontend", "test"]:
                    if s in scripts: result["通用检查"]["passed"].append(f"{tf}: scripts 含 {s}")
                    else: result["通用检查"]["failed"].append(f"{tf}: scripts 缺 {s}")
                # 禁止 type: module
                if pkg.get("type") == "module":
                    result["通用检查"]["failed"].append(f"{tf}: 禁止 type: module（后端 CJS）")
                else:
                    result["通用检查"]["passed"].append(f"{tf}: 无 type: module（正确）")
            except Exception:
                result["通用检查"]["failed"].append(f"{tf}: JSON 解析失败")
        if "config/" in tf and tf.endswith("db.js"):
            for exp in ["pool", "query", "beginTransaction", "commit", "rollback"]:
                if exp in content: result["通用检查"]["passed"].append(f"{tf}: 导出 {exp}")
                else: result["通用检查"]["failed"].append(f"{tf}: 缺导出 {exp}")
        if "middleware/" in tf and tf.endswith("auth.js"):
            if "authenticate" in content: result["通用检查"]["passed"].append(f"{tf}: 导出 authenticate")
            else: result["通用检查"]["failed"].append(f"{tf}: 缺导出 authenticate")
        if "utils/" in tf and tf.endswith("response.js"):
            if "success" in content: result["通用检查"]["passed"].append(f"{tf}: 含 success 函数")
            else: result["通用检查"]["failed"].append(f"{tf}: 缺 success 函数")

    def _check_sql_file(tf: str, content: str, result: dict):
        """db 层 SQL 文件专有检查"""
        has_ct = "CREATE TABLE" in content.upper()
        parens_ok = content.count("(") == content.count(")")
        auto_ok = not ("AUTO_INCREMENT" in content.upper() and "PRIMARY KEY" not in content.upper())
        if has_ct: result["通用检查"]["passed"].append(f"{tf}: 含 CREATE TABLE")
        else: result["通用检查"]["failed"].append(f"{tf}: 缺 CREATE TABLE")
        if parens_ok: result["通用检查"]["passed"].append(f"{tf}: 括号配对正确")
        else: result["通用检查"]["failed"].append(f"{tf}: 括号不配对")
        if auto_ok: result["通用检查"]["passed"].append(f"{tf}: AUTO_INCREMENT 规则正确")
        else: result["通用检查"]["failed"].append(f"{tf}: 有 AUTO_INCREMENT 但缺 PRIMARY KEY")

    async def verify_checkpoints():
        """自检：通用检查（所有任务必跑）+ 任务检查点（checkPoints）。一次性检出全部问题。"""
        reject = _check_limit("verify_checkpoints")
        if reject: return {"error": reject}
        result = {"通用检查": {"passed": [], "failed": []},
                   "任务检查点": {"passed": [], "failed": []}}
        ws = Path(abs_workspace)
        layer = _task.get("layer", "")

        # ═══════════════════════════════════════════
        # 一、通用检查（所有任务逐文件硬校验）
        # ═══════════════════════════════════════════
        for tf in write_whitelist:
            fp = ws / tf
            if not fp.exists():
                result["通用检查"]["failed"].append(f"{tf}: 文件不存在")
                continue
            try: content = fp.read_text("utf-8")
            except Exception:
                result["通用检查"]["failed"].append(f"{tf}: 无法读取")
                continue

            # 1. 语法检查
            if tf.endswith(".js") and "src/" in tf:
                r = subprocess.run(f"npx esbuild {str(fp)} --format=esm --log-level=error --outfile={ws}/.esbuild-check.js",
                    capture_output=True, text=True, shell=True, timeout=30, cwd=str(ws),
                    encoding="utf-8", errors="replace")
                if r.returncode != 0:
                    result["通用检查"]["failed"].append(f"{tf}: ESM语法错误: {(r.stderr or '')[:100]}")
                else:
                    result["通用检查"]["passed"].append(f"{tf}: ESM 语法通过")
            elif tf.endswith(".js"):
                r = subprocess.run(["node", "--check", str(fp)], capture_output=True, text=True,
                    timeout=15, encoding="utf-8", errors="replace")
                if r.returncode != 0:
                    result["通用检查"]["failed"].append(f"{tf}: CJS语法错误: {(r.stderr or '')[:100]}")
                else:
                    result["通用检查"]["passed"].append(f"{tf}: CJS 语法通过")

            # 2. CJS 禁止（src/ 下）
            if "src/" in tf and tf.endswith(".js"):
                if "module.exports" in content or "require(" in content:
                    result["通用检查"]["failed"].append(f"{tf}: CJS 语法 (禁止 require/module.exports)")
                else:
                    result["通用检查"]["passed"].append(f"{tf}: ESM 格式正确")

            # 3. 导出存在性（ESM 查 export，CJS 查 module.exports）
            if tf.endswith(".js"):
                if "src/" in tf:
                    # 前端 ESM
                    exports = set(re.findall(r'export (?:async\s+)?function\s+(\w+)', content))
                    exports.update(re.findall(r'export\s+const\s+(\w+)\s*=', content))
                    if exports:
                        result["通用检查"]["passed"].append(f"{tf}: 导出 {len(exports)} 个: {', '.join(sorted(exports)[:5])}")
                    elif not tf.endswith("request.js"):
                        result["通用检查"]["failed"].append(f"{tf}: 无 ESM export 语句")
                else:
                    # 后端 CJS
                    cjs_exports = set(re.findall(r'module\.exports\.(\w+)\s*=', content))
                    if re.search(r'module\.exports\s*=\s*\{', content):
                        cjs_exports.add("{...}")  # 对象导出
                    if cjs_exports:
                        result["通用检查"]["passed"].append(f"{tf}: module.exports 导出 {len(cjs_exports)} 项")
                    else:
                        result["通用检查"]["failed"].append(f"{tf}: 无 module.exports 导出")

            # 4. infra 层专有
            if layer == "infra":
                _check_infra_file(tf, content, result)

            # 5. db 层专有
            if layer == "db" and tf.endswith(".sql"):
                _check_sql_file(tf, content, result)

        # 6. 交叉检查（frontend/integ 层）
        if layer in ("frontend", "integ"):
            from brainAgent.scheduler import _check_router_components, _check_npm_exports
            for issue in _check_router_components(ws):
                result["通用检查"]["failed"].append(issue)
            for issue in _check_npm_exports(ws):
                result["通用检查"]["failed"].append(issue)

        # ═══════════════════════════════════════════
        # 二、任务检查点（task.checkPoints 逐条 Python 验证）
        # ═══════════════════════════════════════════
        checkpoints = _task.get("checkPoints", [])
        for i, cp in enumerate(checkpoints):
            label = f"#{i+1} {cp[:80]}"
            verified = False

            # 模式1: "导出 X" → ESM export function / CJS module.exports
            m = re.search(r"(?:module\.exports\s+)?导出\s+(\w+)\s*\(?", cp)
            if m:
                expected = m.group(1)
                found = False
                for wf in write_whitelist:
                    if not wf.endswith(".js") or not (ws / wf).exists():
                        continue
                    src = (ws / wf).read_text("utf-8", errors="replace")
                    # ESM: export function X / export const X
                    if re.search(rf'export\s+(?:async\s+)?function\s+{expected}\b', src):
                        found = True; break
                    if re.search(rf'export\s+const\s+{expected}\s*=', src):
                        found = True; break
                    # CJS 单独赋值: module.exports.X = ...
                    if re.search(rf'module\.exports\.{expected}\s*=', src):
                        found = True; break
                    # CJS 对象导出: module.exports = { ..., X, ... } 或 { X: X }
                    if re.search(rf'module\.exports\s*=\s*\{{[^}}]*\b{expected}\b[^}}]*\}}', src):
                        found = True; break
                result["任务检查点"][("passed" if found else "failed")].append(
                    f"{label}: 导出 '{expected}' {'存在' if found else '不存在'}")
                verified = True

            # 模式2: "import { X } from" 或 "import X from"
            m = re.search(r"import\s+(?:\{([^}]+)\}|\s*(\S+))\s*from\s*['\"]([^'\"]+)['\"]", cp)
            if m:
                target_module = m.group(3)
                names = (m.group(1) or m.group(2) or "").strip()
                found = any(
                    (ws / wf).exists() and
                    re.search(rf"import\s+(?:\{{[^}}]*\b{re.escape(names)}\b[^}}]*\}}|\b{re.escape(names)}\b)\s*from\s*['\"]{re.escape(target_module)}['\"]",
                              (ws / wf).read_text("utf-8", errors="replace"))
                    for wf in write_whitelist
                )
                result["任务检查点"][("passed" if found else "failed")].append(
                    f"{label}: import {{{names}}} from '{target_module}' {'存在' if found else '不存在'}")
                verified = True

            # 模式3: "require('X')" 或 "require(\"X\")"
            m = re.search(r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", cp)
            if m:
                target = m.group(1)
                found = any(
                    (ws / wf).exists() and
                    re.search(rf"require\s*\(\s*['\"]{re.escape(target)}['\"]\s*\)",
                              (ws / wf).read_text("utf-8", errors="replace"))
                    for wf in write_whitelist
                )
                result["任务检查点"][("passed" if found else "failed")].append(
                    f"{label}: require('{target}') {'存在' if found else '不存在'}")
                verified = True

            # 模式4: "app.use(X)"
            m = re.search(r"app\.use\s*\(\s*(\w+)", cp)
            if m:
                target = m.group(1)
                found = any(
                    (ws / wf).exists() and
                    (target in (ws / wf).read_text("utf-8", errors="replace"))
                    for wf in write_whitelist
                )
                result["任务检查点"][("passed" if found else "failed")].append(
                    f"{label}: app.use({target}) {'存在' if found else '不存在'}")
                verified = True

            # 模式5: "scripts 包含 X/Y/Z" → 检查 package.json scripts
            m = re.search(r'scripts?\s*(?:包含|含|有)\s+([\w/,\s]+?)(?:\s*(?:命令|字段|等|$))', cp)
            if m:
                expected_scripts = re.findall(r'\w+', m.group(1))
                pkg_file = ws / "package.json"
                if pkg_file.exists():
                    try:
                        pkg_scripts = json.loads(pkg_file.read_text("utf-8")).get("scripts", {})
                        missing = [s for s in expected_scripts if s not in pkg_scripts]
                        result["任务检查点"][("passed" if not missing else "failed")].append(
                            f"{label}: scripts {'全部存在' if not missing else f'缺 {missing}'}")
                    except Exception:
                        result["任务检查点"]["failed"].append(f"{label}: package.json 解析失败")
                else:
                    result["任务检查点"]["failed"].append(f"{label}: package.json 不存在")
                verified = True

            # 未匹配的模式 → 留空，Agent 自行判断
            if not verified:
                result["任务检查点"]["passed"].append(f"{label}（非结构化描述，Agent 自行判断）")

        # ── 汇总 ──
        total_failed = len(result["通用检查"]["failed"]) + len(result["任务检查点"]["failed"])
        result["🛑_REMAINING"] = _remaining_hint()
        if total_failed == 0:
            result["_hint"] = "全部通过 → 输出 <!--FINAL--> + 真理 JSON"
        else:
            result["_hint"] = f"通用检查 {len(result['通用检查']['failed'])} 项 + 任务检查点 {len(result['任务检查点']['failed'])} 项未通过 → 修复或输出 ban"
        return result

    from Tools.rag.search_rag import make_search_rag
    from Tools.rag.search_code import make_search_code
    _raw_sr = make_search_rag(task_id, "source_fixer")
    _raw_sc = make_search_code(task_id, "source_fixer")
    _sr_count = 0; _sc_count = 0
    _step1_open = True

    def _close_step1():
        nonlocal _step1_open
        _step1_open = False

    def _check_step1(tool_name: str):
        if not _step1_open:
            return {"ok": False, "error": f"Step 1 已关闭——{tool_name} 必须在进入修复步骤之前调用，且与其它检索工具在同一次响应中并行调用",
                    "_hint": "继续修复，不再调用检索工具"}
        return None

    async def search_rag(query: str):
        nonlocal _sr_count
        reject = _check_step1("search_rag")
        if reject: return reject
        _sr_count += 1
        if _sr_count > 1:
            return {"ok": False, "error": "搜索只能调 1 次", "_hint": "直接基于 checkPoints 修复，不要重复搜索"}
        try: r = await _raw_sr(query)
        except Exception as e: r = {"ok": False, "error": str(e)[:200]}
        r["_hint"] = "检索完成 → 调用 read_files 读取目标文件，对照 checkPoints 逐条验证"
        return r

    async def search_code(query: str):
        nonlocal _sc_count
        reject = _check_step1("search_code")
        if reject: return reject
        _sc_count += 1
        if _sc_count > 1:
            return {"ok": False, "error": "搜索只能调 1 次", "_hint": "直接基于 checkPoints 修复，不要重复搜索"}
        try: r = await _raw_sc(query)
        except Exception as e: r = {"ok": False, "error": str(e)[:200]}
        r["_hint"] = "检索完成 → 调用 read_files 读取目标文件，对照 checkPoints 逐条验证"
        return r

    if is_static:
        tools = [scan_services, read_files, edit_batch, create_files, install,
                 search_rag, search_code, verify_checkpoints]
    else:
        # ABCD C步：不需要 verify_checkpoints / scan_services
        # 只读源码 → 定点改 → 完事
        tools = [read_files, edit_batch, create_files, install, search_rag, search_code]
    return tools, abs_workspace, _add_read


# ═══════════════════════════════════════════════
# Ban / Truth 提取（对齐 B/D 步骤）
# ═══════════════════════════════════════════════

def _extract_structured(text: str) -> tuple:
    """从 Agent 响应提取真理或 ban。从尾部搜索，避免 skill 模板中的 <!--FINAL--> 干扰。
    Returns: (truth_dict|None, bans_list|None)
    """
    import re as _re

    def _try_parse(json_str: str):
        try: return json.loads(json_str)
        except Exception: return None

    # ── 从尾部找最后一个 <!--FINAL--> 对，避免 skill 文件中的示例标记干扰 ──
    # rfind 找到的是闭合标记，需要回退到最后一个开标记之后的完整内容
    tail = text
    all_starts = [m.start() for m in _re.finditer(r'<!--FINAL-->', text)]
    if len(all_starts) >= 2:
        # 取倒数第二个 <!--FINAL--> 作为开标记，留后面的完整内容
        tail = text[all_starts[-2]:]
    elif len(all_starts) == 1:
        tail = text[all_starts[0]:]

    # 1. 双标记包裹 JSON（从尾部搜索）
    for m in _re.finditer(r'<!--FINAL-->\s*(\[.*?\]|\{.*?\})\s*<!--FINAL-->', tail, _re.DOTALL):
        data = _try_parse(m.group(1))
        if data is not None and (isinstance(data, dict) or (isinstance(data, list) and len(data) > 0)):
            print(f"[source_fixer] 提取成功 (双标记, {len(m.group(1))} 字符, {len(data) if isinstance(data, list) else 'dict'}项)")
            return (None, data) if isinstance(data, list) else (data, None)

    # 2. 单标记 + 括号深度追踪（从最后一个 <!--FINAL--> 开始）
    for m2 in _re.finditer(r'<!--FINAL-->\s*([\[\{])', tail):
        start = m2.end() - 1
        depth, i = 0, start
        while i < len(tail):
            ch = tail[i]
            if ch in '[{': depth += 1
            elif ch in ']}': depth -= 1
            if depth == 0:
                data = _try_parse(tail[start:i+1])
                if data is not None and (isinstance(data, dict) or (isinstance(data, list) and len(data) > 0)):
                    print(f"[source_fixer] 提取成功 (深度追踪, {len(tail[start:i+1])} 字符)")
                    return (None, data) if isinstance(data, list) else (data, None)
                break
            i += 1

    # 3. 双标记之间全文搜索 JSON（从尾部）
    for m3 in _re.finditer(r'<!--FINAL-->(.*?)<!--FINAL-->', tail, _re.DOTALL):
        inner = m3.group(1).strip()
        data = _try_parse(inner)
        if data is not None and (isinstance(data, dict) or (isinstance(data, list) and len(data) > 0)):
            print(f"[source_fixer] 提取成功 (全文搜索, {len(inner)} 字符)")
            return (None, data) if isinstance(data, list) else (data, None)
        # 在 inner 中搜索 JSON 块，取最后一个有效项
        last_valid = None
        for sub_m in _re.finditer(r'(\[.*?\]|\{.*?\})', inner, _re.DOTALL):
            data = _try_parse(sub_m.group(1))
            if data is not None and (isinstance(data, dict) or (isinstance(data, list) and len(data) > 0)):
                last_valid = data
        if last_valid is not None:
            print(f"[source_fixer] 提取成功 (inner JSON, {len(str(last_valid))} 字符)")
            return (None, last_valid) if isinstance(last_valid, list) else (last_valid, None)

    # 4. 最终 fallback: 文本格式 ban (f=...|b=...)，去重
    bans = []
    seen = set()
    for fm in _re.finditer(r'[fF]\s*=\s*(.+?)\s*\|\s*[bB]\s*=\s*(.+?)(?:\n|$)', tail):
        f_val = fm.group(1).strip()
        b_val = fm.group(2).strip()
        key = (f_val, b_val)
        if key not in seen:
            seen.add(key)
            bans.append({"f": f_val, "b": b_val})
    if bans:
        print(f"[source_fixer] 提取成功 (文本格式, {len(bans)} 条 ban)")
        return None, bans

    print(f"[source_fixer] 提取失败: 未找到有效产出")
    return None, None


# ═══════════════════════════════════════════════
# Ban 中提取文件路径
# ═══════════════════════════════════════════════

def _extract_missing_files(bans_text: str, target_files: list, workspace_root: str) -> tuple:
    """从 ban 文本中提取需要创建的文件路径，并查找同级参考文件。"""
    new_files, sibling_refs = [], {}
    ws_path = Path(workspace_root)

    # 从 ban 提取文件名。兼容 3 种格式:
    #   f=layer|source|file:line|TYPE  (skill 中)
    #   f: layer|source|file:line|TYPE  (format_bans_for_agent)
    #   "f": "layer|source|file:line|TYPE"  (<!--FINAL--> JSON)
    for m in re.finditer(r'(?:f[\s:=]+|"f"\s*:\s*")\S+\|source\|([^|"\s]+?)(?::\d+)?\|', bans_text):
        fname = m.group(1).strip()
        if fname not in target_files:
            target_files.append(fname)
            new_files.append(fname)

    # 为缺失文件找同级参考
    for nf in new_files:
        nf_dir = (ws_path / nf).parent
        if nf_dir.exists():
            for sib in nf_dir.iterdir():
                if sib.is_file() and sib.suffix in ('.js', '.json'):
                    sib_rel = str(sib.relative_to(ws_path)).replace('\\', '/')
                    if sib_rel not in target_files:
                        target_files.append(sib_rel)
                        sibling_refs[sib_rel] = f"（{nf} 的同级参考）"
                        if len(sibling_refs) >= 2:
                            break
    return new_files, sibling_refs


# ═══════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════

async def run_source_fixer(
    task: dict, test_file_path: str = None,
    workspace_root: str = "./work/project",
    source_contents: dict = None, model_client=None,
    task_id: str = "", attempt: int = 0,
    bans_text: str = "", save_dir: str = "", save_filename: str = "",
) -> Dict[str, Any]:
    t0 = datetime.now()
    task_id = task.get("id", "unknown") if not task_id else task_id
    target_files = list(task.get("targetFiles", task.get("path", [])))
    source_type = task.get("layer", "")

    # ── 加载角色 ──
    role = load_role(source_type)

    # 🛑 静态层：从 Memory 加载历史 ban（跨 attempt 记忆持久化）
    # ABCD C步：不加载历史 ban，只依赖调度器传入的 bans_text（B/D 诊断结果）
    is_static = test_file_path is None
    if is_static:
        hist_bans = get_bans(task_id, "source_failure") + get_bans(task_id, "test_failure")
        hist_text = format_bans_for_agent(hist_bans) if hist_bans else ""
        if bans_text and hist_text:
            memory_text = bans_text + "\n\n## 📜 历史累计 ban（来自 Memory，跨 attempt 记忆）\n" + hist_text
        elif bans_text:
            memory_text = bans_text
        elif hist_text:
            memory_text = hist_text
        else:
            memory_text = ""
    else:
        # ABCD: 只用 B/D 传入的 ban
        memory_text = bans_text if bans_text else ""

    # 从 ban 提取缺失文件
    new_files, sibling_refs = _extract_missing_files(bans_text or memory_text, target_files, workspace_root)

    # ── 工具（区分静态层 vs ABCD C步）──
    tools, abs_ws, add_read = _build_toolkit(workspace_root, target_files, task_id, task, is_static=is_static)
    for nf in new_files:
        add_read(nf)
    for sib in sibling_refs:
        add_read(sib)

    # ── 源码注入 ──
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

    # ── 指令 ──
    if is_static:
        mode_hint = f"""## 🛑 静态检查模式

### 检查流程
1. **搜集**: `read_files()` + `scan_services()` + `search_rag()` + `search_code()` 并行（目录结构已由调度器注入 prompt）
2. **修复**: `edit_batch` 或 `create_files`，只能调 1 次。全部修改在一个调用中完成。
3. **验证**: `verify_checkpoints()` → 通过输出真理，不通过输出 ban。调完立即停止。

### 🆕 信息搜集工具
- 目录结构已注入 prompt（`## 项目目录结构`），直接对照修复 require 路径深度
- `scan_services()` → 识别第三方服务 + mock 实现，补全 .env 变量

### 🛑 范围铁律
- 构建命令（vite build / node app.js）的错误只修 targetFiles 内的文件
- 其他文件的错误不是你的责任

### 工具有次数限制
- `edit_batch` / `create_files` 合计 1 次
"""
    else:
        mode_hint = """## 🛑 ABCD C步模式

### 工作原则
- 🛑 **不需要读全部源码**：D 已经分析过测试失败并给出了精确 ban（含文件:行号 + fix 代码）
- 🛑 **只读 ban 涉及的文件**：从 ban 的 `f` 字段提取文件路径（格式: `layer|source|file:line|TYPE`），只 read_files 这些文件
- 🛑 **ban 的 fix 是精确代码**：直接复制粘贴到 edit_batch，禁止修改、禁止"优化"、禁止反向修改
- 🛑 **所有 ban 的 fix 在 1 次 edit_batch 中完成**
- 禁止输出"已经正确""不需要改""源码和测试一致"——D 已验证过

### 从 ban 提取修复信息
ban 格式: `f=layer|source|controllers/xController.js:8|UNCHANGED`
→ 文件: `controllers/xController.js`，行号: 8，去读这个文件
→ fix: `async function listShopRefunds(req, res) {` — 直接复制到 edit_batch

### 🛑 重命名铁律
当 ban 要求改名（如 `hasRole` → `requireRole`）：
- read_files 只读 ban 涉及的文件 → 扫描该文件所有行 → 找出**每一个**旧名称出现的位置
- edit_batch 时把**所有位置**都替换，不只是 ban 提到的行
- 🛑 解构别名 `{ hasRole: requireRole }` 只改变量名，文件中所有 `hasRole(x)` 调用必须同步改为 `requireRole(x)`
"""

    # ── instructions: 共享 skill → 真理/ban 记忆 → 模式（越前越缓存）──
    instructions = f"""{role}

## 🛑 下层真理 + 历史禁令（已验证的接口 + 需要修复的问题）
{memory_text}

## 源码类型: {source_type}
## 工作区: {abs_ws}
## 可修改文件: {json.dumps(sorted(target_files), ensure_ascii=False)}

{mode_hint}
"""

    # ── 新文件创建提示 ──
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

    # ── Agent ──
    if model_client is None:
        from utils.model_client import get_model_client
        model_client = get_model_client()

    agent = Agent(
        name=f"source_fixer_{task_id}",
        description="源码修复工程师",
        instructions=instructions,
        model_client=model_client,
        tools=tools,
        max_iterations=6 if is_static else 4,  # 静态层 6 次(需自检 verify) | ABCD 4 次
    )

    collected, tool_calls = [], 0
    try:
        async for event in wrap_agent_stream(
            agent, user_prompt, "source_fixer",
            model=model_client.model, task_id=task_id,
            save_dir=save_dir, save_filename=save_filename,
        ):
            collected.append(str(event))
            if "tool_call" in str(event).lower():
                tool_calls += 1
    except Exception as e:
        return {"success": False, "files_modified": [], "message": f"Agent error: {e}",
                "strategy": "", "elapsed": (datetime.now() - t0).total_seconds()}

    # ── 结果 ──
    raw_output = "\n".join(collected)
    truth, bans = {}, []
    if is_static:
        # 静态层：从 <!--FINAL--> 提取真理或 ban
        truth, bans = _extract_structured(raw_output)
        if bans is None: bans = []
        if truth is None: truth = {}
        # 🆕 自主存储 ban 到 Memory（跨 attempt 记忆持久化）
        if bans:
            stored = store_bans(task_id, "source_failure", bans)
            if stored > 0:
                print(f"[source_fixer] {task_id}: {stored} 条新 ban 已存入 Memory")
        if truth:
            print(f"[source_fixer] {task_id}: 真理已提取 ({len(str(truth))} 字符)")
    # ABCD C步：不提取，修了代码就算成功
    skipped = (not truth and not bans and tool_calls == 0) if is_static else (tool_calls == 0)
    return {"success": not skipped,
            "files_modified": target_files if tool_calls > 0 else [],
            "message": "Fix completed" if not skipped else "Agent declined",
            "elapsed": (datetime.now() - t0).total_seconds(),
            "raw_output": raw_output,
            "bans": bans,
            "truth": truth}
