# brainAgent/orchestrator.py
"""
需求分析编排器。

轮次规划:
  R1 ........................ R{max_rounds-1}: discuss
  R{max_rounds}: final_output (收尾 + PRD)

记忆管理由 PM Agent 根据 skill 文档自主执行。
"""

import asyncio, json, sys
from pathlib import Path
from datetime import datetime

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from agent.product_manager import run_product_manager_agent
from Tools.memory.save_memory import save_memory
from Tools.memory.load_memory import load_memory

MEMORY_DIR = project_root / "Memory" / "chat_sessions"
REPORT_DIR = project_root / "work" / "project" / "doc"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def init_session(session_id: str, requirement: str):
    session_dir = MEMORY_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    base = {"session_id": session_id, "original_requirement": requirement}
    save_memory({**base, "rounds": []}, session_dir / "full_memory.json")
    save_memory({**base, "updated_round": 0, "ui": {},
                 "modules": {}, "entities": [], "pending": []},
                session_dir / "full_summary.json")


def _pm_timeouts():
    return 600, 900


async def run_demand_analysis(session_id: str, requirement: str, max_rounds: int = 3):
    """
    max_rounds = 总轮次 (含 final_output)
    R1..R{max_rounds-1} = discuss
    R{max_rounds}       = final_output
    """
    init_session(session_id, requirement)
    discuss_timeout, final_timeout = _pm_timeouts()
    # ── 讨论轮次 ──
    discuss_failures = 0
    for rnd in range(1, max_rounds):
        remaining = max_rounds - rnd   # 含 final_output 的剩余总轮数
        print(f"\n{'='*40}\n Round {rnd}/{max_rounds} (discuss, 剩余 {remaining} 轮)\n{'='*40}")

        try:
            result = await asyncio.wait_for(
                run_product_manager_agent(
                    session_id=session_id,
                    current_round=rnd,
                    max_rounds=max_rounds,
                    action="discuss",
                ), timeout=discuss_timeout,
            )
            text = result.get("raw_message", "")
            print(text[:3000])
            if text:
                discuss_failures = 0  # 成功则重置计数器
            else:
                discuss_failures += 1
        except asyncio.TimeoutError:
            print(f"[PM timeout after {discuss_timeout}s]")
            discuss_failures += 1
        except Exception as e:
            print(f"[PM error: {e}]")
            discuss_failures += 1

    # 如果所有讨论轮次都失败了，提前退出，避免基于空记忆生成无意义 PRD
    if max_rounds > 1 and discuss_failures >= (max_rounds - 1):
        print("[orchestrator] All discuss rounds failed, aborting before final_output")
        return {"session_id": session_id, "report_path": None,
                "error": "All discuss rounds failed — no meaningful memory to produce PRD"}

    # ── 最终报告 ──
    print(f"\n{'='*40}\n Round {max_rounds}/{max_rounds} (final_output)\n{'='*40}")

    prd_file = project_root / "work" / "project" / "doc" / f"_prd_output_{session_id}.md"
    # 清理旧文件
    if prd_file.exists():
        prd_file.unlink()

    try:
        await asyncio.wait_for(
            run_product_manager_agent(
                session_id=session_id,
                current_round=max_rounds,
                max_rounds=max_rounds,
                action="final_output",
            ), timeout=final_timeout,
        )
    except Exception as e:
        print(f"[PM final_output error: {e}]")

    # 从 save_report 写入的临时文件读取, 读完删掉
    if prd_file.exists():
        final = prd_file.read_text("utf-8").strip()
        prd_file.unlink()
    else:
        final = ""

    if not final or len(final) < 200:
        fs = load_memory("full_summary.json", workspace_root=str(MEMORY_DIR / session_id))
        modules = fs.get("modules", {})
        pending = fs.get("pending", [])
        final = f"""# 需求分析报告 (降级生成)

## 模块清单
{chr(10).join(f'- {n}: {m.get("s","")}' for n, m in modules.items())}

## 待决策
{chr(10).join(f'- {p.get("q","")}: {p.get("d","")}' for p in pending)}

> PM Agent 未产出有效 PRD, 以上为自动降级生成。
"""

    report_name = f"requirement_report_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_path = REPORT_DIR / report_name
    report_path.write_text(final, "utf-8")
    print(f"Report: {report_path}")

    return {"session_id": session_id, "report_path": str(report_path)}


async def main():
    result = await run_demand_analysis("project_session", "设计一个电商平台", max_rounds=3)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
