"""
Token 消耗追踪器 — 在每个阶段结束时查询 DeepSeek 余额并记录。

用法:
    from utils.token_tracker import record_stage

    # 阶段开始时打点（可选）
    tracker = record_stage("需求分析")  # 自动查询余额，保存到 Memory/token/需求分析.json

    # 阶段结束时再打点
    record_stage("需求分析")  # 覆盖写入同一文件

数据格式:
    Memory/token/
      需求分析.json
      架构任务生成.json
      源代码生成.json
      测试任务生成.json
      测试与修复.json

每个文件:
    {
      "stage": "需求分析",
      "timestamp": "2026-07-13T21:00:00",
      "balance": { "total": "110.00", "granted": "10.00", "topped_up": "100.00" },
      "is_available": true
    }
"""

import os
import json
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_TOKEN_DIR = _PROJECT_ROOT / "Memory" / "token"


def _load_env():
    """加载 .env.example 中的配置。"""
    env = {}
    env_path = _PROJECT_ROOT / ".env.example"
    if env_path.exists():
        for line in env_path.read_text("utf-8").split("\n"):
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def query_balance() -> dict:
    """查询 DeepSeek 账户余额。返回 {"total": str, "granted": str, "topped_up": str, "is_available": bool} 或错误信息。"""
    env = _load_env()
    api_key = env.get("OPENAI_API_KEY", "")
    balance_url = env.get("DEEPSEEK_BALANCE_URL", "https://api.deepseek.com/user/balance")

    if not api_key:
        return {"error": "OPENAI_API_KEY 未配置", "total": "0", "granted": "0", "topped_up": "0", "is_available": False}

    req = urllib.request.Request(
        balance_url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            is_available = data.get("is_available", False)
            infos = data.get("balance_infos", [])
            if infos:
                info = infos[0]
                return {
                    "total": info.get("total_balance", "0"),
                    "granted": info.get("granted_balance", "0"),
                    "topped_up": info.get("topped_up_balance", "0"),
                    "currency": info.get("currency", "CNY"),
                    "is_available": is_available,
                }
            return {"total": "0", "granted": "0", "topped_up": "0", "currency": "CNY", "is_available": is_available}
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "total": "0", "granted": "0", "topped_up": "0", "is_available": False}
    except Exception as e:
        return {"error": str(e)[:100], "total": "0", "granted": "0", "topped_up": "0", "is_available": False}


def record_stage(stage: str, phase: str = "start", extra: dict = None) -> dict:
    """记录某个阶段的 Token 消耗快照。

    Args:
        stage: 阶段名称（需求分析/架构任务生成/源代码生成/测试任务生成/测试与修复）
        phase: "start" 阶段开始 / "end" 阶段结束（结束时自动计算消耗）
        extra: 额外数据（如 task_count, duration_seconds 等）

    Returns:
        余额 dict，phase="end" 时额外含 cost 字段
    """
    _TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    balance = query_balance()

    record = {
        "stage": stage,
        "phase": phase,
        "timestamp": datetime.now().isoformat(),
        "balance": {
            "total": balance.get("total", "0"),
            "granted": balance.get("granted", "0"),
            "topped_up": balance.get("topped_up", "0"),
            "currency": balance.get("currency", "CNY"),
        },
        "is_available": balance.get("is_available", False),
    }
    if balance.get("error"):
        record["error"] = balance["error"]
    if extra:
        record["extra"] = extra

    file_path = _TOKEN_DIR / f"{stage}.json"
    history = []
    if file_path.exists():
        try:
            history = json.loads(file_path.read_text("utf-8"))
            if not isinstance(history, list):
                history = [history]
        except Exception:
            history = []

    # phase="end" 时找最近一次 "start" 记录，计算消耗
    if phase == "end" and history:
        start_record = None
        for h in reversed(history):
            if h.get("phase") == "start":
                start_record = h
                break
        if start_record:
            start_total = float(start_record["balance"]["total"])
            end_total = float(record["balance"]["total"])
            cost = start_total - end_total
            record["cost"] = f"{cost:.4f}"
            record["cost_start_total"] = start_record["balance"]["total"]
            record["cost_end_total"] = record["balance"]["total"]
            balance["cost"] = f"{cost:.4f}"

    history.append(record)
    file_path.write_text(json.dumps(history, indent=2, ensure_ascii=False), "utf-8")

    return balance


def get_stage_cost(stage: str) -> dict:
    """计算某个阶段的消耗（最后一个记录 - 第一个记录）。返回 {before, after, cost}。"""
    file_path = _TOKEN_DIR / f"{stage}.json"
    if not file_path.exists():
        return {"error": "无记录"}
    try:
        history = json.loads(file_path.read_text("utf-8"))
        if not history or not isinstance(history, list):
            return {"error": "记录为空"}
        first = history[0]
        last = history[-1]
        cost = float(last["balance"]["total"]) - float(first["balance"]["total"])
        return {
            "stage": stage,
            "before": first["balance"]["total"],
            "after": last["balance"]["total"],
            "cost": f"{cost:.4f}",
            "records": len(history),
        }
    except Exception as e:
        return {"error": str(e)[:100]}
