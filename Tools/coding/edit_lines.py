# Tools/coding/edit_lines.py
"""代码编辑工具 — 标记定位 + 行号两种模式，支持多次调用不漂移"""

from pathlib import Path
from typing import Dict, Any


def _resolve(target: Path, base: Path) -> Path:
    if target.is_absolute():
        return target.resolve()
    return (base / target).resolve()


def _read_lines(target: Path) -> list:
    return target.read_text(encoding='utf-8').split('\n')


def _write(target: Path, lines: list):
    target.write_text('\n'.join(lines), encoding='utf-8')


# ── 标记模式（主力，多次调用不漂移） ──────────────────────────

async def replace_near(
    file_path: str,
    marker: str,
    content: str,
    lines_before: int = 0,
    lines_after: int = 0,
    workspace: str = "",
) -> Dict[str, Any]:
    """
    找到包含 marker 的行，替换该行 ± 上下文行为 content。

    Args:
        file_path: 文件路径
        marker: 用于定位的标记字符串（取文件中某行的唯一片段即可，不需要完整行）
        content: 替换后的新内容（可含换行）
        lines_before: 从 marker 行往上多替换几行（默认0，只替换 marker 行）
        lines_after: 从 marker 行往下多替换几行
        workspace: 工作区根目录

    例: 想把第 12-15 行换成新代码，取第 13 行的片段 "const dbConfig" 作为 marker
        replace_near("init-db.js", "const dbConfig", "新代码", lines_before=1, lines_after=2)
    """
    base = Path(workspace).resolve() if workspace else Path.cwd().resolve()
    target = _resolve(Path(file_path), base)

    try: target.relative_to(base)
    except ValueError:
        return {"success": False, "error": f"Access denied"}

    if not target.exists():
        return {"success": False, "error": f"File not found: {file_path}"}

    try: lines = _read_lines(target)
    except Exception as e: return {"success": False, "error": f"Read failed: {e}"}

    # 找 marker（忽略前后空白，支持多行）
    marker_lines = marker.replace('\\n', '\n').split('\n')
    first = marker_lines[0].strip()
    marker_line = None
    for i, line in enumerate(lines):
        if first and first in line.strip():
            match = True
            for k in range(1, len(marker_lines)):
                if i + k >= len(lines) or marker_lines[k].strip() not in lines[i + k].strip():
                    match = False; break
            if match:
                if marker_line is not None:
                    return {"success": False, "error": f"Marker matches multiple lines"}
                marker_line = i
    if marker_line is None:
        return {"success": False, "error": f"Marker not found: '{marker[:60]}'"}

    start = max(0, marker_line - lines_before)
    end = min(len(lines), marker_line + 1 + lines_after)

    new_lines = content.split('\n')
    replaced = lines[:start] + new_lines + lines[end:]

    try:
        _write(target, replaced)
        return {"success": True, "path": str(target),
                "line_range": f"{start+1}-{end}", "replaced_with": f"{len(new_lines)} lines"}
    except Exception as e:
        return {"success": False, "error": f"Write failed: {e}"}


async def insert_near(
    file_path: str,
    marker: str,
    content: str,
    position: str = "after",
    workspace: str = "",
) -> Dict[str, Any]:
    """
    在 marker 所在行的前面或后面插入 content（不删除原有行）。

    Args:
        position: "before" — 在 marker 行之前插入; "after" — 在 marker 行之后插入
    """
    base = Path(workspace).resolve() if workspace else Path.cwd().resolve()
    target = _resolve(Path(file_path), base)

    try: target.relative_to(base)
    except ValueError:
        return {"success": False, "error": "Access denied"}
    if not target.exists():
        return {"success": False, "error": f"File not found: {file_path}"}

    try: lines = _read_lines(target)
    except Exception as e: return {"success": False, "error": f"Read failed: {e}"}

    marker_line = None
    for i, line in enumerate(lines):
        if marker in line:
            if marker_line is not None:
                return {"success": False, "error": f"Marker matches multiple lines"}
            marker_line = i
    if marker_line is None:
        return {"success": False, "error": f"Marker not found"}

    new_lines = content.split('\n')
    if position == "before":
        replaced = lines[:marker_line] + new_lines + lines[marker_line:]
    else:
        replaced = lines[:marker_line+1] + new_lines + lines[marker_line+1:]

    try:
        _write(target, replaced)
        return {"success": True, "path": str(target), "inserted": f"{len(new_lines)} lines"}
    except Exception as e:
        return {"success": False, "error": f"Write failed: {e}"}


# ── 批量编辑（多文件并行 + 行号定位） ──────────────────────────

async def edit_batch(
    files: list,
    workspace: str = "",
) -> Dict[str, Any]:
    """
    批量修改多个文件，一次调用完成。

    files: [{"file": "path.js", "edits": [{"start": 5, "end": 7, "content": "..."}, ...]}, ...]
      start/end 为 1-indexed 行号（包含 end）。
      若 end < start，则在 start 行之前插入 content（插入模式）。
    """
    base = Path(workspace).resolve() if workspace else Path.cwd().resolve()

    from concurrent.futures import ThreadPoolExecutor

    def edit_one(fe):
        fp = fe.get("file", "")
        edits = fe.get("edits", [])
        target = _resolve(Path(fp), base)
        try:
            target.relative_to(base)
        except ValueError:
            return {"file": fp, "error": "Access denied"}
        if not target.exists():
            return {"file": fp, "error": "File not found"}

        try:
            lines = _read_lines(target)
        except Exception as e:
            return {"file": fp, "error": f"Read failed: {e}"}

        # 按 start 从大到小排序，从后往前修改，避免行号偏移
        sorted_edits = sorted(edits, key=lambda e: e.get("start", 0), reverse=True)
        applied = 0

        for ed in sorted_edits:
            start = ed.get("start", 0)
            end = ed.get("end", 0)
            content = ed.get("content", "")
            if start < 1:
                continue  # 忽略无效行号

            s = start - 1  # 转换为 0-indexed
            if end < start:  # 插入模式：在 start 行之前插入
                new_lines = content.split('\n')
                lines[s:s] = new_lines
                applied += 1
            else:
                e = end  # 因为 end 是包含的，切片结束索引为 end（不包含 end，但正好包含 end-1）
                if e < s:
                    continue
                if e > len(lines):
                    e = len(lines)
                new_lines = content.split('\n')
                lines[s:e] = new_lines
                applied += 1

        # 如果是 JSON 文件，验证格式
        if fp.endswith('.json'):
            import json as _json
            try:
                _json.loads('\n'.join(lines))
            except _json.JSONDecodeError as je:
                return {"file": fp, "error": f"JSON invalid at line {je.lineno}: {je.msg}"}

        try:
            _write(target, lines)
            return {"file": fp, "applied": applied, "lines": len(lines)}
        except Exception as e:
            return {"file": fp, "error": f"Write failed: {e}"}

    if not files:
        return {"success": True, "results": [], "note": "No files to edit — use FIX_SKIP instead"}

    with ThreadPoolExecutor(max_workers=len(files)) as pool:
        results = list(pool.map(edit_one, files))

    return {"success": True, "results": results}


# ── 行号模式（保留，适合一次性批量修改） ──────────────────────

async def replace_lines(
    file_path: str,
    start: int,
    end: int,
    content: str,
    workspace: str = "",
) -> Dict[str, Any]:
    """
    替换第 start~end 行（1-indexed）。适合首次修改，多次调用注意行号漂移。
    """
    base = Path(workspace).resolve() if workspace else Path.cwd().resolve()
    target = _resolve(Path(file_path), base)
    try: target.relative_to(base)
    except ValueError:
        return {"success": False, "error": "Access denied"}
    if not target.exists():
        return {"success": False, "error": f"File not found"}

    try: lines = _read_lines(target)
    except Exception as e: return {"success": False, "error": f"Read failed: {e}"}

    if start < 1 or start > len(lines) + 1:
        return {"success": False, "error": f"Invalid start: {start} (file has {len(lines)} lines)"}
    if end < start - 1:
        return {"success": False, "error": f"Invalid range: {start}-{end}"}
    end = min(end, len(lines))

    new_lines = content.split('\n')
    replaced = lines[:start-1] + new_lines + lines[end:]

    try:
        _write(target, replaced)
        return {"success": True, "path": str(target), "lines_replaced": end - start + 1}
    except Exception as e:
        return {"success": False, "error": f"Write failed: {e}"}
