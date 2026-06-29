# Tools/coding/get_functions_info.py
import ast, re
from pathlib import Path
from typing import List, Dict, Any

def _is_within_workspace(path: Path, workspace_root: Path) -> bool:
    try: path.relative_to(workspace_root); return True
    except ValueError: return False

def _line_at_pos(source: str, pos: int) -> int:
    """字符位置转行号(1-based)"""
    return source[:pos].count('\n') + 1

def _find_js_block_end(source: str, start_pos: int) -> int:
    """找到从 start_pos 开始的 { } 块结束位置（字符索引）。
    处理字符串、模板字符串（不把 ${ 里的 { 当括号）。"""
    depth = 0; in_str = None; esc = False; started = False
    for i in range(start_pos, len(source)):
        ch = source[i]
        if esc: esc = False; continue
        if ch == '\\': esc = True; continue
        if in_str:
            if ch == in_str: in_str = None  # 字符串结束
            continue
        if ch in ('"', "'", '`'):
            in_str = ch
            continue
        if ch == '{': depth += 1; started = True
        elif ch == '}':
            depth -= 1
            if started and depth == 0:
                return i
    return len(source) - 1

def _extract_js_functions(source: str) -> List[Dict[str, Any]]:
    """提取 JS 函数信息，含行号"""
    functions = []
    # 匹配模式及其分组: (name_group, params_group, pattern)
    patterns = [
        (1, 2, r'(?:export\s+)?function\s+([a-zA-Z_$][\w$]*)\s*\(([^)]*)\)'),
        (1, 2, r'(?:export\s+)?async\s+function\s+([a-zA-Z_$][\w$]*)\s*\(([^)]*)\)'),
        (1, 2, r'(?:exports\.|module\.exports\.)?([a-zA-Z_$][\w$]*)\s*=\s*(?:async\s+)?function\s*\(([^)]*)\)'),
        (1, 2, r'(?:exports\.|module\.exports\.)?([a-zA-Z_$][\w$]*)\s*=\s*\(([^)]*)\)\s*=>'),
        (1, 2, r'(?:exports\.|module\.exports\.)?([a-zA-Z_$][\w$]*)\s*=\s*async\s*\(([^)]*)\)\s*=>'),
    ]
    seen = set()
    for name_g, params_g, pattern in patterns:
        for m in re.finditer(pattern, source, re.MULTILINE):
            name = m.group(name_g)
            if name in seen: continue
            # 过滤关键字
            if name in ('if', 'for', 'while', 'switch', 'catch', 'return', 'throw', 'typeof', 'instanceof', 'new', 'delete', 'void', 'this', 'super', 'class', 'import', 'export', 'default', 'require', 'constructor'): continue
            seen.add(name)
            params_str = m.group(params_g)
            params = [p.strip().split('=')[0].strip().split(':')[0].strip() for p in params_str.split(',') if p.strip()]
            pos = m.start()
            line_start = _line_at_pos(source, pos)
            # 找函数体
            body_start = source.find('{', m.end())
            if body_start > 0:
                body_end = _find_js_block_end(source, body_start)
                line_end = _line_at_pos(source, body_end)
            else:
                # 箭头函数可能没有 {}
                line_end = _line_at_pos(source, m.end() + 200) if m.end() + 200 < len(source) else _line_at_pos(source, len(source)-1)
            functions.append({
                "name": name,
                "params": params,
                "line_start": line_start,
                "line_end": line_end,
            })
    return sorted(functions, key=lambda x: x["line_start"])


def _extract_vue_functions(source: str) -> List[Dict[str, Any]]:
    functions = []
    methods_match = re.search(r'methods\s*:\s*\{([\s\S]+?)\n\s*\}', source)
    if methods_match:
        funcs = _extract_js_functions(methods_match.group(1))
        functions.extend(funcs)
    return functions


async def get_functions_info(file_path: str, workspace: str = "") -> List[Dict[str, Any]]:
    """返回所有函数的信息: name, params, line_start, line_end"""
    if workspace:
        base = Path(workspace).resolve()
        if not base.exists(): return [{"error": f"Workspace not found: {workspace}"}]
    else:
        base = Path.cwd().resolve()

    target = Path(file_path)
    target = (base / file_path).resolve() if not target.is_absolute() else target.resolve()
    if not _is_within_workspace(target, base):
        return [{"error": f"Access denied: outside workspace"}]
    if not target.exists():
        return [{"error": f"File not found: {file_path}"}]

    try: source = target.read_text(encoding='utf-8')
    except Exception as e: return [{"error": str(e)}]

    ext = target.suffix.lower()
    if ext == '.py':
        try: tree = ast.parse(source)
        except SyntaxError as e: return [{"error": str(e)}]
        funcs = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                funcs.append({"name": node.name, "params": [a.arg for a in node.args.args],
                              "line_start": node.lineno, "line_end": node.end_lineno or node.lineno,
                              "docstring": (ast.get_docstring(node) or "")[:200]})
        return funcs
    elif ext in ('.js', '.ts', '.mjs', '.cjs'):
        return _extract_js_functions(source)
    elif ext == '.vue':
        m = re.search(r'<script[^>]*>([\s\S]*?)</script>', source)
        return _extract_vue_functions(m.group(1)) if m else []
    return [{"error": f"Unsupported type: {ext}"}]
