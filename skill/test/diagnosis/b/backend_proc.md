# backend_proc 层诊断 (B步骤)

诊断范围限定: HTTP请求→DB列→响应字段的数据管道。

## 判定规则

```
total=0 + SyntaxError → 测试代码语法错 → fix_target=test
total>0 + DB行数≠预期 → fix_target=source, 子类型=FIELD_NOT_PERSISTED
total>0 + DB字段值与请求不符 → fix_target=source, 子类型=FIELD_MAPPING_ERROR  
total>0 + 关联表无数据 → fix_target=source, 子类型=MISSING_RELATED_INSERT
total>0 + 响应字段与DB不一致 → fix_target=source, 子类型=RESPONSE_MISMATCH
```

## 常见失败模式

1. "Expected: 1, Received: 0" — 主表 INSERT 可能成功但关联表遗漏
2. "Expected: 'pending_pay', Received: undefined" — status 字段未写入或 DEFAULT 值不匹配
3. "response.data.orderNo !== db.order_no" — 字段名映射错误 (驼峰 vs 蛇形)
4. "cart_items still present after order" — 副作用未执行

## 禁止扩大到
- 金额计算是否正确 (logic层)
- 库存扣减逻辑 (logic层)
- 支付流程 (logic/scenario层)
