from pathlib import Path
from typing import Dict, Any

def _is_within_workspace(path: Path, workspace_root: Path) -> bool:
    try:
        path.relative_to(workspace_root)
        return True
    except ValueError:
        return False

async def delete_file(
    file_path: str,
    confirm: bool = False,
    workspace: str = ""
) -> Dict[str, Any]:
    """
    删除指定文件（受工作区限制）。

    参数:
        file_path: 文件路径（相对或绝对，但必须在工作区内）
        confirm: 必须为 True 才能执行删除（安全开关）
        workspace: 工作区根目录（绝对路径）。如果为空字符串，使用当前工作目录。

    返回:
        {"success": bool, "path": str, "error": str or None}
    """
    if workspace:
        base = Path(workspace).resolve()
        if not base.exists():
            return {
                "success": False,
                "path": str(base),
                "error": f"Workspace does not exist: {workspace}"
            }
    else:
        base = Path.cwd().resolve()

    target = Path(file_path)
    if target.is_absolute():
        if not _is_within_workspace(target, base):
            return {
                "success": False,
                "path": str(target),
                "error": f"Access denied: path outside workspace. Workspace: {base}"
            }
    else:
        target = base / file_path

    target = target.resolve()
    if not _is_within_workspace(target, base):
        return {
            "success": False,
            "path": str(target),
            "error": f"Access denied: resolved path outside workspace. Workspace: {base}"
        }

    if not target.exists():
        return {
            "success": False,
            "path": str(target),
            "error": f"File not found: {file_path}"
        }

    if not confirm:
        return {
            "success": False,
            "path": str(target),
            "error": "Deletion requires confirm=True (safety measure)"
        }

    try:
        target.unlink()
        return {
            "success": True,
            "path": str(target),
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "path": str(target),
            "error": f"Failed to delete: {str(e)}"
        }