# Tools/memory/merge_memory.py
"""
记忆合并工具。纯函数，供各类 Agent 复用。
模块维度：modules = {"模块名": {"s","p","f","b","d","t","i","c"}}

字段缩写:
  s = 一句话总结 (R1产出)
  p = priority / 分期 (一期/二期/降级)
  f = frontend / 前台功能
  b = backend  / 后台功能
  d = data     / 数据实体与约束
  t = test     / 验收标准
  i = innovation / 创新建议 (Innovator 提出, Architect 确认技术可行)
  c = cost    / 月度运营成本 (Architect 估算, 过高则否决或降级)
"""


def append_round(round_num: int, round_data: dict, full_memory: dict) -> dict:
    """
    追加本轮记录到 full_memory。同名轮次覆盖（支持重试），保留最近 20 轮。
    """
    entry = {
        "round": round_num,
        "topic": round_data.get("topic", ""),
        "summary": round_data.get("summary", ""),
        "modules": round_data.get("modules", {}),
        "entities": round_data.get("entities", []),
        "pending": round_data.get("pending", []),
    }

    rounds = full_memory.setdefault("rounds", [])
    existing = [r for r in rounds if r["round"] != round_num]
    existing.append(entry)
    full_memory["rounds"] = existing[-20:]
    return full_memory


def merge_round(round_num: int, round_data: dict, summary: dict) -> dict:
    """
    模块维度合并到累积摘要。字段白名单，杜绝旧模板残留。

    modules: 同名模块 deep merge（新字段覆盖旧字段）
    entities: 去重追加
    pending: 按 q 文本去重
    """
    clean = {
        "session_id": summary.get("session_id", ""),
        "original_requirement": summary.get("original_requirement", ""),
        "updated_round": round_num,
        "modules": _merge_modules(summary.get("modules", {}), round_data.get("modules", {})),
        "entities": sorted(set(
            summary.get("entities", []) + round_data.get("entities", [])
        )),
        "pending": _merge_pending(summary.get("pending", []), round_data.get("pending", [])),
    }
    return clean


def _merge_dict(base: dict, update: dict) -> dict:
    """浅合并，update 优先"""
    if not update:
        return base
    return {**base, **update}


def _merge_modules(existing: dict, incoming: dict) -> dict:
    """合并模块：同名 deep merge，新模块追加"""
    result = dict(existing)
    for name, fields in incoming.items():
        if name in result:
            result[name] = {**result[name], **fields}
        else:
            result[name] = dict(fields)
    return result


def _merge_pending(existing: list, incoming: list) -> list:
    """合并待解决问题：按 q 文本去重，保留最近 20 条"""
    seen = set()
    result = []
    for p in existing + incoming:
        q = _get(p, "q") or _get(p, "question", "")
        if q and q not in seen:
            seen.add(q)
            normalized = {"q": q}
            for src, dst in [("m", "m"), ("module", "m"),
                              ("d", "d"), ("default", "d"),
                              ("r", "r"), ("round", "r")]:
                v = _get(p, src)
                if v and dst not in normalized:
                    normalized[dst] = v
            result.append(normalized)
    return result[-20:]


def _get(d: dict, *keys):
    """从 dict 取第一个存在的 key 的值"""
    for k in keys:
        v = d.get(k)
        if v is not None:
            return v
    return None
