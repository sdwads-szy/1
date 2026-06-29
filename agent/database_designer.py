# agent/database_designer.py
"""数据库设计师 — 扩展 BaseDesigner，SQL schema 专项处理。"""
import sys, json
from pathlib import Path
from typing import List

current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir.parent))

from agent.base_designer import BaseDesigner


class DatabaseDesigner(BaseDesigner):
    """数据库设计师 — 覆写 _build_result 以检查 SQL 文件而非普通文件。"""

    def __init__(self):
        super().__init__(agent_type="db", description="数据库设计师")

    def _has_json_retry(self) -> bool:
        return False  # SQL 生成不需要 JSON 重试

    def _build_result(self, task, workspace_path, target_files, extra=None):
        tid = self._tid(task)
        safe_tid = tid.replace("/", "_").replace("\\", "_")
        sql_file = workspace_path / "database" / f"schema_{safe_tid}.sql"

        meta_file = workspace_path / ".meta" / f"task_{tid}.json"
        metadata = None
        if meta_file.exists():
            try:
                metadata = json.loads(meta_file.read_text("utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

        result = {"task_id": tid, "success": sql_file.exists(), "error": None, "metadata": metadata}
        if extra:
            result.update(extra)
        return result

    async def run(self, task, workspace_root="./project",
                  relevant_contracts=None, extra_instructions="") -> dict:
        """扩展 run：确保 database/ 目录存在。"""
        workspace_path = Path(workspace_root).resolve()
        tid = self._tid(task)
        safe_tid = tid.replace("/", "_").replace("\\", "_")
        sql_file = workspace_path / "database" / f"schema_{safe_tid}.sql"
        sql_file.parent.mkdir(parents=True, exist_ok=True)
        return await super().run(task, workspace_root=workspace_root,
                                 relevant_contracts=relevant_contracts,
                                 extra_instructions=extra_instructions)


_db_designer = DatabaseDesigner()


async def run_database_task(task: dict, workspace_root: str = "./project",
                            relevant_contracts: list = None,
                            extra_instructions: str = "") -> dict:
    return await _db_designer.run(task, workspace_root=workspace_root,
                                  relevant_contracts=relevant_contracts,
                                  extra_instructions=extra_instructions)
