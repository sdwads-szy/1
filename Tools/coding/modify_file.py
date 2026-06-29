from pathlib import Path
from typing import Dict, Any

def _is_within_workspace(path: Path, workspace_root: Path) -> bool:
    try:
        path.relative_to(workspace_root)
        return True
    except ValueError:
        return False

async def modify_file(
    file_path: str,
    old_string: str,
    new_string: str,
    allow_multiple: bool = False,
    workspace: str = ""
) -> Dict[str, Any]:
    """
    在文件中用 new_string 替换 old_string（受工作区限制）。

    参数:
        file_path: 文件路径（相对或绝对，但必须在工作区内）
        old_string: 要替换的原字符串
        new_string: 替换后的新字符串
        allow_multiple: 是否允许替换多处（默认 False，要求唯一出现）
        workspace: 工作区根目录（绝对路径）。如果为空字符串，使用当前工作目录。

    返回:
        {"success": bool, "path": str, "replaced": bool, "error": str or None}
    """
    if workspace:
        base = Path(workspace).resolve()
        if not base.exists():
            return {
                "success": False,
                "path": str(base),
                "replaced": False,
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
                "replaced": False,
                "error": f"Access denied: path outside workspace. Workspace: {base}"
            }
    else:
        target = base / file_path

    target = target.resolve()
    if not _is_within_workspace(target, base):
        return {
            "success": False,
            "path": str(target),
            "replaced": False,
            "error": f"Access denied: resolved path outside workspace. Workspace: {base}"
        }

    if not target.exists():
        return {
            "success": False,
            "path": str(target),
            "replaced": False,
            "error": f"File not found: {file_path}"
        }

    try:
        original = target.read_text(encoding='utf-8')
    except Exception as e:
        return {
            "success": False,
            "path": str(target),
            "replaced": False,
            "error": f"Failed to read file: {str(e)}"
        }

    count = original.count(old_string)
    if count == 0:
        return {
            "success": False,
            "path": str(target),
            "replaced": False,
            "error": f"String not found: '{old_string[:50]}...'"
        }
    if count > 1 and not allow_multiple:
        return {
            "success": False,
            "path": str(target),
            "replaced": False,
            "error": f"Found {count} occurrences of '{old_string[:50]}...'. Use allow_multiple=True to replace all."
        }

    new_content = original.replace(old_string, new_string) if allow_multiple else original.replace(old_string, new_string, 1)

    try:
        target.write_text(new_content, encoding='utf-8')
        return {
            "success": True,
            "path": str(target),
            "replaced": True,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "path": str(target),
            "replaced": False,
            "error": f"Failed to write file: {str(e)}"
        }