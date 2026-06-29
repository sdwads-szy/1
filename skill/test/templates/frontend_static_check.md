# 前端静态检查模板 (Layer 1.5: frontend_static)

```javascript
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const workspace = process.env.WORKSPACE || '../../';

describe('{task_id}', () => {
  // SFC 语法: node --check
  it('所有 .vue <script> 块通过 node --check', () => {
    const vueFiles = ['{targetFiles}'];  // 从 testScenarios 获取
    vueFiles.forEach(f => {
      const content = fs.readFileSync(path.join(workspace, f), 'utf-8');
      const scriptMatch = content.match(/<script[^>]*>([\s\S]*?)<\/script>/);
      if (scriptMatch) {
        expect(() => execSync(`node --check -`, { input: scriptMatch[1] })).not.toThrow();
      }
    });
  });

  // import 路径: 目标文件存在
  it('所有 @/ import 路径存在', () => {
    const files = ['{targetFiles}'];
    files.forEach(f => {
      const content = fs.readFileSync(path.join(workspace, f), 'utf-8');
      const imports = content.matchAll(/from\s+['"]@\/([^'"]+)['"]/g);
      for (const m of imports) {
        const resolved = path.join(workspace, 'src', m[1]);
        const exists = [resolved, resolved + '.js', resolved + '.vue', resolved + '/index.js']
          .some(p => fs.existsSync(p));
        expect(exists).toBe(true);
      }
    });
  });

  // 命名导出
  it('API 模块使用命名导出, 无 export default', () => {
    const apiFiles = ['{targetFiles}'].filter(f => f.includes('api/'));
    apiFiles.forEach(f => {
      const content = fs.readFileSync(path.join(workspace, f), 'utf-8');
      expect(content).not.toMatch(/export\s+default/);
    });
  });

  // 响应解包
  it('响应字段访问路径与后端格式一致', () => {
    // 扫描 .vue 中的 res.data.xxx vs res.xxx
    const vueFiles = ['{targetFiles}'].filter(f => f.endsWith('.vue'));
    vueFiles.forEach(f => {
      const content = fs.readFileSync(path.join(workspace, f), 'utf-8');
      // Axios 拦截器解包后 data 在第一层: res.data.xxx 正确, res.xxx 错误
      const wrongPattern = content.match(/res\.\w+(?!\.data)\b/g);
      // 允许 res.status / res.body, 但 res.orderId 应该写成 res.data.orderId
    });
  });
});
```
