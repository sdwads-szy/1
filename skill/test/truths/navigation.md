# navigation 真理提取

本层产出页面跳转关系。

**上层**: scenario（全链路需要页面跳转路径）。
**同层**: 各 navigation 任务独立（每组相邻页面互不依赖），无同层数据传递。

{context}
代码:
{files}

```json
{
  "exposed_to_upper": {
    "jumps": [
      {
        "from": "src/pages/frontend/home/Home.vue",
        "to": "src/pages/frontend/category/Category.vue",
        "passBy": "params",
        "params": ["id"],
        "routeName": "Category"
      },
      {
        "from": "src/pages/frontend/home/Home.vue",
        "to": "src/pages/frontend/user/UserProfile.vue",
        "passBy": "none",
        "params": [],
        "routeName": "UserProfile"
      },
      {
        "from": "src/pages/frontend/product/ProductDetail.vue",
        "to": "src/pages/frontend/cart/Cart.vue",
        "passBy": "params",
        "params": ["productId", "skuSn", "quantity"],
        "routeName": "Cart"
      }
    ]
  },
  "exposed_to_peers": {}
}
```

🛑 一个页面可能有多个跳转出口——每个跳转都要在 `jumps[]` 中列出一条。上面 Home.vue → Category 和 Home.vue → UserProfile 两个跳转，全列出来了。

### exposed_to_upper

| 字段 | 类型 | 写给谁 | 说明 |
|------|------|--------|------|
| `from` | string | scenario | 跳转源页面路径 |
| `to` | string | scenario | 跳转目标页面路径 |
| `passBy` | string | scenario | `"params"` / `"query"` / `"none"` |
| `params` | string[] | scenario | 参数名数组 |
| `routeName` | string | scenario | 🛑 目标路由 name |

### exposed_to_peers

空。各 navigation 任务覆盖不同的页面组，互不依赖。
