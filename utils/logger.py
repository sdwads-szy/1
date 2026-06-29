# utils/logger.py
"""
统一日志模块 — 替换裸 except Exception: pass 的吞噬行为。

使用方式:
    from utils.logger import logger
    logger.warning("file not found", path="/tmp/x.json")
    logger.error("agent failed", exc_info=True)

日志级别: DEBUG / INFO / WARNING / ERROR
输出目标: stderr（默认）+ 可选文件
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

_PROJECT_ROOT = Path(__file__).parent.parent
_LOG_DIR = _PROJECT_ROOT / "Memory" / "logs"

# ── 单例 Logger ──

_logger: logging.Logger | None = None


def _build_logger() -> logging.Logger:
    """构建统一 logger 实例（延迟初始化）。"""
    lg = logging.getLogger("agent_system")
    lg.setLevel(logging.DEBUG)

    # 避免重复添加 handler
    if lg.handlers:
        return lg

    # stderr handler — WARNING 及以上
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(logging.Formatter(
        "[%(levelname)s] %(asctime)s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    ))
    lg.addHandler(stderr_handler)

    # 文件 handler — 所有级别（延迟创建目录）
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        today = datetime.now().strftime("%Y%m%d")
        file_handler = logging.FileHandler(
            str(_LOG_DIR / f"agent_{today}.log"),
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            "[%(levelname)s] %(asctime)s %(filename)s:%(lineno)d %(funcName)s | %(message)s"
        ))
        lg.addHandler(file_handler)
    except Exception:
        pass  # 文件日志不可用不影响主流程

    return lg


def get_logger() -> logging.Logger:
    global _logger
    if _logger is None:
        _logger = _build_logger()
    return _logger


# ── 便捷别名 ──

logger = get_logger()


def log_warning(msg: str, **kwargs):
    """记录警告（替代 except Exception: pass）。"""
    extra = " ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
    logger.warning(f"{msg} {extra}".strip())


def log_error(msg: str, exc_info: bool = False, **kwargs):
    """记录错误。exc_info=True 时附带调用栈。"""
    extra = " ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
    logger.error(f"{msg} {extra}".strip(), exc_info=exc_info)
