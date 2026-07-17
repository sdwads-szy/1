# Tools/rag/code_retrieval/code_store.py
"""
优秀代码库 —— 独立于经验知识库 (knowledge_base)。
存储 scheduler 评分 S/A 级的源码，供工程师 Agent 检索参考。

表: code_base (LanceDB)
检索: 两阶段 (BM25 + 向量 → Reranker)
"""

import os
import uuid
import re
import math
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict

import pyarrow as pa
import lancedb


# ── 常量 ──
PROJECT_ROOT = Path.cwd().resolve()
DB_PATH = os.getenv("RAG_DB_DIR", str(PROJECT_ROOT / "knowledge"))
TABLE_NAME = "code_base"
TEST_TABLE_NAME = "test_code_base"
EMBEDDING_DIM = 2560  # Qwen3-Embedding-4B


def _get_db():
    Path(DB_PATH).mkdir(parents=True, exist_ok=True)
    return lancedb.connect(DB_PATH)


# ═══════════════════════════════════════
# 源码表 (code_base) — C 的 search_code 查
# ═══════════════════════════════════════

def open_code_table() -> Optional[Any]:
    try:
        return _get_db().open_table(TABLE_NAME)
    except Exception:
        return None


def create_code_table() -> Optional[Any]:
    db = _get_db()
    try:
        return db.open_table(TABLE_NAME)
    except Exception:
        pass

    schema = pa.schema([
        pa.field("id", pa.string()),
        pa.field("task_id", pa.string()),
        pa.field("task_type", pa.string()),
        pa.field("function_name", pa.string()),
        pa.field("code_snippet", pa.string()),
        pa.field("file_path", pa.string()),
        pa.field("code_score", pa.float64()),
        pa.field("code_level", pa.string()),
        pa.field("contracts", pa.list_(pa.string())),
        pa.field("search_text", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), EMBEDDING_DIM)),
    ])
    db.create_table(TABLE_NAME, schema=schema, mode="create")
    return db.open_table(TABLE_NAME)


# ═══════════════════════════════════════
# 测试代码表 (test_code_base) — A 的 search_code 查
# ═══════════════════════════════════════

def open_test_code_table() -> Optional[Any]:
    try:
        return _get_db().open_table(TEST_TABLE_NAME)
    except Exception:
        return None


def create_test_code_table() -> Optional[Any]:
    db = _get_db()
    try:
        return db.open_table(TEST_TABLE_NAME)
    except Exception:
        pass

    schema = pa.schema([
        pa.field("id", pa.string()),
        pa.field("task_id", pa.string()),
        pa.field("test_layer", pa.string()),          # infra/db/backend/frontend/api/...
        pa.field("test_framework", pa.string()),       # jest/vitest
        pa.field("describe_block", pa.string()),        # describe 块名称
        pa.field("code_snippet", pa.string()),          # 完整 describe 块代码
        pa.field("file_path", pa.string()),
        pa.field("test_score", pa.float64()),           # 测试代码评分 0-100
        pa.field("test_level", pa.string()),            # S/A/B/C/D
        pa.field("search_text", pa.string()),           # BM25 检索文本
        pa.field("vector", pa.list_(pa.float32(), EMBEDDING_DIM)),
    ])
    db.create_table(TEST_TABLE_NAME, schema=schema, mode="create")
    return db.open_table(TEST_TABLE_NAME)


# ── 代码解析 (函数级分割) ──

def extract_functions(code: str, file_path: str = "") -> List[Dict]:
    """从源码文件提取各个导出函数，返回 [{function_name, code_snippet, search_text}]。

    支持三种导出模式:
      1. CJS exports.xxx:  exports.fnName = async (params) => { ... }
      2. CJS module.exports:  module.exports = { fn1, fn2 }  → 回溯找 async function fn1
      3. ESM export:  export async function fnName(params) { ... }
    """
    functions = []
    extracted_names = set()

    # ── 模式1: exports.fnName = ... ──
    for m in re.finditer(
        r'exports\.(\w+)\s*=\s*(?:async\s+)?(?:function\s*)?\(([^)]*)\)\s*(?:=>)?\s*\{',
        code
    ):
        fname = m.group(1)
        params = m.group(2)
        start = m.start()
        end = _find_matching_brace(code, start)
        if end > start:
            snippet = code[start:end]
            functions.append({
                "function_name": fname, "code_snippet": snippet,
                "file_path": file_path, "search_text": _build_search_text(fname, params, snippet),
            })
            extracted_names.add(fname)

    # ── 模式2: ESM export async function / export function ──
    for m in re.finditer(
        r'export\s+(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)\s*\{',
        code
    ):
        fname = m.group(1)
        params = m.group(2)
        start = m.start()
        end = _find_matching_brace(code, start)
        if end > start:
            snippet = code[start:end]
            functions.append({
                "function_name": fname, "code_snippet": snippet,
                "file_path": file_path, "search_text": _build_search_text(fname, params, snippet),
            })
            extracted_names.add(fname)

    # ── 模式3: module.exports = { fn1, fn2 } → 回溯找对应函数定义 ──
    mod_export = re.search(r'module\.exports\s*=\s*\{([^}]+)\}', code)
    if mod_export:
        exported_names = re.findall(r'\b(\w+)\b', mod_export.group(1))
        for fname in exported_names:
            if not fname or fname in extracted_names:
                continue
            # 回溯找: async function fnName(params) { ... } 或 function fnName(params) { ... }
            func_def = re.search(
                rf'(?:async\s+)?function\s+{re.escape(fname)}\s*\(([^)]*)\)\s*\{{',
                code
            )
            if func_def:
                params = func_def.group(1) if func_def.lastindex else ""
                start = func_def.start()
                end = _find_matching_brace(code, start)
                if end > start:
                    snippet = code[start:end]
                    functions.append({
                        "function_name": fname, "code_snippet": snippet,
                        "file_path": file_path,
                        "search_text": _build_search_text(fname, params, snippet),
                    })
                    extracted_names.add(fname)

    return functions


def _find_matching_brace(code: str, start: int) -> int:
    """从 start 位置的 { 开始，找到匹配的闭合 }。"""
    depth = 0
    for i, ch in enumerate(code[start:], start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i + 1
    return start


def _build_search_text(fname: str, params: str, snippet: str) -> str:
    """构造 BM25 检索文本：函数名 + 参数 + SQL 关键字 + 注释。"""
    parts = [fname, params]

    # SQL 关键字
    sql_patterns = re.findall(
        r'(SELECT|UPDATE|INSERT|DELETE|FROM|WHERE|SET|JOIN|FOR UPDATE|'
        r'beginTransaction|commit|rollback|CALL|sp_\w+)', snippet, re.IGNORECASE)
    parts.extend(p.lower() for p in sql_patterns)

    # 中文注释
    comments = re.findall(r'//.*|/\*.*?\*/', snippet, re.DOTALL)
    for c in comments[:3]:
        parts.append(c[:100])

    # 错误码
    errors = re.findall(r"code\s*[:=]\s*['\"](\w+)['\"]|throw.*?['\"](\w+)['\"]", snippet)
    for e in errors:
        parts.append(e[0] or e[1])

    return " ".join(parts)


# ── 存储 ──

def store_code(
    code_files: Dict[str, str],   # {path: content}
    task_id: str,
    task_type: str,
    contracts: List[str],
    code_score: float,
    code_level: str,
) -> int:
    """
    存储高分代码到 code_base。返回存储的函数数。
    """
    from Tools.rag.build.tools import embed_text_batch

    table = open_code_table() or create_code_table()
    if table is None:
        return 0

    all_funcs = []
    for file_path, content in code_files.items():
        funcs = extract_functions(content, file_path)
        for f in funcs:
            f.update({
                "task_id": task_id,
                "task_type": task_type,
                "contracts": contracts,
                "code_score": code_score,
                "code_level": code_level,
            })
        all_funcs.extend(funcs)

    if not all_funcs:
        return 0

    # 向量化
    texts = [f["search_text"] for f in all_funcs]
    vectors = embed_text_batch(texts)

    # 写入
    records = []
    for i, f in enumerate(all_funcs):
        records.append({
            "id": f"code_{task_id}_{f['function_name']}_{uuid.uuid4().hex[:8]}",
            "task_id": f["task_id"],
            "task_type": f["task_type"],
            "function_name": f["function_name"],
            "code_snippet": f["code_snippet"],
            "file_path": f["file_path"],
            "code_score": f["code_score"],
            "code_level": f["code_level"],
            "contracts": f["contracts"],
            "search_text": f["search_text"],
            "vector": vectors[i] if i < len(vectors) else [0.0] * EMBEDDING_DIM,
        })

    arrow_table = pa.Table.from_pylist(records)
    table.merge_insert(on="id").when_matched_update_all().when_not_matched_insert_all().execute(arrow_table)

    return len(records)


# ── BM25 索引 ──

class BM25:
    def __init__(self, k1=1.2, b=0.75):
        self.k1, self.b = k1, b
        self.docs, self.ids, self.lengths = [], [], []
        self.avgdl, self.idf = 0.0, {}
        self._built = False

    def build(self, docs: List[str], ids: List[str]):
        self.docs, self.ids = docs, ids
        self.lengths = [len(self._tok(d)) for d in docs]
        self.avgdl = sum(self.lengths) / max(len(self.lengths), 1)
        N = len(docs)
        df = defaultdict(int)
        for d in docs:
            for t in set(self._tok(d)):
                df[t] += 1
        self.idf = {t: math.log((N - df[t] + 0.5) / (df[t] + 0.5) + 1) for t in df}
        self._built = True

    def search(self, q: str, k=20):
        if not self._built: return []
        qt = self._tok(q)
        scores = []
        for i, doc in enumerate(self.docs):
            tf = defaultdict(int)
            for t in self._tok(doc): tf[t] += 1
            s = sum(self.idf.get(t, 0) * (tf.get(t, 0) * (self.k1 + 1)) / (
                tf.get(t, 0) + self.k1 * (1 - self.b + self.b * self.lengths[i] / self.avgdl)) for t in set(qt) if t in self.idf)
            if s > 0: scores.append((self.ids[i], s))
        scores.sort(key=lambda x: -x[1])
        return scores[:k]

    def _tok(self, t):
        tokens = re.findall(r'[a-zA-Z_]\w+', t.lower())
        ch = re.sub(r'[^一-鿿]', '', t)
        tokens.extend(ch[i:i+2] for i in range(len(ch)-1))
        tokens.extend(re.findall(r'\b(SELECT|UPDATE|INSERT|DELETE|FROM|WHERE|SET|JOIN|FOR UPDATE|beginTransaction|commit|rollback)\b', t, re.I))
        return tokens


# ═══════════════════════════════════════
# 测试代码提取 (describe 块级)
# ═══════════════════════════════════════

def extract_describe_blocks(code: str, file_path: str = "") -> List[Dict]:
    """从测试文件提取各个 describe 块，返回 [{describe_block, code_snippet, search_text}]。"""
    blocks = []
    # describe('...', () => { ... });
    for m in re.finditer(r"describe\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*(?:async\s*)?\(\)\s*=>\s*\{", code):
        desc_name = m.group(1)
        start = m.start()
        depth = 0
        end = start
        for i, ch in enumerate(code[start:], start):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    # include trailing ); if present
                    if end < len(code) and code[end:end+2] == ');':
                        end += 2
                    elif end < len(code) and code[end] == ')':
                        end += 1
                        if end < len(code) and code[end] == ';':
                            end += 1
                    break
        if end > start:
            snippet = code[start:end]
            search_text = _build_test_search_text(desc_name, snippet, code[:start])
            blocks.append({
                "describe_block": desc_name,
                "code_snippet": snippet,
                "file_path": file_path,
                "search_text": search_text,
            })
    return blocks


def _build_test_search_text(desc_name: str, snippet: str, prefix: str) -> str:
    """构造测试代码 BM25 检索文本。"""
    parts = [desc_name]

    # mock 声明
    mocks = re.findall(r'(?:jest|vi)\.mock\s*\(\s*[\'\"]([^\'\"]+)[\'\"]', prefix + snippet)
    parts.extend(f"mock:{m}" for m in mocks)

    # 断言关键词
    if 'toHaveBeenNthCalledWith' in snippet:
        parts.append("ordered")
    if 'toThrow' in snippet:
        parts.append("error_path")
    if 'toMatchObject' in snippet:
        parts.append("structure_check")
    if 'mockResolvedValue' in snippet:
        parts.append("mock_chain")

    # 框架
    if 'vi.mock' in prefix or 'vi.mock' in snippet:
        parts.append("vitest")
    if 'jest.mock' in prefix or 'jest.mock' in snippet:
        parts.append("jest")

    # 层信息从 describe 名推断
    parts.append(desc_name)

    return " ".join(parts)


def store_test_code(
    code_files: Dict[str, str],
    task_id: str,
    test_layer: str,
    test_framework: str,
    test_score: float,
    test_level: str,
) -> int:
    """存储高分测试代码到 test_code_base。返回存储的 describe 块数。"""
    from Tools.rag.build.tools import embed_text_batch

    table = open_test_code_table() or create_test_code_table()
    if table is None:
        return 0

    all_blocks = []
    for file_path, content in code_files.items():
        blocks = extract_describe_blocks(content, file_path)
        for b in blocks:
            b.update({
                "task_id": task_id,
                "test_layer": test_layer,
                "test_framework": test_framework,
                "test_score": test_score,
                "test_level": test_level,
            })
        all_blocks.extend(blocks)

    if not all_blocks:
        return 0

    texts = [b["search_text"] for b in all_blocks]
    vectors = embed_text_batch(texts)

    records = []
    for i, b in enumerate(all_blocks):
        records.append({
            "id": f"test_{task_id}_{b['describe_block'][:40]}_{uuid.uuid4().hex[:8]}",
            "task_id": b["task_id"],
            "test_layer": b["test_layer"],
            "test_framework": b["test_framework"],
            "describe_block": b["describe_block"],
            "code_snippet": b["code_snippet"],
            "file_path": b["file_path"],
            "test_score": b["test_score"],
            "test_level": b["test_level"],
            "search_text": b["search_text"],
            "vector": vectors[i] if i < len(vectors) else [0.0] * EMBEDDING_DIM,
        })

    arrow_table = pa.Table.from_pylist(records)
    table.merge_insert(on="id").when_matched_update_all().when_not_matched_insert_all().execute(arrow_table)

    return len(records)


def count_code() -> int:
    t = open_code_table()
    return t.count_rows() if t else 0


def count_test_code() -> int:
    t = open_test_code_table()
    return t.count_rows() if t else 0
