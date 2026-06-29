import os
from pathlib import Path
from typing import Optional

def load_skill(skill_path: str, project_root: Optional[str] = None) -> str:
    """
    从指定路径加载技能提示词文件（支持 Markdown 或纯文本）。

    Args:
        skill_path: 相对于项目根目录的路径，或绝对路径。
                    例如 "skill/design/user.md"
        project_root: 项目根目录路径。如果为 None，则尝试自动推断。

    Returns:
        文件内容的字符串。

    Raises:
        FileNotFoundError: 如果文件不存在。
    """
    # 确定项目根目录
    if project_root is None:
        # 假设此文件位于 Tools/skill/load_skill.py，项目根目录是其上两级
        current_file = Path(__file__).resolve()           # .../Tools/skill/load_skill.py
        project_root = current_file.parent.parent.parent  # .../your_project/
    else:
        project_root = Path(project_root).expanduser().resolve()

    # 解析最终路径
    full_path = project_root / skill_path
    if not full_path.exists():
        # 备选：直接使用传入路径（可能是绝对路径或相对于当前工作目录）
        alt_path = Path(skill_path)
        if alt_path.exists():
            full_path = alt_path
        else:
            raise FileNotFoundError(f"Skill file not found: {skill_path} (tried {full_path})")

    # 读取文件
    with open(full_path, 'r', encoding='utf-8') as f:
        return f.read()


def load_skill_with_fallback(skill_path: str, fallback_text: str = "", project_root: Optional[str] = None) -> str:
    """
    加载技能文件，如果文件不存在则返回 fallback_text。
    """
    try:
        return load_skill(skill_path, project_root)
    except FileNotFoundError as e:
        print(f"Warning: {e}")
        return fallback_text