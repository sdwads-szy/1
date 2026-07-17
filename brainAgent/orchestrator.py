# brainAgent/orchestrator.py
"""
需求分析编排器 —— PM 规划 + Python 执行 + SubAgent 自存。

轮次规划:
  R1 ........................ R{max_rounds-1}: discuss (PM 出 plan → 执行角色 → 合并摘要)
  R{max_rounds}: final_output (PM 读完整记忆 → 输出 PRD)
"""

import asyncio, json, sys
from pathlib import Path
from datetime import datetime

# Windows GBK encoding compatibility
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from agent.product_manager import (
    RoleSubAgent, merge_role_summaries,
)
from Tools.memory.save_memory import save_memory
from Tools.memory.load_memory import load_memory
from Tools.memory.merge_memory import append_round, merge_round
from utils.token import wrap_agent_stream
from dotenv import load_dotenv
import os

load_dotenv("./.env.example")

MEMORY_DIR = project_root / "Memory" / "chat_sessions"
REPORT_DIR = project_root / "work" / "project" / "doc"
UI_STYLES_DIR = project_root / "Memory" / "ui_styles"
SUBAGENT_LOG_DIR = project_root / "Memory" / "agent_logs" / "pm"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)
UI_STYLES_DIR.mkdir(parents=True, exist_ok=True)

# 依赖顺序: 每个 wave 内的角色可并行执行
ROLE_WAVES = {
    "first":  ["customer", "user", "innovator"],
    "second": ["manager", "business", "security", "designer_tokens"],  # designer_tokens = 全局令牌+组件
    "third":  ["data", "architect", "qa"],
    "fourth": ["designer_pages"],  # 每个页面的 designer
}


def init_session(session_id: str, requirement: str):
    session_dir = MEMORY_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    base = {"session_id": session_id, "original_requirement": requirement}
    save_memory({**base, "rounds": []}, session_dir / "full_memory.json")
    save_memory({**base, "updated_round": 0,
                 "modules": {}, "entities": [], "pending": []},
                session_dir / "full_summary.json")


def _build_role_context(round_num: int, max_rounds: int, requirement: str,
                        tree: dict, focus: str, round_type: str) -> dict:
    """为子Agent 构建标准输入上下文。"""
    return {
        "original_requirement": requirement,
        "round": int(round_num),
        "max_rounds": int(max_rounds),
        "action": "discuss",
        "tree": tree,
        "focus": focus,
        "round_type": round_type,
    }


# ═══════════════════════════════════════════════════════
# PM Planner 调用（注入上下文, PM 直接输出 JSON/markdown）
# ═══════════════════════════════════════════════════════

def _load_skill(path: str) -> str:
    full = (project_root / path).resolve()
    if full.exists():
        return full.read_text("utf-8")
    return ""


async def _run_pm_planner(
    session_id: str,
    current_round: int,
    max_rounds: int,
    action: str,
    requirement: str,
    full_summary: dict,
    full_memory: dict = None,
) -> dict:
    """调用 PM planner agent。不通过工具, 直接把上下文注入 prompt。

    Returns:
        discuss: {"topic": str, "plan": [...], "pending_add": [...]}
        final_output: {"prd": str}
    """
    from picoagents import Agent, OpenAIChatCompletionClient
    model_client = OpenAIChatCompletionClient(model=os.getenv("OPENAI_MODEL"))

    pm_skill = _load_skill("skill/design/product_manager.md")
    progress = current_round / max_rounds if max_rounds > 0 else 0
    remaining = max_rounds - current_round

    if action == "discuss":
        phase_hint = "早期(0-40%)" if progress <= 0.4 else ("中期(40-70%)" if progress <= 0.7 else "后期(70-100%)")

        if current_round == 1:
            round_hint = "R1: 固定主干。按 skill 中的 R1 流程, 确定 3-5 个主干模块。plan 中必须包含全部可调角色。"
        else:
            round_hint = f"R{current_round}: 指派 1-2 个枝干。广度优先。"

        prompt = f"""## Round {current_round}/{max_rounds} | discuss | {phase_hint}

{round_hint}
需求: {requirement}
进度: {progress:.0%}, 剩余 {remaining} 轮后进入 final_output.

## 当前摘要 (full_summary.json)
```json
{json.dumps(full_summary, indent=2, ensure_ascii=False)}
```

🛑 直接输出本轮 plan JSON。不要输出其他文字，不要用 markdown 包裹。"""

    else:  # final_output
        prd_template = _load_skill("skill/design/prd_template.md")
        memory_json = json.dumps(full_memory, indent=2, ensure_ascii=False)

        prompt = f"""## Round {current_round}/{max_rounds} | final_output

需求: {requirement}

## 完整轮次记录 (full_memory.json)
```json
{memory_json}
```

## PRD 模板
{prd_template}

🛑 严格按模板格式输出完整 PRD markdown。"""

    agent = Agent(
        name="pm_planner",
        description="Product Manager - Task Planner",
        instructions=pm_skill,
        model_client=model_client,
        tools=[],
        max_iterations=1,
    )

    log_dir = SUBAGENT_LOG_DIR / session_id
    log_dir.mkdir(parents=True, exist_ok=True)

    collected = []
    try:
        async for event in wrap_agent_stream(
            agent, prompt, "pm_planner",
            model=os.getenv("OPENAI_MODEL", "unknown"),
            task_id=f"pm_{session_id}",
            save_dir=str(log_dir), save_filename="pm_planner_token",
        ):
            collected.append(str(event))
    except Exception as e:
        return {"error": str(e), "raw": ""}

    full_output = "\n".join(collected)

    # 提取有效内容
    lines = []
    for line in full_output.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("TaskStartEvent", "TaskCompleteEvent",
                                 "ModelCallEvent", "ToolCallEvent",
                                 "AgentResponse", "UserMessage",
                                 "AssistantMessage", "ChatCompletion",
                                 "[INFO]", "[DEBUG]")):
            continue
        lines.append(line)
    clean = "\n".join(lines).strip()

    (log_dir / f"r{current_round}_{action}_pm_plan.md").write_text(clean, encoding="utf-8")

    if action == "discuss":
        plan = _parse_plan_json(clean)
        return {"plan": plan}
    else:
        # final_output: 提取 PM 真正的 PRD 输出 (跳过 prompt 回显)
        prd = _extract_final_response(clean)
        return {"prd": prd}


def _parse_plan_json(text: str) -> dict:
    """从 PM 输出中提取 plan JSON。"""
    import re

    # 找最后一个含 "plan" 键的 JSON 对象 (PM 真实输出)
    idx = text.rfind('"plan"')
    if idx >= 0:
        # 往前找最近的 {
        idx = text.rfind('{', 0, idx)

    if idx >= 0:
        # 从该位置开始找匹配的 }
        depth = 0
        end = idx
        for i in range(idx, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end > idx:
            try:
                return json.loads(text[idx:end])
            except (json.JSONDecodeError, TypeError):
                pass

    # 回退: 尝试直接解析
    try:
        return json.loads(text.strip())
    except (json.JSONDecodeError, TypeError):
        pass

    return {"topic": "parse error", "plan": [], "pending_add": [],
            "error": "无法解析 PM 输出", "raw": text[-500:]}


def _extract_final_response(clean: str) -> str:
    """从 final_output 的输出中提取 PM 真正的 PRD（去掉 prompt 回显和框架标记）。"""
    # 找最后一个 [pm_planner] 行，PRD 从那里开始
    lines = clean.split("\n")
    prd_start = -1
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith("[pm_planner]"):
            prd_start = i
            break

    if prd_start < 0:
        return clean  # 回退：返回全部

    # 去掉 [pm_planner] timestamp | 前缀
    prd_lines = []
    for line in lines[prd_start:]:
        if line.startswith("[pm_planner]"):
            # 去掉 "19:04:36 | " 部分
            parts = line.split(" | ", 1)
            if len(parts) > 1:
                prd_lines.append(parts[1])
        else:
            prd_lines.append(line)

    return "\n".join(prd_lines).strip()


# ═══════════════════════════════════════════════════════
# 角色执行
# ═══════════════════════════════════════════════════════

async def _run_role_agent(
    role: str,
    focus: str,
    session_id: str,
    round_num: int,
    max_rounds: int,
    requirement: str,
    tree: dict,
) -> dict:
    """运行单个角色子Agent, 返回 {role, output, summary_json}。"""
    round_type = f"R{round_num} 讨论" if round_num < max_rounds else "final_output"
    ctx = _build_role_context(round_num, max_rounds, requirement, tree, focus, round_type)

    # 注入已有模块名，让角色用统一名称（防止 summary JSON 各起各的名字）
    existing_modules = tree.get("modules", {})
    if existing_modules:
        module_list = ", ".join(existing_modules.keys())
        ctx["focus"] = focus + f"  [已知模块: {module_list}]"

    from picoagents import OpenAIChatCompletionClient
    model_client = OpenAIChatCompletionClient(model=os.getenv("OPENAI_MODEL"))

    sub = RoleSubAgent(role, model_client)
    save_dir = str(SUBAGENT_LOG_DIR / session_id / "subagents")
    result = await sub.speak(ctx, save_dir=save_dir)
    return result


async def _execute_plan(
    plan: list,
    session_id: str,
    round_num: int,
    max_rounds: int,
    requirement: str,
    tree: dict,
) -> list:
    """并行执行 plan 中的所有角色。按依赖关系分 wave:
    Wave 1: customer, user, innovator, designer(全局令牌+组件)
    Wave 2: manager, business, security, data, architect, qa
    Wave 3: designer(页面风格) — 每个模块独立
    """
    # 过滤无 role 的项
    plan = [item for item in plan if item.get("role")]
    results = []

    # Wave 1: customer, user, innovator（无依赖）
    wave1_roles = {"customer", "user", "innovator"}
    wave1 = [item for item in plan if item.get("role") in wave1_roles]
    # Wave 2: designer, data, architect, qa, security, business, manager（需要品牌/功能上下文）
    wave2_roles = {"designer", "data", "architect", "qa", "security", "business", "manager"}
    wave2 = [item for item in plan if item.get("role") in wave2_roles]

    async def run_item(item):
        role = item.get("role", "")
        focus = item.get("focus", "")
        print(f"  [{role}] {focus[:80]}...")
        result = await _run_role_agent(role, focus, session_id, round_num, max_rounds,
                                        requirement, tree)
        if result.get("error"):
            print(f"  [{role} error: {result['error'][:100]}]")
        else:
            print(f"  [{role}] 完成 ({len(result.get('output', ''))} chars)")
        return result

    if wave1:
        print(f"\n  -- Wave 1: {[r['role'] for r in wave1]} --")
        results.extend(await asyncio.gather(*[run_item(item) for item in wave1]))

    if wave2:
        print(f"\n  -- Wave 2: {[r['role'] for r in wave2]} --")
        results.extend(await asyncio.gather(*[run_item(item) for item in wave2]))

    return results


# ═══════════════════════════════════════════════════════
# 主编排流程
# ═══════════════════════════════════════════════════════

async def run_demand_analysis(session_id: str, requirement: str, max_rounds: int = 3):
    """
    max_rounds = 总轮次 (含 final_output)
    R1..R{max_rounds-1} = discuss
    R{max_rounds}       = final_output
    """
    from utils.token_tracker import record_stage
    record_stage("需求分析", phase="start")
    init_session(session_id, requirement)
    session_dir = MEMORY_DIR / session_id

    # ── 讨论轮次 ──
    for rnd in range(1, max_rounds):
        remaining = max_rounds - rnd
        print(f"\n{'='*40}\n Round {rnd}/{max_rounds} (discuss, 剩余 {remaining} 轮)\n{'='*40}")

        try:
            # 1. 加载当前摘要
            full_summary = load_memory("full_summary.json", workspace_root=str(session_dir))
            tree = {
                "session_id": full_summary.get("session_id", ""),
                "original_requirement": full_summary.get("original_requirement", ""),
                "updated_round": full_summary.get("updated_round", 0),
                "modules": {n: {"s": m.get("s",""), "p": m.get("p",""), "parent": m.get("parent")}
                           for n, m in full_summary.get("modules", {}).items() if m.get("parent")}
                | {n: {"s": m.get("s",""), "p": m.get("p","")}
                   for n, m in full_summary.get("modules", {}).items() if not m.get("parent")},
                "pending": full_summary.get("pending", []),
            }

            # 2. PM planner 出 plan
            print("\n[PM planner] 生成 plan...")
            pm_result = await _run_pm_planner(
                session_id, rnd, max_rounds, "discuss", requirement,
                full_summary=full_summary,
            )
            plan = pm_result.get("plan", {})
            if plan.get("error"):
                print(f"[PM planner error: {plan['error']}]")
                continue

            topic = plan.get("topic", f"Round {rnd}")
            summary_text = plan.get("summary", "")
            plan_items = plan.get("plan", [])
            pending_add = plan.get("pending_add", [])

            print(f"[PM planner] topic: {topic}")
            print(f"[PM planner] plan: {len(plan_items)} 个角色")
            for item in plan_items:
                print(f"  - {item.get('role', '?')}: {item.get('focus', '')[:100]}")

            if not plan_items:
                print("[orchestrator] PM returned empty plan, skipping round")
                continue

            # 3. 执行角色
            print("\n[orchestrator] 执行 plan...")
            results = await _execute_plan(plan_items, session_id, rnd, max_rounds, requirement, tree)

            # 4. 合并结果
            print("\n[orchestrator] 合并摘要...")
            merged = merge_role_summaries(results, full_summary.get("modules", {}))

            # 合并 pending
            all_pending = full_summary.get("pending", []) + pending_add

            # 更新 full_summary.json
            round_data = {
                "topic": topic,
                "summary": summary_text,
                "modules": merged["modules"],
                "entities": merged["entities"],
                "pending": all_pending,
            }
            fs = load_memory("full_summary.json", workspace_root=str(session_dir))
            fs = merge_round(rnd, round_data, fs)
            save_memory(fs, session_dir / "full_summary.json")

            # 追加到 full_memory.json
            fm = load_memory("full_memory.json", workspace_root=str(session_dir))
            fm = append_round(rnd, round_data, fm)
            save_memory(fm, session_dir / "full_memory.json")

            print(f"[orchestrator] Round {rnd} 完成 — {len(merged['modules'])} 模块, "
                  f"{len(merged['entities'])} 实体, {len(all_pending)} pending")

        except asyncio.TimeoutError:
            print(f"[orchestrator] Round {rnd} timeout")
        except Exception as e:
            import traceback
            print(f"[orchestrator] Round {rnd} error: {e}")
            traceback.print_exc()

    # ── 最终报告 ──
    print(f"\n{'='*40}\n Round {max_rounds}/{max_rounds} (final_output)\n{'='*40}")

    try:
        full_summary = load_memory("full_summary.json", workspace_root=str(session_dir))
        full_memory = load_memory("full_memory.json", workspace_root=str(session_dir))

        print("\n[PM planner] 生成 PRD...")
        pm_result = await _run_pm_planner(
            session_id, max_rounds, max_rounds, "final_output", requirement,
            full_summary=full_summary,
            full_memory=full_memory,
        )
        prd = pm_result.get("prd", "")

    except Exception as e:
        import traceback
        print(f"[PM final_output error: {e}]")
        traceback.print_exc()
        prd = ""

    # 保存 PRD
    if prd and len(prd) >= 200:
        report_name = f"requirement_report_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_path = REPORT_DIR / report_name
        report_path.write_text(prd, "utf-8")
        print(f"Report: {report_path}")
    else:
        # 降级生成
        fs = load_memory("full_summary.json", workspace_root=str(session_dir))
        modules = fs.get("modules", {})
        pending = fs.get("pending", [])
        prd = f"""# 需求分析报告 (降级生成)

## 模块清单
{chr(10).join(f'- {n}: {m.get("s","")}' for n, m in modules.items())}

## 待决策
{chr(10).join(f'- {p.get("q","")}: {p.get("d","")}' for p in pending)}

> PM Agent 未产出有效 PRD, 以上为自动降级生成。
"""
        report_name = f"requirement_report_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_path = REPORT_DIR / report_name
        report_path.write_text(prd, "utf-8")
        print(f"Report (降级): {report_path}")

    # 记录 Token 消耗
    try:
        balance = record_stage("需求分析", phase="end", extra={"session_id": session_id, "rounds": max_rounds})
        print(f"[token] 需求分析 消耗: {balance.get('cost', '?')} CNY (余额: {balance.get('total', '?')})")
    except Exception as e:
        print(f"[token] 记录失败: {e}")

    return {"session_id": session_id, "report_path": str(report_path) if prd else None}


async def main():
    result = await run_demand_analysis("project_session", "设计一个电商平台", max_rounds=3)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
