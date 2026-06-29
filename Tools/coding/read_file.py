from pathlib import Path
from typing import Dict, Any

def _is_within_workspace(path: Path, workspace_root: Path) -> bool:
    """检查路径是否在工作区根目录内"""
    try:
        path.relative_to(workspace_root)
        return True
    except ValueError:
        return False

async def read_file(
    file_path: str,
    workspace: str = ""
) -> Dict[str, Any]:
    """
    读取文件内容（受工作区限制）。

    参数:
        file_path: 目标文件路径（可以是相对路径，或相对于 workspace 的路径）
        workspace: 工作区根目录（绝对路径）。如果为空字符串，则使用当前工作目录。

    返回:
        {"success": bool, "content": str, "error": str or None, "path": str}
    """
    # 确定工作区根目录
    if workspace:
        base = Path(workspace).resolve()
        if not base.exists():
            return {
                "success": False,
                "content": "",
                "error": f"Workspace does not exist: {workspace}",
                "path": str(base)
            }
    else:
        base = Path.cwd().resolve()

    # 解析目标路径
    target = Path(file_path)
    if target.is_absolute():
        if not _is_within_workspace(target, base):
            return {
                "success": False,
                "content": "",
                "error": f"Access denied: path outside workspace. Workspace: {base}",
                "path": str(target)
            }
    else:
        target = base / file_path

    target = target.resolve()
    if not _is_within_workspace(target, base):
        return {
            "success": False,
            "content": "",
            "error": f"Access denied: resolved path outside workspace. Workspace: {base}",
            "path": str(target)
        }

    if not target.exists():
        return {
            "success": False,
            "content": "",
            "error": f"File not found: {file_path}",
            "path": str(target)
        }

    if not target.is_file():
        return {
            "success": False,
            "content": "",
            "error": f"Path is not a file: {file_path}",
            "path": str(target)
        }

    try:
        content = target.read_text(encoding='utf-8')
        return {
            "success": True,
            "content": content,
            "error": None,
            "path": str(target)
        }
    except Exception as e:
        return {
            "success": False,
            "content": "",
            "error": f"Failed to read file: {str(e)}",
            "path": str(target)
        }