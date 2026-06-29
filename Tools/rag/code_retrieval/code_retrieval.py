# Tools/rag/code_retrieval/code_retrieval.py
"""
两阶段代码检索: BM25 + 向量混合召回 → Reranker 精排

用法:
    from Tools.rag.code_retrieval.code_retrieval import retrieve_code
    results = await retrieve_code("b_order", "cancelOrder 事务回滚")
"""

import os
import json
import hashlib
import numpy as np
from typing import List, Dict, Any, Optional

from Tools.rag.build.tools import embed_text
from Tools.rag.code_retrieval.code_store import open_code_table, open_test_code_table, BM25

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_CODE_CACHE_TTL = 86400  # 24 小时


async def _get_code_redis():
    try:
        import redis.asyncio as aioredis
        r = await aioredis.from_url(_REDIS_URL, decode_responses=True)
        await r.ping()
        return r
    except Exception:
        return None


async def retrieve_code(
    task_id: str,
    query: str,
    top_k: int = 3,
    min_code_score: float = 0,
    use_reranker: bool = True,
) -> List[Dict]:
    """
    两阶段代码检索:
      Stage 1: BM25 + 向量混合 → top-20
      Stage 2: Reranker → top-K

    返回: [{id, task_id, function_name, code_snippet, file_path, code_score, similarity, ...}]
    """
    # ── Redis 缓存检查 ──
    norm = query.strip().lower()[:200]
    cache_key = f"code_cache:{hashlib.md5(f'{norm}|{top_k}|{min_code_score}'.encode()).hexdigest()[:16]}"
    redis = await _get_code_redis()
    if redis:
        try:
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    table = open_code_table()
    if table is None:
        return []

    # 加载全部记录（code_base 通常 ≤500 条，全量扫描可行）
    try:
        cols = ["id", "task_id", "task_type", "function_name", "code_snippet",
                "file_path", "code_score", "code_level", "contracts", "search_text", "vector"]
        all_rows = table.to_lance().to_table(columns=cols).to_pylist()
    except Exception:
        return []

    if not all_rows:
        return []

    # 按评分过滤
    if min_code_score > 0:
        all_rows = [r for r in all_rows if r.get("code_score", 0) >= min_code_score]

    if not all_rows:
        return []

    # ══ Stage 1: BM25 + 向量混合 ══
    bm25 = BM25()
    bm25.build([r.get("search_text", "") for r in all_rows], [r["id"] for r in all_rows])
    bm25_hits = bm25.search(query, k=20)
    bm25_map = {rid: s for rid, s in bm25_hits}
    max_bm = max(bm25_map.values()) if bm25_map else 1.0

    q_emb = await embed_text(query)
    if not q_emb["success"]:
        return _format_results(all_rows[:top_k], {r["id"]: 0.5 for r in all_rows[:top_k]})
    q_vec = np.array(q_emb["vector"])
    q_norm = np.linalg.norm(q_vec)

    vec_scores = {}
    for r in all_rows:
        v = np.array(r.get("vector", [0]*2560))
        v_norm = np.linalg.norm(v)
        if v_norm > 0 and q_norm > 0:
            vec_scores[r["id"]] = float(np.dot(q_vec, v) / (q_norm * v_norm))
    max_vec = max(vec_scores.values()) if vec_scores else 1.0

    # 混合: BM25 30% + 向量 70%
    combined = []
    for r in all_rows:
        bm = bm25_map.get(r["id"], 0) / max_bm if max_bm > 0 else 0
        vs = vec_scores.get(r["id"], 0) / max_vec if max_vec > 0 else 0
        combined.append((0.3 * bm + 0.7 * vs, r))
    combined.sort(key=lambda x: -x[0])
    candidates = combined[:20]

    # ══ Stage 2: Reranker ══
    if use_reranker and len(candidates) > top_k:
        reranker = _get_reranker()
        if reranker:
            pairs = [(query, f"{c[1].get('search_text', '')} {c[1].get('code_snippet', '')[:800]}") for c in candidates]
            try:
                scores = reranker.predict(pairs, show_progress_bar=False)
                for i, c in enumerate(candidates):
                    c = (float(scores[i]), c[1])  # reranker 直接给相关性分
                    candidates[i] = c
                candidates.sort(key=lambda x: -x[0])
            except Exception:
                pass  # reranker 失败 → 用混合分

    final = _format_results(
        [c[1] for c in candidates[:top_k]],
        {c[1]["id"]: c[0] for c in candidates[:top_k] if not isinstance(c[0], tuple)}
    )

    # ── 写入 Redis 缓存 ──
    if redis and final:
        try:
            await redis.set(cache_key, json.dumps(final, ensure_ascii=False), ex=_CODE_CACHE_TTL)
        except Exception:
            pass

    return final


def _get_reranker():
    global _reranker_model
    if "_reranker_model" not in globals():
        _reranker_model = None
    if _reranker_model is None:
        try:
            from sentence_transformers import CrossEncoder
            model_name = os.getenv("RAG_RERANKER_MODEL", "Qwen/Qwen3-Reranker-4B")
            _reranker_model = CrossEncoder(model_name, trust_remote_code=True, device="cuda")
        except Exception:
            _reranker_model = None
    return _reranker_model


def _format_results(rows: List[Dict], scores: Dict[str, float]) -> List[Dict]:
    return [{
        "id": r["id"],
        "task_id": r.get("task_id", ""),
        "task_type": r.get("task_type", ""),
        "function_name": r.get("function_name", ""),
        "code_snippet": r.get("code_snippet", ""),
        "file_path": r.get("file_path", ""),
        "code_score": r.get("code_score", 0),
        "code_level": r.get("code_level", ""),
        "similarity": round(scores.get(r["id"], 0.5), 4),
    } for r in rows]


# ═══════════════════════════════════════
# 测试代码检索 (test_code_base) — A 使用
# ═══════════════════════════════════════

async def retrieve_test_code(
    task_id: str,
    query: str,
    top_k: int = 3,
    min_test_score: float = 0,
    test_layer: str = "",
) -> List[Dict]:
    """检索高分测试代码参考。"""
    table = open_test_code_table()
    if table is None:
        return []

    try:
        cols = ["id", "task_id", "test_layer", "test_framework", "describe_block",
                "code_snippet", "file_path", "test_score", "test_level", "search_text", "vector"]
        all_rows = table.to_lance().to_table(columns=cols).to_pylist()
    except Exception:
        return []

    if not all_rows:
        return []

    # 按评分和层过滤
    if min_test_score > 0:
        all_rows = [r for r in all_rows if r.get("test_score", 0) >= min_test_score]
    if test_layer:
        all_rows = [r for r in all_rows if r.get("test_layer") == test_layer]

    if not all_rows:
        return []

    # BM25 + 向量混合
    bm25 = BM25()
    bm25.build([r.get("search_text", "") for r in all_rows], [r["id"] for r in all_rows])
    bm25_hits = bm25.search(query, k=20)
    bm25_map = {rid: s for rid, s in bm25_hits}
    max_bm = max(bm25_map.values()) if bm25_map else 1.0

    q_emb = await embed_text(query)
    if not q_emb["success"]:
        return _format_test_results(all_rows[:top_k], {r["id"]: 0.5 for r in all_rows[:top_k]})
    q_vec = np.array(q_emb["vector"])
    q_norm = np.linalg.norm(q_vec)

    vec_scores = {}
    for r in all_rows:
        v = np.array(r.get("vector", [0]*2560))
        v_norm = np.linalg.norm(v)
        if v_norm > 0 and q_norm > 0:
            vec_scores[r["id"]] = float(np.dot(q_vec, v) / (q_norm * v_norm))
    max_vec = max(vec_scores.values()) if vec_scores else 1.0

    combined = []
    for r in all_rows:
        bm = bm25_map.get(r["id"], 0) / max_bm if max_bm > 0 else 0
        vs = vec_scores.get(r["id"], 0) / max_vec if max_vec > 0 else 0
        combined.append((0.3 * bm + 0.7 * vs, r))
    combined.sort(key=lambda x: -x[0])

    return _format_test_results(
        [c[1] for c in combined[:top_k]],
        {c[1]["id"]: c[0] for c in combined[:top_k]}
    )


def _format_test_results(rows: List[Dict], scores: Dict[str, float]) -> List[Dict]:
    return [{
        "id": r["id"],
        "task_id": r.get("task_id", ""),
        "test_layer": r.get("test_layer", ""),
        "test_framework": r.get("test_framework", ""),
        "describe_block": r.get("describe_block", ""),
        "code_snippet": r.get("code_snippet", ""),
        "file_path": r.get("file_path", ""),
        "test_score": r.get("test_score", 0),
        "test_level": r.get("test_level", ""),
        "similarity": round(scores.get(r["id"], 0.5), 4),
    } for r in rows]
