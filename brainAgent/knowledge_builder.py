# brainAgent/knowledge_builder.py
"""
知识库构建调度器（Brain Agent）
"""
#      Memory\test_failure,Memory\source_failure,work\project\task,work\project\test
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from localAgent.knowledge_builder import run_knowledge_builder
from Tools.rag.build import tools
from Tools.coding.list_files import list_files
load_dotenv('./.env.example')
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

def print_step(step: str, msg: str = ""):
    print(f"\n{'='*50}")
    print(f"[Step {step}] {msg}")
    print(f"{'='*50}")

def get_file_info(file_path: Path) -> dict:
    try:
        stat = file_path.stat()
        return {"size": stat.st_size, "mtime": stat.st_mtime}
    except Exception:
        return {"size": 0, "mtime": 0.0}

def classify_files(file_list: list, workspace: Path) -> dict:
    memory_files = []
    task_files = []
    source_files = []
    source_exts = {".js", ".py", ".ts", ".vue", ".java", ".go", ".rs", ".cpp", ".c"}

    for rel_path in file_list:
        full_path = workspace / rel_path
        ext = full_path.suffix.lower()
        file_entry = {
            "path": str(full_path).replace('\\', '/'),
            "ext": ext,
            "size": get_file_info(full_path)["size"],
            "mtime": get_file_info(full_path)["mtime"]
        }

        if ext == ".json":
            if "task_" in rel_path.lower() or rel_path.lower().endswith("test_tasks.json"):
                task_files.append(file_entry)
            elif "test" in rel_path.lower() or "failure" in rel_path.lower():
                memory_files.append(file_entry)
        elif ext in source_exts:
            source_files.append(file_entry)

    return {"memory_files": memory_files, "task_files": task_files, "source_files": source_files}

async def run_build(user_query: str) -> dict:
    print("\n" + "🚀" * 30)
    print(f"  知识库构建任务: {user_query}")
    print("🚀" * 30)

    result = {"success": False, "steps": {}, "error": None, "stats": {}}

    # -------- Step 0: 文件发现 --------
    print_step("0", "文件发现 - 硬编码扫描目录")
    parts = user_query.split("build", 1)
    dir_str = parts[1].strip() if len(parts) > 1 else user_query.strip()
    if not dir_str or dir_str.lower() in ("memory", "test_failure"):
        dir_str = "Memory/test_failure,Memory/source_failure,work/project/test,work/project/task"
        print("  未指定目录，使用默认路径: Memory/test_failure, Memory/source_failure, work/project/test, work/project/task")

    try:
        scan_result = await list_files(directory=dir_str, workspace=str(PROJECT_ROOT))
    except Exception as e:
        result["error"] = f"文件扫描失败: {e}"
        return result

    if not scan_result["success"]:
        result["error"] = scan_result.get("error", "扫描失败")
        return result

    file_list = scan_result.get("files", [])
    if not file_list:
        result["error"] = "未找到任何文件"
        return result

    discover_result = classify_files(file_list, PROJECT_ROOT)
    memory_files = discover_result["memory_files"]
    task_files = discover_result["task_files"]
    source_files = discover_result["source_files"]

    result["steps"]["0_discover"] = {
        "total_files": len(file_list),
        "memory_files": len(memory_files),
        "task_files": len(task_files),
        "source_files": len(source_files)
    }

    if not memory_files:
        result["error"] = "未找到任何记忆文件（JSON）"
        return result

    print(f"  发现 {len(memory_files)} 个记忆文件, {len(task_files)} 个任务文件, {len(source_files)} 个源文件")

    # -------- Step 1: 记忆过滤 --------
    print_step("1", "记忆清洗与层级过滤")
    all_bans = []
    for f in memory_files:
        try:
            with open(f["path"], 'r', encoding='utf-8') as fp:
                data = json.load(fp)
                # 为每条 ban 附加 source_file 信息
                if isinstance(data, list):
                    for ban in data:
                        ban["source_file"] = f["path"]
                    all_bans.extend(data)
                elif isinstance(data, dict) and "bans" in data:
                    for ban in data["bans"]:
                        ban["source_file"] = f["path"]
                    all_bans.extend(data["bans"])
        except Exception as e:
            print(f"  警告: 读取 {f['path']} 失败: {e}")
            continue

    filter_result = tools.filter_memory(all_bans)
    cleaned_bans = filter_result["cleaned_bans"]
    result["steps"]["1_filter"] = {
        "total_bans": len(all_bans),
        "cleaned": len(cleaned_bans),
        "discarded": filter_result["discarded"]
    }
    if not cleaned_bans:
        result["error"] = "没有高价值记忆（L3+）"
        return result
    print(f"  过滤后保留 {len(cleaned_bans)} 条高价值记忆")

    # -------- Step 2: 锚点绑定 --------
    print_step("2", "构建双任务映射链")
    test_task_path = None
    arch_task_path = None
    for f in task_files:
        if "test_tasks" in f["path"]:
            test_task_path = f["path"]
        elif "task_" in f["path"]:
            arch_task_path = f["path"]

    if not test_task_path or not arch_task_path:
        result["error"] = f"缺少任务文件: test_tasks={test_task_path}, arch={arch_task_path}"
        return result

    with open(test_task_path, 'r', encoding='utf-8') as f:
        test_tasks = json.load(f)
    with open(arch_task_path, 'r', encoding='utf-8') as f:
        arch_tasks = json.load(f)

    anchored_records = tools.build_anchor_mapping(cleaned_bans, test_tasks, arch_tasks)
    result["steps"]["2_anchor"] = {"anchored_count": len(anchored_records)}
    print(f"  绑定了 {len(anchored_records)} 条记录")

    # -------- Step 3: LLM 净化 --------
    print_step("3", "LLM 深度经验净化")
    refined_records = []
    if anchored_records:
        refine_input = {"anchored_records": anchored_records}
        refine_result = await run_knowledge_builder("refine", refine_input)

        if isinstance(refine_result, list):
            # 补全缺失的图锚点字段
            for i, rec in enumerate(refine_result):
                if i < len(anchored_records):
                    original = anchored_records[i]
                    if "trigger_contracts" not in rec or not rec.get("trigger_contracts"):
                        rec["trigger_contracts"] = original.get("trigger_contracts", [])
                    if "trigger_tags" not in rec or not rec.get("trigger_tags"):
                        rec["trigger_tags"] = original.get("trigger_tags", [])
                    if "trigger_tasks" not in rec or not rec.get("trigger_tasks"):
                        rec["trigger_tasks"] = original.get("trigger_tasks", [])
            refined_records = refine_result
            result["steps"]["3_refine"] = {"refined_count": len(refined_records)}
            print(f"  净化完成: {len(refined_records)} 条")
        else:
            print("  降级使用原始数据")
            for r in anchored_records:
                ban_text = r.get("ban_text", "")
                parts = ban_text.split("|")
                refined_records.append({
                    "source_fingerprint": r.get("source_fingerprint", ""),
                    "do": parts[1] if len(parts) > 1 else ban_text,
                    "dont": parts[0] if len(parts) > 0 else "",
                    "context": "原始记忆，待优化",
                    "entity_refs": [],
                    "severity": r.get("severity", "medium"),
                    "category": "logic pitfall",
                    "trigger_contracts": r.get("trigger_contracts", []),
                    "trigger_tags": r.get("trigger_tags", []),
                    "trigger_tasks": r.get("trigger_tasks", []),
                })
            result["steps"]["3_refine"] = {"refined_count": len(refined_records), "fallback": True}
    else:
        result["error"] = "无数据需要净化"
        return result

    if not refined_records:
        result["error"] = "净化后无数据"
        return result

    # -------- Step 3.5: 泛化 — Python pattern_tags + LLM 语义泛化 --------
    print_step("3.5", "经验泛化 — 提取跨项目通用模式标签")
    from Tools.rag.build.tools import extract_pattern_tags
    generalized_count = 0
    for rec in refined_records:
        # Python 规则驱动: 从 do/dont/context/category/fingerprint 提取通用标签
        pattern_tags = extract_pattern_tags(rec)
        rec["pattern_tags"] = pattern_tags
        if pattern_tags:
            generalized_count += 1

    # LLM 深度泛化: 对 high severity 记录做语义层面的跨项目抽象
    high_severity = [r for r in refined_records if r.get("severity") == "high"]
    if high_severity:
        try:
            generalize_input = {"records": [{
                "source_fingerprint": r.get("source_fingerprint", ""),
                "do": r.get("do", ""),
                "dont": r.get("dont", ""),
                "context": r.get("context", ""),
                "category": r.get("category", ""),
                "severity": r.get("severity", "medium"),
            } for r in high_severity[:5]]}  # 最多 5 条，控制 token
            gen_result = await run_knowledge_builder("generalize", generalize_input)
            if isinstance(gen_result, list):
                for i, gen in enumerate(gen_result):
                    if i < len(high_severity) and isinstance(gen, dict):
                        # 合并泛化标签到原始记录
                        cross_tags = gen.get("cross_project_tags", [])
                        if cross_tags:
                            existing = set(high_severity[i].get("pattern_tags", []))
                            existing.update(cross_tags)
                            high_severity[i]["pattern_tags"] = sorted(existing)
                        # 保存泛化后的通用描述
                        high_severity[i]["generalized_do"] = gen.get("pattern_do", "")
                        high_severity[i]["generalized_dont"] = gen.get("pattern_dont", "")
                        high_severity[i]["generalized_context"] = gen.get("pattern_context", "")
            result["steps"]["3.5_generalize"] = {
                "rule_based_tags": generalized_count,
                "llm_generalized": len(high_severity[:5]) if gen_result and isinstance(gen_result, list) else 0,
            }
            print(f"  规则标签: {generalized_count} 条, LLM泛化: {len(high_severity[:5])} 条(high severity)")
        except Exception as e:
            result["steps"]["3.5_generalize"] = {"rule_based_tags": generalized_count, "llm_error": str(e)[:100]}
            print(f"  规则标签: {generalized_count} 条, LLM泛化失败: {e}")
    else:
        result["steps"]["3.5_generalize"] = {"rule_based_tags": generalized_count}
        print(f"  规则标签: {generalized_count} 条")

    # -------- Step 4: 去重与合并 --------
    print_step("4", "去重与语义合并")
    table = tools.create_table(force_recreate=False)
    if table is None:
        table = tools.create_table(force_recreate=True)
    if table is None:
        result["error"] = "无法创建或打开 LanceDB 表"
        return result

    dedup_result = tools.dedup_by_fingerprint(refined_records, table)
    inserts = dedup_result["inserts"]
    updates = dedup_result["updates"]
    skipped = dedup_result["skipped"]

    semantic_result = tools.semantic_dedup(inserts, table)
    truly_new = semantic_result["truly_new"]
    semantic_skipped = semantic_result["semantic_skipped"]
    review_items = semantic_result["review_items"]

    merged_items = []
    if review_items:
        print(f"  发现 {len(review_items)} 条需要语义合并")
        for item in review_items:
            merge_input = {
                "new_record": {
                    "source_fingerprint": item.get("source_fingerprint", ""),
                    "do": item.get("do", ""),
                    "dont": item.get("dont", ""),
                    "context": item.get("context", ""),
                    "entity_refs": item.get("entity_refs", []),
                    "severity": item.get("severity", "medium"),
                    "category": item.get("category", "logic pitfall")
                },
                "similar_id": item.get("_similar_to", "")
            }
            merge_result = await run_knowledge_builder("merge", merge_input)
            if isinstance(merge_result, dict) and "do" in merge_result:
                try:
                    lance_ds = table.to_lance()
                    old = lance_ds.to_table(filter=f"id = '{item['_similar_to']}'").to_pylist()
                    if old:
                        old_rec = old[0]
                        merged = {
                            "id": old_rec["id"],
                            "version": old_rec.get("version", 1) + 1,
                            "source_fingerprint": old_rec.get("source_fingerprint", "") + "|" + item.get("source_fingerprint", ""),
                            "do": merge_result["do"],
                            "dont": merge_result["dont"],
                            "context": merge_result["context"],
                            "entity_refs": merge_result.get("entity_refs", []),
                            "severity": merge_result.get("severity", old_rec.get("severity", "medium")),
                            "category": merge_result.get("category", old_rec.get("category", "logic pitfall")),
                            "trigger_tasks": list(set(old_rec.get("trigger_tasks", []) + item.get("trigger_tasks", []))),
                            "trigger_contracts": list(set(old_rec.get("trigger_contracts", []) + item.get("trigger_contracts", []))),
                            "trigger_tags": list(set(old_rec.get("trigger_tags", []) + item.get("trigger_tags", []))),
                            "source_files": list(set(old_rec.get("source_files", []) + item.get("source_files", []))),
                        }
                        merged_items.append(merged)
                except Exception as e:
                    print(f"  合并失败: {e}")
                    merged_items.append(item)
            else:
                merged_items.append(item)

        updates.extend(merged_items)
        merged_fingerprints = {item.get("source_fingerprint") for item in review_items}
        inserts = [r for r in truly_new if r.get("source_fingerprint") not in merged_fingerprints]
    else:
        inserts = truly_new
        print("  无语义重复需要合并")

    final_inserts = inserts
    final_updates = updates
    final_skipped = skipped + semantic_skipped

    result["steps"]["4_dedup"] = {
        "inserts": len(final_inserts),
        "updates": len(final_updates),
        "skipped": len(final_skipped),
        "merged": len(merged_items)
    }
    print(f"  新增: {len(final_inserts)}, 更新: {len(final_updates)}, 跳过: {len(final_skipped)}")

    if not final_inserts and not final_updates:
        result["success"] = True
        result["stats"] = {"stored": 0, "updated": 0, "skipped": len(final_skipped)}
        result["message"] = "无新数据需要存储"
        return result

    # -------- Step 5: 向量化并存储 --------
    print_step("5", "向量化并存储")
    to_store = final_inserts + final_updates
    store_result = tools.vectorize_and_store(to_store)
    result["steps"]["5_store"] = store_result
    print(f"  存储完成: {store_result.get('stored', 0)} 条, 更新 {store_result.get('updated', 0)} 条")

    # -------- Step 6: 创建索引 --------
    print_step("6", "创建索引")
    table = tools.open_table()
    if table:
        tools.create_indices(table)
        result["steps"]["6_index"] = {"success": True}
        print("  索引创建完成")
    else:
        result["steps"]["6_index"] = {"success": False, "error": "表不存在"}
        print("  警告: 表不存在，跳过索引")

    # -------- 完成 --------
    result["success"] = True
    result["stats"] = {
        "stored": store_result.get("stored", 0),
        "updated": store_result.get("updated", 0),
        "skipped": len(final_skipped),
        "total_in_db": tools.table_count()
    }

    print("\n" + "✅" * 30)
    print("  知识库构建完成！")
    print(f"  新增: {result['stats']['stored']} 条")
    print(f"  更新: {result['stats']['updated']} 条")
    print(f"  跳过: {result['stats']['skipped']} 条")
    print(f"  总记录数: {result['stats']['total_in_db']}")
    print("✅" * 30)

    return result

# ---------- 入口 ----------
async def main():
    print("\n" + "🧠" * 30)
    print("  Knowledge Builder - Brain Agent")
    print("  硬编码调度 + Agent 按需 LLM 调用")
    print("🧠" * 30)

    while True:
        try:
            query = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[Exit]")
            break
        if not query:
            continue
        if query.lower() in ("quit", "exit"):
            break

        result = await run_build(query)
        if result.get("success"):
            print(f"\n✅ 构建成功")
        else:
            print(f"\n❌ 构建失败: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(main())