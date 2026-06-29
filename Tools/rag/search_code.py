# Tools/rag/search_code.py
"""代码库检索工具 —— 搜索高分参考实现（S/A 级源码）。

用法:
    from Tools.rag.search_code import make_search_code
    search_code = make_search_code(task_id)
    tools = [create_files, search_code, ...]
"""


def make_search_code(task_id: str, agent_type: str = "code_generator"):
    """创建一个 search_code(query) 工具，按 agent_type 路由到对应代码库。

    agent_type:
      - test_writer / test_generator  → test_code_base (A 查测试代码)
      - source_fixer / code_generator → code_base (C 查源码)
    """

    _is_test = agent_type in ("test_writer", "test_generator")

    async def search_code(query: str) -> dict:
        """搜索高分参考实现。"""
        try:
            if _is_test:
                from Tools.rag.code_retrieval.code_retrieval import retrieve_test_code
                results = await retrieve_test_code(task_id, query, top_k=3, min_test_score=85)
            else:
                from Tools.rag.code_retrieval.code_retrieval import retrieve_code
                results = await retrieve_code(task_id, query, top_k=3, min_code_score=85)

            if not results:
                return {"ok": True, "results": [], "summary": "代码库暂无相关参考实现，请直接基于模板生成，不要重试搜索。"}

            simplified = []
            for r in results:
                simplified.append({
                    "function_name": r.get("function_name", r.get("describe_block", "")),
                    "code_snippet": r.get("code_snippet", "")[:2000],
                    "file_path": r.get("file_path", ""),
                    "score": r.get("code_score", r.get("test_score", 0)),
                    "similarity": round(r.get("similarity", 0), 3),
                })
            return {
                "ok": True,
                "results": simplified,
                "summary": f"找到 {len(simplified)} 个参考实现",
            }
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    return search_code
