# C: integrate — 集成修复

继承 [static.md](../static.md) 通用规则。

## 🛑 工作流程

integ 是静态层最后一道门——所有 infra/db/frontend/peer_deps 已验证通过，integ 做最终集成检查。

1. **先读 prompt 中的「任务检查点」** — 逐条验证
2. **🛑 路由注册完整性**: app.js 中 require 的路由文件存在 + routes/ 下所有文件都被注册（双向）+ app.use 前缀与 @mount 一致
3. **🛑 前后端启动验证**: `node -e "require('./app')"` 不崩溃 + `npx vite build` 不报错
4. **npm 依赖完整性**: 扫描 `src/` 下所有裸 import，确保 package.json + node_modules 就绪
5. **🆕 种子数据就绪**: 检查 `database/seed/` 目录 → `node scripts/init-db.js --seed-only`
6. **🛑 env 配置 + 注释（铁律）**: 
   - prompt 含根 .env.example 全部内容
   - 扫描代码 process.env.X → 取交集填真实值，无交集填 your_xxx_here
   - 🛑 **每个变量上方必须单独一行 # 注释**，例: `# 数据库主机地址` + 下一行 `DB_HOST=localhost`
   - 🛑 分组用 `# ══ 分组名 ══` 头，第三方 API 区加 `# -- MODE=real 需填 --`
   - 🛑 create_files 写 .env 时 content 字符串中每行 KEY=VALUE 上方必须有 # 注释行
   - 只写 work/project/.env

## 修复策略

```
🛑 死路由（import 指向不存在的 .vue）:
  - **删除整条路由块 + 对应的 import 行**（不注释，直接删）
  - 页面存在但路径不对 → 修正 import 路径

🛑 路由缺漏:
  - src/pages/ 下 .vue 未注册 → 补 import + route 到 router/index.js
  - routes/ 下 .js 未注册 → 补 require + app.use 到 app.js

🛑 env 配置（扫描代码 ∩ 根 .env.example → 写 .env → Python 同步）:
  - prompt 中已包含根 .env.example 全部内容，不要自己读文件
  - 扫描代码 process.env.X → 得到项目需要的变量集
  - 🛑 取交集：代码引用的变量 ∩ 根配置有的 → 填根配置真实值
  - 🛑 根配置没有的 → 填占位符 your_xxx_here
  - 🛑 每个变量必须单独一行 # 注释，禁止裸变量。格式:
    ```
    # 数据库主机地址
    DB_HOST=localhost
    # 数据库端口
    DB_PORT=3306
    # 数据库用户名
    DB_USER=root
    # 数据库密码
    DB_PASSWORD=szyszy
    # 数据库名
    DB_NAME=testdb
    ```
  - 分组用 # ══ 分组名 ══ 头，第三方 API 区用 # -- MODE=real 需填 -- 标注
  - *_MODE 值写死 mock
  - 只写 work/project/.env — Python 后处理自动同步其他三个文件

🛑 CJS require 链断裂:
  - 全量扫描后端 require() → 每个 require 目标必须存在
  - 文件缺失 → create_files 创建；路径错误 → edit_batch 修正
  - 🛑 **middleware 导入铁律**: `middleware/auth.js` 导出 `{ authenticate, optionalAuth }` → 必须用 `const { authenticate } = require('./middleware/auth')` 解构导入，禁止 `const authenticate = require(...)`（拿到的是整个对象不是函数）

npm 依赖缺失 → src/ 下 import 的包不在 package.json 中，npm install --save 补上
```
