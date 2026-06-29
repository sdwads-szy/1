# Tools/rag/search_rag.py
"""RAG 检索工具 —— 供 Agent 自主调用，查询历史经验知识库。

用法:
    from Tools.rag.search_rag import make_search_rag
    search_rag = make_search_rag(task_id, agent_type)
    tools = [create_files, search_rag, ...]
"""

from typing import Optional


def make_search_rag(task_id: str, agent_type: str = "code_generator"):
    """创建一个 search_rag(query) 工具函数，Agent 可在需要时自主调用。

    Args:
        task_id: 当前任务 ID (用于图约束过滤)
        agent_type: code_generator | test_generator | test_repair | architect | requirement

    Returns:
        async function search_rag(query) -> dict
    """
    async def search_rag(query: str) -> dict:
        """搜索历史经验知识库。当你不确定某个业务场景的最佳实践、常见陷阱、或并发处理方式时调用。

        Args:
            query: 自然语言查询，如 "创建订单时如何防止库存超卖？"

        Returns:
            {ok, summary, content, results_count}
            - 无结果时 summary="知识库暂无相关数据，请直接基于模板生成，不要重试搜索。"，此时应直接进入下一轮。
        """
        try:
            from brainAgent.retrieval_scheduler import retrieval_scheduler
            result = await retrieval_scheduler(task_id, query, agent_type)
            count = len(result.get("raw_results", [])) if isinstance(result, dict) else 0
            summary = result.get("summary", "") if isinstance(result, dict) else ""
            # 交付内容：优先取 agent_type 对应的格式化内容，否则用 summary
            delivery = result.get("delivery", {}) if isinstance(result, dict) else {}
            if isinstance(delivery, dict) and agent_type in delivery:
                entry = delivery[agent_type]
                if isinstance(entry, dict) and "content" in entry:
                    content = entry["content"]
                elif isinstance(entry, str):
                    content = entry
                else:
                    content = summary
            elif isinstance(delivery, str):
                content = delivery
            else:
                content = summary
            return {
                "ok": True,
                "summary": summary[:500] if summary else "知识库暂无相关数据，请直接基于模板生成，不要重试搜索。",
                "content": (content or summary or "")[:3000],
                "results_count": count,
            }
        except Exception as e:
            return {
                "ok": True,
                "summary": "知识库暂无相关数据，请直接基于模板生成，不要重试搜索。",
                "content": "",
                "results_count": 0,
                "_error": str(e)[:200],
            }

    return search_rag
