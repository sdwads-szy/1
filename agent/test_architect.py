# agent/test_architect.py
"""
TestArchitect Agent —— 读 PRD + task.json → 生成 test_tasks.json。
8 层测试设计，自底向上依赖执行。不读源码。
"""

import asyncio, json, os, sys
from pathlib import Path
from datetime import datetime
from picoagents import Agent, OpenAIChatCompletionClient
from dotenv import load_dotenv

load_dotenv("./.env.example")

current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from utils.token import wrap_agent_stream

TEST_SKILL = parent_dir / "skill" / "test" / "test_architect.md"
TASK_DIR = parent_dir / "work" / "project" / "task"
DOC_DIR = parent_dir / "work" / "project" / "doc"
TEST_OUTPUT_DIR = parent_dir / "work" / "project" / "test"
TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_skill(path: Path) -> str:
    if path.exists():
        return path.read_text("utf-8")
    return ""


def find_latest_task() -> Path:
    files = sorted(TASK_DIR.glob("task_*.json"))
    if not files:
        raise FileNotFoundError(f"No task files in {TASK_DIR}")
    return max(files, key=lambda p: p.stat().st_mtime)


def find_latest_prd() -> Path:
    files = sorted(DOC_DIR.glob("requirement_report_*.md"))
    if not files:
        raise FileNotFoundError(f"No PRD files in {DOC_DIR}")
    return max(files, key=lambda p: p.stat().st_mtime)


async def run_test_architect(task_path: str = None, prd_path: str = None) -> dict:
    """Generate test_tasks.json from PRD + architecture_plan.json.

    Args:
        task_path: Path to task JSON. Auto-discovers latest if None.
        prd_path: Path to PRD markdown. Auto-discovers latest if None.
    """
    if task_path:
        task_path = Path(task_path)
    else:
        task_path = find_latest_task()

    if prd_path:
        prd_path = Path(prd_path)
    else:
        prd_path = find_latest_prd()

    if not task_path.exists():
        return {"success": False, "error": f"Task not found: {task_path}"}
    if not prd_path.exists():
        return {"success": False, "error": f"PRD not found: {prd_path}"}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = TEST_OUTPUT_DIR / f"test_tasks_{timestamp}.json"

    skill = load_skill(TEST_SKILL)

    # 预加载输入文件内容
    task_content = task_path.read_text("utf-8")
    prd_content = prd_path.read_text("utf-8")

    # 读取 .env + .env.example 用于 mock/real 判定
    env_text = ""
    for env_name in [".env", ".env.example"]:
        env_path = task_path.parent.parent / env_name  # work/project/.env
        if env_path.exists():
            env_text += f"\n### {env_name}\n```\n{env_path.read_text('utf-8')[:3000]}\n```\n"

    # 读取失败任务清单（engineer 阶段产出）
    failed_text = ""
    failed_path = task_path.parent.parent / ".meta" / "failed_tasks.json"
    if failed_path.exists():
        failed_text = f"\n### 失败任务（需优先修复，含原始 outputFiles+description+dependencies）\n```json\n{failed_path.read_text('utf-8')[:10000]}\n```\n"

    instructions = f"""{skill}

## 本次任务
- 任务文件: {task_path}（已预加载）
- 需求报告: {prd_path}（已预加载）
- 输出文件: {output_file}
- Truth 目录: Memory/truths/engineer/（接口声明，替代读源码）

## 执行要点
1. 基于 PRD + task JSON + truth 文件 + .env + failed_tasks 生成测试计划。🛑 不读业务源码——需要接口信息时从 Memory/truths/engineer/{'{task_id}'}.json 的 exposed 字段获取。
2. 🛑 **先建规划树**：用 create_file 将树保存到 work/project/test/_test_plan_tree.md。树建完后对照 task.json 校验每个 targetFile 是否来自 sourceTask.outputFiles。校验通过后树即为唯一基准，后续只需对照树。
3. 🛑 **Layer -1 修复层**：若存在 failed_tasks.json，为 `failed` 列表生成修复任务。**跳过 `pruned` 列表**——pruned 任务的 outputFiles 从未生成，禁止为其创建测试任务。修复任务不能出现在其他 dependencies 中。
4. 🛑 **静态层 (Layer 0~2) 全绿后才进入动态层 (Layer 3~8)**——不需要 HTTP 的放前面。
5. 🛑 **每层只测连接点**：scenario 不测 logic、logic 不测 DB、api 不测前后端内部。只测本层负责的接口匹配。
6. 🛑 **targetFiles 必填**：从 sourceTask 的 outputFiles 逐字复制，禁止自编文件名。
7. 🛑 **逐层数量对照**：对照 task JSON contracts 数量，每层 byLayer ≥ 对应契约数量。不满足→回补。
8. 🛑 **同层依赖从 sourceTask.dependencies 推导**：架构任务 A 依赖 B → A 的测试任务依赖 B 的测试任务。
9. 🛑 **.env 真值决定 mock**：已预加载。本地服务直连，占位符 mock。
10. 生成完毕后对照 Skill 的"闭合检查区"逐项勾选，全部 ✅ 后再写 test_tasks.json。

## 输入文件内容

### 1. 任务文件
{task_content}

### 2. 需求报告
{prd_content}
{env_text}
{failed_text}
"""

    model_client = OpenAIChatCompletionClient(model=os.getenv("OPENAI_MODEL"))

    from Tools.coding.create_file import create_file

    agent = Agent(
        name="test_architect",
        description="Test Architect - test plan generation from PRD + task JSON",
        instructions=instructions,
        model_client=model_client,
        tools=[create_file],
        max_iterations=20,
    )

    print(f"[test_architect] Task: {task_path.name}")
    print(f"[test_architect] PRD: {prd_path.name}")
    print(f"[test_architect] Output: {output_file.name}")

    collected = []
    try:
        async for event in agent.run_stream(
            "Read the PRD and task JSON, then generate the complete test plan.",
            stream_tokens=False,
        ):
            collected.append(str(event))
    except Exception as e:
        print(f"[test_architect] Error: {e}")
        return {"success": False, "error": str(e)}

    # 处理 LLM 分片输出（part1/part2/part3...）
    part_files = sorted(TEST_OUTPUT_DIR.glob(f"test_tasks_{timestamp}_part*.json"))
    if part_files:
        print(f"[test_architect] 合并 {len(part_files)} 个分片文件...")
        merged_tasks = []
        metadata = {}
        summary = {}
        for pf in part_files:
            try:
                pd = json.loads(pf.read_text("utf-8"))
                merged_tasks.extend(pd.get("testTasks", []))
                if not metadata:
                    metadata = pd.get("metadata", {})
                # 合并 summary
                for k, v in pd.get("summary", {}).items():
                    if isinstance(v, dict):
                        summary.setdefault(k, {}).update(v)
                    elif isinstance(v, (int, float)):
                        summary[k] = summary.get(k, 0) + v
            except (json.JSONDecodeError, KeyError):
                pass  # skip corrupt fragment
        if merged_tasks:
            final = {"metadata": metadata, "summary": summary, "testTasks": merged_tasks}
            output_file.write_text(json.dumps(final, indent=2, ensure_ascii=False), "utf-8")
            # 删分片
            for pf in part_files:
                pf.unlink()
            print(f"[test_architect] 合并完成: {len(merged_tasks)} 个测试任务")
        # 清理其它遗留分片和索引文件
        for stale in TEST_OUTPUT_DIR.glob("test_tasks_*_index.json"):
            stale.unlink()
        for stale in TEST_OUTPUT_DIR.glob("test_tasks_*_summary.md"):
            stale.unlink()

    ok = output_file.exists()
    task_count = 0
    validation_issues = []
    if ok:
        try:
            data = json.loads(output_file.read_text("utf-8"))
            test_tasks = data.get("testTasks", [])
            task_count = len(test_tasks)
            print(f"[test_architect] Done: {task_count} test tasks")

            # ── Python 后校验: targetFiles vs sourceTask.outputFiles ──
            validation_issues = _validate_test_tasks(test_tasks, task_path)
            if validation_issues:
                print(f"[test_architect] Validation: {len(validation_issues)} issues found, auto-fixing...")
                _auto_fix_test_tasks(test_tasks, task_path, validation_issues)
                data["testTasks"] = test_tasks
                output_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
                print(f"[test_architect] Auto-fixed and saved")
        except Exception:
            ok = False

    return {
        "success": ok,
        "output": str(output_file),
        "task_count": task_count,
        "validation_issues": len(validation_issues),
    }


def _validate_test_tasks(test_tasks: list, task_path: Path) -> list:
    """校验每个测试任务的 targetFiles 是否来自对应架构任务的 outputFiles。"""
    issues = []
    try:
        arch_data = json.loads(task_path.read_text("utf-8"))
        arch_tasks = arch_data.get("tasks", [])
        arch_by_id = {}
        for t in arch_tasks:
            tid = t.get("taskId") or t.get("id", "")
            arch_by_id[tid] = set(t.get("outputFiles") or t.get("files") or [])

        for tt in test_tasks:
            st = tt.get("sourceTask", "")
            tfs = tt.get("targetFiles", [])
            if not st:
                continue
            valid_outputs = arch_by_id.get(st, set())
            if not valid_outputs:
                continue
            bad = [f for f in tfs if f not in valid_outputs]
            if bad:
                issues.append({"task_id": tt["id"], "bad_files": bad, "valid_files": list(valid_outputs)})
    except Exception:
        pass
    return issues


def _auto_fix_test_tasks(test_tasks: list, task_path: Path, issues: list):
    """自动修复: 删除编造的 targetFiles，移除对应的 scenarios。"""
    bad_map = {i["task_id"]: set(i["bad_files"]) for i in issues}
    for tt in test_tasks:
        tid = tt.get("id", "")
        if tid not in bad_map:
            continue
        bad_set = bad_map[tid]
        # 移除编造的 targetFiles
        tt["targetFiles"] = [f for f in tt.get("targetFiles", []) if f not in bad_set]
        # 移除引用这些文件的 scenarios
        tt["testScenarios"] = [
            s for s in tt.get("testScenarios", [])
            if not any(bf in s.get("given", "") + s.get("when", "") for bf in bad_set)
        ]


async def main():
    result = await run_test_architect()
    print(f"\nResult: {result}")


if __name__ == "__main__":
    asyncio.run(main())
