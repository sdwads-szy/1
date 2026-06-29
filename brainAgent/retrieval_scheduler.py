# brainAgent/retrieval_scheduler.py
"""
统一检索调度器（Retrieval Scheduler）

供其他 Agent 调用的检索入口。使用方式：

    from brainAgent.retrieval_scheduler import init_retrieval, retrieval_scheduler

    init_retrieval()                              # 一次性初始化（加载锚点缓存）
    result = await retrieval_scheduler(           # 执行检索
        task_id="b_order",
        query="创建订单时如何扣减库存才能防止超卖？",
        agent_type="code_generator",
    )
    # result["raw_results"]  → 去重后的记录列表
    # result["delivery"]     → 按 agent_type 格式化的交付内容
    # result["summary"]      → 文本摘要
"""

import asyncio
import json
import hashlib
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

from localAgent.retrieval_agent import run_retrieval_agent
from Tools.rag.retrieval.tools import (
    retrieve_single_angle,
    deduplicate_results,
    format_retrieval_stats,
)
from Tools.rag.build.tools import load_anchor_cache_from_tasks, _anchor_cache, open_table

_initialized = False
_redis_client: Optional[Any] = None
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = 86400  # 24 小时


async def _get_redis():
    global _redis_client
    if _redis_client is None:
        try:
            import redis.asyncio as aioredis
            _redis_client = await aioredis.from_url(REDIS_URL, decode_responses=True)
            await _redis_client.ping()
        except Exception:
            _redis_client = False  # 标记不可用
    return _redis_client if _redis_client is not False else None


def _cache_key(query: str, agent_type: str, top_k: int, min_similarity: float) -> str:
    """生成缓存 key：query 规范化后 hash，同义查询命中同一缓存。"""
    norm = query.strip().lower()
    # 去掉过长的 query（截断到 200 字符后 hash）
    if len(norm) > 200:
        norm = norm[:200]
    fingerprint = hashlib.md5(
        f"{norm}|{agent_type}|{top_k}|{min_similarity:.2f}".encode()
    ).hexdigest()[:16]
    return f"rag_cache:{fingerprint}"


def init_retrieval(task_dir: Optional[Path] = None) -> None:
    """一次性初始化：加载图锚点缓存。幂等，可多次调用。"""
    global _initialized
    if _initialized:
        return
    if task_dir is None:
        task_dir = PROJECT_ROOT / "work" / "project" / "task"
    load_anchor_cache_from_tasks(task_dir)
    _initialized = True


def _log(msg: str, verbose: bool) -> None:
    if verbose:
        print(msg)


async def retrieval_scheduler(
    task_id: str,
    query: str,
    agent_type: str = "code_generator",
    top_k_per_angle: int = 3,
    min_similarity: float = 0.55,
    severity_filter: Optional[List[str]] = None,
    category_filter: Optional[List[str]] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    init_retrieval()  # 自动初始化，外部忘记调用也不影响

    # ── Redis 缓存检查 ──
    cache_key = _cache_key(query, agent_type, top_k_per_angle, min_similarity)
    redis = await _get_redis()
    if redis:
        try:
            cached = await redis.get(cache_key)
            if cached:
                _log(f"\n[Cache HIT] {cache_key}", verbose)
                return json.loads(cached)
        except Exception:
            pass

    _log("\n" + "🔍" * 30, verbose)
    _log(f"  统一检索调度器", verbose)
    _log(f"  任务: {task_id} | 类型: {agent_type}", verbose)
    _log(f"  查询: {query}", verbose)
    _log("🔍" * 30, verbose)

    result = {
        "success": False,
        "query": query,
        "task_id": task_id,
        "agent_type": agent_type,
        "summary": "",
        "delivery": None,
        "raw_results": [],
        "suggestions": [],
        "error": None
    }

    # ============================================================
    # 步骤 1：角度分析
    # ============================================================
    _log("\n[Step 1] 角度分析...", verbose)

    angle_input = {
        "query": query,
        "task_id": task_id,
        "agent_type": agent_type
    }
    angle_result = await run_retrieval_agent("angle_analysis", angle_input)

    if isinstance(angle_result, dict) and "error" in angle_result:
        _log(f"  角度分析失败，使用降级方案: {angle_result.get('error')}", verbose)
        angles = [
            {"id": "A", "name": "正确实现", "query": f"如何正确实现 {query}？"},
            {"id": "B", "name": "边界与异常", "query": f"{query} 有哪些边界条件和异常情况？"},
            {"id": "C", "name": "陷阱防御", "query": f"{query} 有哪些常见陷阱和防御方法？"}
        ]
    else:
        angles = angle_result.get("angles", [])
        if len(angles) < 2:
            default_angles = [
                {"id": "A", "name": "正确实现", "query": f"如何正确实现 {query}？"},
                {"id": "B", "name": "边界与异常", "query": f"{query} 有哪些边界条件？"},
                {"id": "C", "name": "陷阱防御", "query": f"{query} 有哪些常见陷阱？"}
            ]
            for i, ang in enumerate(angles):
                if i < len(default_angles):
                    default_angles[i] = ang
            angles = default_angles

    _log(f"  生成 {len(angles)} 个角度:", verbose)
    for a in angles:
        _log(f"    {a['id']}. {a['name']}: {a['query']}", verbose)

    # ============================================================
    # 步骤 2：3×3 扩散检索（硬编码）
    # ============================================================
    _log("\n[Step 2] 3×3 扩散检索...", verbose)

    all_candidates = []
    seen_ids: set = set()
    for angle in angles:
        results = await retrieve_single_angle(
            task_id=task_id,
            query=angle["query"],
            top_k=top_k_per_angle,
            severity_filter=severity_filter,
            category_filter=category_filter,
            exclude_ids=seen_ids,
        )
        for r in results:
            r["angle_id"] = angle["id"]
            r["angle_name"] = angle["name"]
            seen_ids.add(r["id"])
        all_candidates.extend(results)

    final_results = deduplicate_results(all_candidates, min_similarity=min_similarity)
    stats = format_retrieval_stats(final_results, angles)

    _log(f"  检索完成: {len(all_candidates)} 条候选 → 去重后 {len(final_results)} 条（噪音阈值={min_similarity}）", verbose)
    for i, r in enumerate(final_results):
        _log(f"    {i+1}. [{r.get('angle_name', '未知')}] 相似度 {r.get('similarity', 0):.2f}", verbose)

    # ============================================================
    # 步骤 3：结果交付
    # ============================================================
    _log("\n[Step 3] 结果交付...", verbose)

    if not final_results:
        summary = "知识库暂无相关数据，请直接基于模板生成，不要重试搜索。"
        delivery_content = {"raw_results": []}
        suggestions = ["建议补充更多经验到知识库"]
    else:
        deliver_input = {
            "original_query": query,
            "task_id": task_id,
            "agent_type": agent_type,
            "angles": angles,
            "results": final_results,
            "total_found": len(final_results),
            "empty_result": False,
            "stats": stats
        }
        deliver_result = await run_retrieval_agent("deliver", deliver_input)

        if isinstance(deliver_result, dict) and "error" not in deliver_result:
            summary = deliver_result.get("summary", "")
            delivery = deliver_result.get("delivery", {})
            suggestions = deliver_result.get("suggestions", [])
            if agent_type in delivery:
                delivery_content = delivery[agent_type]
            else:
                delivery_content = delivery
        else:
            summary = f"检索到 {len(final_results)} 条相关经验"
            delivery_content = {"raw_results": final_results}
            suggestions = ["建议补充更多经验到知识库"]

    result["success"] = True
    result["summary"] = summary
    result["delivery"] = delivery_content
    result["raw_results"] = final_results
    result["suggestions"] = suggestions

    _log("\n" + "✅" * 30, verbose)
    _log(f"  检索调度完成", verbose)
    _log(f"  摘要: {summary[:100]}..." if summary else "  无摘要", verbose)
    _log("✅" * 30, verbose)

    # ── 写入 Redis 缓存 ──
    if redis and result["success"]:
        try:
            await redis.set(cache_key, json.dumps(result, ensure_ascii=False), ex=CACHE_TTL)
        except Exception:
            pass

    return result


async def get_prompt_injection(
    task_id: str,
    query: str,
    agent_type: str = "code_generator"
) -> str:
    """便捷方法：直接返回可注入 prompt 的经验文本，供其他 Agent 调用。"""
    result = await retrieval_scheduler(task_id, query, agent_type)
    if result["success"]:
        delivery = result.get("delivery", {})
        if isinstance(delivery, dict) and agent_type in delivery:
            content = delivery[agent_type]
            if isinstance(content, dict) and "content" in content:
                return content["content"]
        if isinstance(delivery, str):
            return delivery
        return result["summary"]
    return "暂无相关经验"


async def inspect_table():
    """检查数据库中的记录，打印前几条经验的关键字段"""
    table = open_table()
    if table is None:
        print("无法打开表")
        return
    rows = table.to_lance().to_table(limit=5).to_pylist()
    print("\n=== 数据库中的经验记录（前5条）===")
    for i, r in enumerate(rows):
        print(f"\n--- 记录 {i+1} ---")
        print(f"source_fingerprint: {r.get('source_fingerprint')}")
        print(f"trigger_contracts: {r.get('trigger_contracts')}")
        print(f"trigger_tags: {r.get('trigger_tags')}")
        print(f"trigger_tasks: {r.get('trigger_tasks')}")
        print(f"do: {r.get('do', '')[:100]}...")
    print("\n====================================\n")


if __name__ == "__main__":
    init_retrieval()
    print(f"已加载 {len(_anchor_cache)} 个任务的图锚点缓存")

    async def main():
        # 先检查数据库记录
        await inspect_table()

        print("检索调度器已启动，正在执行测试查询...")
        # 测试用例：订单库存扣减
        result = await retrieval_scheduler(
            task_id="b_order",
            query="创建订单时如何扣减库存才能防止超卖？",
            agent_type="code_generator",
            top_k_per_angle=3,
            min_similarity=0.55,
            verbose=True,
        )

        print("\n" + "=" * 60)
        print("检索结果摘要:")
        print(f"成功: {result['success']}")
        print(f"摘要: {result['summary']}")
        print(f"结果数: {len(result['raw_results'])}")
        for i, r in enumerate(result['raw_results']):
            print(f"\n--- 结果 {i+1} ---")
            fp = r.get('source_fingerprint', '')
            if not fp:
                fp = r.get('id', '未知')
            print(f"指纹/ID: {fp[:40]}...")
            print(f"DO: {r.get('do', '')[:100]}...")
            print(f"DONT: {r.get('dont', '')[:100]}...")
            print(f"相似度: {r.get('similarity', 0)}")
        print("=" * 60)

    asyncio.run(main())