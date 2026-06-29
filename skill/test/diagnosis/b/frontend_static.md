# 前端静态层诊断 (B步骤)
诊断范围限定: SFC语法、import路径、Store引用、导出格式
- SyntaxError → fix_target=source, 子类型=syntax, 指向具体.vue文件
- Cannot find module '@/...' → fix_target=source, 子类型=MISSING_IMPORT, 指向具体import行
- xxx is not a function (Store) → fix_target=source, 子类型=STORE_REF, 指向store文件
- export default found → fix_target=source, 子类型=DEFAULT_EXPORT, 指向api模块
禁止扩大到: 业务逻辑、后端路由、数据库结构
