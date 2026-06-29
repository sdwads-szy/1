# brainAgent/basic.py
"""
统一入口：从一句话需求到完整可运行系统的自动化流程。

流程:
  1. 需求分析 (orchestrator)   → requirement_report_*.md
  2. 架构设计 (architect)      → task_*.json (含契约)
  3. 代码生成 (engineer)       → 源代码 + 基础校验
  4. 测试验证 (test pipeline)  → 测试生成 + 执行 + 自动修复 + 报告

用法:
    python brainAgent/basic.py "设计一个线上商城购物系统"              # 全流程
    python brainAgent/basic.py -orchestrator "需求"                   # 只跑需求分析
    python brainAgent/basic.py -architect                             # 从架构开始
    python brainAgent/basic.py -engineer                              # 从代码生成开始
    python brainAgent/basic.py -test                                  # 从测试开始
    python brainAgent/basic.py -test --fast                           # 从测试开始(快速模式)
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


def _validate_code_generation(workspace: Path) -> dict:
    ws = Path(workspace).resolve()
    if not ws.exists():
        return {"ok": False, "error": f"workspace not found: {ws}"}

    def _is_esm_frontend(filepath: Path) -> bool:
        try:
            head = filepath.read_text("utf-8")[:1024]
            cleaned = __import__('re').sub(r'//.*|/\*[\s\S]*?\*/', '', head)
            return bool(__import__('re').search(r'(?:^|\n)\s*(?:import\s+|export\s+)', cleaned))
        except Exception:
            return False

    js_files = list(ws.rglob("*.js"))
    src_files = [f for f in js_files
                 if "node_modules" not in str(f)
                 and str(ws / "test") not in str(f.parent.resolve())
                 and not _is_esm_frontend(f)]

    syntax_errors = []
    for f in src_files:
        r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            rel = str(f.relative_to(ws)).replace("\\", "/")
            err = (r.stderr or "")[:120].replace('\n', ' ')
            syntax_errors.append(f"{rel}: {err}")

    return {
        "ok": len(syntax_errors) == 0,
        "js_files": len(src_files),
        "vue_files": len(list(ws.rglob("*.vue"))),
        "sql_files": len(list(ws.rglob("*.sql"))),
        "syntax_errors": syntax_errors,
    }


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
        # 从统一配置文件加载默认值，与 integrator.py 保持一致
        try:
            import json
            config_path = project_root / "config" / "env_defaults.json"
            config = json.loads(config_path.read_text("utf-8"))
            defaults = config.get("env_defaults", {})
        except Exception:
            defaults = {}
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
    parser.add_argument("-test", action="store_true", help="从测试验证开始（跳过需求+架构+代码）")
    parser.add_argument("--task-file", type=str, help="指定任务文件路径")
    parser.add_argument("--requirement-report", type=str, help="指定需求报告路径")
    parser.add_argument("--max-rounds", type=int, default=3, help="需求分析最大轮次")
    parser.add_argument("--session-id", type=str, default="project_session", help="会话ID")
    parser.add_argument("--fast", action="store_true", help="测试快速模式")
    parser.add_argument("--resume", action="store_true", help="恢复模式：跳过已成功生成的代码")
    args = parser.parse_args()

    # 确定起始阶段
    start_from = "orchestrator"
    if args.architect: start_from = "architect"
    if args.engineer: start_from = "engineer"
    if args.test: start_from = "test"

    run_orch = start_from == "orchestrator"
    run_arch = start_from in ("orchestrator", "architect")
    run_eng = start_from in ("orchestrator", "architect", "engineer")
    run_test = True  # always run test

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
        print(f"  Step 1/4: 需求分析")
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
        print(f"  Step 2/4: 架构设计（生成开发任务+契约）")
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
        print(f"  Step 3/4: 代码生成（并发执行开发任务）")
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
    # Step 4: 测试验证
    # ═══════════════════════════════════════════════════════════
    if run_test:
        print(f"\n{'='*60}")
        print(f"  Step 4/4: 测试验证（生成 + 执行 + 自动修复）")
        print(f"{'='*60}")

        # 4a: 生成测试任务清单（-test 模式下跳过，直接用已有文件）
        import glob
        if start_from == "test":
            files = sorted(glob.glob(f"{WORKSPACE}/test/test_tasks_*.json"))
            test_tasks_file = files[-1] if files else ""
            if test_tasks_file:
                print(f"\n[Step 4a] 跳过生成，使用已有: {test_tasks_file}")
            else:
                print("\n[Step 4a] 未找到 test_tasks_*.json，无法运行测试")
        else:
            print("\n[Step 4a] 生成测试任务清单...")
            t0 = _timer()
            test_arch_result = await run_test_architect(task_path=task_file)
            if test_arch_result.get("success"):
                test_tasks_file = str(test_arch_result.get('output', ''))
                print(f"测试任务: {test_tasks_file} ({test_arch_result.get('task_count', 0)} 个)  ({_elapsed(t0)})")
            else:
                print(f"测试任务生成失败: {test_arch_result.get('error', '')[:200]}")
                files = sorted(glob.glob(f"{WORKSPACE}/test/test_tasks_*.json"))
                test_tasks_file = files[-1] if files else ""
                if test_tasks_file:
                    print(f"降级使用: {test_tasks_file}")

        # 4b: 运行测试调度器（自动多轮）
        if test_tasks_file and Path(test_tasks_file).exists():
            print("\n[Step 4b] 测试调度器（自动多轮）...")
            t0 = _timer()
            prev_passed, passed, failed, blocked = 0, 0, 0, 0
            stagnation_count = 0
            for auto_round in range(1, 11):
                test_report = await run_scheduler(str(WORKSPACE), test_tasks_file, fast=args.fast)
                s = test_report.get("summary", {})
                passed, failed, blocked = s.get('passed', 0), s.get('failed', 0), s.get('blocked', 0)
                total = s.get('total', 0)
                print(f"  第{auto_round}轮: {passed}通过 {failed}失败 {blocked}阻塞  ({_elapsed(t0)})")
                if total > 0 and passed == total:
                    print(f"  全部通过!")
                    break
                if passed > prev_passed:
                    prev_passed = passed
                    stagnation_count = 0  # 有进展，重置停滞计数
                    continue
                stagnation_count += 1
                if stagnation_count >= 2:
                    print(f"  连续{stagnation_count}轮停滞 ({prev_passed}->{passed})，需人工")
                    break
                print(f"  停滞 {stagnation_count}/2 ({prev_passed}->{passed})，继续尝试...")

            print(f"\n测试完成: {passed}通过 {failed}失败 {blocked}阻塞  ({_elapsed(t0)})")
        else:
            print("未找到测试任务文件")
    else:
        print("跳过测试验证")

    # ═══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  全部流程完成! (总耗时 {_elapsed(t_total)})")
    print(f"{'='*60}")
    print(f"代码目录: {WORKSPACE}")
    print(f"测试目录: {WORKSPACE / 'test'}")


if __name__ == "__main__":
    asyncio.run(main())
