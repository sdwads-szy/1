# 同层依赖检查模板 (Layer 3.5: peer_deps) — require/import + exportStyle

```javascript
const fs = require('fs');
const path = require('path');
const workspace = process.env.WORKSPACE || '../../';

describe('{task_id}', () => {
  // 扫描目标文件中的所有 require/import, 验证目标存在并导出格式匹配
  const targetFiles = ['{targetFiles}'];

  targetFiles.forEach(tf => {
    const filepath = path.join(workspace, tf);
    if (!fs.existsSync(filepath)) return;
    const content = fs.readFileSync(filepath, 'utf-8');

    // CJS require: 目标文件存在
    const requires = [...content.matchAll(/require\s*\(\s*['"](\.[^'"]+)['"]\s*\)/g)];
    requires.forEach(m => {
      const relPath = m[1];
      it(`${tf} require('${relPath}') 目标存在`, () => {
        const resolved = path.resolve(path.dirname(filepath), relPath);
        const exists = [resolved, resolved + '.js', resolved + '/index.js']
          .some(p => fs.existsSync(p));
        expect(exists).toBe(true);
      });
    });

    // 导出/消费格式匹配: 若目标 module.exports = X (default), 消费方不能 const { X } = require()
    requires.forEach(m => {
      const relPath = m[1];
      const resolved = [path.resolve(path.dirname(filepath), relPath),
        path.resolve(path.dirname(filepath), relPath + '.js')].find(p => fs.existsSync(p));
      if (!resolved) return;
      const targetSrc = fs.readFileSync(resolved, 'utf-8');
      const isDefaultExport = /module\.exports\s*=\s*\w+\s*;?\s*$/.test(targetSrc);
      const consumerLine = m[0];
      const isDestructured = /\{\s*\w+\s*\}/.test(consumerLine);

      it(`${tf} 消费 ${relPath} 格式匹配`, () => {
        if (isDefaultExport && isDestructured) {
          // default export 不能被解构消费
          expect(false).toBe(true);
        }
      });
    });
  });
});
```
