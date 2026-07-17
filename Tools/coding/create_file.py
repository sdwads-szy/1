from pathlib import Path
from typing import Dict, Any

def _is_within_workspace(path: Path, workspace_root: Path) -> bool:
    """检查路径是否在工作区根目录内"""
    try:
        path.relative_to(workspace_root)
        return True
    except ValueError:
        return False

async def create_file(
    file_path: str,
    content: str = "",
    overwrite: bool = False,
    workspace: str = ""
) -> Dict[str, Any]:
    """
    创建新文件并写入内容（受工作区限制）。
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
        # 默认 workspace 为项目根（此文件在 Tools/coding/ 下，项目根在上两级）
        base = (Path(__file__).resolve().parent.parent.parent)
        if not base.exists():
            base = Path.cwd().resolve()

    # 解析目标路径
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

    if target.exists() and not overwrite:
        return {
            "success": False,
            "path": str(target),
            "error": f"File already exists: {file_path}. Use overwrite=True to replace."
        }

    # JSON 文件先校验再写入
    if target.suffix == '.json':
        import json as _json
        try: _json.loads(content)
        except _json.JSONDecodeError as je:
            return {"success": False, "path": str(target),
                    "error": f"JSON invalid at line {je.lineno}: {je.msg} — create rejected"}

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
        lines = content.count('\n') + 1
        return {
            "success": True,
            "path": str(target),
            "message": f"Created: {target.name} ({lines} lines, {len(content.encode('utf-8'))} bytes)",
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "path": str(target),
            "error": f"Failed to write file: {str(e)}"
        }