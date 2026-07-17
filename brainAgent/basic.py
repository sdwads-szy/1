# brainAgent/basic.py
"""
统一入口：从一句话需求到完整可运行系统的自动化流程。

5 阶段:
  1. 需求分析 (orchestrator)    → requirement_report_*.md
  2. 架构生成 (architect)       → task_*.json (含契约)
  3. 源代码生成 (engineer)      → 项目源码
  4. 测试架构生成 (test-architect) → test_tasks_*.json
  5. 测试与修复执行 (test)      → 测试执行 + 自动修复 + 报告

用法:
    python brainAgent/basic.py "设计一个B2B2C线上商城购物系统，并给系统取个好名字"              # 1→2→3→4→5 全流程
    python brainAgent/basic.py -orchestrator "需求"                   # 1→5 从需求分析开始
    python brainAgent/basic.py -architect                             # 2→5 跳过需求，从架构开始
    python brainAgent/basic.py -engineer                              # 3→5 跳过需求+架构，从代码生成开始
    python brainAgent/basic.py --test-architect                       # 4→5 跳过前三步
    python brainAgent/basic.py -test                                  # 5 只跑测试执行
    python brainAgent/basic.py -test --fast                           # 5 快速模式
"""

import asyncio, os, sys, time, argparse, subprocess
from pathlib import Path
from datetime import datetime

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from agent.architect import run_architect_agent
from agent.test_architect import run_test_architect
from brainAgent.engineer import run_engineer
from brainAgent.orchestrator import run_demand_analysis
from brainAgent.scheduler import run_scheduler

WORKSPACE = project_root / "work" / "project"


def _timer():
    return time.time()


def _elapsed(t0):
    return f"{time.time() - t0:.0f}s"


def _cleanup_round_failures(workspace: Path):
    """每轮末清理 failed 任务的 ban 日志——无效经验不留。passed 任务的 ban 保留（有效经验）。"""
    import json as _json
    test_log_dir = project_root / "Memory" / "test_logs"
    ban_dirs = [
        project_root / "Memory" / "test_failure",
        project_root / "Memory" / "source_failure",
    ]

    # 从 test_logs 找出本轮 passed 的任务（它们的 ban 是有效经验，保留）
    passed_ids = set()
    if test_log_dir.exists():
        for f in test_log_dir.glob("*.json"):
            try:
                data = _json.loads(f.read_text("utf-8"))
                if data.get("test_success") and data.get("source_success"):
                    passed_ids.add(f.stem)
            except Exception:
                pass

    # 只清理未通过任务的 ban
    for d in ban_dirs:
        if d.exists():
            for f in d.glob("*.json"):
                if f.stem not in passed_ids:
                    try:
                        f.unlink()
                    except OSError:
                        pass


def _validate_code_generation(workspace: Path) -> dict:
    ws = Path(workspace).resolve()
    if not ws.exists():
        return {"ok": False, "error": f"workspace not found: {ws}"}

    def _is_esm(filepath: Path) -> bool:
        try:
            head = filepath.read_text("utf-8")[:1024]
            cleaned = __import__('re').sub(r'//.*|/\*[\s\S]*?\*/', '', head)
            return bool(__import__('re').search(r'(?:^|\n)\s*(?:import\s+|export\s+)', cleaned))
        except Exception:
            return False

    js_files = list(ws.rglob("*.js"))
    # CJS 文件 → node --check
    cjs_files = [f for f in js_files
                 if "node_modules" not in str(f)
                 and str(ws / "test") not in str(f.parent.resolve())
                 and not _is_esm(f)]
    # ESM 文件 → esbuild 检查（node --check 不支持 import/export）
    esm_files = [f for f in js_files
                 if "node_modules" not in str(f)
                 and str(ws / "test") not in str(f.parent.resolve())
                 and _is_esm(f)]

    syntax_errors = []

    # CJS 语法检查
    for f in cjs_files:
        r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            rel = str(f.relative_to(ws)).replace("\\", "/")
            err = (r.stderr or "")[:120].replace('\n', ' ')
            syntax_errors.append(f"{rel}: {err}")

    # ESM 语法检查（用 esbuild，Vite 已自带）
    if esm_files:
        esbuild_ok = _check_esm_syntax(ws, esm_files)
        syntax_errors.extend(esbuild_ok)

    return {
        "ok": len(syntax_errors) == 0,
        "js_files": len(cjs_files) + len(esm_files),
        "cjs_files": len(cjs_files),
        "esm_files": len(esm_files),
        "vue_files": len(list(ws.rglob("*.vue"))),
        "sql_files": len(list(ws.rglob("*.sql"))),
        "syntax_errors": syntax_errors,
    }


def _check_esm_syntax(ws: Path, esm_files: list) -> list:
    """用 esbuild 批量检查 ESM 文件语法。esbuild 是 Vite 的依赖，速度极快。"""
    errors = []
    esbuild = ws / "node_modules" / ".bin" / "esbuild"
    if not esbuild.exists():
        esbuild = ws / "node_modules" / "esbuild" / "bin" / "esbuild"
    if not esbuild.exists():
        # 尝试 npx
        esbuild = "npx"
        esbuild_args = ["esbuild"]
    else:
        esbuild = str(esbuild)
        esbuild_args = []

    for f in esm_files:
        rel = str(f.relative_to(ws)).replace("\\", "/")
        cmd = [esbuild] + esbuild_args + [str(f), "--bundle", "--format=esm", "--log-level=error", "--outfile=" + str(ws / ".esbuild-tmp.js")]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                             cwd=str(ws), encoding="utf-8", errors="replace")
            if r.returncode != 0:
                # 提取最有用的一行错误
                err_lines = [l.strip() for l in (r.stderr or "").split('\n') if l.strip() and 'X [ERROR]' in l]
                err = err_lines[0][:150] if err_lines else (r.stderr or "").strip()[:150]
                errors.append(f"{rel}: {err}")
        except subprocess.TimeoutExpired:
            errors.append(f"{rel}: timeout")
        except Exception as e:
            errors.append(f"{rel}: {str(e)[:100]}")
    # 清理临时文件
    tmp = ws / ".esbuild-tmp.js"
    if tmp.exists():
        try:
            tmp.unlink()
        except OSError:
            pass
    return errors


def _validate_env_consistency(workspace: Path) -> dict:
    import re
    ws = Path(workspace).resolve()
    code_vars = set()
    for root, dirs, files in os.walk(str(ws)):
        dirs[:] = [d for d in dirs if d not in ('node_modules', '.git', 'test')]
        for f in files:
            if f.endswith(('.js', '.vue')):
                try:
                    content = open(os.path.join(root, f), encoding='utf-8').read()
                    code_vars.update(re.findall(r'process\.env\.(\w+)', content))
                except Exception:
                    pass
    code_vars.add('REDIS_URL')
    env_file = ws / ".env"
    env_vars = set()
    if env_file.exists():
        for line in env_file.read_text(encoding='utf-8').split('\n'):
            m = re.match(r'^(\w+)=', line)
            if m: env_vars.add(m.group(1))
    missing = sorted(code_vars - env_vars)
    if missing and env_file.exists():
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
        lines = env_file.read_text(encoding='utf-8').split('\n')
        for var in missing:
            default_val = defaults.get(var, f'your_{var.lower()}_here')
            lines.append(f"{var}={default_val}")
        env_file.write_text('\n'.join(lines), encoding='utf-8')
    return {"consistent": len(missing) == 0, "missing": missing, "auto_fixed": len(missing)}


async def main():
    parser = argparse.ArgumentParser(description="从一句话需求生成完整系统")
    parser.add_argument("requirement", nargs="?", default=None, help="一句话需求描述")
    parser.add_argument("-orchestrator", action="store_true", help="从需求分析开始（全流程默认起点）")
    parser.add_argument("-architect", action="store_true", help="从架构设计开始（跳过需求分析）")
    parser.add_argument("-engineer", action="store_true", help="从代码生成开始（跳过需求+架构）")
    parser.add_argument("-test", action="store_true", help="从测试执行开始（跳过需求+架构+代码+测试架构）")
    parser.add_argument("--test-architect", action="store_true", help="只生成测试任务清单（不执行测试）")
    parser.add_argument("--task-file", type=str, help="指定任务文件路径")
    parser.add_argument("--requirement-report", type=str, help="指定需求报告路径")
    parser.add_argument("--max-rounds", type=int, default=5, help="需求分析最大轮次")
    parser.add_argument("--session-id", type=str, default="project_session", help="会话ID")
    parser.add_argument("--fast", action="store_true", help="测试快速模式")
    parser.add_argument("--resume", action="store_true", help="恢复模式：跳过已成功生成的代码")
    args = parser.parse_args()

    # 5 阶段级联：指定阶段 → 跳过之前部分，从该阶段开始跑到底
    if args.test:             start_idx = 4
    elif args.test_architect: start_idx = 3
    elif args.engineer:       start_idx = 2
    elif args.architect:      start_idx = 1
    elif args.orchestrator:   start_idx = 0
    else:                     start_idx = 0  # 未指定 → 全流程

    run_orch      = start_idx <= 0
    run_arch      = start_idx <= 1
    run_eng       = start_idx <= 2
    run_test_arch = start_idx <= 3
    run_test_exec = start_idx <= 4

    t_total = _timer()

    # ═══════════════════════════════════════════════════════════
    # Step 1: 需求分析
    # ═══════════════════════════════════════════════════════════
    report_path = args.requirement_report
    if run_orch:
        if not args.requirement:
            print("错误：需求分析需要提供需求描述")
            sys.exit(1)
        print(f"\n{'='*60}")
        print(f"  Step 1/5: 需求分析")
        print(f"{'='*60}")
        t0 = _timer()
        result = await run_demand_analysis(session_id=args.session_id, requirement=args.requirement,
                                            max_rounds=args.max_rounds)
        report_path = result["report_path"]
        print(f"需求报告: {report_path}  ({_elapsed(t0)})")
    else:
        if report_path:
            print(f"使用需求报告: {report_path}")
        else:
            from agent.architect import REPORT_DIR
            files = list(REPORT_DIR.glob("requirement_report_*.md"))
            report_path = str(max(files, key=lambda p: p.stat().st_mtime)) if files else None
            if not report_path and run_arch:
                print("错误：未找到需求报告，无法运行架构设计")
                sys.exit(1)

    # ═══════════════════════════════════════════════════════════
    # Step 2: 架构设计
    # ═══════════════════════════════════════════════════════════
    task_file = args.task_file
    if run_arch:
        print(f"\n{'='*60}")
        print(f"  Step 2/5: 架构生成（开发任务+契约）")
        print(f"{'='*60}")
        t0 = _timer()
        arch_result = await run_architect_agent(report_path=report_path)
        if not arch_result.get("success"):
            print(f"架构设计失败: {arch_result.get('error', '未知错误')}")
            sys.exit(1)
        task_file = arch_result["task_file"]
        print(f"任务文件: {task_file}  (契约{arch_result.get('contract_count', '?')} 任务{arch_result.get('task_count', '?')})  ({_elapsed(t0)})")
    else:
        if task_file:
            print(f"使用任务文件: {task_file}")
        else:
            from brainAgent.engineer import TASK_DIR
            files = list(TASK_DIR.glob("task_*.json"))
            task_file = str(max(files, key=lambda p: p.stat().st_mtime)) if files else None
            if not task_file and run_eng:
                print("错误：未找到任务文件，无法运行代码生成")
                sys.exit(1)

    # ═══════════════════════════════════════════════════════════
    # Step 3: 代码生成
    # ═══════════════════════════════════════════════════════════
    if run_eng:
        print(f"\n{'='*60}")
        print(f"  Step 3/5: 源代码生成（并发执行开发任务）")
        print(f"{'='*60}")
        t0 = _timer()
        # 清理旧产物
        for _stale in [WORKSPACE / "app.js", WORKSPACE / "src/router/index.js"]:
            if _stale.exists(): _stale.unlink()
        _meta = WORKSPACE / ".meta"
        if _meta.exists():
            import shutil; shutil.rmtree(str(_meta))
        eng_report = await run_engineer(Path(task_file), resume=args.resume)
        s = eng_report.get("summary", {})
        print(f"代码生成: {s.get('success', 0)}/{s.get('total', 0)} 成功  ({_elapsed(t0)})")

        # 校验
        print(f"\n[校验] 语法检查...")
        v = _validate_code_generation(WORKSPACE)
        ok_msg = 'OK' if v['ok'] else f"{len(v['syntax_errors'])} syntax errors"
        print(f"  JS:{v['js_files']} Vue:{v['vue_files']} SQL:{v['sql_files']}  {ok_msg}")
        env_ok = _validate_env_consistency(WORKSPACE)
        if not env_ok["consistent"]:
            print(f"  .env 补全 {env_ok.get('auto_fixed', 0)} 个缺失变量")
    else:
        print("跳过代码生成")

    # ═══════════════════════════════════════════════════════════
    # Step 4: 测试架构生成
    # ═══════════════════════════════════════════════════════════
    test_tasks_file = None
    if run_test_arch:
        print(f"\n{'='*60}")
        print(f"  Step 4/5: 测试架构生成（生成测试任务清单）")
        print(f"{'='*60}")
        t0 = _timer()
        if not task_file:
            from brainAgent.engineer import TASK_DIR as _ENG_TASK_DIR
            _task_files = list(_ENG_TASK_DIR.glob("task_*.json"))
            task_file = str(max(_task_files, key=lambda p: p.stat().st_mtime)) if _task_files else None
        if not task_file:
            print("错误：未找到任务文件，无法生成测试任务")
        else:
            print(f"使用任务文件: {task_file}")
            test_arch_result = await run_test_architect(task_path=task_file)
            if test_arch_result.get("success"):
                test_tasks_file = str(test_arch_result.get('output', ''))
                print(f"测试任务: {test_tasks_file} ({test_arch_result.get('task_count', 0)} 个)  ({_elapsed(t0)})")
            else:
                print(f"测试任务生成失败: {test_arch_result.get('error', '')[:200]}")

    # ═══════════════════════════════════════════════════════════
    # Step 5: 测试与修复执行
    # ═══════════════════════════════════════════════════════════
    if run_test_exec:
        print(f"\n{'='*60}")
        print(f"  Step 5/5: 测试与修复执行（自动多轮）")
        print(f"{'='*60}")

        import glob
        if not test_tasks_file:
            _files = sorted(glob.glob(f"{WORKSPACE}/test/test_tasks_*.json"))
            test_tasks_file = _files[-1] if _files else ""

        if test_tasks_file and Path(test_tasks_file).exists():
            print(f"测试任务文件: {test_tasks_file}")
            t0 = _timer()
            prev_passed = None
            for auto_round in range(1, 100):
                test_report = await run_scheduler(str(WORKSPACE), test_tasks_file, fast=args.fast)
                s = test_report.get("summary", {})
                passed = s.get('passed', 0)
                failed = s.get('failed', 0)
                blocked = s.get('blocked', 0)
                total = s.get('total', 0)
                print(f"  第{auto_round}轮: {passed}通过 / {failed}失败 / {blocked}阻塞  ({_elapsed(t0)})")

                if total > 0 and passed == total:
                    print(f"  全部通过!")
                    break

                _cleanup_round_failures(WORKSPACE)

                if prev_passed is not None and passed <= prev_passed:
                    print(f"  无进展 (passed {passed} <= {prev_passed})，停止")
                    break
                prev_passed = passed

            print(f"\n测试完成: {passed}通过 / {failed}失败 / {blocked}阻塞  ({_elapsed(t0)})")
        else:
            print("未找到测试任务文件")

    # ═══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  全部流程完成! (总耗时 {_elapsed(t_total)})")
    print(f"{'='*60}")
    print(f"代码目录: {WORKSPACE}")
    print(f"测试目录: {WORKSPACE / 'test'}")


if __name__ == "__main__":
    asyncio.run(main())
