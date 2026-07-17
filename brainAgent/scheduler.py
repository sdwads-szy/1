# brainAgent/scheduler.py
"""
测试调度器 —— 4类型22层: 静态层(直通) + 接口/逻辑/质量层(ABCD循环) + 真理传递
"""

from __future__ import annotations
import asyncio, json, os, sys, hashlib,re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

import redis.asyncio as aioredis

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from picoagents import Agent
from dotenv import load_dotenv

from agent.test_writer import run_test_writer
from agent.test_runner import run_test_runner
from agent.source_fixer import run_source_fixer
from Tools.memory.ban_memory import get_bans, store_bans, format_bans_for_agent, clear_bans
from utils.dependency_graph import build as build_dependency_graph, print_levels
from utils.json_extractor import extract_json
import re as _ban_re


# ═══════════════════════════════════════════
# 常量与全局状态
# ═══════════════════════════════════════════

def _store_bans_by_target(task_id: str, bans: list) -> tuple:
    """按每条 ban 的 target=test/source 分别写入对应 Memory 目录。

    判断优先级:
      1. b 字段中 target=test 或 target=source 标记
      2. f 字段 fingerprint 第二段 (fix_target)
      3. 兜底: source_failure

    Returns: (test_count, source_count)
    """
    test_bans, source_bans = [], []
    for ban in bans:
        if not isinstance(ban, dict):
            source_bans.append(ban)
            continue
        b_text = ban.get("b", "")
        # 优先: b 字段中的 target= 标记
        m = _ban_re.search(r'target=(test|source)', b_text)
        if m:
            (test_bans if m.group(1) == "test" else source_bans).append(ban)
            continue
        # 回退: f fingerprint 第二段
        f_text = ban.get("f", "")
        parts = f_text.split("|") if f_text else []
        if len(parts) >= 2 and parts[1] == "test":
            test_bans.append(ban)
        else:
            source_bans.append(ban)

    t_cnt = store_bans(task_id, "test_failure", test_bans) if test_bans else 0
    s_cnt = store_bans(task_id, "source_failure", source_bans) if source_bans else 0
    return (t_cnt, s_cnt)

load_dotenv('./.env.example')

MEMORY_DIR = project_root / "Memory" / "test_logs"
AGENT_LOG_DIR = project_root / "Memory" / "agent_logs" / "test"
TRUTH_DIR_ENGINEER = project_root / "Memory" / "truths" / "engineer"
TRUTH_DIR_TEST = project_root / "Memory" / "truths" / "test"
BAN_TEST_DIR = project_root / "Memory" / "test_failure"
BAN_SOURCE_DIR = project_root / "Memory" / "source_failure"

for d in [MEMORY_DIR, AGENT_LOG_DIR, TRUTH_DIR_TEST]:
    d.mkdir(parents=True, exist_ok=True)



def _build_dir_tree(ws: Path) -> str:
    """生成工作区目录结构摘要（两层），替代 list_dir 工具。
    跳过不相关目录: node_modules, test, task, logs, doc, .meta, Memory, report, package-lock.json 等。
    """
    _SKIP = {'.git', 'node_modules', 'test', 'task', 'logs', 'doc', '.meta', 'Memory', 'report',
             'package-lock.json'}
    lines = ["```"]
    try:
        items = sorted(ws.iterdir())
    except (PermissionError, FileNotFoundError):
        return "```\n(目录不存在或无权访问)\n```"
    for item in items:
        if item.name.startswith('.') or item.name in _SKIP:
            continue
        if item.is_dir():
            lines.append(f"{item.name}/")
            try:
                for sub in sorted(item.iterdir()):
                    if sub.name.startswith('.') or sub.name in _SKIP:
                        continue
                    prefix = "  ├── " if sub.is_dir() else "  └── "
                    suffix = "/" if sub.is_dir() else ""
                    lines.append(f"{prefix}{sub.name}{suffix}")
            except PermissionError:
                pass
        else:
            lines.append(f"{item.name}")
    lines.append("```")
    return "\n".join(lines)


MAX_CONCURRENT = 100
_DB_INITIALIZED = False  # 数据库初始化只跑一次，integ 重试跳过
_IS_LAST_LEVEL = False  # 当前层级是否为依赖图最后一层（终端层跳过真理）

# 双层屏障：文件锁=注册点 → B/C 计数 → 烟雾 → D 计数 → 解锁下轮
# total: 本轮参与 barrier 的任务总数（_attempt_once 入口注册）
# b_p: B 测试全部通过 → done（无需 C/D）
# s_o: C 完成 + smoke 通过 → 等 C→D 解锁 → 进入 D
# s_f: C 完成 + smoke 失败 → 回滚，不参与 D
# skipped: B test ban / C source_fixer fail 等跳过本轮的（不贡献 b_p/s_o/s_f，但需计入屏障1）
# d_p: D 验证通过
# d_f: D 验证失败
# 屏障1: b_p + s_o + s_f + skipped >= total → _cd_ev.set()  全部 B/C+smoke+skip 完成
# 屏障2: d_p + d_f >= s_o                    → _d_ev.set()  全部 D 完成
# gen 重置: _round_done >= total 且 d_p+d_f >= s_o → total=0, 新 Events, _registered_tasks 清空
_cd_state = {"total":0, "b_p":0, "s_o":0, "s_f":0, "skipped":0, "d_p":0, "d_f":0}
_cd_ev = None  # C→D 解锁
_d_ev = None   # D→下轮解锁
_cd_lk = asyncio.Lock()  # 计数互斥
_round_done = 0  # 已完成本轮贡献的任务数
_registered_tasks = set()  # 当前 gen 已注册的任务 ID

# 全局构建命令锁 — 防止并发 npx vite build / node app.js 冲突
import threading
_vite_lock = threading.Lock()
_node_app_lock = threading.Lock()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_redis_client: Optional[aioredis.Redis] = None


# ═══════════════════════════════════════════════
# 4 大测试类型
# ═══════════════════════════════════════════════

# testType → layer 映射
TEST_TYPE_LAYERS = {
    "static":    ["infra", "db", "frontend", "peer_deps", "integ"],
    "interface": ["auth", "db_api", "api", "navigation"],
    "logic":     ["backend_proc", "logic", "scenario"],
    "quality":   ["nfr"],
}

# 类型优先级（执行顺序：static → interface → logic → quality）
TYPE_PRIORITY = {"static": 0, "interface": 1, "logic": 2, "quality": 3}


# ═══════════════════════════════════════════════
# Truth 加载 (Agent生成主数据源 + 正则验证回退)
# ═══════════════════════════════════════════════


# ═══════════════════════════════════════════
# TaskTestState — 任务状态持久化
# ═══════════════════════════════════════════

class TaskTestState:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.test_success = False
        self.source_success = False
        self.test_file_path: Optional[str] = None
        self.attempt = 0
        self.done = False
        self.best_score: float = 0.0
        self.best_attempt: int = 0
        self.source_hash: str = ""
        self.truth: Any = None

    @property
    def state_label(self) -> str:
        return f"({'TS' if self.test_success else 'TF'}, {'SS' if self.source_success else 'SF'})"

    @property
    def is_ts_ss(self) -> bool:
        return self.test_success and self.source_success

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id, "test_success": self.test_success,
            "source_success": self.source_success, "test_file_path": self.test_file_path,
            "attempt": self.attempt, "done": self.done,
            "best_score": self.best_score, "best_attempt": self.best_attempt,
            "source_hash": self.source_hash, "state": self.state_label, "truth": self.truth,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TaskTestState":
        s = cls(d["task_id"])
        s.test_success = d.get("test_success", False)
        s.source_success = d.get("source_success", False)
        s.test_file_path = d.get("test_file_path")
        s.attempt = d.get("attempt", 0)
        s.done = d.get("done", False)
        s.best_score = d.get("best_score", 0.0)
        s.best_attempt = d.get("best_attempt", 0)
        s.source_hash = d.get("source_hash", "")
        s.truth = d.get("truth", None)
        return s



def _load_state(task_id: str) -> TaskTestState:
    f = MEMORY_DIR / f"{task_id}.json"
    if f.exists():
        try:
            return TaskTestState.from_dict(json.loads(f.read_text("utf-8")))
        except Exception:
            pass
    return TaskTestState(task_id)



def _save_state(state: TaskTestState):
    f = MEMORY_DIR / f"{state.task_id}.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    d = state.to_dict()
    d.pop("truth", None)  # truth 已单独存 truths/test/，不在状态文件重复
    f.write_text(json.dumps(d, indent=2, ensure_ascii=False), "utf-8")



class DebugLogger:
    @staticmethod
    def _dir(task_id: str, attempt: int) -> Path:
        d = AGENT_LOG_DIR / task_id / f"attempt_{attempt}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @classmethod
    def save_raw(cls, task_id: str, attempt: int, step: str, agent_name: str, raw_output: str):
        d = cls._dir(task_id, attempt)
        fp = d / f"{step}_{agent_name}.md"
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(raw_output, "utf-8")




# ═══════════════════════════════════════════
# 工具函数 (npm, jest, DB scripts, env, barrier)
# ═══════════════════════════════════════════

def _fix_jest_test_match(ws_path: Path):
    """统一 jest 配置——消除 projects 双配置，改为单层 testMatch。

    测试模板全部写入 test/ 目录，不需要 backend/frontend 分离。
    如果存在 projects 配置则合并为单一配置。
    """
    import json
    package_json = ws_path / "package.json"
    if not package_json.exists():
        return
    try:
        pkg = json.loads(package_json.read_text("utf-8"))
    except Exception:
        return
    jest_config = pkg.get("jest", {})
    projects = jest_config.get("projects")

    if not projects:
        # 已经是单层配置，只需确保 test/ 在 testMatch 中
        test_match = jest_config.get("testMatch", [])
        if not isinstance(test_match, list):
            test_match = []
        if not any("test/" in m for m in test_match):
            test_match.insert(0, "<rootDir>/test/**/*.test.js")
            test_match.insert(1, "<rootDir>/test/**/*.spec.js")
            jest_config["testMatch"] = test_match
            pkg["jest"] = jest_config
            package_json.write_text(json.dumps(pkg, indent=2, ensure_ascii=False) + "\n", "utf-8")
            print("[scheduler] jest testMatch: +test/ pattern")
        return

    # projects 模式 → 合并为统一的单层配置
    merged_module_name_mapper = {}
    merged_transform = {}

    for proj in projects:
        mapper = proj.get("moduleNameMapper", {})
        if isinstance(mapper, dict):
            merged_module_name_mapper.update(mapper)
        transform = proj.get("transform", {})
        if isinstance(transform, dict):
            merged_transform.update(transform)

    # 最终配置：只有 test/ 目录
    jest_config = {
        "testMatch": ["<rootDir>/test/**/*.test.js", "<rootDir>/test/**/*.spec.js"],
        "testEnvironment": "node",
        "testPathIgnorePatterns": ["/node_modules/"],
        "moduleNameMapper": merged_module_name_mapper,
        "transform": merged_transform,
        "forceExit": True,
    }
    # 修复 scripts：删除 --selectProjects 参数
    scripts = pkg.get("scripts", {})
    for key in list(scripts.keys()):
        if "selectProjects" in scripts[key]:
            if key == "test":
                scripts[key] = "jest"
            else:
                del scripts[key]
    pkg["scripts"] = scripts

    pkg["jest"] = jest_config
    package_json.write_text(json.dumps(pkg, indent=2, ensure_ascii=False) + "\n", "utf-8")
    print("[scheduler] jest: projects 已合并，testMatch=test/，scripts 已清理")



def _fix_package_versions(ws_path: Path):
    """将 package.json 中所有精确版本号加 ^ 前缀，避免 LLM 生成的版本不存在。"""
    import json
    pkg_json = ws_path / "package.json"
    if not pkg_json.exists():
        return
    try:
        pkg = json.loads(pkg_json.read_text("utf-8"))
    except Exception:
        return
    changed = False
    for section in ["dependencies", "devDependencies"]:
        deps = pkg.get(section, {})
        for name, ver in list(deps.items()):
            if isinstance(ver, str) and ver and ver[0].isdigit():
                deps[name] = f"^{ver}"
                changed = True
    if changed:
        pkg_json.write_text(json.dumps(pkg, indent=2, ensure_ascii=False) + "\n", "utf-8")
        print("[scheduler] package.json: 精确版本 → ^前缀（防止 LLM 生成不存在的 patch 版本）")



def _ensure_npm_install(ws_path: Path, all_tasks: list):
    import subprocess
    # 🛑 先修复 LLM 生成的精确版本号（如 7.23.0 不存在 → ^7.23.0 会自动选最新 7.x）
    _fix_package_versions(ws_path)

    needs = []
    if not (ws_path / "node_modules").exists() or not (ws_path / "node_modules" / "jest").exists():
        needs.append("jest")
    if not (ws_path / "node_modules" / "jest-environment-jsdom").exists():
        needs.append("jest-environment-jsdom")
    if not (ws_path / "node_modules" / "jest-environment-node").exists():
        needs.append("jest-environment-node")
    # 🆕 API 测试需要 supertest（HTTP 断言）
    has_api_tests = any(t.get("testType") in ("interface", "logic") or
                        t.get("layer") in ("api", "auth", "navigation", "backend_proc", "logic", "scenario")
                        for t in all_tasks)
    if has_api_tests and not (ws_path / "node_modules" / "supertest").exists():
        needs.append("supertest")
    # 🆕 babel-jest 需要 @babel/preset-env（package.json 的 jest.transform 依赖 babel）
    if not (ws_path / "node_modules" / "@babel" / "preset-env").exists():
        needs.append("@babel/preset-env")
    if needs:
        pkgs = " ".join(needs)
        print(f"[scheduler] 安装缺失包: {pkgs}")
        subprocess.run(f"npm install --save-dev {pkgs} --legacy-peer-deps --no-audit --no-fund", shell=True, capture_output=True, text=True,
                      cwd=str(ws_path), timeout=600, encoding="utf-8", errors="replace")

    # 🆕 确保 babel.config.js 存在（jest transform 需要）
    babel_config = ws_path / "babel.config.js"
    if not babel_config.exists():
        babel_config.write_text(
            "module.exports = {\n"
            "  presets: [['@babel/preset-env', { targets: { node: 'current' }, modules: 'commonjs' }]],\n"
            "};\n",
            encoding="utf-8"
        )
        print("[scheduler] 已创建 babel.config.js")

    # 检查 package.json 依赖是否全部安装
    pkg_json = ws_path / "package.json"
    if pkg_json.exists():
        try:
            import json
            pkg = json.loads(pkg_json.read_text("utf-8"))
            all_deps = list(pkg.get("dependencies", {}).keys()) + list(pkg.get("devDependencies", {}).keys())
            missing = [d for d in all_deps if not (ws_path / "node_modules" / d).exists()]
            if missing:
                print(f"[scheduler] npm install (missing: {len(missing)} packages)")
                subprocess.run("npm install --legacy-peer-deps --no-audit --no-fund", shell=True, capture_output=True, text=True,
                             cwd=str(ws_path), timeout=600, encoding="utf-8", errors="replace")
        except Exception:
            pass



def _check_frontend_test_infra(ws_path: Path, all_tasks: list):
    has_vue = any(any(tf.endswith('.vue') for tf in t.get('targetFiles', [])) for t in all_tasks)
    if not has_vue:
        return
    if not (ws_path / "node_modules" / "@vue" / "vue3-jest").exists():
        import subprocess
        print("[scheduler] 安装 @vue/vue3-jest...")
        subprocess.run("npm install --save-dev @vue/vue3-jest --legacy-peer-deps", shell=True, capture_output=True, text=True,
                      cwd=str(ws_path), timeout=600, encoding="utf-8", errors="replace")



def _verify_jest_working(ws_path: Path):
    """初始化时验证 jest 能正常运行（用 node 直调，不依赖 npx PATH）。"""
    import subprocess as _sp
    jest_js = ws_path / "node_modules" / "jest" / "bin" / "jest.js"
    if not jest_js.exists():
        print("[scheduler] ⚠️ jest 未安装，正在安装...")
        _sp.run("npm install --save-dev jest --legacy-peer-deps --no-audit --no-fund", shell=True,
               cwd=str(ws_path), timeout=600, encoding="utf-8", errors="replace")
        jest_js = ws_path / "node_modules" / "jest" / "bin" / "jest.js"
    if not jest_js.exists():
        print("[scheduler] ⚠️ jest 安装失败，跳过验证（后续步骤会重试）")
        return
    try:
        r = _sp.run(["node", str(jest_js), "--version"], capture_output=True, text=True,
                   cwd=str(ws_path), timeout=30, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            print(f"[scheduler] jest OK (v{r.stdout.strip()[:20]})")
        else:
            print(f"[scheduler] ⚠️ jest 验证失败: {r.stderr[:100]}")
    except Exception as e:
        print(f"[scheduler] ⚠️ jest 验证异常: {e}")



def _check_k6_available():
    """检查 k6 是否可用。Docker → winget 一键安装 → 跳过。"""
    import subprocess as _sp, shutil

    # 1. Docker 拉取 grafana/k6 镜像
    if shutil.which("docker"):
        print("[scheduler] k6: docker pull grafana/k6 (首次约2-5分钟)...")
        try:
            has = _sp.run(["docker", "image", "inspect", "grafana/k6"],
                         capture_output=True, timeout=10).returncode == 0
            if not has:
                _sp.run(["docker", "pull", "grafana/k6"], capture_output=True, timeout=300)
            r2 = _sp.run(["docker", "run", "--rm", "grafana/k6", "version"],
                        capture_output=True, text=True, timeout=30)
            if r2.returncode == 0:
                print("[scheduler] k6 OK (docker)")
                return True
        except Exception as e:
            print(f"  docker: {e}")

    # 2. winget 一键安装
    if shutil.which("winget"):
        print("[scheduler] k6: winget install k6.k6 ...")
        try:
            r = _sp.run(["winget", "install", "-e", "--id", "k6.k6",
                        "--accept-source-agreements", "--accept-package-agreements", "--source", "winget"],
                       check=False, timeout=120, capture_output=True)
            if r.returncode == 0:
                print("[scheduler] k6 OK (winget)")
                return True
        except Exception as e:
            print(f"  winget: {e}")

    print("[scheduler] ⚠️ k6 不可用，性能测试(nfr_perf_*)将被跳过")
    return False



def _compute_fk_order(ws_path: Path) -> list:
    """从 DDL SQL 文件分析外键依赖，返回拓扑排序的表名列表。"""
    import re
    db_dir = ws_path / "database"
    if not db_dir.exists():
        return ["users", "categories", "merchants", "products", "reviews"]

    # 收集所有表名和 FK 关系
    tables = set()
    fk_edges = []  # [(child, parent)]
    sql_files = list(db_dir.rglob("*.sql"))

    for fp in sql_files:
        content = fp.read_text('utf-8', errors='replace')
        for m in re.finditer(r'CREATE\s+TABLE.*?`(\w+)`', content, re.IGNORECASE):
            tables.add(m.group(1))
        # FK: CONSTRAINT fk_x FOREIGN KEY (col) REFERENCES parent(col)
        for m in re.finditer(r'FOREIGN\s+KEY\s*\([^)]+\)\s*REFERENCES\s+`(\w+)`', content, re.IGNORECASE):
            parent = m.group(1)
            # 找到这个 FK 属于哪个 CREATE TABLE
            for tm in re.finditer(r'CREATE\s+TABLE.*?`(\w+)`', content, re.IGNORECASE):
                child = tm.group(1)
                if child != parent:  # 跳过自引用
                    fk_edges.append((child, parent))

    if not tables:
        return ["users", "categories", "merchants", "products", "reviews"]

    # 拓扑排序：被依赖的父表先执行（无 FK 依赖 = 父表 = 先执行）
    deps = {t: set() for t in tables}  # table → 它依赖的父表
    for child, parent in fk_edges:
        if child in deps and parent in deps:
            deps[child].add(parent)

    result = []
    remaining = set(tables)
    while remaining:
        # 找当前无未满足依赖的表
        ready = [t for t in remaining if not deps[t] & remaining]
        if not ready:
            # 有环或剩余表全有依赖 → 全加进去
            result.extend(sorted(remaining))
            break
        result.extend(sorted(ready))
        remaining -= set(ready)

    # 补充未参与 FK 的表
    for t in sorted(tables - set(result)):
        result.append(t)

    return result



def _ensure_db_scripts(ws_path: Path):
    """Python 自动生成 init-db.js（仅 DDL）和 seed-users.js（仅种子数据）。"""
    from utils._gen_db_scripts import generate
    fk = json.dumps(_compute_fk_order(ws_path))
    generate(str(ws_path), fk)



def _init_database(ws_path: Path, all_tasks: list):
    global _DB_INITIALIZED
    has_db = any(t.get("layer") == "db" for t in all_tasks)
    if not has_db:
        return
    import subprocess
    ddl_script = ws_path / "scripts" / "init-db.js"
    seed_script = ws_path / "scripts" / "seed-users.js"

    if ddl_script.exists():
        print("[scheduler] DDL 建表: node scripts/init-db.js（30s 超时）...")
        try:
            r = subprocess.run(["node", str(ddl_script)], capture_output=True, text=True,
                              cwd=str(ws_path), timeout=30, encoding="utf-8", errors="replace")
            if r.returncode != 0:
                print(f"  ⚠️ DDL 失败: {(r.stderr or r.stdout or '')[:200]}")
        except Exception as e:
            print(f"  ⚠️ DDL 异常: {e}")

    if seed_script.exists() and (ws_path / "database" / "seed").exists():
        print("[scheduler] 种子数据: node scripts/seed-users.js（30s 超时）...")
        try:
            r = subprocess.run(["node", str(seed_script)], capture_output=True, text=True,
                              cwd=str(ws_path), timeout=30, encoding="utf-8", errors="replace")
            if r.returncode == 0:
                _DB_INITIALIZED = True
                print("  ✓ 数据库初始化完成（DDL + 种子数据）")
            else:
                print(f"  ⚠️ 种子数据失败: {(r.stderr or r.stdout or '')[:200]}")
        except Exception as e:
            print(f"  ⚠️ 种子数据异常: {e}")
    elif ddl_script.exists():
        _DB_INITIALIZED = True



def _check_layer_services(layer_name: str, ws_path: Path) -> str:
    """检查当前层需要的服务是否可用。不可用返回阻断原因，可用返回空字符串。"""
    # db_api 层需要 MySQL 连接
    if layer_name == "db_api":
        import subprocess
        try:
            # 用 node 直连验证 MySQL 可达 + 数据库存在
            env_path = ws_path / ".env"
            env_vars = {}
            if env_path.exists():
                for line in env_path.read_text("utf-8").split("\n"):
                    s = line.strip()
                    if s and not s.startswith("#") and "=" in s:
                        k, v = s.split("=", 1)
                        env_vars[k.strip()] = v.strip().strip('"').strip("'")
            host = env_vars.get("DB_HOST", "localhost")
            port = env_vars.get("DB_PORT", "3306")
            user = env_vars.get("DB_USER", "root")
            pwd = env_vars.get("DB_PASSWORD", "")
            db = env_vars.get("DB_NAME", "testdb")
            # 用 node + mysql2 测连接（比 Python 更接近真实测试环境）
            check_script = f"""
const mysql = require('mysql2/promise');
(async () => {{
  try {{
    const conn = await mysql.createConnection({{
      host: '{host}', port: {port}, user: '{user}',
      password: '{pwd}', database: '{db}',
      connectTimeout: 5000
    }});
    await conn.query('SELECT 1');
    await conn.end();
    process.exit(0);
  }} catch(e) {{
    console.error(e.code || e.message);
    process.exit(1);
  }}
}})();
"""
            r = subprocess.run(
                ["node", "-e", check_script],
                capture_output=True, text=True, timeout=10,
                cwd=str(ws_path), encoding="utf-8", errors="replace",
            )
            if r.returncode != 0:
                err = (r.stderr or "").strip()[:200]
                return f"MySQL 不可达（db_api 层需要数据库）: {err}"
        except subprocess.TimeoutExpired:
            return "MySQL 连接超时（db_api 层需要数据库）"
        except Exception as e:
            return f"MySQL 连接检查异常: {str(e)[:100]}"
    return ""



def _sync_env_files(ws_path: Path):
    """integ passed 后：将 .env 同步到 .env.example / .env.development / .env.production。"""
    import shutil
    env_master = ws_path / ".env"
    if not env_master.exists():
        return
    for fname in [".env.example", ".env.development", ".env.production"]:
        dest = ws_path / fname
        shutil.copy2(str(env_master), str(dest))
    print("  ✓ .env → .env.example / .env.development / .env.production 已同步")



async def _fast_jest_sweep(ws_path: Path):
    import subprocess
    print("[scheduler] Fast mode: running full jest suite...")
    subprocess.run("npx jest --json --forceExit 2>&1", shell=True, capture_output=True, text=True,
                  cwd=str(ws_path), timeout=300, encoding="utf-8", errors="replace")



def _collect_shared_files(tasks: list) -> dict:
    """收集同层共享 targetFiles 的任务（不注入依赖，执行层按文件信号量控制并发）。
    Returns: {file_path: [task_ids]} — 仅 static 层
    """
    from collections import defaultdict
    from utils.dependency_graph import _LAYER_TO_TYPE

    shared = defaultdict(list)
    for t in tasks:
        ltype = t.get("testType") or _LAYER_TO_TYPE.get(t.get("layer", ""), "logic")
        if ltype != "static":
            continue
        for tf in t.get("targetFiles", []):
            if any(tf.endswith(ext) for ext in (".js", ".sql", ".vue", ".json")):
                shared[tf].append(t.get("id", ""))
    return {k: v for k, v in shared.items() if len(v) > 1}


def _inject_layer_from_task_file(ws_path: Path, test_tasks: list):
    """从 task.json 推导每个 test task 的原始 engineer 层，注入到 layer 字段。"""
    import json as _json
    task_dir = ws_path / "task"
    if not task_dir.exists():
        return
    task_files = sorted(task_dir.glob("task_*.json"))
    if not task_files:
        return

    eng_data = _json.loads(task_files[-1].read_text("utf-8"))
    eng_tasks = eng_data.get("tasks", [])
    # 构建 sourceTask.id → type 映射
    type_map = {}
    for t in eng_tasks:
        tid = t.get("taskId") or t.get("id", "")
        ttype = t.get("type", "")
        # 归一化旧名
        if ttype == "infrastructure": ttype = "infra"
        elif ttype == "database": ttype = "db"
        elif ttype == "backend": ttype = "backend_proc"
        type_map[tid] = ttype

    for tt in test_tasks:
        if not tt.get("layer"):
            st = tt.get("sourceTask", "")
            tt["layer"] = type_map.get(st, "static")




# ═══════════════════════════════════════════
# 静态检查函数（Python 硬校验）
# ═══════════════════════════════════════════

def _build_static_check_prompt(task: dict, source_contents: dict, layer: str) -> str:
    """构建静态层检查提示词——告诉 source_fixer 检查什么。"""
    target_files = list(source_contents.keys())
    tid = task.get("id", "unknown")

    check_items = _STATIC_CHECK_RULES.get(layer, _STATIC_CHECK_RULES.get(
        layer.split("_")[0] if "_" in layer else layer, []))

    lines = [
        f"## 静态检查任务: {tid} | 类型: {layer}",
        f"## 目标文件: {', '.join(target_files)}",
        "",
    ]
    checkpoints = task.get("checkPoints", [])
    if checkpoints:
        lines.append("## 🛑 检查点（必须逐条通过）")
        for i, cp in enumerate(checkpoints):
            lines.append(f"{i+1}. {cp}")
        lines.append("")
    lines.append("## 检查规则")
    for item in check_items:
        lines.append(f"- {item}")
    lines.append("")

    # 🛑 执行流程和工具使用规则见 skill/test/roles/c/static.md，此处不重复

    return "\n".join(lines)


# ── 各层静态检查规则 ──
_STATIC_CHECK_RULES = {
    "infra": [
        "package.json: name/version/scripts(db,backend,frontend,test) 字段存在，🛑 禁止添加 \"type\": \"module\"（后端 CJS）",
        "package.json jest: testMatch=['<rootDir>/test/**/*.test.js'], 单层无projects, testEnvironment=node",
        "所有 .env* 文件变量集一致（.env/.env.example/.env.development/.env.production）",
        "config/db.js 导出: pool, query, beginTransaction, commit, rollback, testConnection",
        "config/logger.js 导出: info, error, warn, debug",
        "middleware/auth.js 导出: authenticate, optionalAuth",
        "middleware/permission.js 导出: hasRole",
        "middleware/errorHandler.js 导出: errorHandler",
        "utils/response.js 导出: success(res,data,msg), fail(res,msg,code,data)",
        "所有导出风格一致（module.exports.xxx = 或 {xxx}，不混用）",
        "🆕 npm 依赖: src/ 下所有 import 的裸包名（非 @/ 非相对路径）必须在 package.json dependencies/devDependencies 中",
    ],
    "db": [
        "SQL 语法正确（无缺逗号、缺括号、缺分号、无尾随逗号、括号配对）",
        "AUTO_INCREMENT 列必须有 PRIMARY KEY（否则 MySQL 报错）",
        "🛑 索引/约束名无重复（INDEX/UNIQUE INDEX/CONSTRAINT 名称全局唯一，MySQL 拒绝重名建表）",
        "🛑 列名无重复（同一 CREATE TABLE 内列名唯一）",
        "CREATE TABLE 表名 vs model 契约 tableName 一致",
        "所有字段名/类型 vs model 契约 fields[].name/type 一致",
        "所有种子数据与model契约中的seedData字段一致"
        "NOT NULL/DEFAULT/UNIQUE 约束 vs model 契约一致",
        "FOREIGN KEY 引用目标表存在",
        "INDEX 列 vs model 契约 indexes 一致",
        "ENUM 取值 vs model 契约一致",
    ],
    "frontend": [
        "🆕 npx vite build → 只修复本任务 targetFiles 中的错误，其他文件错误不属于本任务",
        "src/ 下所有 .js 文件使用 ESM (import/export)，禁止 CJS (require/module.exports)",
        ".vue <script> 通过 node --input-type=module --check（ESM 模式）",
        "import from '@/...' 路径指向的文件存在（含 .js/.vue 扩展名尝试）",
        "src/api/ 下文件的 export 函数名 vs 页面 import {X} 的名称一致",
        "🛑 src/api/*.js 禁止跨层数据处理：无 bcrypt/bcryptjs/crypto 导入",
        "v-model 字段名 vs model truth 字段名一致",
        "🛑 src/router/index.js 每条路由有 component/redirect/children",
        "🛑 UI 设计系统 (源: skill/design/designer.md): 令牌引用(颜色/间距/字号/圆角/阴影/动效→var(--xxx-*)) + 组件对齐(按钮4变体×5态/输入框4态/卡片3态/模态框/表格/Toast/标签/导航→_components.md) + 页面规范(禁止inline/emoji/四态齐全)",
        "🛑 导航入口完整性 (静态层负责): 每个角色可见页面必须从至少一个入口页通过 <router-link> 或 router.push 到达。首页含全局入口，每个dashboard含全部子页入口。缺失入口 → C步在源页补建。",
        "🆕 文件路径: img/video/audio/a src 使用 FILE_BASE_URL + 相对路径，禁止硬编码 https:// 完整 URL（见 skill/code/file_uploads.md）",
    ],
    "peer_deps": [
        "🆕 后端 peer_deps: node app.js 找错 → 只报本任务 targetFiles 内的",
        "同层 A 文件 require/import B 文件 → B 确实导出被引用的名称",
        "require 路径文件存在（含扩展名尝试 .js/.vue）",
        "exportStyle (named/default) 与下游 require 方式一致",
        "🆕 npm 依赖按类型校验: 后端 peer_deps→扫描 routes/controllers/services/等 require() 包名 vs package.json",
        "🆕 npm 依赖按类型校验: 前端 peer_deps→扫描 src/ import 包名 vs package.json",
    ],
    "integ": [
        "🛑 app.js 中所有 route require 的文件存在 + routes/ 目录下所有路由文件被 app.js 注册（双向验证）",
        "🛑 src/router/index.js 每条路由有 component/redirect/children，懒加载路径指向文件存在（前端路由注册完整性）",
        "🛑 .env 变量与 .env.example 一致（环境配置完整性）",
        "🆕 数据库初始化: scripts/init-db.js 成功执行（DDL + database/seed/ 种子数据）",
        "🆕 数据库连接可用: config/db.js testConnection() 返回 true",
        "🛑 语法/模板/npm依赖/导出格式已由 frontend/peer_deps/infra 层覆盖，integ 不重复检查",
    ],
}

# 从 utils 导入映射
from utils.dependency_graph import _LAYER_TO_TYPE



def _build_env_reference(ws_path: Path) -> str:
    """生成标准环境变量参考：扫描代码 process.env.X → 交叉 .env.example → 输出模板。"""
    import re as _re

    # 1. 扫描项目中所有 process.env.X 引用
    code_vars = set()
    for root, dirs, files in os.walk(str(ws_path)):
        dirs[:] = [d for d in dirs if d not in ('node_modules', '.git', '.meta', 'test', 'Memory', 'doc', 'report')]
        for fn in files:
            if not fn.endswith(('.js', '.vue')):
                continue
            try:
                content = Path(os.path.join(root, fn)).read_text('utf-8', errors='replace')
                code_vars.update(_re.findall(r'process\.env\.(\w+)', content))
            except Exception:
                pass

    if not code_vars:
        return ""

    # 2. 内置默认值（无需外部 config 文件）
    defaults = {
        'PORT': '3000', 'NODE_ENV': 'development',
        'DB_HOST': 'localhost', 'DB_PORT': '3306', 'DB_USER': 'root',
        'DB_PASSWORD': 'your_db_password', 'DB_NAME': 'testdb',
        'JWT_SECRET': 'your_jwt_secret', 'JWT_EXPIRES_IN': '7d',
        'JWT_REFRESH_SECRET': 'your_refresh_secret',
        'ENCRYPTION_KEY': 'your_encryption_key_32chars',
        'REDIS_URL': 'redis://localhost:6379/0', 'LOG_LEVEL': 'info',
        'CORS_ORIGIN': '*',
    }

    # 3. 读取 .env.example 作为模板
    env_example = ws_path / ".env.example"
    existing = {}
    if env_example.exists():
        for line in env_example.read_text('utf-8').split('\n'):
            s = line.strip()
            if s and not s.startswith('#') and '=' in s:
                k = s.split('=', 1)[0].strip()
                v = s.split('=', 1)[1].strip().strip('"').strip("'")
                existing[k] = v

    # 4. 生成参考：代码引用的变量 → 有默认值用默认值，否则用占位符
    lines = ["\n## 🛑 环境变量标准参考（从代码扫描 + 配置模板生成，以此为权威）\n"]
    lines.append("代码中实际引用的环境变量：")
    for var in sorted(code_vars):
        val = existing.get(var) or defaults.get(var) or f"your_{var.lower()}_here"
        marker = " [代码引用]" if var not in existing else ""
        lines.append(f"  {var}={val}{marker}")
    lines.append(f"\n共 {len(code_vars)} 个代码引用变量。以上值为权威参考，禁止随意修改。")
    lines.append("未在代码中引用的变量（冗余变量）应删除。")

    return "\n".join(lines)



def _run_full_static_check(ws_path: Path, target_files: list, layer: str, task_id: str, task: dict = None) -> str:
    """首轮全量检查——Python 运行所有检查工具，返回原始结果文本。
    Python 不写 memory，结果直接注入 agent prompt。"""
    import re as _re, json as _json
    lines = []

    for tf in target_files:
        fp = ws_path / tf
        if not fp.exists():
            lines.append(f"❌ {tf}: 文件不存在")
            continue
        try:
            content = fp.read_text("utf-8")
        except Exception:
            lines.append(f"❌ {tf}: 无法读取")
            continue

        # 1. 语法检查
        if tf.endswith(".vue"):
            # .vue 文件不逐文件用 esbuild 检查（esbuild 不认 SFC 语法，会误报）
            # SFC 语法正确性由 integ 层的 vite build 统一验证
            lines.append(f"📋 {tf}: SFC 语法由 integ 层 vite build 验证")
        elif tf.endswith(".js") and "src/" in tf:
            import subprocess
            r = subprocess.run(f"npx esbuild {str(fp)} --format=esm --log-level=error --outfile={ws_path}/.esbuild-pre-check.js",
                capture_output=True, text=True, shell=True, timeout=30, cwd=str(ws_path),
                encoding="utf-8", errors="replace")
            if r.returncode != 0:
                lines.append(f"❌ {tf}: ESM语法错误: {(r.stderr or '')[:200]}")
            else:
                lines.append(f"✅ {tf}: ESM 语法通过")
        elif tf.endswith(".js"):
            import subprocess
            r = subprocess.run(["node", "--check", str(fp)], capture_output=True, text=True,
                             timeout=10, cwd=str(ws_path), encoding="utf-8", errors="replace")
            if r.returncode != 0:
                lines.append(f"❌ {tf}: CJS语法错误: {(r.stderr or '')[:200]}")
            else:
                lines.append(f"✅ {tf}: CJS 语法通过 (node --check)")

        # 2. CJS 禁止（src/ 下）
        if "src/" in tf and tf.endswith(".js"):
            has_cjs = "module.exports" in content or "require(" in content
            if has_cjs:
                lines.append(f"❌ {tf}: 包含 CJS 语法 (require/module.exports)，前端必须使用 ESM")

        # 3. 导出分析
        if tf.endswith(".js"):
            actual = set(_re.findall(r'export (?:async\s+)?function\s+(\w+)', content))
            actual.update(_re.findall(r'export\s+const\s+(\w+)\s*=', content))
            lines.append(f"📋 {tf}: 实际导出 {len(actual)} 个: {', '.join(sorted(actual)) if actual else '(无)'}")

        # 4. checkPoints 对照
        if task is not None:
            checkpoints = task.get("checkPoints", [])
            cp_issues = []
            for i, cp in enumerate(checkpoints):
                m = _re.search(r'导出\s+(\w+)\s*\(', cp)
                if m:
                    expected_name = m.group(1)
                    if tf.endswith(".js"):
                        content_check = content
                        if expected_name not in content_check:
                            cp_issues.append(f"  ❌ checkPoint#{i+1}: 要求导出 '{expected_name}' — 文件中不存在")
                        else:
                            cp_issues.append(f"  ✅ checkPoint#{i+1}: '{expected_name}' 存在")
            if cp_issues:
                lines.append(f"📋 {tf}: checkPoints 对照结果:")
                lines.extend(cp_issues)

    # 5. 交叉检查（前端/peer_deps）
    if task is not None and layer in ("frontend", "peer_deps"):
        mismatches = _check_export_import_names_raw(ws_path, task)
        if mismatches:
            lines.append(f"\n📋 交叉导入检查: 发现 {len(mismatches)} 个 import/export 不匹配:")
            for m in mismatches:
                lines.append(f"  ❌ {m}")

    # 5b. 死路由检查（frontend / integ 层）
    if task is not None and layer in ("frontend", "integ"):
        dead = _fix_dead_routes(ws_path)
        if dead:
            lines.append(f"\n📋 死路由自动修复: 注释了 {len(dead)} 个指向不存在文件的懒加载:")
            for d in dead:
                lines.append(f"  ✅ {d}")

    # 5c. npm 包导出名检查（frontend / integ 层）
    if task is not None and layer in ("frontend", "integ"):
        npm_export_issues = _check_npm_exports(ws_path)
        if npm_export_issues:
            lines.append(f"\n📋 npm 包导出检查: 发现 {len(npm_export_issues)} 个无效导入:")
            for ne in npm_export_issues:
                lines.append(f"  ❌ {ne}")

    # 5c. 🆕 端点覆盖检查（api/backend_proc/logic 层）：比对 route 文件注册的端点 vs 前端 API 模块的调用
    if task is not None and layer in ("api", "backend_proc", "logic"):
        route_files = [tf for tf in target_files if 'routes/' in tf]
        api_files = [tf for tf in target_files if 'src/api/' in tf]
        if route_files and api_files:
            coverage = _check_endpoint_coverage(ws_path, route_files, api_files)
            if coverage:
                lines.append(f"\n📋 端点覆盖检查: {coverage}")

    # 6. CJS require 链检查（仅后端 JS 层，db/infra 层无 JS 产出不检查）
    _cjs_layers = {"backend_proc", "logic", "api", "peer_deps", "scenario", "integ"}
    if task is not None and layer in _cjs_layers:
        broken = _check_cjs_require_chain(ws_path)
        if broken:
            lines.append(f"\n📋 CJS require 链断裂: 发现 {len(broken)} 处:")
            for b in broken[:10]:
                lines.append(f"  ❌ {b}")

    # npm 依赖检查: infra 全局生成，peer_deps/ integ 按类型校验
    if task is not None and layer in ("infra", "integ"):
        # infra/integ: 全量检查（infra 生成 package.json，integ 最终兜底）
        dep_issues = _check_npm_dependencies(ws_path)
        if dep_issues:
            lines.append(f"\n📋 npm 依赖检查: 发现 {len(dep_issues)} 个缺失:")
            for d in dep_issues:
                lines.append(f"  ❌ {d}")
        # 🆕 infra 层专属: package.json scripts 字段验证
        if layer == "infra":
            pkg_script_issues = _check_package_json_scripts(ws_path)
            if pkg_script_issues:
                lines.append(f"\n📋 package.json scripts 检查: 发现 {len(pkg_script_issues)} 个问题:")
                for pi in pkg_script_issues:
                    lines.append(f"  ❌ {pi}")
    elif task is not None and layer == "peer_deps":
        # peer_deps: 只检查本任务管辖的文件类型（前端只看 src/，后端只看 routes/controllers/services/）
        frontend_files = [tf for tf in target_files if tf.startswith("src/")]
        backend_files = [tf for tf in target_files if any(tf.startswith(d) for d in ("routes/", "controllers/", "services/", "middleware/", "config/", "utils/", "queues/", "jobs/"))]
        dep_issues = _check_npm_dependencies_scoped(ws_path, frontend=bool(frontend_files), backend=bool(backend_files))
        if dep_issues:
            scope_label = "前端" if frontend_files else "后端" if backend_files else "全量"
            lines.append(f"\n📋 npm 依赖检查({scope_label}): 发现 {len(dep_issues)} 个缺失:")
            for d in dep_issues:
                lines.append(f"  ❌ {d}")

    # 🆕 前端层: UI 色板扫描（从 Memory/ui_styles/_global.md 动态读取色板）
    if task is not None and layer == "frontend":
        ui_issues = _check_ui_colors(ws_path, target_files)
        if ui_issues:
            lines.append(f"\n📋 UI 色板检查 (Memory/ui_styles/): 发现 {len(ui_issues)} 个不在色板内的颜色:")
        # 🆕 图片路径检查：img src 禁止硬编码 https:// URL
        img_issues = _check_image_sources(ws_path, target_files)
        if img_issues:
            lines.append(f"\n📋 图片路径检查 (禁止硬编码 URL): 发现 {len(img_issues)} 个问题:")
            for ii in img_issues[:10]:
                lines.append(f"  ❌ {ii}")
            for ui in ui_issues[:15]:
                lines.append(f"  ⚠️ {ui}")

    # 🆕 前端层: npx vite build 找错，只报本任务 targetFiles 内的
    if task is not None and layer == "frontend":
        vite_issues = _check_vite_for_task(ws_path, target_files)
        if vite_issues:
            lines.append(f"\n📋 vite build 检查(本任务文件): 发现 {len(vite_issues)} 个问题:")
            for vi in vite_issues:
                lines.append(f"  ❌ {vi}")

    # 🆕 peer_deps 后端: node app.js 找错，只报本任务 targetFiles 内的
    if task is not None and layer == "peer_deps":
        be_files = [tf for tf in target_files if any(tf.startswith(d) for d in ("routes/", "controllers/", "services/", "middleware/", "config/", "utils/"))]
        if be_files:
            node_issues = _check_node_app_for_task(ws_path, target_files)
            if node_issues:
                lines.append(f"\n📋 node app.js 检查(本任务文件): 发现 {len(node_issues)} 个问题:")
                for ni in node_issues:
                    lines.append(f"  ❌ {ni}")

    # integ 层: 只检查路由注册 + 环境配置（其他由专属静态层负责）
    if task is not None and layer == "integ":
        # 1. require 路径深度: routes/ 下所有文件的 require() 相对路径是否正确
        depth_issues = _check_require_path_depth(ws_path)
        if depth_issues:
            lines.append(f"\n📋 require 路径深度检查: 发现 {len(depth_issues)} 个问题:")
            for di in depth_issues:
                lines.append(f"  ❌ {di}")

        # 2. 后端路由注册: app.js 中 require 的路由文件是否存在
        route_files_ok, route_file_issues = _check_app_route_files(ws_path)
        if route_file_issues:
            lines.append(f"\n📋 app.js 路由文件检查: 发现 {len(route_file_issues)} 个问题:")
            for ri in route_file_issues:
                lines.append(f"  ❌ {ri}")

        # 2. 前端路由: 懒加载路径是否存在
        router_issues = _check_router_components(ws_path)
        if router_issues:
            lines.append(f"\n📋 前端路由检查: 发现 {len(router_issues)} 个问题:")
            for ri in router_issues:
                lines.append(f"  ❌ {ri}")

        # 2b. 🆕 前端路由缺漏: src/pages/ 下 .vue 文件是否全部注册到 router
        missing = _check_unregistered_pages(ws_path)
        if missing:
            lines.append(f"\n📋 前端路由缺漏: {len(missing)} 个 .vue 页面未注册到 router/index.js:")
            for m in missing:
                lines.append(f"  ❌ {m}")

        # 2c. 🆕 后端路由缺漏: routes/ 下 .js 文件是否全部注册到 app.js
        missing_routes = _check_unregistered_backend_routes(ws_path)
        if missing_routes:
            lines.append(f"\n📋 后端路由缺漏: {len(missing_routes)} 个 routes/*.js 未在 app.js 中注册:")
            for m in missing_routes:
                lines.append(f"  ❌ {m}")

        # 3. 第三方服务扫描: 代码中引用的 process.env.X → 哪些服务需要配置
        service_issues = _scan_third_party_services(ws_path)
        if service_issues:
            lines.append(f"\n📋 第三方服务扫描: 发现 {len(service_issues)} 个需要配置的服务:")
            for si in service_issues:
                lines.append(f"  🔧 {si}")

        # 4. 🆕 环境配置: 注入根 .env.example 真实值 → agent 写 .env → 同步四文件
        root_env = project_root / ".env.example"
        if root_env.exists():
            # 全部传入，agent 自己做交集：代码引用的变量 ∩ 根配置有的 → 填真实值
            clean_env = []
            for line in root_env.read_text('utf-8', errors='replace').split('\n'):
                s = line.strip()
                if s and not s.startswith('#') and '=' in s:
                    k, v = s.split('=', 1)
                    clean_val = v.split('#')[0].strip().strip('"').strip("'")
                    clean_env.append(f"{k.strip()}={clean_val}")
            lines.append(f"\n## 🛑 根 .env.example（共 {len(clean_env)} 个变量，与代码扫描结果取交集填真实值）\n```\n" + "\n".join(clean_env) + "\n```")
            lines.append("\n🛑 .env 写入铁律：create_files 时 content 字符串中每个 KEY=VALUE 上一行必须有 # 注释。例: '# 数据库主机地址\\nDB_HOST=localhost'。禁止裸变量无注释。")
        env_issues = _check_env_alignment(ws_path)
        if env_issues:
            lines.append(f"\n📋 环境变量对齐（代码引用 ↔ .env）: 发现 {len(env_issues)} 个问题:")
            for ei in env_issues:
                lines.append(f"  ❌ {ei}")

        # 5. 🆕 数据库初始化: 表是否创建、种子数据是否插入
        db_issues = _check_database_ready(ws_path)
        if db_issues:
            lines.append(f"\n📋 数据库初始化检查: 发现 {len(db_issues)} 个问题:")
            for di in db_issues:
                lines.append(f"  ❌ {di}")

        # 5b. 🆕 DB 表存在验证: init-db.js 执行后 SHOW TABLES 对比 DDL
        table_issues = _check_db_tables_exist(ws_path)
        if table_issues:
            lines.append(f"\n📋 DB 表存在验证 (SHOW TABLES vs DDL): 发现 {len(table_issues)} 个问题:")
            for ti in table_issues:
                lines.append(f"  ❌ {ti}")

        # 6. 🆕 后端全链加载: node -e \"require('./app')\" 不崩溃
        app_load_issues = _check_app_load(ws_path)
        if app_load_issues:
            lines.append(f"\n📋 app.js 加载检查: 发现 {len(app_load_issues)} 个问题:")
            for ai in app_load_issues:
                lines.append(f"  ❌ {ai}")

        # 7. 🆕 前端构建: npx vite build 不报错
        vite_issues = _check_vite_build(ws_path)
        if vite_issues:
            lines.append(f"\n📋 vite build 检查: 发现 {len(vite_issues)} 个问题:")
            for vi in vite_issues:
                lines.append(f"  ❌ {vi}")

        # 8. 🆕 路由名交叉校验: router.push({name}) vs 实际路由定义
        route_name_issues = _check_route_name_refs(ws_path)
        if route_name_issues:
            lines.append(f"\n📋 路由名交叉校验: 发现 {len(route_name_issues)} 个问题:")
            for ri in route_name_issues:
                lines.append(f"  ❌ {ri}")

    # 6. DDL vs 契约对比（db 层：Python 逐字段对照，减轻 Agent 负担）
    if task is not None and layer == "db":
        # 🆕 SQL 基础语法检查（括号配对/分号/关键字 — 确定性检查，不做完整 SQL 解析）
        sql_issues = _check_sql_basic_syntax(ws_path, task)
        if sql_issues:
            lines.append(f"\n📋 SQL 基础语法检查: 发现 {len(sql_issues)} 个问题:")
            for si in sql_issues:
                lines.append(f"  ❌ {si}")
        ddl_issues = _check_ddl_vs_contract(ws_path, task)
        if ddl_issues:
            lines.append(f"\n📋 DDL 与 enginee 契约对比: 发现 {len(ddl_issues)} 处差异:")
            for di in ddl_issues:
                lines.append(f"  ❌ {di}")

        # 7. 种子数据检查（所有 db 层：Python 验证 seed JSON 完整性）
        seed_issues = _check_seed_files(ws_path, task)
        if seed_issues:
            lines.append(f"\n📋 种子数据检查: 发现 {len(seed_issues)} 个问题:")
            for si in seed_issues:
                lines.append(f"  ❌ {si}")

    return "\n".join(lines) if lines else ""



def _check_sql_basic_syntax(ws_path: Path, task: dict) -> list:
    """检查 SQL 文件的基础语法：括号配对、分号、关键字拼写、重复索引/列名。
    db 层职责：SQL 文件是 db 的产出，基础语法确定性检查由 Python 完成。
    不做完整 SQL 解析——那是 MySQL 的工作。
    """
    import re as _re
    issues = []
    for tf in task.get("targetFiles", []):
        if not tf.endswith(".sql"):
            continue
        fp = ws_path / tf
        if not fp.exists():
            continue
        try:
            content = fp.read_text("utf-8", errors="replace")
        except Exception:
            continue

        # 1. 括号配对检查
        depth = 0
        for i, ch in enumerate(content):
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            if depth < 0:
                line_no = content[:i].count('\n') + 1
                issues.append(f"{tf}:{line_no}: 多余的 ')' — 括号不配对")
                depth = 0
        if depth > 0:
            issues.append(f"{tf}: 括号未闭合（多了 {depth} 个 '('）")

        # 2. 每个 CREATE TABLE 逐表检查
        for tm in _re.finditer(
            r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?\s*\((.*?)\)\s*ENGINE[^;]*',
            content, _re.IGNORECASE | _re.DOTALL
        ):
            tbl_name = tm.group(1)
            body = tm.group(2)

            # 2a. 🆕 重复索引/约束名 — MySQL 会直接拒绝建表
            idx_names = []
            for im in _re.finditer(r'(?:UNIQUE\s+)?(?:KEY|INDEX)\s+`(\w+)`', body, _re.IGNORECASE):
                idx_names.append(im.group(1))
            for im in _re.finditer(r'CONSTRAINT\s+`(\w+)`', body, _re.IGNORECASE):
                idx_names.append(im.group(1))
            seen_idx = set()
            for name in idx_names:
                if name in seen_idx:
                    issues.append(f"{tf}: 表 `{tbl_name}` 重复索引/约束名 `{name}` — MySQL 拒绝建表")
                seen_idx.add(name)

            # 2b. 🆕 重复列名
            col_names = _re.findall(r'`(\w+)`\s+\w+', body)
            seen_col = set()
            for cn in col_names:
                if cn in seen_col:
                    issues.append(f"{tf}: 表 `{tbl_name}` 重复列名 `{cn}`")
                seen_col.add(cn)

            # 2c. 🆕 AUTO_INCREMENT 列必须有 PRIMARY KEY
            has_auto = bool(_re.search(r'AUTO_INCREMENT', body, _re.IGNORECASE))
            has_pk = bool(_re.search(r'PRIMARY\s+KEY', body, _re.IGNORECASE))
            if has_auto and not has_pk:
                issues.append(f"{tf}: 表 `{tbl_name}` AUTO_INCREMENT 列缺少 PRIMARY KEY — MySQL 拒绝建表")

            # 2d. 🆕 尾随逗号
            body_stripped = _re.sub(r'--.*', '', body)
            if _re.search(r',\s*$', body_stripped.strip()):
                issues.append(f"{tf}: 表 `{tbl_name}` ) 前有尾随逗号 — SQL 语法错误")

            # 2e. 末尾分号检查
            stmt_end = tm.end()
            if stmt_end < len(content) and content[stmt_end] != ';':
                line_no = content[:stmt_end].count('\n') + 1
                issues.append(f"{tf}:{line_no}: 表 `{tbl_name}` CREATE TABLE 末尾缺分号")

        # 3. 常见关键字拼写检查（LLM 容易写错）
        typos = {
            r'\bAUTO_INCREAMENT\b': 'AUTO_INCREMENT',
            r'\bPRIAMRY\b': 'PRIMARY',
            r'\bFORIEGN\b': 'FOREIGN',
            r'\bREFERECNES\b': 'REFERENCES',
            r'\bVACHAR\b': 'VARCHAR',
        }
        for pattern, correct in typos.items():
            for m in _re.finditer(pattern, content, _re.IGNORECASE):
                line_no = content[:m.start()].count('\n') + 1
                issues.append(f"{tf}:{line_no}: 疑似拼写错误 '{m.group(0)}' → 应为 '{correct}'")

    return issues



def _check_ddl_vs_contract(ws_path: Path, task: dict) -> list:
    """对比 DDL SQL 文件与 task JSON 中对应的 contracts.model 契约。
    只加载本任务 DDL 涉及的表契约，不加载全部。
    逐字段检查: 表名、字段名、类型、NOT NULL、DEFAULT、INDEX、FOREIGN KEY。
    返回问题列表。"""
    import re as _re, json as _json
    issues = []

    # 1. 先解析 DDL 文件，提取本任务管辖的表名
    ddl_tables = {}
    ddl_table_names = set()
    for tf in task.get("targetFiles", []):
        if not tf.endswith(".sql"):
            continue
        fp = ws_path / tf
        if not fp.exists():
            continue
        content = fp.read_text("utf-8", errors="replace")

        for m in _re.finditer(
            r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?\s*\((.*?)\)\s*ENGINE',
            content, _re.IGNORECASE | _re.DOTALL
        ):
            tbl_name = m.group(1)
            ddl_table_names.add(tbl_name.lower())
            body = m.group(2)
            fields = []
            indexes = []
            fks = []

            for line in body.split('\n'):
                line = line.strip().rstrip(',').strip()
                if not line or line.startswith('--'):
                    continue

                # PRIMARY KEY / INDEX / KEY
                idx_m = _re.match(
                    r'(?:PRIMARY\s+KEY|(?:UNIQUE\s+)?(?:KEY|INDEX))\s+`?(\w+)`?\s*\(([^)]+)\)',
                    line, _re.IGNORECASE
                )
                if idx_m:
                    idx_name = idx_m.group(1).lower()
                    cols = [c.strip().strip('`') for c in idx_m.group(2).split(',')]
                    uniq = 'primary' in line.lower() or 'unique' in line.lower()
                    indexes.append({
                        "name": "PRIMARY" if 'primary' in line.lower() else idx_name,
                        "columns": cols, "unique": uniq
                    })
                    continue

                # FOREIGN KEY
                fk_m = _re.match(
                    r'(?:CONSTRAINT\s+`?\w+`?\s+)?FOREIGN\s+KEY\s*\(`?(\w+)`?\)\s*REFERENCES\s+`?(\w+)`?\s*\(`?(\w+)`?\)',
                    line, _re.IGNORECASE
                )
                if fk_m:
                    fks.append({
                        "columns": [fk_m.group(1)],
                        "refTable": fk_m.group(2),
                        "refColumns": [fk_m.group(3)]
                    })
                    continue

                # 字段: `name` TYPE CONSTRAINTS...
                col_m = _re.match(r'`(\w+)`\s+(\w+(?:\([^)]+\))?)\s*(.*)', line)
                if col_m:
                    name = col_m.group(1)
                    col_type = col_m.group(2).upper()
                    raw = (col_m.group(3) or "").strip().upper()
                    raw = _re.sub(
                        r'CHARACTER\s+SET\s+\w+|COLLATE\s+\w+',
                        '', raw, flags=_re.IGNORECASE
                    ).strip()
                    fields.append({"name": name, "type": col_type, "constraints": raw})

            if fields:
                ddl_tables[tbl_name.lower()] = {
                    "name": tbl_name, "file": tf,
                    "fields": fields, "indexes": indexes, "fks": fks,
                }

    if not ddl_tables:
        return issues

    # 2. 加载 task JSON contracts.model，只取 DDL 中存在的表契约
    task_dir = ws_path / "task"
    if not task_dir.exists():
        return issues
    task_files = sorted(task_dir.glob("task_*.json"))
    if not task_files:
        return issues
    try:
        task_data = _json.loads(task_files[-1].read_text("utf-8"))
    except Exception:
        return issues
    models = task_data.get("contracts", {}).get("model", [])
    if not models:
        return issues

    # 归一化 model 字段格式 → 只保留 DDL 中存在的表
    # task JSON: {name, type, nullable(bool), unique(bool), default(str), primary(bool), autoIncrement(bool)}
    # 目标格式: {name, type, "constraints": "NOT NULL UNIQUE DEFAULT 'x' AUTO_INCREMENT"}
    tables_contract = []
    for model in models:
        if not isinstance(model, dict):
            continue
        tbl_name = model.get("tableName", "").lower()
        if tbl_name not in ddl_table_names:
            continue  # 不是本任务管辖的表，跳过
        tbl = {"name": model.get("tableName", ""), "fields": [], "indexes": [], "foreignKeys": []}
        for f in model.get("fields", []):
            if not isinstance(f, dict):
                continue
            constraints_parts = []
            if not f.get("nullable", True):
                constraints_parts.append("NOT NULL")
            if f.get("unique"):
                constraints_parts.append("UNIQUE")
            if f.get("default") is not None:
                constraints_parts.append(f"DEFAULT {f['default']}")
            if f.get("primary"):
                constraints_parts.append("PRIMARY KEY")
            if f.get("autoIncrement"):
                constraints_parts.append("AUTO_INCREMENT")
            tbl["fields"].append({
                "name": f.get("name", ""),
                "type": (f.get("type") or "").upper(),
                "constraints": " ".join(constraints_parts),
            })
        for idx in model.get("indexes", []):
            if isinstance(idx, dict):
                tbl["indexes"].append({"name": idx.get("name", ""), "columns": idx.get("columns", [])})
        for fk in model.get("foreignKeys", []):
            if isinstance(fk, dict):
                col = fk.get("column", "")
                tbl["foreignKeys"].append({
                    "columns": [col] if isinstance(col, str) else col,
                    "refTable": fk.get("refTable", ""),
                    "refColumns": [fk.get("refColumn", "")] if fk.get("refColumn") else [],
                })
        if tbl["fields"]:
            tables_contract.append(tbl)

    if not tables_contract:
        return issues

    # 索引契约表: name -> contract
    contract_by_name = {}
    for tbl in tables_contract:
        if isinstance(tbl, dict):
            contract_by_name[tbl.get("name", "").lower()] = tbl

    # 3. 逐表对照
    for tbl_name_lower, ddl_tbl in ddl_tables.items():
        ct = contract_by_name.get(tbl_name_lower)
        if not ct:
            issues.append(f"DDL 有表 `{ddl_tbl['name']}` 但契约中未定义")
            continue

        ct_fields = ct.get("fields", [])
        if isinstance(ct_fields, dict):
            ct_fields = [{"name": k, **v} for k, v in ct_fields.items()]

        ct_field_map = {}
        for f in ct_fields:
            if isinstance(f, dict):
                ct_field_map[f.get("name", "").lower()] = f
            elif isinstance(f, str):
                ct_field_map[f.lower()] = {"name": f}
        ddl_field_map = {f["name"].lower(): f for f in ddl_tbl["fields"]}

        # 契约有但 DDL 缺
        for fn_lower, cf in ct_field_map.items():
            if fn_lower not in ddl_field_map:
                issues.append(
                    f"`{ddl_tbl['name']}`.`{cf.get('name', fn_lower)}` 契约要求但 DDL 缺失")
                continue
            df = ddl_field_map[fn_lower]
            ct_type = (cf.get("type") or "").upper() if isinstance(cf, dict) else ""
            ct_con = (cf.get("constraints") or "").upper() if isinstance(cf, dict) else ""

            # 类型（归一化比较: VARCHAR(N) → VARCHAR）
            if ct_type:
                norm_ct = _re.sub(r'\(\d+\)', '', ct_type)
                norm_ddl = _re.sub(r'\(\d+\)', '', df["type"])
                if norm_ct != norm_ddl:
                    issues.append(
                        f"`{ddl_tbl['name']}`.`{df['name']}` 类型: 契约={ct_type} DDL={df['type']}")

            # 约束
            ddl_con = df.get("constraints", "")
            if ct_con:
                for kw in ["NOT NULL", "DEFAULT", "UNIQUE", "AUTO_INCREMENT"]:
                    if kw in ct_con and kw not in ddl_con:
                        issues.append(
                            f"`{ddl_tbl['name']}`.`{df['name']}` 缺约束 {kw}（契约要求）")

        # DDL 有但契约缺
        for fn_lower, df in ddl_field_map.items():
            if fn_lower not in ct_field_map:
                issues.append(
                    f"`{ddl_tbl['name']}`.`{df['name']}` DDL 有此字段但契约中未定义")

        # 索引
        ct_indexes = ct.get("indexes", [])
        if isinstance(ct_indexes, dict):
            ct_indexes = [{"name": k, **v} for k, v in ct_indexes.items()]
        ct_idx_names = set()
        for idx in ct_indexes:
            if isinstance(idx, dict):
                ct_idx_names.add(idx.get("name", "").lower())
            elif isinstance(idx, str):
                ct_idx_names.add(idx.lower())
        ddl_idx_names = set(idx["name"].lower() for idx in ddl_tbl["indexes"])
        for iname in ct_idx_names:
            if iname and iname not in ddl_idx_names:
                issues.append(f"`{ddl_tbl['name']}` 缺索引 {iname}（契约要求）")

        # FK
        ct_fks = ct.get("foreignKeys", [])
        if isinstance(ct_fks, dict):
            ct_fks = [{"columns": [k], **v} for k, v in ct_fks.items()]
        ddl_fk_sigs = set(
            (tuple(fk["columns"]), fk["refTable"].lower()) for fk in ddl_tbl["fks"])
        for cfk in ct_fks:
            if isinstance(cfk, dict):
                cols = cfk.get("columns", cfk.get("column", []))
                if isinstance(cols, str):
                    cols = [cols]
                ref = (cfk.get("refTable") or "").lower()
                if (tuple(cols), ref) not in ddl_fk_sigs:
                    issues.append(
                        f"`{ddl_tbl['name']}` 缺 FK({', '.join(cols)}) -> {cfk.get('refTable','?')}")

    # 契约有但 DDL 无
    for tn, ct in contract_by_name.items():
        if tn not in ddl_tables:
            issues.append(f"契约定义表 `{ct.get('name', tn)}` 但 DDL 中不存在")

    return issues



def _check_seed_files(ws_path: Path, task: dict) -> list:
    """检查种子数据文件：存在性 + JSON 有效性 + 列名与 DDL 对齐 + FK 引用一致性。
    返回问题列表。"""
    import json as _json, re as _re
    issues = []
    target_files = task.get("targetFiles", [])

    # 收集所有 seed JSON 文件
    seed_files = [f for f in target_files if "seed/" in f and f.endswith(".json")]
    if not seed_files:
        return issues

    # 扫描所有 DDL 表名和列名
    ddl_columns = {}  # {table_name: {col_name}}
    for sf in sorted(ws_path.glob("database/schema/*.sql")):
        content = sf.read_text("utf-8", errors="replace")
        for m in _re.finditer(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?\s*\((.*?)\)\s*ENGINE",
                              content, _re.IGNORECASE | _re.DOTALL):
            table = m.group(1)
            body = m.group(2)
            cols = set()
            for cm in _re.finditer(r"`(\w+)`\s+\w+", body):
                cols.add(cm.group(1))
            ddl_columns[table] = cols

    # 逐 seed 文件检查
    all_seed_ids = {}  # {table: [ids]} 用于 FK 交叉校验
    for seed_rel in seed_files:
        fp = ws_path / seed_rel
        table_name = seed_rel.replace("\\", "/").split("/")[-1].replace(".json", "")

        # 1. 文件存在
        if not fp.exists():
            issues.append(f"{seed_rel}: 文件不存在")
            continue
        if fp.stat().st_size == 0:
            issues.append(f"{seed_rel}: 文件为空")
            continue

        # 2. JSON 有效性
        try:
            rows = _json.loads(fp.read_text("utf-8"))
        except Exception as e:
            issues.append(f"{seed_rel}: JSON 解析失败 — {str(e)[:80]}")
            continue
        if not isinstance(rows, list):
            issues.append(f"{seed_rel}: 非数组类型（应为 JSON 数组）")
        elif len(rows) == 0:
            # 空数组合法：运行时动态生成的表（如 payments）不需要种子数据
            pass
            continue

        # 3. 列名与 DDL 对齐
        if table_name in ddl_columns:
            ddl_cols = ddl_columns[table_name]
            seed_cols = set(rows[0].keys())
            extra = seed_cols - ddl_cols
            missing = ddl_cols - seed_cols - {"created_at", "updated_at"}  # 自动时间戳可省略
            if extra:
                issues.append(f"{seed_rel}: 多余列 {sorted(extra)}（不在 {table_name} DDL 中）")
            if missing:
                issues.append(f"{seed_rel}: 缺列 {sorted(missing)}（{table_name} DDL 中有但 seed 没有）")

        # 4. 记录 ID 用于 FK 交叉校验
        ids = [r.get("id") for r in rows if "id" in r]
        all_seed_ids[table_name] = ids

        # 5. 行数检查
        if len(rows) < 2:
            issues.append(f"{seed_rel}: 只有 {len(rows)} 行（至少需要 2 行演示数据）")

    # 6. FK 引用一致性（跨文件检查）
    for seed_rel in seed_files:
        fp = ws_path / seed_rel
        if not fp.exists():
            continue
        try:
            raw = _json.loads(fp.read_text("utf-8"))
        except Exception:
            continue
        # 兼容包装对象 {"table": [...]} 和裸数组 [...] 两种格式
        if isinstance(raw, list):
            rows = raw
        elif isinstance(raw, dict):
            arr_key = next((k for k in raw if isinstance(raw[k], list)), None)
            rows = raw[arr_key] if arr_key else []
        else:
            continue
        if not isinstance(rows, list):
            continue
        # 检查每一行的 FK 字段是否引用了有效的父表 ID
        for i, row in enumerate(rows):
            for key, val in row.items():
                if key.endswith("_id") and val is not None and isinstance(val, (int, float)):
                    parent_table = key.replace("_id", "")  # user_id → user
                    # 尝试单复数匹配
                    candidates = [parent_table, parent_table + "s"]
                    for candidate in candidates:
                        if candidate in all_seed_ids and all_seed_ids[candidate]:
                            if int(val) not in all_seed_ids[candidate]:
                                issues.append(
                                    f"{seed_rel}[{i}].{key}={val} 引用了不存在的 {candidate}.id"
                                    f"（可用 ID: {all_seed_ids[candidate][:5]}）")
                            break

    return issues



def _check_cjs_require_chain(ws: Path) -> list:
    """检查所有后端 .js 文件的 require() 路径是否可解析。"""
    import re as _re
    broken = []
    for root, dirs, files in os.walk(str(ws)):
        dirs[:] = [d for d in dirs if d not in ('node_modules', '.git', '.meta', 'test', 'Memory', 'doc', 'report', 'src')]
        for fn in files:
            if not fn.endswith('.js'):
                continue
            fp = Path(root) / fn
            try:
                content = fp.read_text('utf-8', errors='replace')
            except Exception:
                continue
            for m in _re.finditer(r"""require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)""", content):
                target = m.group(1)
                if not target.startswith('.'):
                    continue  # npm 包，跳过
                resolved = (fp.parent / target).resolve()
                found = resolved.exists()
                if not found:
                    for ext in ['.js', '/index.js']:
                        if Path(str(resolved) + ext).exists():
                            found = True
                            break
                if not found:
                    rel_src = str(fp.relative_to(ws)).replace('\\', '/')
                    broken.append(f"{rel_src} require('{target}') → 文件不存在")
                elif found:
                    # 文件存在 → 检查解构导入的名称是否真实导出
                    target_path = resolved if resolved.exists() else Path(str(resolved) + '.js') if Path(str(resolved) + '.js').exists() else resolved
                    if not target_path.exists():
                        continue
                    try:
                        target_content = target_path.read_text('utf-8', errors='replace')
                    except Exception:
                        continue
                    # 提取目标文件的所有导出名
                    t_exports = set(_re.findall(r'module\.exports\.(\w+)\s*=', target_content))
                    m_obj = _re.search(r'module\.exports\s*=\s*\{([^}]+)\}', target_content)
                    if m_obj:
                        t_exports.update(_re.findall(r'(\w+)', m_obj.group(1)))
                    # 检查解构 require 的名称
                    line_start = content.rfind('\n', 0, m.start()) + 1
                    line_end = content.find('\n', m.end())
                    req_line = content[line_start:line_end if line_end != -1 else len(content)]
                    dest_match = _re.search(r'(?:const|let|var)\s*\{([^}]+)\}\s*=\s*require', req_line)
                    if dest_match:
                        for name in dest_match.group(1).split(','):
                            name = name.strip().split(':')[0].strip().split(' as ')[0].strip()
                            if name and name not in t_exports:
                                rel_src = str(fp.relative_to(ws)).replace('\\', '/')
                                rel_target = str(target_path.relative_to(ws)).replace('\\', '/')
                                broken.append(f"{rel_src} require {{{name}}} from '{target}' → {rel_target} 未导出（实际导出: {', '.join(sorted(t_exports)[:8]) or '(无)'}）")

    # 🆕 循环依赖检测（peer_deps 职责：require 图是 peer_deps 的核心领域）
    _cycles = _detect_require_cycles(ws)
    if _cycles:
        broken.append(f"\n🛑 循环依赖检测: 发现 {len(_cycles)} 个环:")
        for cycle in _cycles[:5]:
            broken.append(f"  ❌ {' → '.join(cycle)}")

    return broken



def _detect_require_cycles(ws: Path) -> list:
    """在 require 图中检测循环依赖。DFS 三色标记法。
    返回环的列表，每个环是文件路径列表。
    """
    import re as _re

    # 1. 构建邻接表: {源文件相对路径: [目标文件相对路径]}
    graph = {}
    for root, dirs, files in os.walk(str(ws)):
        dirs[:] = [d for d in dirs if d not in ('node_modules', '.git', '.meta', 'test', 'Memory', 'doc', 'report', 'src')]
        for fn in files:
            if not fn.endswith('.js'):
                continue
            fp = Path(root) / fn
            rel = str(fp.relative_to(ws)).replace('\\', '/')
            if rel not in graph:
                graph[rel] = []
            try:
                content = fp.read_text('utf-8', errors='replace')
            except Exception:
                continue
            for m in _re.finditer(r"""require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)""", content):
                target = m.group(1)
                if not target.startswith('.'):
                    continue
                resolved = (fp.parent / target).resolve()
                found = resolved.exists()
                if not found:
                    for ext in ['.js', '/index.js']:
                        p = Path(str(resolved) + ext)
                        if p.exists():
                            resolved = p
                            found = True
                            break
                if found:
                    target_rel = str(resolved.relative_to(ws)).replace('\\', '/')
                    graph[rel].append(target_rel)

    # 2. DFS 三色标记找环
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in graph}
    parent = {}

    def dfs_find_cycle(node):
        color[node] = GRAY
        for neighbor in graph.get(node, []):
            if neighbor not in color:
                continue  # 外部文件（npm 包），跳过
            if color[neighbor] == GRAY:
                # 找到环：回溯 parent 链
                cycle = [neighbor, node]
                cur = node
                while parent.get(cur) and parent[cur] != neighbor:
                    cur = parent[cur]
                    cycle.append(cur)
                cycle.append(neighbor)
                cycle.reverse()
                return cycle
            if color[neighbor] == WHITE:
                parent[neighbor] = node
                result = dfs_find_cycle(neighbor)
                if result:
                    return result
        color[node] = BLACK
        return None

    cycles = []
    remaining = set(graph.keys())
    while remaining:
        start = next(iter(remaining))
        # 只从入度>0的节点开始（剪枝）
        cycle = dfs_find_cycle(start)
        if cycle:
            cycles.append(cycle)
            # 移除环中所有节点，继续找其他环
            for node in cycle:
                remaining.discard(node)
        else:
            # 移除所有被标记为 BLACK 的节点
            remaining = {n for n in remaining if color.get(n) != BLACK}
            if remaining and start in remaining:
                remaining.discard(start)  # 避免死循环

    return cycles



def _check_export_import_names_raw(ws: Path, task: dict) -> list:
    """返回 import/export 不匹配的原始描述列表（不写 ban）。"""
    import re as _re
    target_files = task.get("targetFiles", [])
    mismatches = []
    truth_exports = _load_frontend_api_exports(ws)

    for tf in target_files:
        fp = ws / tf
        if not fp.exists():
            continue
        content = fp.read_text("utf-8", errors="replace")
        exports = set(_re.findall(r'export (?:async\s+)?function\s+(\w+)', content))
        exports.update(_re.findall(r'export\s+const\s+(\w+)\s*=', content))

        tf_norm = tf.replace("\\", "/")
        for truth_file, truth_names in truth_exports.items():
            if tf_norm.endswith(truth_file.replace("\\", "/").lstrip("src/")) or \
               truth_file.replace("\\", "/").endswith(tf_norm.split("/")[-1]):
                exports.update(truth_names)

        if not exports:
            continue

        rel = tf.replace("\\", "/")
        import_paths = [rel]
        if rel.startswith("src/"):
            import_paths.append("@" + rel[3:])
            import_paths.append("@" + rel[3:-3])

        for vf in ws.glob("src/**/*.vue"):
            vf_content = vf.read_text("utf-8", errors="replace")
            for ip in import_paths:
                ip_no_ext = ip.replace(".js", "")
                for m in _re.finditer(rf"import\s*\{{([^}}]+)\}}\s*from\s*['\"]({_re.escape(ip_no_ext)}|{_re.escape(ip)})(?:\.js)?['\"]", vf_content):
                    for name in m.group(1).split(','):
                        name = name.strip().split(' as ')[0].strip()
                        if name and name not in exports:
                            mismatches.append(f"{vf.relative_to(ws)} 导入 {{{name}}} 但 {tf} 未导出（实际导出: {', '.join(sorted(exports)[:8])}）")
    return mismatches

def _check_npm_dependencies(ws_path: Path) -> list:
    """扫描前端 import + 后端 require 的裸包名，检查是否在 package.json 中。返回问题列表。"""
    import re, json
    issues = []
    pkg_file = ws_path / "package.json"
    if not pkg_file.exists():
        return ["package.json 不存在，无法检查 npm 依赖"]

    pkg = json.loads(pkg_file.read_text("utf-8"))
    all_deps = set(pkg.get("dependencies", {}).keys()) | set(pkg.get("devDependencies", {}).keys())

    # Node.js 内置模块（不需要在 package.json 中）
    node_builtins = {"fs", "path", "http", "https", "crypto", "os", "url", "querystring",
                     "stream", "util", "events", "assert", "buffer", "child_process", "net",
                     "tls", "dns", "zlib", "cluster", "process", "readline", "timers",
                     "string_decoder", "punycode", "domain", "console", "perf_hooks",
                     "worker_threads", "vm", "v8", "async_hooks", "inspector", "trace_events"}

    bare_imports = {}  # {package_name: [file]}
    # 1. 前端 src/ 下的裸包 import（非 @/ 非相对路径）
    for pattern in ["src/**/*.js", "src/**/*.vue"]:
        for fp in ws_path.glob(pattern):
            try:
                content = fp.read_text("utf-8", errors="replace")
            except Exception:
                continue
            for m in re.finditer(r"""from\s+['"]([^@./][^'"]+)['"]""", content):
                pkg_name = m.group(1).split("/")[0]
                bare_imports.setdefault(pkg_name, set()).add(str(fp.relative_to(ws_path)))
            for m in re.finditer(r"""import\s+['"]([^@./][^'"]+)['"]""", content):
                pkg_name = m.group(1).split("/")[0]
                bare_imports.setdefault(pkg_name, set()).add(str(fp.relative_to(ws_path)))

    # 2. 🆕 后端 require() 裸包（非 ./ 非 ../ 开头，非内置模块）
    for d in ["routes", "controllers", "services", "middleware", "config", "utils", "queues", "jobs", "scripts"]:
        dpath = ws_path / d
        if not dpath.exists():
            continue
        for fp in dpath.rglob("*.js"):
            try:
                content = fp.read_text("utf-8", errors="replace")
            except Exception:
                continue
            rel = str(fp.relative_to(ws_path)).replace("\\", "/")
            for m in re.finditer(r"""require\s*\(\s*['\"]([^'"]+)['\"]\s*\)""", content):
                target = m.group(1)
                if target.startswith(".") or target.startswith("/"):
                    continue  # 相对/绝对路径，不是 npm 包
                pkg_name = target.split("/")[0]
                if pkg_name in node_builtins:
                    continue
                bare_imports.setdefault(pkg_name, set()).add(rel)
    # 也检查根目录下的 app.js
    for root_js in ["app.js"]:
        fp = ws_path / root_js
        if fp.exists():
            try:
                content = fp.read_text("utf-8", errors="replace")
            except Exception:
                continue
            for m in re.finditer(r"""require\s*\(\s*['\"]([^'"]+)['\"]\s*\)""", content):
                target = m.group(1)
                if target.startswith("."):
                    continue
                pkg_name = target.split("/")[0]
                if pkg_name in node_builtins:
                    continue
                bare_imports.setdefault(pkg_name, set()).add(root_js)

    missing = {pkg: files for pkg, files in bare_imports.items() if pkg not in all_deps}
    for pkg, files in sorted(missing.items()):
        issues.append(f"npm 依赖缺失: '{pkg}' (imported by {', '.join(sorted(files)[:3])}) — 不在 package.json 中")

    return issues



def _check_npm_dependencies_scoped(ws_path: Path, frontend: bool = True, backend: bool = True) -> list:
    """按类型范围检查 npm 依赖。frontend=仅 src/，backend=仅后端目录。"""
    import re, json
    issues = []
    pkg_file = ws_path / "package.json"
    if not pkg_file.exists():
        return ["package.json 不存在"]

    pkg = json.loads(pkg_file.read_text("utf-8"))
    all_deps = set(pkg.get("dependencies", {}).keys()) | set(pkg.get("devDependencies", {}).keys())
    node_builtins = {"fs", "path", "http", "https", "crypto", "os", "url", "querystring",
                     "stream", "util", "events", "assert", "buffer", "child_process", "net",
                     "tls", "dns", "zlib", "cluster", "process", "readline", "timers",
                     "string_decoder", "domain", "console", "perf_hooks", "worker_threads",
                     "vm", "v8", "async_hooks", "inspector"}

    bare_imports = {}

    if frontend:
        for pattern in ["src/**/*.js", "src/**/*.vue"]:
            for fp in ws_path.glob(pattern):
                try:
                    content = fp.read_text("utf-8", errors="replace")
                except Exception:
                    continue
                rel = str(fp.relative_to(ws_path)).replace("\\", "/")
                for m in re.finditer(r"""from\s+['"]([^@./][^'"]+)['"]""", content):
                    pkg_name = m.group(1).split("/")[0]
                    bare_imports.setdefault(pkg_name, set()).add(rel)
                for m in re.finditer(r"""import\s+['"]([^@./][^'"]+)['"]""", content):
                    pkg_name = m.group(1).split("/")[0]
                    bare_imports.setdefault(pkg_name, set()).add(rel)

    if backend:
        backend_dirs = ["routes", "controllers", "services", "middleware", "config", "utils", "queues", "jobs"]
        for d in backend_dirs:
            dpath = ws_path / d
            if not dpath.exists():
                continue
            for fp in dpath.rglob("*.js"):
                try:
                    content = fp.read_text("utf-8", errors="replace")
                except Exception:
                    continue
                rel = str(fp.relative_to(ws_path)).replace("\\", "/")
                for m in re.finditer(r"""require\s*\(\s*['\"]([^'"]+)['\"]\s*\)""", content):
                    target = m.group(1)
                    if target.startswith("."):
                        continue
                    pkg_name = target.split("/")[0]
                    if pkg_name in node_builtins:
                        continue
                    bare_imports.setdefault(pkg_name, set()).add(rel)
        # app.js
        for root_js in ["app.js"]:
            fp = ws_path / root_js
            if fp.exists():
                try:
                    content = fp.read_text("utf-8", errors="replace")
                except Exception:
                    continue
                for m in re.finditer(r"""require\s*\(\s*['\"]([^'"]+)['\"]\s*\)""", content):
                    target = m.group(1)
                    if target.startswith("."):
                        continue
                    pkg_name = target.split("/")[0]
                    if pkg_name in node_builtins:
                        continue
                    bare_imports.setdefault(pkg_name, set()).add(root_js)

    missing = {pkg: files for pkg, files in bare_imports.items() if pkg not in all_deps}
    for pkg, files in sorted(missing.items()):
        issues.append(f"npm 依赖缺失: '{pkg}' (imported by {', '.join(sorted(files)[:3])}) — 不在 package.json 中")

    return issues



def _check_package_json_scripts(ws_path: Path) -> list:
    """检查 package.json 是否包含必需的 scripts 字段。
    infra 职责：package.json 是 infra 的产出，验证结构正确性。
    不检查 scripts 是否能成功执行（那是 integ 的职责）。
    """
    import json as _json
    issues = []
    pkg_file = ws_path / "package.json"
    if not pkg_file.exists():
        return ["package.json 不存在"]

    try:
        pkg = _json.loads(pkg_file.read_text("utf-8"))
    except Exception:
        return ["package.json JSON 解析失败"]

    scripts = pkg.get("scripts", {})
    if not isinstance(scripts, dict):
        return ["package.json scripts 字段不是对象"]

    required = {
        "db": "数据库脚本（如 node scripts/init-db.js）",
        "backend": "后端启动（如 node app.js）",
        "frontend": "前端启动/构建（如 vite 或 vite build）",
        "test": "测试运行（如 jest）",
    }
    for key, desc in required.items():
        if key not in scripts:
            issues.append(f"package.json scripts 缺 '{key}' 字段（{desc}）")
        elif not scripts[key] or not isinstance(scripts[key], str):
            issues.append(f"package.json scripts.{key} 值无效（空或非字符串）")

    return issues


def _fix_dead_routes(ws_path: Path) -> list:
    """处理 router/index.js 中指向不存在文件的懒加载路由。

    策略：注释掉整条路由记录 ({...})，而不是只注释 component 行。
    只注释 component 会导致路由记录缺少 component/children，触发 Vue Router 警告。
    同时支持"复活"：如果之前标记为 DEAD 的路由，对应 .vue 文件现已存在，则取消注释。
    """
    import re as _re
    router = ws_path / "src" / "router" / "index.js"
    if not router.exists():
        return []
    content = router.read_text("utf-8", errors="replace")
    lines = content.split('\n')
    removed = []
    revived = []

    # ══ 第一阶段：收集所有需要处理的 import 行 ══
    actions = []
    for i, line in enumerate(lines):
        # 锚定到行首，提取缩进、DEAD前缀、import路径
        m = _re.match(r'^(\s*)((?:^|\s*)//\s*(?:\[DEAD\]\s*)*)?.*import\s*\(\s*[\"\\\']@?/?([^\"\\\']+\.vue)[\"\\\']', line)
        if not m:
            continue
        indent = m.group(1)
        dead_prefix = m.group(2) or ""
        import_path = m.group(3)
        target = ws_path / "src" / import_path

        if dead_prefix and 'DEAD' in dead_prefix:
            if target.exists():
                # 需要复活：记录原始行以便去除 DEAD 标记
                rest_of_line = line[len(indent):].lstrip('//').lstrip()  # 去除 // [DEAD]
                actions.append((i, import_path, 'revive', indent, rest_of_line))
            continue

        if not target.exists():
            actions.append((i, import_path, 'dead', indent, line))

    if not actions:
        return []

    # ══ 第二阶段：从后往前处理 ══
    for item in reversed(actions):
        line_idx = item[0]
        import_path = item[1]
        action = item[2]

        if action == 'revive':
            indent = item[3]
            rest = item[4]
            # 去除 `— 文件不存在` 后缀和多余空格
            clean_line = _re.sub(r'\s*—\s*文件不存在\s*$', '', rest)
            lines[line_idx] = indent + clean_line
            revived.append(import_path)
            continue

        if action == 'dead':
            start_idx = line_idx
            depth = 0
            for j in range(line_idx, -1, -1):
                l = lines[j]
                depth += l.count('}') - l.count('{')
                if '{' in l and depth < 0:
                    start_idx = j
                    break

            end_idx = line_idx
            depth = 0
            for j in range(start_idx, len(lines)):
                l = lines[j]
                depth += l.count('{') - l.count('}')
                if '}' in l and depth <= 0:
                    end_idx = j
                    break

            # 删除整条路由块（含 import 行） + 清理空行
            del lines[start_idx:end_idx + 1]
            # 删除对应的 import 行
            import_line = None
            for j in range(len(lines)):
                if f"import('{import_path}')" in lines[j] or f'import("{import_path}")' in lines[j]:
                    import_line = j
                    break
            if import_line is not None:
                del lines[import_line]
            removed.append(import_path)

    new_content = '\n'.join(lines)
    if new_content != content:
        router.write_text(new_content, "utf-8")

    result = []
    if removed:
        result.append(f"删除 {len(removed)} 个死路由: {', '.join(removed)}")
    if revived:
        result.append(f"恢复 {len(revived)} 个已复活路由: {', '.join(revived)}")
    return result



def _check_router_components(ws_path: Path) -> list:
    """检查 router/index.js 中每条路由是否有 component / redirect / children。
    返回有问题的路由列表。"""
    import re as _re
    router = ws_path / "src" / "router" / "index.js"
    if not router.exists():
        return []
    try:
        content = router.read_text("utf-8", errors="replace")
    except Exception:
        return []

    issues = []

    # 提取 routes 数组中的每个顶层 route 对象
    # 策略：在 routes = [...] 中逐行扫描，跟踪每个顶层 { } 块
    routes_section = _re.search(r'const\s+routes\s*=\s*\[', content)
    if not routes_section:
        return []

    # 从 routes = [ 之后开始扫描
    start_pos = routes_section.end()
    # 找到匹配的 ]
    depth = 0
    end_pos = start_pos
    for i in range(start_pos, len(content)):
        ch = content[i]
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
            if depth == 0:
                end_pos = i
                break

    routes_body = content[start_pos:end_pos]

    # 按顶层 { } 块拆分（追踪大括号深度，但忽略嵌套 {}）
    route_blocks = []
    block_start = -1
    brace_depth = 0
    for i, ch in enumerate(routes_body):
        if ch == '{':
            if brace_depth == 0:
                block_start = i
            brace_depth += 1
        elif ch == '}':
            brace_depth -= 1
            if brace_depth == 0 and block_start >= 0:
                route_blocks.append(routes_body[block_start:i + 1])
                block_start = -1

    for block in route_blocks:
        # 跳过完全被注释的块
        active_lines = [l for l in block.split('\n')
                       if l.strip() and not l.strip().startswith('//')]
        if not active_lines:
            continue  # 整条路由被注释掉了，没问题

        # 检查是否有 component / redirect / children
        has_component = bool(_re.search(r'component\s*:', block))
        has_redirect = bool(_re.search(r'redirect\s*:', block))
        has_children = bool(_re.search(r'children\s*:', block))

        if not (has_component or has_redirect or has_children):
            # 提取 path 用于报告
            path_match = _re.search(r"""path\s*:\s*['\"]([^'\"]+)['\"]""", block)
            route_path = path_match.group(1) if path_match else "?"
            issues.append(f"router: path='{route_path}' 缺少 component / redirect / children")

    return issues



def _check_npm_exports(ws_path: Path) -> list:
    """扫描 src/ 下所有 .vue/.js 中 import {X} from 'npm-pkg' 的导出名是否真实存在。
    支持 import { X as Y } 别名语法，只检查源名称。
    返回无效导入列表。"""
    import re as _re, subprocess, json as _json

    router = ws_path / "src" / "router" / "index.js"
    issues = []

    # 收集所有需要检查的 (包名, 导入名称) 对
    pkg_imports = {}  # {package_name: [(file, line_no, original_token, source_name)]}
    bare_pattern = _re.compile(
        r"""import\s*\{([^}]+)\}\s*from\s*['\"]([^@./][^'\"]+)['\"]"""
    )

    for pattern in ["src/**/*.js", "src/**/*.vue"]:
        for fp in ws_path.glob(pattern):
            try:
                content = fp.read_text("utf-8", errors="replace")
            except Exception:
                continue
            rel = str(fp.relative_to(ws_path)).replace("\\", "/")
            for m in bare_pattern.finditer(content):
                imports_block = m.group(1)
                package_name = m.group(2).split("/")[0]  # scoped支持: @vue/xxx → @vue
                for token in imports_block.split(","):
                    token = token.strip()
                    if not token:
                        continue
                    # 处理 "X as Y" → 源名称是 X
                    source_name = token.split(" as ")[0].strip()
                    pkg_imports.setdefault(package_name, []).append(
                        (rel, content[:m.start()].count("\n") + 1, token, source_name)
                    )

    if not pkg_imports:
        return []

    # 逐个包验证导出
    for pkg_name, entries in pkg_imports.items():
        # 尝试在项目目录下用 node 加载包
        cmd = f"node -e \"const m = require('{pkg_name}'); console.log(JSON.stringify(Object.keys(m)))\""
        try:
            r = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15,
                cwd=str(ws_path), encoding="utf-8", errors="replace", shell=True
            )
            if r.returncode != 0:
                # 包无法加载，跳过（可能是 peer dep 问题）
                continue
            exports = _json.loads(r.stdout.strip())
        except Exception:
            continue

        export_set = set(exports)
        for rel, line_no, token, source_name in entries:
            if source_name not in export_set:
                # 尝试模糊匹配提供建议
                suggestions = [e for e in exports
                              if source_name.lower()[:3] == e.lower()[:3]][:5]
                sug_text = f"（建议: {', '.join(suggestions)}）" if suggestions else ""
                issues.append(
                    f"{rel}:{line_no}: import {{{token.strip()}}} from '{pkg_name}' — "
                    f"'{source_name}' 不存在{sug_text}"
                )

    return issues



def _check_require_path_depth(ws_path: Path) -> list:
    """检查 routes/ 下 require() 相对路径深度是否正确。"""
    import re as _re, os as _os
    issues = []
    routes_dir = ws_path / "routes"
    if not routes_dir.exists():
        return issues

    # 收集所有 controller/service/config 文件在磁盘上的位置
    disk_files = {}  # {basename: [relative_path_from_root]}
    for d in ["controllers", "services", "middleware", "config", "utils"]:
        dpath = ws_path / d
        if not dpath.exists():
            continue
        for fp in dpath.rglob("*.js"):
            rel = str(fp.relative_to(ws_path)).replace("\\", "/")
            disk_files.setdefault(fp.stem, []).append(rel)

    # 遍历所有路由文件
    for rf in sorted(routes_dir.rglob("*.js")):
        try:
            content = rf.read_text("utf-8", errors="replace")
        except Exception:
            continue

        rf_rel = str(rf.relative_to(ws_path)).replace("\\", "/")
        # 源文件深度: 从 routes/ 算起有几层子目录
        rf_depth = rf_rel.count("/") - 1 if "routes/" in rf_rel else 0  # routes/本身算一层

        for m in _re.finditer(r"""require\s*\(\s*['\"](\.\.?/[^'\"]+)['\"]\s*\)""", content):
            req_path = m.group(1)  # 如 ../controllers/adminCategoryController

            # 计算 require 声明的深度: ../ = 1层, ../../ = 2层
            declared_depth = req_path.count("../")
            if declared_depth == 0:
                continue  # ./ 同级引用，跳过

            # 去除 ../ 前缀得到目标路径（去掉 .js 扩展名如果写了）
            target = req_path
            while target.startswith("../"):
                target = target[3:]
            if target.endswith(".js"):
                target = target[:-3]
            target_basename = target.split("/")[-1]

            # 计算源文件到 target 的正确深度: 源文件所在目录到 target 文件目录
            # 源文件目录: 从 routes/ 去掉文件名
            rf_dir = rf_rel.rsplit("/", 1)[0]  # 如 routes/admin
            rf_dir_depth = rf_dir.count("/") + 1 if "/" in rf_dir else 1

            # 查找 target 文件在磁盘上的位置
            candidates = disk_files.get(target_basename, [])
            if not candidates:
                continue  # 文件不存在，由其他检查处理

            # 找最可能的候选（匹配 target 中的目录前缀）
            best = None
            for c in candidates:
                if target in c or c.endswith("/" + target_basename):
                    best = c
                    break
            if not best:
                best = candidates[0]

            # 从 rf_dir 到 best 所在目录的相对深度
            target_dir = best.rsplit("/", 1)[0]  # 如 controllers

            # 计算: 从 rf_dir 到 target_dir 需要几个 ../
            # 如果 rf_dir="routes" (depth=1), target_dir="controllers" (depth=1)
            #   → 需要 ../controllers/X  ✅
            # 如果 rf_dir="routes/admin" (depth=2), target_dir="controllers" (depth=1)
            #   → 从 routes/admin 到 controllers: ../ → routes, ../../ → root, ../../controllers/X ✅
            correct_depth = rf_dir_depth  # 从 routes/X/... 回到项目根需要 dir_depth 层

            if declared_depth != correct_depth and best:
                correct_path = "/".join([".."] * correct_depth) + "/" + best.replace(".js", "")
                issues.append(
                    f"{rf_rel}:{m.start()}: require('{req_path}') 深度错误 → "
                    f"文件在 {rf_dir}/ 下({rf_dir_depth}层深)，应写 require('{correct_path}')"
                )

    return issues



def _check_app_route_files(ws_path: Path) -> tuple:
    """双向检查路由注册完整性。
    正向: app.js 中 require 的路由文件是否都存在。
    反向: routes/ 目录下所有 .js 文件是否都被 app.js 注册。
    返回 (all_ok, issues)。"""
    import re as _re, os as _os
    issues = []
    app_js = ws_path / "app.js"
    if not app_js.exists():
        return False, ["app.js 不存在"]

    content = app_js.read_text("utf-8", errors="replace")

    # ── 正向: app.js 引用的路由 → 文件必须存在 ──
    registered_in_app = set()  # 收集 app.js 中已注册的路由文件（用于反向检查）
    for m in _re.finditer(r"""require\s*\(\s*['\"](\./routes/[^'\"]+)['\"]\s*\)""", content):
        route_path = m.group(1)
        # 移除 .js 扩展名（如果写了）用于后续匹配
        clean_path = route_path[:-3] if route_path.endswith(".js") else route_path
        registered_in_app.add(clean_path)
        # 尝试解析路径
        resolved = (ws_path / route_path).resolve()
        found = resolved.exists()
        if not found:
            for ext in ["", ".js", "/index.js"]:
                if Path(str(resolved) + ext).exists():
                    found = True; resolved = Path(str(resolved) + ext)
                    break
        if not found:
            issues.append(f"app.js require('{route_path}') → 文件不存在")

    # ── 反向: routes/ 下的路由文件 → 必须在 app.js 中被注册 ──
    routes_dir = ws_path / "routes"
    if routes_dir.exists():
        for rf in sorted(routes_dir.rglob("*.js")):
            # 跳过非路由文件（如 __tests__、helpers、utils 等）
            if any(seg in rf.parts for seg in ("__tests__", "node_modules", ".git")):
                continue
            rel = str(rf.relative_to(ws_path)).replace("\\", "/")
            # 构造 app.js 中的 require 路径: ./routes/xxx (去掉 .js)
            require_path = "./" + rel[:-3] if rel.endswith(".js") else "./" + rel
            if require_path not in registered_in_app:
                # 也尝试匹配子目录索引文件 routes/admin/index.js 的情况
                # 这种通常不需要显式注册（被父目录路由 require）
                if rf.name == "index.js":
                    continue
                issues.append(f"routes/ 文件未注册: '{rel}' 未被 app.js require — 缺少 app.use() 挂载行")

    # ── @mount 注解 vs app.js 挂载前缀交叉验证 ──
    # 规则: @mount 注解是权威来源，app.js 挂载应对齐 @mount
    # 收集所有已挂载的路由文件（用于缺 @mount 检查）
    mounted_files = set()
    for m2 in _re.finditer(
        r"""app\.use\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*require\s*\(\s*['\"](\./routes/[^'\"]+)['\"]\s*\)""",
        content
    ):
        mount_prefix = m2.group(1)
        req_path = m2.group(2)
        clean_req = req_path[:-3] if req_path.endswith(".js") else req_path
        route_file = ws_path / (clean_req.lstrip("./") + ".js")
        if not route_file.exists():
            continue
        mounted_files.add(clean_req)
        fc = route_file.read_text("utf-8", errors="replace")
        am = _re.search(r'@mount\s+(/\S+)', fc)
        rel = str(route_file.relative_to(ws_path)).replace("\\", "/")
        if am:
            expected = am.group(1).strip()
            if expected != mount_prefix:
                issues.append(
                    f"@mount 不匹配: '{rel}' @mount={expected} 但 app.js={mount_prefix}。"
                    f"@mount 是权威来源 → 将 app.js 中挂载改为 app.use('{expected}', require('{clean_req}'))")
        else:
            # 路由文件缺少 @mount 注解 → 无法交叉验证
            issues.append(
                f"缺 @mount 注解: '{rel}' 无 @mount 注释，请在该文件首行添加 // @mount {mount_prefix}")

        # ── 双重前缀检测: mount后缀 == route第一个路径段 ──
        internal_routes = _re.findall(r"router\.(get|post|put|delete|patch)\s*\(\s*['\"](/[^'\"]+)['\"]", fc)
        mount_suffix = mount_prefix.rstrip("/").split("/")[-1] if mount_prefix != "/" else ""
        for method, rp in internal_routes:
            path_first = rp.strip("/").split("/")[0] if rp != "/" else ""
            if mount_suffix and path_first and mount_suffix == path_first:
                full_url = mount_prefix + rp
                # 建议的修复：改用 @mount 注解值作为 mount 前缀（或去掉 mount 后缀）
                suggested_mount = am.group(1).strip() if am else mount_prefix.replace("/" + mount_suffix, "")
                suggested_url = suggested_mount + rp
                issues.append(
                    f"双重前缀: {method.upper()} {full_url} → 应改为 {method.upper()} {suggested_url}。"
                    f"原因: mount后缀'{mount_suffix}'与route前缀重复。"
                    f"修复: app.js 挂载改为 app.use('{suggested_mount}', require('{clean_req}'))")

    return len(issues) == 0, issues



def _check_endpoint_coverage(ws_path: Path, route_files: list, api_files: list) -> str:
    """比对 route 文件注册的端点 vs 前端 API 模块调用的端点。
    返回覆盖报告字符串，端点全覆盖时返回空字符串。
    """
    import re as _re

    # 1. 从 route 文件收集已注册的端点 (method, path_pattern)
    registered = set()  # {(method, path)}
    for rf in route_files:
        fp = ws_path / rf
        if not fp.exists():
            continue
        try:
            content = fp.read_text("utf-8", errors="replace")
        except Exception:
            continue
        for m in _re.finditer(
            r"""router\.(get|post|put|delete|patch|all)\s*\(\s*['\"]([^'\"]+)['\"]""",
            content, _re.IGNORECASE
        ):
            method = m.group(1).upper()
            path = m.group(2)
            registered.add((method, path))

    if not registered:
        return ""

    # 2. 从前端 API 文件收集调用的端点
    called = set()  # {(method, path)}
    for af in api_files:
        fp = ws_path / af
        if not fp.exists():
            continue
        try:
            content = fp.read_text("utf-8", errors="replace")
        except Exception:
            continue
        # 匹配 request.get('/path'), request.post('/path', data), axios.get('/path') 等
        for m in _re.finditer(
            r"""(?:request|axios|http|api)\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]""",
            content, _re.IGNORECASE
        ):
            method = m.group(1).upper()
            path = m.group(2)
            called.add((method, path))
        # 也匹配 fetch('/path', {method:'POST'})
        for m in _re.finditer(
            r"""fetch\s*\(\s*['\"]([^'\"]+)['\"]""",
            content, _re.IGNORECASE
        ):
            path = m.group(1)
            called.add(("GET", path))
        # 匹配路径中的动态参数 /:id → 归一化
        for m in _re.finditer(
            r"""['\"](\/[^'\"]+)['\"]""",
            content
        ):
            path = m.group(1)
            if path.startswith("/api/") or path.startswith("/auth/"):
                called.add(("ANY", path))

    if not called:
        return ""

    # 3. 比对：前端调用 vs 后端注册
    # 归一化路径动态参数: /:id → 用 /:param 表示
    def _norm_path(p: str) -> str:
        return _re.sub(r'/\d+', '/:id', _re.sub(r'/:(\w+)', '/:param', p))

    reg_norm = {(_norm_path(p), m) for m, p in registered}
    missing = []
    for method, path in sorted(called):
        np = _norm_path(path)
        # 精确匹配 或 ANY 匹配
        matched = ((np, method) in reg_norm or
                   (np, "ANY") in reg_norm or
                   (np, "ALL") in reg_norm or
                   any(rm == method and rp == np for rp, rm in reg_norm))
        if not matched:
            # 检查是否有同路径其他方法的注册
            alt_methods = {rm for rp, rm in reg_norm if rp == np}
            if alt_methods:
                missing.append(f"{method} {path} — 路由已注册但方法不匹配（已注册: {', '.join(sorted(alt_methods))}）")
            else:
                missing.append(f"{method} {path} — 端点未在后端 route 文件中注册")

    if missing:
        return f"发现 {len(missing)} 个端点覆盖问题:\n" + "\n".join(f"  ❌ {m}" for m in missing)
    return ""



def _scan_third_party_services(ws_path: Path) -> list:
    """收集原始环境数据供 Agent 推理，不做服务归类。

    输出格式: 每行一个事实，Agent 根据 npm 包名+env变量推断所需服务配置。
    """
    import re as _re, json as _json
    issues = []

    # 1. 所有 npm 依赖（Agent 根据包名推断服务: bullmq→需要Redis, nodemailer→需要SMTP等）
    pkg_json = ws_path / "package.json"
    if pkg_json.exists():
        try:
            pkg = _json.loads(pkg_json.read_text("utf-8"))
            deps = sorted(set(pkg.get("dependencies", {}).keys()) | set(pkg.get("devDependencies", {}).keys()))
            # 过滤掉明显不是服务的包（构建工具、测试框架、前端框架等）
            skip_prefixes = ("@vitejs", "@vue", "vite", "vue", "pinia", "element-plus", "axios",
                           "jest", "eslint", "prettier", "postcss", "tailwind", "autoprefixer")
            service_deps = [d for d in deps if not any(d.startswith(p) for p in skip_prefixes)]
            issues.append(f"[npm 依赖] {', '.join(service_deps)}")
        except Exception:
            pass

    # 2. 代码中所有 process.env.X 引用（Agent 根据变量名推断用途）
    code_vars = set()
    for root, dirs, files in __import__("os").walk(str(ws_path)):
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", ".meta", "test", "Memory", "doc")]
        for fn in files:
            if not fn.endswith((".js", ".vue")):
                continue
            try:
                content = Path(root, fn).read_text("utf-8", errors="replace")
                code_vars.update(_re.findall(r"process\.env\.(\w+)", content))
            except Exception:
                pass
    if code_vars:
        issues.append(f"[代码引用的 env 变量] {', '.join(sorted(code_vars))}")

    # 3. 当前 .env 已有的变量
    env_file = ws_path / ".env"
    existing_vars = set()
    if env_file.exists():
        for line in env_file.read_text("utf-8", errors="replace").split("\n"):
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                existing_vars.add(s.split("=")[0].strip())
    if existing_vars:
        missing = code_vars - existing_vars
        if missing:
            issues.append(f"[.env 缺少的变量] {', '.join(sorted(missing))}")

    # 4. mock 实现检测（代码中有 mock 函数但可能缺真实配置）
    mock_hints = set()
    for root, dirs, files in __import__("os").walk(str(ws_path)):
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", ".meta", "test", "Memory")]
        for fn in files:
            if not fn.endswith((".js", ".vue")):
                continue
            try:
                content = Path(root, fn).read_text("utf-8", errors="replace")
                for m in _re.finditer(r"(?:mock|Mock)([A-Z][a-zA-Z]+?)(?:\s*\(|Auth|Pay|SMS|Email|Upload)", content):
                    hint = m.group(0)[:50]
                    mock_hints.add(hint)
            except Exception:
                pass
    if mock_hints:
        issues.append(f"[检测到 mock 实现] {', '.join(sorted(mock_hints)[:10])}")

    # Agent 推理指引
    issues.append("[Agent 任务] 根据以上信息：1) 从 npm 包名推断需要哪些第三方服务 2) 对照 env 变量检查是否缺配置 3) 补全 .env 缺失变量 4) 如检测到 mock 实现，建议添加 *_MODE=mock|real 开关")

    return issues



def _check_database_ready(ws_path: Path) -> list:
    """检查数据库是否可连接 + init-db.js 是否存在。
    不在此运行 init-db.js — 由 _init_database 在 integ passed 后统一执行。"""
    import subprocess as _sp
    issues = []

    # 已初始化过 → 快速连接检查
    if _DB_INITIALIZED:
        return _check_db_connection(ws_path)

    # 未初始化: 检查脚本存在 + 种子目录
    for s in ["scripts/init-db.js", "scripts/seed-users.js"]:
        if not (ws_path / s).exists():
            issues.append(f"{s} 不存在")
    if not (ws_path / "database" / "seed").exists():
        issues.append("database/seed/ 目录不存在，无种子数据")
    return issues



def _check_db_tables_exist(ws_path: Path) -> list:
    """integ 层职责：init-db.js 执行后验证 DDL 表是否真实创建。
    用 SHOW TABLES 对比 DDL 中定义的表名。
    信任 db 层（DDL 正确）+ infra 层（config/db.js 连接正确）。
    """
    import subprocess as _sp, re as _re, json as _json
    issues = []

    # 1. 从 DDL 文件收集期望的表名
    expected_tables = set()
    db_dir = ws_path / "database"
    if db_dir.exists():
        for fp in db_dir.rglob("*.sql"):
            try:
                content = fp.read_text("utf-8", errors="replace")
            except Exception:
                continue
            for m in _re.finditer(
                r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?',
                content, _re.IGNORECASE
            ):
                expected_tables.add(m.group(1).lower())

    if not expected_tables:
        return issues  # 无 DDL 文件，跳过

    # 2. 从 .env 读取数据库凭据
    env_vars = {}
    env_file = ws_path / ".env"
    if env_file.exists():
        for line in env_file.read_text("utf-8", errors="replace").split("\n"):
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                env_vars[k.strip()] = v.strip().strip('"').strip("'")
    host = env_vars.get("DB_HOST", "localhost")
    port = env_vars.get("DB_PORT", "3306")
    user = env_vars.get("DB_USER", "root")
    pwd = env_vars.get("DB_PASSWORD", "")
    db = env_vars.get("DB_NAME", "testdb")

    # 3. SHOW TABLES 获取实际表名
    check_script = f"""
const mysql = require('mysql2/promise');
(async () => {{
  try {{
    const conn = await mysql.createConnection({{
      host: '{host}', port: {port}, user: '{user}',
      password: '{pwd}', database: '{db}',
      connectTimeout: 5000
    }});
    const [rows] = await conn.query('SHOW TABLES');
    console.log(JSON.stringify(rows.map(r => Object.values(r)[0])));
    await conn.end();
    process.exit(0);
  }} catch(e) {{
    console.error(e.code || e.message);
    process.exit(1);
  }}
}})();
"""
    try:
        r = _sp.run(
            ["node", "-e", check_script],
            capture_output=True, text=True, timeout=15,
            cwd=str(ws_path), encoding="utf-8", errors="replace",
        )
        if r.returncode != 0:
            issues.append(f"SHOW TABLES 失败: {(r.stderr or '')[:100]}")
            return issues
        actual_tables = set(t.lower() for t in _json.loads(r.stdout.strip()))
    except _sp.TimeoutExpired:
        issues.append("SHOW TABLES 超时（15s）")
        return issues
    except Exception as e:
        issues.append(f"SHOW TABLES 异常: {str(e)[:100]}")
        return issues

    # 4. 对比期望 vs 实际
    missing = expected_tables - actual_tables
    extra = actual_tables - expected_tables
    if missing:
        issues.append(f"DDL 定义但数据库中不存在的表: {sorted(missing)}")
    if extra:
        issues.append(f"数据库中存在但 DDL 未定义的表: {sorted(extra)}（可能是前次残留）")
    if not missing and not extra:
        print(f"    [integ] DB 表验证: {len(actual_tables)} 张表全部匹配 ✓")

    return issues


def _check_ui_colors(ws_path: Path, target_files: list = None) -> list:
    """从 Memory/ui_styles/_global.md 动态读取色板，扫描 .vue 中不在色板内的硬编码颜色。
    同时检查硬编码的 hsl()/rgb() —— 应该全部用 CSS 变量引用设计 token，禁止直接写颜色值。
    """
    import re as _re

    # 1. 从 Memory/ui_styles/_global.md 提取色板（HEX + HSL）
    ui_styles_dir = project_root / "Memory" / "ui_styles"
    palette_hex = set()
    palette_hsl = set()
    global_md = ui_styles_dir / "_global.md"
    palette_sources = [global_md] if global_md.exists() else sorted(ui_styles_dir.glob("*.md"))
    for src in palette_sources:
        if src.exists():
            text = src.read_text("utf-8", errors="replace")
            for m in _re.finditer(r'#[0-9a-fA-F]{6}', text):
                palette_hex.add(m.group(0).lower())
            for m in _re.finditer(r'hsl\((\d+),\s*(\d+)%,\s*(\d+)%\)', text):
                palette_hsl.add((int(m.group(1)), int(m.group(2)), int(m.group(3))))

    if not palette_hex and not palette_hsl:
        return ["Memory/ui_styles/ 不存在或无色板数据"]

    issues = []
    files_to_check = target_files if target_files else []
    if not files_to_check:
        for p in ws_path.glob("src/**/*.vue"):
            files_to_check.append(str(p.relative_to(ws_path)).replace("\\", "/"))

    for tf in files_to_check:
        fp = ws_path / tf if not Path(tf).is_absolute() else Path(tf)
        if not fp.exists() or not fp.suffix == ".vue":
            continue
        try:
            content = fp.read_text("utf-8", errors="replace")
        except Exception:
            continue
        rel = str(fp.relative_to(ws_path)).replace("\\", "/")
        found = {}
        # 2a. HEX 硬编码（不在色板内）
        for m in _re.finditer(r'#[0-9a-fA-F]{6}\b', content):
            h = m.group(0).lower()
            if h not in palette_hex and h not in ("#000000", "#ffffff"):
                found.setdefault(h, content[:m.start()].count("\n") + 1)
        # 2b. 🆕 hsl() / rgb() 硬编码（应全部替换为 CSS 变量）
        for m in _re.finditer(r'(hsl|rgb)a?\s*\([^)]+\)', content):
            raw = m.group(0)
            # 跳过 CSS 变量引用本身
            if 'var(--' in raw:
                continue
            ln = content[:m.start()].count("\n") + 1
            # 如果是 hsl，检查是否在设计色板内
            hsl_m = _re.match(r'hsl\((\d+),\s*(\d+)%,\s*(\d+)%\)', raw)
            if hsl_m:
                t = (int(hsl_m.group(1)), int(hsl_m.group(2)), int(hsl_m.group(3)))
                if t in palette_hsl:
                    found.setdefault(f"{raw}（应替换为对应 CSS 变量）", ln)
                else:
                    found.setdefault(f"{raw}（不在设计色板内）", ln)
            else:
                found.setdefault(f"{raw}（硬编码，应用 CSS 变量）", ln)
        for c, ln in sorted(found.items(), key=lambda x: x[1]):
            issues.append(f"{rel}:{ln} {c}")

    return issues



def _check_image_sources(ws_path: Path, target_files: list = None) -> list:
    """检查 .vue 文件中静态资源 src 是否使用了硬编码 https:// URL。
    覆盖 img / video / audio / a 标签，对应 /img/ /video/ /audio/ /file/ 四类。
    frontend 层职责：验证前端代码中的资源引用符合 FILE_BASE_URL 规范。
    """
    import re as _re
    issues = []
    files_to_check = target_files if target_files else []
    if not files_to_check:
        for p in ws_path.glob("src/**/*.vue"):
            files_to_check.append(str(p.relative_to(ws_path)).replace("\\", "/"))

    _url_pattern = _re.compile(
        r'''(?:src|href)\s*=\s*["'](https?://[^"']+\.(?:jpg|jpeg|png|gif|webp|svg|ico|mp4|webm|avi|mov|mp3|wav|ogg|flac|pdf|doc|xls|csv|zip))["']''',
        _re.IGNORECASE
    )
    for tf in files_to_check:
        fp = ws_path / tf if not Path(tf).is_absolute() else Path(tf)
        if not fp.exists() or not fp.suffix == ".vue":
            continue
        try:
            content = fp.read_text("utf-8", errors="replace")
        except Exception:
            continue
        rel = str(fp.relative_to(ws_path)).replace("\\", "/")
        for m in _url_pattern.finditer(content):
            line_no = content[:m.start()].count("\n") + 1
            issues.append(f"{rel}:{line_no}: 禁止硬编码文件 URL '{m.group(1)[:60]}' → 应使用 FILE_BASE_URL + 相对路径")

    return issues


def _check_vite_for_task(ws_path: Path, target_files: list) -> list:
    """运行 npx vite build，只报告属于 targetFiles 的错误。其他文件错误不属于本任务。"""
    import subprocess as _sp, re as _re
    issues = []

    # 只对包含 src/ 文件的任务有意义
    fe_files = [f for f in target_files if f.startswith("src/")]
    if not fe_files:
        return issues

    try:
        with _vite_lock:  # 全局锁，防止并发 vite build 冲突
            r = _sp.run(
                ["npx", "vite", "build", "--logLevel", "error", "--outDir", ".vite-check-tmp"],
                capture_output=True, text=True, timeout=120, shell=True,
                cwd=str(ws_path), encoding="utf-8", errors="replace",
            )
        # 清理临时目录
        tmp = ws_path / ".vite-check-tmp"
        if tmp.exists():
            import shutil; shutil.rmtree(str(tmp), ignore_errors=True)

        if r.returncode == 0:
            return issues  # 全部通过

        err_out = (r.stderr or r.stdout or "")
        # 提取文件路径: 匹配 "FILE:..." 或 "C:/.../file.vue" 等格式
        file_errors = {}  # {file_path: [error_lines]}
        current_file = None
        for line in err_out.split("\n"):
            # Vite/esbuild 错误通常包含文件路径
            fm = _re.search(r"""(?:^|\s)(src/[^\s:]+\.(?:vue|js))(?::|$|\s)""", line.strip())
            if fm:
                current_file = fm.group(1).replace("\\", "/")
            elif current_file:
                cleaned = line.strip()
                if cleaned and ("error" in cleaned.lower() or "Error" in cleaned):
                    file_errors.setdefault(current_file, []).append(cleaned[:200])

        # 只保留本任务管辖的文件
        tf_set = set(f.replace("\\", "/") for f in fe_files)
        my_errors = 0
        other_errors = 0
        for fpath, errs in file_errors.items():
            # 匹配: 完整路径或文件名
            in_scope = fpath in tf_set or any(
                fpath.endswith(tf.split("/")[-1]) or tf.endswith(fpath.split("/")[-1])
                for tf in tf_set
            )
            if in_scope:
                issues.append(f"{fpath}: {' | '.join(errs[:2])}")
                my_errors += 1
            else:
                other_errors += 1

        if other_errors > 0:
            print(f"    [vite] {other_errors} 个错误不在本任务 targetFiles 中，跳过")
    except _sp.TimeoutExpired:
        issues.append("vite build 超时（120s）")
    except Exception as e:
        issues.append(f"vite build 异常: {str(e)[:200]}")

    return issues



def _check_node_app_for_task(ws_path: Path, target_files: list) -> list:
    """运行 node app.js（monkey-patch listen），只报告属于 targetFiles 的后端错误。"""
    import subprocess as _sp, re as _re
    issues = []

    be_files = [f for f in target_files if any(
        f.startswith(d) for d in ("routes/", "controllers/", "services/", "middleware/", "config/", "utils/")
    )]
    if not be_files:
        return issues

    load_script = """
const http = require('http');
const orig = http.Server.prototype.listen;
http.Server.prototype.listen = function() { console.log('APP_LOAD_OK'); process.exit(0); };
setTimeout(() => { console.log('APP_LOAD_OK (timeout)'); process.exit(0); }, 10000);
try { require('./app'); } catch(e) { console.error('APP_LOAD_FAIL:' + e.message + '\\n' + (e.stack||'')); process.exit(1); }
"""
    try:
        with _node_app_lock:  # 全局锁，防止并发 node app.js 冲突
            r = _sp.run(
                ["node", "-e", load_script],
                capture_output=True, text=True, timeout=20,
                cwd=str(ws_path), encoding="utf-8", errors="replace",
            )
        if "APP_LOAD_OK" in (r.stdout or ""):
            return issues

        err_out = (r.stderr or r.stdout or "")
        # 提取后端文件路径
        tf_set = set(f.replace("\\", "/") for f in be_files)
        for line in err_out.split("\n"):
            fm = _re.search(r"""([\w/]+\.js):(\d+)""", line)
            if fm:
                fpath = fm.group(1).replace("\\", "/")
                # 标准化路径匹配
                in_scope = any(
                    fpath == tf or fpath.endswith("/" + tf) or tf.endswith("/" + fpath.split("/")[-1])
                    for tf in tf_set
                )
                if in_scope:
                    issues.append(line.strip()[:250])
    except _sp.TimeoutExpired:
        pass  # 超时=服务挂起，不算本任务的问题
    except Exception:
        pass

    return issues



def _check_env_alignment(ws_path: Path) -> list:
    """检查 .env / .env.example / .env.development / .env.production 四文件变量集一致。
    以 .env 为权威源，其他文件必须与 .env 变量集完全一致。"""
    issues = []

    env_path = ws_path / ".env"
    if not env_path.exists():
        return [".env 不存在"]

    # 读 .env 变量集（权威源）
    env_vars = set()
    for line in env_path.read_text('utf-8', errors='replace').split('\n'):
        s = line.strip()
        if s and not s.startswith('#') and '=' in s:
            env_vars.add(s.split('=')[0].strip())

    # 🆕 MODE 变量值校验: 必须是 mock 或 real
    for line in env_path.read_text('utf-8', errors='replace').split('\n'):
        s = line.strip()
        if s and not s.startswith('#') and '_MODE=' in s:
            key, val = s.split('=', 1)
            val = val.strip().strip('"').strip("'")
            if val not in ('mock', 'real'):
                issues.append(f".env: {key}={val} — 值必须是 mock 或 real")

    # 对比其他三个文件
    for fname in ['.env.example', '.env.development', '.env.production']:
        fp = ws_path / fname
        if not fp.exists():
            issues.append(f"{fname} 不存在")
            continue
        other_vars = set()
        for line in fp.read_text('utf-8', errors='replace').split('\n'):
            s = line.strip()
            if s and not s.startswith('#') and '=' in s:
                other_vars.add(s.split('=')[0].strip())
        missing = env_vars - other_vars
        extra = other_vars - env_vars
        if missing:
            issues.append(f"{fname} 缺 {len(missing)} 个变量: {sorted(missing)}")
        if extra:
            issues.append(f"{fname} 多 {len(extra)} 个变量: {sorted(extra)}")

    return issues



def _check_unregistered_pages(ws_path: Path) -> list:
    """扫描 src/pages/**/*.vue，与 router/index.js 注册的懒加载路径对比，找出未注册的页面。"""
    import re as _re
    issues = []
    router = ws_path / "src" / "router" / "index.js"
    if not router.exists():
        return ["src/router/index.js 不存在"]

    router_content = router.read_text("utf-8", errors="replace")
    # 提取 router 中已注册的 import 路径
    registered = set(_re.findall(r"""import\s*\(\s*['\"](?:@/)?([^'\"]+\.vue)['\"]""", router_content))

    # 扫描所有 .vue 页面
    pages_dir = ws_path / "src" / "pages"
    if not pages_dir.exists():
        return []
    all_pages = set()
    for vf in pages_dir.rglob("*.vue"):
        rel = str(vf.relative_to(ws_path)).replace("\\", "/")
        # 同时记录 src/pages/xxx.vue 和 @/pages/xxx.vue 两种写法
        all_pages.add(rel)
        if rel.startswith("src/"):
            all_pages.add(rel[4:])  # pages/xxx.vue

    unregistered = {p for p in all_pages if p not in registered and not any(p in r for r in registered)}
    for p in sorted(unregistered):
        issues.append(f"页面 {p} 未在 router/index.js 中注册")

    return issues



def _check_unregistered_backend_routes(ws_path: Path) -> list:
    """扫描 routes/*.js，与 app.js 的 require+app.use 对比，找出未注册的路由文件。"""
    import re as _re
    issues = []
    app_js = ws_path / "app.js"
    routes_dir = ws_path / "routes"

    if not app_js.exists():
        return ["app.js 不存在"]
    if not routes_dir.exists():
        return []

    app_content = app_js.read_text("utf-8", errors="replace")
    # 提取 app.js 中已注册的路由文件
    registered = set()
    for m in _re.finditer(r"""require\s*\(\s*['\"](\./routes/[^'\"]+)['\"]""", app_content):
        rp = m.group(1)[2:]  # 去掉 ./
        registered.add(rp + ("" if rp.endswith(".js") else ".js"))

    # 扫描 routes/ 下所有 .js 文件
    for rf in sorted(routes_dir.rglob("*.js")):
        rel = str(rf.relative_to(ws_path)).replace("\\", "/")
        # 兼容多级子目录
        route_key = rel.replace("routes/", "")
        if route_key not in registered:
            issues.append(f"路由文件 {rel} 未在 app.js 中注册 (require + app.use)")

    return issues



def _check_db_connection(ws_path: Path) -> list:
    """DB 已初始化后的快速连接检查。"""
    import subprocess as _sp
    issues = []
    try:
        r = _sp.run(
            "node -e \"require('dotenv').config();const m=require('mysql2/promise');m.createConnection({host:process.env.DB_HOST||'localhost',port:parseInt(process.env.DB_PORT)||3306,user:process.env.DB_USER||'root',password:process.env.DB_PASSWORD||'',database:process.env.DB_NAME||'testdb'}).then(c=>{c.end();process.exit(0)}).catch(e=>{process.exit(1)})\"",
            capture_output=True, text=True, shell=True, timeout=10,
            cwd=str(ws_path), encoding="utf-8", errors="replace",
        )
        if r.returncode != 0:
            issues.append("数据库连接失败（已跳过 init-db.js 重跑，请检查 MySQL 服务）")
    except Exception:
        issues.append("数据库连接检查异常")
    return issues



def _check_app_load(ws_path: Path) -> list:
    """快速检查 app.js 能否加载（monkey-patch listen 后立即退出）。"""
    import subprocess as _sp
    issues = []
    if not (ws_path / "app.js").exists():
        return ["app.js 不存在"]
    load_script = "const h=require('http');h.Server.prototype.listen=function(){console.log('OK');process.exit(0)};setTimeout(()=>{process.exit(0)},5000);try{require('./app')}catch(e){console.error('FAIL:'+e.message);process.exit(1)}"
    try:
        r = _sp.run(["node", "-e", load_script], capture_output=True, text=True, timeout=10,
                     cwd=str(ws_path), encoding="utf-8", errors="replace")
        if r.returncode != 0:
            err = (r.stderr or r.stdout or "")[:300].replace("\n", " | ")
            issues.append(f"app.js 加载失败: {err}")
    except _sp.TimeoutExpired:
        issues.append("app.js 加载超时（10s）")
    except Exception as e:
        issues.append(f"app.js 加载异常: {str(e)[:200]}")
    return issues



def _check_vite_build(ws_path: Path) -> list:
    """快速检查前端能否构建（只要不报错就行）。"""
    import subprocess as _sp
    issues = []
    if not (ws_path / "vite.config.js").exists():
        return []  # 没有 vite 配置，跳过
    try:
        r = _sp.run("npx vite build --log-level error 2>&1", shell=True, capture_output=True, text=True,
                     timeout=60, cwd=str(ws_path), encoding="utf-8", errors="replace")
        if r.returncode != 0:
            err = (r.stderr or r.stdout or "")[:300].replace("\n", " | ")
            issues.append(f"vite build 失败: {err}")
    except _sp.TimeoutExpired:
        issues.append("vite build 超时（60s）")
    except Exception as e:
        issues.append(f"vite build 异常: {str(e)[:200]}")
    return issues



def _check_route_name_refs(ws_path: Path) -> list:
    """扫描所有 .vue/.js 中的 router.push({name:'X'}) / { name: 'X' }（router-link to），
    对照 router/index.js 实际定义的路由名，返回不存在的路由名列表。"""
    import re as _re
    issues = []
    router_file = ws_path / "src" / "router" / "index.js"
    if not router_file.exists():
        return issues

    # 1. 从 router/index.js 提取所有定义的 route name
    router_content = router_file.read_text("utf-8", errors="replace")
    defined_names = set(_re.findall(r"""name\s*:\s*['\"]([^'\"]+)['\"]""", router_content))

    # 2. 扫描所有 .vue/.js 中的路由名引用
    # router.push({name:'X'}) / router.replace({name:'X'}) / { name:'X' }（在 to 属性中）
    refs_by_file = {}  # {file: {name}}
    for pattern in ["src/**/*.vue", "src/**/*.js"]:
        for fp in ws_path.glob(pattern):
            try:
                content = fp.read_text("utf-8", errors="replace")
            except Exception:
                continue
            names = set()
            # router.push({ name: 'X' }) / router.replace({ name: 'X' })
            names.update(_re.findall(r"""router\.(?:push|replace)\s*\(\s*\{\s*name\s*:\s*['\"]([^'\"]+)['\"]""", content))
            # :to="{ name: 'X' }" in template
            names.update(_re.findall(r"""to\s*=\s*['\"]\s*\{\s*name\s*:\s*['\"]([^'\"]+)['\"]""", content))
            # :to="{ name: 'X', ... }" 属性绑定
            names.update(_re.findall(r"""name\s*:\s*['\"]([^'\"]+)['\"]""", content))
            if names:
                rel = str(fp.relative_to(ws_path)).replace("\\", "/")
                refs_by_file[rel] = names - defined_names  # 只保留不存在的

    # 3. 过滤掉 router/index.js 自身（它定义 name 而非引用）
    refs_by_file = {f: n for f, n in refs_by_file.items()
                    if "router/index.js" not in f and n}

    for f, missing in sorted(refs_by_file.items()):
        issues.append(f"路由名不存在: {f} 引用了 {sorted(missing)}，但 router 中未定义这些 name（已定义: {sorted(defined_names)}）")

    return issues



def _smoke_check(ws: Path, files: list) -> list:
    """C 步骤后烟雾检测：node --check (后端) / esbuild (前端) 仅当前任务文件。"""
    import subprocess as _sp
    issues = []
    for tf in files:
        fp = ws / tf
        if not fp.exists(): continue
        if tf.endswith('.js'):
            if tf.startswith('src/') or 'src/' in tf:
                # 前端 ESM: esbuild 语法检查
                r = _sp.run(f'npx esbuild "{fp}" --format=esm --log-level=error --outfile={ws}/.smoke-tmp.js',
                           shell=True, capture_output=True, text=True, timeout=15,
                           cwd=str(ws), encoding='utf-8', errors='replace')
            else:
                r = _sp.run(['node', '--check', str(fp)], capture_output=True, text=True,
                           timeout=10, encoding='utf-8', errors='replace')
            if r.returncode != 0:
                issues.append(f'{tf}: 语法错误: {(r.stderr or r.stdout or "")[:150]}')
        elif tf.endswith('.vue'):
            # .vue 文件不逐文件检查——esbuild 不认 SFC 语法会假阳性。
            # SFC 正确性由 integ 层的 _check_vite_build (npx vite build) 统一验证。
            pass
    # 清理临时文件
    tmp = ws / '.smoke-tmp.js'
    if tmp.exists(): tmp.unlink(missing_ok=True)
    return issues




# ═══════════════════════════════════════════
# 静态层处理 + 修复层
# ═══════════════════════════════════════════

async def _handle_static_task(task: dict, state: TaskTestState, attempt: int,
                              workspace: str, model, task_map: dict = None,
                              layer_truths: dict = None) -> TaskTestState:
    """静态层：Python全量检查→Agent读+判+修→Agent自检→产出真理或ban。单轮，无后判断。"""
    task_id = task.get("id", "unknown")
    layer = task.get("layer", task.get("testType", "static"))
    target_files = task.get("targetFiles", [])
    ws_path = Path(workspace).resolve()

    print(f"  [{task_id}] STATIC check (Python全量→Agent判断+修复→Agent自检产出)")

    # 首次执行前清空旧日志
    if attempt == 1:
        old_logs = AGENT_LOG_DIR / task_id
        if old_logs.exists():
            import shutil
            shutil.rmtree(str(old_logs), ignore_errors=True)

    # 兜底：env 检查任务缺少 .env 时自动补上
    if layer == "infra" and any(f.endswith(".env.example") or ".env." in f for f in target_files):
        env_file = ".env"
        if env_file not in target_files and (ws_path / env_file).exists():
            target_files.append(env_file)
            task["targetFiles"] = target_files

    if not target_files:
        state.test_success = True
        state.source_success = True
        state.done = True
        _save_state(state)
        return state

    from agent.source_fixer import run_source_fixer

    # 🛑 扩展白名单：加入直接依赖的 targetFiles（上游缺失时允许本任务补建）
    dep_target_files = list(target_files)
    if task_map:
        for dep_id in task.get("dependencies", []):
            dep_task = task_map.get(dep_id, {})
            for tf in dep_task.get("targetFiles", []):
                if tf not in dep_target_files:
                    dep_target_files.append(tf)
    task["targetFiles"] = dep_target_files  # 临时扩展，只影响本次调用

    # ── Round 1: Python 全量检查（特殊，仅首轮）──
    source_contents = {}
    for tf in target_files:
        p = ws_path / tf
        if p.exists():
            try: source_contents[tf] = p.read_text("utf-8")
            except Exception: pass
    if not source_contents:
        state.source_success = False; _save_state(state); return state

    check_instructions = _build_static_check_prompt(task, source_contents, layer)
    # 🆕 注入工作区目录结构（替代 list_dir 工具）
    check_instructions += f"\n\n## 📁 工作区目录结构（已注入，不需要 list_dir）\n{_build_dir_tree(ws_path)}"
    full_results = _run_full_static_check(ws_path, target_files, layer, task_id, task)
    # Python 硬校验标记：只有确定性的硬错误才阻断，建议性检查交给 Agent 判断
    _HARD_ERROR_PATTERNS = [
        "语法错误", "语法错", "SyntaxError", "esbuild", "CJS 语法",
        "文件不存在", "无法读取", "JSON 解析失败", "文件为空",
        "非数组类型（应为 JSON 数组）", "多余列（不在", "缺列（",
        "引用了不存在的",
        # 🆕 SQL 硬错误（db 层 Python 预检查出，Agent 不可绕过）
        "AUTO_INCREMENT", "PRIMARY KEY", "MySQL 拒绝建表", "MySQL 会拒绝",
        "重复索引", "重复列名", "尾随逗号", "括号不配对", "括号未闭合",
        "SQL 语法错误", "CREATE TABLE 末尾缺分号",
    ]
    python_pass = True
    python_errors = []
    if full_results:
        check_instructions += "\n\n## 🔍 全量检查结果（Python 硬校验，作为你的判断依据）\n" + full_results
        for line in full_results.split("\n"):
            stripped = line.strip()
            if stripped.startswith("❌") and any(p in stripped for p in _HARD_ERROR_PATTERNS):
                python_pass = False
                python_errors.append(stripped)
    if not python_pass:
        print(f"    [{task_id}] Python 硬校验发现 {len(python_errors)} 个错误（Agent 无法覆盖）:")
        for pe in python_errors[:5]:
            print(f"      {pe}")
    if layer == "infra" and any(f.endswith(".env") or ".env" in f for f in target_files):
        env_ref = _build_env_reference(ws_path)
        if env_ref: check_instructions += env_ref
    if layer == "frontend":
        # 🆕 从 Memory/ui_styles/ 加载 PM+Designer 产出的动态 UI 风格文档
        ui_styles_dir = project_root / "Memory" / "ui_styles"
        if ui_styles_dir.exists():
            ui_parts = []
            for ui_file in sorted(ui_styles_dir.glob("*.md")):
                try:
                    content = ui_file.read_text("utf-8", errors="replace")
                    ui_parts.append(f"### {ui_file.stem}\n{content}")
                except Exception:
                    pass
            if ui_parts:
                check_instructions += "\n\n## 🛑 UI 风格文档（Memory/ui_styles/ — PM+Designer 产出，修改 .vue 时必须遵守）\n"
                check_instructions += "\n".join(ui_parts)

    max_rounds = 3
    all_bans = []  # 累积所有轮次的 ban，跨轮传递

    # 🆕 跨 attempt ban 记忆：从 Memory 加载历史 ban，防止重复犯同样错误
    if attempt > 1:
        from Tools.memory.ban_memory import get_bans as _get_bans, format_bans_for_agent as _fmt_bans
        hist_test_bans = _get_bans(task_id, "test_failure")
        hist_source_bans = _get_bans(task_id, "source_failure")
        all_bans.extend(hist_test_bans + hist_source_bans)
        if all_bans:
            print(f"    [{task_id}] 加载 {len(all_bans)} 条历史 ban（来自前 {attempt-1} 次尝试）")

    for rnd in range(1, max_rounds + 1):
        # 重新加载源码（上一轮可能已修改）
        source_contents = {}
        for tf in target_files:
            p = ws_path / tf
            if p.exists():
                try: source_contents[tf] = p.read_text("utf-8")
                except Exception: pass

        # 🆕 首轮注入历史 ban + Python 预检结果
        if rnd == 1 and all_bans:
            from Tools.memory.ban_memory import format_bans_for_agent as _fmt_bans
            check_instructions += f"\n\n## ⚠️ 历史累计 {len(all_bans)} 条 ban（前几轮未修复，请逐条处理）\n{_fmt_bans(all_bans)}"

        # 🆕 前端静态层：注入全局 + 本页专属 UI 设计规范（已预加载）
        if layer == "frontend":
            ui_dir = project_root / "Memory" / "ui_styles"
            if ui_dir.exists():
                for name in ("_global", "_components"):
                    fp = ui_dir / f"{name}.md"
                    if fp.exists():
                        try:
                            check_instructions += f"\n\n## 🎨 UI 设计规范 — {name}\n{fp.read_text('utf-8')}"
                        except Exception:
                            pass
                # 本页专属 UI 文档
                ui_name = task.get("ui_style", "")
                if ui_name:
                    fp = ui_dir / f"{ui_name}.md"
                    print(fp)
                    if fp.exists():
                        try:
                            check_instructions += f"\n\n## 🎨 本页专属 UI 风格 — {ui_name}\n{fp.read_text('utf-8')}"
                        except Exception:
                            pass

        cr = await run_source_fixer(
            task=task, test_file_path=None, workspace_root=workspace,
            source_contents=source_contents, model_client=model, task_id=task_id,
            attempt=attempt,
            bans_text=check_instructions,
            save_dir=str(AGENT_LOG_DIR / task_id / f"attempt_{attempt}_round_{rnd}"),
            save_filename="static_check",
        )
        raw_output = cr.get("raw_output", "")
        round_dir = AGENT_LOG_DIR / task_id / f"attempt_{attempt}_round_{rnd}"
        round_dir.mkdir(parents=True, exist_ok=True)
        (round_dir / "static_check_source_fixer.md").write_text(raw_output, encoding="utf-8")

        bans = cr.get("bans", [])
        # 🆕 source_fixer 内部已自主存储 ban，此处不再重复存储
        all_bans.extend(bans)
        agent_truth = cr.get("truth") or {}

        if agent_truth:
            # Agent 产出真理后硬校验：targetFiles 必须全部存在且非空
            missing = []
            for tf in target_files:
                fp = ws_path / tf
                if not fp.exists() or fp.stat().st_size == 0:
                    missing.append(tf)
            if missing:
                print(f"    [{task_id}] Agent 产出真理但 {len(missing)} 个文件缺失: {missing[:5]}")
                all_bans.append({"f": f"{layer}|source|{task_id}|MISSING_FILE",
                    "b": f"DON'T: 真理声称验证通过但以下文件不存在或为空: {', '.join(missing[:5])} | fix: 调用 create_files 补建这些文件 | target=source"})
                # 不通过，继续下一轮
            elif not python_pass:
                # Python 硬校验有错误 → Agent 产出真理也无效，必须修复
                print(f"    [{task_id}] Agent 产出真理但 Python 硬校验有 {len(python_errors)} 个错误未修复")
                all_bans.append({"f": f"{layer}|source|{task_id}|PYTHON_CHECK_FAIL",
                    "b": f"DON'T: Python 硬校验发现 {len(python_errors)} 个错误，Agent 不能绕过 | fix: 修复以下问题后重新验证: {'; '.join(python_errors[:3])} | target=source"})
                # 重新运行 Python 检查，更新状态
                full_results = _run_full_static_check(ws_path, target_files, layer, task_id, task)
                python_pass = True
                python_errors = []
                if full_results:
                    for line in full_results.split("\n"):
                        s = line.strip()
                        if s.startswith("❌") and any(p in s for p in _HARD_ERROR_PATTERNS):
                            python_pass = False
                            python_errors.append(s)
                check_instructions = _build_static_check_prompt(task, source_contents, layer)
                if full_results:
                    check_instructions += "\n\n## 🔍 全量检查结果（重新扫描）\n" + full_results
                # 不通过，下一轮
            else:
                print(f"    [{task_id}] STATIC pass (round {rnd}) — Python✅ + Agent✅ + 文件✅")
                state.test_success = True; state.source_success = True; state.done = True
                _save_state(state)
                # 终端层（依赖图最后一层）无下游消费者 → flag 为真时跳过真理
                if not _IS_LAST_LEVEL:
                    saved = _save_truth(task_id, {"task_id": task_id, "type": layer,
                        "description": task.get("description", ""), "exposed": agent_truth})
                    if not saved:
                        print(f"    [{task_id}] 真理保存失败，不通过")
                        state.test_success = False; state.source_success = False; state.done = False
                        _save_state(state)
                        continue
                    if task_map and task_id in task_map:
                        layer_truths.setdefault(task_map[task_id].get("layer", layer), {})[task_id] = agent_truth
                return state

        # 未产出真理 — 准备下一轮（注入全部累计 ban，无 Python 预检）
        if rnd < max_rounds:
            check_instructions = _build_static_check_prompt(task, source_contents, layer)
            if all_bans:
                from Tools.memory.ban_memory import format_bans_for_agent as _fmt_bans
                check_instructions += f"\n\n## ⚠️ 累计 {len(all_bans)} 条 ban（请逐条修复，不要重复已修复的）\n{_fmt_bans(all_bans)}"
            else:
                check_instructions += "\n\n## ⚠️ 上一轮 Agent 未产出真理或 ban，请对照全量检查结果修复并输出真理"
            print(f"    [{task_id}] STATIC round {rnd}: {len(bans)} new bans (total {len(all_bans)}) → retry")

    print(f"    [{task_id}] STATIC failed after {max_rounds} rounds")
    state.test_success = True; state.source_success = False
    _save_state(state)
    return state



def _clean_round_artifacts():
    """轮间清理：删除本轮未通过任务的全部产物，已通过的保留。
    清理范围: test_logs(状态) + agent_logs(日志) + test_failure/source_failure(ban) + truths/test(真理) + snapshots(源码快照)
    返回: (passed_count, failed_count)"""
    import shutil
    passed_ids = set()
    failed_ids = set()
    # 1. 扫描状态文件，分类通过/失败
    for tf in MEMORY_DIR.glob("*.json"):
        try:
            data = json.loads(tf.read_text("utf-8"))
            ts = data.get("test_success")
            ss = data.get("source_success")
            test_ok = ts.get("failed", 0) == 0 if isinstance(ts, dict) else bool(ts)
            source_ok = ss.get("failed", 0) == 0 if isinstance(ss, dict) else bool(ss)
            if test_ok and source_ok:
                passed_ids.add(tf.stem)
            else:
                failed_ids.add(tf.stem)
        except Exception:
            pass

    if not failed_ids:
        return (len(passed_ids), 0)

    # 2. 删失败任务的状态文件（下一轮 _execute_single_task 会重建）
    for tid in failed_ids:
        (MEMORY_DIR / f"{tid}.json").unlink(missing_ok=True)

    # 3. 删失败任务的 agent 日志
    if AGENT_LOG_DIR.exists():
        for td in AGENT_LOG_DIR.iterdir():
            if td.is_dir() and td.name in failed_ids:
                shutil.rmtree(str(td), ignore_errors=True)

    # 4. 删失败任务的 ban（test + source）
    for ban_dir in [BAN_TEST_DIR, BAN_SOURCE_DIR]:
        if ban_dir.exists():
            for bf in ban_dir.glob("*.json"):
                if bf.stem in failed_ids:
                    bf.unlink(missing_ok=True)

    # 5. 删失败任务的真理（本轮未通过 → 真理已失效）
    if TRUTH_DIR_TEST.exists():
        for tf in TRUTH_DIR_TEST.glob("*.json"):
            if tf.stem in failed_ids:
                tf.unlink(missing_ok=True)

    # 6. 删失败任务的源码快照（best + snap_*）
    snapshot_dir = project_root / "Memory" / "snapshots"
    if snapshot_dir.exists():
        for sf in snapshot_dir.glob("*.json"):
            # 文件名格式: best_{task_id}.json 或 snap_{task_id}_{hash}.json
            stem = sf.stem
            if stem.startswith("best_"):
                tid = stem[5:]
            elif stem.startswith("snap_"):
                # snap_t_api_user_a1b2c3d4e5f6 → t_api_user
                tid = stem[5:-17] if len(stem) > 22 else stem[5:]
            else:
                continue
            if tid in failed_ids:
                sf.unlink(missing_ok=True)

    print(f"[cleanup] 轮间清理: {len(passed_ids)} passed 保留, {len(failed_ids)} failed 已清")
    return (len(passed_ids), len(failed_ids))



async def _handle_repair_task(task: dict, workspace: str) -> TaskTestState:
    """修复层: 读取 .meta/failed_tasks.json，重新生成缺失源文件。不走ABCD。"""
    task_id = task.get("id", "unknown")
    ws_path = Path(workspace)

    # 🆕 从 .meta/failed_tasks.json 动态加载失败文件列表
    failed_file = ws_path / ".meta" / "failed_tasks.json"
    if not failed_file.exists():
        print(f"  [{task_id}] REPAIR: 无 failed_tasks.json，跳过")
        state = TaskTestState(task_id)
        state.test_success = True
        state.source_success = True
        state.done = True
        _save_state(state)
        return state

    import json as _json
    failed_data = _json.loads(failed_file.read_text("utf-8"))
    raw_failed = failed_data.get("failed", [])
    raw_pruned = failed_data.get("pruned", [])
    repair_order = failed_data.get("repair_order", [])

    # 🛑 合并 failed + pruned，按 repair_order 拓扑顺序排列
    # pruned 任务在上游修复后也需要重新生成，否则下游测试层找不到源文件
    all_failed_map = {}
    for entry in raw_failed:
        all_failed_map[entry.get("task_id", "")] = entry
    for entry in raw_pruned:
        tid = entry.get("task_id", "")
        if tid not in all_failed_map:
            all_failed_map[tid] = entry

    # 按 repair_order 排序（repair_order 已按依赖拓扑排好）
    if repair_order:
        ordered_list = []
        for tid in repair_order:
            if tid in all_failed_map:
                ordered_list.append(all_failed_map.pop(tid))
        ordered_list.extend(all_failed_map.values())  # 兜底：repair_order 中没有的放最后
        failed_list = ordered_list
    else:
        failed_list = raw_failed + raw_pruned

    if not failed_list:
        print(f"  [{task_id}] REPAIR: 无失败任务，跳过")
        state = TaskTestState(task_id)
        state.test_success = True
        state.source_success = True
        state.done = True
        _save_state(state)
        return state

    print(f"  [{task_id}] REPAIR: {len(raw_failed)} failed + {len(raw_pruned)} pruned = {len(failed_list)} total to repair")
    all_repaired = True
    for entry in failed_list:
        source_task = entry.get("task_id", "")
        target_files = entry.get("outputFiles", [])
        agent_type = entry.get("type", "")
        print(f"    Re-running {agent_type} for {source_task}: {target_files}")

        # 跳过集成任务（集成由后续层单独处理）
        if agent_type == "integration":
            continue

        # 检查: files + truth 都满足则跳过
        truth_file = project_root / "Memory" / "truths" / "engineer" / f"{source_task}.json"
        files_ok = all((ws_path / f).exists() and (ws_path / f).stat().st_size > 0 for f in target_files) if target_files else False
        if files_ok and truth_file.exists():
            print(f"      Already OK, skip")
            continue

        # Re-run the engineer agent
        try:
            from agent.base_designer import run_infrastructure_task, run_database_task, run_backend_task, run_frontend_task
            task_input = {"taskId": source_task, "outputFiles": target_files}
            if agent_type in ("infra", "infrastructure"):
                result = await run_infrastructure_task(task_input, workspace_root=workspace)
            elif agent_type == "db":
                result = await run_database_task(task_input, workspace_root=workspace)
            elif agent_type in ("backend", "backend_proc"):
                result = await run_backend_task(task_input, workspace_root=workspace)
            elif agent_type in ("frontend", "frontend_static"):
                result = await run_frontend_task(task_input, workspace_root=workspace)
            else:
                result = {"success": False, "error": f"Unknown agent type: {agent_type}"}
        except Exception as e:
            result = {"success": False, "error": str(e)}
            print(f"      Exception: {e}")

        # 复检: files + truth
        files_ok = all((ws_path / f).exists() and (ws_path / f).stat().st_size > 0 for f in target_files) if target_files else False
        truth_ok = truth_file.exists()
        if files_ok and truth_ok:
            print(f"      Repaired successfully")
        else:
            all_repaired = False
            print(f"      Still failing: files={files_ok} truth={truth_ok}")

    state = TaskTestState(task_id)
    state.test_success = all_repaired
    state.source_success = all_repaired
    state.done = all_repaired
    _save_state(state)
    return state





# ═══════════════════════════════════════════
# 真理 & 状态辅助函数
# ═══════════════════════════════════════════

def _load_test_truths() -> Dict[str, dict]:
    """从 Memory/truths/test/ 加载测试阶段真理。返回 {task_id: exposed_dict}。"""
    truths = {}
    if TRUTH_DIR_TEST.exists():
        for fp in sorted(TRUTH_DIR_TEST.glob("*.json")):
            try:
                data = json.loads(fp.read_text("utf-8"))
                exposed = data.get("exposed", {})
                if exposed and isinstance(exposed, dict):
                    truths[fp.stem] = exposed
            except (json.JSONDecodeError, OSError):
                pass
    return truths

def _extract_router_defs(router_content: str) -> list:
    """从 router/index.js 提取路由定义（path/name/component），供 navigation 测试引用 routeName。"""
    import re as _re
    routes = []
    # 匹配 { path: '...', name: '...', component: ... }
    for m in _re.finditer(
        r"""path\s*:\s*['\"]([^'\"]+)['\"].*?name\s*:\s*['\"]([^'\"]+)['\"].*?component\s*:\s*(\S+)""",
        router_content
    ):
        component = m.group(3).rstrip(',')
        routes.append({"path": m.group(1), "name": m.group(2), "component": component})
    return routes



def _scan_interface_from_files(layer: str, file_contents: dict, target_files: list, engineer_truth: dict, ws_path: Path = None) -> dict:
    """Python 正则回退: 从生成文件中扫描接口。"""
    import re
    result = {"exposed_to_upper": {}, "exposed_to_peers": {}}

    for tf, content in file_contents.items():
        if layer == "infra":
            # package.json: 提取 scripts + dependencies
            if tf == "package.json":
                try:
                    pkg = json.loads(content)
                    result["exposed_to_upper"]["package"] = {
                        "name": pkg.get("name", ""),
                        "version": pkg.get("version", ""),
                        "scripts": pkg.get("scripts", {}),
                        "dependencies": list(pkg.get("dependencies", {}).keys()),
                        "devDependencies": list(pkg.get("devDependencies", {}).keys()),
                    }
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
            # .env 文件: 提取变量名
            elif tf.endswith('.env') or '.env' in tf:
                vars_list = re.findall(r'^(\w+)=', content, re.MULTILINE)
                if vars_list:
                    result["exposed_to_upper"].setdefault("env_vars", [])
                    result["exposed_to_upper"]["env_vars"].extend(vars_list)
            # config/*.js / middleware/*.js / utils/*.js: 提取 module.exports
            elif tf.endswith('.js'):
                exports = re.findall(r'module\.exports\.(\w+)\s*=', content)
                if not exports:
                    m = re.search(r'module\.exports\s*=\s*\{([^}]+)\}', content)
                    if m:
                        exports = re.findall(r'(\w+)', m.group(1))
                if not exports:
                    m = re.search(r'module\.exports\s*=\s*(\w+)', content)
                    if m:
                        exports = [m.group(1)]
                if exports:
                    result["exposed_to_upper"].setdefault("config_exports", [])
                    result["exposed_to_upper"]["config_exports"].append({"file": tf, "exports": exports})

        elif layer == "peer_deps":
            exports = re.findall(r'module\.exports\.(\w+)\s*=', content)
            if not exports:
                m = re.search(r'module\.exports\s*=\s*\{([^}]+)\}', content)
                if m:
                    exports = re.findall(r'(\w+)', m.group(1))
            if not exports:
                m = re.search(r'module\.exports\s*=\s*(\w+)', content)
                if m:
                    exports = [m.group(1)]
            if exports:
                result["exposed_to_upper"]["exports"] = exports

        elif layer == "db":
            tables = []
            # 匹配完整 CREATE TABLE 语句
            for m in re.finditer(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?\s*\((.*?)\)\s*ENGINE', content, re.IGNORECASE | re.DOTALL):
                table_name = m.group(1)
                body = m.group(2)
                fields = []
                indexes = []
                fks = []
                for line in body.split('\n'):
                    line = line.strip().rstrip(',')
                    if not line or line.startswith('--') or line.startswith('PRIMARY KEY') or line.startswith('KEY ') or line.startswith('INDEX '):
                        # 提取 INDEX
                        idx_m = re.match(r'(?:KEY|INDEX)\s+`?(\w+)`?\s*\(([^)]+)\)', line)
                        if idx_m:
                            indexes.append({"name": idx_m.group(1), "columns": [c.strip().strip('`') for c in idx_m.group(2).split(',')]})
                        continue
                    # FOREIGN KEY
                    fk_m = re.match(r'FOREIGN\s+KEY\s*\(`?(\w+)`?\)\s*REFERENCES\s+`?(\w+)`?\s*\(`?(\w+)`?\)', line, re.IGNORECASE)
                    if fk_m:
                        fks.append({"columns": [fk_m.group(1)], "refTable": fk_m.group(2), "refColumns": [fk_m.group(3)]})
                        continue
                    # 字段: `name` TYPE CONSTRAINTS
                    col_m = re.match(r'`(\w+)`\s+(\w+(?:\([^)]+\))?)\s*(.*)', line)
                    if col_m:
                        constraints = col_m.group(3).strip().upper() if col_m.group(3) else ""
                        if constraints:
                            constraints = re.sub(r'CHARACTER\s+SET\s+\w+', '', constraints, flags=re.IGNORECASE).strip()
                        fields.append({"name": col_m.group(1), "type": col_m.group(2).upper(), "constraints": constraints})
                if fields:
                    tables.append({"name": table_name, "file": tf, "fields": fields, "indexes": indexes, "foreignKeys": fks})
            if tables:
                result["exposed_to_upper"]["tables"] = tables

        elif layer == "api":
            routes = []
            # 匹配 router.{method}('{path}', [middleware], handler) 完整模式
            for rm in re.finditer(r'router\.(get|post|put|delete|patch)\s*\(\s*[\'\"]([^\'\"]+)[\'\"](.*?)\)', content, re.DOTALL):
                method = rm.group(1).upper()
                path = rm.group(2)
                rest = rm.group(3)
                middleware = re.findall(r'(\w+)\s*(?:,|$)', rest.strip().lstrip(',').strip())
                handler = middleware.pop() if middleware and not middleware[-1].startswith('hasRole') and not middleware[-1].startswith('authenticate') else ""
                routes.append({"method": method, "path": path, "middleware": middleware, "handler": handler})
            if routes:
                result["exposed_to_upper"]["routes"] = [{"file": tf, "basePath": "", "handlers": routes}]

        elif layer == "backend_proc":
            # 提取 controller/service 函数签名
            svc_fns = []
            for fm in re.finditer(r'(?:async\s+)?(?:function\s+|const\s+)?(\w+)\s*(?:=\s*(?:async\s+)?\(|\(([^)]*)\))', content):
                name = fm.group(1)
                params = fm.group(2) or ""
                if name not in ('require','module','exports','if','for','while','return'):
                    svc_fns.append({"name": name, "params": [p.strip() for p in params.split(',') if p.strip()]})
            if svc_fns:
                result["exposed_to_peers"]["services"] = [{"file": tf, "functions": svc_fns}]

        elif layer == "frontend":
            pages = []
            for tf_path in target_files:
                if tf_path.endswith('.vue'):
                    pages.append({"file": tf_path})
            if pages:
                result["exposed_to_upper"]["pages"] = pages
            # 从 router/index.js 提取路由定义（供 navigation 测试引用 routeName）
            if ws_path and (ws_path / "src" / "router" / "index.js").exists():
                router_content = (ws_path / "src" / "router" / "index.js").read_text("utf-8", errors="replace")
                router_defs = _extract_router_defs(router_content)
                if router_defs:
                    result["exposed_to_upper"]["router"] = router_defs
            # 提取 store state/actions
            state_matches = re.findall(r'(?:const|let|var)\s+(\w+)\s*=\s*ref\(|reactive\(', content)
            action_matches = re.findall(r'(?:const|async\s+)?(?:function\s+)?(\w+)\s*[=(]', content)
            if state_matches or action_matches:
                result["exposed_to_peers"]["stores"] = [{"file": tf, "state": state_matches, "actions": action_matches}]

        elif layer == "db_api":
            # 从 Service SQL 提取列名
            tables = re.findall(r'(?:FROM|INTO|UPDATE)\s+`?(\w+)`?', content, re.IGNORECASE)
            columns = re.findall(r'`(\w+)`', content)
            if columns:
                result["exposed_to_upper"]["sql_columns_verified"] = [{
                    "file": tf,
                    "tables": sorted(set(tables)),
                    "columns": sorted(set(columns)),
                }]

        elif layer == "auth":
            # 提取 token 配置
            secret_match = re.search(r'(?:JWT_SECRET|SECRET)\s*[=:]\s*[\'\"]([^\'\"]+)', content)
            exp_match = re.search(r'(?:expiresIn|JWT_EXPIRES)\s*[=:]\s*[\'\"]([^\'\"]+)', content)
            mw_inject = re.search(r'(req\.\w+)\s*=\s*(\w+\.\w+)', content)
            auth_result = {}
            if secret_match: auth_result["secret"] = secret_match.group(1)
            if exp_match: auth_result["expiresIn"] = exp_match.group(1)
            if mw_inject: auth_result["injection"] = f"{mw_inject.group(1)} = {mw_inject.group(2)}"
            if auth_result: result["exposed_to_upper"]["token_config"] = auth_result

    return result



def _load_truth_prompt(layer: str) -> str:
    """加载真理提取 prompt：skill/test/truths/{layer}.md，回退到 _default.md"""
    prompt_file = project_root / "skill" / "test" / "truths" / f"{layer}.md"
    if not prompt_file.exists():
        prompt_file = project_root / "skill" / "test" / "truths" / "_default.md"
    if prompt_file.exists():
        return prompt_file.read_text("utf-8")
    return """你是接口提取器。输出 JSON: {"exposed_to_upper": {...}, "exposed_to_peers": {...}}"""






def _collect_dep_truths(task: dict, task_map: dict, layer_truths: dict) -> str:
    """收集**直接依赖**的真理，按任务层级过滤只保留相关部分。"""
    if not layer_truths:
        return ""
    layer = task.get("layer", "")
    flat = {}
    for _, tasks in layer_truths.items():
        for tid, entry in tasks.items():
            if entry and isinstance(entry, dict):
                flat[tid] = entry
    parts = []
    for dep_id in task.get("dependencies", []):
        exposed = flat.get(dep_id)
        if exposed and isinstance(exposed, dict):
            filtered = _filter_exposed_for_layer(exposed, layer)
            if filtered:
                parts.append(f"### @truth {dep_id}\n```json\n{json.dumps(filtered, indent=2, ensure_ascii=False)}\n```")
    if not parts:
        return ""
    return "\n## 🛑 下层真理（直接依赖，已通过测试验证，接口不可质疑）\n\n" + "\n".join(parts)


# ── 按测试层过滤真理：每层只保留直接相关的部分 ──
_TRUTH_FILTER = {
    # 全保留：依赖关系（dependencies 列表）控制传哪些任务，skill 文件控制解读哪些字段
    # 不在 Python 层做字段级过滤，由各层 ABCD 的 role/template 自行挑选所需字段
}




def _filter_exposed_for_layer(exposed: dict, layer: str) -> dict:
    """按测试层过滤真理，去掉不相关的部分以减少 token。keep=[] 表示全保留。"""
    rule = _TRUTH_FILTER.get(layer)
    if not rule or not rule["keep"]:  # 无规则或空列表 = 全保留
        return exposed
    keep_keys = set(rule["keep"])
    # 兼容两种格式：有 exposed_to_upper 包裹的（Agent产出）和直接存放的（静态层Python提取）
    upper = exposed.get("exposed_to_upper") or {}
    peers = exposed.get("exposed_to_peers") or {}
    # 如果没有包裹，整层就是 upper
    if not upper and not peers:
        upper = {k: v for k, v in exposed.items() if k not in ("exposed_to_upper", "exposed_to_peers")}
    filtered_upper = {k: v for k, v in upper.items() if k in keep_keys} if isinstance(upper, dict) else {}
    filtered_peers = {k: v for k, v in peers.items() if k in keep_keys} if isinstance(peers, dict) else {}
    result = {}
    if filtered_upper: result["exposed_to_upper"] = filtered_upper
    if filtered_peers: result["exposed_to_peers"] = filtered_peers
    return result if result else exposed  # 过滤后为空则回退全保留



def _save_truth(task_id: str, truth_entry: dict):
    """保存真理文件，并验证写入成功。"""
    if not truth_entry or not isinstance(truth_entry, dict):
        print(f"    [truth] {task_id}: 拒绝保存空真理")
        return False
    exposed = truth_entry.get("exposed")
    if not exposed or not isinstance(exposed, dict):
        print(f"    [truth] {task_id}: 真理缺少 exposed 字段，拒绝保存")
        return False
    fp = TRUTH_DIR_TEST / f"{task_id}.json"
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(truth_entry, indent=2, ensure_ascii=False), "utf-8")
    # 二次验证
    if not fp.exists() or fp.stat().st_size < 10:
        print(f"    [truth] {task_id}: 真理写入失败（文件为空或不存在）")
        return False
    return True



def _load_frontend_api_exports(ws: Path) -> dict:
    """从 engineer truth 加载前端 API 模块的实际导出名。
    Returns: {规范化文件路径: {exported_name, ...}}
    示例: {'src/api/admin.js': {'getMerchants', 'auditMerchant', ...}}
    """
    import json as _json
    result = {}
    TRUTH_DIR = Path(__file__).resolve().parent.parent / "Memory" / "truths" / "engineer"
    if not TRUTH_DIR.exists():
        return result
    for tf_json in TRUTH_DIR.glob("*.json"):
        try:
            d = _json.loads(tf_json.read_text("utf-8", errors="replace"))
        except Exception:
            continue
        if d.get("type") != "frontend":
            continue
        # 来源1: metadata.api_exports（base_designer 自动提取）
        api_exports = d.get("metadata", {}).get("api_exports", {})
        # 来源2: 兜底 — 扫描实际文件
        if not api_exports:
            output_files = d.get("output_files", [])
            for f in output_files:
                if "api" in f and f.endswith(".js"):
                    fp = ws / f
                    if fp.exists():
                        import re
                        content = fp.read_text("utf-8", errors="replace")
                        names = set(re.findall(r'export (?:async\s+)?function\s+(\w+)', content))
                        names.update(re.findall(r'export\s+const\s+(\w+)\s*=', content))
                        if names:
                            api_exports[f] = sorted(names)
        for fname, names in api_exports.items():
            norm = fname.replace("\\", "/")
            if norm in result:
                result[norm].update(names)
            else:
                result[norm] = set(names)
    return result



# ═══════════════════════════════════════════
# ABCD 循环 + C→D 屏障
# ═══════════════════════════════════════════

def _init_c_barrier(ws_path: Path = None, tasks: list = None):
    """每个 level 开始前重置屏障。任务在 _attempt_once 入口通过 _cd_register() 注册。"""
    global _cd_state, _cd_ev, _d_ev, _cd_lk, _round_done, _registered_tasks
    _cd_state = {"total":0, "b_p":0, "s_o":0, "s_f":0, "skipped":0, "d_p":0, "d_f":0}
    _cd_ev = asyncio.Event()
    _d_ev = asyncio.Event()
    _cd_lk = asyncio.Lock()
    _round_done = 0
    _registered_tasks = set()



async def _cd_register(task_id: str = ""):
    """注册到当前 gen。每 attempt 入口调用，去重：同 gen 内只计一次。"""
    global _cd_state, _registered_tasks
    async with _cd_lk:
        if task_id and task_id not in _registered_tasks:
            _registered_tasks.add(task_id)
            _cd_state["total"] += 1



async def _cd_mark_done():
    """标记完成。_round_done>=total 且 D 全部完成时，创建新 gen（清零 total+_registered_tasks）。"""
    global _cd_state, _cd_ev, _d_ev, _round_done, _registered_tasks
    async with _cd_lk:
        _round_done += 1
        if _round_done >= _cd_state["total"] and _cd_state["total"] > 0:
            if _cd_state["d_p"] + _cd_state["d_f"] >= _cd_state["s_o"]:
                _cd_state["total"] = 0
                _cd_state["b_p"] = 0
                _cd_state["s_o"] = 0
                _cd_state["s_f"] = 0
                _cd_state["skipped"] = 0
                _cd_state["d_p"] = 0
                _cd_state["d_f"] = 0
                _round_done = 0
                _registered_tasks = set()
                _cd_ev = asyncio.Event()
                _d_ev = asyncio.Event()



async def _cd_count_b_passed():
    """B 全部通过（无需 C/D）：b_p++。检查屏障1（>= total，含 skipped）。标记完成。"""
    global _cd_state, _cd_ev, _d_ev
    async with _cd_lk:
        _cd_state["b_p"] += 1
        if _cd_state["b_p"] + _cd_state["s_o"] + _cd_state["s_f"] + _cd_state["skipped"] >= _cd_state["total"] > 0:
            _cd_ev.set()
            if _cd_state["s_o"] == 0:
                _d_ev.set()  # 无人需要 D，直接解锁 D 屏障
    await _cd_mark_done()



async def _cd_count_skipped():
    """B test ban / C source_fixer fail / A fail 等跳过本轮：skipped++。检查屏障1。标记完成。"""
    global _cd_state, _cd_ev, _d_ev
    async with _cd_lk:
        _cd_state["skipped"] += 1
        if _cd_state["b_p"] + _cd_state["s_o"] + _cd_state["s_f"] + _cd_state["skipped"] >= _cd_state["total"] > 0:
            _cd_ev.set()
            if _cd_state["s_o"] == 0:
                _d_ev.set()  # 无人需要 D，直接解锁 D 屏障
    await _cd_mark_done()



async def _cd_count_smoke_ok():
    """C 完成 + smoke 通过：s_o++。检查屏障1（>= total）→ 等待 C→D 解锁。"""
    global _cd_state, _cd_ev
    async with _cd_lk:
        _cd_state["s_o"] += 1
        if _cd_state["b_p"] + _cd_state["s_o"] + _cd_state["s_f"] + _cd_state["skipped"] >= _cd_state["total"] > 0:
            _cd_ev.set()
    await _cd_ev.wait()



async def _cd_count_smoke_failed():
    """C 完成 + smoke 失败：s_f++。检查屏障1（>= total）。标记完成。"""
    global _cd_state, _cd_ev, _d_ev
    async with _cd_lk:
        _cd_state["s_f"] += 1
        if _cd_state["b_p"] + _cd_state["s_o"] + _cd_state["s_f"] + _cd_state["skipped"] >= _cd_state["total"] > 0:
            _cd_ev.set()
            if _cd_state["s_o"] == 0:
                _d_ev.set()  # 无人需要 D，直接解锁 D 屏障
    await _cd_mark_done()



async def _cd_count_d_passed():
    """D 通过：d_p++。检查 d_p+d_f>=s_o → 解锁 D→下轮。"""
    global _cd_state, _d_ev
    async with _cd_lk:
        _cd_state["d_p"] += 1
        if _cd_state["d_p"] + _cd_state["d_f"] >= _cd_state["s_o"] and _cd_state["s_o"] > 0:
            _d_ev.set()



async def _cd_count_d_failed():
    """D 失败：d_f++。检查 d_p+d_f>=s_o → 解锁 D→下轮。"""
    global _cd_state, _d_ev
    async with _cd_lk:
        _cd_state["d_f"] += 1
        if _cd_state["d_p"] + _cd_state["d_f"] >= _cd_state["s_o"] and _cd_state["s_o"] > 0:
            _d_ev.set()



async def _d_barrier_wait():
    """等待 D→下一轮 解锁。注意：不在这里调 _cd_mark_done（由 D 任务调用方负责）。"""
    global _d_ev
    await _d_ev.wait()



async def _execute_single_task(
    task: dict, workspace: str, max_attempts: int, model,
    layer_truths: dict = None, task_map: dict = None,
) -> TaskTestState:
    task_id = task.get("id", "unknown")
    state = _load_state(task_id)
    # 上一轮失败 → 本轮开始前清理旧产物（测试文件/ban/真理），给A重新生成的机会
    if state.done and not state.is_ts_ss:
        if state.test_file_path:
            tp = Path(state.test_file_path)
            if tp.exists(): tp.unlink()
        clear_bans(task_id, "test_failure"); clear_bans(task_id, "source_failure")
        # 清除过期真理（上次通过但本次失败 → 真理已失效）
        old_truth = TRUTH_DIR_TEST / f"{task_id}.json"
        if old_truth.exists():
            old_truth.unlink()
        state.test_success = False; state.source_success = False; state.test_file_path = None
        state.done = False; _save_state(state)
    for attempt in range(1, max_attempts + 1):
        state.attempt = attempt
        # 🛑 每轮 attempt 开始时重置屏障计数器（本 attempt 内所有 C 必须完成 + 烟雾通过才解锁 D）
        _c_barrier_count = 0
        print(f"\n  [{task_id}] Attempt {attempt}/{max_attempts}, state={state.state_label}")
        try:
            return_val = await _attempt_once(task, state, attempt, max_attempts, workspace, model, layer_truths, task_map)
            if task.get("layer") == "integ" and not _DB_INITIALIZED and state.is_ts_ss:
                _init_database(Path(workspace), task_map.values() if task_map else [])
                # 同步 .env → .env.example / .env.development / .env.production
                _sync_env_files(Path(workspace))
            if return_val is not None:
                return return_val
        except Exception as exc:
            import traceback
            print(f"    [!] {exc}")
            traceback.print_exc()
            state.test_success = False; state.source_success = False
            _save_state(state); continue
    # 本轮未通过 → 标记 done，保留产物供排查。下一轮开始时才清理旧产物。
    if not state.is_ts_ss:
        state.test_file_path = None  # 测试文件路径可能已过期
    state.done = True; _save_state(state)
    return state



async def _attempt_once(
    task: dict, state: TaskTestState, attempt: int,
    max_attempts: int, workspace: str, model,
    layer_truths: dict = None,
    task_map: dict = None,
):
    task_id = task.get("id", "unknown")
    layer = task.get("layer", "")

    if state.is_ts_ss:
        return state

    test_type = task.get("testType") or _LAYER_TO_TYPE.get(layer, "logic")

    # ── Type 0: 静态层 — Agent 直接读源码+检查+修复，不写测试 ──
    if test_type == "static":
        return await _handle_static_task(task, state, attempt, workspace, model, task_map, layer_truths)

    # 非静态+非repair层：每个 attempt 注册到 barrier（去重，跨 attempt 自动重置）
    if layer != "repair":
        await _cd_register(task_id)

    fw = task.get("testFramework", "jest")
    target_files = task.get("targetFiles", task.get("path", []))
    ws = Path(workspace).resolve()
    current_source_hash = RedisCache.compute_source_hash(target_files, workspace)

    _SKIP_READ = {'package-lock.json', 'node_modules', '.git'}
    source_contents = {}
    for tf in target_files:
        if any(s in tf for s in _SKIP_READ):
            continue
        p = ws / tf
        if p.exists():
            try:
                source_contents[tf] = p.read_text(encoding='utf-8')
            except Exception as e:
                source_contents[tf] = f"[读取失败: {e}]"

    if state.test_file_path:
        tp = Path(state.test_file_path)
        if tp.exists():
            try:
                source_contents[f"__TEST_FILE__:{state.test_file_path}"] = tp.read_text(encoding='utf-8')
            except Exception:
                pass

    test_bans = get_bans(task_id, "test_failure")
    source_bans = get_bans(task_id, "source_failure")

    # ── 注入下层真理 ──
    lower_truths_text = _collect_dep_truths(task, task_map or {}, layer_truths or {})

    if attempt == 1:
        task_log_dir = AGENT_LOG_DIR / task_id
        if task_log_dir.exists():
            import shutil
            shutil.rmtree(str(task_log_dir))
    log_dir = str(AGENT_LOG_DIR / task_id / f"attempt_{attempt}")

    # ── 真理注入（A/B/C/D 都注入：A 需要知道上游真实字段名来写测试）──
    test_bans_text = format_bans_for_agent(test_bans)
    source_bans_text_raw = format_bans_for_agent(source_bans)
    # 组装：真理 + 历史 ban，用明确分隔线拆开
    _truth_section = lower_truths_text
    _test_ban_section = f"\n---\n## ⚠️ 历史测试 ban（上一轮的错误和修复指令）\n{test_bans_text}" if test_bans_text.strip() else ""
    _source_ban_section = f"\n---\n## ⚠️ 历史源码 ban\n{source_bans_text_raw}" if source_bans_text_raw.strip() else ""
    # 🆕 注入工作区目录结构（替代 list_dir 工具）
    _dir_tree = f"\n\n## 📁 工作区目录结构（已注入，不需要 list_dir）\n{_build_dir_tree(ws)}"
    # 🆕 前端任务：注入全局 + 本页专属 UI 设计规范
    _ui_styles_tree = ""
    if layer == "frontend":
        ui_dir = project_root / "Memory" / "ui_styles"
        if ui_dir.exists():
            ui_parts = []
            for name in ("_global", "_components"):
                fp = ui_dir / f"{name}.md"
                if fp.exists():
                    try:
                        ui_parts.append(fp.read_text('utf-8'))
                    except Exception:
                        pass
            # 本页专属 UI 文档
            ui_name = task.get("ui_style", "")
            if ui_name:
                fp = ui_dir / f"{ui_name}.md"
                if fp.exists():
                    try:
                        ui_parts.append(f"### {ui_name}\n{fp.read_text('utf-8')}")
                    except Exception:
                        pass
            if ui_parts:
                _ui_styles_tree = "\n\n## 🎨 UI 设计规范（Memory/ui_styles/，已预加载）\n\n" + "\n\n".join(ui_parts)
    a_bans_text = _truth_section + _test_ban_section + _dir_tree + _ui_styles_tree
    cd_bans_text = _truth_section + _source_ban_section + _dir_tree + _ui_styles_tree

    # ── A: 写测试 ──
    test_file_expected = ws / "test" / f"{task_id}.test.js"
    pre_written_exists = test_file_expected.exists()
    if pre_written_exists and not state.test_file_path:
        state.test_file_path = str(test_file_expected)
    skip_a = (state.test_success and state.test_file_path and Path(state.test_file_path).exists())

    if skip_a:
        print(f"    [a] SKIP")
    else:
        print(f"    [{task_id}] [a] Writing test...")
        wr = await run_test_writer(
            task=task, workspace_root=workspace, source_contents=source_contents,
            model_client=model, task_id=task_id, attempt=attempt,
            bans_text=a_bans_text, save_dir=log_dir + "/", save_filename="a_test_writer_token",
        )
        DebugLogger.save_raw(task_id, attempt, "a", "test_writer", wr.get("raw_output", ""))
        state.test_file_path = wr.get("test_file")

        validation_errors = wr.get("validation_errors", [])
        if validation_errors:
            # 只记录原始校验结果供 agent 参考，ban 由 B 步 agent 产出
            state._a_validation_errors = validation_errors
            state.test_success = False
            _save_state(state)

        if not wr["success"] and not validation_errors:
            state.test_success = False
            _save_state(state)
            if not state.test_file_path:
                await _cd_count_skipped()
                return None
        if not validation_errors:
            state.test_success = True

    # ── B: 运行测试 ──
    if not state.test_file_path:
        await _cd_count_skipped()
        return None
    if state.is_ts_ss:
        return state

    # 🆕 注入 A 步校验原始数据到 B 步 prompt（agent 产出 ban，Python 不创作）
    a_validation_context = ""
    if hasattr(state, '_a_validation_errors') and state._a_validation_errors:
        a_validation_context = "\n## 🔍 A 步语法校验原始结果（Python 硬校验，供 B 诊断参考）\n"
        for err in state._a_validation_errors:
            msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            a_validation_context += f"- {msg}\n"

    run_b = not state.test_success or not skip_a
    if not run_b:
        print(f"    [b] SKIP")
    else:
        print(f"    [{task_id}] [b] Running test...")
        br = await run_test_runner(
            test_file_path=state.test_file_path, test_framework=fw, workspace_root=workspace,
            step="b", model_client=model, task_id=task_id,
            bans=test_bans, source_contents=source_contents, task=task,
            extra_context=lower_truths_text + a_validation_context,
            save_dir=log_dir + "/", save_filename="b_test_runner_token",
        )
        total, failed = br.get("total", 0), br.get("failed", 0)
        DebugLogger.save_raw(task_id, attempt, "b", "test_runner", br.get("raw_output", ""))

        if total == 0:
            bans = br.get("bans", [])
            has_l0_source = any(
                b.get("f", "").startswith("L0|") or
                (len(b.get("f", "").split("|")) >= 2 and b.get("f", "").split("|")[1] == "source")
                for b in bans
            ) or br.get("fix_target") == "source"
            t_cnt, s_cnt = _store_bans_by_target(task_id, bans)
            if s_cnt > 0 or has_l0_source:
                state.test_success = True
                state.source_success = False
                _save_state(state)
                # 直接跳到 C
            else:
                state.test_success = False
                state.source_success = False
                _save_state(state)
                await _cd_count_skipped()
                return None

        if failed == 0 and total > 0:
            await _cd_count_b_passed()  # B 全部通过: b_p++，计入屏障
            # 提取真理 + 评分入库 (total>0 & failed==0: B步骤首次全部通过)
            interface = await _extract_test_interface(task, source_contents, workspace, task_id, model)
            if interface:
                state.truth = interface
                saved = _save_truth(task_id, {"task_id": task_id, "type": layer,
                    "description": task.get("description", ""), "exposed": interface})
                if not saved and not _IS_LAST_LEVEL:
                    print(f"    [{task_id}] B通过但真理保存失败，不通过")
                    state.test_success = False; state.source_success = False
                    _save_state(state)
                    return None
            elif not _IS_LAST_LEVEL:
                print(f"    [{task_id}] B通过但未提取到真理（interface为空），不通过")
                state.test_success = False; state.source_success = False
                _save_state(state)
                return None
            state.test_success = True
            state.source_success = True
            state.done = True
            await _score_and_store(task, br, workspace, task_id, attempt, log_dir, state.test_file_path)
            _save_state(state)
            return state

        if failed > 0:
            t_cnt, s_cnt = _store_bans_by_target(task_id, br.get("bans", []))
            if t_cnt > 0:
                # 测试代码有问题 → 保留文件让A在修复模式下 edit_batch 定点改（不删除重写）
                state.test_success = False
                state.source_success = False
                _save_state(state)
                print(f"    [fix] B判测试问题（{t_cnt}条ban），保留文件，下轮A修复模式 edit_batch 定点改")
                await _cd_count_skipped()
                return None
            if s_cnt > 0:
                state.test_success = True
                state.source_success = False

    # ── C: 修复源码 ──
    if not state.test_success and not state.source_success:
        await _cd_count_skipped()  # 测试有问题, 下一轮A重写
        return None

    if state.source_success:
        return state

    print(f"    [{task_id}] [c] Fixing source...")
    _save_state(state)
    await RedisCache.save_source_snapshot(task_id, current_source_hash, target_files, workspace)

    # 🛑 B 可能刚存入了新的 source ban，必须刷新加载（不能用 A 之前加载的旧变量）
    source_bans = get_bans(task_id, "source_failure")
    test_bans = get_bans(task_id, "test_failure")

    # ── C/D 步骤只看消费者代码（所有 targetFiles 均可修改）──
    consumer_files = target_files

    # 🛑 从 source ban 提取需要读取/修复的文件（C 步按需读取，不全量注入 targetFiles）
    ban_mentioned_files = set()
    for b in source_bans:
        if isinstance(b, dict):
            f_val = b.get("f", "")
            parts = f_val.split("|")
            if len(parts) >= 3:
                ban_file = parts[2].split(":")[0]
                if ban_file and not ban_file.startswith("?") and not ban_file.startswith("test/"):
                    ban_mentioned_files.add(ban_file)

    current_source_contents = {}
    # 🛑 只注入 ban 提到的文件（D 已分析出问题所在，不需要全量注入 targetFiles）
    for tf in sorted(ban_mentioned_files):
        p = ws / tf
        if p.exists():
            try:
                current_source_contents[tf] = p.read_text(encoding='utf-8')
            except Exception:
                pass
    # 🛑 如果 ban 没提到任何文件（异常情况），回退注入全部 targetFiles
    if not current_source_contents:
        for tf in consumer_files:
            if any(s in tf for s in _SKIP_READ):
                continue
            p = ws / tf
            if p.exists():
                try:
                    current_source_contents[tf] = p.read_text(encoding='utf-8')
                except Exception:
                    pass

    # C 需要: 下层真理 + 最新源码侧 ban
    c_bans_text = lower_truths_text + "\n\n" + format_bans_for_agent(source_bans)

    c_task = {**task, "targetFiles": consumer_files}
    cr = await run_source_fixer(
        task=c_task, test_file_path=state.test_file_path, workspace_root=workspace,
        source_contents=current_source_contents, model_client=model, task_id=task_id,
        attempt=attempt, bans_text=c_bans_text,
        save_dir=log_dir + "/", save_filename="c_source_fixer_token",
    )
    DebugLogger.save_raw(task_id, attempt, "c", "source_fixer", cr.get("raw_output", ""))
    if not cr["success"]:
        state.test_success = False
        state.source_success = False
        _save_state(state)
        await _cd_count_skipped()
        return None

    # 🛑 烟雾检测：C 修完后检查语法（含 ban 扩展文件）
    smoke_issues = _smoke_check(ws, consumer_files)
    if smoke_issues:
        print(f"    [smoke] C 修改导致 {len(smoke_issues)} 个问题，回滚源码")
        await RedisCache.rollback_to_best(task_id, target_files, workspace)
        for issue in smoke_issues[:3]:
            _store_bans_by_target(task_id, [{"f": f"{layer}|source|smoke|REGRESSION",
                "b": f"DON'T: C 修改导致服务无法启动 — {issue} | fix: 回滚后重新修复，确保 node --check 通过且 app.js 可加载 | target=source"}])
        state.source_success = False
        _save_state(state)
        # s_f++：smoke 失败，不进入 D，不等 C→D 锁
        await _cd_count_smoke_failed()
        return None

    new_source_hash = RedisCache.compute_source_hash(target_files, workspace)
    # D 与 C 同理：消费者文件 + ban 扩展文件
    post_c_source = {}
    for tf in consumer_files:
        p = ws / tf
        if p.exists():
            try:
                post_c_source[tf] = p.read_text(encoding='utf-8')
            except Exception:
                pass

    # s_o++：smoke 通过，注册并等待 C→D 屏障（所有 B/C+smoke 完成后才进入 D）
    await _cd_count_smoke_ok()

    # ── D: 验证修复 ──
    print(f"    [{task_id}] [d] Verifying fix...")
    # 刷新 ban（C 可能已修改，B/C 可能存入了新的诊断）
    source_bans = get_bans(task_id, "source_failure")
    dr = await run_test_runner(
        test_file_path=state.test_file_path, test_framework=fw, workspace_root=workspace,
        step="d", model_client=model, task_id=task_id,
        bans=source_bans, source_contents=post_c_source, task=task,
        extra_context=lower_truths_text,
        save_dir=log_dir + "/", save_filename="d_test_runner_token",
    )
    d_total, d_failed = dr.get("total", 0), dr.get("failed", 0)
    DebugLogger.save_raw(task_id, attempt, "d", "test_runner", dr.get("raw_output", ""))

    if d_total == 0 or d_failed > 0:
        _store_bans_by_target(task_id, dr.get("bans", []))
        state.test_success = True
        state.source_success = False
        _save_state(state)
        await _cd_count_d_failed()    # d_f++，检查屏障2
        await _d_barrier_wait()       # 等所有 D 完成
        await _cd_mark_done()         # D 任务完成，标记贡献
        return None

    interface = await _extract_test_interface(task, post_c_source, workspace, task_id, model)
    if interface:
        state.truth = interface
        saved = _save_truth(task_id, {"task_id": task_id, "type": layer,
            "description": task.get("description", ""), "exposed": interface})
        if not saved and not _IS_LAST_LEVEL:
            print(f"    [{task_id}] D通过但真理保存失败，不通过")
            state.test_success = False; state.source_success = False; state.done = True
            _save_state(state)
            await _cd_count_d_failed(); await _d_barrier_wait(); await _cd_mark_done()
            return None
    elif not _IS_LAST_LEVEL:
        print(f"    [{task_id}] D通过但未提取到真理（interface为空），不通过")
        state.test_success = False; state.source_success = False; state.done = True
        _save_state(state)
        await _cd_count_d_failed(); await _d_barrier_wait(); await _cd_mark_done()
        return None

    state.test_success = True
    state.source_success = True
    state.done = True
    state.source_hash = new_source_hash
    await _score_and_store(task, dr, workspace, task_id, attempt, log_dir, state.test_file_path)
    _save_state(state)
    await _cd_count_d_passed()     # d_p++，检查屏障2
    await _d_barrier_wait()        # 等所有 D 完成
    await _cd_mark_done()          # D 任务完成，标记贡献
    return state




async def _score_and_store(task, test_result, workspace, task_id, attempt, log_dir, test_file_path):
    """评分 + 高分自动入库 (左脑数据来源)。"""
    try:
        from Tools.scoring.code_scorer import score_code, score_test_code, format_score_report
        from Tools.memory.ban_memory import get_bans as _get_bans

        target_files = task.get("targetFiles", [])
        ws = Path(workspace).resolve()
        source_files = {}
        for tf in target_files:
            fp = ws / tf
            if fp.exists():
                source_files[tf] = fp.read_text("utf-8")

        if not source_files:
            return

        src_mem = _get_bans(task_id, "source_failure")
        test_mem = _get_bans(task_id, "test_failure")
        jest_output = {"numTotalTests": test_result.get("total", 0), "numPassedTests": test_result.get("passed", 0)}

        result = score_code(source_files=source_files, engineer_tasks=[task], test_tasks=None,
                           source_memory=src_mem, test_memory=test_mem, test_output=jest_output)

        # 源码 >= 70 (A级) 入库，积累代码参考库
        if result.total >= 70:
            try:
                from Tools.rag.code_retrieval.code_store import store_code
                store_code(code_files=source_files, task_id=task_id, task_type=task.get("layer", "backend_proc"),
                          contracts=task.get("usesContracts", []), code_score=result.total, code_level=result.level)
                print(f"    [score] 源码入库: {len(source_files)} files (score={result.total:.0f})")
            except Exception:
                pass

        # 测试代码 >= 70 (A级) 入库
        if test_file_path and Path(test_file_path).exists():
            test_code = Path(test_file_path).read_text("utf-8")
            test_result_obj = score_test_code(test_content=test_code, task=task,
                                              test_output=jest_output, test_bans=test_mem)
            if test_result_obj.total >= 70:
                try:
                    from Tools.rag.code_retrieval.code_store import store_test_code
                    store_test_code(code_files={Path(test_file_path).name: test_code}, task_id=task_id,
                                   test_layer=task.get("layer", ""), test_framework=task.get("testFramework", "jest"),
                                   test_score=test_result_obj.total, test_level=test_result_obj.level)
                    print(f"    [score] 测试入库: {Path(test_file_path).name} (score={test_result_obj.total:.0f})")
                except Exception:
                    pass

        # 保存评分报告
        if log_dir:
            import os as _os
            _os.makedirs(log_dir, exist_ok=True)
            from datetime import datetime
            score_log = {"task_id": task_id, "attempt": attempt, "total": result.total, "level": result.level,
                        "timestamp": datetime.now().isoformat(), "source_files": list(source_files.keys())}
            with open(_os.path.join(log_dir, "code_score.json"), "w", encoding="utf-8") as f:
                json.dump(score_log, f, indent=2, ensure_ascii=False)
    except Exception:
        pass



async def _extract_test_interface(task, source_contents, workspace, task_id, model) -> dict:
    """测试通过后提取对外接口。Agent 主生成 + Python 验证回退。"""
    layer = task.get("layer", "")
    target_files = task.get("targetFiles", [])
    ws = Path(workspace).resolve()

    # ── 1. 读取上层测试真理（测试阶段产出）──
    engineer_truth = {}

    # ── 2. 读取实际生成的文件内容 ──
    file_contents = {}
    for tf_path in target_files:
        fp = ws / tf_path
        if fp.exists():
            try:
                file_contents[tf_path] = fp.read_text("utf-8")[:8000]
            except Exception:
                pass

    if not file_contents:
        return task.get("produces", {})

    # ── 3. Agent 主生成: LLM 精读源码 + truth → 结构化接口 ──
    prompt = _load_truth_prompt(layer)
    context = f"任务: {task.get('description', '')}\n测试层: {layer}\n测试场景: {json.dumps(task.get('testScenarios', []), ensure_ascii=False)[:2000]}"
    files_block = "\n\n".join(f"### {p}\n```\n{c}\n```" for p, c in file_contents.items())
    instructions = prompt.replace("{context}", context).replace("{files}", files_block)

    extract_agent = Agent(
        name=f"truth_extractor_{task_id}",
        description="接口提取器 — 只读不写",
        instructions=instructions,
        model_client=model,
        tools=[],
        max_iterations=1,
    )

    collected = ""
    try:
        async for event in extract_agent.run_stream("提取对外暴露接口，输出 JSON。", stream_tokens=False):
            collected += str(event)
    except Exception:
        pass

    interface = extract_json(collected)
    if isinstance(interface, dict) and interface:
        return interface

    # ── 4. Python 回退: Agent 失败时用正则扫描 ──
    return _scan_interface_from_files(layer, file_contents, target_files, engineer_truth, ws)




class RedisCache:
    _redis_available: Optional[bool] = None
    _snapshot_dir = project_root / "Memory" / "snapshots"

    @classmethod
    async def _ensure_available(cls) -> bool:
        if cls._redis_available is not None:
            return cls._redis_available
        global _redis_client
        try:
            _redis_client = await aioredis.from_url(REDIS_URL, decode_responses=True)
            await _redis_client.ping()
            cls._redis_available = True
        except Exception as e:
            cls._redis_available = False
            _redis_client = None
            cls._snapshot_dir.mkdir(parents=True, exist_ok=True)
            print(f"[scheduler] Redis 不可用({e})，降级到文件快照")
        return cls._redis_available

    @staticmethod
    def compute_source_hash(target_files: List[str], workspace: str) -> str:
        hasher = hashlib.md5(usedforsecurity=False)
        ws = Path(workspace).resolve()
        for tf in sorted(target_files):
            src = ws / tf
            if src.is_file():
                hasher.update(src.read_bytes())
        return hasher.hexdigest()[:16]

    @classmethod
    def _best_file(cls, task_id: str) -> Path:
        return cls._snapshot_dir / f"best_{task_id}.json"

    @classmethod
    def _snap_file(cls, task_id: str, source_hash: str) -> Path:
        return cls._snapshot_dir / f"snap_{task_id}_{source_hash}.json"

    @classmethod
    async def get_best(cls, task_id: str) -> Optional[Dict[str, Any]]:
        fp = cls._best_file(task_id)
        if fp.exists():
            try:
                return json.loads(fp.read_text("utf-8"))
            except Exception:
                pass
        if await cls._ensure_available():
            try:
                data = await _redis_client.hgetall(f"test_scheduler:best:{task_id}")
                if data:
                    return {
                        "best_score": float(data.get("best_score", 0)),
                        "best_attempt": int(data.get("best_attempt", 0)),
                        "source_hash": data.get("source_hash", ""),
                    }
            except Exception:
                pass
        return None

    @classmethod
    async def set_best(cls, task_id: str, attempt: int, score: float,
                       source_hash: str, test_result: dict):
        data = {"best_score": score, "best_attempt": attempt, "source_hash": source_hash, "test_result": test_result}
        fp = cls._best_file(task_id)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
        if await cls._ensure_available():
            try:
                await _redis_client.hset(f"test_scheduler:best:{task_id}", mapping={
                    "best_score": score, "best_attempt": attempt,
                    "source_hash": source_hash,
                    "test_result": json.dumps(test_result, ensure_ascii=False),
                })
            except Exception:
                pass

    @classmethod
    async def save_source_snapshot(cls, task_id: str, source_hash: str,
                                   target_files: List[str], workspace: str):
        if not target_files:
            return
        ws = Path(workspace).resolve()
        snap = {}
        for tf in target_files:
            src = ws / tf
            if src.exists():
                snap[tf] = src.read_text("utf-8")
        if snap:
            fp = cls._snap_file(task_id, source_hash)
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(json.dumps(snap, indent=2, ensure_ascii=False), "utf-8")

    @classmethod
    async def restore_source_snapshot(cls, task_id: str, source_hash: str,
                                      target_files: List[str], workspace: str) -> int:
        fp = cls._snap_file(task_id, source_hash)
        if not fp.exists():
            return 0
        try:
            snap = json.loads(fp.read_text("utf-8"))
        except Exception:
            return 0
        ws = Path(workspace).resolve()
        restored = 0
        for tf, content in snap.items():
            dst = ws / tf
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(content, "utf-8")
            restored += 1
        return restored

    @classmethod
    async def rollback_to_best(cls, task_id: str, target_files: List[str],
                               workspace: str) -> Tuple[int, float, int]:
        best = await cls.get_best(task_id)
        if not best or not best.get("source_hash"):
            return (0, 0, 0)
        restored = await cls.restore_source_snapshot(
            task_id, best["source_hash"], target_files, workspace)
        return (best["best_attempt"], best["best_score"], restored)





# ═══════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════

async def run_scheduler(
    workspace: str = "./work/project",
    test_tasks_file: str = "./work/project/test/test_tasks.json",
    fast: bool = False,
    max_total_attempts: int = 3,
    max_concurrent: int = MAX_CONCURRENT,
    model_client=None,
) -> Dict[str, Any]:
    from utils.token_tracker import record_stage
    record_stage("测试与修复", phase="start")
    t0 = datetime.now()
    ws_path = Path(workspace).resolve()
    tasks_file = Path(test_tasks_file)
    if not tasks_file.exists():
        return {"error": f"test_tasks.json not found: {test_tasks_file}"}
    tasks_data = json.loads(tasks_file.read_text("utf-8"))
    all_tasks = tasks_data.get("testTasks", [])
    if not all_tasks:
        return {"error": "No test tasks found"}
    print(f"[scheduler] Loaded {len(all_tasks)} test tasks")

    # 🛑 启动时清理上一轮失败任务的旧产物，防止脏数据污染本轮（已通过的保留）
    # 任务运行前删除 → 本轮运行结束后日志完整保留，便于人工排查
    import shutil
    _clean_round_artifacts()

    _fix_jest_test_match(ws_path)
    _ensure_npm_install(ws_path, all_tasks)
    _check_frontend_test_infra(ws_path, all_tasks)
    from utils.placeholder_files import ensure as _ensure_placeholders
    _ensure_placeholders(ws_path)  # Python 自动生成占位文件
    _verify_jest_working(ws_path)
    _check_k6_available()

    if model_client is None:
        from utils.model_client import get_model_client
        model_client = get_model_client()
    model = model_client

    if fast:
        await _fast_jest_sweep(ws_path)

    # ── 预过滤: 移除 targetFiles 中不存在的文件（防止 test_architect 编造的文件名导致死循环）──
    for t in all_tasks:
        tfs = t.get("targetFiles", [])
        if tfs:
            existing = [tf for tf in tfs if (ws_path / tf).exists()]
            removed = len(tfs) - len(existing)
            if removed and existing:  # 至少保留 1 个文件，不能全删
                print(f"  [prune-targetFiles] {t['id']}: removed {removed} non-existent files from targetFiles: {set(tfs) - set(existing)}")
                t["targetFiles"] = existing
                # 同步移除对应 scenarios
                removed_files = set(tfs) - set(existing)
                t["testScenarios"] = [s for s in t.get("testScenarios", [])
                                      if not any(rf in s.get("given", "") + s.get("when", "") for rf in removed_files)]

    # ── 注入 layer（从 sourceTask 映射到原始 engineer 类型）──
    _inject_layer_from_task_file(ws_path, all_tasks)

    # ── 🆕 共享文件串行化: 多个任务 target 同一文件时，插入顺序依赖防止并发竞态 ──
    shared_files = _collect_shared_files(all_tasks)
    if shared_files:
        print(f"[scheduler] Shared file groups: {len(shared_files)} files, max concurrency={max(len(v) for v in shared_files.values())}")

    # ── 依赖图 ──
    task_map, levels = build_dependency_graph(all_tasks)
    print(f"\n[scheduler] Dependency graph: {len(levels)} levels")
    print_levels(levels)
    # 终端层标记：每轮 level 开始前更新，最后一层跳过真理检查

    completed: Dict[str, TaskTestState] = {}
    failed_task_ids: set = set()
    layer_truths: Dict[str, dict] = {}
    test_truths = _load_test_truths()
    for tid, truth_entry in test_truths.items():
        task_layer = task_map.get(tid, {}).get("layer", "")
        if task_layer:
            layer_truths.setdefault(task_layer, {})[tid] = truth_entry

    all_results = []
    summary = {"total": len(all_tasks), "passed": 0, "failed": 0, "blocked": 0, "manual_needed": 0}
    global_blocked = False

    for level_idx, level in enumerate(levels):
        if global_blocked:
            summary["blocked"] += len(level)
            continue

        layer_name = level[0].get("layer", "?") if level else "?"

        runnable = []
        for task in level:
            tid = task.get("id", "?")
            # 已通过（内存或磁盘）→ 直接跳过
            if tid in completed and completed[tid].is_ts_ss:
                continue
            disk_state = _load_state(tid)
            if disk_state.is_ts_ss:
                completed[tid] = disk_state
                continue
            deps_ok = all(dep in completed and completed[dep].is_ts_ss for dep in task.get("dependencies", []))
            if deps_ok:
                runnable.append(task)
            else:
                summary["blocked"] += 1

        skipped = len(level) - len(runnable)
        skip_info = f" ({skipped} already passed)" if skipped > 0 else ""
        print(f"\n{'='*50}\n Level {level_idx}: {len(runnable)}/{len(level)} tasks [{layer_name}]{skip_info}\n{'='*50}")
        global _IS_LAST_LEVEL
        _IS_LAST_LEVEL = (level_idx == len(levels) - 1)

        if not runnable:
            continue

        # 在 integ 层之前重新生成 db 脚本，防止 repair/db 层修改 schema 后产生偏差
        if layer_name == "integ":
            _ensure_db_scripts(ws_path)

        # 层前置检查：必要服务不可用 → 阻断整层，防止大量连接错误
        svc_blocked = _check_layer_services(layer_name, ws_path)
        if svc_blocked:
            print(f"  BLOCKED Level {level_idx}: {svc_blocked}")
            global_blocked = True
            for t in runnable:
                summary["blocked"] += 1
            continue

        sem = asyncio.Semaphore(max_concurrent)
        # 文件级信号量：同一文件同时只允许一个任务修改（防死锁：排序加锁）
        file_locks = {}
        def _get_file_lock(filepath: str) -> asyncio.Lock:
            if filepath not in file_locks:
                file_locks[filepath] = asyncio.Lock()
            return file_locks[filepath]

        async def run_one(t):
            test_type = t.get("testType") or _LAYER_TO_TYPE.get(t.get("layer", ""), "logic")
            # 文件锁：所有层都拿
            files = sorted(t.get("targetFiles", []))
            locks = [_get_file_lock(f) for f in files]
            for lk in locks:
                await lk.acquire()
            try:
                async with sem:
                    if t.get("layer") == "repair":
                        return await _handle_repair_task(t, str(ws_path))
                    else:
                        return await _execute_single_task(t, str(ws_path), max_total_attempts, model, layer_truths, task_map)
            finally:
                for lk in locks:
                    lk.release()

        # 🛑 初始化 C→D 屏障（每个 level 开始前，必须在 gather 之前）
        _init_c_barrier(ws_path, runnable)
        level_results = await asyncio.gather(*[run_one(t) for t in runnable], return_exceptions=True)

        level_all_passed = True
        for task, result in zip(runnable, level_results):
            tid = task["id"]
            if isinstance(result, Exception):
                print(f"  [{tid}] EXCEPTION: {result}")
                summary["failed"] += 1
                failed_task_ids.add(tid)
                level_all_passed = False
                continue

            state = result
            completed[tid] = state
            status = "passed" if state.is_ts_ss else "failed"
            if state.is_ts_ss:
                summary["passed"] += 1
                task_layer = task.get("layer", "")
                if task_layer and state.truth:
                    # 使用 engineer 真理格式: {exposed: {exposed_to_upper, exposed_to_peers}}
                    truth_entry = {
                        "task_id": tid,
                        "type": task.get("layer", ""),
                        "description": task.get("description", ""),
                        "exposed": state.truth,  # 直接存 dict，不 double-encode
                    }
                    layer_truths.setdefault(task_layer, {})[tid] = truth_entry["exposed"]
                    _save_truth(tid, truth_entry)
            else:
                summary["failed"] += 1
                failed_task_ids.add(tid)
                level_all_passed = False
            all_results.append({"task_id": tid, "status": status, "attempts": state.attempt})
            print(f"  [{tid}] {status} ({state.state_label})")

        if level_all_passed:
            print(f"  OK Level {level_idx}: all {len(runnable)} passed")
        else:
            global_blocked = True
            n_failed = sum(1 for t in runnable if t["id"] in failed_task_ids)
            print(f"  FAIL Level {level_idx}: {n_failed}/{len(runnable)} failed. downstream blocked.")

    if _redis_client:
        await _redis_client.close()

    elapsed = (datetime.now() - t0).total_seconds()
    print(f"\n[scheduler] {summary['passed']} passed, {summary['failed']} failed, "
          f"{summary['blocked']} blocked ({elapsed:.0f}s)")

    # 记录 Token 消耗
    try:
        balance = record_stage("测试与修复", phase="end", extra={"passed": summary["passed"], "failed": summary["failed"],
                                                     "blocked": summary["blocked"], "elapsed": elapsed})
        print(f"[token] 测试与修复 消耗: {balance.get('cost', '?')} CNY (余额: {balance.get('total', '?')})")
    except Exception as e:
        print(f"[token] 记录失败: {e}")

    result = {"summary": {**summary, "elapsed_seconds": elapsed}, "results": all_results}
    return result




# ═══════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════

async def main():
    import sys, glob
    ws = sys.argv[1] if len(sys.argv) > 1 else "./work/project"
    pattern = f"{ws}/test/test_tasks_*.json"
    files = sorted(glob.glob(pattern))
    tf = files[-1] if files else f"{ws}/test/test_tasks.json"
    fast = "--fast" in sys.argv

    prev_passed = None
    for rnd in range(1, 100):
        r = await run_scheduler(workspace=ws, test_tasks_file=tf, fast=fast)
        if "error" in r:
            print(f"Error: {r['error']}")
            break
        s = r["summary"]
        print(f"\nRound {rnd}: {s['passed']} passed, {s['failed']} failed, {s['blocked']} blocked")
        if s["passed"] == s["total"]:
            print("All passed!")
            break
        # 首轮必跑；后续只有在 passed 实际增加时才继续
        if prev_passed is not None and s["passed"] <= prev_passed:
            print(f"No progress (passed {s['passed']} <= {prev_passed}), stopping.")
            break
        prev_passed = s["passed"]


if __name__ == "__main__":
    asyncio.run(main())

