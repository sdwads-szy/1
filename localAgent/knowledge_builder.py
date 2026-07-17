# localAgent/knowledge_builder.py
"""
本地 Agent 调用器 —— 使用 picoagents Agent 框架 + 云端 OpenAI 兼容 API。
用于 refine（经验净化）和 merge（语义合并）任务。
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from picoagents import Agent, OpenAIChatCompletionClient

current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from Tools.skill.load_skill import load_skill
from utils.json_extractor import extract_json

load_dotenv('./.env.example')

# ---------- 云端模型配置 ----------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "deepseek-v4-pro")

if not OPENAI_API_KEY:
    print("[WARN] OPENAI_API_KEY not set. Please set it in .env")

model_client = OpenAIChatCompletionClient(
    model=OPENAI_MODEL,
    base_url=OPENAI_BASE_URL,
    api_key=OPENAI_API_KEY,
)

SKILL_PATH = {
    "refine": parent_dir / "skill" / "rag" / "build" / "refine.md",
    "merge": parent_dir / "skill" / "rag" / "build" / "merge.md",
    "generalize": parent_dir / "skill" / "rag" / "build" / "generalize.md",
}


async def run_knowledge_builder(role: str, task) -> dict:
    """
    使用 picoagents Agent 调用云端模型执行 refine 或 merge 任务。
    """
    skill_path = SKILL_PATH.get(role)
    if not skill_path:
        return {"error": f"未知角色: {role}"}

    try:
        skill = load_skill(skill_path)
    except Exception as e:
        return {"error": f"加载 Skill 失败: {e}"}

    if isinstance(task, (dict, list)):
        task_str = json.dumps(task, indent=2, ensure_ascii=False)
    else:
        task_str = str(task)

    instructions = f"""{skill}

用户的输入:
{task_str}"""

    agent = Agent(
        name=f"knowledge_builder_{role}",
        description=f"{role}",
        instructions=instructions,
        model_client=model_client,
        tools=[],
        max_iterations=2,
    )

    collected = ""
    try:
        async for event in agent.run_stream(stream_tokens=False):
            collected += str(event)
    except Exception as e:
        return {"error": f"Agent 执行失败: {e}", "raw": collected}
    parsed = extract_json(collected)
    if parsed is None:
        if "error" in collected.lower():
            return {"error": "Agent 返回错误", "raw": collected[:500]}
        return {"error": "未找到有效 JSON", "raw": collected[:500] + "..." if len(collected) > 500 else collected}

    # 对于 refine，如果返回了单个对象而不是数组，包装成数组
    if role == "refine" and isinstance(parsed, dict):
        parsed = [parsed]
    return parsed