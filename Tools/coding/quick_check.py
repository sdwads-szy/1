# Tools/coding/quick_check.py
"""
轻量语法校验 — 纯 Python，零外部依赖。跟在 create_files/edit_files 后自动执行。
只检查容易当场发现的低级问题（括号配对、引号配对、JSON 合法性等）。
"""

import json as _json
import re as _re
from pathlib import Path
from typing import List, Dict


async def quick_check(files: List[str], workspace: str = "") -> Dict:
    """对指定文件运行快速静态检查，返回问题列表。

    Args:
        files: 相对路径列表
        workspace: 工作区绝对路径

    Returns:
        {"ok": bool, "checked": int, "issues": [{"file": str, "line": int, "msg": str}]}
    """
    base = Path(workspace).resolve() if workspace else Path.cwd()
    issues = []
    checked = 0

    for fp in files:
        target = (base / fp).resolve()
        if not target.exists() or target.stat().st_size == 0:
            continue
        try:
            content = target.read_text("utf-8", errors="replace")
        except Exception:
            continue

        ext = target.suffix.lower()

        if ext == ".json":
            file_issues = _check_json(content, fp)
        elif ext == ".sql":
            file_issues = _check_sql(content, fp)
        elif ext in (".js", ".vue", ".jsx", ".ts", ".mjs", ".cjs"):
            file_issues = _check_js_like(content, fp, target, base)
        else:
            file_issues = []

        if file_issues:
            issues.extend(file_issues)
        checked += 1

    return {
        "ok": len(issues) == 0,
        "checked": checked,
        "issues": issues,
    }


# ═══════════════════════════════════════════════
# 各类型检查器
# ═══════════════════════════════════════════════

def _check_json(content: str, fp: str) -> list:
    """JSON 合法性验证。"""
    try:
        _json.loads(content)
    except _json.JSONDecodeError as e:
        return [{"file": fp, "line": e.lineno or 0, "msg": f"JSON 解析失败: {e.msg}"}]
    return []


def _check_js_like(content: str, fp: str, target: Path, base: Path) -> list:
    """JS/TS/Vue SFC — 括号 + 引号 + require/import 路径 + CJS 禁止。"""
    issues = []

    # Vue 文件只检查 <script> 块
    orig_content = content
    if fp.endswith(".vue"):
        m = _re.search(r"<script[^>]*>(.*?)</script>", content, _re.DOTALL)
        content = m.group(1) if m else ""

    lines = content.split("\n")

    # ── 1. 括号栈检查 ({[ ──
    _pairs = {"{": "}", "(": ")", "[": "]"}
    _pairs_inv = {v: k for k, v in _pairs.items()}
    _stack = []
    for i, line in enumerate(lines, 1):
        for ch in line:
            if ch in _pairs:
                _stack.append((_pairs[ch], i))
            elif ch in ("}", ")", "]"):
                if not _stack:
                    issues.append({"file": fp, "line": i,
                                   "msg": f"多余的 '{ch}' — 前面没有匹配的左括号"})
                else:
                    expected, _ = _stack.pop()
                    if ch != expected:
                        issues.append({"file": fp, "line": i,
                                       "msg": f"括号不匹配: 期望 '{expected}' 但遇到 '{ch}'"})
    for expected, line_no in _stack:
        issues.append({"file": fp, "line": line_no,
                       "msg": f"未闭合的 '{_pairs_inv[expected]}' — 缺少对应的 '{expected}'"})

    # ── 2. 引号/反引号按行检查 ──
    for i, line in enumerate(lines, 1):
        for ch, name in [('"', '双引号'), ("'", '单引号'), ('`', '反引号')]:
            count = line.count(ch)
            escaped = line.count("\\" + ch)
            if (count - escaped) % 2 != 0:
                issues.append({"file": fp, "line": i, "msg": f"{name} 可能未闭合"})
                break

    # ── 3. CJS require 路径解析 ──
    _check_require_paths(content, fp, target, issues)

    # ── 4. ESM import 路径解析 ──
    _check_import_paths(content, fp, target, base, issues)

    # ── 5. 🆕 CJS 禁止（src/ 下前端文件必须用 ESM）──
    if "src/" in fp.replace("\\", "/") and fp.endswith(".js"):
        if "module.exports" in orig_content or "require(" in orig_content:
            line_no = 0
            for i, line in enumerate(orig_content.split("\n"), 1):
                if "module.exports" in line or "require(" in line:
                    line_no = i
                    break
            issues.append({"file": fp, "line": line_no,
                           "msg": "前端 src/ 下禁止 CJS (require/module.exports)，必须使用 ESM (import/export)"})

    return issues


def _check_require_paths(content: str, fp: str, target: Path, issues: list):
    """检查 require('./...') 路径是否可解析到实际文件。"""
    file_dir = target.parent
    for m in _re.finditer(r"""require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)""", content):
        req_path = m.group(1)
        if not req_path.startswith('.'):
            continue  # npm 包，跳过
        resolved = (file_dir / req_path).resolve()
        if not _path_exists(resolved):
            # 计算行号
            line_no = content[:m.start()].count('\n') + 1
            issues.append({"file": fp, "line": line_no,
                           "msg": f"require('{req_path}') → 文件不存在"})


def _check_import_paths(content: str, fp: str, target: Path, base: Path, issues: list):
    """检查 import ... from './...' 或 '@/...' 路径是否可解析。"""
    file_dir = target.parent
    for m in _re.finditer(
        r"""import\s+(?:[\w*\s{},]*\s+from\s+)?['\"]([^'\"]+)['\"]""",
        content
    ):
        imp_path = m.group(1)
        if not imp_path.startswith('.') and not imp_path.startswith('@/'):
            continue  # npm 包或绝对路径，跳过
        if imp_path.startswith('@/'):
            resolved = (base / "src" / imp_path[2:]).resolve()
        else:
            resolved = (file_dir / imp_path).resolve()
        if not _path_exists(resolved):
            line_no = content[:m.start()].count('\n') + 1
            issues.append({"file": fp, "line": line_no,
                           "msg": f"import '{imp_path}' → 文件不存在"})


def _path_exists(resolved: Path) -> bool:
    """检查模块路径是否可解析（尝试 .js/.vue/.ts/.jsx/.tsx/index.js 等）。"""
    if resolved.exists():
        return True
    for ext in [".js", ".vue", ".ts", ".jsx", ".tsx", ".mjs", ".cjs",
                "/index.js", "/index.vue", "/index.ts"]:
        if Path(str(resolved) + ext).exists():
            return True
    return False


def _check_sql(content: str, fp: str) -> list:
    """SQL — 括号配对 + BEGIN/END 配对 + DELIMITER 配对 + CREATE TABLE 分号 + 关键字拼写。"""
    issues = []

    open_p = content.count("(")
    close_p = content.count(")")
    if open_p != close_p:
        issues.append({"file": fp, "line": 0,
                       "msg": f"括号不配对: {open_p} 开 vs {close_p} 闭"})

    begin_c = len(_re.findall(r'\bBEGIN\b', content))
    end_c = len(_re.findall(r'\bEND\b', content))
    if begin_c != end_c and ("PROCEDURE" in content.upper() or "FUNCTION" in content.upper()):
        issues.append({"file": fp, "line": 0,
                       "msg": f"BEGIN/END 不配对: {begin_c} BEGIN vs {end_c} END"})

    if "DELIMITER $$" in content and content.count("DELIMITER $$") != content.count("DELIMITER ;"):
        issues.append({"file": fp, "line": 0,
                       "msg": "DELIMITER $$ 与 DELIMITER ; 不配对"})

    # 🆕 CREATE TABLE 语句末尾分号检查
    for m in _re.finditer(
        r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?\w+`?\s*\(.*?\)\s*ENGINE[^;]*',
        content, _re.IGNORECASE | _re.DOTALL
    ):
        if not m.group(0).rstrip().endswith(';'):
            line_no = content[:m.start()].count('\n') + 1
            issues.append({"file": fp, "line": line_no,
                           "msg": "CREATE TABLE 语句末尾缺分号"})

    # 🆕 常见关键字拼写检查（LLM 容易写错，纯 regex）
    _typos = {
        r'\bAUTO_INCREAMENT\b': 'AUTO_INCREMENT',
        r'\bPRIAMRY\b': 'PRIMARY',
        r'\bFORIEGN\b': 'FOREIGN',
        r'\bREFERECNES\b': 'REFERENCES',
        r'\bVACHAR\b': 'VARCHAR',
    }
    for pat, correct in _typos.items():
        for m in _re.finditer(pat, content, _re.IGNORECASE):
            line_no = content[:m.start()].count('\n') + 1
            issues.append({"file": fp, "line": line_no,
                           "msg": f"疑似拼写错误 '{m.group(0)}' → 应为 '{correct}'"})

    return issues
