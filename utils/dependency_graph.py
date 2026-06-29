# utils/dependency_graph.py
"""
共享依赖图构建 — 拓扑排序 + 严格类型分层。

核心规则:
  1. 同类型任务必须在连续层中执行（提高 LLM system prompt 缓存命中率）
  2. 不同类型任务不得在同一层并发（避免 prompt 前缀频繁切换）
  3. 层间按 (拓扑深度, 类型优先级) 排序

类型优先级（自底向上）:
  infra < db < backend < frontend < integration
"""

from typing import List, Dict, Tuple, Optional

TYPE_ORDER = [
    "repair",          # -1: 修复层
    "infra",           #  0: 基础设施
    "db",              #  1: 数据库
    "frontend_static", #  1.5: 前端静态
    "auth",            #  2: Auth
    "db_api",          #  3: db-api
    "peer_deps",       #  3.5: 同层依赖
    "api",             #  4: api
    "backend_proc",    #  4.5: 后端处理
    "navigation",      #  5: navigation
    "logic",           #  6: logic
    "scenario",        #  7: scenario
    "nfr",             #  8: NFR
]
_TYPE_RANK = {t: i for i, t in enumerate(TYPE_ORDER)}


def _get_tid(t: dict) -> str:
    """统一 task ID 获取（兼容 taskId / id）。"""
    return t.get("taskId") or t.get("id", "")


def _get_type(t: dict) -> str:
    """统一 type 获取。优先 layer（测试任务），fallback 到 type（架构任务）。"""
    raw = t.get("layer") or t.get("type") or ""
    # 旧名→新名归一化
    aliases = {"infrastructure": "infra", "database": "db",
               "frontend": "frontend_static", "backend": "backend_proc"}
    return aliases.get(raw, raw)


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

    return task_map, dependents, in_degree


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

    # ── Step 2: 排序（先按类型优先级，再按深度）──
    # 🛑 类型优先于深度：确保所有 infra 在一起、所有 db 在一起...
    #    只有同类型任务内部的依赖关系才体现在深度排序中
    sorted_tasks = sorted(
        tasks,
        key=lambda t: (
            _TYPE_RANK.get(_get_type(t), 99),   # 类型优先
            depth.get(_get_tid(t), 999),         # 同类型内按深度
        ),
    )

    # ── Step 3: 同类型按依赖深度拆分为连续层 ——
    # 同类型任务仍保持连续（缓存命中），但若有依赖关系则拆层
    layers: List[List[dict]] = []
    current_type: Optional[str] = None
    current_layer: List[dict] = []

    for t in sorted_tasks:
        ttype = _get_type(t)
        tid = _get_tid(t)
        deps = set(t.get("dependencies", []))
        layer_ids = {_get_tid(x) for x in current_layer}

        # 新类型 或 依赖当前层内某个任务 → 新层
        if ttype != current_type or (deps & layer_ids):
            if current_layer:
                layers.append(current_layer)
            current_type = ttype
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
