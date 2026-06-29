import json
import os
from pathlib import Path
from typing import Dict, Any

def load_memory(filename: str, workspace_root: str = "./Memory") -> Dict[str, Any]:
    """
    从指定工作区目录加载记忆文件（JSON格式）。

    Args:
        filename: 文件名，例如 "chat.json"
        workspace_root: 记忆文件所在目录，默认为 "./Memory"

    Returns:
        字典格式的记忆内容。如果文件不存在，返回默认的空记忆结构。

    默认记忆结构示例:
        {
            "session_id": "default",
            "original_requirement": "",
            "messages": [],
            "decisions": [],
            "pending_questions": [],
            "customer_status": "online",
            "user_status": "online"
        }
    """
    # 构建完整文件路径
    root = Path(workspace_root).expanduser().resolve()
    file_path = root / filename

    # 默认记忆结构
    default_memory = {
        "session_id": "default",
        "original_requirement": "",
        "messages": [],
        "decisions": [],
        "pending_questions": [],
        "customer_status": "online",
        "user_status": "online"
    }

    # 如果文件不存在，创建目录并返回默认结构
    if not file_path.exists():
        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        # 可选：写入一个默认的空记忆文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(default_memory, f, indent=2, ensure_ascii=False)
        return default_memory

    # 读取现有文件
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            memory = json.load(f)
        # 确保必要字段存在（兼容旧文件）
        for key, default_value in default_memory.items():
            if key not in memory:
                memory[key] = default_value
        return memory
    except (json.JSONDecodeError, IOError) as e:
        # 文件损坏时返回默认结构并打印警告
        print(f"Warning: Failed to load memory from {file_path}: {e}")
        return default_memory
