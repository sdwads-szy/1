# agent/architect.py
"""
架构工程师 —— 读 PRD → 生成 task_<timestamp>.json (contracts + tasks)。

输出结构:
  {
    "project_name": "...",
    "plan_version": "1.0.0",
    "created_at": "...",
    "contracts": {
      "scenario": [],
      "model": [],
      "logic": [],
      "api": [],
      "db-api": [],
      "navigation": [],
      "auth": []
    },
    "tasks": [ infra/db/backend/frontend/integration tasks ]
  }
"""

import asyncio, json, os, sys
from pathlib import Path
from datetime import datetime

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from picoagents import Agent, OpenAIChatCompletionClient
from Tools.coding.read_file import read_file
from Tools.coding.create_file import create_file
from Tools.coding.modify_file import modify_file

load_dotenv("./.env.example")
model_client = OpenAIChatCompletionClient(model=os.getenv("OPENAI_MODEL"))

REPORT_DIR = project_root / "work" / "project" / "doc"
TASK_DIR = project_root / "work" / "project" / "task"
TASK_DIR.mkdir(parents=True, exist_ok=True)

ARCHITECT_SKILL = project_root / "skill" / "engineer" / "architect.md"

def load_skill(path: Path) -> str:
    if path.exists(): return path.read_text("utf-8")
    return ""

def find_latest_report() -> Path:
    reports = sorted(REPORT_DIR.glob("requirement_report_*.md"))
    if not reports: raise FileNotFoundError(f"No report in {REPORT_DIR}")
    return max(reports, key=lambda p: p.stat().st_mtime)


async def run_architect_agent(report_path: str = None) -> dict:
    """Run architect agent to generate task_<timestamp>.json from PRD report.

    Args:
        report_path: Optional path to requirement report. If None,
                     auto-discovers the latest report in REPORT_DIR.
    """
    if report_path:
        report_path = Path(report_path)
        if not report_path.exists():
            return {"success": False, "error": f"Report not found: {report_path}"}
    else:
        report_path = find_latest_report()
    report_abs = str(report_path.resolve())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    task_filename = f"task_{timestamp}.json"
    task_filepath = TASK_DIR / task_filename

    skill = load_skill(ARCHITECT_SKILL)

    instructions = f"""{skill}

## 本次任务
- 需求报告: {report_abs}
- 输出文件: {task_filepath}

## 执行要点
1. 严格遵循上述 Skill 的 §2（自顶向下构建 7 类契约）和 §3（自底向上分配 5 类任务）。
2. 必须执行 §2.1 的模块清单摘录和 §2.3 的模块→契约追溯，所有模块 ✅ 后才能进入任务分配。
3. 7 类契约: scenario / model / logic / api / db-api / navigation / auth — 缺一不可。
4. 5 类任务: infra / db / backend / frontend / integration — integrate.dependencies 必须列出所有其他 taskId。
5. 使用 create_file 一次性生成完整 JSON，再用 read_file 回读校验，遗漏用 modify_file 补充。
"""

    print(f"[architect] Report: {report_path.name}")
    print(f"[architect] Output: {task_filename}")

    agent = Agent(
        name="architect",
        description="Architect - task generation from PRD",
        instructions=instructions,
        model_client=model_client,
        tools=[read_file, create_file, modify_file],
        max_iterations=50,
    )

    collected = []
    try:
        async for event in agent.run_stream(
            "Read the PRD, plan all contracts and tasks, then generate the complete JSON.",
            stream_tokens=False,
        ):
            collected.append(str(event))
    except Exception as e:
        print(f"[architect] Error: {e}")
        return {"success": False, "error": str(e)}

    task_ok = task_filepath.exists()
    task_count = 0
    contract_count = 0
    warnings = []

    if task_ok:
        try:
            data = json.loads(task_filepath.read_text("utf-8"))
            tasks = data.get("tasks", [])
            contracts_raw = data.get("contracts", {})

            # 兼容旧格式（contracts 为数组）和新格式（contracts 按类型分组为 dict）
            if isinstance(contracts_raw, dict):
                contracts = []
                for ctype, clist in contracts_raw.items():
                    if isinstance(clist, list):
                        contracts.extend(clist)
            else:
                contracts = contracts_raw

            task_count = len(tasks)
            contract_count = len(contracts)

            # ── 后处理：校验 + 自动修复 ──
            warnings = _post_process_architect_output(tasks, contracts)
            task_filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")

            print(f"[architect] Done: {task_count} tasks + {contract_count} contracts")
            if warnings:
                print(f"[architect] Warnings ({len(warnings)}):")
                for w in warnings[:5]:
                    print(f"  - {w}")
        except Exception as e:
            task_ok = False
            print(f"[architect] Post-process error: {e}")

    return {
        "success": task_ok,
        "task_file": str(task_filepath),
        "task_count": task_count,
        "contract_count": contract_count,
        "warnings": warnings,
    }


def _load_file_refs() -> dict:
    """从 config/file_refs.json 加载文件引用关系表。"""
    config_path = project_root / "config" / "file_refs.json"
    try:
        import json
        config = json.loads(config_path.read_text("utf-8"))
        return config.get("known_refs", {})
    except Exception:
        print(f"[architect] WARNING: failed to load config/file_refs.json, using empty refs")
        return {}


def _post_process_architect_output(tasks: list, contracts: list) -> list:
    """校验 LLM 生成的 contracts + tasks，自动修复可修问题。返回告警列表。

    同时兼容新旧两种命名风格：
      新: taskId / outputFiles / usesContracts / type:infra/db
      旧: id     / files       / requiredContracts / type:infrastructure/database
    """
    warnings = []

    # ── 辅助：统一 task ID 获取 ──
    def _tid(t: dict) -> str: return t.get("taskId") or t.get("id", "")
    def _ttype(t: dict) -> str:
        raw = t.get("type", "")
        # 新旧 type 值归一化
        if raw in ("infrastructure",): return "infra"
        if raw in ("database",):       return "db"
        return raw
    def _tfiles(t: dict) -> list: return t.get("outputFiles") or t.get("files") or t.get("path", [])
    def _tcontracts(t: dict) -> list: return t.get("usesContracts") or t.get("requiredContracts", [])

    task_ids = {_tid(t) for t in tasks}
    contract_ids = {c.get("contractId", "") for c in contracts}

    # 1. 校验契约必填字段 + 自动修复
    contract_types_seen = set()
    for c in contracts:
        cid = c.get("contractId", "")
        ctype = c.get("type", "")
        contract_types_seen.add(ctype)

        if ctype == "model":
            if c.get("indexes") is None:
                c["indexes"] = []
            if c.get("constraints") is None:
                c["constraints"] = []
            if c.get("fields") is None:
                warnings.append(f"{cid}: model 缺 fields")
            else:
                for fld in c["fields"]:
                    if "nullable" not in fld:
                        fld["nullable"] = True

        if ctype == "scenario":
            if not c.get("steps"):
                warnings.append(f"{cid}: scenario steps 为空")
            if c.get("priority") not in ("main_trunk", "branch"):
                warnings.append(f"{cid}: scenario priority 非 main_trunk/branch")

        if ctype == "db-api":
            # 🛑 新格式: db-api 使用 typeHints（语义方向 + 类型提示），不再预定义具体 params
            # 旧格式校验（sqlTemplate + params）已废弃，仅保留基本字段检查
            type_hints = c.get("typeHints", {})
            if not type_hints:
                warnings.append(f"{cid}: db-api 缺 typeHints")
            else:
                input_dir = type_hints.get("inputDirection", {})
                output_dir = type_hints.get("outputDirection", {})
                if not input_dir:
                    warnings.append(f"{cid}: typeHints 缺 inputDirection")
                if not output_dir:
                    warnings.append(f"{cid}: typeHints 缺 outputDirection")
            if not c.get("operation"):
                warnings.append(f"{cid}: db-api 缺 operation (CRUD_CREATE/CRUD_READ/CRUD_UPDATE/CRUD_DELETE)")
            if not c.get("tableName"):
                warnings.append(f"{cid}: db-api 缺 tableName（必须指定操作的数据库表）")

        if ctype == "api":
            if not c.get("basePath"):
                warnings.append(f"{cid}: api 缺 basePath")
            elif not c["basePath"].startswith("/api"):
                warnings.append(f"{cid}: basePath 不以 /api 开头: {c['basePath']}")
            # 🛑 新格式: api 使用 typeHints，检查端点是否有 typeHints
            for ep in c.get("endpoints", []):
                if not ep.get("typeHints"):
                    warnings.append(f"{cid}/{ep.get('method','?')} {ep.get('path','?')}: endpoint 缺 typeHints")
            # 后台 API 应含 permission
            if "admin" in cid.lower() or "/admin/" in c.get("basePath", ""):
                for ep in c.get("endpoints", []):
                    if ep.get("auth") and not ep.get("permission"):
                        ep["permission"] = "admin"  # 自动补全

        if ctype == "logic":
            if c.get("steps") is None:
                warnings.append(f"{cid}: logic steps 为空")
            if c.get("transactionBoundary") is None:
                c["transactionBoundary"] = False

        if ctype == "navigation":
            if not c.get("toPageRoute"):
                warnings.append(f"{cid}: navigation 缺 toPageRoute")
            if not c.get("toPage"):
                warnings.append(f"{cid}: navigation 缺 toPage")
            if not c.get("passBy"):
                warnings.append(f"{cid}: navigation 缺 passBy (必须指定 params/query/state)")
            elif c["passBy"] not in ("params", "query", "state"):
                warnings.append(f"{cid}: passBy 值非法 '{c['passBy']}' (须为 params/query/state)")

        if ctype == "auth":
            if not c.get("tokenConfig"):
                warnings.append(f"{cid}: auth 缺 tokenConfig")
            if not c.get("frontendContract"):
                warnings.append(f"{cid}: auth 缺 frontendContract (storageKey/headerFormat)")
            if not c.get("middlewareContract"):
                warnings.append(f"{cid}: auth 缺 middlewareContract (reqInjection)")

        # 规范化
        c.pop("repairStrategy", None)

    # 2. 检测缺失的契约类型（7 类缺一不可）
    expected_types = {"scenario", "model", "logic", "api", "db-api", "navigation", "auth"}
    missing_types = expected_types - contract_types_seen
    if missing_types:
        warnings.append(f"缺少契约类型: {', '.join(sorted(missing_types))}（7类契约缺一不可）")

    # 3. 校验任务 + 规范化
    infra_ids = {_tid(t) for t in tasks if _ttype(t) == "infra"}
    db_ids   = {_tid(t) for t in tasks if _ttype(t) == "db"}

    for t in tasks:
        tid = _tid(t)
        ttype = _ttype(t)

        # 清除 LLM 乱写的字段
        for junk in ("repairStrategy", "manualReason", "fallbackToManual"):
            t.pop(junk, None)

        # 校验依赖
        deps = t.get("dependencies", [])
        for dep in deps:
            if dep not in task_ids:
                warnings.append(f"{tid}: 依赖不存在 {dep}")

        # 最小依赖检查
        if ttype == "db" and not (set(deps) & infra_ids):
            # db 任务可独立（仅需 mysql2 包），不强依赖 infra 代码
            pass
        if ttype == "backend" and not (set(deps) & infra_ids):
            warnings.append(f"{tid}: backend 未依赖 infra")

        # 校验 frontend scope
        if ttype == "frontend":
            scope = t.get("scope", "")
            if scope not in ("frontend", "backend_admin"):
                warnings.append(f"{tid}: frontend 缺 scope 或值非法（须为 frontend/backend_admin）")

            # 🛑 多页面任务必须有导航契约
            files = _tfiles(t)
            vue_pages = [f for f in files if f.endswith(".vue")]
            if len(vue_pages) >= 2:
                refs = _tcontracts(t)
                nav_refs = [r for r in refs if r.startswith("nav_")]
                if not nav_refs:
                    pages_str = ", ".join(f.split("/")[-1] for f in vue_pages)
                    warnings.append(
                        f"{tid}: {len(vue_pages)} 个 .vue 页面（{pages_str}）"
                        f" 但 usesContracts 中无 navigation 契约"
                    )

        # 校验文件数 + 建议拆分
        files = _tfiles(t)
        if ttype == "infra" and len(files) > 3:
            warnings.append(f"{tid}: infra 文件数 {len(files)} > 3, 须拆分子任务")
        if ttype in ("backend", "frontend") and len(files) > 4:
            pages = [f for f in files if 'pages' in f or 'Page' in f or '.vue' in f]
            suggestion = ""
            if len(pages) > 3:
                groups = [pages[i:i+3] for i in range(0, len(pages), 3)]
                suggestion = f" → 建议拆为{len(groups)}个任务: " + ", ".join(
                    f"{tid}_{chr(97+i)}" for i in range(len(groups)))
            warnings.append(f"{tid}: {ttype} 文件数 {len(files)} > 4{suggestion}")
        if ttype == "db" and len(files) > 2:
            warnings.append(f"{tid}: db 文件数 {len(files)} > 2, 须按表拆分")

        # 校验 usesContracts
        for rc in _tcontracts(t):
            if rc not in contract_ids:
                warnings.append(f"{tid}: 引用了不存在的契约 {rc}")

    # 4. 校验 integrate 任务
    for t in tasks:
        if _ttype(t) == "integration":
            non_integrate = [tid for tid in task_ids if tid != _tid(t)]
            missing = set(non_integrate) - set(t.get("dependencies", []))
            if missing:
                warnings.append(f"{_tid(t)}: integrate 缺 {len(missing)} 个依赖")
            actions = t.get("actions", [])
            if len(actions) < 5:
                warnings.append(f"{_tid(t)}: integrate.actions 仅 {len(actions)} 项（≥5 项: 路由注册/前端路由/env-check/.env.example/端到端测试）")

    # 5. 契约交叉校验：环境变量约束一致性
    env_constraints = _extract_env_constraints(contracts)
    if env_constraints:
        for t in tasks:
            if _ttype(t) == "infra":
                existing = t.get("envConstraints", {})
                for k, v in env_constraints.items():
                    if k not in existing:
                        existing[k] = v
                if existing:
                    t["envConstraints"] = existing
                warnings.append(
                    f"已注入 {len(env_constraints)} 个 env 约束到 infra 任务: "
                    + ", ".join(f"{k}={v}" for k, v in env_constraints.items())
                )

    # 6. 第三方服务 env 依赖：从契约扫描 → 注入到对应 backend 任务的 envDependencies
    service_deps = _extract_service_env_deps(contracts)
    if service_deps:
        for t in tasks:
            if _ttype(t) not in ("backend",):
                continue
            used_contracts = _tcontracts(t)
            merged = {}
            for cid in used_contracts:
                if cid in service_deps:
                    merged.update(service_deps[cid])
            if merged:
                raw = t.get("envDependencies")
                existing = {}
                if isinstance(raw, dict):
                    existing = raw
                elif isinstance(raw, list):
                    # LLM 可能误生成为数组，转为 dict
                    for item in raw:
                        existing[str(item)] = ""
                existing.update(merged)
                t["envDependencies"] = existing
                warnings.append(
                    f"{_tid(t)}: 已注入 envDependencies: "
                    + ", ".join(merged.keys())
                )

    # 7. 同类任务文件引用依赖检查
    # 找出同类任务中 A 的 outputFiles 包含 require(B 的 outputFiles) 但 A 未声明依赖 B 的情况
    file_to_task = {}
    for t in tasks:
        for f in _tfiles(t):
            file_to_task[f] = _tid(t)

    # 已知的同类引用模式（文件名→文件名） — 从配置文件加载
    known_refs = _load_file_refs()

    for t in tasks:
        tid = _tid(t)
        ttype = _ttype(t)
        if ttype == "integration":
            continue
        deps = set(t.get("dependencies", []))
        files = _tfiles(t)

        for src_file in files:
            refs = known_refs.get(src_file, [])
            for ref in refs:
                if ref in file_to_task:
                    ref_task = file_to_task[ref]
                    if ref_task != tid and ref_task not in deps:
                        t.setdefault("dependencies", []).append(ref_task)
                        warnings.append(
                            f"{tid}: 已自动注入依赖 {ref_task}"
                            f" ({src_file} → {ref})"
                        )

    # 8. db 任务 FK 依赖检查 — 构建索引后 O(n) 完成
    model_to_db = {}
    for t in tasks:
        if _ttype(t) == "db":
            for rc in _tcontracts(t):
                if rc.startswith("model_"):
                    model_to_db[rc] = _tid(t)

    # 构建 table_name → contractId 索引，避免内层全量扫描
    table_to_contract = {}
    for c in contracts:
        if c.get("type") == "model" and c.get("tableName"):
            table_to_contract[c["tableName"]] = c.get("contractId", "")

    # 构建 task_id → task 索引，避免重复遍历
    task_index = {_tid(t): t for t in tasks}

    for c in contracts:
        if c.get("type") != "model":
            continue
        cid = c.get("contractId", "")
        table = c.get("tableName", "")
        child_task_id = model_to_db.get(cid)
        if not child_task_id:
            continue
        for fk in c.get("constraints", []):
            if fk.get("type") != "foreignKey":
                continue
            refs = fk.get("references", "")
            ref_table = refs.split("(")[0] if "(" in refs else refs
            # O(1) 查找 ref_table 所属的 model 和 db task
            ref_contract_id = table_to_contract.get(ref_table)
            if ref_contract_id:
                parent_task_id = model_to_db.get(ref_contract_id)
                if parent_task_id and parent_task_id != child_task_id:
                    child_task = task_index.get(child_task_id)
                    if child_task and parent_task_id not in child_task.get("dependencies", []):
                        child_task.setdefault("dependencies", []).append(parent_task_id)
                        warnings.append(
                            f"{child_task_id}: 已自动注入依赖 {parent_task_id}"
                            f" (FK: {table}→{ref_table})"
                        )

    # 9. frontend 任务页面跳转依赖检查
    page_to_ftask = {}
    for t in tasks:
        if _ttype(t) == "frontend":
            for f in _tfiles(t):
                if f.endswith(".vue"):
                    page_to_ftask[f.split("/")[-1].replace(".vue", "")] = _tid(t)

    for c in contracts:
        if c.get("type") != "navigation":
            continue
        action = c.get("action", "")
        # 🛑 back/reload 不传递数据，不创建依赖。只有 navigate/detail/edit 需要
        if action in ("back", "reload"):
            continue
        fp = c.get("fromPage", "")
        tp = c.get("toPage", "")
        from_task = page_to_ftask.get(fp)
        to_task = page_to_ftask.get(tp)
        if from_task and to_task and from_task != to_task:
            # 🛑 防循环: 如果反向已有依赖，跳过
            from_deps = []
            for t in tasks:
                if _tid(t) == from_task:
                    from_deps = t.get("dependencies", [])
                    break
            if to_task in from_deps:
                continue
            to_deps = []
            for t in tasks:
                if _tid(t) == to_task:
                    to_deps = t.get("dependencies", [])
                    break
            if from_task not in to_deps:
                for t2 in tasks:
                    if _tid(t2) == to_task:
                        t2.setdefault("dependencies", []).append(from_task)
                        break
                warnings.append(
                    f"{to_task}: 已自动注入依赖 {from_task}"
                    f" (nav: {fp}->{tp})"
                )

    return warnings


def _extract_service_env_deps(contracts: list) -> dict:
    """扫描契约文本，检测第三方服务引用 → 返回 {contractId: {ENV_VAR: description}}。

    依据 envDependencies 白名单（定义见 skill/code/quality.md §十一）:
      短信 → SMS_API_KEY / SMS_API_SECRET / SMS_TEMPLATE_ID
      微信支付 → WECHAT_PAY_*
      支付宝 → ALIPAY_*
      微信OAuth → WECHAT_APP_ID / WECHAT_APP_SECRET
    """
    import re

    # 服务检测规则: (关键词正则, {env变量: 描述})
    service_rules = [
        (
            r"短信|验证码|sms|SMS",
            {
                "SMS_API_KEY": "短信服务API密钥",
                "SMS_API_SECRET": "短信服务API密钥Secret",
                "SMS_TEMPLATE_ID": "短信模板ID",
            },
        ),
        (
            r"微信支付|wxpay|wechat.*pay|微信.*支付",
            {
                "WECHAT_PAY_APP_ID": "微信支付AppID",
                "WECHAT_PAY_MCH_ID": "微信支付商户号",
                "WECHAT_PAY_API_KEY": "微信支付API密钥",
                "WECHAT_PAY_NOTIFY_URL": "微信支付回调URL",
            },
        ),
        (
            r"支付宝|alipay",
            {
                "ALIPAY_APP_ID": "支付宝AppID",
                "ALIPAY_PRIVATE_KEY": "支付宝应用私钥",
                "ALIPAY_PUBLIC_KEY": "支付宝公钥",
                "ALIPAY_NOTIFY_URL": "支付宝回调URL",
            },
        ),
        (
            r"微信.*登录|微信.*OAuth|wechat.*oauth|wechat.*login|微信.*授权",
            {
                "WECHAT_APP_ID": "微信开放平台AppID",
                "WECHAT_APP_SECRET": "微信开放平台AppSecret",
            },
        ),
    ]

    result = {}

    for c in contracts:
        cid = c.get("contractId", "")
        # 收集该契约的全部文本
        texts = []
        for field in ("description", "procedureSignature", "sqlTemplate"):
            if c.get(field):
                texts.append(str(c[field]))
        if c.get("steps"):
            for step in c["steps"]:
                texts.append(str(step.get("description", "")))
                texts.append(str(step.get("businessRule", "")))
                # 也检查 dbOperations 中的表名和操作描述
                for dbop in step.get("dbOperations", []):
                    if isinstance(dbop, dict):
                        texts.append(str(dbop.get("table", "")))
                    elif isinstance(dbop, str):
                        texts.append(dbop)
        if c.get("endpoints"):
            for ep in c["endpoints"]:
                texts.append(str(ep.get("description", "")))
                texts.append(str(ep.get("path", "")))
        if c.get("errorMapping"):
            for err in c.get("errorMapping", {}).values():
                texts.append(str(err.get("message", "")))

        combined = " ".join(texts)

        for pattern, env_vars in service_rules:
            if re.search(pattern, combined, re.IGNORECASE):
                if cid not in result:
                    result[cid] = {}
                result[cid].update(env_vars)

    return result


def _extract_env_constraints(contracts: list) -> dict:
    """从 logic/api 契约中提取环境变量约束，确保 infra 任务生成正确的 .env 值。

    扫描规则：
    - logic 契约的 description/steps 中提及 ENCRYPTION_KEY/JWT_SECRET 等
    - 提取格式约束，如 "64位十六进制字符串" → 生成对应占位符说明
    """
    import re
    constraints = {}

    # 已知 env 变量 + 约束模式（从 logic/api 契约描述中提取）
    env_patterns = {
        "ENCRYPTION_KEY": [
            (r"64\s*位.*十六进制|64.*hex|32\s*字节|AES-256", "64位十六进制字符串(32字节)"),
            (r"32\s*字符|32\s*char", "32字符字符串"),
        ],
        "JWT_SECRET": [
            (r"256\s*位|HMAC-SHA256|至少\s*32", "至少32字符随机字符串"),
        ],
        "JWT_REFRESH_SECRET": [
            (r"256\s*位|HMAC-SHA256|至少\s*32", "至少32字符随机字符串"),
        ],
        "REDIS_URL": [
            (r"redis://", "redis://host:port/db"),
        ],
    }

    for c in contracts:
        ctype = c.get("type", "")
        if ctype not in ("logic", "api", "scenario", "db-api"):
            continue

        # 收集所有可能包含 env 约束的文本
        texts = []
        for field in ("description", "procedureSignature"):
            if c.get(field):
                texts.append(str(c[field]))
        if c.get("steps"):
            for step in c["steps"]:
                texts.append(str(step.get("description", "")))
                texts.append(str(step.get("businessRule", "")))
        combined = " ".join(texts)

        for env_var, patterns in env_patterns.items():
            for pattern, constraint in patterns:
                if re.search(pattern, combined, re.IGNORECASE):
                    if env_var not in constraints:
                        constraints[env_var] = constraint
                    break

    return constraints


async def main():
    result = await run_architect_agent()
    print(f"\nResult: tasks={result.get('task_count', 0)}")


if __name__ == "__main__":
    asyncio.run(main())
