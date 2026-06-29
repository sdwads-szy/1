# agent/test_writer.py
"""
测试编写 Agent —— 调度器提供源码内容，Agent 不再读取文件。
"""

import asyncio, json, os, sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from picoagents import Agent
from dotenv import load_dotenv
from Tools.coding.create_files import create_files as _create_files
from Tools.coding.edit_lines import edit_batch as _edit_batch
from Tools.skill.load_skill import load_skill
from Tools.testing.npm_install import npm_install
from Tools.memory.ban_memory import get_bans, format_bans_for_agent
from utils.token import wrap_agent_stream

load_dotenv('./.env.example')
ROLE_PATH = parent_dir / "skill" / "test" / "roles" / "a_test_writer.md"

# 🛑 层专精角色: 不同层使用完全不同的 system prompt，LLM 不会被其他层的模式干扰
_LAYER_ROLE_MAP = {
    # 静态层 = 文件检查工程师
    "infra":           "a_static_check.md",
    "db":              "a_static_check.md",
    "frontend_static": "a_static_check.md",
    "peer_deps":       "a_static_check.md",
    # 接口层 = 连接点验证工程师
    "auth":            "a_interface_check.md",
    "api":             "a_interface_check.md",
    "db_api":          "a_interface_check.md",
    "navigation":      "a_interface_check.md",
    # 业务层 = 端到端验证工程师
    "backend_proc":    "a_logic_check.md",
    "logic":           "a_logic_check.md",
    "scenario":        "a_logic_check.md",
    "nfr":             "a_logic_check.md",
    "repair":          "a_static_check.md",
}

def load_role(task: dict = None) -> str:
    role = ""
    layer = task.get("layer", "") if task else ""

    # 🛑 层专精: 先加载该层的专属角色定义 (如果存在)
    role_file = _LAYER_ROLE_MAP.get(layer, "")
    role_path = parent_dir / "skill" / "test" / "roles" / role_file if role_file else None
    if role_path and role_path.exists():
        role = load_skill(str(role_path))
    else:
        # 层不在映射表中 = 配置错误，使用静态检查作为最安全兜底
        role = load_skill(str(parent_dir / "skill" / "test" / "roles" / "a_static_check.md"))

    if task:
        # 根据 layer 加载对应检查模板
        template_path = _pick_template(task)
        if template_path and template_path.exists():
            role += f"\n\n## 参考模板 [{layer}]（严格遵循结构，替换内容）\n" + load_skill(str(template_path))

        # 加载 layer 专属修复策略
        repair_text = _load_repair_strategy_by_layer(layer)
        if repair_text:
            role += repair_text

    return role


def _load_repair_strategy_by_layer(layer: str) -> str:
    """按 layer 加载测试修复策略。"""
    repair_dir = Path(__file__).parent.parent / "skill" / "test" / "repair" / "a"
    layer_file = repair_dir / f"{layer}.md"
    if layer_file.exists():
        return f"\n## 修复策略（{layer} 类型）\n{load_skill(str(layer_file))}\n"
    # 回退到 test_type
    return ""


def _build_env_real_mock_hint(workspace: str) -> str:
    """读取 .env.example，分析每个环境变量是真实值还是占位符。

    规则：
    - 值含 your_ / changeme / xxx / example / 空值 → 占位符 → 必须 mock
    - 值含 localhost / 具体IP / 真实密码 → 真实值 → 可用真实连接
    - 值含 your_domain / your- → 占位符 URL → 必须 mock

    返回格式化的 mock/real 决策表供 A 参考。
    """
    import re
    env_path = Path(workspace) / ".env.example"
    if not env_path.exists():
        return ""

    real_vars = []
    mock_vars = []

    for line in env_path.read_text("utf-8").split("\n"):
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, _, value = s.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        is_placeholder = (
            not value or
            "your_" in value.lower() or
            "changeme" in value.lower() or
            "xxx" in value.lower() or
            "example" in value.lower() or
            "your-" in value.lower() or
            "your_domain" in value.lower()
        )

        if is_placeholder:
            mock_vars.append((key, value if value else "(空)"))
        else:
            real_vars.append((key, value))

    if not real_vars and not mock_vars:
        return ""

    lines = ["## 🔌 环境变量分析：Mock vs Real 决策表\n",
             "根据 `.env.example` 的实际值判定哪些服务需要 mock：\n"]

    if real_vars:
        lines.append("### ✅ 可用真实连接的服务（值非占位符，说明真实可用）")
        for key, val in real_vars:
            lines.append(f"- `{key}={val}` → **直连**，不需要 mock")

    if mock_vars:
        lines.append("\n### ❌ 必须 mock 的服务（值是占位符或空，Agent 不可能知道真实密钥）")
        for key, val in mock_vars:
            lines.append(f"- `{key}={val}` → **必须 mock**")
        lines.append("\n这些服务的 mock 只需返回 jest.fn() 桩即可，不要尝试填真实值。")

    lines.append("\n**铁律**：真实连接的服务不 mock；占位符服务 mock 但只桩不填值。\n")
    return "\n".join(lines)


def _pick_template(task: dict):
    """根据 task 的 layer 选择对应测试模板。新架构: layer 决定测试类型。"""
    templates_dir = parent_dir / "skill" / "test" / "templates"
    layer = task.get("layer", "")
    targets = " ".join(task.get("targetFiles", []))

    # 新层模板映射 (优先按 layer)
    layer_templates = {
        "infra":           "infra_check.md",
        "db":              "db_check.md",
        "frontend_static": "frontend_static_check.md",
        "auth":            "auth_check.md",
        "db_api":          "db_api_check.md",
        "peer_deps":       "peer_deps_check.md",
        "api":             "api_check.md",
        "backend_proc":    "backend_proc_check.md",
        "navigation":      "navigation_check.md",
        "logic":           "logic_check.md",
        "scenario":        "scenario_check.md",
        "nfr":             "nfr_check.md",
        "repair":          "repair_check.md",
    }
    if layer in layer_templates:
        tmpl = templates_dir / layer_templates[layer]
        if tmpl.exists():
            return tmpl

    # 回退: 按 targetFiles 路径选模板
    if ".vue" in targets or "src/pages" in targets:
        return templates_dir / "frontend.md"
    if ".sql" in targets:
        return templates_dir / "db.md"
    if "middleware" in targets:
        return templates_dir / "middleware.md"
    if "routes/" in targets:
        return templates_dir / "route.md"
    if "service" in targets.lower():
        return templates_dir / "service.md"
    return templates_dir / "service.md"

def _test_subdir(category: str) -> str:
    return {
        "unit": "test/unit", "business": "test/business",
        "joint": "test/joint", "special": "test/special",
    }.get(category, "test/unit")


def _detect_module_format(source_contents: dict, target_files: list, workspace: str = "") -> str:
    """扫描每个源文件的模块格式，返回给 Agent 的提示文本。
    检测：ESM (import/export) vs CJS (require/module.exports) vs 混合。

    目的：防止 Agent 在 Jest CJS 环境里给 ESM 源码写 import 测试，
    或在 CJS 源码上用 vi.mock（Vitest API）而非 jest.mock。
    """
    import re
    hints = []
    for tf in target_files:
        src = ""
        if isinstance(source_contents.get(tf), dict):
            src = source_contents[tf].get("content", "")
        elif isinstance(source_contents.get(tf), str):
            src = source_contents[tf]
        else:
            # 尝试从磁盘读取（需要 workspace 前缀，因为 tf 是相对路径）
            p = (Path(workspace) / tf) if workspace else Path(tf)
            if p.exists():
                src = p.read_text("utf-8")

        if not src:
            continue

        has_import = bool(re.search(r'^\s*import\s+', src, re.MULTILINE))
        has_export = bool(re.search(r'^\s*export\s+', src, re.MULTILINE))
        has_require = bool(re.search(r'require\s*\(', src))
        has_module_exports = bool(re.search(r'module\.exports', src))

        if has_import or has_export:
            if ".vue" in tf or "src/pages" in tf or "src/stores" in tf:
                # Vitest 测试: ESM 源文件 → 测试也用 ESM import + vi.mock
                hints.append(
                    f"[ESM-Vitest] {tf} is ES module (import/export) — 这是前端 Vitest 测试\n"
                    f"    → 测试文件使用 ESM import 语法 + vi.mock/vi.hoisted()，"
                    f"    禁止使用 require() 和 jest.mock。\n"
                    f"    → import 路径使用 @/ 别名（vitest 原生支持）。"
                )
            else:
                hints.append(
                    f"[ESM] {tf} is ES module (import/export)\n"
                    f"    → Jest CJS 无法直接 require 该文件。测试必须 jest.mock 整个模块，"
                    f"或用 moduleNameMapper 映射。\n"
                    f"    → 测试文件本身必须用 CJS（jest.mock + require），禁止使用 import/vi.mock。"
                )
        elif has_require or has_module_exports:
            hints.append(
                f"[CJS] {tf} is CommonJS (require/module.exports)\n"
                f"    → 测试可直接 require 并调用导出函数。使用 jest.mock + jest.fn。"
            )
        else:
            hints.append(
                f"[UNKNOWN] {tf} module format unclear, check after read_files()."
            )

    if hints:
        return "## [!]源文件模块格式检测（严格遵循）\n" + "\n".join(hints) + "\n"
    return ""


def _detect_third_party_requires(source_contents: dict, target_files: list, workspace: str,
                                 category: str = "unit") -> set:
    """扫描源码中所有第三方包 require，返回需要 mock 的包名集合。

    对于 business 测试，额外扫描 app.js 的级联 require 链，
    因为加载 app.js 会触发所有中间件 → 所有第三方包。
    """
    import re
    builtins = {'fs', 'path', 'os', 'http', 'https', 'crypto', 'child_process', 'stream', 'util', 'url'}
    project_prefixes = {'.', '/', '..'}
    packages = set()

    # 对于 business 测试，app.js 的 require 链会级联加载所有包
    if category == "business":
        ws_path = Path(workspace)
        # 始终扫描 app.js（所有 business 测试的入口）
        app_paths = ["app.js", "src/app.js", "server.js", "index.js"]
        for app_path in app_paths:
            app_file = ws_path / app_path
            if app_file.exists():
                target_files = list(target_files) + [app_path]
                break

    for tf in target_files:
        # 尝试从 source_contents 获取，没有就从磁盘读
        src = source_contents.get(tf, {}).get("content", "") if isinstance(source_contents.get(tf), dict) else ""
        if not src:
            p = Path(workspace) / tf
            if p.exists():
                src = p.read_text("utf-8")
        if not src:
            continue

        for m in re.finditer(r"""require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)""", src):
            pkg = m.group(1)
            # 跳过项目内路径
            if any(pkg.startswith(prefix) for prefix in project_prefixes):
                continue
            # 跳过内置模块
            if pkg in builtins:
                continue
            # 跳过已 mock 的 db 相关 (由 mockSpec 处理)
            if 'db' in pkg.lower() or 'database' in pkg.lower():
                continue
            packages.add(pkg)

    return packages


def _load_mock_factories_config() -> dict:
    """从 config/mock_factories.json 加载 mock 工厂默认值。"""
    import json
    config_path = parent_dir / "config" / "mock_factories.json"
    try:
        return json.loads(config_path.read_text("utf-8")).get("factories", {})
    except Exception:
        from utils.logger import log_warning
        log_warning("failed to load mock_factories config", file=str(config_path))
        return {}


def _mock_factory(pkg: str, source_code: str = "") -> str:
    """根据包名 + 源码实际用法返回 mock 工厂函数。

    优先分析源码中对该包的实际调用方式，生成匹配的 mock；
    源码不可用时回退到通用桩。
    """
    import re

    # ── 源码可用时，分析实际用法 ──
    if source_code:
        usages = _extract_package_usages(pkg, source_code)
        if usages:
            return _build_mock_from_usages(pkg, usages)

    # ── 回退：从配置文件加载通用工厂 ──
    factories = _load_mock_factories_config()
    return factories.get(pkg, 'jest.fn()')


def _extract_package_usages(pkg: str, source: str) -> set:
    """从源码中提取对指定包的调用方式。返回 {'call', '.use()', '.get()', ...}"""
    import re
    usages = set()
    # 包的 require 变量名（如 const express = require('express') → var='express'）
    var_names = set()
    for m in re.finditer(rf'(?:const|let|var)\s+(\w+)\s*=\s*require\s*\(\s*[\'"]{re.escape(pkg)}[\'"]\s*\)', source):
        var_names.add(m.group(1))
    # 解构: const { Router } = require('express')
    for m in re.finditer(rf'(?:const|let|var)\s*\{{\s*([^}}]+)\}}\s*=\s*require\s*\(\s*[\'"]{re.escape(pkg)}[\'"]\s*\)', source):
        for name in re.findall(r'(\w+)', m.group(1)):
            var_names.add(name)
            usages.add(f'.{name}()')

    if not var_names:
        return usages

    for vn in var_names:
        # 作为函数调用: express()
        if re.search(rf'\b{vn}\s*\(', source):
            usages.add('call')
        # 方法调用: app.use(), app.get()
        for call_m in re.finditer(rf'\b{vn}\.(\w+)\s*\(', source):
            usages.add(f'.{call_m.group(1)}()')
        # 属性访问: app.locals
        for prop_m in re.finditer(rf'\b{vn}\.(\w+)\b(?!\s*\()', source):
            usages.add(f'.{prop_m.group(1)}')

    return usages


def _build_mock_from_usages(pkg: str, usages: set) -> str:
    """根据实际用法构建准确的 mock 工厂。"""
    if not usages:
        return 'jest.fn()'

    # express 常用模式
    if pkg == 'express':
        # app = express() → jest.fn(() => app_mock)
        props = []
        for u in sorted(usages):
            if u == 'call':
                continue  # express() 由外层的 jest.fn() 模拟
            if u.startswith('.') and u.endswith('()'):
                props.append(f'{u[1:-2]}: jest.fn()')
            elif u.startswith('.'):
                props.append(f'{u[1:]}: jest.fn()')
        if props:
            return f'jest.fn(() => {{ return {{ {", ".join(props)} }}; }})'

    # 中间件类: cors(), helmet(), morgan()
    if pkg in ('cors', 'helmet', 'morgan'):
        if 'call' in usages:
            return '() => (req, res, next) => next()'

    # 通用：返回对象字面量
    props = []
    for u in sorted(usages):
        if u == 'call':
            continue
        if u.startswith('.') and u.endswith('()'):
            props.append(f'{u[1:-2]}: jest.fn()')
        elif u.startswith('.'):
            props.append(f'{u[1:]}: jest.fn()')
    if props:
        return f'{{ {", ".join(props)} }}'

    return 'jest.fn()'


def _build_app_js_mock_block(target_files: list, workspace: str, category: str) -> str:
    """当测试目标包含 app.js 时，确定性生成完整 mock 块。
    LLM 不需要自己拼 mock 结构，只需填充测试场景。
    """
    import re
    ws = Path(workspace)
    app_js = ws / "app.js"
    if not app_js.exists():
        return ""

    app_content = app_js.read_text("utf-8")

    # 扫描 app.js 中的 require 调用
    route_requires = []
    middleware_requires = []
    config_requires = []
    for m in re.finditer(r"""(?:const|let|var)\s+(\w+)\s*=\s*require\s*\(\s*['\"](\.[^'\"]+)['\"]\s*\)""", app_content):
        var_name, path = m.group(1), m.group(2)
        if '/routes/' in path:
            route_requires.append((var_name, path))
        elif '/middleware/' in path:
            middleware_requires.append((var_name, path))
        elif '/config/' in path:
            config_requires.append((var_name, path))

    # 生成确定性 mock 块
    lines = []
    lines.append("// ====== 第三方包 Mock（确定性生成，不要修改） ======")
    lines.append("jest.mock('cors', () => () => (req, res, next) => next());")
    lines.append("jest.mock('helmet', () => () => (req, res, next) => next());")
    lines.append("jest.mock('morgan', () => () => (req, res, next) => next());")
    lines.append("jest.mock('dotenv', () => ({ config: jest.fn() }));")
    lines.append("jest.mock('winston', () => ({")
    lines.append("  createLogger: jest.fn(() => ({ error: jest.fn(), warn: jest.fn(), info: jest.fn(), debug: jest.fn() })),")
    lines.append("  format: { combine: jest.fn(), timestamp: jest.fn(), errors: jest.fn(), json: jest.fn(), printf: jest.fn(), colorize: jest.fn() },")
    lines.append("  transports: { Console: jest.fn(), File: jest.fn() }")
    lines.append("}));")
    lines.append("jest.mock('express', () => {")
    lines.append("  const mockJson = jest.fn(() => 'jsonParser');")
    lines.append("  const mockUrlencoded = jest.fn(() => 'urlencodedParser');")
    lines.append("  const app = { use: jest.fn(), get: jest.fn(), listen: jest.fn(), post: jest.fn(), put: jest.fn(), delete: jest.fn() };")
    lines.append("  const mockExpress = jest.fn(() => app);")
    lines.append("  mockExpress.json = mockJson;")
    lines.append("  mockExpress.urlencoded = mockUrlencoded;")
    lines.append("  mockExpress.static = jest.fn(() => (req, res, next) => next());")
    lines.append("  return mockExpress;")
    lines.append("});")
    lines.append("")

    # 中间件/配置/路由 mock — 路径从 test/unit/ 出发需加 ../../ 前缀
    for var_name, path in middleware_requires:
        test_path = '../../' + path.lstrip('./')
        lines.append(f"jest.mock('{test_path}', () => {{}});")

    for var_name, path in config_requires:
        test_path = '../../' + path.lstrip('./')
        lines.append(f"jest.mock('{test_path}', () => {{}});")

    for var_name, path in route_requires:
        test_path = '../../' + path.lstrip('./')
        # app.js 一定要 require 这些路由 → 必须 mock，不能 SKIP
        actual_file = ws / path.lstrip('./')
        if not actual_file.exists():
            actual_file = ws / (path.lstrip('./') + '.js')
        if actual_file.exists():
            lines.append(f"jest.mock('{test_path}', () => {{}});")
        else:
            lines.append(f"jest.mock('{test_path}', () => ({{}}), {{ virtual: true }});")

    lines.append("")
    lines.append("// ====== 测试代码（在下方编写 describe/it 块） ======")
    lines.append("// 注意：本测试文件位于 test/unit/，所有项目内 require 路径需加 ../../ 前缀")
    lines.append("")
    lines.append("")

    return "## [!]完整 Mock 块（已确定性生成，直接复制到 create_file 中，不要修改 mock 部分！）\n```javascript\n" + "\n".join(lines) + "\n```\n"


def _build_smoke_env_template() -> str:
    """t_smoke_env 确定性模板——mock 匹配 init-db.js/seed-users.js 实际依赖。"""
    return """// ====== t_smoke_env 确定性模板 ======

jest.mock('dotenv', () => ({ config: jest.fn() }));
jest.mock('bcrypt', () => ({
  hash: jest.fn().mockResolvedValue('hashed_password')
}));
jest.mock('../../config/db', () => ({
  testConnection: jest.fn().mockResolvedValue(true),
  query: jest.fn().mockResolvedValue([{ affectedRows: 1 }])
}));
jest.mock('../../config/logger', () => ({
  info: jest.fn(),
  error: jest.fn()
}));

const mockExit = jest.spyOn(process, 'exit').mockImplementation(() => {});

const dotenv = require('dotenv');
const db = require('../../config/db');
const logger = require('../../config/logger');
const bcrypt = require('bcrypt');
const pkg = require('../../package.json');

describe('t_smoke_env', () => {
  // NO beforeEach(clearAllMocks) at outer describe
  // -- it clears mock calls from beforeAll require()

  describe('package.json', () => {
    it('name and version defined', () => {
      expect(pkg.name).toBeTruthy();
      expect(pkg.version).toBeTruthy();
    });
    it('has required scripts: db, backend', () => {
      expect(pkg.scripts).toHaveProperty('db');
      expect(pkg.scripts).toHaveProperty('backend');
    });
    it('has core dependencies: express, mysql2, jsonwebtoken', () => {
      expect(pkg.dependencies).toHaveProperty('express');
      expect(pkg.dependencies).toHaveProperty('mysql2');
      expect(pkg.dependencies).toHaveProperty('jsonwebtoken');
    });
    it('has devDependencies: jest, @vue/test-utils, supertest', () => {
      expect(pkg.devDependencies).toHaveProperty('jest');
      expect(pkg.devDependencies).toHaveProperty('@vue/test-utils');
      expect(pkg.devDependencies).toHaveProperty('supertest');
    });
  });

  describe('init-db.js', () => {
    let configCalls, testConnCalls;
    beforeAll(async () => {
      jest.clearAllMocks();
      require('../../scripts/init-db');
      await new Promise(resolve => setImmediate(resolve));
      configCalls = dotenv.config.mock.calls.length;
      testConnCalls = db.testConnection.mock.calls.length;
    });

    it('dotenv.config() called', () => {
      expect(configCalls).toBeGreaterThanOrEqual(1);
    });
    it('db.testConnection() called', () => {
      expect(testConnCalls).toBeGreaterThanOrEqual(1);
    });
    it('logs success and exits with 0', () => {
      expect(logger.info).toHaveBeenCalledWith('数据库连接成功');
      expect(logger.info).toHaveBeenCalledWith('数据库初始化完成');
      expect(process.exit).toHaveBeenCalledWith(0);
    });
  });

  describe('seed-users.js', () => {
    beforeAll(async () => {
      jest.clearAllMocks();
      require('../../scripts/seed-users');
      await new Promise(resolve => setImmediate(resolve));
    });

    it('bcrypt.hash called twice with saltRounds=10', () => {
      expect(bcrypt.hash).toHaveBeenCalledTimes(2);
      expect(bcrypt.hash).toHaveBeenNthCalledWith(1, 'admin123', 10);
      expect(bcrypt.hash).toHaveBeenNthCalledWith(2, 'test123', 10);
    });
    it('INSERT admin with role=admin', () => {
      expect(db.query).toHaveBeenCalledWith(
        expect.stringContaining('INSERT INTO users'),
        ['admin', 'hashed_password', 'admin']
      );
    });
    it('INSERT testuser with role=consumer', () => {
      expect(db.query).toHaveBeenCalledWith(
        expect.stringContaining('INSERT INTO users'),
        ['testuser', 'hashed_password', 'consumer']
      );
    });
    it('logs seed success and exits with 0', () => {
      expect(logger.info).toHaveBeenCalledWith('种子数据创建完成');
      expect(process.exit).toHaveBeenCalledWith(0);
    });
  });
});"""



def _validate_test_file(file_path: str, scenarios: list, framework: str = "jest",
                        task_id: str = "") -> list:
    """硬校验：语法 + 禁止模式 + mock 完整性。
    返回 list[dict]，每项 {'type': 子类型, 'message': 错误描述}。空列表=通过。
    子类型: syntax | MOCK_GAP | MOCK_DUP | MISSING_MOCK | BANNED_PATTERN | MISSING_CLEARALL

    语法检查使用两层策略：
      1. node --check 快速扫描（毫秒级）
      2. 若 node --check 失败，用 npx jest 实际运行验证（秒级）
         因为 node --check 对 jest.mock hoisting / 顶层裸 require 存在误报

    冒烟测试例外 (t_smoke_*): 跳过 BANNED_PATTERN + BLOCK_INTEGRITY，
    因为冒烟测试运行 shell 命令，不遵循标准测试模板。
    """
    is_smoke = task_id.startswith("t_smoke_")
    import subprocess, re
    errors = []
    p = Path(file_path)
    if not p.exists():
        return [{"type": "syntax", "message": "文件不存在"}]

    is_vitest = framework == "vitest"
    content = p.read_text("utf-8")

    # 1. 语法检查
    if is_vitest:
        # vitest 测试使用 ESM import 语法，node --check 不支持
        # 跳过 node --check，用 vitest 本身验证
        pass
    else:
        r = subprocess.run(["node", "--check", str(p)], capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            err_lines = [l.strip() for l in (r.stderr or "").split('\n') if l.strip() and 'SyntaxError' in l]
            node_err_msg = err_lines[0][:120] if err_lines else r.stderr[:120]

            # 二次确认：用 Jest 实际运行，排除 node --check 对 jest.mock 的误报
            try:
                jest_r = subprocess.run(
                    ["npx", "jest", str(p), "--no-coverage", "--passWithNoTests"],
                    capture_output=True, text=True, timeout=60,
                    cwd=str(p.parent.parent.parent), encoding="utf-8", errors="replace",
                )
                jest_ok = "Test Suites:" in (jest_r.stdout + jest_r.stderr) and \
                          "failed to parse" not in jest_r.stderr and \
                          "SyntaxError" not in jest_r.stderr and \
                          "Unexpected token" not in jest_r.stderr
            except Exception:
                jest_ok = False

            if not jest_ok:
                errors.append({"type": "syntax", "message": f"语法错误(node+Jest双确): {node_err_msg}"})

    # 2. 禁止模式检查（冒烟测试跳过）
    if not is_smoke:
        banned = {
            "jest.isolateModules": "禁止使用 isolateModules",
            "jest.resetModules": "禁止使用 resetModules",
            "jest.doMock": "禁止使用 doMock",
            "@jest/globals": "禁止使用 @jest/globals — jest 在标准 Jest 环境中是全局变量，不需要 require/import",
        }
        for pattern, msg in banned.items():
            if pattern in content:
                errors.append({"type": "BANNED_PATTERN", "message": msg})

    # 3. Mock 完整性 (对照 mockSpec) → MOCK_GAP
    #    支持嵌套 mock 结构：createPool → {execute, getConnection} → {beginTransaction, commit, ...}
    all_mock_apis = set()
    for sc in scenarios:
        for api in (sc.get("mockSpec") or []):
            all_mock_apis.add(api)
    if all_mock_apis:

        def _balanced_braces(text: str, start: int) -> str:
            """从 text[start] 的 '{' 提取平衡括号内容（不含外层 {}）。"""
            depth = 0
            for i in range(start, len(text)):
                if text[i] == '{':
                    depth += 1
                elif text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        return text[start + 1:i]
            return ""

        def _extract_mock_keys(obj_body: str, external_mocks: dict) -> set:
            """从 JS 对象字面量中递归提取所有 mock key。
            处理: 顶层 jest.fn() key、嵌套 mockReturnValue({...})/mockResolvedValue({...})、
            以及对外部 mock 变量（如 mockConnection）的引用。
            """
            keys = set()
            # 1) 顶层 key: jest.fn(...) 或 key: mockVar 变量引用
            for m in re.finditer(r'(\w+)\s*:\s*(?:(?:jest|vi)\.fn\([^)]*\)|mock\w+)', obj_body):
                keys.add(m.group(1))
            # 2) 嵌套 mockReturnValue({...}) / mockResolvedValue({...})
            for m in re.finditer(r'\.mock(?:Return|Resolved)Value\s*\(\s*(\{)', obj_body):
                nested_body = _balanced_braces(obj_body, m.start(1))
                if nested_body:
                    keys.update(_extract_mock_keys(nested_body, external_mocks))
            # 3) mockResolvedValue(mockVar) / mockReturnValue(mockVar) 引用外部变量
            for m in re.finditer(r'\.mock(?:Return|Resolved)Value\s*\(\s*(mock\w+)\s*\)', obj_body):
                var_name = m.group(1)
                if var_name in external_mocks:
                    keys.update(external_mocks[var_name])
            return keys

        # 扫描外部 mock 对象定义: const/let/var mockXxx = { key1: jest.fn()/vi.fn(), ... }
        external_mocks = {}
        for m in re.finditer(r'(?:const|let|var)\s+(mock\w+)\s*=\s*\{', content):
            var_name = m.group(1)
            nested = _balanced_braces(content, m.end() - 1)
            if nested:
                ext_keys = set(re.findall(r'(\w+)\s*:\s*(?:jest|vi)\.fn\(', nested))
                if ext_keys:
                    external_mocks[var_name] = ext_keys

        # 遍历所有 mock 工厂（jest.mock 或 vi.mock），递归提取 mock key
        all_mocked = set()
        mock_re = r"(?:jest|vi)\.mock\(\s*['\"]([^'\"]+)['\"]\s*,\s*\(\)\s*=>\s*\(?\{"
        for m in re.finditer(mock_re, content):
            start = m.end() - 1  # '{' 的位置（匹配串以 { 结尾）
            body = _balanced_braces(content, start)
            if not body:
                # fallback: 从头用 depth 计数（兼容旧逻辑）
                depth_val = 0
                end = start
                for i in range(start, len(content)):
                    if content[i] == '{':
                        depth_val += 1
                    elif content[i] == '}':
                        depth_val -= 1
                        if depth_val == 0:
                            end = i + 1
                            break
                body = content[start + 1:end - 1] if end > start + 1 else content[start:end]
            # 判断是函数体（含 return 语句）还是隐式返回对象
            ret_m = re.search(r'return\s*(\{)', body)
            if ret_m:
                factory_body = _balanced_braces(body, ret_m.start(1))
            else:
                # 隐式返回对象: ()=>({...}) → body 即工厂对象内容
                # 去掉可能的外层 ()
                factory_body = body.strip()
                if factory_body.startswith('(') and factory_body.endswith(')'):
                    factory_body = factory_body[1:-1]
            if factory_body:
                all_mocked.update(_extract_mock_keys(factory_body, external_mocks))

        if all_mocked:
            missing = all_mock_apis - all_mocked
            if missing:
                errors.append({"type": "MOCK_GAP", "message": f"Mock API 缺失: {', '.join(sorted(missing))} (scenario 要求但 mock 工厂未包含)"})
        else:
            mock_name = "vi.mock" if is_vitest else "jest.mock"
            errors.append({"type": "MOCK_GAP", "message": f"未找到 {mock_name} 工厂定义"})

    # 4. beforeEach 检查
    if "beforeEach" in content:
        has_clear = "jest.clearAllMocks()" in content or "vi.clearAllMocks()" in content
        if not has_clear:
            need = 'vi.clearAllMocks()' if is_vitest else 'jest.clearAllMocks()'
            errors.append({"type": "MISSING_CLEARALL", "message": "beforeEach 缺少 " + need})

    # 5. 重复 mock 检测 → MOCK_DUP（jest.mock 和 vi.mock 都检查）
    mock_targets = re.findall(r"""(?:jest|vi)\.mock\s*\(\s*['\"]([^'\"]+)['\"]""", content)
    seen = {}
    for mt in mock_targets:
        if mt in seen:
            mock_api = "vi.mock" if is_vitest else "jest.mock"
            errors.append({"type": "MOCK_DUP", "message": f"{mock_api}('{mt}') 重复声明，后者覆盖前者"})
        else:
            seen[mt] = 1

    # 6. Business 测试第三方包 mock 清单检查 → MISSING_MOCK
    # smoke 测试不受此限制（它们自己管理 mock 结构）
    if task_id.startswith("t_smoke_"):
        pass
    elif "jest.mock('../../app'" in content or "require('../../app')" in content or \
         any("supertest" in line for line in content.split('\n')[:5]):
        business_required = ['express', 'dotenv', 'cors', 'helmet', 'morgan', 'winston']
        for pkg in business_required:
            if f"jest.mock('{pkg}'" not in content:
                errors.append({"type": "MISSING_MOCK", "message": f"Business 测试缺少 jest.mock('{pkg}')"})

    # 7. 闭包完整性检测 → BLOCK_INTEGRITY（冒烟测试跳过）
    if not is_smoke:
        closure_errors = _check_closure_integrity(content)
        errors.extend(closure_errors)

    # 8. Mock 可调用性校验 → MOCK_MISMATCH
    # 扫描源码中对 mock 模块的使用方式，与测试 mock 工厂做对比
    mock_errors = _check_mock_callability(content, scenarios, str(p.parent))
    errors.extend(mock_errors)

    # 9. Express mock 调用链校验 → MOCK_LAYER
    # 检测 mockExpress.json/mockExpress.urlencoded 是否多了 () => 包装
    mock_layer_errors = _check_mock_layer(content)
    errors.extend(mock_layer_errors)

    return errors


def _check_mock_layer(test_content: str) -> list:
    """检测 mock 工厂是否多了 () => 包装层，导致返回值类型不匹配。

    典型 Bug: mockExpress.json = () => mockJson
    正确:     mockExpress.json = mockJson
    """
    import re
    errors = []

    # 检测 express mock 中的 () => 多包装模式
    # Bug 模式: mockExpress.json = () => mockAnything（多了一层箭头函数）
    bug_pattern = re.search(
        r'mockExpress\.(\w+)\s*=\s*\(\)\s*=>\s*(mock\w+)',
        test_content
    )
    if bug_pattern:
        method = bug_pattern.group(1)
        var = bug_pattern.group(2)
        errors.append({
            "type": "MOCK_LAYER",
            "message": (
                f"mockExpress.{method} = () => {var} 多了 () => 包装层。"
                f"express.{method}() 会返回 {var}（jest.fn）而非调用结果。"
                f"应改为 mockExpress.{method} = {var}"
            )
        })

    return errors


def _check_mock_callability(test_content: str, scenarios: list, test_dir: str) -> list:
    """检测测试 mock 的返回值是否匹配源码中的调用方式。

    典型场景：
    - 源码: const instance = axios.create(); instance(config)  ← instance 被当作函数调用
    - 测试 mock: jest.mock('axios', () => ({ create: () => ({ get: jest.fn() }) }))
      → create 返回的 {get: jest.fn()} 不是函数 → MOCK_MISMATCH

    通过扫描测试中的 jest.mock 工厂 + 源码使用模式来检测。
    """
    import re
    errors = []

    # 从测试文件中提取所有 jest.mock 的模块名和工厂返回值结构
    mock_factories = {}
    for m in re.finditer(
        r"(?:jest|vi)\.mock\(['\"]([^'\"]+)['\"],\s*(?:\(\)\s*=>\s*)?(\{[\s\S]*?\})\s*\)",
        test_content
    ):
        module_name = m.group(1)
        factory_body = m.group(2)
        # 解析工厂返回值的顶层 key
        keys = re.findall(r'(\w+)\s*:', factory_body)
        # 检测哪些 key 的值是 jest.fn()（可调用）
        callable_keys = set(re.findall(
            r'(\w+)\s*:\s*(?:jest|vi)\.fn\(\)', factory_body
        ))
        non_callable_keys = set(keys) - callable_keys
        mock_factories[module_name] = {
            "callable": callable_keys,
            "non_callable": non_callable_keys,
            "body": factory_body,
        }

    # 对每个 scenario 的 mockSpec 检查：如果源码中某 API 需要返回可调用对象，
    # 但 mock 工厂返回的是普通对象，则标记
    for sc in scenarios:
        for api in (sc.get("mockSpec") or []):
            # api 格式示例: "create → instance", "instance.config → fn"
            parts = api.split(".")
            if len(parts) < 1:
                continue
            root_module = parts[0]  # 简化：假设第一个 token 匹配 mock 模块名

    # 简化版检测：检查常见模式
    # 模式1: jest.mock 返回非函数对象，但源码可能将其作为函数调用
    for module_name, factory in mock_factories.items():
        body = factory["body"]
        # 如果工厂返回 { create: jest.fn(() => obj), ... }，
        # 且 create 的返回值 obj 不是 jest.fn()，
        # 则源码中 instance(args) 会失败
        create_return = re.search(r'create\s*:\s*jest\.fn\s*\(\s*\(\s*\)\s*=>\s*(\{[\s\S]*?\})\s*\)', body)
        if create_return:
            inner = create_return.group(1)
            # 检查 inner 对象是否有 jest.fn() 作为顶层值
            if 'jest.fn()' not in inner:
                errors.append({
                    "type": "MOCK_MISMATCH",
                    "message": (
                        f"jest.mock('{module_name}'): create 返回 {inner[:50]}... "
                        f"不是可调用对象。如果源码中将其作为函数调用(如 instance(config))会报 TypeError。"
                        f"请用 jest.fn() 包装返回值, 并在返回值上挂载方法: "
                        f"const instance = jest.fn(); instance.get = jest.fn(); return instance;"
                    )
                })

    return errors


def _check_closure_integrity(content: str) -> list:
    """检测测试文件的闭包完整性。返回 BLOCK_INTEGRITY 类型错误列表。

    扫描每一行，跟踪当前是否在 it/describe/beforeEach/afterEach/beforeAll/afterAll
    闭包内。如果在闭包外发现 expect/断言语句，说明存在孤儿代码（edit_batch 破坏了闭包边界）。
    """
    import re
    errors = []
    lines = content.split('\n')

    # 闭包开始标记：覆盖所有 Jest/Vitest 标准块
    block_start_re = re.compile(
        r'^\s*(fdescribe|xdescribe|describe\.each|describe|'
        r'fit|xit|it\.only|test\.only|it\.skip|test\.skip|it|test|'
        r'beforeEach|afterEach|beforeAll|afterAll)\s*\('
    )
    # 闭包结束标记：独立一行的 }); 或 }) 或 } ) ; (允许空格和尾注释)
    block_end_re = re.compile(r'^\s*\}\s*\)\s*;?\s*(?://.*)?$')

    # 顶层合法语句（允许在闭包外出现）
    top_level_ok_re = re.compile(
        r'^\s*(const|let|var|import|export|'
        r'jest\.mock|jest\.fn|jest\.useFakeTimers|jest\.useRealTimers|'
        r'jest\.setTimeout|jest\.spyOn|jest\.requireActual|jest\.requireMock|'
        r'vi\.mock|vi\.fn|vi\.hoisted|vi\.useFakeTimers|vi\.useRealTimers|'
        r'vi\.spyOn|vi\.stubGlobal|'
        r'require\s*\(|module\.exports|process\.env|global\.|'
        r'//|/\*|\*|}|\)|$)'
    )

    depth = 0
    prev_stripped = ""
    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # 先检查 block 开始（增加深度）
        if block_start_re.search(line):
            depth += 1
            prev_stripped = stripped
            continue

        # 再检查 block 结束（减少深度）
        # ⚠️ 关键：mockResolvedValue({...}) 的 }); 不是测试块结束，不能减深度
        # 判定：如果前一行是 mock 数据（以 , 或 { 结尾），这个 }); 是数据闭合，不触发
        is_data_closure = (
            prev_stripped.endswith(',') or prev_stripped.endswith('{') or
            'mockResolvedValue' in prev_stripped or 'mockRejectedValue' in prev_stripped
        )
        if block_end_re.search(line) and depth > 0 and not is_data_closure:
            depth -= 1
            prev_stripped = stripped
            continue

        prev_stripped = stripped

        # 在闭包外（depth == 0），检测是否有可疑的执行语句
        if depth == 0 and stripped and not stripped.startswith('}'):
            if not top_level_ok_re.search(stripped):
                # 检测 expect/toHaveBeenCalled 等断言关键词
                # 注意: mockResolvedValue/mockRejectedValue 是 mock 准备，不是断言，不在此列
                if re.search(
                    r'\b(expect|toBe|toEqual|toContain|toMatch|toHaveBeen|'
                    r'toThrow|toHaveLength|toBeGreaterThan|toBeLessThan|'
                    r'\.not\.|'
                    r'\.resolves\.|\.rejects\.)\b',
                    stripped
                ):
                    errors.append({
                        "type": "BLOCK_INTEGRITY",
                        "message": f"行{i}: 断言/执行语句在闭包外（孤儿代码），可能是 edit_batch 破坏了 it/describe 边界"
                    })

    return errors


def _detect_test_type_from_task(target_files: list, category: str = "unit") -> str:
    """根据 targetFiles 和 category 检测测试类型。
    category=business → 返回 'business'，加载对应的 business 修复策略。
    """
    # category 优先：business 类型加载 business 修复策略
    if category == "business":
        return "business"
    if category == "joint":
        return "joint"
    targets = " ".join(target_files)
    if ".sql" in targets:
        return "db"
    if "services/" in targets:
        return "service"
    if "middleware/" in targets:
        return "middleware"
    if "routes/" in targets:
        return "route"
    if any(k in targets for k in (".vue", "src/pages/", "src/stores/", "src/router/", "src/api/")):
        return "frontend"
    return "utils"


def _load_repair_strategy(test_type: str) -> str:
    """加载层专属测试修复策略。"""
    repair_dir = Path(__file__).parent.parent / "skill" / "test" / "repair" / "a"
    type_file = repair_dir / f"{test_type}.md"
    if type_file.exists():
        return f"\n## 修复策略（{test_type} 类型）\n{load_skill(str(type_file))}\n"
    return ""


async def run_test_writer(
    task: dict,
    workspace_root: str = "./work/project",
    source_contents: dict = None,
    model_client=None,
    task_id: str = "",
    attempt: int = 0,
    bans_text: str = "",
    save_dir: str = "",
    save_filename: str = "",
) -> Dict[str, Any]:
    t0 = datetime.now()
    task_id = task.get("id", "unknown") if not task_id else task_id
    role = load_role(task)
    abs_workspace = str(Path(workspace_root).resolve())
    target_files = task.get("targetFiles", [])
    subdir = _test_subdir(task.get("category", "unit"))
    test_file_rel = f"{subdir}/{task_id}.test.js"
    test_exists = (Path(abs_workspace) / test_file_rel).exists()

    # 修复模式：从 source_contents 提取测试文件当前内容（调度器已预读）
    current_test_content = ""
    if test_exists and source_contents:
        test_key_posix = f"__TEST_FILE__:{abs_workspace}/{test_file_rel}".replace("\\", "/")
        # 兼容路径分隔符差异 — 使用归一化后的精确匹配，避免 "t_auth" 误匹配 "t_auth_admin"
        for k, v in source_contents.items():
            k_norm = k.replace("\\", "/")
            if k.startswith("__TEST_FILE__:") and k_norm.endswith("/" + test_file_rel):
                current_test_content = v
                del source_contents[k]  # 从源码列表中移除，避免混淆
                break

    if bans_text:
        memory_text = bans_text
    else:
        memories = get_bans(task_id)
        memory_text = format_bans_for_agent(memories)

    # 从场景中提取 mockSpec 和 assertType，生成强制模板
    scenarios = task.get("testScenarios", [])
    all_mock_apis = set()
    assertion_requirements = []
    for i, sc in enumerate(scenarios):
        for api in (sc.get("mockSpec") or []):
            all_mock_apis.add(api)
        atype = sc.get("assertType", "")
        scenario_name = sc.get("scenario", f"scenario {i+1}")
        if atype == "called":
            # 验证事务 API 被调用（成功路径只验 beginTransaction + commit，不验 rollback）
            for api in (sc.get("mockSpec") or []):
                if api in ("beginTransaction", "commit"):
                    assertion_requirements.append(
                        f"  // scenario [{scenario_name}]: MUST assert db.{api} was called\n"
                        f"  expect(db.{api}).toHaveBeenCalled();"
                    )
                elif api == "rollback":
                    assertion_requirements.append(
                        f"  // scenario [{scenario_name}]: MUST assert db.rollback was NOT called (success path)\n"
                        f"  expect(db.rollback).not.toHaveBeenCalled();"
                    )
        elif atype == "callOrder":
            # 从 scenario 名称或期望行为中提取操作顺序
            order_desc = sc.get("expectedBehavior", scenario_name)
            assertion_requirements.append(
                f"  // scenario [{scenario_name}]: 操作顺序必须为: {order_desc}\n"
                f"  // 用 toHaveBeenNthCalledWith 逐个验证，顺序不可颠倒。源码的实际顺序如果和这里不一致 → 说明源码有Bug，测试应按这里的正确顺序断言！\n"
                f"  // 强制: expect(db.query).toHaveBeenNthCalledWith(1, ...); toHaveBeenNthCalledWith(2, ...); 按正确顺序写，不要按源码顺序写！"
            )
        elif atype == "throws":
            assertion_requirements.append(
                f"  // scenario [{scenario_name}]: MUST use await expect(...).rejects.toThrow()"
            )

    mock_hint = ""
    if all_mock_apis:
        apis = sorted(all_mock_apis)
        # 根据被测文件确定 mock 目标模块
        targets_str = " ".join(target_files)
        if "config/db.js" in targets_str or "config/db" in targets_str:
            # 测试 config/db.js 本身 → mock 它的依赖 mysql2/promise
            mock_module = "mysql2/promise"
        else:
            # 测试 service/route 等 → mock config/db
            mock_module = "../../config/db"
        mock_hint = f"## [!]Mock 工厂（必须包含以下全部 API，缺一不可）\n" + \
                    f"jest.mock('{mock_module}', () => ({{ {', '.join(f'{a}: jest.fn()' for a in apis)} }}));\n"

    assertion_hint = ""
    if assertion_requirements:
        assertion_hint = "## [!]强制断言要求（每个场景必须包含对应断言，缺一个测试就无效）\n" + \
                         "\n".join(assertion_requirements[:10])  # 限制数量

    cat = task.get("category", "unit")
    sc_text = json.dumps(scenarios, indent=2, ensure_ascii=False)
    fw_text = task.get("testFramework", "jest")

    # ── .env.example 分析：判断每个服务是用真实连接还是 mock ──
    env_real_mock_hint = _build_env_real_mock_hint(abs_workspace)

    # 计算从测试文件到各源码文件的正确 require 路径
    test_dir_depth = len(Path(test_file_rel).parent.parts)
    require_hints = []
    for tf in target_files:
        rel = '/'.join(['..'] * test_dir_depth) + '/' + tf.replace('.js', '')
        require_hints.append(f"  require('{rel}')  // → {tf}")

    # 扫描源文件的模块格式（ESM/CJS），注入提示防止 Agent 选错测试框架
    module_format_hint = _detect_module_format(source_contents or {}, target_files, abs_workspace)

    # 扫描源码中引用的第三方包，自动生成 mock 提示
    third_party_mocks = _detect_third_party_requires(source_contents or {}, target_files, abs_workspace, cat)
    # 合并所有源码用于分析包的实际用法
    _all_source = "\n".join(
        v if isinstance(v, str) else v.get("content", "")
        for v in (source_contents or {}).values()
    ) if source_contents else ""
    mock_stubs = ""

    # t_smoke_env: 确定性模板（mock 生命周期复杂，LLM 极易搞错 ORDER/syntax）
    if task_id == "t_smoke_env":
        mock_stubs = "## [!] t_smoke_env 确定性模板（直接复制到 create_file，只修改 it 块内容！）\n```javascript\n" + _build_smoke_env_template() + "\n```\n"
        if test_exists:
            mock_stubs = "## ⚠️ 文件已损坏，必须 create_file 用下面的确定性模板完整重写！\n" + mock_stubs

# db 层测试直连 MySQL，使用 templates/db.md 模板，不走 mock 骨架
    # 如果目标包含 app.js，生成确定性完整 mock 块
    targets_str = " ".join(target_files)
    if "app.js" in targets_str and not mock_stubs:
        # 生成模式：总是用确定性 mock
        # 修复模式：ban 含 BLOCK_INTEGRITY/MOCK_DUP/syntax → mock 结构已损坏，强制 create_file + 确定性 mock
        has_block_issue = test_exists and memory_text and any(
            kw in memory_text for kw in ("BLOCK_INTEGRITY", "MOCK_DUP", "syntax", "结构损坏"))
        if not test_exists or has_block_issue:
            mock_stubs = _build_app_js_mock_block(target_files, abs_workspace, cat)
            if has_block_issue:
                mock_stubs = "## ⚠️ mock 结构已损坏，必须 create_file 完整重写！用下面的确定性 mock 块替换全部 mock 声明！\n" + mock_stubs

    if not mock_stubs and third_party_mocks:
        mock_stubs = "## [!]第三方包 Mock（源码中引用了以下包，测试文件顶部必须 jest.mock）\n"
        for pkg in sorted(third_party_mocks):
            mock_stubs += f"jest.mock('{pkg}', () => {_mock_factory(pkg, _all_source)});\n"
        mock_stubs += "\n"

    is_vitest = fw_text == "vitest"
    if test_exists:
        flow_section = "## 修复流程\n🛑 第1轮: read_files() — 读当前测试+源码\n🛑 第2轮: edit_batch(优先) / create_file / FIX_SKIP — 必须执行修复动作\n🛑 禁止第3轮（失败自动重试）"
    else:
        flow_section = "## 生成流程\n🛑 第1轮: search_rag+search_code(并行一次调用)\n🛑 第2轮: create_file — 必须执行写入动作\n🛑 禁止第3轮（失败自动重试）"

    fw_hint = "## vitest 规则\n- ESM import, 非 require\n- vi.mock() 顶层声明\n- 无需 jest.mock/babel-jest" if is_vitest else ""

    # 修复策略 → 系统提示词（始终加载，生成模式作为参考，修复模式作为指南）
    test_type = _detect_test_type_from_task(target_files, task.get("category", "unit"))
    repair_strategy_text = _load_repair_strategy(test_type)
    if test_exists and memory_text:
        collapse_keywords = ["BLOCK_INTEGRITY", "syntax", "多余的", "缺少 describe",
                            "孤儿", "闭包", "花括号", "MOCK_DUP", "≥3"]
        collapse_score = sum(1 for kw in collapse_keywords if kw in memory_text)
        if collapse_score >= 2:
            repair_strategy_text = (
                "## ⚠️ 文件结构已崩塌，edit_batch 不可用。必须用 create_file 基于模板完整重写！\n"
                + repair_strategy_text
            )

    instructions = f"""{role}

{flow_section}
{fw_hint}

{repair_strategy_text}
{env_real_mock_hint}
## 工作区: {abs_workspace}

## 目标源码文件（可读取）
{json.dumps(sorted(target_files), ensure_ascii=False)}

## 测试文件: {test_file_rel}（{"已存在，edit_batch 修改" if test_exists else "不存在，create_file 创建"}）

{module_format_hint}
{mock_stubs}{"## [!]require 路径（必须严格使用，不能自己编）" if not any(tf.endswith('.sql') for tf in target_files) else ""}
{"测试文件位于 " + test_file_rel + " (深度=" + str(test_dir_depth) + ")，require 源码时必须用以下路径:" if not any(tf.endswith('.sql') for tf in target_files) else ""}
{chr(10).join(require_hints) if not any(tf.endswith('.sql') for tf in target_files) else ""}
{"" if any(tf.endswith('.sql') for tf in target_files) else "require('../../config/db')  // → config/db.js (数据库 mock)"}

{"**路径铁律**: 项目内文件必须用上面列出的确切路径，禁止自己编。禁止引入 targetFiles 之外的任何项目文件。" if not any(tf.endswith('.sql') for tf in target_files) else "## db 层测试: 直连 MySQL，使用 templates/db.md 模板，不 mock 数据库，不 require config/db"}
"""

    fc = len(target_files)
    sc = len(task.get("testScenarios", []))
    # (per_min, per_max, total_max): 每场景最少 it()数, 每文件最多 it()数, 总上限
    limits = {"unit": (2, 5, 12), "business": (2, 5, 10), "joint": (2, 3, 8), "special": (1, 3, 5)}
    per_min, per_max, total_max = limits.get(cat, (2, 3, 10))
    # 至少保证每个 scenario 有 per_min 个 it()，且总数不低于 sc（确保每个场景都有测试）
    max_cases = max(int(sc * per_min + (fc - 1) * 1.5), min(fc * per_max, total_max), sc)
    max_cases = min(max_cases, total_max)

    current_test_section = ""
    if test_exists and current_test_content:
        lines = current_test_content.split('\n')
        numbered = '\n'.join(f"  {i+1:>4}| {l}" for i, l in enumerate(lines))
        current_test_section = f"""
## 当前测试文件 ({test_file_rel}) — 无需 read_files，内容已在下方
{numbered}
"""

    # repair_strategy_text 已在上方加载（需在 instructions f-string 之前）
    # 只有结构性崩塌才强制 create_file（语法错/describe缺失/闭包破坏）
    # 普通 ban（缺 mock/路径错/字段名错）优先 edit_batch
    collapse_keywords = ["syntax", "缺少 describe", "孤儿", "闭包", "花括号"]
    force_create_file = test_exists and memory_text and sum(1 for kw in collapse_keywords if kw in memory_text) >= 2

    # 构建 user_prompt（只拼非空行，避免大片空白）
    prompt_parts = [f"{'修复' if test_exists else '生成'}测试文件: {task_id}"]
    if current_test_section:
        prompt_parts.append(current_test_section)
    prompt_parts.append(f"- ID: {task_id} | 框架: {fw_text} | 类别: {cat} | 上限: {max_cases} 个 it()")
    if cat == "unit":
        prompt_parts.append("- unit: 关注边界/异常/空值，每个文件均匀覆盖")
    if mock_hint:
        prompt_parts.append(mock_hint)
    if assertion_hint:
        prompt_parts.append(assertion_hint)
    prompt_parts.append(f"## 测试场景\n{sc_text}")
    if memory_text:
        prompt_parts.append(memory_text)
    user_prompt = "\n\n".join(prompt_parts)

    async def install(packages: str = ""):
        return await npm_install(packages, workspace=abs_workspace)

    from Tools.rag.search_rag import make_search_rag
    from Tools.rag.search_code import make_search_code
    search_rag = make_search_rag(task_id, "test_generator")
    search_code = make_search_code(task_id, "test_writer")

    if test_exists:
        async def read_files():
            """读取现有测试文件 + 源码（仅修复模式）。无需参数，自动读取全部。"""
            from Tools.coding.read_file import read_file as _rf
            result = {}
            files_to_read = list(target_files) + [test_file_rel]
            for f in files_to_read:
                r = await _rf(f, workspace=abs_workspace)
                content = r.get("content", "")
                result[f] = {"content": content, "lines": content.count(chr(10)) + 1 if content else 0}
            return result
        async def edit_batch(files: list):
            """批量修改测试文件。参数: [{"file":"path","edits":[{"start":N,"end":N,"content":"..."}]}, ...]
            start/end 为 1-indexed 行号。end<start=插入, end=start=替换, end>start=替换范围, content=""=删除"""
            result = await _edit_batch(files, workspace=abs_workspace)
            # 写入后立即校验 — Vitest 测试跳过 node --check（ESM 语法 node 不支持）
            if result.get("ok") and not is_vitest:
                import subprocess
                for fe in files:
                    fp = fe.get("file", "")
                    if fp.endswith(".js"):
                        test_path = Path(abs_workspace) / fp
                        r = subprocess.run(["node", "--check", str(test_path)], capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace")
                        if r.returncode != 0:
                            err_msg = (r.stderr or "")[:200].replace('\n', ' ')
                            return {"error": f"WRITE REJECTED: {fp} 语法错误: {err_msg}。请修正后重试。"}
            return result
        # 修复模式同时提供 edit_batch 和 create_files——Agent 按策略选择
        async def create_files(files):
            """批量创建/重写文件。参数: [{"path": "...", "content": "..."}]。只能写测试文件。"""
            for fe in files:
                fp = fe.get("path", "")
                # 白名单: 只允许 test/ 目录下的 .test.js / .spec.js 文件
                if not (fp.startswith("test/") and (fp.endswith(".test.js") or fp.endswith(".spec.js"))):
                    return {"error": f"[WHITELIST] 禁止写入 '{fp}'。A只能写测试文件: test/{task_id}.test.js"}
            import subprocess
            result = await _create_files(files, overwrite=True, workspace=abs_workspace)
            if result.get("success") and not is_vitest:
                for fe in files:
                    fp = fe.get("path", "")
                    if fp.endswith(".js"):
                        test_path = Path(abs_workspace) / fp
                        r = subprocess.run(["node", "--check", str(test_path)], capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace")
                        if r.returncode != 0:
                            err_msg = (r.stderr or "")[:200].replace('\n', ' ')
                            return {"error": f"WRITE REJECTED: {fp} 语法错误: {err_msg}。请修正后重试。"}
            return result
        if force_create_file:
            # 硬强制：结构性崩塌，只给 create_files
            tools = [create_files, install, search_rag, search_code]
        else:
            tools = [read_files, edit_batch, create_files, install, search_rag, search_code]
    else:
        async def create_files(files):
            """批量创建/重写测试文件。参数: [{"path": "test/unit/xxx.test.js", "content": "..."}]。一次调用写一个或多个文件。"""
            for fe in files:
                fp = fe.get("path", "")
                if not fp.startswith("test/") or not fp.endswith(".test.js"):
                    return {"error": f"Access denied: '{fp}' 不是合法的测试文件路径。只能写入 test/{test_file_rel}"}
            import subprocess
            result = await _create_files(files, overwrite=True, workspace=abs_workspace)
            if result.get("success") and not is_vitest:
                for fe in files:
                    fp = fe.get("path", "")
                    if fp.endswith(".js"):
                        test_path = Path(abs_workspace) / fp
                        r = subprocess.run(["node", "--check", str(test_path)], capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace")
                        if r.returncode != 0:
                            err_msg = (r.stderr or "")[:200].replace('\n', ' ')
                            return {"error": f"WRITE REJECTED: {fp} 语法错误: {err_msg}。请修正后重试。"}
            return result
        tools = [create_files, install, search_rag, search_code]

    if model_client is None:
        from utils.model_client import get_model_client
        model_client = get_model_client()
    model = model_client

    agent = Agent(
        name=f"test_writer_{task_id}",
        description="测试编写工程师",
        instructions=instructions,
        model_client=model,
        tools=tools,
        max_iterations=3,
    )

    collected = []
    for retry in range(2):  # 最多重试1次（picoagents 流式 JSON 解析偶发错误）
        try:
            async for event in wrap_agent_stream(
                agent, user_prompt, "test_writer",
                model=model.model, task_id=task_id,
                save_dir=save_dir, save_filename=save_filename,
            ):
                collected.append(str(event))
        except Exception as e:
            err_str = str(e)
            if ("Expecting" in err_str or "JSONDecodeError" in err_str or "column" in err_str) and retry == 0:
                collected = []; continue
            return {"success": False, "test_file": None, "validation_errors": [],
                    "message": f"Agent error: {e}", "elapsed": (datetime.now() - t0).total_seconds()}
        # 检查流中是否有 picoagents 框架的 ErrorEvent（框架不抛异常，yield 错误事件后 break）
        full = "\n".join(collected)
        if "Unexpected error" in full and ("Expecting" in full or "column" in full) and retry == 0:
            collected = []; continue
        break

    # 检查测试文件是否生成
    test_file_candidates = [
        Path(abs_workspace) / subdir / f"{task_id}.test.js",
        Path(abs_workspace) / subdir / f"{task_id}.spec.js",
        Path(abs_workspace) / f"{subdir}" / f"{task_id}.test.js",
    ]
    test_file = None
    for cand in test_file_candidates:
        if cand.exists():
            test_file = str(cand)
            break

    # ── 硬校验层：在返回前检查测试文件质量 ──
    validation_errors = []
    if test_file:
        validation_errors = _validate_test_file(
            test_file, task.get("testScenarios", []), task.get("testFramework", "jest"),
            task_id=task.get("id", ""))

    elapsed = (datetime.now() - t0).total_seconds()
    success = test_file is not None and len(validation_errors) == 0

    return {
        "success": success,
        "test_file": test_file,
        "validation_errors": validation_errors,
        "message": f"Test file {'created' if test_file else 'NOT created'}: {test_file}"
                   + (f" | VALIDATION FAILED: {'; '.join(e.get('message', str(e)) for e in validation_errors[:3])}" if validation_errors else ""),
        "elapsed": elapsed,
        "raw_output": "\n".join(collected),
    }
