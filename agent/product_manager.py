# agent/product_manager.py
"""
产品经理 Agent —— 角色子Agent + 摘要合并。

RoleSubAgent: 接收 focus → 推理 → 自存回答 + 返回结构化摘要
merge_role_summaries: 合并各角色子Agent 的输出为统一模块树
"""

import asyncio, os, sys, json, re
from pathlib import Path

# Windows GBK 编码兼容
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from picoagents import Agent, OpenAIChatCompletionClient
from utils.token import wrap_agent_stream
from dotenv import load_dotenv

load_dotenv("./.env.example")

# ═══════════════════════════════════════════════════════
# 角色定义
# ═══════════════════════════════════════════════════════

ROLE_CARDS = {
    "customer":        "skill/design/customer.md",
    "user":            "skill/design/user.md",
    "manager":         "skill/design/manager.md",
    "innovator":       "skill/design/innovator.md",
    "business":        "skill/design/business_expert.md",
    "qa":              "skill/design/qa.md",
    "data":            "skill/design/data.md",
    "architect":       "skill/design/architect.md",
    "security":        "skill/design/security.md",
    "designer":        "skill/design/designer.md",
}

FIELD_OWNERS = {
    "s": "pm", "p": "customer", "parent": "pm",
    "f": "user", "b": "manager", "d": "data",
    "t": "qa", "i": "innovator", "c": "architect",
    "ui": "designer",
}


def _load_skill(path: str) -> str:
    full = (Path(__file__).parent.parent / path).resolve()
    if full.exists():
        return full.read_text("utf-8")
    return "你是产品经理，负责引导需求分析。"


# ═══════════════════════════════════════════════════════
# designer 写文件工具
# ═══════════════════════════════════════════════════════

async def _create_file_tool(path: str, content: str) -> dict:
    """创建单个文件。path 相对于项目根目录（如 Memory/ui_styles/_global.md）。"""
    full = (parent_dir / path).resolve()
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, "utf-8")
    return {"ok": True, "path": str(full), "size": len(content)}


async def _create_files_tool(files: list) -> dict:
    """批量创建文件。files: [{"path": "...", "content": "..."}, ...]。一次性写完所有文件。"""
    results = []
    for f in files:
        full = (parent_dir / f["path"]).resolve()
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(f["content"], "utf-8")
        results.append({"path": f["path"], "size": len(f["content"])})
    return {"ok": True, "count": len(results), "files": results}


# ═══════════════════════════════════════════════════════
# RoleSubAgent — 被 orchestrator 直接调用
# ═══════════════════════════════════════════════════════

class RoleSubAgent:
    """独立角色子Agent。接收 focus → 推理 → 自存回答 + 返回结构化结果。"""

    def __init__(self, role_name: str, model_client=None):
        self.role_name = role_name
        self.role_path = ROLE_CARDS.get(role_name, "")
        if not self.role_path:
            raise ValueError(f"未知角色: {role_name}, 可用: {list(ROLE_CARDS.keys())}")

        skill_file = (Path(__file__).parent.parent / self.role_path).resolve()
        if not skill_file.exists():
            raise FileNotFoundError(f"角色卡不存在: {skill_file}")
        self.skill_content = skill_file.read_text("utf-8")

        self.model_client = model_client or OpenAIChatCompletionClient(
            model=os.getenv("OPENAI_MODEL"))

    def _build_instructions(self, context: dict) -> str:
        parts = [self.skill_content]
        parts.append(f"## 当前: R{context.get('round', 1)} | 需求: {context.get('original_requirement', '')}")
        return "\n\n".join(parts)

    def _build_prompt(self, context: dict) -> str:
        focus = context.get("focus", "")
        rt = context.get("round_type", "")
        req = context.get('original_requirement', '')
        cr = int(context.get('round', 1))
        mr = int(context.get('max_rounds', 3))
        p = cr / mr if mr > 0 else 0
        phase = "早期保守" if p <= 0.4 else ("中期深化" if p <= 0.7 else "后期加强")
        tree = json.dumps(context.get('tree', {}), indent=2, ensure_ascii=False)[:2000]

        if rt == "final_output":
            return f"""## final_output — {self.role_name}
进度: R{cr}/{mr} ({p:.0%}, {phase})
模块树: {tree}
按角色卡格式审查, 确认是否有遗漏。"""

        return f"""## {self.role_name} — 任务
需求: {req} | R{cr}/{mr} ({p:.0%}, {phase})
{('模块树: ' + tree) if tree and tree != '{{}}' else ''}
### 任务: {focus}
按角色卡格式输出。只围绕任务发言。"""

    def _extract_content(self, full_output: str) -> str:
        import re
        lines = []
        for line in full_output.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith(("TaskStartEvent", "TaskCompleteEvent",
                                     "ModelCallEvent", "ToolCallEvent",
                                     "AgentResponse", "UserMessage",
                                     "AssistantMessage", "ChatCompletion",
                                     "[INFO]", "[DEBUG]", "[usage]")):
                continue
            if stripped.startswith("{") and ('"type"' in stripped or '"source"' in stripped):
                continue
            # 去掉 picoagents 角色前缀: [role_xxx] timestamp |
            stripped = re.sub(r'^\[role_\w+\]\s*\d+:\d+:\d+\s*\|\s*', '', stripped)
            lines.append(stripped)
        return "\n".join(lines).strip()

    def _try_parse_json(self, text: str) -> dict:
        m = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if m:
            try:
                return json.loads(m.group(1))
            except (json.JSONDecodeError, TypeError):
                pass
        return None

    async def speak(self, context: dict, save_dir: str = None) -> dict:
        """运行角色子Agent, 返回 {role, output, parsed, summary_json}。

        如果提供 save_dir, 自动保存完整回答到 save_dir/r{round}_{role}.md。
        """
        role_instructions = self._build_instructions(context)
        prompt = self._build_prompt(context)

        # designer 有写文件工具，其他角色纯推理
        tools = []
        max_iter = 1
        if self.role_name == "designer":
            tools = [_create_file_tool, _create_files_tool]
            max_iter = 3  # 1次想设计 + 1次批量写文件 + 1次摘要

        agent = Agent(
            name=f"role_{self.role_name}",
            description=f"需求分析角色: {self.role_name}",
            instructions=role_instructions,
            model_client=self.model_client,
            tools=tools,
            max_iterations=max_iter,
        )

        collected = []
        try:
            async for event in wrap_agent_stream(
                agent, prompt, f"pm_{self.role_name}",
                model=os.getenv("OPENAI_MODEL", "unknown"),
                task_id=self.role_name,
                save_dir=save_dir, save_filename=f"{self.role_name}_token",
            ):
                collected.append(str(event))
        except Exception as e:
            return {
                "role": self.role_name,
                "output": f"[{self.role_name} 发言失败: {e}]",
                "parsed": None,
                "summary_json": None,
                "error": str(e)[:200],
            }

        full_output = "\n".join(collected)
        output = self._extract_content(full_output)
        parsed = self._try_parse_json(output)
        summary_json = self._extract_summary_json(output)

        # 自存完整回答（同名角色多调用时自动编号: r1_designer.md, r1_designer_2.md, ...）
        if save_dir:
            save_path = Path(save_dir)
            save_path.mkdir(parents=True, exist_ok=True)
            rnd = context.get('round', 0)
            base = save_path / f"r{rnd}_{self.role_name}.md"
            if base.exists():
                # 找下一个可用编号
                for n in range(2, 100):
                    alt = save_path / f"r{rnd}_{self.role_name}_{n}.md"
                    if not alt.exists():
                        base = alt
                        break
            base.write_text(output, encoding="utf-8")

        return {
            "role": self.role_name,
            "output": output,
            "parsed": parsed,
            "summary_json": summary_json,
        }

    def _extract_summary_json(self, output: str) -> dict:
        """从角色输出中提取末尾的结构化摘要 JSON。"""
        # 找最后一个 ```json 代码块
        blocks = list(re.finditer(r'```json\s*(\{[^`]+\})\s*```', output, re.DOTALL))
        if not blocks:
            return None
        # 取最后一个（应该是摘要 JSON）
        try:
            return json.loads(blocks[-1].group(1))
        except (json.JSONDecodeError, TypeError):
            return None


# ═══════════════════════════════════════════════════════
# 角色输出合并（给 orchestrator 用）
# ═══════════════════════════════════════════════════════

def merge_role_summaries(role_results: list, existing_modules: dict = None) -> dict:
    """合并多个角色返回的 summary_json 为 modules + entities + pending。

    合并策略:
    - 每个角色的 summary_json.modules 按模块名合并
    - 字段归属: f→user, b→manager, d→data, t→qa, i→innovator, c→architect
    - 归属角色字段优先, 非归属角色仅在缺失时填充
    - entities 去重
    - pending 按 q 文本去重
    """
    modules = dict(existing_modules) if existing_modules else {}
    entities = []
    pending = []

    for result in role_results:
        summary = result.get("summary_json", {})
        if not summary or not isinstance(summary, dict):
            continue

        # modules
        role_modules = summary.get("modules", {})
        if isinstance(role_modules, dict):
            role = result.get("role", "")
            for mod_name, mod_fields in role_modules.items():
                if mod_name not in modules:
                    modules[mod_name] = {}
                if isinstance(mod_fields, dict):
                    for field, value in mod_fields.items():
                        owner = FIELD_OWNERS.get(field, "")
                        if owner == role or owner == "pm":
                            modules[mod_name][field] = value  # 归属角色直接覆盖
                        elif field not in modules[mod_name]:
                            modules[mod_name][field] = value  # 非归属角色仅在缺失时填充

        # entities
        role_entities = summary.get("entities", [])
        if isinstance(role_entities, list):
            entities.extend(role_entities)

        # pending
        role_pending = summary.get("pending", [])
        if isinstance(role_pending, list):
            pending.extend(role_pending)

    entities = sorted(set(entities))

    seen_q = set()
    unique_pending = []
    for p in pending:
        q = p.get("q", p.get("question", str(p)))
        if q not in seen_q:
            seen_q.add(q)
            unique_pending.append(p)

    return {
        "modules": modules,
        "entities": entities,
        "pending": unique_pending,
    }


# ═══════════════════════════════════════════════════════
# 测试入口（验证 RoleSubAgent 各项角色正常运作）
# ═══════════════════════════════════════════════════════

async def main():
    sid = "test_role_agent"
    ctx = {
        "original_requirement": "设计一个电商平台",
        "round": 1,
        "max_rounds": 3,
        "action": "discuss",
        "tree": {"modules": {}, "pending": []},
        "focus": "B2C电商平台。商业模式：自营+平台。一期范围：用户端核心交易链路",
        "round_type": "R1 讨论",
    }
    try:
        sub = RoleSubAgent("customer")
        result = await sub.speak(ctx)
        print(f"[{result['role']}] {len(result.get('output', ''))} chars")
        if result.get("summary_json"):
            print(json.dumps(result["summary_json"], indent=2, ensure_ascii=False)[:2000])
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
