# 前端静态层源码修复 (C步骤)

C 修改 .vue 文件、API 模块或 router 文件。修复目标: 文件语法正确、引用存在、格式规范。

## 典型 ban → 修复动作

```
syntax:
  .vue <script> 块语法错误 → node --check 定位错误行
  → edit_batch 修正 或 create_files 重写整个 <script> 块
  → 常见: 多余的 }); 、缺少闭合括号、正则语法错

MISSING_IMPORT:
  from '@/pages/Xxx' 目标不存在 → 用 fs.existsSync 验证实际路径
  → 修正: @/pages/auth/Login.vue → @/pages/Login.vue (文件在根目录时)
  → 或修正: @/pages/FavoriteList.vue → @/pages/frontend/FavoriteList.vue (缺子目录)

STORE_REF:
  store.xxx 在 store truth 中不存在 → 查 store truth 的实际 state/actions
  → 修正: userStore.userInfo → userStore.user (truth 中实际属性)
  → 修正: userStore.userRole → userStore.user?.role (从 user 对象取)

DEFAULT_EXPORT:
  API 模块用了 export default → 改为 export function xxx() {}
  → create_files 重写整个 API 模块为命名导出

RESPONSE_UNWRAP:
  页面中 res.orderId → 应为 res.data.orderId (Axios 拦截器解包后 data 在第一层)
  → edit_batch 替换: res.xxx → res.data.xxx
  → 例外: res.status / res.body 等 Axios 原生属性不改
```

## 修复方式
- 单行语法错 → edit_batch
- 多处语法错/结构性崩塌 → create_files 重写
- 路径错误 → edit_batch 替换路径字符串
- 不修改测试文件
