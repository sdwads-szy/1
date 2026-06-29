# agent/frontend_designer.py
"""前端开发工程师 — 委托给 BaseDesigner 执行。"""
import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir.parent))

from agent.base_designer import BaseDesigner

_frontend = BaseDesigner(agent_type="frontend",
                         description="前端开发工程师（Vue 3 + Vite + Pinia）")


async def run_frontend_task(task: dict, workspace_root: str = "./project",
                            relevant_contracts: list = None,
                            extra_instructions: str = "") -> dict:
    return await _frontend.run(task, workspace_root=workspace_root,
                               relevant_contracts=relevant_contracts,
                               extra_instructions=extra_instructions)
