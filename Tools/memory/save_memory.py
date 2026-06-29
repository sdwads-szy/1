# Tools/memory/save_memory.py

import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

def save_memory(memory: Dict[str, Any], filepath: Path) -> bool:
    """
    将记忆字典保存为 JSON 文件。

    Args:
        memory: 要保存的记忆对象
        filepath: 保存路径（Path 对象或字符串）

    Returns:
        是否保存成功
    """
    try:
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(memory, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存记忆失败: {e}")
        return False


def save_round_memory(memory: Dict[str, Any], round_num: int, base_dir: Path) -> Path:
    """
    保存某一轮的记忆快照，命名为 chart{round_num}.json，
    并在记忆中的 chart_files 列表里记录文件名。

    Args:
        memory: 当前记忆对象（会被复制一份，不影响原对象）
        round_num: 轮次编号（0 为初始状态）
        base_dir: 保存目录（如 Memory/chat_sessions/）

    Returns:
        保存的文件路径
    """
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    filename = f"chart{round_num}.json"
    filepath = base_dir / filename

    # 创建快照（深拷贝）
    snapshot = {
        "round": round_num,
        "timestamp": datetime.now().isoformat(),
        "memory": memory.copy()
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    # 可选：在原始记忆中记录已保存的文件名
    if "chart_files" not in memory:
        memory["chart_files"] = []
    if filename not in memory["chart_files"]:
        memory["chart_files"].append(filename)

    print(f"[记忆保存] 已保存: {filepath}")
    return filepath