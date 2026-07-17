# Tools/testing/run_test.py
"""
测试运行工具（增强版）—— 粗加工层。

增强点:
  1. 执行 Jest/Vitest，解析输出
  2. 从每个失败用例中智能提取关键信息（错误类型、预期/实际值、精简堆栈）
  3. 截断长文本至合理长度，大幅减少 token 消耗
  4. 返回结构化结果供 Agent 精加工
"""

import subprocess
import json
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional


async def run_test(
    test_file_path: str,
    test_framework: str = "jest",
    project_root: str = "",
    timeout_seconds: int = 120,
    extra_args: str = "",
) -> Dict[str, Any]:
    """
    执行测试并返回粗加工结果。

    返回结构:
        {
            "total": int,
            "passed": int,
            "failed": int,
            "error_type": str | None,        # 粗加工分类（缺失模块/语法/其他）
            "failures": [                    # 每个失败的精简信息
                {
                    "test_name": str,
                    "error_message": str,    # 简短描述（<500字符）
                    "expected": str | None,
                    "received": str | None,
                    "file": str,
                    "line": int | None
                }
            ],
            "raw_output": str,               # 截断的原始输出（前2000字符，仅供调试）
            "command": str,
            "duration_ms": int
        }
    """
    root = Path(project_root).resolve() if project_root else Path.cwd()
    test_path = Path(test_file_path)
    if not test_path.is_absolute():
        test_path = root / test_file_path

    if not test_path.exists():
        return _error_result(f"Test file not found: {test_path}", "missing_file")

    rel_path = str(test_path.relative_to(root)).replace("\\", "/")
    # 用 node 直调避免 Windows PATH 问题（npx 在 subprocess 中可能找不到）
    if test_framework == "vitest":
        vitest_bin = root / "node_modules" / "vitest" / "vitest.mjs"
        if vitest_bin.exists():
            cmd = f'node "{vitest_bin}" run "{rel_path}" --reporter=json'
        else:
            cmd = f'npx vitest run "{rel_path}" --reporter=json'
    elif test_framework in ("jest", "jest+supertest", "jest+supertest (CJS)"):
        jest_bin = root / "node_modules" / "jest" / "bin" / "jest.js"
        cmd = f'node "{jest_bin}" "{rel_path}" --json --verbose --forceExit --testTimeout={timeout_seconds * 1000}'
    elif test_framework == "k6":
        # k6: 优先本地二进制，不可用则 Docker
        import shutil, platform
        if shutil.which("k6"):
            cmd = f'k6 run "{rel_path}"'
        else:
            abs_root = str(root).replace("\\", "/")
            if platform.system() == "Windows":
                drive = abs_root[0].lower()
                docker_path = f"/{drive}{abs_root[2:]}"
            else:
                docker_path = abs_root
            cmd = f'docker run --rm -v "{docker_path}":/tests grafana/k6 run /tests/{rel_path}'
    else:
        cmd = f'npx {test_framework} "{rel_path}"'
    if extra_args:
        cmd += " " + extra_args

    start_ms = time.time() * 1000
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(root),
            timeout=timeout_seconds,
            env={**__import__("os").environ, "CI": "true", "NODE_ENV": "test",
                 "FORCE_COLOR": "0", "NO_COLOR": "1", "PYTHONIOENCODING": "utf-8"},
        )
        duration_ms = int(time.time() * 1000 - start_ms)
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""

        if test_framework in ("jest", "vitest", "jest+supertest", "jest+supertest (CJS)"):
            result = _parse_json(stdout, stderr, proc.returncode)
        else:
            result = _parse_text(stdout, stderr, proc.returncode)

        result["command"] = cmd
        result["duration_ms"] = duration_ms
        return result

    except subprocess.TimeoutExpired:
        duration_ms = int(time.time() * 1000 - start_ms)
        return _error_result(f"Test execution timed out after {timeout_seconds}s", "timeout", cmd, duration_ms)
    except FileNotFoundError:
        duration_ms = int(time.time() * 1000 - start_ms)
        return _error_result("npx not found. Install Node.js/npm.", "environment", cmd, duration_ms)


def _parse_json(stdout: str, stderr: str, exit_code: int) -> Dict[str, Any]:
    """解析 Jest/Vitest JSON 输出，智能提取关键信息"""
    combined = stdout + "\n" + stderr
    try:
        data = json.loads(combined)
    except json.JSONDecodeError:
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return _parse_text(stdout, stderr, exit_code)

    if not isinstance(data, dict):
        return _parse_text(stdout, stderr, exit_code)

    total = data.get("numTotalTests", 0)
    passed = data.get("numPassedTests", 0)
    failed = data.get("numFailedTests", 0)

    failures = []
    for tr in data.get("testResults", []):
        file_path = tr.get("name", "")
        # 当 total==0 时，错误在 testResult.message 里（测试套件加载失败）
        if total == 0 and tr.get("message"):
            msg = tr["message"]
            # 提取第一行有意义的内容
            lines = [l.strip() for l in msg.split('\n') if l.strip() and not l.strip().startswith('\x1b')]
            error_line = ""
            for line in lines:
                if "Cannot find module" in line or "Error:" in line or "TypeError" in line or "SyntaxError" in line:
                    error_line = line
                    break
            if not error_line:
                error_line = lines[0] if lines else msg[:200]
            failures.append({
                "test_name": "Test suite failed to load",
                "error_message": error_line[:500],
                "expected": None,
                "received": None,
                "file": file_path,
                "line": None,
            })
            break  # 一个 suite 级别错误就够了

        for assertion in tr.get("assertionResults", []):
            if assertion.get("status") != "failed":
                continue
            full_name = assertion.get("fullName", assertion.get("title", ""))
            failure_messages = assertion.get("failureMessages", [])
            raw_msg = failure_messages[0] if failure_messages else ""
            # 智能提取关键信息
            extracted = _extract_key_info(raw_msg)
            failures.append({
                "test_name": full_name,
                "error_message": extracted["error_message"],
                "expected": extracted.get("expected"),
                "received": extracted.get("received"),
                "file": file_path,
                "line": assertion.get("location", {}).get("line") if assertion.get("location") else None,
            })
            if len(failures) >= 15:   # 最多保留15个失败
                break
        if len(failures) >= 15:
            break

    # 粗加工错误类型（仅当 total == 0 时才有明确判定）
    error_type = None
    if total == 0:
        lower_combined = combined.lower()
        if "cannot find module" in lower_combined:
            error_type = "missing_module"
        elif "syntaxerror" in lower_combined:
            error_type = "syntax"
        else:
            error_type = "test_bug"

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "error_type": error_type,
        "failures": failures,
        "stderr": stderr[:2000],
        "raw_output": combined[:2000],
        "command": "",
        "duration_ms": 0,
    }


def _extract_key_info(raw_msg: str) -> Dict[str, Any]:
    """从原始错误消息中提取关键片段——保留足够上下文供 Agent 诊断"""
    lines = raw_msg.split("\n")
    result = {"error_message": "", "expected": None, "received": None}

    key_lines = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        # 错误类型 + 堆栈跟踪（保留项目中所有堆栈行，不限制为1个）
        if ("Error:" in s or "TypeError" in s or "AssertionError" in s or
            ("at " in s and "node_modules" not in s and "internal/" not in s)):
            key_lines.append(s[:200])
        # toHaveBeenCalledWith / toHaveLength 等匹配器保留完整 expected/received
        if "Expected:" in s or "Received:" in s:
            key_lines.append(s[:300])
        if "Number of calls:" in s:
            key_lines.append(s[:100])

    if not key_lines:
        result["error_message"] = raw_msg[:400]
    else:
        result["error_message"] = "\n".join(key_lines)[:800]

    exp_match = re.search(r'Expected:\s*(.+?)(?:\n|$)', raw_msg)
    rec_match = re.search(r'Received:\s*(.+?)(?:\n|$)', raw_msg)
    if exp_match: result["expected"] = exp_match.group(1)[:300]
    if rec_match: result["received"] = rec_match.group(1)[:300]
    return result


def _parse_text(stdout: str, stderr: str, exit_code: int) -> Dict[str, Any]:
    """回退方案：从纯文本中解析"""
    combined = stdout + "\n" + stderr
    # 尝试用正则提取测试数量
    total_match = re.search(r'Tests:\s*(?:\d+\s*passed,\s*)?(?:\d+\s*failed,\s*)?(\d+)\s*total', combined)
    passed_match = re.search(r'Tests:\s*(\d+)\s*passed', combined)
    failed_match = re.search(r'(\d+)\s*failed', combined)
    total = int(total_match.group(1)) if total_match else 0
    passed = int(passed_match.group(1)) if passed_match else 0
    failed = int(failed_match.group(1)) if failed_match else max(0, total - passed)

    # 提取失败块
    failures = []
    # 按 FAIL 标记或 ● 符号分割
    fail_blocks = re.split(r'\n\s*[●❌]', combined)
    for block in fail_blocks[1:]:
        if 'FAIL' in block or 'AssertionError' in block or 'Expected' in block:
            # 只保留前200字符
            failures.append({
                "test_name": "",
                "error_message": block.strip()[:400],
                "expected": None,
                "received": None,
                "file": "",
                "line": None,
            })
            if len(failures) >= 10:
                break
    if total == 0:
        error_type = "test_bug"
        lower = combined.lower()
        if "cannot find module" in lower:
            error_type = "missing_module"
        elif "syntaxerror" in lower:
            error_type = "syntax"
    else:
        error_type = None

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "error_type": error_type,
        "failures": failures,
        "stderr": stderr[:2000],
        "raw_output": combined[:2000],
        "command": "",
        "duration_ms": 0,
    }


def _error_result(error_msg: str, error_type: str, command: str = "", duration_ms: int = 0) -> Dict[str, Any]:
    return {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "error_type": error_type,
        "failures": [{"test_name": "", "error_message": error_msg}],
"stderr": error_msg,
        "raw_output": error_msg,
        "command": command,
        "duration_ms": duration_ms,
    }


async def agent_run_test(
    file_path: str,
    framework: str = "jest",
    timeout_seconds: int = 120,
    workspace: str = "",
) -> Dict[str, Any]:
    """供 Agent 调用的异步包装"""
    if workspace:
        project_root = str(Path(workspace).resolve())
    else:
        # 回退：从文件路径往上找含 node_modules 的目录
        p = Path(file_path).resolve()
        for parent in [p.parent.parent, p.parent.parent.parent]:
            if (parent / "node_modules").exists():
                project_root = str(parent)
                break
        else:
            project_root = str(Path(file_path).parent.parent.resolve()) if file_path else "."
    return await run_test(file_path, framework, project_root, timeout_seconds)