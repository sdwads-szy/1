# Navigation 检查模板 (Layer 5: navigation) — passBy + 参数传递

```javascript
const fs = require('fs');
const path = require('path');
const workspace = process.env.WORKSPACE || '../../';

describe('{task_id}', () => {
  // 从 navigation 契约读取: passBy, fromPage, toPage, dataTransfer
  const passBy = '{passBy}';  // params 或 query
  const fromPage = '{fromPage}';
  const toPage = '{toPage}';
  const dataKeys = ['{dataKeys}'];  // dataTransfer 中的字段名

  // 读取源页面文件
  const fromFile = path.join(workspace, 'src/pages', fromPage + '.vue');
  const fromCode = fs.existsSync(fromFile) ? fs.readFileSync(fromFile, 'utf-8') : '';

  // 读取目标页面文件
  const toFile = path.join(workspace, 'src/pages', toPage + '.vue');
  const toCode = fs.existsSync(toFile) ? fs.readFileSync(toFile, 'utf-8') : '';

  // 读取 router
  const routerFile = path.join(workspace, 'src/router/index.js');
  const routerCode = fs.readFileSync(routerFile, 'utf-8');

  it('源页传递方式与 passBy 一致', () => {
    if (passBy === 'params') {
      expect(fromCode).toMatch(/router\.push\(\s*\{\s*name:.*params:/);
    } else if (passBy === 'query') {
      expect(fromCode).toMatch(/router\.push\(\s*\{\s*name:.*query:/);
    }
  });

  it('目标页用对应方式读取参数', () => {
    if (passBy === 'params') {
      expect(toCode).toMatch(/route\.params\./);
    } else if (passBy === 'query') {
      expect(toCode).toMatch(/route\.query\./);
    }
  });

  it('参数名在源和目标之间一致', () => {
    dataKeys.forEach(key => {
      const passPattern = new RegExp(key + '\\s*:', 'i');
      const readPattern = new RegExp('route\\.(params|query)\\.' + key, 'i');
      expect(fromCode).toMatch(passPattern);
      expect(toCode).toMatch(readPattern);
    });
  });

  it('目标路由在 router 中注册', () => {
    const routeName = '{routeName}';
    expect(routerCode).toContain(`name: '${routeName}'`);
  });

  it('passBy=params 时路由路径有动态段', () => {
    if (passBy === 'params') {
      const routePath = '{toPageRoute}';
      expect(routePath).toMatch(/:\w+/);  // 至少一个 :paramName 段
    }
  });
});
```
