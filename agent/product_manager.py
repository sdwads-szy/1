# agent/product_manager.py
"""
产品经理 Agent —— 单 Agent 主持需求讨论，自主管理记忆。

支持两种 action:
  discuss:      轻量上下文 (read_tree 只返回树结构)
  final_output: 完整上下文 (read_summary 返回全字段) → PRD

记忆结构:
  Memory/chat_sessions/{session_id}/
    full_summary.json  ← 模块维度累积 (s/p/f/b/d/t/i/c + parent)
    full_memory.json   ← 每轮结构化记录
"""

import os, sys
from pathlib import Path

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from picoagents import Agent, OpenAIChatCompletionClient
from dotenv import load_dotenv

from Tools.skill.load_skill import load_skill
from Tools.memory.load_memory import load_memory
from Tools.memory.save_memory import save_memory
from Tools.memory.merge_memory import append_round, merge_round

load_dotenv("./.env.example")
model_client = OpenAIChatCompletionClient(model=os.getenv("OPENAI_MODEL"))

MEM_DIR: Path = None


def _load_skill(path: str) -> str:
    full = (Path(__file__).parent.parent / path).resolve()
    if full.exists():
        return full.read_text("utf-8")
    return "你是产品经理，负责引导需求分析。"


# ═══════════════════════════════════════════════════════
# 工具: discuss 用轻量版, final_output 用完整版
# ═══════════════════════════════════════════════════════

def _lightweight_modules(modules: dict) -> dict:
    """discuss 轮次只需树结构, 去掉 f/b/d/t/i/c 省 token"""
    light = {}
    for name, m in modules.items():
        light[name] = {
            "s": m.get("s", ""),
            "p": m.get("p", ""),
        }
        if m.get("parent"):
            light[name]["parent"] = m["parent"]
    return light


async def read_tree() -> dict:
    """轻量树形视图 — discuss 每轮开始调用, 只返回 s/p/parent/pending/ui"""
    fs = load_memory("full_summary.json", workspace_root=str(MEM_DIR))
    return {
        "session_id": fs.get("session_id", ""),
        "original_requirement": fs.get("original_requirement", ""),
        "updated_round": fs.get("updated_round", 0),
        "ui": fs.get("ui", {}),
        "modules": _lightweight_modules(fs.get("modules", {})),
        "pending": fs.get("pending", []),
    }


async def read_summary() -> dict:
    """完整累积摘要 — final_output 调用, 含全部字段"""
    return load_memory("full_summary.json", workspace_root=str(MEM_DIR))


async def read_full() -> dict:
    """完整记忆 — final_output 按需查看历史轮次"""
    return load_memory("full_memory.json", workspace_root=str(MEM_DIR))


async def save_round(
    round_num: int,
    topic: str,
    summary: str,
    modules: dict,
    entities: list = None,
    ui: dict = None,
    pending: list = None,
) -> dict:
    """
    保存本轮并合并更新两个记忆文件。
    modules: {"模块名": {"s","p","parent?","f","b","d","t","i","c"}, ...}
    """
    round_data = {
        "topic": topic,
        "summary": summary,
        "modules": modules,
        "entities": entities or [],
        "ui": ui or {},
        "pending": pending or [],
    }

    fm = load_memory("full_memory.json", workspace_root=str(MEM_DIR))
    fs = load_memory("full_summary.json", workspace_root=str(MEM_DIR))

    fm = append_round(round_num, round_data, fm)
    fs = merge_round(round_num, round_data, fs)

    save_memory(fm, MEM_DIR / "full_memory.json")
    save_memory(fs, MEM_DIR / "full_summary.json")

    # 校验
    REQUIRED_TRUNK = ("s", "p", "f", "b", "d", "t", "i", "c")
    REQUIRED_BRANCH = ("s", "p", "parent", "f", "b", "d", "t", "i", "c")

    hints = []
    existing_modules = set(fs.get("modules", {}).keys())
    if not modules:
        hints.append("modules 为空")
    for name, m in modules.items():
        if m.get("parent"):
            missing = [k for k in REQUIRED_BRANCH if not m.get(k)]
            if missing:
                hints.append(f"枝干 [{name}] 缺字段: {missing}")
            if m["parent"] not in existing_modules and m["parent"] not in modules:
                hints.append(f"枝干 [{name}] 的 parent [{m['parent']}] 不存在")
        elif round_num == 1:
            missing = [k for k in REQUIRED_TRUNK if not m.get(k)]
            if missing:
                hints.append(f"主干 [{name}] 缺字段: {missing}")
        else:
            hints.append(f"模块 [{name}] 非主干非枝干, 缺 parent")
    if not entities:
        hints.append("entities 为空")
    return {"ok": True, "round": round_num, "hints": hints}


async def load_role_card(path: str) -> dict:
    try:
        content = load_skill(path)
        return {"ok": True, "content": content[:3000]}
    except Exception as e:
        return {"error": str(e)}


async def save_report(content: str) -> dict:
    """将 PRD 正文写入文件 — final_output 最后一步必须调用。
    使用 session 隔离的临时文件名，防止多会话并发冲突。"""
    # 从 MEM_DIR 提取 session_id 确保隔离
    sid = MEM_DIR.name if MEM_DIR else "unknown"
    out = Path(parent_dir) / "work" / "project" / "doc" / f"_prd_output_{sid}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, "utf-8")
    return {"ok": True, "path": str(out), "size": len(content)}


async def load_prd_template() -> dict:
    try:
        content = load_skill("skill/design/prd_template.md")
        return {"ok": True, "content": content}
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════
# Agent 入口
# ═══════════════════════════════════════════════════════

async def run_product_manager_agent(
    session_id: str,
    current_round: int,
    action: str,
    max_rounds: int = 7,
) -> dict:
    global MEM_DIR
    MEM_DIR = (Path(parent_dir) / "Memory" / "chat_sessions" / session_id).resolve()
    MEM_DIR.mkdir(parents=True, exist_ok=True)

    pm_skill = _load_skill("skill/design/product_manager.md")
    remaining = max_rounds - current_round

    if action == "discuss":
        if current_round == 1:
            round_type = f"R1/{max_rounds}: 定主干 (5-7个根模块, 每个 s+p+f+b+d+t+i+c 全维)"
        else:
            round_type = f"R{current_round}/{max_rounds}: 长枝干 (剩余 {remaining} 轮, 延申 1-3 新模块, R{max_rounds} 为 final_output)"

        mode = f"""## Round {current_round}/{max_rounds} | Action: discuss

{round_type}

工作目录: {MEM_DIR}

流程:
1. read_tree() → 轻量树形: modules(s/p/parent) + pending + ui
2. R1: 每个主干 f+b+d+t+i+c 全维深挖
   R2+: 广度优先, 选枝干最少的主干, 延申 1-3 新枝干
   ⚠ 还剩 {remaining} 轮讨论, 按剩余轮数规划节奏, 不要提前收尾
3. 按角色顺序发言(C→U→M→I→B→Q→D→A→S)
4. 输出结构化 JSON, 检查 hints
5. save_round({current_round}, ...) 保存"""

        tools = [read_tree, save_round, load_role_card, ]

    else:
        mode = f"""## Round {current_round}/{max_rounds} | Action: final_output

工作目录: {MEM_DIR}

流程:
1. read_summary() → pending 逐一决议 → save_round 写回
2. load_prd_template() + read_full() 如需细节
3. 按8章节模板生成 PRD 正文
4. save_report(prd_content) 将 PRD 写入文件 — 最后一步必须调用"""

        tools = [read_summary, read_full, save_round, save_report,
                 load_prd_template, ]

    prompt = f"""{mode}

严格按照 PM skill 执行。"""

    agent = Agent(
        name="pm",
        description="Product Manager - Requirement Discussion Host",
        instructions=pm_skill,
        model_client=model_client,
        tools=tools,
        max_iterations=50,
    )

    collected = []
    async for event in agent.run_stream(prompt, stream_tokens=False):
        collected.append(str(event))

    if action == "final_output":
        # 优先从 save_report 写入的文件读取
        report_file = Path(parent_dir) / "work" / "project" / "doc" / "_prd_output.md"
        if report_file.exists():
            text = report_file.read_text("utf-8").strip()
        else:
            # 降级: 从事件流中找 <start_requirement>...<end_requirement>
            parts = []
            for msg in collected:
                if isinstance(msg, str) and " | " in msg:
                    parts.append(msg.split(" | ", 1)[1].strip())
            full = "\n".join(parts)
            start = full.find("<start_requirement>")
            end = full.find("<end_requirement>")
            if start != -1 and end != -1:
                text = full[start + len("<start_requirement>"):end].strip()
            else:
                candidates = [p for p in parts if p and p[0] not in "{["]
                text = max(candidates, key=len) if candidates else ""
    else:
        text = ""
        for msg in reversed(collected):
            if isinstance(msg, str) and len(msg) > 50:
                if " | " in msg:
                    content = msg.split(" | ", 1)[1].strip()
                    if content[0] in "{[":
                        continue
                    text = content
                else:
                    text = msg
                break

    return {"success": True, "action": action, "raw_message": text}


async def main():
    from Tools.memory.save_memory import save_memory

    sid = "test"
    session_dir = Path("Memory/chat_sessions") / sid
    session_dir.mkdir(parents=True, exist_ok=True)
    init = {"session_id": sid, "original_requirement": "设计一个电商平台"}
    save_memory({**init, "rounds": []}, session_dir / "full_memory.json")
    save_memory({**init, "updated_round": 0, "ui": {},
                 "modules": {}, "entities": [], "pending": []},
                session_dir / "full_summary.json")

    result = await run_product_manager_agent(session_id=sid, current_round=1, action="discuss")
    print(result["raw_message"][:2000])


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
