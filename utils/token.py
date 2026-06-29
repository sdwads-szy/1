# utils/token.py — Agent Token Tracker (reusable module)
# ============================================================================
# 非侵入式 token 追踪工具。对 agent.run_stream() 的每个 event 统计 token 消耗，
# 完全不干扰 agent 自身过程（纯旁路观测）。
#
# 用法一：手动包装
#   from utils.token import TokenTracker
#   tracker = TokenTracker(agent.run_stream(task, verbose=True), model="...")
#   async for event in tracker.track():
#       ...  # 正常处理 event
#   tracker.save("token/category/task_id.json")  # 保存报告
#
# 用法二：一行包装（推荐）
#   from utils.token import wrap_agent_stream
#   async for event in wrap_agent_stream(agent, task, "category", model="..."):
#       ...  # 正常处理 event — 循环结束后自动保存到 token/category/
# ============================================================================

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

# 确保项目根在 path 中
_current_dir = Path(__file__).resolve().parent
_project_root = _current_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from picoagents.types import (
    AgentResponse,
    ChatCompletionChunk,
    ErrorEvent,
    FatalErrorEvent,
    ModelCallEvent,
    ModelResponseEvent,
    TaskCompleteEvent,
    TaskStartEvent,
    ToolApprovalEvent,
    ToolCallEvent,
    ToolCallResponseEvent,
    ToolValidationEvent,
)
from picoagents.messages import (
    AssistantMessage,
    ToolMessage,
    UserMessage,
)

# ═══════════════════════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════════════════════

MODEL_PRICING = {
    "deepseek-v4-pro": {"input": 0.025, "output": 6.0},  # ¥/1M tokens (DeepSeek 人民币定价)
}

# token 报告输出目录
TOKEN_DIR = _project_root / "token"

# 是否在 stderr 输出彩色追踪（生产环境可关）
VERBOSE_STDERR = os.getenv("TOKEN_TRACKER_VERBOSE", "0") == "1"


# ═══════════════════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════════════════

def estimate_tokens(text: str) -> int:
    """粗略估算: 中文 ~1.5 char/token, 英文 ~4 char/token"""
    if not text:
        return 0
    chinese = sum(1 for c in text if "一" <= c <= "鿿")
    other = len(text) - chinese
    return int(chinese / 1.5 + other / 4)


def estimate_cost(model: str, tokens_input: int, tokens_output: int) -> float:
    """估算费用 (USD)"""
    p = MODEL_PRICING.get(model, {"input": 2.0, "output": 8.0})
    return (tokens_input / 1_000_000) * p["input"] + (tokens_output / 1_000_000) * p["output"]


def fmt_tokens(n: int) -> str:
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


# ═══════════════════════════════════════════════════════════════════════════
# TokenTracker
# ═══════════════════════════════════════════════════════════════════════════

class TokenTracker:
    """非侵入式事件流包装器 — 旁路观测 token 消耗，原样传递事件"""

    def __init__(self, source: AsyncGenerator, model: str = "unknown",
                 category: str = "unknown", task_id: str = ""):
        self._source = source
        self._model = model
        self._category = category
        self._task_id = task_id
        self._event_idx = 0
        self._start_time = None
        self._end_time = None

        # ── 双轨累计 ──
        self.api_in = 0
        self.api_out = 0
        self.est_in = 0
        self.est_out = 0
        self.total_tool_calls = 0

        # ── 上一轮 API 累计值（用于计算每次调用的增量）──
        self._prev_api_in = 0
        self._prev_api_out = 0

        # ── 按 LLM 调用分组 ──
        self._call_idx = 0
        self._calls: list[dict] = []

        # ── 事件统计 ──
        self.event_counts: dict[str, int] = {}

        # ── 内容快照 (用于报告可读性) ──
        self._task_prompt = ""          # 用户任务原文
        self._final_response = ""       # Agent 最终回复
        self._tool_results: list[dict] = []  # 每次工具调用的结果摘要

    # ── stderr 输出（仅 VERBOSE_STDERR 时） ────────────────────────

    def _emit(self, text: str) -> None:
        if VERBOSE_STDERR:
            sys.stderr.write(text + "\n")
            sys.stderr.flush()

    def _banner(self, text: str, char: str = "-") -> None:
        if VERBOSE_STDERR:
            w = 80
            p = (w - len(text) - 2) // 2
            self._emit(f"\n\x1b[36m{char * p} {text} {char * (w - len(text) - 2 - p)}\x1b[0m")

    def _header(self) -> None:
        self._emit(f"\x1b[90m{'#':<4} {'call':<5} {'event':<22} token\x1b[0m")

    def _line(self, event_type: str, detail: str = "",
              api_in: int = 0, api_out: int = 0,
              est_in: int = 0, est_out: int = 0,
              extra: str = "", call_num: int = 0) -> None:
        if not VERBOSE_STDERR:
            return
        idx_s = f"#{self._event_idx:<3}"
        call_s = f"C{call_num:<4}" if call_num else " " * 5
        type_s = f"\x1b[1m{event_type:<22}\x1b[0m"
        parts = []
        if api_in or api_out:
            if api_in:
                parts.append(f"\x1b[1;33mAPI in:\x1b[0m {fmt_tokens(api_in):>6}")
            if api_out:
                parts.append(f"\x1b[1;32mAPI out:\x1b[0m {fmt_tokens(api_out):>6}")
            if api_in and api_out:
                parts.append(f"\x1b[1;37m=\x1b[0m {fmt_tokens(api_in + api_out):>6}")
        elif est_in or est_out:
            if est_in:
                parts.append(f"\x1b[90mest in:\x1b[0m {fmt_tokens(est_in):>6}")
            if est_out:
                parts.append(f"\x1b[90mest out:\x1b[0m {fmt_tokens(est_out):>6}")
        else:
            parts.append("\x1b[90m-\x1b[0m")
        token_str = "  ".join(parts)
        line = f"\x1b[2m{idx_s}\x1b[0m \x1b[90m{call_s}\x1b[0m {type_s} {token_str}"
        if detail:
            line += f"  \x1b[90m|\x1b[0m {detail}"
        if extra:
            line += f"  {extra}"
        self._emit(line)

    def _call_sep(self) -> None:
        if VERBOSE_STDERR:
            self._emit(f"\x1b[90m  {'-' * 75}\x1b[0m")

    # ── 累计 ────────────────────────────────────────────────────────

    def _add_api(self, ti: int, to: int) -> None:
        self.api_in += ti
        self.api_out += to

    def _add_est(self, ti: int, to: int) -> None:
        self.est_in += ti
        self.est_out += to

    def _count(self, name: str) -> None:
        self.event_counts[name] = self.event_counts.get(name, 0) + 1

    # ── 事件处理 ────────────────────────────────────────────────────

    def _on_user_message(self, msg: UserMessage) -> None:
        est = estimate_tokens(msg.content)
        self._task_prompt = msg.content  # 保存任务原文
        trunc = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        self._line("UserMessage", f'"{trunc}"', est_in=est)
        self._count("UserMessage"); self._add_est(est, 0)

    def _on_task_start(self, _event: TaskStartEvent) -> None:
        self._line("TaskStartEvent", "(diagnostic)")
        self._count("TaskStartEvent")

    def _on_model_call(self, event: ModelCallEvent) -> None:
        self._call_idx += 1
        total_est = sum(estimate_tokens(getattr(m, "content", "") or "") for m in event.input_messages)
        self._call_sep()
        self._line("ModelCallEvent", f"model={event.model}, {len(event.input_messages)} msgs",
                   est_in=total_est, call_num=self._call_idx,
                   extra=f"\x1b[1;36m<< LLM Call #{self._call_idx}\x1b[0m")
        self._count("ModelCallEvent"); self._add_est(total_est, 0)
        self._calls.append({"idx": self._call_idx, "api_in": None, "api_out": None,
                            "est_in": total_est, "est_out": 0, "tools": [], "has_response": False,
                            "content_preview": "", "tool_call_details": []})

    def _on_assistant_message(self, msg: AssistantMessage) -> None:
        usage = getattr(msg, "usage", None)
        cumulative_in = (getattr(usage, "tokens_input", 0) or 0) if usage else 0
        cumulative_out = (getattr(usage, "tokens_output", 0) or 0) if usage else 0

        # API usage 是累计值，需要计算本次调用的增量
        delta_in = cumulative_in - (self._prev_api_in or 0)
        delta_out = cumulative_out - (self._prev_api_out or 0)
        if delta_in < 0:
            delta_in = cumulative_in  # 重置（新一轮 agent 调用）
        if delta_out < 0:
            delta_out = cumulative_out

        if cumulative_in:
            self._prev_api_in = cumulative_in
        if cumulative_out:
            self._prev_api_out = cumulative_out

        trunc = msg.content[:80] + "..." if len(msg.content) > 80 else (msg.content or "")
        preview = f'"{trunc}"' if trunc else ""
        detail = f"{preview}" if preview else "(empty)"

        tag = "\x1b[1;33m[API]\x1b[0m" if (delta_in or delta_out) else "\x1b[90m[est]\x1b[0m"
        self._line("AssistantMessage", detail, api_in=delta_in, api_out=delta_out, extra=tag)
        self._count("AssistantMessage"); self._add_api(delta_in, delta_out)
        # 填到最后一个 call
        if self._calls:
            c = self._calls[-1]
            c["api_in"] = delta_in; c["api_out"] = delta_out; c["has_response"] = True
            if msg.content:
                c["content_preview"] = msg.content[:300] + ("..." if len(msg.content) > 300 else "")

    _tool_mr_count = 0
    def _on_model_response(self, event: ModelResponseEvent) -> None:
        est = estimate_tokens(event.response)
        status = "tool_calls" if event.has_tool_calls else "final_text"
        self._line("ModelResponseEvent", f"{status}, {len(event.response)} chars", est_out=est)
        self._count("ModelResponseEvent"); self._add_est(0, est)
        # 每个 ModelResponseEvent 就是一次 LLM 调用结束
        self._tool_mr_count += 1
        # 第1次是 ModelCallEvent 已经创建的 Call #1，后续才新建
        if self._tool_mr_count > 1:
            self._call_idx += 1
            self._calls.append({"idx": self._call_idx, "api_in": None, "api_out": None,
                                "est_in": 0, "est_out": 0, "tools": [], "has_response": False,
                                "content_preview": "", "tool_call_details": []})
        if self._calls:
            self._calls[-1]["est_out"] += est

    def _on_tool_call(self, event: ToolCallEvent) -> None:
        params_str = json.dumps(event.parameters, ensure_ascii=False)
        est = estimate_tokens(params_str)
        self._line("ToolCallEvent", f"{event.tool_name}(...)", est_in=est,
                   extra="\x1b[90m(context cost)\x1b[0m")
        self._count("ToolCallEvent"); self._add_est(est, 0)
        self.total_tool_calls += 1
        if self._calls:
            self._calls[-1]["tools"].append(event.tool_name)
            self._calls[-1]["est_in"] += est
        # 保存工具调用详情
        self._tool_results.append({
            "tool": event.tool_name,
            "params": {k: str(v)[:100] for k, v in event.parameters.items()},
            "result_preview": "",
            "success": None,
        })

    def _on_tool_call_response(self, event: ToolCallResponseEvent) -> None:
        est = estimate_tokens(str(event.result.result)) if event.result else 0
        self._line("ToolCallResponseEvent", f"call_id={event.call_id[:8]}...",
                   est_out=est, extra="\x1b[90m(see ToolMessage)\x1b[0m")
        self._count("ToolCallResponseEvent")  # 不累计 est — 与 ToolMessage 去重

    def _on_tool_message(self, msg: ToolMessage) -> None:
        est = estimate_tokens(msg.content)
        status = "\x1b[32m[OK]\x1b[0m" if msg.success else "\x1b[31m[FAIL]\x1b[0m"
        trunc = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        self._line("ToolMessage", f"{status} {msg.tool_name}: \"{trunc}\"",
                   est_out=est, extra="\x1b[90m(context cost)\x1b[0m")
        self._count("ToolMessage"); self._add_est(0, est)
        if self._calls:
            self._calls[-1]["est_out"] += est
        # 保存工具结果预览 (最近一次同名调用)
        if self._tool_results:
            self._tool_results[-1]["result_preview"] = msg.content[:300] + ("..." if len(msg.content) > 300 else "")
            self._tool_results[-1]["success"] = msg.success

    def _on_task_complete(self, _event: TaskCompleteEvent) -> None:
        self._line("TaskCompleteEvent", "(diagnostic)")
        self._count("TaskCompleteEvent")

    def _on_agent_response(self, response: AgentResponse) -> None:
        usage = response.usage

        # ── 从 context.messages 提取每次 LLM 调用的真实 per-call usage ──
        # AssistantMessage.usage 是每次调用的独立消耗（非累计），包括
        # 未被 yield 到流中的 tool_decision 消息。
        per_call_data: list[dict] = []  # [{tokens_in, tokens_out, has_text, content_preview, tools}, ...]
        if response.context and response.context.messages:
            for m in response.context.messages:
                if isinstance(m, AssistantMessage) and m.usage is not None:
                    ti = getattr(m.usage, "tokens_input", 0) or 0
                    to = getattr(m.usage, "tokens_output", 0) or 0
                    if ti > 0 or to > 0:
                        tool_names = [tc.tool_name for tc in m.tool_calls] if m.tool_calls else []
                        has_text = bool(m.content and m.content.strip())
                        content_preview = (m.content[:300] + ("..." if len(m.content) > 300 else "")) if has_text else ""
                        per_call_data.append({
                            "tokens_in": ti, "tokens_out": to,
                            "has_text": has_text, "content_preview": content_preview,
                            "tools": tool_names,
                        })

        # 将真实 per-call 数据填入 _calls（按顺序匹配）
        if per_call_data:
            # 重置将被覆盖的 call 的字段
            for i, c in enumerate(self._calls):
                if i < len(per_call_data):
                    c["api_in"] = None
                    c["api_out"] = None
                    c["has_response"] = False
                    c["content_preview"] = ""
                    c["tools"] = []
            self.api_in = 0
            self.api_out = 0

            for i, cd in enumerate(per_call_data):
                if i < len(self._calls):
                    c = self._calls[i]
                    c["api_in"] = cd["tokens_in"]
                    c["api_out"] = cd["tokens_out"]
                    c["has_response"] = cd["has_text"]
                    c["content_preview"] = cd["content_preview"] or None
                    c["tools"] = cd["tools"]
                    self._add_api(cd["tokens_in"], cd["tokens_out"])

        # ── 剩余的未匹配消耗 → 按估算比例分配到缺失的 call ──
        delta_in = max(0, usage.tokens_input - self.api_in)
        delta_out = max(0, usage.tokens_output - self.api_out)
        missing = [c for c in self._calls if c.get("api_in") is None]

        if missing and (delta_in > 0 or delta_out > 0):
            if len(missing) == 1:
                missing[0]["api_in"] = delta_in
                missing[0]["api_out"] = delta_out
            else:
                total_est_in = sum(c["est_in"] for c in missing) or 1
                total_est_out = sum(c["est_out"] for c in missing) or 1
                for c in missing:
                    ratio_in = c["est_in"] / total_est_in
                    ratio_out = c["est_out"] / total_est_out
                    c["api_in"] = max(1, int(delta_in * ratio_in))
                    c["api_out"] = max(1, int(delta_out * ratio_out))
                assigned_in = sum(c["api_in"] for c in missing)
                assigned_out = sum(c["api_out"] for c in missing)
                if delta_in > assigned_in:
                    missing[-1]["api_in"] += delta_in - assigned_in
                if delta_out > assigned_out:
                    missing[-1]["api_out"] += delta_out - assigned_out

            for c in missing:
                self._add_api(c["api_in"], c["api_out"])

        # ── 标注每个 call ──
        for c in self._calls:
            if c.get("tools"):
                c["label"] = f"Call #{c['idx']} (tool_decision)"
            else:
                c["label"] = f"Call #{c['idx']} (final_answer)"

        detail = f"finish={response.finish_reason}  calls={usage.llm_calls}"
        if per_call_data:
            detail += f" \x1b[90m(per-call: {len(per_call_data)} msgs from context)\x1b[0m"
        elif delta_in or delta_out:
            detail += f" \x1b[90m(fallback: {delta_in}/{delta_out} distributed)\x1b[0m"
        self._call_sep()
        self._line("\x1b[1;35mAgentResponse\x1b[0m", detail,
                   api_in=usage.tokens_input, api_out=usage.tokens_output,
                   extra="\x1b[90mAGGREGATE | tools={} dur={}ms\x1b[0m".format(usage.tool_calls, usage.duration_ms))
        self._count("AgentResponse")
        # 最终以 API 报告值为准
        self.api_in = usage.tokens_input
        self.api_out = usage.tokens_output

        if response.context and response.context.messages:
            for m in reversed(response.context.messages):
                if isinstance(m, AssistantMessage) and m.content and m.content.strip():
                    self._final_response = m.content[:500] + ("..." if len(m.content) > 500 else "")
                    break

    def _on_error(self, event: ErrorEvent) -> None:
        self._line(f"\x1b[31mErrorEvent\x1b[0m", f"{event.error_type}: {event.error_message[:50]}")
        self._count("ErrorEvent")

    def _on_fatal_error(self, event: FatalErrorEvent) -> None:
        self._line(f"\x1b[31mFatalErrorEvent\x1b[0m", f"{event.error_type}: {event.error_message[:50]}")
        self._count("FatalErrorEvent")

    def _on_tool_approval(self, _event: ToolApprovalEvent) -> None:
        self._line("ToolApprovalEvent", "[PAUSE] approval requested")
        self._count("ToolApprovalEvent")

    def _on_tool_validation(self, event: ToolValidationEvent) -> None:
        self._line("ToolValidationEvent", f"valid={event.is_valid}")
        self._count("ToolValidationEvent")

    def _on_stream_chunk(self, chunk: ChatCompletionChunk) -> None:
        if chunk.usage:
            cumulative_in = getattr(chunk.usage, "tokens_input", 0) or 0
            cumulative_out = getattr(chunk.usage, "tokens_output", 0) or 0

            # 计算增量
            delta_in = cumulative_in - (self._prev_api_in or 0)
            delta_out = cumulative_out - (self._prev_api_out or 0)
            if delta_in < 0:
                delta_in = cumulative_in
            if delta_out < 0:
                delta_out = cumulative_out

            if cumulative_in:
                self._prev_api_in = cumulative_in
            if cumulative_out:
                self._prev_api_out = cumulative_out

            self._line("StreamChunk(final)", "usage from stream", api_in=delta_in, api_out=delta_out)
            self._add_api(delta_in, delta_out)
        else:
            preview = chunk.content[:25] + "..." if len(chunk.content) > 25 else chunk.content
            self._line("StreamChunk", f'"{preview}"')
        self._count("StreamChunk")

    def _on_other(self, event) -> None:
        name = type(event).__name__
        self._line(f"\x1b[90m{name}\x1b[0m", str(event)[:50])
        self._count(name)

    # ── 主循环 ──────────────────────────────────────────────────────

    async def track(self) -> AsyncGenerator:
        """遍历事件流，追踪 token，原样 yield 每个事件"""
        self._start_time = time.time()
        self._banner(f"Token Tracker - {self._category}/{self._task_id} - model: {self._model}")
        self._header()

        async for event in self._source:
            self._event_idx += 1

            # 分发
            if isinstance(event, UserMessage):
                self._on_user_message(event)
            elif isinstance(event, TaskStartEvent):
                self._on_task_start(event)
            elif isinstance(event, ModelCallEvent):
                self._on_model_call(event)
            elif isinstance(event, AssistantMessage):
                self._on_assistant_message(event)
            elif isinstance(event, ModelResponseEvent):
                self._on_model_response(event)
            elif isinstance(event, ToolCallEvent):
                self._on_tool_call(event)
            elif isinstance(event, ToolCallResponseEvent):
                self._on_tool_call_response(event)
            elif isinstance(event, ToolMessage):
                self._on_tool_message(event)
            elif isinstance(event, ChatCompletionChunk):
                self._on_stream_chunk(event)
            elif isinstance(event, TaskCompleteEvent):
                self._on_task_complete(event)
            elif isinstance(event, AgentResponse):
                self._on_agent_response(event)
            elif isinstance(event, ErrorEvent):
                self._on_error(event)
            elif isinstance(event, FatalErrorEvent):
                self._on_fatal_error(event)
            elif isinstance(event, ToolApprovalEvent):
                self._on_tool_approval(event)
            elif isinstance(event, ToolValidationEvent):
                self._on_tool_validation(event)
            else:
                self._on_other(event)

            yield event  # 原样传递

        self._end_time = time.time()

    # ── 结构化输出 ──────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """返回结构化 token 报告（含内容截取，便于理解上下文）"""
        dur_ms = int((self._end_time - self._start_time) * 1000) if self._end_time else 0
        cost = estimate_cost(self._model, self.api_in, self.api_out)
        return {
            "category": self._category,
            "task_id": self._task_id,
            "model": self._model,
            "timestamp": datetime.now().isoformat(),
            # ── 任务上下文 ──
            "task": {
                "prompt": self._task_prompt[:500] + ("..." if len(self._task_prompt) > 500 else ""),
                "prompt_est_tokens": estimate_tokens(self._task_prompt),
            },
            # ── 最终回复 ──
            "final_response": self._final_response or "(no text response)",
            # ── 用量汇总 ──
            "summary": {
                "duration_ms": dur_ms,
                "total_events": self._event_idx,
                "tool_calls": self.total_tool_calls,
                "api_input_tokens": self.api_in,
                "api_output_tokens": self.api_out,
                "api_total_tokens": self.api_in + self.api_out,
                "est_input_tokens": self.est_in,
                "est_output_tokens": self.est_out,
                "est_total_tokens": self.est_in + self.est_out,
                "estimated_cost_cny": round(cost, 6),
            },
            # ── 每次 LLM 调用详情 ──
            "llm_calls": [
                {
                    "call_number": c["idx"],
                    "role": c.get("label", "unknown"),
                    "api_input_tokens": c["api_in"] or 0,
                    "api_output_tokens": c["api_out"] or 0,
                    "api_total_tokens": (c["api_in"] or 0) + (c["api_out"] or 0),
                    "est_input_tokens": c["est_in"],
                    "est_output_tokens": c["est_out"],
                    "tools_called": c["tools"],
                    "has_text_response": c["has_response"],
                    "content_preview": c.get("content_preview", "") or None,
                    "tool_call_requests": c.get("tool_call_details", []) or None,
                }
                for c in self._calls
            ],
            # ── 工具调用结果 ──
            "tool_executions": [
                {
                    "tool": tr["tool"],
                    "params": tr["params"],
                    "success": tr["success"],
                    "result_preview": tr["result_preview"] or None,
                }
                for tr in self._tool_results
            ] or None,
            # ── 事件统计 ──
            "event_counts": dict(self.event_counts),
        }

    def save(self, filepath: Path = None) -> Path:
        """保存 JSON 报告到 token/{category}/{filename}.json"""
        if filepath is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            fname = f"{ts}_{self._task_id}.json" if self._task_id else f"{ts}.json"
            filepath = TOKEN_DIR / self._category / fname
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        data = self.to_dict()
        filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
        self._emit(f"\n\x1b[90m[TokenTracker] report saved: {filepath}\x1b[0m")
        return filepath

    def print_summary(self) -> None:
        """打印汇总到 stderr"""
        dur = (self._end_time - self._start_time) if self._end_time else 0
        self._banner("SUMMARY", "=")
        self._emit(f"""
  \x1b[1;37m{'':<30} {'API (actual)':>20}  {'est (context)':>20}\x1b[0m
  {'-' * 30}  {'-' * 20}  {'-' * 20}
  \x1b[33m{'Input tokens':<30}\x1b[0m \x1b[1;33m{self.api_in:>20,}\x1b[0m  \x1b[90m{self.est_in:>20,}\x1b[0m
  \x1b[32m{'Output tokens':<30}\x1b[0m \x1b[1;32m{self.api_out:>20,}\x1b[0m  \x1b[90m{self.est_out:>20,}\x1b[0m
  \x1b[1;37m{'Total tokens':<30}\x1b[0m \x1b[1;37m{self.api_in + self.api_out:>20,}\x1b[0m  \x1b[90m{self.est_in + self.est_out:>20,}\x1b[0m
  {'-' * 30}  {'-' * 20}  {'-' * 20}
""")
        cost = estimate_cost(self._model, self.api_in, self.api_out)
        self._emit(f"  \x1b[35m{'Estimated cost (CNY)':<30}\x1b[0m \x1b[1;35m¥{cost:>19.6f}\x1b[0m")
        self._emit(f"  {'Total events':<30} {self._event_idx:>20}")
        self._emit(f"  {'Tool calls':<30} {self.total_tool_calls:>20}")
        self._emit(f"  {'Duration':<30} {dur:>19.1f}s")

        if self._calls:
            self._emit(f"\n  \x1b[1;37mPer-LLM-Call Breakdown\x1b[0m (Call #1=工具决策输出少, Call #2=最终回答输入含工具结果多)")
            for c in self._calls:
                tools = ", ".join(c["tools"]) if c["tools"] else "-"
                label = c.get("label", f"Call #{c['idx']}")
                api_in_val = c['api_in'] or 0
                api_out_val = c['api_out'] or 0
                self._emit(f"    {label:<55} tools={tools:<15} API in={fmt_tokens(api_in_val):>6} out={fmt_tokens(api_out_val):>6}")

        self._emit(f"\n  \x1b[90mNote: 'API' = actual LLM usage; 'est' = char/4 heuristic (context size, not billed).\x1b[0m")
        self._banner("END", "=")
        self._emit("")


# ═══════════════════════════════════════════════════════════════════════════
# 便捷包装函数
# ═══════════════════════════════════════════════════════════════════════════

async def wrap_agent_stream(
    agent,              # picoagents.Agent 实例
    task: str,          # 任务 prompt
    category: str,      # agent 分类（用于 token/ 子目录），如 "product_manager"
    model: str = "",    # 模型名
    task_id: str = "",  # 任务标识（用于文件名）
    save_report: bool = True,
    save_dir: str = "",      # 自定义保存目录（优先级高于 TOKEN_DIR）
    save_filename: str = "", # 自定义文件名（不含 .json 后缀）
) -> AsyncGenerator:
    """
    一行包装 agent.run_stream()，自动追踪 token 并保存报告。

    用法:
        async for event in wrap_agent_stream(agent, task, "architect", model="deepseek-v4-pro"):
            collected.append(str(event))
        # 循环结束后报告已自动保存

    不消耗任何额外 API token — TokenTracker 是纯旁路观测。
    """
    model_name = model or os.getenv("OPENAI_MODEL", "unknown")
    raw_stream = agent.run_stream(task, verbose=True, stream_tokens=False)
    tracker = TokenTracker(raw_stream, model=model_name, category=category, task_id=task_id)

    async for event in tracker.track():
        yield event

    if save_report:
        if save_dir and save_filename:
            path = Path(save_dir) / f"{save_filename}.json"
            tracker.save(filepath=path)
        else:
            tracker.save()
        if VERBOSE_STDERR:
            tracker.print_summary()

    # 将 tracker 挂到 generator 上，调用方可以访问
    wrap_agent_stream.last_tracker = tracker
