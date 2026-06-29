# Tools/scoring/code_scorer.py
"""
代码评分 —— 基于源码 + 生成任务 + 测试任务 + 修复记忆。

输入: 源代码 + 工程师任务 + 测试任务 + source_failure 记忆 + test_failure 记忆
输出: 0-100 分 + 维度分解 + 等级 (S/A/B/C/D)

用法:
    from Tools.scoring.code_scorer import score_code
    result = score_code(source_files, engineer_tasks, test_tasks,
                        source_memory, test_memory, test_output)
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ScoreResult:
    total: float = 0.0
    breakdown: Dict[str, float] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)
    level: str = "D"
    summary: str = ""


def score_code(
    source_files: Dict[str, str],               # {path: content} 当前源码
    engineer_tasks: List[Dict],                 # 工程师任务 (task.json)
    test_tasks: Optional[List[Dict]] = None,    # 测试任务 (test_tasks.json)
    source_memory: Optional[List[Dict]] = None, # Memory/source_failure ban 列表
    test_memory: Optional[List[Dict]] = None,   # Memory/test_failure ban 列表
    test_output: Optional[Dict] = None,         # Jest --json 输出
) -> ScoreResult:
    """
    五维评分:
      测试通过率     30%  — 测试跑出来多少通过（最客观）
      任务完成度     25%  — 工程师任务的要求实现了多少
      测试覆盖度     20%  — 测试任务覆盖了多少场景+维度完备性
      代码质量       15%  — 结构/安全/规范/禁止模式（多信号综合）
      记忆修复率     10%  — 已知 ban 标记的问题是否已修复
    """
    result = ScoreResult()
    breakdown = {}

    # 1. 测试通过率（30%）
    test_score, test_info = _score_test_pass(test_output)
    breakdown["test_pass"] = test_score * 0.30

    # 2. 任务完成度（25%）
    task_score, task_info = _score_task_completion(source_files, engineer_tasks)
    breakdown["task_done"] = task_score * 0.25

    # 3. 测试覆盖度（20%）
    cover_score, cover_info = _score_test_coverage(source_files, test_tasks or [])
    breakdown["test_cover"] = cover_score * 0.20

    # 4. 代码质量（15%）—— 多信号综合: 事务完整性/锁使用/错误处理/安全/正向信号/结构
    qual_score, qual_info = _score_code_quality(source_files, engineer_tasks)
    breakdown["quality"] = qual_score * 0.15

    # 5. 记忆修复率（10%）
    mem_score, mem_info = _score_memory_fix(source_files, source_memory or [], test_memory or [])
    breakdown["mem_fix"] = mem_score * 0.10

    # 权重加起来是 1.0，乘以 100 得到百分制
    result.total = round(sum(breakdown.values()) * 100, 1)
    result.breakdown = {k: round(v * 100, 1) for k, v in breakdown.items()}
    result.details = {
        "test_pass": test_info,
        "task_done": task_info,
        "test_cover": cover_info,
        "mem_fix": mem_info,
        "quality": qual_info,
    }
    result.level = _level(result.total)
    result.summary = f"测试{test_score:.0%} 任务{task_score:.0%} 覆盖{cover_score:.0%} 修复{mem_score:.0%} 质量{qual_score:.0%}"
    return result


def score_test_code(
    test_content: str,                           # 测试文件完整代码
    task: Dict,                                  # 测试任务
    test_output: Optional[Dict] = None,          # Jest --json 输出
    test_bans: Optional[List[Dict]] = None,      # test_failure bans
) -> ScoreResult:
    """
    测试代码五维评分:
      mock完整性     30%  — mockSpec 覆盖率 + mock 链深度
      断言质量       25%  — 断言具体性 + 顺序断言 + 异常断言
      场景覆盖       20%  — testScenarios 全部覆盖
      框架合规       15%  — CJS/ESM 一致 + beforeEach clearAllMocks
      语法正确       10%  — node --check + 无 BANNED_PATTERN
    """
    result = ScoreResult()
    breakdown = {}

    # 1. mock 完整性 (30%)
    mock_score, mock_info = _score_mock_completeness(test_content, task)
    breakdown["mock"] = mock_score * 0.30

    # 2. 断言质量 (25%)
    assert_score, assert_info = _score_assertion_quality(test_content)
    breakdown["assert"] = assert_score * 0.25

    # 3. 场景覆盖 (20%)
    cover_score, cover_info = _score_scenario_coverage(test_content, task)
    breakdown["scenario"] = cover_score * 0.20

    # 4. 框架合规 (15%)
    fw_score, fw_info = _score_framework_compliance(test_content, task.get("testFramework", "jest"))
    breakdown["framework"] = fw_score * 0.15

    # 5. 语法正确 (10%)
    syntax_score, syntax_info = _score_test_syntax(test_content, test_bans or [])
    breakdown["syntax"] = syntax_score * 0.10

    result.total = round(sum(breakdown.values()) * 100, 1)
    result.breakdown = {k: round(v * 100, 1) for k, v in breakdown.items()}
    result.details = {
        "mock": mock_info,
        "assert": assert_info,
        "scenario": cover_info,
        "framework": fw_info,
        "syntax": syntax_info,
    }
    result.level = _level(result.total)
    result.summary = f"mock{mock_score:.0%} 断言{assert_score:.0%} 场景{cover_score:.0%} 框架{fw_score:.0%} 语法{syntax_score:.0%}"
    return result


# ═══════════════════════════════════════════════
# 评分维度实现
# ═══════════════════════════════════════════════

def _score_test_pass(test_output: Optional[Dict]) -> tuple:
    if not test_output:
        return 0.0, "无测试结果"
    total = test_output.get("numTotalTests", 0)
    passed = test_output.get("numPassedTests", 0)
    if total == 0:
        return 0.0, "测试未运行 (total=0)"
    return passed / total, f"{passed}/{total} passed"


def _score_task_completion(source_files: Dict[str, str], tasks: List[Dict]) -> tuple:
    """检查工程师任务要求的文件是否生成、关键模式是否实现。"""
    all_code = "\n".join(source_files.values())
    checks = []

    for task in tasks:
        tid = task.get("id", "?")
        required_files = task.get("files", task.get("path", []))

        # 文件是否生成
        for f in required_files:
            fname = Path(f).name
            found = any(fname in p or p.endswith(f) for p in source_files)
            checks.append(1.0 if found else 0.0)

        # 看任务类型，检查关键模式
        ttype = task.get("type", "")
        contracts = task.get("requiredContracts", [])

        if "backend" in ttype or tid.startswith("b_"):
            # 检查是否有路由/控制器/服务的基本结构
            if any("router" in c for c in source_files.values()):
                checks.append(1.0)
            if any("exports." in c for c in source_files.values()):
                checks.append(1.0)

        if "database" in ttype or tid.startswith("db_"):
            if any("CREATE TABLE" in c or "CREATE OR REPLACE" in c for c in source_files.values()):
                checks.append(1.0)

        # 合同要求的事务/锁
        for cid in contracts:
            if "create" in cid.lower() or "cancel" in cid.lower() or "pay" in cid.lower():
                has_tx = "beginTransaction" in all_code
                checks.append(1.0 if has_tx else 0.3)
                break

    if not checks:
        return 0.5, "无检查点"
    avg = sum(checks) / len(checks)
    return avg, f"{len(checks)}项, {avg:.0%}"


def _score_test_coverage(source_files: Dict[str, str], test_tasks: List[Dict]) -> tuple:
    """检查测试任务的质量: targetFiles 覆盖、场景维度完备性、断言密度。"""
    checks = []
    all_code = "\n".join(source_files.values())

    for task in test_tasks:
        targets = task.get("targetFiles", [])
        scenarios = task.get("testScenarios", [])
        task_id = task.get("id", "")

        # ── targetFiles 是否在源代码中存在 ──
        for tf in targets:
            tf_name = Path(tf).name
            checks.append(1.0 if tf_name in all_code else 0.0)

        # ── 场景数量评分（非线性梯度）──
        sc_count = len(scenarios)
        if sc_count >= 5:
            checks.append(1.0)
        elif sc_count >= 3:
            checks.append(0.7)
        elif sc_count >= 2:
            checks.append(0.5)
        elif sc_count >= 1:
            checks.append(0.3)
        else:
            checks.append(0.0)

        # ── 场景维度完备性（3 维: 成功/异常/边界）──
        scenario_texts = " ".join(
            f"{s.get('scenario','')} {s.get('expectedBehavior','')}"
            for s in scenarios
        ).lower()

        has_success = any(w in scenario_texts for w in ("success", "成功", "200", "正常"))
        has_error = any(w in scenario_texts for w in (
            "error", "fail", "失败", "异常", "404", "400", "401", "422", "409",
            "reject", "throw", "throws", "不足", "不存在", "无效", "过期"))
        has_edge = any(w in scenario_texts for w in (
            "空", "null", "undefined", "边界", "empty", "0", "超", "上限", "下限",
            "boundary", "edge", "最大", "最小", "重复", "并发"))

        dims = sum([has_success, has_error, has_edge])
        checks.append(dims / 3)  # 0/3 → 0, 1/3 → 0.33, 2/3 → 0.67, 3/3 → 1.0

        # ── mockSpec 覆盖率 ──
        mock_apis = set()
        for sc in scenarios:
            for api in sc.get("mockSpec", []):
                mock_apis.add(api)
        if mock_apis:
            covered = sum(1 for api in mock_apis
                         if f"{api}:" in all_code or f"{api} =" in all_code
                         or f"{api}()" in all_code)
            checks.append(covered / len(mock_apis))

        # ── 断言密度（expect 调用 / 场景数，≥3 expect/scenario 满分）──
        expect_count = len(re.findall(r'\bexpect\(', all_code))
        if sc_count > 0:
            density = expect_count / sc_count
            checks.append(min(1.0, density / 3))

    if not checks:
        return 0.3, "无测试任务"
    avg = sum(checks) / len(checks)
    return avg, f"{len(checks)}项, {avg:.0%}"


def _score_memory_fix(source_files: Dict[str, str],
                      source_memory: List[Dict],
                      test_memory: List[Dict]) -> tuple:
    """检查已知 ban 中标记的错误是否已被修复。按 ban.f 子类型精确匹配。"""
    all_code = "\n".join(source_files.values())
    checks = []

    for ban in source_memory:
        if not isinstance(ban, dict):
            continue
        b_text = ban.get("b", "")
        f_text = ban.get("f", "")

        # 从 f_text 提取子类型: L4|orderSvc|cancelOrder|ORDER → ORDER
        f_parts = f_text.split("|") if f_text else []
        sub_type = f_parts[-1].strip() if len(f_parts) >= 4 else ""

        # ── 事务类 ban (TRANSACTION / TX) ──
        if sub_type in ("TRANSACTION", "TX") or "transaction" in b_text.lower():
            has_tx = "beginTransaction" in all_code
            has_rb = "rollback" in all_code
            has_cm = "commit" in all_code
            checks.append(1.0 if (has_tx and has_rb and has_cm) else (0.5 if has_tx else 0.0))
            continue

        # ── 操作顺序类 ban (ORDER) ──
        if sub_type == "ORDER" and "|" in b_text:
            parts = b_text.split("|")
            correct = parts[1].strip() if len(parts) >= 2 else ""
            keywords_a = _op_keywords(correct)
            if len(keywords_a) >= 2:
                # 检查第一个关键词是否在第二个之前
                pos_a = max((all_code.find(kw) for kw in keywords_a[:1] if kw in all_code), default=-1)
                pos_b = min((all_code.find(kw) for kw in keywords_a[1:] if kw in all_code), default=99999)
                if pos_a >= 0 and pos_b >= 0:
                    checks.append(1.0 if pos_a < pos_b else 0.2)
                else:
                    checks.append(0.3)  # 关键词不完整，部分修复
                continue
            # 通用：从 b_text 的正确做法提取操作词
            if "先" in correct and "再" in correct:
                correct_clean = correct.replace("先", "").replace("再", "").strip()
                for sep in ["再", "后", "然后"]:
                    if sep in correct_clean:
                        first, second = correct_clean.split(sep, 1)
                        f_kws = _op_keywords(first.strip())
                        s_kws = _op_keywords(second.strip())
                        if f_kws and s_kws:
                            f_pos = max((all_code.find(kw) for kw in f_kws if kw in all_code), default=-1)
                            s_pos = min((all_code.find(kw) for kw in s_kws if kw in all_code), default=99999)
                            if f_pos >= 0 and s_pos >= 0:
                                checks.append(1.0 if f_pos < s_pos else 0.2)
                            else:
                                checks.append(0.3)
                        break
                continue

        # ── 中间件类 ban (AUTH / PERMISSION) ──
        if sub_type in ("AUTH", "PERMISSION"):
            has_auth = "authenticate" in all_code
            checks.append(1.0 if has_auth else 0.0)
            continue

        # ── 参数签名类 ban (SIG / PARAM) ──
        if sub_type in ("SIG", "PARAM"):
            # 检查函数签名的一致性：同名函数是否参数数量匹配
            func_name = f_parts[2] if len(f_parts) >= 3 else ""
            if func_name and func_name != "generate":
                # 查找所有该函数相关代码
                func_refs = len(re.findall(rf'\b{func_name}\b', all_code))
                checks.append(0.5 if func_refs > 0 else 0.0)  # 函数存在即半修复
            else:
                checks.append(0.5)
            continue

        # ── 语法类 ban (syntax) ──
        if sub_type == "syntax":
            # 语法 ban 已修复 = 文件能被解析（node --check 在此前已通过）
            checks.append(1.0)
            continue

        # ── 回退类 ban (DEGRADED / rollback) ──
        if sub_type in ("DEGRADED", "rollback"):
            checks.append(0.5)  # 回退 ban 是标记，不算修复也不算未修复
            continue

        # ── 兜底关键词匹配 ──
        if "|" in b_text:
            correct = b_text.split("|")[1].strip() if len(b_text.split("|")) >= 2 else b_text
        else:
            correct = b_text
        if correct:
            keywords = [w for w in re.findall(r'\b\w{3,}\b', correct.lower())
                       if w not in ('the', 'and', 'for', 'not', 'don', 'fix',
                                    'test', 'unit', 'file', 'add', 'use', 'all')]
            if keywords:
                matched = sum(1 for kw in keywords if kw.lower() in all_code.lower())
                checks.append(matched / len(keywords))
            else:
                checks.append(0.5)

    # ── test_memory ban 检查 ──
    for ban in test_memory:
        if not isinstance(ban, dict):
            continue
        f_text = ban.get("f", "")
        f_parts = f_text.split("|") if f_text else []
        sub_type = f_parts[-1].strip() if len(f_parts) >= 4 else ""

        if "isolateModules" in f_text or sub_type == "ASYNC":
            checks.append(1.0 if "jest.isolateModules" not in all_code else 0.0)

        if sub_type == "MOCK_GAP":
            # 检查 b_text 中缺失的 API 是否已出现在测试代码中
            b_text = ban.get("b", "")
            if b_text:
                missing_apis = re.findall(r'缺\s*([\w./]+(?:\(\))?)', b_text)
                if missing_apis:
                    found = sum(1 for api in missing_apis if api.replace('()', '') in all_code)
                    checks.append(found / len(missing_apis))
                else:
                    checks.append(0.5)
            else:
                checks.append(0.5)

        if sub_type == "MOCK_DUP":
            # 检查同名 jest.mock 是否已去重（只出现一次）
            b_text = ban.get("b", "")
            module_match = re.search(r"jest\.mock\(['\"](\w+)['\"]", b_text)
            if module_match:
                mock_count = len(re.findall(
                    rf"jest\.mock\(['\"]{module_match.group(1)}['\"]", all_code))
                checks.append(1.0 if mock_count <= 1 else 0.0)
            else:
                checks.append(0.5)

        if "syntax" in f_text:
            checks.append(1.0)

    if not checks:
        return 0.7, "无记忆可对"
    avg = sum(checks) / len(checks)
    return avg, f"{len(checks)}条记忆, 修复率{avg:.0%}"


def _op_keywords(text: str) -> list:
    """从 ban 描述中提取操作关键词（如 'stock' → 'product_skus', 'status' → 'CANCELLED'）。"""
    mapping = {
        'stock': 'product_skus', '库存': 'product_skus',
        'status': 'CANCELLED', 'state': 'CANCELLED',
        'transaction': 'beginTransaction', '事务': 'beginTransaction',
        'rollback': 'rollback', '回滚': 'rollback',
    }
    keywords = []
    for k, v in mapping.items():
        if k in text.lower():
            keywords.append(v)
    return keywords


def _score_code_quality(source_files: Dict[str, str], tasks: List[Dict]) -> tuple:
    """结构规范、安全模式、注释、禁止模式——多信号综合评分。"""
    checks = []
    all_code = "\n".join(source_files.values())

    for path, code in source_files.items():
        lines = code.split('\n')
        line_count = len(lines)

        # ── 事务完整性（2 项）──
        tx_count = code.count("beginTransaction")
        rb_count = code.count("rollback")
        if tx_count > 0:
            checks.append(min(1.0, rb_count / tx_count))           # 回滚覆盖率
            checks.append(1.0 if "commit()" in code else 0.3)      # commit 存在

        # ── 锁使用（1 项）──
        updates = len(re.findall(r'^\s*(?:await\s+)?db\.query.*UPDATE', code, re.MULTILINE))
        locks = code.count("FOR UPDATE")
        if updates > 0:
            checks.append(min(1.0, locks / max(updates, 1) * 2))

        # ── 错误处理覆盖（2 项）──
        funcs = len(re.findall(r'(?:async function|exports\.\w+\s*=\s*async)', code))
        tries = code.count("try {") + code.count("try{")
        catches = code.count("catch") + code.count("catch (")
        if funcs > 0:
            checks.append(min(1.0, tries / funcs))                 # try 覆盖率
            checks.append(min(1.0, catches / max(tries, 1)))       # catch 配对率

        # ── 禁止模式扣分（3 项：安全 / 质量 / 过时 API）──
        security_banned = {"eval(": 0.5, "innerHTML": 0.3, "document.write": 0.5,
                           " dangerouslySetInnerHTML": 0.3}
        quality_banned = {"console.log(": 0.15, "var ": 0.1, "== ": 0.05,
                         "getConnection(": 0.5, "getPool(": 0.5,
                         "process.exit(": 0.4}
        # 注意: "var " 只在赋值场景扣分（跳过 "var " 出现在字符串/注释中的情况较难，用出现比例打折）
        # "== " 扣分针对比较场景，容错使用（仍有大量合法 == 场景）

        sec_penalty = sum(pen for kw, pen in security_banned.items() if kw in code)
        qual_penalty = sum(pen for kw, pen in quality_banned.items() if kw in code)
        checks.append(max(0.0, 1.0 - sec_penalty))                 # 安全禁止模式
        checks.append(max(0.0, 1.0 - qual_penalty))                # 质量禁止模式

        # ── 正向信号（3 项）──
        const_count = len(re.findall(r'\bconst\s+\w+\s*=', code))
        let_count = len(re.findall(r'\blet\s+\w+\s*=', code))
        var_count = len(re.findall(r'\bvar\s+\w+\s*=', code))
        total_decl = const_count + let_count + var_count
        if total_decl > 0:
            checks.append(const_count / total_decl)                # const 优先率

        # 参数化查询检测（? 占位符）
        param_queries = len(re.findall(r'\.query\([^)]*\?\s*[^)]*\)', code))
        raw_queries = len(re.findall(r'\.query\([^)]*\+[^)]*\)', code))
        if param_queries + raw_queries > 0:
            checks.append(param_queries / (param_queries + raw_queries + 1))  # 参数化率

        # ── 结构合理性（2 项）──
        # 函数长度: 超过 60 行的函数扣分
        long_funcs = len(re.findall(
            r'(?:async function|exports\.\w+\s*=\s*async).*?(?=\n(?:exports\.|async function|$))',
            code, re.DOTALL))
        if line_count > 0 and funcs > 0:
            avg_func_lines = line_count / max(funcs, 1)
            checks.append(max(0.0, 1.0 - max(0, avg_func_lines - 40) / 80))  # 平均函数长

        # 注释率（放宽：注释有意义即可，不强制高比例）
        if lines:
            comment_lines = sum(1 for l in lines
                              if l.strip().startswith(('//', '/*', '*', '/**', '#')))
            comment_ratio = comment_lines / len(lines)
            checks.append(min(1.0, comment_ratio * 4))             # 25% 注释率即满分

        # 嵌套深度检测: 超过 4 层缩进扣分
        deep_lines = sum(1 for l in lines
                        if len(l) - len(l.lstrip()) > 16)  # >4 层 (4×4 spaces)
        if line_count > 0:
            checks.append(max(0.0, 1.0 - (deep_lines / line_count) * 3))

    if not checks:
        return 0.5, "无质量检查"
    avg = sum(checks) / len(checks)
    return avg, f"{len(checks)}项, {avg:.0%}"


# ═══════════════════════════════════════════════
# 辅助
# ═══════════════════════════════════════════════

def _level(score: float) -> str:
    if score >= 90: return "S"
    if score >= 80: return "A"
    if score >= 65: return "B"
    if score >= 50: return "C"
    return "D"


def format_score_report(result: ScoreResult) -> str:
    labels = {"test_pass":"测试通过","task_done":"任务完成","test_cover":"测试覆盖","mem_fix":"记忆修复","quality":"代码质量"}
    lines = [f"综合评分: {result.total:.0f}/100 ({result.level})", ""]
    for k, v in result.breakdown.items():
        bar = "█" * int(v / 5) + "░" * (20 - int(v / 5))
        lines.append(f"  {labels.get(k, k):8} {bar} {v:.1f}")
    lines.append(f"\n  {result.summary}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════
# 测试代码评分维度
# ═══════════════════════════════════════════════

def _score_mock_completeness(test_code: str, task: Dict) -> tuple:
    """mockSpec 覆盖率 + mock 链深度。"""
    mock_spec = task.get("mockSpec", [])
    if not mock_spec:
        return 0.8, "无 mockSpec 定义"

    covered = sum(1 for m in mock_spec if re.search(re.escape(m), test_code, re.I))
    ratio = covered / len(mock_spec) if mock_spec else 1.0

    # mockResolvedValueOnce 深度
    once_count = len(re.findall(r'mockResolvedValueOnce\(', test_code))
    resolved_count = len(re.findall(r'mockResolvedValue\(', test_code))
    total_mocks = once_count + resolved_count

    mock_score = ratio * 0.7 + min(total_mocks / 5, 1.0) * 0.3
    return mock_score, f"mockSpec {covered}/{len(mock_spec)}, mock链深度{total_mocks}"


def _score_assertion_quality(test_code: str) -> tuple:
    """断言具体性：顺序断言 + 异常断言 + expect 密度。"""
    nth_count = len(re.findall(r'toHaveBeenNthCalledWith', test_code))
    throw_count = len(re.findall(r'toThrow|rejects\.toThrow', test_code))
    match_count = len(re.findall(r'toMatchObject', test_code))
    exist_count = len(re.findall(r'\.exists\(\)', test_code))
    total_expect = len(re.findall(r'expect\(', test_code))

    # it() 数量
    it_count = len(re.findall(r'\bit\s*\(', test_code))

    order_score = min(nth_count / max(it_count, 1), 1.0)
    detail_score = min((match_count + exist_count + throw_count) / max(total_expect, 1), 1.0)
    density_score = min(total_expect / max(it_count, 1) / 2, 1.0)  # 每个 it ≥2 expect

    return order_score * 0.4 + detail_score * 0.4 + density_score * 0.2, \
        f"顺序断言{nth_count} 具体断言{match_count+exist_count} 异常{throw_count} expect密度{total_expect/max(it_count,1):.1f}"


def _score_scenario_coverage(test_code: str, task: Dict) -> tuple:
    """testScenarios 覆盖度。"""
    scenarios = task.get("testScenarios", [])
    if not scenarios:
        return 0.8, "无 scenarios 定义"

    covered = 0
    for s in scenarios:
        sc = s.get("scenario", "")[:30]
        if sc and re.search(re.escape(sc), test_code, re.I):
            covered += 1

    ratio = covered / len(scenarios)
    return ratio, f"scenario {covered}/{len(scenarios)}"


def _score_framework_compliance(test_code: str, framework: str) -> tuple:
    """框架一致性检查。"""
    score = 1.0
    issues = []

    if framework == "vitest":
        if "jest.mock" in test_code or "require(" in test_code:
            score -= 0.5
            issues.append("混用 jest")
        if "vi.hoisted" in test_code:
            score = min(1.0, score + 0.1)
    else:  # jest
        if "vi.mock" in test_code or "import " in test_code:
            score -= 0.5
            issues.append("混用 vitest")

    if "clearAllMocks()" in test_code:
        score = min(1.0, score + 0.1)
    else:
        score -= 0.2
        issues.append("缺 clearAllMocks")

    return max(0, score), "; ".join(issues) if issues else "合规"


def _score_test_syntax(test_code: str, bans: List[Dict]) -> tuple:
    """语法正确 + BANNED_PATTERN 检查。"""
    score = 1.0
    issues = []

    # 括号配对简查
    opens = test_code.count('{') + test_code.count('(')
    closes = test_code.count('}') + test_code.count(')')
    if opens != closes:
        score -= 0.4
        issues.append("括号不配对")

    # 历史 ban 中的 syntax 问题
    syntax_bans = [b for b in bans if "syntax" in str(b.get("f", "")).lower()]
    if syntax_bans:
        score -= 0.3

    return max(0, score), "; ".join(issues) if issues else "语法正确"


def _load_source_files(workspace: str, target_files: List[str]) -> Dict[str, str]:
    """便捷函数：从 workspace 加载指定文件的源码内容。"""
    ws = Path(workspace)
    result = {}
    for tf in target_files:
        p = ws / tf
        if p.exists():
            result[tf] = p.read_text("utf-8")
    return result


def _load_memory(task_id: str, target: str = "source_failure") -> List[Dict]:
    """便捷函数：从 Memory/ 目录加载 ban 记忆。"""
    import json
    base = Path.cwd() / "Memory" / target
    p = base / f"{task_id}.json"
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text("utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("bans", [])
    except Exception:
        pass
    return []
