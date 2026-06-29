# brainAgent/run_integration.py
"""
独立集成运行器 — 扫描 workspace 中已有的后端路由和前端页面，重新运行集成 Agent。

用法:
    python brainAgent/run_integration.py
    python brainAgent/run_integration.py --workspace work/project
    python brainAgent/run_integration.py --task-file work/project/task/task_xxx.json
"""

import asyncio, json, sys, re, argparse
from pathlib import Path
from datetime import datetime

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from agent.integrator import run_integration_task
from utils.dependency_graph import _get_tid

WORKSPACE_DEFAULT = project_root / "work" / "project"
TASK_DIR = project_root / "work" / "project" / "task"


def find_latest_task() -> Path:
    files = list(TASK_DIR.glob("task_*.json"))
    if not files:
        raise FileNotFoundError(f"No task files in {TASK_DIR}")
    return max(files, key=lambda p: p.stat().st_mtime)


def find_integration_task(tasks: list) -> dict | None:
    for t in tasks:
        ttype = t.get("type", "")
        if ttype in ("integration", "integrate"):
            return t
    return None


def scan_backend_routes(workspace: Path) -> list:
    routes = []
    routes_dir = workspace / "routes"
    if not routes_dir.exists():
        return routes
    for rf in sorted(routes_dir.rglob("*.js")):
        try:
            content = rf.read_text("utf-8", errors="replace")
        except Exception:
            continue
        rel = str(rf.relative_to(workspace)).replace("\\", "/")
        mount_match = re.search(r'@mount\s+(/\S+)', content)
        base_path = mount_match.group(1) if mount_match else ""
        methods = []
        for m in re.finditer(r'router\.(get|post|put|delete|patch)\s*\(\s*[\'\"]([^\'\"]+)', content):
            methods.append({"method": m.group(1).upper(), "path": m.group(2)})
        if base_path or methods:
            routes.append({"routeFile": rel, "basePath": base_path, "methods": methods})
    return routes


def scan_frontend_pages(workspace: Path) -> list:
    pages = []
    api_calls = []
    src_dir = workspace / "src"
    if not src_dir.exists():
        return pages
    for vf in sorted(src_dir.rglob("*.vue")):
        rel = str(vf.relative_to(workspace)).replace("\\", "/")
        try:
            content = vf.read_text("utf-8", errors="replace")[:2000]
        except Exception:
            content = ""
        name = vf.stem
        route_meta = {}
        if "requiresAdmin" in content:
            route_meta["requiresAdmin"] = True
        pages.append({"component": name, "file": rel, "meta": route_meta if route_meta else None})
    api_dir = src_dir / "api"
    if api_dir.exists():
        for af in sorted(api_dir.rglob("*.js")):
            rel = str(af.relative_to(workspace)).replace("\\", "/")
            try:
                content = af.read_text("utf-8", errors="replace")
            except Exception:
                continue
            endpoints = []
            for m in re.finditer(r"""request\s*\(\s*\{\s*url:\s*['\"]([^'\"]+)['\"]\s*,\s*method:\s*['\"]([^'\"]+)['\"]""", content):
                endpoints.append(f"{m.group(2).upper()} {m.group(1)}")
            if endpoints:
                api_calls.append({"from": rel, "endpoints": endpoints})
    return pages


def build_metadata(workspace: Path) -> dict:
    backend_routes = scan_backend_routes(workspace)
    frontend_pages = scan_frontend_pages(workspace)
    print(f"  扫描结果: {len(backend_routes)} routes + {len(frontend_pages)} pages")
    if backend_routes:
        for r in backend_routes:
            methods_str = ", ".join(f"{m['method']} {m['path']}" for m in r.get("methods", [])[:3])
            print(f"    route: {r['routeFile']} -> {r['basePath']} [{methods_str}]")
    if frontend_pages:
        for p in frontend_pages[:10]:
            print(f"    page: {p['file']} ({p['component']})")
    return {"backend_routes": backend_routes, "frontend_pages": frontend_pages}


async def run(workspace: str | Path = None, task_file: str | Path = None):
    workspace = Path(workspace) if workspace else WORKSPACE_DEFAULT
    workspace = workspace.resolve()
    if not workspace.exists():
        print(f"错误: workspace 不存在 - {workspace}")
        return

    if task_file:
        task_path = Path(task_file)
    else:
        task_path = find_latest_task()
    if not task_path.exists():
        print(f"错误: task 文件不存在 - {task_path}")
        return

    print(f"{'='*60}")
    print(f"  独立集成运行器")
    print(f"  Workspace: {workspace}")
    print(f"  Task:      {task_path.name}")
    print(f"{'='*60}")

    data = json.loads(task_path.read_text("utf-8"))
    tasks = data.get("tasks", data if isinstance(data, list) else [])

    integration_task = find_integration_task(tasks)
    if not integration_task:
        print("错误: 未找到 integration 任务")
        return
    print(f"\n集成任务: {_get_tid(integration_task)} - {integration_task.get('description', '')[:80]}")

    print(f"\n[扫描] 构建元数据...")
    metadata = build_metadata(workspace)

    if not metadata["backend_routes"] and not metadata["frontend_pages"]:
        print("\n警告: 未扫描到任何 routes 或 pages")

    print(f"\n[执行] 启动集成 Agent...")
    t0 = datetime.now()
    try:
        result = await run_integration_task(
            integration_task,
            workspace_root=str(workspace),
            metadata_memory=metadata,
        )
        duration = (datetime.now() - t0).total_seconds()
        success = result.get("success", False)
        print(f"\n{'OK' if success else 'FAIL'} 集成完成 ({duration:.1f}s)")
        post_warnings = result.get("metadata", {}).get("post_warnings", [])
        if post_warnings:
            print(f"  后处理警告 ({len(post_warnings)}):")
            for w in post_warnings[:10]:
                print(f"    - {w}")
    except Exception as e:
        import traceback
        print(f"\n集成失败: {e}")
        traceback.print_exc()


async def main():
    parser = argparse.ArgumentParser(description="独立集成运行器")
    parser.add_argument("--workspace", type=str, help="项目 workspace 路径")
    parser.add_argument("--task-file", type=str, help="架构任务文件路径")
    args = parser.parse_args()
    await run(workspace=args.workspace, task_file=args.task_file)


if __name__ == "__main__":
    asyncio.run(main())
