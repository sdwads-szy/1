# A repair: backend_proc

A 的测试代码被 B 判定 `fix_target=test` → A 自我修复。

## 判定：删了重写 vs 修补

| 情况 | 动作 | 工具 |
|------|------|------|
| 忘了 jest.mock('../../config/db') | **重写** | `create_files` 加载 [模板](../../../templates/logic/backend_proc.md) 全新生成 |
| 调了 supertest HTTP（backend_proc 直接调 service 函数） | **重写** | 同上 |
| mock 返回值结构全错（missing affectedRows/insertId） | **重写** | 同上 |
| mockResolvedValueOnce 顺序不对齐 process | **修补** | `edit_batch` 调整顺序 |
| toHaveBeenNthCalledWith(n) n 序号错 | **修补** | `edit_batch` 改序号 |
| 用了 toHaveBeenCalledWith 而非 NthCalledWith | **修补** | `edit_batch` 改为 NthCalledWith |
| 正向正常缺 `rollback 禁出现` | **修补** | `edit_batch` 补 `expect(rollback).not.toHaveBeenCalled()` |
| 正向异常缺 `commit 禁出现` | **修补** | `edit_batch` 补 `expect(commit).not.toHaveBeenCalled()` |
| catch 里 rollback 后忘 throw | **修补** | `edit_batch` 补 `await expect(...).rejects.toThrow()` |

🛑 修复后对照 [测试点表](../../roles/a/logic/backend_proc.md) 确认 process 每步→1个it + 正向正异 + 补偿。
