# 后端处理层修复策略 (A步骤)
- 修复范围: HTTP请求→DB落库的数据管道问题
- 请求字段未映射到DB列 → 检查 controller 的 req.body 解构 vs service INSERT
- 响应字段与DB不一致 → 检查 service 返回值 vs response.success data
- 关联表未写入 → 补充 INSERT 语句
