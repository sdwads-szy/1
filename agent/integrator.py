# agent/integrator.py
import asyncio
import json
import os
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
from utils.token import wrap_agent_stream
from agent.prompt_builder import build_system_prompt, build_integration_user_prompt

load_dotenv('./.env.example')
model_client = OpenAIChatCompletionClient(
    model=os.getenv("OPENAI_MODEL"),
)


async def run_integration_task(task: dict, workspace_root: str = "./project",
                               metadata_memory: dict = None,
                               extra_instructions: str = "") -> dict:
    tid = task.get("taskId") or task.get("id", "integration")
    workspace_path = Path(workspace_root).resolve()
    abs_workspace = str(workspace_path)
    workspace_path.mkdir(parents=True, exist_ok=True)

    # ── 确定性预扫描：在 LLM Agent 运行前检测断裂 ──
    pre_scan_issues = _pre_integration_scan(workspace_path)
    if pre_scan_issues:
        print(f"  [pre-scan] 发现 {len(pre_scan_issues)} 个潜在问题:")
        for issue in pre_scan_issues[:10]:
            print(f"    - {issue}")
        extra_instructions += "\n\n## [pre-scan] 预扫描发现以下断裂（优先修复）\n"
        for issue in pre_scan_issues[:20]:
            extra_instructions += f"- {issue}\n"

    if metadata_memory:
        backend_routes = metadata_memory.get("backend_routes", [])
        frontend_pages = metadata_memory.get("frontend_pages", [])
        print(f"  元数据: {len(backend_routes)} routes + {len(frontend_pages)} pages")
    else:
        backend_routes, frontend_pages = [], []

    metadata_summary = {
        "backend_routes": backend_routes,
        "frontend_pages": frontend_pages,
        "workspace": abs_workspace,
    }

    # ══ 扫描 database/*.sql 文件名，传给 Agent 维护 init-db.js 的 SQL_FILES 列表 ══
    sql_files = sorted(p.name for p in workspace_path.glob("database/*.sql") if p.is_file())
    if sql_files:
        extra_instructions += "\n\n## database/*.sql 文件列表（需列入 init-db.js 的 SQL_FILES 数组，FK 依赖序）\n"
        for f in sql_files:
            extra_instructions += f"- {f}\n"

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

    async def edit_batch(files):
        return await _edit_batch(files, workspace=abs_workspace)

    async def create_files(files, metadata=None):
        return await _create_files(files, overwrite=True, workspace=abs_workspace, metadata=metadata)

    from Tools.rag.search_rag import make_search_rag
    from Tools.rag.search_code import make_search_code
    search_rag = make_search_rag(tid, "code_generator")
    search_code = make_search_code(tid)

    instructions = build_system_prompt("integration", abs_workspace, extra_instructions, task=task)
    user_prompt = build_integration_user_prompt(task, metadata_summary)

    agent = Agent(
        name=f"integrator_{tid}",
        description="集成工程师",
        instructions=instructions,
        model_client=model_client,
        tools=[read_files, edit_batch, create_files, search_rag, search_code],
        max_iterations=4,
    )

    agent_log_dir = parent_dir / "Memory" / "agent_logs" / "engineer" / tid
    agent_log_dir.mkdir(parents=True, exist_ok=True)

    collected_messages = []
    try:
        async for event in wrap_agent_stream(
            agent, user_prompt, "integrator",
            model=model_client.model, task_id=tid,
            save_dir=str(agent_log_dir), save_filename="integrator_token",
        ):
            collected_messages.append(str(event))
    except Exception as e:
        from utils.logger import log_error
        log_error("integrator agent stream failed", task=tid, error=str(e)[:200])
        pass

    (agent_log_dir / "integrator_raw.md").write_text(
        "\n".join(collected_messages), encoding="utf-8")

    # 后处理
    post_warnings = _post_process_integrator_output(workspace_path)

    return {
        "task_id": tid,
        "success": True,
        "error": None,
        "metadata": {"post_warnings": post_warnings},
    }


def _pre_integration_scan(workspace_path: Path) -> list:
    """确定性预扫描：在 LLM Agent 运行前检测所有可自动发现的断裂。返回问题列表。"""
    import re
    ws = workspace_path
    issues = []

    # ── 1. 全量 require/import 路径扫描 ──
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
                # 尝试加扩展名
                found = resolved.exists()
                if not found:
                    for ext in [".js", ".vue", "/index.js"]:
                        if Path(str(resolved) + ext).exists():
                            found = True
                            break
                if not found:
                    issues.append(f"[missing require] {rel_src} -> {target}")

        # ESM static import (skip bare modules like 'vue', 'express'; only check project paths)
        for m in re.finditer(r"""from\s+['\"]([^'\"]+)['\"]""", content):
            target = m.group(1)
            if target.startswith("."):
                # relative path — resolve against the source file's directory
                resolved = (src_file.parent / target).resolve()
            elif target.startswith("@/"):
                # project alias — resolve against workspace src/
                resolved = (ws / target.replace("@/", "src/", 1)).resolve()
            else:
                continue  # bare module (npm package), skip
            found = resolved.exists()
            if not found:
                for ext in [".js", ".vue", "/index.js"]:
                    if Path(str(resolved) + ext).exists():
                        found = True
                        break
            if not found:
                issues.append(f"[missing import] {rel_src} -> {m.group(1)}")

        # Dynamic import() — only check project paths, skip bare modules
        for m in re.finditer(r"""import\s*\(\s*['\"]([^'\"]+)['\"]\s*\)""", content):
            target = m.group(1)
            if target.startswith("@/"):
                target = target.replace("@/", "src/", 1)
            elif target.startswith("."):
                pass  # relative path
            else:
                continue  # bare module (npm package), skip
            resolved = (ws / target).resolve()
            found = resolved.exists()
            if not found:
                for ext in [".js", ".vue"]:
                    if Path(str(resolved) + ext).exists():
                        found = True
                        break
            if not found:
                issues.append(f"[missing lazy import] {rel_src} -> {m.group(1)}")

    # ── 2. package.json scripts 文件存在性 ──
    pkg_json = ws / "package.json"
    if pkg_json.exists():
        import json
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

    # ── 3. app.js 中 require 的路由文件存在性 ──
    app_js = ws / "app.js"
    if app_js.exists():
        content = app_js.read_text("utf-8", errors="replace")
        for m in re.finditer(r"""require\s*\(\s*['\"](\./routes/[^'\"]+)['\"]\s*\)""", content):
            route_file = ws / (m.group(1) + ("" if m.group(1).endswith(".js") else ".js"))
            if not route_file.exists():
                issues.append(f"[missing route] app.js 引用了不存在的路由文件: {m.group(1)}")

    return issues


def _post_process_integrator_output(workspace_path: Path) -> list:
    """后处理：修复多路由导出 + 自动注入缺失路由 + env 补齐。"""
    import re, subprocess

    app_js = workspace_path / "app.js"
    if not app_js.exists():
        return ["app.js not found"]

    content = app_js.read_text("utf-8")
    original = content
    warnings = []

    # Step 1: 发现磁盘路由文件 + 自动注入缺失的挂载
    routes_dir = workspace_path / "routes"
    disk_routes = {}
    if routes_dir.exists():
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
            stem = Path(rel).stem
            parts = rel.replace("routes/", "").replace(".js", "").split("/")
            vn = parts[0] + "".join(p.capitalize() for p in parts[1:]) + "Routes"
            new_mounts.append((rel, vn, base_path))
            mounted[rel] = vn

    if new_mounts:
        req_lines = [f"const {v} = require('./{r.replace('.js', '')}');" for r, v, _ in new_mounts]
        use_lines = []
        for _, v, bp in new_mounts:
            path = bp if bp else "/api/" + Path(rel).stem
            use_lines.append(f"app.use('{path}', {v});")
        injection = "\n" + "\n".join(req_lines) + "\n" + "\n".join(use_lines)
        if "// ROUTES_INJECTION_POINT" in content:
            content = content.replace("// ROUTES_INJECTION_POINT", injection + "\n// ROUTES_INJECTION_POINT")
        else:
            content = content.replace("app.listen", injection + "\n\napp.listen")
        warnings.append(f"Auto-injected {len(new_mounts)} routes")

    # Step 2: 多路由导出展开
    route_vars = {}
    for m in re.finditer(r"const\s+(\w+)\s*=\s*require\(['\"](\./routes/[^'\"]+)['\"]\)", content):
        route_vars[m.group(1)] = m.group(2)

    for var_name, route_rel in route_vars.items():
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
            replacement = f"app.use({path}, {var_name}.{prop1});\napp.use({path}, {var_name}.{prop2})"
            content = content.replace(um.group(0), replacement)
            break

    # Step 3: 清理不存在文件的 require
    for m in re.finditer(r"""(?:const|let|var)\s+(\w+)\s*=\s*require\s*\(\s*['\"](\.[^'\"]+)['\"]\s*\)\s*;?""", content):
        rp = m.group(2)
        rf = workspace_path / rp
        if not rf.is_file():
            rf = workspace_path / (rp + ".js")
        if not rf.is_file():
            content = content.replace(m.group(0), f"// REMOVED: {m.group(0).strip()} — file not found")
            warnings.append(f"Removed: {rp}")

    if content != original:
        app_js.write_text(content, "utf-8")
        r = subprocess.run(["node", "--check", str(app_js)], capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            warnings.append(f"app.js syntax: {(r.stderr or '')[:200]}")

    # Step 4: env sweep
    env_warnings = _env_sweep(workspace_path)
    warnings.extend(env_warnings)

    return warnings


def _env_sweep(workspace_path: Path) -> list:
    """扫描代码 process.env.X → 补齐 env 文件缺失变量。"""
    import re, os as _os
    warnings = []

    code_vars = set()
    for root, dirs, files in _os.walk(str(workspace_path)):
        dirs[:] = [d for d in dirs if d not in ('node_modules', '.git', '.meta', 'test', 'Memory', 'doc', 'report')]
        for fn in files:
            if not fn.endswith(('.js', '.vue')):
                continue
            try:
                code_vars.update(re.findall(r'process\.env\.(\w+)', Path(_os.path.join(root, fn)).read_text('utf-8')))
            except (UnicodeDecodeError, OSError):
                pass  # skip binary/unreadable files

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
                lines.append(f'{var}={defaults.get(var, f"your_{var.lower()}_here")}')
            env_path.write_text('\n'.join(lines) + '\n', 'utf-8')
            warnings.append(f'{env_name}: +{len(missing)} vars')

    return warnings
