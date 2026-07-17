# agent/integrator.py
"""
集成工程师 — 负责全链路集成：路由注册、env 配置、前端构建、DB 初始化。
在所有分模块 engineer agent 完成后执行。
"""

# ═══════════════════════════════════════════════════════
# SECTION 1: 导入
# ═══════════════════════════════════════════════════════

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from picoagents import Agent, OpenAIChatCompletionClient

current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from Tools.coding.create_files import create_files as _create_files
from Tools.coding.read_file import read_file as _read_file
from Tools.coding.edit_lines import edit_batch as _edit_batch
from Tools.rag.search_rag import make_search_rag
from Tools.rag.search_code import make_search_code
from utils.token import wrap_agent_stream
from utils.logger import log_error
from agent.prompt_builder import build_system_prompt, build_integration_user_prompt

load_dotenv('./.env.example')
model_client = OpenAIChatCompletionClient(model=os.getenv("OPENAI_MODEL"))


# ═══════════════════════════════════════════════════════
# SECTION 2: 主入口
# ═══════════════════════════════════════════════════════

async def run_integration_task(task: dict, workspace_root: str = "./project",
                               metadata_memory: dict = None,
                               extra_instructions: str = "") -> dict:
    tid = task.get("taskId") or task.get("id", "integration")
    workspace_path = Path(workspace_root).resolve()
    abs_workspace = str(workspace_path).replace("\\", "/")
    workspace_path.mkdir(parents=True, exist_ok=True)

    # ── 构建额外指令 ──
    extra_instructions = _build_integration_extra(task, extra_instructions, workspace_path, abs_workspace)

    # ── 元数据 ──
    metadata_summary = _build_metadata(metadata_memory, abs_workspace)

    # ── 工具函数 ──
    read_files = _make_read_files(workspace_path, abs_workspace)
    edit_batch = _make_edit_batch(abs_workspace)
    create_files = _make_create_files(abs_workspace)
    install = _make_install(abs_workspace)
    search_rag = make_search_rag(tid, "code_generator")
    search_code = make_search_code(tid)

    # ── Agent 执行 ──
    instructions = build_system_prompt("integration", abs_workspace, extra_instructions, task=task)
    user_prompt = build_integration_user_prompt(task, metadata_summary)

    agent = Agent(
        name=f"integrator_{tid}", description="集成工程师",
        instructions=instructions, model_client=model_client,
        tools=[read_files, edit_batch, create_files, install, search_rag, search_code],
        max_iterations=7,
    )

    agent_log_dir = parent_dir / "Memory" / "agent_logs" / "engineer" / tid
    agent_log_dir.mkdir(parents=True, exist_ok=True)

    collected_messages = []
    stream_error = None
    try:
        async for event in wrap_agent_stream(
            agent, user_prompt, "integrator",
            model=model_client.model, task_id=tid,
            save_dir=str(agent_log_dir), save_filename="integrator_token",
        ):
            collected_messages.append(str(event))
    except Exception as e:
        log_error("integrator agent stream failed", task=tid, error=str(e)[:200])
        stream_error = str(e)[:300]

    (agent_log_dir / "integrator_raw.md").write_text("\n".join(collected_messages), encoding="utf-8")

    # ── 后处理 ──
    post_warnings = _post_process_integrator_output(workspace_path)

    # ── 成功判定 ──
    success, errors = _validate_integration(task, workspace_path, stream_error, tid)

    return {"task_id": tid, "success": success,
            "error": stream_error or ("; ".join(errors[:3]) if errors else None)}


# ═══════════════════════════════════════════════════════
# SECTION 3: 额外指令构建
# ═══════════════════════════════════════════════════════

def _build_integration_extra(task: dict, extra_instructions: str,
                             workspace_path: Path, abs_workspace: str) -> str:
    """构建集成 Agent 的额外指令（预扫描 + env 模板 + SQL 文件列表）。"""
    extra = extra_instructions or ""

    # 预扫描
    pre_scan_issues = _pre_integration_scan(workspace_path)
    if pre_scan_issues:
        print(f"  [pre-scan] 发现 {len(pre_scan_issues)} 个潜在问题:")
        for issue in pre_scan_issues[:10]:
            print(f"    - {issue}")
        extra += "\n\n## [pre-scan] 预扫描发现以下断裂（优先修复）\n"
        for issue in pre_scan_issues[:20]:
            extra += f"- {issue}\n"

    # 根 .env.example
    root_env_path = parent_dir / ".env.example"
    if root_env_path.exists():
        clean_env = []
        for line in root_env_path.read_text('utf-8', errors='replace').split('\n'):
            s = line.strip()
            if s and not s.startswith('#') and '=' in s:
                k, v = s.split('=', 1)
                clean_val = v.split("#")[0].strip().strip('"').strip("'")
                clean_env.append(f"{k.strip()}={clean_val}")
        extra += f"\n\n## 🛑 根 .env.example（全部变量，与代码扫描取交集填 project .env）\n```\n" + "\n".join(clean_env) + "\n```\n"
        extra += "🛑 agent 任务: 扫描代码 process.env.X → 取与根配置的交集填真实值，无交集的填占位符。每个变量一行 # 注释。只写 work/project/.env。\n"

    # SQL 文件列表
    sql_files = sorted(
        f"{p.parent.name}/{p.name}" if p.parent.name != "database" else p.name
        for p in workspace_path.glob("database/**/*.sql") if p.is_file()
    )
    if sql_files:
        extra += "\n\n## database/**/*.sql 文件列表（需列入 init-db.js 的 SQL_FILES 数组，FK 依赖序）\n"
        for f in sql_files:
            extra += f"- {f}\n"

    return extra


def _build_metadata(metadata_memory: dict, abs_workspace: str) -> dict:
    if metadata_memory:
        print(f"  元数据: {len(metadata_memory.get('backend_routes', []))} routes + "
              f"{len(metadata_memory.get('frontend_pages', []))} pages")
    return {
        "backend_routes": (metadata_memory or {}).get("backend_routes", []),
        "frontend_pages": (metadata_memory or {}).get("frontend_pages", []),
        "workspace": abs_workspace,
    }


# ═══════════════════════════════════════════════════════
# SECTION 4: 工具工厂函数
# ═══════════════════════════════════════════════════════

def _make_read_files(workspace_path: Path, abs_workspace: str):
    async def read_files():
        targets = ["app.js", "src/router/index.js", "src/main.js"]
        init_db = "scripts/init-db.js"
        if (workspace_path / init_db).exists():
            targets.append(init_db)
        result = {}
        for f in targets:
            r = await _read_file(f, workspace=abs_workspace)
            content = r.get("content", "")
            if content:
                result[f] = {"content": content, "lines": content.count("\n") + 1}
        return result
    return read_files


def _make_edit_batch(abs_workspace: str):
    async def edit_batch(files):
        return await _edit_batch(files, workspace=abs_workspace)
    return edit_batch


def _make_create_files(abs_workspace: str):
    async def create_files(files, metadata=None):
        if isinstance(files, list):
            for i, f in enumerate(files):
                if not isinstance(f, dict):
                    continue
                p = f.get("path", f.get("file", ""))
                p = p.replace("\\", "/")
                ws_prefix = abs_workspace.replace("\\", "/") + "/"
                if p.startswith(ws_prefix):
                    p = p[len(ws_prefix):]
                for prefix in ("work/project/", "project/"):
                    if p.startswith(prefix):
                        p = p[len(prefix):]
                        break
                f["path"] = p
        return await _create_files(files, overwrite=True, workspace=abs_workspace, metadata=metadata)
    return create_files


def _make_install(abs_workspace: str):
    async def install(packages: str):
        npm = "npm.cmd" if shutil.which("npm.cmd") else "npm"
        try:
            r = subprocess.run([npm, "install", "--save", "--legacy-peer-deps"] + packages.split(),
                             capture_output=True, text=True, timeout=120,
                             cwd=abs_workspace, encoding="utf-8", errors="replace")
            return {"ok": r.returncode == 0, "output": (r.stdout + r.stderr)[:500]}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}
    return install


# ═══════════════════════════════════════════════════════
# SECTION 5: 集成验证
# ═══════════════════════════════════════════════════════

def _validate_integration(task: dict, workspace_path: Path,
                          stream_error: str, tid: str) -> tuple:
    """两层验证：Python 静态检测 + Agent 产出验证。"""
    errors = []

    # 第 1 层: Python 全量静态检测（只检查集成 Agent 职责范围内的问题）
    post_scan_issues = _pre_integration_scan(workspace_path)
    # 🛑 集成 Agent 职责：路由懒加载断裂、路由注册、脚本文件、npm 依赖、app 加载。
    # 前端 import 缺失归前端 engineer。
    _INTEG_SCOPE = ("[missing require]", "[missing lazy import]", "[missing route]", "[missing script file]",
                    "[missing npm dep]", "[app load fail]", "[app load timeout]", "[app load error]")
    integ_unresolved = [i for i in post_scan_issues if i.startswith(_INTEG_SCOPE)]
    non_integ_unresolved = [i for i in post_scan_issues if not i.startswith(_INTEG_SCOPE)]
    if non_integ_unresolved:
        print(f"    [pre-scan] {len(non_integ_unresolved)} 个非集成职责问题（前端 import 缺失等，留给测试阶段）")
    if integ_unresolved:
        errors.append(f"pre-scan 断裂未修复: {len(integ_unresolved)} 个")
        for i in integ_unresolved[:5]:
            print(f"    [unresolved] {i}")

    build_errors = _post_build_check(workspace_path)
    if build_errors:
        errors.extend(build_errors)

    output_files = task.get("outputFiles") or task.get("files") or task.get("path") or []
    missing = [f for f in output_files
               if not (workspace_path / f).exists() or (workspace_path / f).stat().st_size == 0]
    if missing:
        errors.append(f"文件缺失: {', '.join(missing[:5])}")

    # 第 2 层: Agent 产出验证（integration 无下游消费者，跳过真理检查）
    if task.get("type") != "integration":
        truth_file = parent_dir / "Memory" / "truths" / "engineer" / f"{tid}.json"
        if not truth_file.exists() or truth_file.stat().st_size == 0:
            errors.append("真理文件缺失或为空")
        else:
            try:
                truth = json.loads(truth_file.read_text("utf-8"))
                if not truth.get("exposed"):
                    errors.append("真理文件缺少 exposed 字段")
            except Exception:
                errors.append("真理文件 JSON 解析失败")

    success = len(errors) == 0 and not stream_error
    if errors:
        print(f"  [integ] 失败原因: {'; '.join(errors[:5])}")

    return success, errors


# ═══════════════════════════════════════════════════════
# SECTION 6: 预扫描
# ═══════════════════════════════════════════════════════

def _pre_integration_scan(workspace_path: Path) -> list:
    """确定性预扫描：检测所有可自动发现的断裂。"""
    ws = workspace_path
    issues = []

    # 1. 全量 require/import 路径扫描
    all_files = []
    for ext in ["*.js", "*.vue"]:
        for f in ws.rglob(ext):
            if "node_modules" in str(f) or ".git" in str(f):
                continue
            all_files.append(f)

    for src_file in all_files:
        try:
            content = src_file.read_text("utf-8", errors="replace")
        except Exception:
            continue
        rel_src = str(src_file.relative_to(ws)).replace("\\", "/")

        # CJS require
        for m in re.finditer(r"""require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)""", content):
            target = m.group(1)
            if target.startswith("."):
                resolved = (src_file.parent / target).resolve()
                found = resolved.exists()
                if not found:
                    for ext_try in [".js", ".vue", "/index.js"]:
                        if Path(str(resolved) + ext_try).exists():
                            found = True
                            break
                if not found:
                    issues.append(f"[missing require] {rel_src} -> {target}")

        # ESM static import
        for m in re.finditer(r"""from\s+['\"]([^'\"]+)['\"]""", content):
            target = m.group(1)
            if target.startswith("."):
                resolved = (src_file.parent / target).resolve()
            elif target.startswith("@/"):
                resolved = (ws / target.replace("@/", "src/", 1)).resolve()
            else:
                continue
            found = resolved.exists()
            if not found:
                for ext_try in [".js", ".vue", "/index.js"]:
                    if Path(str(resolved) + ext_try).exists():
                        found = True
                        break
            if not found:
                issues.append(f"[missing import] {rel_src} -> {m.group(1)}")

        # Dynamic import()
        for m in re.finditer(r"""import\s*\(\s*['\"]([^'\"]+)['\"]\s*\)""", content):
            target = m.group(1)
            if target.startswith("@"):
                target = target.replace("@/", "src/", 1)
            elif target.startswith("."):
                pass
            else:
                continue
            resolved = (ws / target).resolve()
            found = resolved.exists()
            if not found:
                for ext_try in [".js", ".vue"]:
                    if Path(str(resolved) + ext_try).exists():
                        found = True
                        break
            if not found:
                issues.append(f"[missing lazy import] {rel_src} -> {m.group(1)}")

    # 2. package.json scripts → 文件存在性
    pkg_json = ws / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text("utf-8"))
            for name, cmd in pkg.get("scripts", {}).items():
                script_match = re.search(r'node\s+(\S+\.js)', cmd)
                if script_match:
                    script_file = ws / script_match.group(1)
                    if not script_file.exists():
                        issues.append(f"[missing script file] package.json scripts.{name} -> {script_match.group(1)}")
        except Exception:
            pass

    # 3. app.js 中 require 的路由文件
    app_js = ws / "app.js"
    if app_js.exists():
        content = app_js.read_text("utf-8", errors="replace")
        for m in re.finditer(r"""require\s*\(\s*['\"](\./routes/[^'\"]+)['\"]\s*\)""", content):
            route_file = ws / (m.group(1) + ("" if m.group(1).endswith(".js") else ".js"))
            if not route_file.exists():
                issues.append(f"[missing route] app.js 引用了不存在的路由文件: {m.group(1)}")

    # 4. npm 依赖完整性
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text("utf-8"))
            all_deps = set(pkg.get("dependencies", {}).keys()) | set(pkg.get("devDependencies", {}).keys())
            node_builtins = {"fs","path","http","https","crypto","os","url","querystring",
                           "stream","util","events","assert","buffer","child_process","net",
                           "tls","dns","zlib","cluster","process"}
            bare_requires = {}
            for jsf in ws.rglob("*.js"):
                if "node_modules" in str(jsf) or "test/" in str(jsf):
                    continue
                try:
                    c = jsf.read_text("utf-8", errors="replace")
                except Exception:
                    continue
                for m in re.finditer(r"""require\s*\(\s*['\"]([^.][^'\"]+)['\"]\s*\)""", c):
                    pkg_name = m.group(1).split("/")[0]
                    if pkg_name not in all_deps and pkg_name not in node_builtins:
                        bare_requires.setdefault(pkg_name, []).append(str(jsf.relative_to(ws)))
            for pkg_name, files in bare_requires.items():
                issues.append(f"[missing npm dep] '{pkg_name}' (required by {', '.join(files[:3])}) — 不在 package.json 中")
        except Exception:
            pass

    # 5. 全链加载测试
    if app_js.exists():
        try:
            load_test = (
                "const http = require('http');"
                "const orig = http.Server.prototype.listen;"
                "http.Server.prototype.listen = function() { console.log('APP_LOAD_OK'); process.exit(0); };"
                "setTimeout(() => { console.log('APP_LOAD_OK (timeout)'); process.exit(0); }, 8000);"
                "try { require('./app'); } catch(e) { console.error('APP_LOAD_FAIL:' + e.message); process.exit(1); }"
            )
            r = subprocess.run(["node", "-e", load_test], capture_output=True, text=True, timeout=15,
                             cwd=str(ws), encoding="utf-8", errors="replace")
            if "APP_LOAD_OK" not in (r.stdout or ""):
                err = (r.stderr or r.stdout or "").strip()[:300].replace("\n", " | ")
                issues.append(f"[app load fail] node app.js 加载失败: {err}")
        except subprocess.TimeoutExpired:
            issues.append("[app load timeout] node app.js 加载超时（15s）")
        except Exception as e:
            issues.append(f"[app load error] node app.js 加载异常: {str(e)[:200]}")

    return issues


# ═══════════════════════════════════════════════════════
# SECTION 7: 构建检查
# ═══════════════════════════════════════════════════════

def _post_build_check(workspace_path: Path) -> list:
    """集成后置构建验证：node --check app.js + vite build（仅当 node_modules 存在）。"""
    errors = []
    has_node = shutil.which("node") is not None
    has_modules = (workspace_path / "node_modules").exists()

    # 后端
    app_js = workspace_path / "app.js"
    if app_js.exists() and has_node:
        try:
            r = subprocess.run(["node", "--check", str(app_js)], capture_output=True, text=True,
                             timeout=15, encoding="utf-8", errors="replace")
            if r.returncode != 0:
                errors.append(f"app.js syntax: {(r.stderr or '')[:150]}")
        except Exception:
            pass

    # 前端
    if has_modules and has_node and ((workspace_path / "vite.config.js").exists() or
                                      (workspace_path / "vite.config.ts").exists()):
        try:
            r = subprocess.run(["npx", "--yes", "vite", "build", "--logLevel", "error",
                              "--outDir", ".vite-integ-check"],
                             capture_output=True, text=True, timeout=120,
                             cwd=str(workspace_path), encoding="utf-8", errors="replace")
            if r.returncode != 0:
                err_out = (r.stderr or r.stdout or "")[:300]
                import_errors = re.findall(r'Failed to resolve import "([^"]+)" from "([^"]+)"', err_out)
                if import_errors:
                    for imp, src in import_errors[:3]:
                        errors.append(f"import 解析失败: {imp} (from {src})")
                else:
                    errors.append(f"vite build: {err_out[:200]}")
        except subprocess.TimeoutExpired:
            errors.append("vite build 超时（120s）")
        except Exception:
            pass
        finally:
            tmp = workspace_path / ".vite-integ-check"
            if tmp.exists():
                shutil.rmtree(str(tmp), ignore_errors=True)

    return errors


# ═══════════════════════════════════════════════════════
# SECTION 8: 后处理
# ═══════════════════════════════════════════════════════

def _post_process_integrator_output(workspace_path: Path) -> list:
    """后处理：修复多路由导出 + 自动注入缺失路由 + env 补齐。"""
    warnings = []

    # 回退: LLM 有时生成 app.core.js 而非 app.js
    app_js = workspace_path / "app.js"
    app_core = workspace_path / "app.core.js"
    if not app_js.exists() and app_core.exists():
        shutil.copy2(str(app_core), str(app_js))
        print("  [auto-fix] app.core.js → app.js")

    if not app_js.exists():
        return ["app.js not found"]

    content = app_js.read_text("utf-8")
    original = content

    # Step 1: 自动注入缺失路由
    content, route_warnings = _auto_inject_routes(workspace_path, content)
    warnings.extend(route_warnings)

    # Step 2: 多路由导出展开
    content, multi_warnings = _expand_multi_routes(workspace_path, content)
    warnings.extend(multi_warnings)

    # Step 3: 清理不存在文件的 require
    content, clean_warnings = _clean_broken_requires(workspace_path, content)
    warnings.extend(clean_warnings)

    if content != original:
        app_js.write_text(content, "utf-8")
        if shutil.which("node"):
            try:
                r = subprocess.run(["node", "--check", str(app_js)], capture_output=True, text=True,
                                 timeout=15, encoding="utf-8", errors="replace")
                if r.returncode != 0:
                    warnings.append(f"app.js syntax: {(r.stderr or '')[:200]}")
            except Exception:
                pass

    # Step 4: 死路由 + env + 同步 + 图片清单
    warnings.extend(_clean_dead_routes(workspace_path))
    warnings.extend(_env_sweep(workspace_path))
    _sync_project_env_files(workspace_path)

    # 🆕 部署清单 → 生成 Memory/deployment_manifest.json（静态文件 + 服务 + 占位文件）
    try:
        from utils.file_scanner import save_manifest
        _manifest = save_manifest(str(workspace_path))
        warnings.append(f"部署清单: {_manifest}")
    except Exception:
        pass

    return warnings


def _auto_inject_routes(workspace_path: Path, content: str) -> tuple:
    """发现磁盘路由文件 + 自动注入缺失的挂载。"""
    routes_dir = workspace_path / "routes"
    if not routes_dir.exists():
        return content, []

    disk_routes = {}
    for rf in sorted(routes_dir.rglob("*.js")):
        rel = str(rf.relative_to(workspace_path)).replace("\\", "/")
        src = rf.read_text("utf-8")
        m = re.search(r'@mount\s+(/\S+)', src)
        disk_routes[rel] = m.group(1) if m else ""

    mounted = {}
    for m in re.finditer(r"const\s+(\w+)\s*=\s*require\(['\"](\./routes/[^'\"]+)['\"]\)", content):
        rp = m.group(2)
        rp_norm = rp[2:] if rp.startswith("./") else rp
        mounted[rp_norm + ("" if rp_norm.endswith(".js") else ".js")] = m.group(1)

    new_mounts = []
    for rel, base_path in sorted(disk_routes.items()):
        if rel not in mounted:
            parts = rel.replace("routes/", "").replace(".js", "").split("/")
            vn = parts[0] + "".join(p.capitalize() for p in parts[1:]) + "Routes"
            new_mounts.append((rel, vn, base_path))

    if not new_mounts:
        return content, []

    req_lines = [f"const {v} = require('./{r.replace('.js', '')}');" for r, v, _ in new_mounts]
    use_lines = []
    for _, v, bp in new_mounts:
        path = bp if bp else "/api/" + Path(new_mounts[0][0]).stem
        use_lines.append(f"app.use('{path}', {v});")

    injection = "\n" + "\n".join(req_lines) + "\n" + "\n".join(use_lines)
    if "// ROUTES_INJECTION_POINT" in content:
        content = content.replace("// ROUTES_INJECTION_POINT", injection + "\n// ROUTES_INJECTION_POINT")
    else:
        content = content.replace("app.listen", injection + "\n\napp.listen")

    return content, [f"Auto-injected {len(new_mounts)} routes"]


def _expand_multi_routes(workspace_path: Path, content: str) -> tuple:
    """多路由导出展开。"""
    warnings = []
    for m in re.finditer(r"const\s+(\w+)\s*=\s*require\(['\"](\./routes/[^'\"]+)['\"]\)", content):
        var_name, route_rel = m.group(1), m.group(2)
        rf = workspace_path / route_rel
        if not rf.is_file():
            rf = workspace_path / (route_rel + ".js")
        if not rf.is_file():
            continue
        route_src = rf.read_text("utf-8")
        multi = re.search(r'module\.exports\s*=\s*\{\s*(\w+)\s*,\s*(\w+)\s*\}', route_src)
        if not multi:
            continue
        prop1, prop2 = multi.group(1), multi.group(2)
        if not re.search(rf'const\s+{prop1}\s*=\s*express\.Router\(\)', route_src):
            continue
        if not re.search(rf'const\s+{prop2}\s*=\s*express\.Router\(\)', route_src):
            continue
        warnings.append(f"{var_name}: 多路由导出 {{{prop1}, {prop2}}} 展开")
        for um in re.finditer(rf"app\.use\((['\"]/api/\S+['\"])\s*,\s*{var_name}\)", content):
            path = um.group(1)
            content = content.replace(um.group(0),
                f"app.use({path}, {var_name}.{prop1});\napp.use({path}, {var_name}.{prop2})")
            break
    return content, warnings


def _clean_broken_requires(workspace_path: Path, content: str) -> tuple:
    """清理不存在文件的 require。"""
    warnings = []
    for m in re.finditer(r"""(?:const|let|var)\s+(\w+)\s*=\s*require\s*\(\s*['\"](\.[^'\"]+)['\"]\s*\)\s*;?""", content):
        rp = m.group(2)
        rf = workspace_path / rp
        if not rf.is_file():
            rf = workspace_path / (rp + ".js")
        if not rf.is_file():
            content = content.replace(m.group(0), f"// REMOVED: {m.group(0).strip()} — file not found")
            warnings.append(f"Removed: {rp}")
    return content, warnings


# ═══════════════════════════════════════════════════════
# SECTION 9: 死路由 + env + 同步
# ═══════════════════════════════════════════════════════

def _clean_dead_routes(workspace_path: Path) -> list:
    """清理 router/index.js 中指向不存在文件的死路由（注释整条路由记录）。"""
    router = workspace_path / "src" / "router" / "index.js"
    if not router.exists():
        return []

    content = router.read_text("utf-8", errors="replace")
    lines = content.split('\n')
    removed = []
    revived = []

    actions = []
    for i, line in enumerate(lines):
        m = re.match(r'^(\s*)(?://\s*(?:\[DEAD\]\s*)*)?(.*import\s*\(\s*[\'"]@/([^\'"]+\.vue)[\'"]\s*\).*)', line)
        if not m:
            continue
        indent, rest, import_path = m.group(1), m.group(2), m.group(3)
        dead_prefix = line.strip().startswith("// [DEAD]")
        target = workspace_path / "src" / import_path

        if dead_prefix:
            if target.exists():
                actions.append((i, import_path, 'revive', indent, rest))
            continue
        if not target.exists():
            actions.append((i, import_path, 'dead', indent, rest))

    if not actions:
        return []

    for item in reversed(actions):
        line_idx, import_path, action = item[0], item[1], item[2]
        if action == 'revive':
            indent, rest = item[3], item[4]
            clean_line = re.sub(r'\s*—\s*文件不存在\s*$', '', rest)
            lines[line_idx] = indent + clean_line
            revived.append(import_path)
            continue
        if action == 'dead':
            start_idx = line_idx
            depth = 0
            for j in range(line_idx, -1, -1):
                l = lines[j]
                depth += l.count('}') - l.count('{')
                if '{' in l and depth < 0:
                    start_idx = j; break
            end_idx = line_idx
            depth = 0
            for j in range(start_idx, len(lines)):
                l = lines[j]
                depth += l.count('{') - l.count('}')
                if '}' in l and depth <= 0:
                    end_idx = j; break
            for j in range(start_idx, end_idx + 1):
                lc = lines[j]
                if lc.strip() and not lc.strip().startswith('//'):
                    lines[j] = '// [DEAD] ' + lc
            removed.append(import_path)

    new_content = '\n'.join(lines)
    if new_content != content:
        router.write_text(new_content, "utf-8")

    result = []
    if removed:
        result.append(f"注释 {len(removed)} 个死路由: {', '.join(removed)}")
    if revived:
        result.append(f"恢复 {len(revived)} 个已复活路由: {', '.join(revived)}")
    return result


def _sync_project_env_files(workspace_path: Path):
    """将 .env 同步到 .env.example / .env.development / .env.production。"""
    env_master = workspace_path / ".env"
    if not env_master.exists():
        return
    for fname in [".env.example", ".env.development", ".env.production"]:
        shutil.copy2(str(env_master), str(workspace_path / fname))


def _env_sweep(workspace_path: Path) -> list:
    """扫描代码 process.env.X → 补齐 env 文件缺失变量。"""
    warnings = []

    code_vars = set()
    for root, dirs, files in os.walk(str(workspace_path)):
        dirs[:] = [d for d in dirs if d not in ('node_modules', '.git', '.meta', 'test', 'Memory', 'doc', 'report')]
        for fn in files:
            if not fn.endswith(('.js', '.vue')):
                continue
            try:
                code_vars.update(re.findall(r'process\.env\.(\w+)',
                    Path(os.path.join(root, fn)).read_text('utf-8')))
            except (UnicodeDecodeError, OSError):
                pass

    

    if not code_vars:
        return warnings

    defaults = {
        'PORT': '3000', 'NODE_ENV': 'development',
        'DB_HOST': 'localhost', 'DB_PORT': '3306', 'DB_USER': 'root',
        'DB_PASSWORD': 'your_db_password', 'DB_NAME': 'testdb',
        'JWT_SECRET': 'your_jwt_secret', 'JWT_EXPIRES_IN': '7d',
        'JWT_REFRESH_SECRET': 'your_refresh_secret',
        'ENCRYPTION_KEY': 'your_encryption_key_32chars',
        'REDIS_URL': 'redis://localhost:6379/0',
        'LOG_LEVEL': 'info', 'CORS_ORIGIN': '*',
    }

    for env_name in ['.env', '.env.example', '.env.development', '.env.production']:
        env_path = workspace_path / env_name
        if not env_path.exists():
            continue
        content = env_path.read_text('utf-8')
        existing = set()
        for line in content.split('\n'):
            s = line.strip()
            if s and not s.startswith('#') and '=' in s:
                existing.add(s.split('=', 1)[0].strip())
        missing = code_vars - existing
        if missing:
            lines = content.rstrip('\n').split('\n')
            lines.append(f'\n# Auto-injected by integrator ({len(missing)} vars from code scan)')
            for var in sorted(missing):
                default_val = defaults.get(var, f"your_{var.lower()}_here")
                lines.append(f'{var}={default_val}')
            env_path.write_text('\n'.join(lines) + '\n', 'utf-8')
            warnings.append(f'{env_name}: +{len(missing)} vars')

    return warnings
