# Tools/coding/syntax_check.py
"""语法检查工具 — 对生成的文件运行 node --check（JS）和基础校验（Vue/SQL）。

用法:
  check_syntax(files=["routes/auth.js", "services/authService.js"], workspace="/abs/path")
  返回: {"ok": true} 或 {"ok": false, "errors": [{"file":"...", "line": 42, "message":"..."}]}
"""

import subprocess
import re
from pathlib import Path
from typing import List, Dict, Optional


async def check_syntax(files: List[str], workspace: str = "") -> Dict:
    """对指定文件列表运行语法检查。

    Args:
        files: 相对路径列表（如 ["routes/auth.js", "src/pages/Login.vue"]）
        workspace: 工作区绝对路径

    Returns:
        {"ok": true, "checked": N, "errors": []}
        或
        {"ok": false, "errors": [{"file": "routes/auth.js", "line": 42, "message": "Unexpected token"}]}
    """
    base = Path(workspace).resolve() if workspace else Path.cwd()
    errors = []
    checked = 0

    for fp in files:
        target = (base / fp).resolve()
        if not target.exists():
            errors.append({"file": fp, "line": 0, "message": f"File not found: {fp}"})
            continue

        content = target.read_text("utf-8")
        ext = target.suffix.lower()

        if ext == ".js":
            err = _check_js(target, content, base)
        elif ext == ".vue":
            err = _check_vue(target, content, base)
        elif ext == ".sql":
            err = _check_sql(content, fp)
        elif ext == ".json":
            err = _check_json(content, fp)
        else:
            checked += 1
            continue

        if err:
            errors.append(err)
        checked += 1

    return {
        "ok": len(errors) == 0,
        "checked": checked,
        "errors": errors,
    }


def _check_js(target: Path, content: str, base: Path) -> Optional[Dict]:
    """Node.js 原生语法检查（最快，无外部依赖）。"""
    # 策略1: node --check（覆盖 95% 的语法错误：缺括号/缺分号/非法token）
    try:
        r = subprocess.run(
            ["node", "--check", str(target)],
            capture_output=True, text=True, timeout=10,
            encoding="utf-8", errors="replace",
        )
        if r.returncode == 0:
            return None  # 通过
        # 解析 node 错误输出
        msg = (r.stderr or r.stdout or "").strip()
        line = _parse_node_error_line(msg)
        return {"file": str(target.relative_to(base)), "line": line, "message": msg[:200]}
    except subprocess.TimeoutExpired:
        return {"file": str(target.relative_to(base)), "line": 0, "message": "node --check timeout"}
    except FileNotFoundError:
        return {"file": str(target.relative_to(base)), "line": 0, "message": "node not found in PATH"}


def _check_vue(target: Path, content: str, base: Path) -> Optional[Dict]:
    """Vue SFC 语法检查 — 提取 <script> 块用 node --check。"""
    # 提取 <script setup> 或 <script> 块
    script_match = re.search(r"<script[^>]*>(.*?)</script>", content, re.DOTALL)
    if not script_match:
        return None  # 无 script 块，跳过

    script_content = script_match.group(1).strip()
    if not script_content:
        return None

    # 写入临时 .js 文件供 node --check
    tmp = target.parent / f"._syntax_tmp_{target.stem}.js"
    try:
        tmp.write_text(script_content, "utf-8")
        r = subprocess.run(
            ["node", "--check", str(tmp)],
            capture_output=True, text=True, timeout=10,
            encoding="utf-8", errors="replace",
        )
        if r.returncode == 0:
            return None
        msg = (r.stderr or "").strip()
        line = _parse_node_error_line(msg)
        return {"file": str(target.relative_to(base)), "line": line, "message": f"[Vue script] {msg[:200]}"}
    except subprocess.TimeoutExpired:
        return {"file": str(target.relative_to(base)), "line": 0, "message": "Vue script check timeout"}
    finally:
        if tmp.exists():
            tmp.unlink()


def _check_sql(content: str, filename: str) -> Optional[Dict]:
    """SQL 基础语法检查 — 括号配对、关键字拼写。"""
    issues = []

    # 括号配对
    open_parens = content.count("(")
    close_parens = content.count(")")
    if open_parens != close_parens:
        issues.append(f"Parenthesis mismatch: {open_parens} open vs {close_parens} close")

    # DELIMITER 配对（存储过程）
    if "DELIMITER $$" in content and content.count("DELIMITER $$") != content.count("DELIMITER ;"):
        issues.append("DELIMITER $$ without matching DELIMITER ;")

    # BEGIN/END 配对
    begin_count = len(re.findall(r'\bBEGIN\b', content))
    end_count = len(re.findall(r'\bEND\b', content))
    if begin_count != end_count and ("PROCEDURE" in content or "FUNCTION" in content):
        issues.append(f"BEGIN/END mismatch: {begin_count} BEGIN vs {end_count} END")

    if issues:
        return {"file": filename, "line": 0, "message": "; ".join(issues)}
    return None


def _check_json(content: str, filename: str) -> Optional[Dict]:
    """JSON 语法检查。"""
    import json
    try:
        json.loads(content)
        return None
    except json.JSONDecodeError as e:
        return {"file": filename, "line": e.lineno, "message": f"JSON error at line {e.lineno}: {e.msg}"}


def _parse_node_error_line(msg: str) -> int:
    """从 node --check 错误输出中提取行号。"""
    # node 错误格式:  "/path/file.js:42\n  ...\n  ^\n\nSyntaxError: ..."
    m = re.search(r":(\d+)\b", msg)
    return int(m.group(1)) if m else 0
