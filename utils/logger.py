# utils/logger.py
"""
统一日志模块 — 仅 stderr 输出，WARNING 及以上级别。

使用方式:
    from utils.logger import log_warning, log_error
    log_warning("file not found", path="/tmp/x.json")
    log_error("agent failed", exc_info=True)
"""

import sys
import logging

_logger: logging.Logger | None = None


def _build_logger() -> logging.Logger:
    lg = logging.getLogger("agent_system")
    lg.setLevel(logging.DEBUG)
    if lg.handlers:
        return lg

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(logging.Formatter(
        "[%(levelname)s] %(asctime)s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    ))
    lg.addHandler(stderr_handler)
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
