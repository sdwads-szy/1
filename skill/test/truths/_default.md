# 通用真理提取

提取本层验证通过后的对外接口信息。

{context}
代码:
{files}

输出 JSON:
```json
{
  "exposed_to_upper": {},
  "exposed_to_peers": {}
}
```
🛑 exposed_to_upper: 上层需要知道的接口
🛑 exposed_to_peers: 同层需要引用的接口
