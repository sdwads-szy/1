# Tools/coding/modify_files.py
"""批量修改文件 — 一次调用完成多个文件的字符串替换"""

import os as _os
from pathlib import Path
from typing import Dict, Any, List


def _resolve(target: Path, base: Path) -> Path:
    if target.is_absolute():
        return Path(_os.path.normpath(str(target)))
    return Path(_os.path.normpath(str(base / target)))


def _is_within_workspace(path: Path, workspace_root: Path) -> bool:
    try:
        path.relative_to(workspace_root)
        return True
    except ValueError:
        return False


async def modify_files(
    edits: List[Dict[str, Any]],
    workspace: str = "",
) -> Dict[str, Any]:
    """
    批量修改多个文件，一次调用完成。文件间并行执行。

    Args:
        edits: [{"file_path": "routes/auth.js", "old_string": "...", "new_string": "...", "allow_multiple": false}, ...]
        workspace: 工作区根目录（绝对路径）

    Returns:
        {"success": bool, "results": [...], "summary": str}
    """
    base = Path(workspace).resolve() if workspace else Path.cwd().resolve()
    if not base.exists():
        return {"success": False, "results": [], "summary": f"Workspace does not exist: {workspace}"}

    results = []
    ok_count = 0
    fail_count = 0

    for i, edit in enumerate(edits):
        file_path = edit.get("file_path", "")
        old_string = edit.get("old_string", "")
        new_string = edit.get("new_string", "")
        allow_multiple = edit.get("allow_multiple", False)

        target = _resolve(Path(file_path), base)
        if not _is_within_workspace(target, base):
            results.append({"index": i, "file": file_path, "ok": False,
                           "error": f"Access denied: path outside workspace"})
            fail_count += 1
            continue

        if not target.exists():
            results.append({"index": i, "file": file_path, "ok": False,
                           "error": f"File not found: {file_path}"})
            fail_count += 1
            continue

        try:
            original = target.read_text(encoding='utf-8')
        except Exception as e:
            results.append({"index": i, "file": file_path, "ok": False,
                           "error": f"Failed to read: {e}"})
            fail_count += 1
            continue

        count = original.count(old_string)
        if count == 0:
            results.append({"index": i, "file": file_path, "ok": False,
                           "error": f"String not found: '{old_string[:50]}...'"})
            fail_count += 1
            continue
        if count > 1 and not allow_multiple:
            results.append({"index": i, "file": file_path, "ok": False,
                           "error": f"Found {count} occurrences. Use allow_multiple=True"})
            fail_count += 1
            continue

        new_content = original.replace(old_string, new_string) if allow_multiple else original.replace(old_string, new_string, 1)
        try:
            target.write_text(new_content, encoding='utf-8')
            results.append({"index": i, "file": file_path, "ok": True,
                           "replaced": True, "occurrences": count if allow_multiple else 1})
            ok_count += 1
        except Exception as e:
            results.append({"index": i, "file": file_path, "ok": False,
                           "error": f"Failed to write: {e}"})
            fail_count += 1

    return {
        "success": fail_count == 0,
        "results": results,
        "summary": f"{ok_count} modified, {fail_count} failed"
    }
