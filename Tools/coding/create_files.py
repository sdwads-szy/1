# Tools/coding/create_files.py
"""批量创建文件 — 一次调用创建所有文件，避免逐个调用浪费迭代"""

import os as _os
from pathlib import Path
from typing import Dict, Any, List


def _resolve(target: Path, base: Path) -> Path:
    """Resolve a file path relative to base.
    不使用 Path.resolve() — Windows 上会调用 GetFinalPathNameByHandle，
    多线程并发 mkdir 时可能因父目录尚未稳定而返回异常路径，
    导致后续 relative_to(base) 误判为越权访问。
    """
    if target.is_absolute():
        return Path(_os.path.normpath(str(target)))
    return Path(_os.path.normpath(str(base / target)))


async def create_files(
    files: List[Dict[str, str]],
    overwrite: bool = True,
    workspace: str = "",
    metadata: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    批量创建多个文件，一次调用完成。文件间并行执行。
    可选传入 metadata，工具自动保存到 .meta/task_{taskId}.json。

    Args:
        files: [{"path": "routes/auth.js", "content": "完整代码..."}, ...]
        overwrite: 是否覆盖已存在的文件（默认 True）
        workspace: 工作区根目录（绝对路径）
        metadata: 可选，任务元数据（含 taskId, type, createdFiles, routes 等）。
                  工具自动以 JSON 保存到 .meta/task_{taskId}.json

    Returns:
        {"success": bool, "results": [...], "summary": str, "meta_saved": bool|null}
    """
    base = Path(workspace).resolve() if workspace else Path.cwd().resolve()
    if not base.exists():
        return {"success": False, "results": [], "error": f"Workspace does not exist: {workspace}"}

    if not files:
        return {"success": True, "results": [], "note": "No files to create"}

    from concurrent.futures import ThreadPoolExecutor

    def create_one(fe):
        fp = fe.get("path", fe.get("file", ""))
        content = fe.get("content", "")
        if not fp:
            return {"path": "", "created": False, "error": "Missing path"}

        target = _resolve(Path(fp), base)
        # 用 normpath + startswith 替代 relative_to — 避免 Windows resolve()
        # 在多线程并发 mkdir 时调用 GetFinalPathNameByHandle 失败导致误判
        target_s = str(target)
        base_s = str(base)
        if not target_s.startswith(base_s + _os.sep) and target_s != base_s:
            return {"path": fp, "created": False, "error": "Access denied: outside workspace"}

        # ── 路径合法性校验 ──
        path_err = _validate_path(fp)
        if path_err:
            return {"path": fp, "created": False, "error": f"Path rejected: {path_err}"}

        if target.exists() and not overwrite:
            return {"path": fp, "created": False, "lines": 0, "bytes": 0,
                    "error": "File exists, overwrite=False"}

        # JSON 预校验
        if target.suffix == '.json':
            import json as _json
            try:
                _json.loads(content)
            except _json.JSONDecodeError as je:
                return {"path": fp, "created": False,
                        "error": f"JSON invalid at line {je.lineno}: {je.msg}"}

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding='utf-8')
            lines = content.count('\n') + 1
            nbytes = len(content.encode('utf-8'))
            return {"path": fp, "created": True, "lines": lines, "bytes": nbytes}
        except Exception as e:
            return {"path": fp, "created": False, "error": str(e)}

    with ThreadPoolExecutor(max_workers=len(files)) as pool:
        results = list(pool.map(create_one, files))

    n_created = sum(1 for r in results if r.get("created"))
    n_failed = sum(1 for r in results if not r.get("created"))

    # 自动保存元数据（避免 agent 二次调用只为了输出 METADATA）
    meta_saved = None
    if metadata and isinstance(metadata, dict):
        task_id = metadata.get("taskId", metadata.get("task_id", ""))
        if task_id and n_created > 0:
            # 自动填充 createdFiles
            if "createdFiles" not in metadata:
                metadata["createdFiles"] = [
                    r["path"] for r in results if r.get("created")
                ]
            meta_dir = base / ".meta"
            meta_dir.mkdir(parents=True, exist_ok=True)
            meta_path = meta_dir / f"task_{task_id}.json"
            try:
                import json as _json
                meta_path.write_text(
                    _json.dumps(metadata, indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )
                meta_saved = str(meta_path)
            except Exception:
                pass

    return {
        "success": n_failed == 0,
        "results": results,
        "summary": f"Created {n_created}/{len(files)} files" + (f", {n_failed} failed" if n_failed else ""),
        "meta_saved": meta_saved,
    }


def _validate_path(fp: str) -> str:
    """校验文件路径是否合法。返回错误信息字符串，合法则返回空字符串。"""
    p = fp.replace("\\", "/")

    # 提取 workspace 内的相对路径 (去掉绝对路径前缀)
    if "/work/project/" in p:
        p = p.split("/work/project/", 1)[1]

    # 禁止的目录名映射 (Agent 常见编造 → 正确目录)
    _FORBIDDEN_DIRS = {
        "db/":        "database/",
        "schema/":    "database/",
        "models/":    "src/pages/",
        "views/":     "src/pages/",
        "components/":"src/components/",
    }

    for wrong, correct in _FORBIDDEN_DIRS.items():
        if p.startswith(wrong):
            return f"禁止使用 '{wrong}' 目录，应使用 '{correct}'"

    # 测试文件必须在 test/ 下
    if p.endswith(".test.js") or p.endswith(".spec.js"):
        if not p.startswith("test/"):
            return "测试文件必须在 test/ 目录下"

    # DDL 文件必须在 database/ 下
    if p.endswith(".sql") and not p.startswith("database/"):
        return "SQL 文件必须在 database/ 目录下"

    # 前端页面必须在 src/pages/ 下
    if p.endswith(".vue") and not p.startswith("src/"):
        return ".vue 文件必须在 src/ 目录下"

    # API 模块必须在 src/api/ 下
    if "/api/" in p and p.endswith(".js") and not p.startswith("src/"):
        return "API 模块必须在 src/ 目录下"

    return ""
