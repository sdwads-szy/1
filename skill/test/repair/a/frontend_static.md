# 前端静态层修复策略 (A步骤)
- 修复范围: .vue SFC语法、import路径、Store引用、API模块导出格式
- 语法错误 → create_file 重写 .vue 的 <script> 块
- import路径不存在 → 修正 @/ 路径或创建缺失文件
- Store引用不存在 → 对齐 store truth 中的属性名/action名
- export default → 改为命名导出 export function
