# Tools/rag/retrieval/tools.py
"""
检索专用硬编码工具集
"""

from typing import List, Dict, Any, Optional

from Tools.rag.build.tools import ExperienceQuery, embed_text, open_table, table_vector_search


async def retrieve_single_angle(
    task_id: str,
    query: str,
    top_k: int = 3,
    severity_filter: Optional[List[str]] = None,
    category_filter: Optional[List[str]] = None,
    fallback: bool = True,
    exclude_ids: Optional[set] = None,
) -> List[Dict]:
    """
    单角度检索（图约束 + 向量语义）。

    当 fallback=True 且首次检索无结果时，自动降级移除合约过滤重试。
    exclude_ids: 已在前序角度中出现的记录 ID 集合，检索时多取一些再过滤，
                 保证每个角度贡献不同的记录。
    """
    query_obj = ExperienceQuery(
        task_id=task_id,
        query_text=query,
        severity_filter=severity_filter,
        category_filter=category_filter,
        top_k=top_k
    )
    filter_expr = query_obj.build_lance_filter()

    emb_result = await embed_text(query)
    if not emb_result["success"]:
        return []
    query_vector = emb_result["vector"]

    table = open_table()
    if table is None:
        return []

    # 如果有排除列表，多取一些以保证过滤后仍有 top_k 条
    fetch_limit = top_k
    if exclude_ids:
        fetch_limit = top_k + len(exclude_ids) + 2

    result = await table_vector_search(
        table=table,
        query_vector=query_vector,
        filter_expr=filter_expr,
        limit=fetch_limit,
        columns=["id", "do", "dont", "context", "severity", "category"]
    )

    rows = result.get("rows", []) if result["success"] else []

    # 过滤已在前序角度中出现的记录
    if exclude_ids:
        rows = [r for r in rows if r.get("id") not in exclude_ids]
        rows = rows[:top_k]

    # 降级：如果带合约过滤无结果，移除合约过滤重试（保留标签过滤）
    if fallback and len(rows) == 0 and filter_expr != "1=1":
        # 构建仅含标签过滤的表达式
        tag_conditions = []
        if query_obj.severity_filter:
            sev_list = ", ".join(f"'{s}'" for s in query_obj.severity_filter)
            tag_conditions.append(f"severity IN ({sev_list})")
        if query_obj.category_filter:
            cat_list = ", ".join(f"'{c}'" for c in query_obj.category_filter)
            tag_conditions.append(f"category IN ({cat_list})")
        tag_conditions.append(
            "(array_contains(trigger_tags, 'memory_test') "
            "OR array_contains(trigger_tags, 'memory_source') "
            "OR array_contains(trigger_tags, 'smoke'))"
        )
        fallback_filter = " AND ".join(tag_conditions) if tag_conditions else "1=1"

        fallback_result = await table_vector_search(
            table=table,
            query_vector=query_vector,
            filter_expr=fallback_filter,
            limit=top_k + (len(exclude_ids) + 2 if exclude_ids else 0),
            columns=["id", "do", "dont", "context", "severity", "category"]
        )
        if fallback_result["success"]:
            rows = fallback_result.get("rows", [])
            if exclude_ids:
                rows = [r for r in rows if r.get("id") not in exclude_ids]
                rows = rows[:top_k]

    formatted = []
    for r in rows:
        sim = 1.0 - float(r.get("_distance", 1.0))
        formatted.append({
            "id": r.get("id"),
            "do": r.get("do", ""),
            "dont": r.get("dont", ""),
            "context": r.get("context", ""),
            "severity": r.get("severity", "medium"),
            "category": r.get("category", "logic pitfall"),
            "similarity": round(sim, 4),
        })
    return formatted


def deduplicate_results(
    candidates: List[Dict],
    min_similarity: float = 0.0,
) -> List[Dict]:
    """
    ID 去重 + 噪音过滤，保留所有有效结果。

    - 同一 ID 出现在多个角度时，保留相似度最高的版本
    - 相似度低于 min_similarity 的视为噪音丢弃
    - 返回按相似度降序排列的全部有效记录（最少 0 条，最多等于候选唯一 ID 数）
    """
    # 1. ID 去重：同一 ID 保留最高相似度版本
    seen: Dict[str, Dict] = {}
    for r in candidates:
        exp_id = r.get("id")
        if exp_id:
            if exp_id not in seen or r.get("similarity", 0) > seen[exp_id].get("similarity", 0):
                seen[exp_id] = r

    # 2. 噪音过滤
    valid = [r for r in seen.values() if r.get("similarity", 0) >= min_similarity]

    # 3. 按相似度降序
    valid.sort(key=lambda x: x.get("similarity", 0), reverse=True)

    return valid


def format_retrieval_stats(final_results: List[Dict], angles: List[Dict]) -> Dict[str, Any]:
    angle_counts = {a["id"]: 0 for a in angles}
    for r in final_results:
        angle_id = r.get("angle_id")
        if angle_id in angle_counts:
            angle_counts[angle_id] += 1
    return {"total": len(final_results), "angles": angle_counts}