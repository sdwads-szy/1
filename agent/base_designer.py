# agent/base_designer.py
"""
设计器基类 — 消除 backend/frontend/database/infrastructure designer 的重复代码。

用法（子类只需定义差异化参数）:
    from agent.base_designer import BaseDesigner

    designer = BaseDesigner(
        agent_type="backend",
        agent_desc="后端开发工程师（Node.js + Express + MySQL）",
    )
    result = await designer.run(task, workspace_root, relevant_contracts, extra_instructions)
"""

import asyncio, os, json, sys
from pathlib import Path
from typing import Dict, Any, List, Optional

current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from dotenv import load_dotenv
from picoagents import Agent
from Tools.coding.create_files import create_files as _create_files
from Tools.coding.edit_lines import edit_batch as _edit_batch
from Tools.coding.syntax_check import check_syntax as _check_syntax
from utils.token import wrap_agent_stream
from utils.logger import log_warning, log_error
from utils.model_client import get_model_client
from agent.prompt_builder import build_system_prompt, build_user_prompt

load_dotenv("./.env.example")
model_client = get_model_client()

# ── Agent 描述映射 ──
_DESCRIPTIONS = {
    "infra":    "基础设施工程师",
    "db":       "数据库设计师",
    "backend":  "后端开发工程师（Node.js + Express + MySQL）",
    "frontend": "前端开发工程师（Vue 3 + Vite + Pinia）",
}

# ── 动态 max_iterations ──
def _calc_iterations(task: dict, agent_type: str) -> int:
    """根据任务复杂度动态计算 max_iterations。
    规则: base=3, 文件数>3则+1, 契约数>5则+1, 上限5。
    integration 基础值较高 (4)。
    """
    if agent_type == "integration":
        base = 4
    else:
        base = 3
    files = len(task.get("outputFiles") or task.get("files") or task.get("path") or [])
    contracts = len(task.get("usesContracts") or task.get("requiredContracts") or [])
    extra = 0
    if files > 3:
        extra += 1
    if contracts > 5:
        extra += 1
    return min(base + extra, 5)


class BaseDesigner:
    """通用设计器 — 封装 Agent 创建/流处理/重试/日志等公共逻辑。"""

    def __init__(self, agent_type: str, description: str = ""):
        self.agent_type = agent_type
        self.description = description or _DESCRIPTIONS.get(agent_type, f"{agent_type}工程师")

    # ── 钩子：子类可覆写 ──

    def _has_json_retry(self) -> bool:
        """是否需要 JSON 解析错误自动重试。db 类型不需要。"""
        return self.agent_type != "db"

    def _build_result(self, task: dict, workspace_path: Path,
                      target_files: List[str], extra: dict = None) -> dict:
        """构建返回值。优先使用 Agent 生成的 truth 文件，正则提取作为验证和回退。"""
        tid = self._tid(task)
        all_exist = all((workspace_path / f).exists() for f in target_files) if target_files else True

        # 1. 主数据源: Agent 在 create_files 中同时生成的真理文件
        # 从 workspace 内加载, 然后搬运到项目根 Memory/
        _copy_truth_to_root(workspace_path, tid)
        metadata = _load_agent_truth(parent_dir / "Memory", tid)

        # 2. 验证: 正则扫描实际文件, 与 Agent 声明的真理做交叉比对
        scanned = _extract_metadata_from_files(workspace_path, target_files, self.agent_type, tid)
        if metadata and scanned:
            warnings = _validate_truth_consistency(tid, metadata, scanned)
            if warnings:
                for w in warnings:
                    log_warning("truth mismatch", task=tid, detail=w)

        # 3. 回退: Agent 没生成 truth → 用正则提取
        if not metadata:
            metadata = scanned or _load_metadata(workspace_path, tid)

        result = {"task_id": tid, "success": all_exist, "error": None, "metadata": metadata}
        if extra:
            result.update(extra)
        return result

    def _get_target_files(self, task: dict) -> List[str]:
        """获取任务目标文件列表。"""
        return task.get("path") or task.get("outputFiles") or task.get("files") or []

    @staticmethod
    def _tid(task: dict) -> str:
        return task.get("taskId") or task.get("id", f"unknown_{task.get('type', 'task')}")

    # ── 主流程 ──

    async def run(self, task: dict, workspace_root: str = "./project",
                  relevant_contracts: list = None,
                  extra_instructions: str = "") -> dict:
        tid = self._tid(task)
        workspace_path = Path(workspace_root).resolve()
        workspace_path.mkdir(parents=True, exist_ok=True)
        abs_workspace = str(workspace_path)
        (workspace_path / ".meta").mkdir(exist_ok=True)
        # Truth 目录在项目根, 不在 workspace 内
        (parent_dir / "Memory" / "truths" / "engineer").mkdir(parents=True, exist_ok=True)

        target_files = self._get_target_files(task)
        safe_tid = tid.replace("/", "_").replace("\\", "_")

        # ── RAG 工具 ──
        from Tools.rag.search_rag import make_search_rag
        from Tools.rag.search_code import make_search_code
        search_rag = make_search_rag(tid, "code_generator")
        search_code = make_search_code(tid)

        # ── 工具列表 ──
        async def create_files(files, metadata=None):
            result = await _create_files(files, overwrite=True, workspace=abs_workspace, metadata=metadata)
            created = [f["path"] for f in files] if isinstance(files, list) else []
            if created:
                try:
                    result["syntax"] = await _check_syntax(created, workspace=abs_workspace)
                except Exception as e:
                    log_warning("syntax check failed", agent=self.agent_type, task=tid, error=str(e)[:100])
            return result

        async def edit_files(edits):
            return await _edit_batch(edits, workspace=abs_workspace)

        tools = [create_files, edit_files, search_rag, search_code]

        # ── 提示词 ──
        instructions = build_system_prompt(self.agent_type, abs_workspace, extra_instructions, task=task)
        user_prompt = build_user_prompt(task, relevant_contracts, self.agent_type)

        # ── 日志目录 ──
        agent_log_dir = parent_dir / "Memory" / "agent_logs" / "engineer" / tid
        agent_log_dir.mkdir(parents=True, exist_ok=True)

        # ── Agent 实例 ──
        max_iter = _calc_iterations(task, self.agent_type)
        agent = Agent(
            name=f"{self.agent_type}_worker_{tid}",
            description=self.description,
            instructions=instructions,
            model_client=model_client,
            tools=tools,
            max_iterations=max_iter,
        )

        # ── 流处理 ──
        collected_messages = await self._stream_agent(
            agent, user_prompt, tid, agent_log_dir, f"{self.agent_type}_token"
        )

        # ── JSON 转义/解析错误自动重试 ──
        if self._has_json_retry():
            full_output = "".join(collected_messages)
            json_errors = ("Extra data", "Expecting ',' delimiter", "char 0", "Invalid \\escape", "Invalid \\u")
            if any(e in full_output for e in json_errors):
                # 如果是转义错误，在 retry prompt 中明确告知 Agent 修复方向
                if "Invalid \\escape" in full_output or "Invalid \\u" in full_output:
                    extra_instructions = (extra_instructions or "") + \
                        "\n\n## [Retry] 上次因 JSON 转义错误失败。生成 create_files 前检查：代码中所有 \\ 必须写成 \\\\，正则如 /\\d+/g 必须写成 /\\\\d+/g。用 create_files 重新写入全部文件。"
                collected_messages = await self._retry_agent(
                    task, relevant_contracts, extra_instructions,
                    abs_workspace, tid, agent_log_dir, tools,
                )

        # ── 保存原始输出 ──
        (agent_log_dir / f"{self.agent_type}_raw.md").write_text(
            "\n".join(collected_messages), encoding="utf-8"
        )

        # ── 提取对外暴露接口（LLM 精读生成代码 → 结构化摘要）──
        interface = await self._extract_exposed_interface(
            task, workspace_path, target_files, abs_workspace, agent_log_dir, tid,
        )

        return self._build_result(task, workspace_path, target_files,
                                   extra={"interface": interface})

    # ── 内部方法 ──

    async def _stream_agent(self, agent, user_prompt, tid, log_dir, filename) -> List[str]:
        from picoagents.types import ErrorEvent, FatalErrorEvent
        collected = []
        try:
            async for event in wrap_agent_stream(
                agent, user_prompt, self.agent_type,
                model=model_client.model, task_id=tid,
                save_dir=str(log_dir), save_filename=filename,
            ):
                # 显式捕获 ErrorEvent 的错误信息（picoagents 的 str(event) 不包含详情）
                if isinstance(event, ErrorEvent):
                    collected.append(f"[ERROR] {event.error_type}: {event.error_message}")
                elif isinstance(event, FatalErrorEvent):
                    collected.append(f"[FATAL] {event.error_type}: {event.error_message}")
                else:
                    collected.append(str(event))
        except Exception as e:
            log_error("agent stream failed", exc_info=True,
                      agent=self.agent_type, task=tid, error=str(e)[:200])
        return collected

    async def _retry_agent(self, task, contracts, extra, workspace,
                           tid, log_dir, orig_tools) -> List[str]:
        """JSON 解析错误时的精简重试（只用 create_files 工具）。"""
        instructions = build_system_prompt(self.agent_type, workspace, extra_instructions=(extra or ""), task=task)
        user_prompt = build_user_prompt(task, contracts, self.agent_type)
        retry_agent = Agent(
            name=f"{self.agent_type}_worker_{tid}_retry",
            description=f"{self.description}（精简重试）",
            instructions=instructions,
            model_client=model_client,
            tools=[orig_tools[0]],  # 只用 create_files
            max_iterations=1,
        )
        collected = []
        try:
            async for event in wrap_agent_stream(
                retry_agent, user_prompt, self.agent_type,
                model=model_client.model, task_id=tid,
                save_dir=str(log_dir), save_filename=f"{self.agent_type}_token_retry",
            ):
                collected.append(str(event))
        except Exception as e:
            log_error("retry agent failed", agent=self.agent_type, task=tid, error=str(e)[:200])
        return collected


    # ── 对外接口提取 ──

    async def _extract_exposed_interface(self, task: dict, workspace_path: Path,
                                          target_files: list, abs_workspace: str,
                                          log_dir: Path, tid: str) -> dict:
        """让 LLM 综合契约 + 依赖关系 + 源码，推断对外暴露的接口。

        输入三要素：
          1. 契约（contracts）：本任务必须实现的接口承诺
          2. 依赖（dependencies）：谁依赖本任务 → 他们需要什么
          3. 源码：实际生成了什么
        LLM 综合三者：契约规定要暴露什么 + 依赖方实际需要什么 + 代码真正实现了什么
        → 准确提取 exposed_to_upper 和 exposed_to_peers
        """
        # 只读实际生成的文件
        existing_files = {}
        for tf in target_files:
            fp = workspace_path / tf
            if fp.exists() and fp.stat().st_size > 0:
                try:
                    existing_files[tf] = fp.read_text("utf-8")[:8000]
                except Exception:
                    pass
        if not existing_files:
            return {}

        # 构建上下文：契约 + 依赖 + 任务描述
        context_parts = []
        desc = task.get("description", "")
        if desc:
            context_parts.append(f"**任务描述**: {desc}")
        context_parts.append(f"**任务类型**: {self.agent_type}（在分层架构中的角色：{_LAYER_ROLES.get(self.agent_type, '')}）")

        # 契约上下文
        contracts = task.get("usesContracts") or task.get("requiredContracts") or []
        if contracts:
            context_parts.append(f"\n### 本任务的接口契约（必须暴露的内容）\n共 {len(contracts)} 个契约引用: {', '.join(contracts[:10])}")

        # 依赖上下文：谁依赖我？
        deps = task.get("dependencies", [])
        if deps:
            context_parts.append(f"\n### 本任务的依赖链\n本任务依赖 {len(deps)} 个上游: {', '.join(deps[:10])}")
        context_parts.append(f"\n### 需要暴露给下游的内容\n根据分层架构，{self.agent_type} 的上层是 {_UPPER_LAYER.get(self.agent_type, '未知')}，同层任务间可能通过 import 互相引用。\n请根据契约约定 + 代码实际实现，准确提取这两类接口。")

        context_block = "\n".join(context_parts)

        # 按 agent_type 选择提取模板
        prompt = _INTERFACE_EXTRACT_PROMPTS.get(
            self.agent_type, _INTERFACE_EXTRACT_PROMPTS["_default"]
        )

        files_block = "\n\n".join(
            f"### {path}\n```\n{content}\n```" for path, content in existing_files.items()
        )

        instructions = prompt.replace("{context_block}", context_block).replace("{files_block}", files_block)

        extract_agent = Agent(
            name=f"{self.agent_type}_interface_extractor_{tid}",
            description="接口提取器 — 只读不写",
            instructions=instructions,
            model_client=model_client,
            tools=[],
            max_iterations=1,
        )

        collected = ""
        try:
            async for event in extract_agent.run_stream(
                "提取对外暴露接口，输出 JSON。", stream_tokens=False,
            ):
                collected += str(event)
        except Exception as e:
            log_warning("interface extraction failed", agent=self.agent_type, task=tid, error=str(e)[:100])
            return {}

        # 解析 LLM 输出的 JSON
        from utils.json_extractor import extract_json
        interface = extract_json(collected)
        if isinstance(interface, dict):
            (log_dir / f"{self.agent_type}_interface.json").write_text(
                json.dumps(interface, indent=2, ensure_ascii=False), encoding="utf-8",
            )
            return interface
        return {}


# ── 分层架构元数据 ──

_LAYER_ROLES = {
    "infra": "最底层 — 提供中间件/工具函数/配置/env 变量",
    "db": "数据层 — 提供表结构/字段/约束，上层 frontend+backend 据此编码",
    "frontend": "展示层 — 先生成，产出前端真理 (API调用+路由+store)，供后端对齐",
    "backend": "业务层 — 接收前端真理+数据库模型，实现前后端连接器",
}

_UPPER_LAYER = {
    "infra": "db / frontend / backend / integration",
    "db": "frontend / backend / integration",
    "frontend": "backend / integration",
    "backend": "integration",
}


# ── 接口提取提示词模板 ──

_INTERFACE_EXTRACT_PROMPTS = {
    "infra": """你是接口提取器。请综合以下上下文，提取对外暴露接口。

{context_block}

请按两层分类提取，输出严格 JSON：
{{
  "exposed_to_upper": {{
    "_comment": "上层（backend/frontend/integration）需要知道的所有接口",
    "middleware": [{{"name": "authenticate", "signature": "(req, res, next) => ..."}}],
    "utils_exports": [{{"file": "utils/response.js", "exports": ["success(res, data)", "error(res, msg)"]}}],
    "config_exports": [{{"file": "config/db.js", "exports": ["pool", "testConnection"]}}],
    "env_vars_used": ["DB_HOST", "JWT_SECRET"]
  }},
  "exposed_to_peers": {{
    "_comment": "同层 infra 任务之间的 import 依赖（A 文件的导出被 B 文件 require）",
    "internal_exports": [{{"file": "...", "exports": ["..."], "imported_by": ["..."]}}]
  }}
}}

代码：
{files_block}""",

    "db": """你是接口提取器。请综合以下上下文，提取对外暴露接口。

{context_block}

请按两层分类提取，输出严格 JSON：

{{
  "exposed_to_upper": {{
    "_comment": "上层（backend）需要知道的所有表结构，字段不可省略",
    "tables": [
      {{
        "name": "users",
        "fields": [
          {{"name": "id", "type": "INT", "constraints": "PRIMARY KEY AUTO_INCREMENT"}},
          {{"name": "username", "type": "VARCHAR(50)", "constraints": "NOT NULL UNIQUE"}}
        ],
        "indexes": [{{"name": "idx_username", "columns": ["username"]}}],
        "foreignKeys": [{{"columns": ["user_id"], "references": "users(id)"}}]
      }}
    ],
    "seed_data_summary": "admin(admin/admin123)"
  }},
  "exposed_to_peers": {{
    "_comment": "db 任务通常独立，无同层依赖。如有 seed 数据跨表引用则填写",
    "cross_table_refs": []
  }}
}}

代码：
{files_block}""",

    "backend": """你是接口提取器。请综合以下上下文，提取对外暴露接口。

{context_block}

请按两层分类提取，输出严格 JSON：

{{
  "exposed_to_upper": {{
    "_comment": "上层（frontend/integration）需要调用的 API 路由",
    "routes": [
      {{
        "file": "routes/order.js",
        "basePath": "/api/orders",
        "handlers": [
          {{"method": "POST", "path": "/", "handler": "createOrder", "middleware": ["authenticate"], "request": "{{items:[...]}}", "response": "{{orderId, totalPrice}}"}}
        ]
      }}
    ]
  }},
  "exposed_to_peers": {{
    "_comment": "同层 backend 任务之间的调用（controller → service）",
    "services": [
      {{
        "file": "services/orderService.js",
        "functions": [
          {{"name": "createOrder", "params": ["userId", "items"], "returns": "{{orderId, totalPrice}}"}}
        ]
      }}
    ],
    "cross_task_imports": [{{"file": "...", "imports": ["require('../services/orderService')"]}}]
  }}
}}

代码：
{files_block}""",

    "frontend": """你是接口提取器。请综合以下上下文，提取对外暴露接口。

{context_block}

请按两层分类提取，输出严格 JSON：

{{
  "exposed_to_upper": {{
    "_comment": "上层（integration）需要知道的路由和页面",
    "pages": [{{"file": "src/pages/OrderList.vue", "route": "/orders"}}],
    "router": [{{"path": "/orders", "name": "OrderList", "component": "OrderList.vue"}}],
    "api_calls": [{{"from": "src/api/order.js", "endpoints": ["POST /api/orders"]}}]
  }},
  "exposed_to_peers": {{
    "_comment": "同层 frontend 任务之间的引用（页面 → store，组件 → 组件）",
    "stores": [
      {{
        "file": "src/stores/order.js",
        "state": ["orders"],
        "actions": ["fetchOrders()"],
        "getters": ["orderById(id)"],
        "imported_by": ["src/pages/OrderList.vue"]
      }}
    ]
  }}
}}

代码：
{files_block}""",

    "_default": """你是接口提取器。请综合以下上下文，提取对外暴露接口。

{context_block}

请按两层分类提取，输出严格 JSON：
{{
  "exposed_to_upper": {{ ... 上层需要调用的接口 ... }},
  "exposed_to_peers": {{ ... 同层依赖方需要 import 的导出 ... }}
}}

代码：
{files_block}""",
}


# ── 辅助函数 ──

def _load_metadata(workspace_path: Path, tid: str) -> dict:
    meta_file = workspace_path / ".meta" / f"task_{tid}.json"
    if meta_file.exists():
        try:
            return json.loads(meta_file.read_text("utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            log_warning("failed to load metadata", task=tid, error=str(e)[:100])
    return None


def _extract_metadata_from_files(workspace_path: Path, target_files: List[str],
                                  agent_type: str, tid: str) -> dict:
    """从生成的文件内容中自动提取元数据，不依赖 Agent 手动传递。

    提取规则:
      - backend: 扫描 route 文件的 // @mount 注释 → routes[]
      - frontend: 扫描 .vue 文件 → pages[]，扫描 router 文件 → router_config
      - infra: 扫描中间件/工具文件 → middleware[] + utils[] + config_exports[]
      - db: 扫描 SQL 文件 → tables[]
    """
    import re
    ws = workspace_path
    metadata = {"taskId": tid, "type": agent_type}

    if agent_type == "backend":
        routes = []
        for tf in target_files:
            fp = ws / tf
            if not fp.exists() or "route" not in tf.lower():
                continue
            content = fp.read_text("utf-8")
            mount_match = re.search(r'@mount\s+(/\S+)', content)
            base_path = mount_match.group(1) if mount_match else ""
            methods = []
            for m in re.finditer(r'router\.(get|post|put|delete|patch)\s*\(\s*[\'\"]([^\'\"]+)', content):
                methods.append({"method": m.group(1).upper(), "path": m.group(2)})
            if base_path or methods:
                routes.append({
                    "routeFile": tf,
                    "basePath": base_path,
                    "methods": methods,
                })
        if routes:
            metadata["routes"] = routes

        # 扫描 services/ 目录，提取导出的函数签名
        services = []
        for tf in target_files:
            fp = ws / tf
            if not fp.exists() or "service" not in tf.lower():
                continue
            content = fp.read_text("utf-8", errors="replace")
            # 提取 async function / function 声明
            fns = []
            for m in re.finditer(r'(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)', content):
                fns.append({"name": m.group(1), "params": [p.strip() for p in m.group(2).split(",") if p.strip()]})
            if fns:
                services.append({"file": tf, "functions": fns})
        if services:
            metadata["services"] = services

    elif agent_type == "frontend":
        pages = []
        for tf in target_files:
            fp = ws / tf
            if not fp.exists() or not tf.endswith(".vue"):
                continue
            content = fp.read_text("utf-8", errors="replace")[:2000]
            # 提取组件名（从文件名推导）
            name = Path(tf).stem
            # 尝试提取 route meta
            route_meta = {}
            if "requiresAdmin" in content:
                route_meta["requiresAdmin"] = True
            pages.append({
                "component": name,
                "file": tf,
                "meta": route_meta if route_meta else None,
            })
        if pages:
            metadata["pages"] = pages

        # 扫描前端 API 模块，提取实际调用的 URL 和 method
        api_calls = []
        for tf in target_files:
            fp = ws / tf
            if not fp.exists() or "api" not in tf.lower():
                continue
            if not tf.endswith(".js"):
                continue
            content = fp.read_text("utf-8", errors="replace")
            endpoints = []
            for m in re.finditer(r"""request\s*\(\s*\{\s*url:\s*['\"]([^'\"]+)['\"]\s*,\s*method:\s*['\"]([^'\"]+)['\"]""", content):
                endpoints.append(f"{m.group(2).upper()} {m.group(1)}")
            if endpoints:
                api_calls.append({"from": tf, "endpoints": endpoints})
        if api_calls:
            metadata["api_calls"] = api_calls

        # 检查是否生成了 router 文件
        router_file = ws / "src" / "router" / "index.js"
        if router_file.exists():
            content = router_file.read_text("utf-8", errors="replace")
            route_names = re.findall(r"name:\s*['\"]([^'\"]+)", content)
            route_paths = re.findall(r"path:\s*['\"]([^'\"]+)", content)
            # 提取所有 import 路径，用于后续存在性检查
            import_paths = re.findall(r"""from\s+['\"](@/[^'\"]+)['\"]""", content)
            lazy_imports = re.findall(r"""import\s*\(\s*['\"](@/[^'\"]+)['\"]\s*\)""", content)
            if route_names or route_paths:
                metadata["router"] = {
                    "names": route_names,
                    "paths": route_paths,
                    "imports": import_paths + lazy_imports,
                }

    elif agent_type == "infra":
        middleware_list = []
        utils_list = []
        config_exports = []
        for tf in target_files:
            fp = ws / tf
            if not fp.exists():
                continue
            content = fp.read_text("utf-8", errors="replace")
            # 三种导出模式: module.exports.xxx =, module.exports = { ... }, module.exports = singleVar
            exports = re.findall(r'module\.exports\.(\w+)\s*=', content)
            if not exports:
                obj_match = re.search(r'module\.exports\s*=\s*\{([^}]+)\}', content)
                if obj_match:
                    exports = re.findall(r'(\w+)', obj_match.group(1))
            if not exports:
                single_match = re.search(r'module\.exports\s*=\s*(\w+)\s*;?\s*$', content, re.MULTILINE)
                if single_match:
                    exports = [single_match.group(1)]

            if "middleware" in tf.lower():
                middleware_list.append({"file": tf, "exports": exports})
            elif "utils" in tf.lower():
                utils_list.append({"file": tf, "exports": exports})
            elif "config" in tf.lower():
                config_exports.append({"file": tf, "exports": exports})

        if middleware_list:
            metadata["middleware"] = middleware_list
        if utils_list:
            metadata["utils"] = utils_list
        if config_exports:
            metadata["config"] = config_exports

    elif agent_type == "db":
        tables = []
        for tf in target_files:
            fp = ws / tf
            if not fp.exists():
                continue
            content = fp.read_text("utf-8", errors="replace")
            for m in re.finditer(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?', content, re.IGNORECASE):
                tables.append(m.group(1))
        if tables:
            metadata["tables"] = tables

    # 持久化到 .meta/ 供其他进程读取
    if len(metadata) > 2:  # 除了 taskId 和 type 之外还有内容
        meta_dir = ws / ".meta"
        meta_dir.mkdir(parents=True, exist_ok=True)
        (meta_dir / f"task_{tid}.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False), "utf-8")

    return metadata if len(metadata) > 2 else None


def _copy_truth_to_root(workspace_path: Path, tid: str):
    """将 workspace 内的 truth 文件搬运到项目根 Memory/，搬运后删除源文件避免双写。"""
    src = workspace_path / "Memory" / "truths" / "engineer" / f"{tid}.json"
    if not src.exists():
        return
    import shutil
    dst = Path(__file__).parent.parent / "Memory" / "truths" / "engineer" / f"{tid}.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(dst))
    # 搬运后删除 workspace 内的源文件，避免 work/project/Memory/ 膨胀
    try:
        src.unlink()
    except OSError:
        pass


def _load_agent_truth(memory_root: Path, tid: str) -> dict:
    """读取 Agent 在 create_files 中同时生成的真理文件（主数据源）。

    返回归一化结构，保留 type 字段并将 exposed_to_upper 的 routes/pages
    提升到顶层，方便上游元数据收集。
    """
    truth_file = memory_root / "truths" / "engineer" / f"{tid}.json"
    if truth_file.exists():
        try:
            data = json.loads(truth_file.read_text("utf-8"))
            if not isinstance(data, dict):
                return None
            exposed = data.get("exposed", {})
            if not isinstance(exposed, dict):
                return None
            # 归一化：保留 type + 提升 exposed_to_upper 的 routes/pages 到顶层
            result = {
                "type": data.get("type", ""),
                "taskId": data.get("task_id", tid),
            }
            upper = exposed.get("exposed_to_upper", {})
            if isinstance(upper, dict):
                # 提升常见字段到顶层
                for key in ("routes", "pages", "middleware", "tables",
                           "utils_exports", "config_exports", "api_calls", "router"):
                    if key in upper:
                        result[key] = upper[key]
            # 也保留完整的 exposed 供下游使用
            result["exposed"] = exposed
            return result
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _validate_truth_consistency(tid: str, agent_truth: dict, scanned: dict) -> list:
    """交叉比对 Agent 声明的真理 vs 正则从实际文件中扫描的结果。返回不一致项列表。"""
    warnings = []

    # 检查导出数量: Agent 声称的导出 vs 实际扫描到的
    for section in ["middleware", "utils_exports", "config_exports", "tables", "routes", "services"]:
        declared = _count_declared(agent_truth, section)
        found = _count_found(scanned, section)
        if declared > 0 and found == 0:
            warnings.append(f"{section}: Agent 声明了 {declared} 个但扫描到 0 个（可能是 exportStyle 提取失败）")

    # 检查关键字段: middleware 必须声明 reqInjection
    for mw in agent_truth.get("exposed_to_upper", {}).get("middleware", []):
        if mw.get("name") == "authenticate" and not mw.get("reqInjection"):
            warnings.append("middleware authenticate 未声明 reqInjection（下游 Agent 不知道 req.userId 存在）")

    # 检查 exportStyle: 对每个导出声明的文件验证
    for section, key in [("utils_exports", "utils"), ("config_exports", "config")]:
        for item in agent_truth.get("exposed_to_upper", {}).get(section, []):
            exported_file = item.get("file", "")
            if exported_file and not item.get("exportStyle"):
                warnings.append(f"{exported_file}: 未声明 exportStyle (named/default/object)")

    return warnings


def _count_declared(truth: dict, section: str) -> int:
    upper = truth.get("exposed_to_upper", {})
    peers = truth.get("exposed_to_peers", {})
    return len(upper.get(section, [])) + len(peers.get(section, []))


def _count_found(scanned: dict, section: str) -> int:
    return len(scanned.get(section, []))
