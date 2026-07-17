# k6 性能测试模板

🛑 用 k6 编写性能/并发测试。k6 是 Go 编写的压测工具，脚本是 JavaScript（ES5 子集）。
🛑 不支持 `require`、`import`、`async/await`。用 k6 内置模块 `http`、`check`、`sleep`。
🛑 执行方式（调度器自动选择）:
   - Docker: `docker run --rm -v $(pwd):/tests grafana/k6 run /tests/test.js`
   - 本地: `k6 run test.js`（winget install k6.k6）

## 占位符取值

| 占位符 | 来源 | 怎么用 |
|--------|------|--------|
| `{task_id}` | 任务数据 `id` | describe 名称 |
| `{base_url}` | .env VITE_API_TARGET 或 http://localhost:3000 | k6 请求的 base URL |
| `{path}` | testScenarios[].input | 被测接口路径 |
| `{vus}` | testScenarios[].input (并发数) | options.vus |
| `{duration}` | testScenarios[].input (持续时间) | options.duration |

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: {vus},           // 并发虚拟用户数
  duration: '{duration}s', // 持续时间
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% 请求 < 500ms
    http_req_failed: ['rate<0.01'],   // 失败率 < 1%
  },
};

const BASE_URL = __ENV.BASE_URL || '{base_url}';

export default function () {
  // ── correct: 正常请求响应时间 ──
  const res = http.get(`${BASE_URL}{path}`);
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  sleep(0.1);
}

// ── 并发场景 ──
export function concurrencyTest() {
  const payload = JSON.stringify({ productId: 10, quantity: 1 });
  const params = { headers: { 'Content-Type': 'application/json' } };
  const res = http.post(`${BASE_URL}/api/order`, payload, params);
  check(res, {
    'order created (201) or conflict (409)': (r) => r.status === 201 || r.status === 409,
  });
}
```
