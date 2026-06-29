# Tools/testing/npm_install.py
"""npm install 工具 — 仅限安装依赖，不执行其他命令"""

import subprocess
from pathlib import Path


async def npm_install(packages: str = "", workspace: str = "") -> dict:
    """
    安装 npm 依赖包。仅执行 npm install，不做其他操作。

    Args:
        packages: 要安装的包名（空格分隔），留空则按 package.json 安装全部
        workspace: 项目根目录

    Returns:
        {"ok": True, "message": "...", "packages": [...]}
        或 {"ok": False, "message": "...", "packages": [...]}
    """
    ws = Path(workspace).resolve() if workspace else Path.cwd()
    if not (ws / "package.json").exists():
        return {"ok": False, "message": f"package.json not found in {ws}", "packages": []}

    # 防御：如果 packages 看起来像命令（以 node/npm/npx 开头或包含 --），拒绝执行
    stripped = packages.strip()
    if stripped:
        first_word = stripped.split()[0] if stripped else ""
        if first_word in ("node", "npm", "npx", "cd", "ls", "dir") or stripped.startswith("-"):
            return {
                "ok": False,
                "message": f"install() 仅用于安装 npm 包（如 install('supertest') 或 install() 安装全部），"
                           f"收到疑似命令: '{stripped[:80]}'。请用空参数 install() 安装 package.json 全部依赖。",
                "packages": [],
            }

    cmd = ["npm", "install", "--no-audit", "--no-fund"]
    if packages.strip():
        cmd.extend(packages.strip().split())

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(ws),
            timeout=120,
            encoding="utf-8", errors="replace",
        )
        output = result.stdout + result.stderr
        ok = result.returncode == 0
        # 提取关键状态给 agent
        status = "already up to date" if "up to date" in output.lower() else "packages installed"
        if "added" in output.lower():
            import re
            m = re.search(r'added (\d+) package', output)
            status = f"added {m.group(1)} packages" if m else "packages installed"
        if not ok:
            status = "install failed"
        pkg_list = packages.strip().split() if packages.strip() else ["all"]
        if not ok:
            msg = f"install failed (exit code {result.returncode}): {output[-200:].strip()}"
        elif "already up to date" in output.lower() or "up to date" in output.lower():
            msg = "所有依赖已就绪，无需操作"
        else:
            added = ""
            import re
            m = re.search(r'added (\d+) package', output)
            if m: added = f"，新增 {m.group(1)} 个包"
            msg = f"安装完成{added}"
        return {"ok": ok, "message": msg, "packages": pkg_list}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "npm install timed out after 120s"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
