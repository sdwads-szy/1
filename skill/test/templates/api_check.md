# API 检查模板 (Layer 4: api) — 前端调用 vs 后端路由匹配

```javascript
const fs = require('fs');
const path = require('path');
const workspace = process.env.WORKSPACE || '../../';

describe('{task_id}', () => {
  // 从前端 API 模块提取调用: POST /orders, GET /orders/:id...
  const apiFile = path.join(workspace, '{frontendApiModule}');
  const apiCode = fs.existsSync(apiFile) ? fs.readFileSync(apiFile, 'utf-8') : '';
  const feCalls = [...apiCode.matchAll(/url:\s*['"]([^'"]+)['"]\s*,\s*method:\s*['"]([^'"]+)['"]/g)]
    .map(m => ({ method: m[2].toUpperCase(), url: m[1] }));

  // 从后端路由文件提取 handler: router.post('/'), router.get('/:id')...
  const routeFile = path.join(workspace, '{backendRouteFile}');
  const routeCode = fs.existsSync(routeFile) ? fs.readFileSync(routeFile, 'utf-8') : '';
  const beRoutes = [...routeCode.matchAll(/router\.(get|post|put|delete|patch)\s*\(\s*['"]([^'"]+)['"]/g)]
    .map(m => ({ method: m[1].toUpperCase(), path: m[2] }));

  it('每个前端 API 调用在后端有对应路由', () => {
    feCalls.forEach(call => {
      const matched = beRoutes.some(r => {
        // 路径匹配: /orders/:id ↔ /:id (basePath 前缀在挂载时处理)
        const fePath = call.url.replace(/:\w+/g, ':param');
        const bePath = r.path.replace(/:\w+/g, ':param');
        return r.method === call.method && fePath === bePath;
      });
      expect(matched).toBe(true);
    });
  });

  it('auth 标记一致: 前端 auth=true → 后端有 authenticate 中间件', () => {
    // 从 route 文件检查中间件链
    const beHandlers = [...routeCode.matchAll(/router\.(get|post|put|delete)\s*\(\s*['"][^'"]+['"]\s*,\s*([^)]+)\)/g)];
    beHandlers.forEach(h => {
      const handlerList = h[2];
      if (apiCode.includes('auth') && !handlerList.includes('authenticate')) {
        // 前端 auth=true 但后端无 authenticate
      }
    });
  });
});
```
