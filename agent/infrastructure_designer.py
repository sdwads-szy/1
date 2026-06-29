# agent/infrastructure_designer.py
"""基础设施工程师 — 扩展 BaseDesigner，env 变量专项处理。"""
import sys, json, re
from pathlib import Path
from typing import Dict, List

current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from agent.base_designer import BaseDesigner
from utils.logger import log_warning

# ── 从配置文件加载 env 默认值 ──
def _load_env_config() -> tuple:
    config_path = parent_dir / "config" / "env_defaults.json"
    try:
        config = json.loads(config_path.read_text("utf-8"))
        defaults = config.get("env_defaults", {})
        prefixes = config.get("web_env_prefixes", [])
        return defaults, prefixes
    except Exception:
        log_warning("failed to load env config, using fallback", file=str(config_path))
        return {}, []

_FALLBACK_ENV, _WEB_ENV_PREFIXES = _load_env_config()

# ── 系统 env 模板 ──
_SYSTEM_ENV_EXAMPLE = parent_dir / ".env.example"
_ENV_VARIABLE_SET = ""
_CANONICAL_ENV_KEYS: List[str] = []

if _SYSTEM_ENV_EXAMPLE.exists():
    raw = _SYSTEM_ENV_EXAMPLE.read_text("utf-8").strip()
    for line in raw.split("\n"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            key = s.split("=", 1)[0].strip()
            val = s.split("=", 1)[1].strip().strip('"').strip("'")
            if any(key.startswith(p) for p in _WEB_ENV_PREFIXES):
                _ENV_VARIABLE_SET += f"{key}={val}\n"
                _CANONICAL_ENV_KEYS.append(key)

# 补全缺失变量
for key, val in _FALLBACK_ENV.items():
    if key not in _CANONICAL_ENV_KEYS:
        _ENV_VARIABLE_SET += f"{key}={val}\n"
        _CANONICAL_ENV_KEYS.append(key)

_ENV_VARIABLE_SET = _ENV_VARIABLE_SET.strip()


class InfraDesigner(BaseDesigner):
    """基础设施工程师 — env 变量管理 + 校验。"""

    def __init__(self):
        super().__init__(agent_type="infra", description="基础设施工程师")

    def _build_result(self, task, workspace_path, target_files, extra=None):
        tid = self._tid(task)
        all_exist = all((workspace_path / f).exists() for f in target_files) if target_files else True
        env_ok = _validate_env_consistency(workspace_path)
        missing = sum(1 for f in target_files if not (workspace_path / f).exists()) if target_files else 0
        result = {
            "task_id": tid,
            "success": all_exist,
            "error": None if all_exist else f"{missing} files missing",
            "metadata": {"env_validation": env_ok},
        }
        if extra:
            result.update(extra)
        return result

    async def run(self, task, workspace_root="./project",
                  relevant_contracts=None, extra_instructions="") -> dict:
        """注入 env 变量模板到 extra_instructions。"""
        env_extra = ""
        if _ENV_VARIABLE_SET:
            env_extra = f"\n## 环境变量模板\n```\n{_ENV_VARIABLE_SET}\n```\n"
        arch = task.get("envConstraints", {})
        if arch:
            effective = {k: v for k, v in arch.items() if v not in ("", None)}
            if effective:
                env_extra += "\n## env 约束\n" + "\n".join(
                    f"- {k}: {v}" for k, v in effective.items()
                )
        combined = env_extra + (extra_instructions or "")
        return await super().run(task, workspace_root=workspace_root,
                                 relevant_contracts=relevant_contracts,
                                 extra_instructions=combined)


_infra_designer = InfraDesigner()


async def run_infrastructure_task(task: dict, workspace_root: str = "./project",
                                  extra_instructions: str = "") -> dict:
    return await _infra_designer.run(task, workspace_root=workspace_root,
                                     extra_instructions=extra_instructions)


# ── env 一致性校验（保留原逻辑）──

def _validate_env_consistency(workspace_path: Path) -> dict:
    ref_keys = set(_CANONICAL_ENV_KEYS)
    env_paths = {n: workspace_path / n for n in [".env", ".env.example", ".env.development", ".env.production"]}
    file_sets = {}
    for name, path in env_paths.items():
        if not path.exists():
            continue
        keys = set()
        for line in path.read_text("utf-8").split("\n"):
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                keys.add(s.split("=", 1)[0].strip())
        file_sets[name] = keys
    if not file_sets:
        return {"ok": False}
    if not ref_keys:
        ref_keys = file_sets.get(".env.example", set().union(*file_sets.values()))
    issues = []
    for name, keys in file_sets.items():
        if ref_keys - keys:
            issues.append(f"{name}: 缺 {ref_keys - keys}")
        if keys - ref_keys:
            issues.append(f"{name}: 多 {keys - ref_keys}")
    if issues:
        _repair_env_files(workspace_path, ref_keys, file_sets, env_paths)
    return {"ok": len(issues) == 0, "variable_count": len(ref_keys)}


def _repair_env_files(workspace_path, ref_keys, file_sets, env_paths):
    canonical = {}
    if _SYSTEM_ENV_EXAMPLE.exists():
        for line in _SYSTEM_ENV_EXAMPLE.read_text("utf-8").split("\n"):
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k = s.split("=", 1)[0].strip()
                if k in ref_keys:
                    canonical[k] = s.split("=", 1)[1].strip().strip('"').strip("'")
    # 回退：从 _FALLBACK_ENV 加载默认值，避免用空值覆盖
    for k in ref_keys:
        if k not in canonical and k in _FALLBACK_ENV:
            canonical[k] = _FALLBACK_ENV[k]
    for name, path in env_paths.items():
        if not path.exists():
            path.write_text(
                "\n".join([f"# {name}"] + [f"{k}={canonical.get(k, 'your_value_here')}" for k in sorted(ref_keys)]) + "\n",
                "utf-8")
            continue
        content = path.read_text("utf-8")
        lines = [l for l in content.split("\n")
                 if not (l.strip() and not l.strip().startswith("#") and "=" in l.strip()
                         and l.strip().split("=", 1)[0].strip() not in ref_keys)]
        missing = ref_keys - file_sets.get(name, set())
        for k in sorted(missing):
            lines.append(f"{k}={canonical.get(k, 'your_value_here')}")
        path.write_text("\n".join(lines) + "\n", "utf-8")
