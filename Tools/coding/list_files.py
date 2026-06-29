# Tools/coding/list_files.py
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Union

def _is_within_workspace(path: Path, workspace_root: Path) -> bool:
    try:
        path.relative_to(workspace_root)
        return True
    except ValueError:
        return False

async def list_files(
    directory: Union[str, List[str]],
    workspace: str = ""
) -> Dict[str, Any]:
    """
    列出工作区内指定目录（一个或多个）下的所有文件（递归），返回相对路径列表。
    排除目录硬编码：node_modules, .git, __pycache__, dist, build, .venv, env。

    参数:
        directory: 相对于 workspace 的目录路径（可以是 "."），或多个路径用逗号分隔的字符串，
                   或 JSON 数组字符串，或 Python 列表。
        workspace: 工作区根目录（绝对路径）。如果为空字符串，使用当前工作目录。

    返回:
        {"success": bool, "files": List[str], "error": str or None, "warnings": List[str] | None}
    """
    exclude_dirs = ["node_modules", ".git", "__pycache__", "dist", "build", ".venv", "env"]

    if workspace:
        base = Path(workspace).resolve()
        if not base.exists():
            return {
                "success": False,
                "files": [],
                "error": f"Workspace does not exist: {workspace}",
                "warnings": None
            }
    else:
        base = Path.cwd().resolve()

    # 解析目录列表
    dirs = []
    if isinstance(directory, str):
        # 尝试解析为 JSON 数组字符串
        stripped = directory.strip()
        if stripped.startswith('[') and stripped.endswith(']'):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    dirs = [str(d).strip() for d in parsed if d]
                else:
                    dirs = [directory]
            except json.JSONDecodeError:
                # 不是 JSON，当作逗号分隔或单个路径
                if ',' in directory:
                    dirs = [d.strip() for d in directory.split(',') if d.strip()]
                else:
                    dirs = [directory.strip()]
        else:
            # 普通字符串，按逗号分隔或单个
            if ',' in directory:
                dirs = [d.strip() for d in directory.split(',') if d.strip()]
            else:
                dirs = [directory.strip()]
    elif isinstance(directory, list):
        dirs = [str(d).strip() for d in directory if d]
    else:
        return {
            "success": False,
            "files": [],
            "error": "Invalid directory parameter. Expected string or list.",
            "warnings": None
        }

    if not dirs:
        return {
            "success": False,
            "files": [],
            "error": "No valid directory provided.",
            "warnings": None
        }

    all_files = []
    warnings = []

    for dir_str in dirs:
        target_dir = Path(dir_str)
        if target_dir.is_absolute():
            if not _is_within_workspace(target_dir, base):
                warnings.append(f"Access denied: {dir_str} outside workspace.")
                continue
        else:
            target_dir = base / dir_str

        target_dir = target_dir.resolve()
        if not _is_within_workspace(target_dir, base):
            warnings.append(f"Access denied: resolved path {target_dir} outside workspace.")
            continue

        if not target_dir.exists():
            warnings.append(f"Directory not found: {dir_str}")
            continue

        for root, dirs_list, filenames in os.walk(target_dir):
            dirs_list[:] = [d for d in dirs_list if d not in exclude_dirs]
            for filename in filenames:
                full_path = Path(root) / filename
                rel_path = full_path.relative_to(base)
                all_files.append(str(rel_path).replace('\\', '/'))

    all_files = sorted(set(all_files))

    return {
        "success": True,
        "files": all_files,
        "error": None,
        "warnings": warnings if warnings else None
    }