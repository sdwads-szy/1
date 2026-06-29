# Tools/memory/ban_memory.py
"""
共享 Ban 记忆工具 — 测试失败/源码失败记忆的读写与格式化。

跨模块使用:
  scheduler.py, test_runner.py, test_writer.py, source_fixer.py
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Union

# 项目根目录下的 Memory 子目录
from pathlib import Path as _Path
_PROJECT_ROOT = _Path(__file__).parent.parent.parent.resolve()
TEST_FAILURE_DIR = _PROJECT_ROOT / "Memory" / "test_failure"
SOURCE_FAILURE_DIR = _PROJECT_ROOT / "Memory" / "source_failure"


def get_bans(task_id: str, target: str = "test_failure") -> list:
    """读取全量 ban 记忆。返回 [{f, b}, ...] 列表。兼容旧格式。

    Args:
        task_id: 任务 ID
        target: "test_failure" 或 "source_failure"

    Returns:
        ban 字典列表，每项至少含 {"f": 指纹, "b": 禁止指令}
    """
    base = TEST_FAILURE_DIR if target == "test_failure" else SOURCE_FAILURE_DIR
    p = base / f"{task_id}.json"
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return []

    if isinstance(data, dict):
        bans = data.get("bans", [])
    elif isinstance(data, list):
        bans = data
    else:
        return []

    result = []
    for ban in bans:
        if isinstance(ban, str):
            result.append({"f": "", "b": ban})
        elif isinstance(ban, dict):
            result.append(ban)
    return result


def store_bans(task_id: str, target: str, new_bans: list) -> int:
    """存储多条 ban。过滤 fallback、空 ban、以及指纹完全相同的重复 ban。

    Args:
        task_id: 任务 ID
        target: "test_failure" 或 "source_failure"
        new_bans: 新 ban 列表

    Returns:
        实际新增的 ban 数量
    """
    if not new_bans:
        return 0

    base = TEST_FAILURE_DIR if target == "test_failure" else SOURCE_FAILURE_DIR
    p = base / f"{task_id}.json"
    existing = get_bans(task_id, target)
    existing_fps = {b.get("f", "") for b in existing if isinstance(b, dict)}
    added = 0

    for ban in new_bans:
        if not isinstance(ban, dict):
            continue
        fp = ban.get("f", "")
        if fp == "fallback":
            continue
        if not ban.get("b", "").strip():
            continue
        # 去重：同一指纹已存在则跳过
        if fp and fp in existing_fps:
            continue
        existing.append(ban)
        if fp:
            existing_fps.add(fp)
        added += 1

    if added > 0:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding='utf-8')

    return added


def format_bans_for_agent(bans: list) -> str:
    """格式化 bans 给 Agent prompt。完整展示 f + b。

    Args:
        bans: ban 字典列表，每项 {"f": 指纹, "b": 禁止指令}

    Returns:
        格式化的 markdown 文本，无 ban 时返回空字符串
    """
    if not bans:
        return ""

    lines = [
        "## 禁止清单（根据 fingerprint 判断哪些已修复、哪些仍需处理）",
        "格式：f = layer|actor|target|subtype | b = DON'T: 错误 | fix: 正确做法 | file",
        "layer: repair/infra/db/frontend_static/auth/db_api/peer_deps/api/backend_proc/navigation/logic/scenario/nfr",
        "actor: test_writer(A)/test_runner(B)/source_fixer(C)/test_runner(D)",
        "subtype: syntax/MOCK_GAP/MISSING_IMPORT/EXPORT_MISMATCH/PASSBY_MISMATCH/PATH_MISMATCH/COLUMN_MISMATCH..."
    ]
    files = set()

    for b in bans:
        if isinstance(b, dict):
            f_text = b.get("f", "")
            b_text = b.get("b", "")

            # 从 f 中提取文件简名（第二个字段）
            if f_text:
                parts = f_text.split("|")
                if len(parts) >= 3:
                    files.add(parts[1])

            # 兼容旧格式：如果 b 中含有 "| fix:"，则提取
            if "| fix:" in b_text:
                fix_part = b_text.split("| fix:", 1)[1].strip().split(",")[0].strip()
                if fix_part:
                    files.add(fix_part)

            if b_text:
                lines.append(f"- f: {f_text} | b: {b_text}")
        else:
            lines.append(f"- {str(b)}")

    if files:
        lines.append(f"- 需修复的文件: {', '.join(sorted(files))}")
    return "\n".join(lines)


def format_history_for_runner(bans: list) -> str:
    """将历史 ban 格式化为 B/D 的诊断参考（区别于 format_bans_for_agent）。

    Args:
        bans: ban 字典列表

    Returns:
        格式化的 markdown 文本，无 ban 时返回空字符串
    """
    if not bans:
        return ""
    lines = ["## 历史禁止指令（前几轮的诊断，请逐条判断当前错误是否命中）", ""]
    for i, ban in enumerate(bans):
        fp = ban.get("f", "")
        b_text = ban.get("b", "")
        fp_tag = f" [{fp}]" if fp else ""
        lines.append(f"{i+1}.{fp_tag} {b_text}")
    lines.append("")
    lines.append("判断标准：")
    lines.append("- 当前错误的 fingerprint 命中上述某条 → A/C 没修好，同一问题反复")
    lines.append("- 当前错误的 fingerprint 全新 → A/C 修出了新问题，需要新的 ban")
    return "\n".join(lines)


def load_memory(task_id: str, target: str = "source_failure") -> list:
    """读取全量记忆（别名，供 scoring 等模块使用）。

    与 get_bans 功能相同，命名兼容旧代码。
    """
    return get_bans(task_id, target)


def clear_bans(task_id: str, target: str = "source_failure") -> bool:
    """清除某个任务的 ban 记忆文件。

    Args:
        task_id: 任务 ID
        target: "test_failure" 或 "source_failure"

    Returns:
        True 如果文件被删除，False 如果文件不存在
    """
    base = TEST_FAILURE_DIR if target == "test_failure" else SOURCE_FAILURE_DIR
    p = base / f"{task_id}.json"
    if p.exists():
        try:
            p.unlink()
            return True
        except OSError as e:
            from utils.logger import log_warning
            log_warning("failed to clear ban file", file=str(p), error=str(e)[:100])
            pass
    return False
