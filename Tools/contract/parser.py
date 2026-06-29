# Tools/contract/parser.py
"""
合同步骤解析器 —— 将 logic 契约的 steps 转为具体实现指令，注入工程师 Agent prompt。

用法:
    from Tools.contract.parser import contract_to_prompt
    instructions = contract_to_prompt(logic_contracts)
"""

from typing import List, Dict, Any


def contract_to_prompt(contracts: List[Dict]) -> str:
    """将多个 logic 契约转为工程师可执行的具体实现指令。"""
    logic_contracts = [c for c in contracts if c.get("type") == "logic"]
    if not logic_contracts:
        return ""

    sections = []
    for c in logic_contracts:
        cid = c.get("contractId", "")
        desc = c.get("description", "")
        impl = _parse_one(c)
        if impl:
            sections.append(f"### {cid}: {desc}\n{impl}")

    if not sections:
        return ""

    return "\n## 契约步骤解析（必须逐条实现，缺一视为 Bug）\n\n" + "\n\n".join(sections)


def _parse_one(c: dict) -> str:
    lines = []
    steps = c.get("steps", [])
    cc = c.get("concurrencyControl", {})
    errs = c.get("errorMapping", {})
    tx_boundary = c.get("transactionBoundary", False)
    compensation = c.get("compensation", {})
    proc_sig = c.get("procedureSignature", "")

    # 1. 存储过程（特殊处理）
    if c.get("implementation") == "stored_procedure" and proc_sig:
        lines.append(f"调用存储过程: `{proc_sig}`")
        lines.append("  - 参数顺序必须与签名完全一致")
        lines.append("  - OUT 参数通过用户变量取回")
        for code, mapping in errs.items():
            lines.append(f"  - 错误码 {code} → HTTP {mapping.get('httpStatus', 500)} {mapping.get('message', '')}")
        return "\n".join(lines)

    # 2. 事务边界
    if tx_boundary:
        lines.append("**事务要求**:")
        lines.append("  - 开启事务: `await db.beginTransaction()`")
        lines.append("  - 成功: `await db.commit()`")
        lines.append("  - 失败: `await db.rollback()` + `throw err`")
        lines.append("  - try/catch 必须包裹所有写操作")

    # 3. 并发控制
    strategy = cc.get("strategy", "")
    lock_target = cc.get("lockTarget", "")
    if strategy == "pessimistic_lock":
        lines.append(f"**悲观锁**: SELECT ... FOR UPDATE ON `{lock_target}` (事务内第一个查询前加锁)")
    elif strategy == "optimistic_lock":
        lines.append(f"**乐观锁**: UPDATE 时检查 `{lock_target}` 的 version 字段，影响行数=0 则返回 409")
    elif strategy == "redis_lua_atomic":
        lines.append("**Redis 原子操作**: 使用 Lua 脚本保证原子性")

    # 4. 补偿逻辑
    if compensation:
        comp_steps = compensation.get("steps", [])
        if comp_steps:
            lines.append("**补偿逻辑 (Saga)**:")
            for cs in comp_steps:
                lines.append(f"  - 失败时: {cs.get('onFailure', '')} → 补偿: {cs.get('undoOperation', '')}")

    # 5. 步骤详解
    if steps:
        lines.append("**实现步骤 (strict order)**:")
        for i, step in enumerate(steps, 1):
            sid = step.get("stepId", f"step_{i}")
            sdesc = step.get("description", "")
            stype = step.get("type", "")
            rule = step.get("businessRule", "")
            fail_action = step.get("failureAction", "")
            error_code = step.get("errorCode", "")
            db_ops = step.get("dbOperations", [])

            # 步骤类型
            if stype == "control":
                lines.append(f"  {i}. [{sid}] 控制: {sdesc}")
            elif sdesc:
                lines.append(f"  {i}. [{sid}] {sdesc}")

            # 业务规则 → 条件检查
            if rule:
                lines.append(f"     - 条件: `{rule}` → 不满足时抛异常")
            if fail_action:
                lines.append(f"     - 失败: {fail_action}" + (f" → error_code={error_code}" if error_code else ""))
            if error_code and not fail_action:
                lines.append(f"     - 失败时返回: {error_code}")

            # DB 操作 → SQL 模板
            for op in db_ops:
                op_type = op.get("type", "")
                table = op.get("table", "")
                condition = op.get("condition", "")
                set_clause = op.get("set", "")
                fields = op.get("fields", [])
                generates = op.get("generates", "")

                if op_type == "SELECT":
                    lines.append(f"     - SELECT FROM `{table}` WHERE {condition}")
                elif op_type == "SELECT ... FOR UPDATE":
                    lines.append(f"     - SELECT ... FOR UPDATE `{table}` WHERE {condition}")
                elif op_type == "UPDATE":
                    lines.append(f"     - UPDATE `{table}` SET {set_clause} WHERE {condition}")
                elif op_type == "INSERT":
                    fields_str = ", ".join(fields)
                    lines.append(f"     - INSERT INTO `{table}` ({fields_str})" + (f" → 生成 {generates}" if generates else ""))
                elif op_type == "DELETE":
                    lines.append(f"     - DELETE FROM `{table}` WHERE {condition}")

    # 6. 错误码映射
    if errs:
        lines.append("**错误码映射**:")
        for code, mapping in errs.items():
            lines.append(f"  - `{code}` → throw Error('{mapping.get('message', code)}'), code={mapping.get('httpStatus', 500)}")

    return "\n".join(lines)


def contract_to_test_scenarios(contracts: List[Dict]) -> List[Dict]:
    """从 logic 契约的 steps + errorMapping 生成测试场景建议。"""
    scenarios = []
    for c in contracts:
        if c.get("type") != "logic":
            continue
        cid = c.get("contractId", "")

        # 成功路径
        steps = c.get("steps", [])
        mutation_steps = [s for s in steps if s.get("dbOperations")]
        if mutation_steps:
            scenarios.append({
                "scenario": f"{cid} success",
                "mockSpec": _mock_spec_from_steps(steps),
                "assertType": "equals",
                "expectedBehavior": f"returns expected result from {cid}"
            })

        # 多步骤顺序检测
        mutation_steps_list = [s for s in steps if s.get("dbOperations")]
        if len(mutation_steps_list) >= 2:
            op_descs = []
            for s in mutation_steps_list:
                for op in s.get("dbOperations", []):
                    table = op.get("table", "?")
                    optype = op.get("type", "").replace("SELECT ... FOR UPDATE", "SELECT").split()[0]
                    if optype in ("UPDATE", "INSERT", "DELETE"):
                        op_descs.append(f"{optype} {table}")
            if op_descs:
                scenarios.append({
                    "scenario": f"{cid} operation order: {' → '.join(op_descs)}",
                    "mockSpec": _mock_spec_from_steps(steps),
                    "assertType": "callOrder",
                    "expectedBehavior": f"db.query calls in order: {' then '.join(op_descs)}"
                })

        # 并发控制
        cc = c.get("concurrencyControl", {})
        if cc.get("strategy") == "pessimistic_lock":
            scenarios.append({
                "scenario": f"{cid} uses FOR UPDATE lock",
                "mockSpec": _mock_spec_from_steps(steps),
                "assertType": "callOrder",
                "expectedBehavior": "SELECT ... FOR UPDATE before any UPDATE"
            })
        if cc.get("strategy") == "optimistic_lock":
            scenarios.append({
                "scenario": f"{cid} handles version conflict (409)",
                "mockSpec": _mock_spec_from_steps(steps),
                "assertType": "throws",
                "expectedBehavior": "rejects with 409 when version mismatch"
            })

        # 事务
        if c.get("transactionBoundary"):
            scenarios.append({
                "scenario": f"{cid} uses transaction",
                "mockSpec": _mock_spec_from_steps(steps),
                "assertType": "called",
                "expectedBehavior": "db.beginTransaction and db.commit called"
            })

        # 错误路径
        for code, mapping in c.get("errorMapping", {}).items():
            scenarios.append({
                "scenario": f"{cid} error: {code}",
                "mockSpec": _mock_spec_from_steps(steps),
                "assertType": "throws",
                "expectedBehavior": f"rejects with {mapping.get('httpStatus', 500)}: {mapping.get('message', code)}"
            })

    return scenarios


def _mock_spec_from_steps(steps: list) -> list:
    """从 steps 自动推断需要的 mock API。"""
    apis = {"query"}
    for s in steps:
        for op in s.get("dbOperations", []):
            t = op.get("type", "")
            if "UPDATE" in t or "INSERT" in t or "DELETE" in t:
                apis.update(["beginTransaction", "commit", "rollback"])
            if "FOR UPDATE" in t:
                apis.update(["beginTransaction", "commit", "rollback"])
    return sorted(apis)


def enrich_test_tasks(test_tasks: List[Dict], contracts: List[Dict]) -> List[Dict]:
    """给已有的 test_tasks 补充合同自动生成的场景（去重）。"""
    auto_scenarios = contract_to_test_scenarios(contracts)

    # 按合同 ID 索引自动场景
    auto_by_task = {}
    for s in auto_scenarios:
        # scenario 格式: "contractId: ..." 或 "contractId error: ..."
        cid = s["scenario"].split(" ")[0]
        auto_by_task.setdefault(cid, []).append(s)

    enriched = []
    for task in test_tasks:
        tid = task.get("id", "")
        existing_scenarios = task.get("testScenarios", [])

        # 找到关联的逻辑合同 (通过 requiredContracts)
        # 简化: 从 task targetFiles 推断 —— 如果包含 service，找同名 logic 合同
        target = " ".join(task.get("targetFiles", []))
        matched_cid = None
        for cid in auto_by_task:
            # 合同名转服务名: logic_cancel_order → cancelOrder 或 order
            name_parts = cid.replace("logic_", "").split("_")
            for part in name_parts:
                if part in target.lower():
                    matched_cid = cid
                    break
            if matched_cid:
                break

        if matched_cid:
            auto = auto_by_task.get(matched_cid, [])
            # 去重：已有场景不追加
            existing_titles = {s.get("scenario", "") for s in existing_scenarios}
            new_auto = [s for s in auto if s["scenario"] not in existing_titles]
            if new_auto:
                task = dict(task)
                task["testScenarios"] = existing_scenarios + new_auto

        enriched.append(task)

    return enriched
