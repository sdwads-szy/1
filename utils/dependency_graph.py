# utils/dependency_graph.py
"""
共享依赖图构建 — 拓扑排序 + 3 大测试类型分层。

核心规则:
  1. 同类型任务必须在连续层中执行
  2. 层间按 (拓扑深度, 类型优先级) 排序: static → interface → logic
"""

from typing import List, Dict, Tuple, Optional

# 4 大测试类型 — 自底向上
TYPE_ORDER = [
    "static",          # 0: 静态检查 (infra/db/frontend/peer_deps/integ)
    "interface",       # 1: 接口测试 (auth/db_api/api/navigation)
    "logic",           # 2: 逻辑测试 (backend_proc/logic/scenario)
    "quality",         # 3: 质量测试 (nfr)
]
_TYPE_RANK = {t: i for i, t in enumerate(TYPE_ORDER)}

# 同一 testType 内的原始层优先级（子层排序）
_SUB_LAYER_RANK = {
    "repair": 0, "infra": 1, "db": 2, "frontend_static": 3, "frontend": 3,
    "peer_deps": 4, "integ": 5,
    "auth": 10, "db_api": 11, "api": 12, "navigation": 13,
    "backend_proc": 20, "backend": 20, "logic": 21, "scenario": 22, "nfr": 23,
}

# 层 → 4 类型映射
_LAYER_TO_TYPE = {
    "repair": "static", "infra": "static", "db": "static",
    "frontend": "static", "peer_deps": "static", "integ": "static",
    "auth": "interface", "db_api": "interface", "api": "interface",
    "navigation": "interface",
    "backend_proc": "logic", "backend": "logic",
    "logic": "logic", "scenario": "logic",
    "nfr": "quality",
}


def _get_tid(t: dict) -> str:
    """统一 task ID 获取（兼容 taskId / id）。"""
    return t.get("taskId") or t.get("id", "")


def _get_type(t: dict) -> str:
    """统一 type 获取。优先 testType（新），fallback layer→映射，最后 type。"""
    # 新格式：testType
    tt = t.get("testType", "")
    if tt in _TYPE_RANK:
        return tt
    # 旧格式：layer → 映射到 3 类型
    raw = t.get("layer") or t.get("type") or ""
    aliases = {"infrastructure": "infra", "database": "db",
               "frontend": "frontend_static", "backend": "backend_proc"}
    old_type = aliases.get(raw, raw)
    return _LAYER_TO_TYPE.get(old_type, old_type)


def build_full(tasks: list) -> Tuple[Dict[str, dict], Dict[str, list], Dict[str, int]]:
    """构建完整依赖图数据，返回 (task_map, dependents, in_degree)。

    Returns:
        - task_map: {task_id: task_dict}
        - dependents: {task_id: [dependent_ids]}  (被依赖方 → 依赖方列表)
        - in_degree: {task_id: int}                (每个任务的未完成依赖数)
    """
    task_map = {_get_tid(t): t for t in tasks}
    in_degree = {}
    dependents = {}

    for t in tasks:
        tid = _get_tid(t)
        in_degree[tid] = len(t.get("dependencies", []))
        dependents[tid] = []

    for t in tasks:
        for dep in t.get("dependencies", []):
            if dep in dependents:
                dependents[dep].append(_get_tid(t))

    # 🛑 环检测
    cycles = _detect_cycles(task_map)
    if cycles:
        print(f"[dependency_graph] ⚠️ {len(cycles)} 个循环依赖: {cycles}")

    return task_map, dependents, in_degree


def _detect_cycles(task_map: dict) -> list:
    """DFS 检测依赖图中的环"""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {tid: WHITE for tid in task_map}
    cycles = []

    def dfs(tid, path):
        color[tid] = GRAY
        for dep in task_map[tid].get("dependencies", []):
            if dep not in color: continue
            if color[dep] == GRAY:
                start = path.index(dep) if dep in path else 0
                cycles.append(path[start:] + [dep])
            elif color[dep] == WHITE:
                dfs(dep, path + [dep])
        color[tid] = BLACK

    for tid in task_map:
        if color[tid] == WHITE:
            dfs(tid, [tid])
    return cycles


def build_layered(tasks: list) -> List[List[dict]]:
    """构建严格类型分层的执行计划。

    算法:
      1. 计算每个任务的拓扑深度:
         depth[t] = 0                            (无依赖)
         depth[t] = max(depth[dep] for dep in deps) + 1  (有依赖)
      2. 每个任务分配 (depth, type_rank) 排序键
      3. 按排序键全局排序
      4. 相邻同类型任务合并为一层 → 并行执行

    Returns:
        [[task_dict, ...], ...]  — 每层为同类型任务列表
    """
    if not tasks:
        return []

    task_map = {_get_tid(t): t for t in tasks}

    # ── Step 1: 计算拓扑深度（迭代至收敛，最大迭代次数防循环依赖）──
    depth: Dict[str, int] = {_get_tid(t): 0 for t in tasks}
    changed = True
    iteration = 0
    max_iterations = len(tasks) * 10  # 防止循环依赖导致死循环
    while changed and iteration < max_iterations:
        changed = False
        iteration += 1
        for t in tasks:
            tid = _get_tid(t)
            deps = t.get("dependencies", [])
            if deps:
                max_dep = max(depth.get(d, 0) for d in deps)
                new_d = max_dep + 1
                if new_d > depth[tid]:
                    depth[tid] = new_d
                    changed = True
    if iteration >= max_iterations:
        # 检测到循环依赖，打印受影响的节点
        cyclic = [tid for tid, d in depth.items() if d >= max_iterations // 2]
        raise ValueError(f"Circular dependency detected among tasks: {cyclic[:10]}")

    # ── Step 2: 排序（类型 → 子层 → 深度）──
    def _sort_key(t):
        ttype = _get_type(t)
        layer = t.get("layer") or _get_type(t)
        return (
            _TYPE_RANK.get(ttype, 99),
            _SUB_LAYER_RANK.get(layer, 50),
            depth.get(_get_tid(t), 999),
        )

    sorted_tasks = sorted(tasks, key=_sort_key)

    # ── Step 3: 按 (type, sublayer) 拆分 ——
    # 同一 (testType, 原始layer) 内仍有依赖时再拆
    layers: List[List[dict]] = []
    current_type: Optional[str] = None
    current_sublayer: Optional[int] = None
    current_layer: List[dict] = []

    for t in sorted_tasks:
        ttype = _get_type(t)
        layer = t.get("layer") or ttype
        sublayer = _SUB_LAYER_RANK.get(layer, 50)
        tid = _get_tid(t)
        deps = set(t.get("dependencies", []))
        layer_ids = {_get_tid(x) for x in current_layer}

        # 新类型 / 新子层 / 依赖当前层任务 → 新层
        if ttype != current_type or sublayer != current_sublayer or (deps & layer_ids):
            if current_layer:
                layers.append(current_layer)
            current_type = ttype
            current_sublayer = sublayer
            current_layer = [t]
        else:
            current_layer.append(t)

    if current_layer:
        layers.append(current_layer)

    return layers


def build(tasks: list) -> Tuple[Dict[str, dict], List[List[dict]]]:
    """兼容旧接口：返回 (task_map, levels)。levels 已按类型分层。"""
    task_map = {_get_tid(t): t for t in tasks}
    levels = build_layered(tasks)
    return task_map, levels


def split_by_type(levels: list) -> list:
    """兼容旧接口：build_layered 已按类型分层，直接返回。"""
    return levels


def print_levels(levels: list) -> None:
    """兼容旧接口：打印分层信息。"""
    print_layers(levels)


def print_layers(layers: List[List[dict]]) -> None:
    """打印分层信息，用于调试。"""
    for i, layer in enumerate(layers):
        ids = [_get_tid(t) for t in layer]
        types = {_get_type(t) for t in layer}
        type_str = ", ".join(sorted(types))
        print(f"  Layer {i}: {len(layer)} tasks [{type_str}] — {ids[:5]}{'...' if len(ids) > 5 else ''}")
