# navigation 测试模板 — 参数化跳转验证

🛑 不验证 .vue 存在（frontend 真理已验证）、不验证 router 注册（integ 真理已验证）。
🛑 只验证跳转逻辑: routeName 一致 + passBy 方式 + 参数名传递。
🛑 **所有值从真理 JSON 提取，禁止编造不存在的跳转或参数名。**

## 第一步：从真理提取参数

在 `## 🥇 下层真理` 的 `@truth t_frontend_*` → `pages` + `router` 中提取：

```
{FROM_PAGE}     ← pages.{PageName}.file             如 "src/pages/frontend/home/Home.vue"
{TO_PAGE}       ← pages.{PageName}.file             如 "src/pages/frontend/category/Category.vue"
{ROUTE_NAME}    ← router.{Name}.name                如 "Category"
{PASS_BY}       ← router.{Name}.params→"params"     如 "params" / "query" / "none"
                / router.{Name}.query→"query"
{PARAMS}        ← router.{Name}.params              如 ["id"]
{FROM_ORIGIN}   ← router.{Name}.origin              如 "Home.vue goToCategory"
```

🛑 **铁律：上面每个值从真理 JSON 逐字抄。真理 router 没有某个跳转 → 不测这个跳转。禁止编造不存在的页面跳转（如 Register→Home）。**

## 第二步：按 scenario category 选维度

| category | 启用维度 |
|:---:|------|
| correct | 维度1(入口) + 维度2(passBy) + 维度3(参数名) + 维度4(返回) |
| error | 维度5(passBy不匹配) + 维度6(参数名不一致) |

🛑 error 场景必须基于真实存在的跳转。不能编造一个不存在的跳转然后断言它"不匹配"。

## 第三步：填入骨架

```javascript
const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

function readPageSafe(pagePath) {
  const fullPath = path.join(workspace, pagePath);
  if (!fs.existsSync(fullPath)) { console.warn('SKIP: ' + pagePath); return null; }
  return fs.readFileSync(fullPath, 'utf-8');
}

describe('{TASK_ID}', () => {
  const fromPagePath = '{FROM_PAGE}';
  const toPagePath   = '{TO_PAGE}';
  const routeName    = '{ROUTE_NAME}';
  const passBy       = '{PASS_BY}';
  const params       = {PARAMS_ARRAY};

  const fromPage = readPageSafe(fromPagePath);
  const toPage   = readPageSafe(toPagePath);

  // ==== 维度1: 源页包含跳转入口 ====
  describe('correct — 源页包含跳转入口', () => {
    if (!fromPage || !toPage) return;

    it('源页提到了目标路由名: ' + routeName, () => {
      expect(fromPage).toContain(routeName);
    });
  });

  // ==== 维度2: passBy 方式 ====
  describe('correct — passBy 方式: ' + passBy, () => {
    if (!fromPage) return;

    it('源页用 ' + passBy + ' 传参', () => {
      if (passBy === 'params') {
        expect(fromPage.includes('params:') || fromPage.includes('params :')).toBe(true);
      } else if (passBy === 'query') {
        expect(fromPage.includes('query:') || fromPage.includes('query :')).toBe(true);
      }
      // passBy=none → 不传参，跳过此检查
    });
  });

  // ==== 维度3: 参数名一致 ====
  describe('correct — 参数名一致', () => {
    if (!fromPage) return;

    // 🛑 每个参数 1 个 it()
    {PARAM_ITEMS}
  });

  // ==== 维度4: 返回导航 ====
  describe('correct — 返回导航', () => {
    if (!toPage) return;

    it('目标页可返回源页（提到了源路由名）', () => {
      const FROM_NAME = {FROM_ROUTE_NAME};
      expect(toPage).toContain(FROM_NAME);
    });
  });

  // ==== 维度5: error — passBy 不匹配 ====
  describe('error — passBy 不匹配', () => {
    if (!fromPage) return;

    it('源页传参方式与预期不一致则参数丢失', () => {
      const hasQuery = fromPage.includes('query:') || fromPage.includes('query :');
      const hasParams = fromPage.includes('params:') || fromPage.includes('params :');

      if (passBy === 'params' && hasQuery) {
        fail('passBy 冲突: 预期 params 但源页用了 query');
      } else if (passBy === 'query' && hasParams) {
        fail('passBy 冲突: 预期 query 但源页用了 params');
      }
      // 无冲突 → 通过
    });
  });

  // ==== 维度6: error — 参数名不一致 ====
  describe('error — 参数名不一致', () => {
    if (!fromPage || !toPage || params.length === 0) return;

    it('源页和目标页的参数名应一致', () => {
      params.forEach(p => {
        expect(fromPage).toContain(p);
        expect(toPage).toContain(p);
      });
    });
  });
});
```

**{PARAM_ITEMS} 填充规则：**
```javascript
// params = ["id"] → 1 个 it()
it('参数 id 在源页中传递', () => {
  expect(fromPage).toContain('id');
});
// params = [] 或 passBy=none → 跳过此 describe
```

🛑 只用 toContain，不写复杂正则。routeName 是精确字符串，直接匹配。
🛑 error 场景只测真实存在的跳转，不编造假跳转。
🛑 不在 navigation 中断言 router/index.js 内容（integ 层负责）。
🛑 **导航入口按钮的生成归静态层**（frontend checkPoints）：navigation 只验证已存在跳转的 passBy/params 正确性，不负责发现缺失的入口。

---

## 🆕 auth-flow 骨架（登录→重定向 运行时测试）

**当 testScenario 包含 `category: auth-flow` 时，使用此骨架替代静态骨架。**
此骨架用 `jest.mock` mock store + `fs.readFileSync` 读页面源码，验证登录后的角色跳转逻辑。

```javascript
const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

// Mock 路由（只 mock push/replace，保留其他导出）
jest.mock('vue-router', () => ({
  ...jest.requireActual('vue-router'),
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
  useRoute: () => mockRoute,
}));

// Mock store
jest.mock('@/stores/user', () => ({
  useUserStore: () => userStoreMock,
}));

const mockPush = jest.fn();
const mockReplace = jest.fn();
const mockRoute = { query: {} };
const userStoreMock = { role: null, token: null };

// 导入被测模块（trigger mock 后导入）
const loginPage = fs.readFileSync(path.join(workspace, '{LOGIN_PAGE}'), 'utf-8');

describe('{TASK_ID} — auth-flow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockRoute.query = {};
    userStoreMock.role = null;
    userStoreMock.token = null;
  });

  // ==== 维度1: redirect query 参数回跳 ====
  describe('redirect query 回跳来源页', () => {
    it('有 redirect query 时 router.push(redirectPath)', () => {
      // 源码: const redirectPath = route.query.redirect;
      //       if (redirectPath) { router.push(redirectPath); }
      expect(loginPage).toContain('route.query.redirect');
      expect(loginPage).toContain('router.push');
    });
  });

  // ==== 维度2: 角色跳转 ====
  describe('角色跳转', () => {
    it('role=user → router.push(\'/\')', () => {
      // 源码: } else { router.push('/'); }
      expect(loginPage).toContain("router.push('/')");
    });

    it('role=merchant → router.push({name:\'MerchantDashboard\'})', () => {
      // 源码: userStore.role === 'merchant'
      expect(loginPage).toContain("userStore.role");
      expect(loginPage).toContain('MerchantDashboard');
    });

    it('role=admin → router.push({name:\'AdminDashboard\'})', () => {
      expect(loginPage).toContain('AdminDashboard');
    });
  });

  // ==== 维度3: store 正确消费 API 返回值 ====
  describe('store 消费 API 返回值', () => {
    it('store.login() 从 res.data 提取 token 写入 localStorage', () => {
      // 🛑 验证 store 源码不是 res.data.data.token（双重 wrapper）
      const storeSrc = fs.readFileSync(path.join(workspace, '{STORE_FILE}'), 'utf-8');
      expect(storeSrc).toContain('localStorage.setItem');
      expect(storeSrc).toContain('token');
      // 不应该有 res.data.data（request.js 拦截器已剥掉一层）
      if (storeSrc.includes('res.data.data')) {
        throw new Error('store 使用了 res.data.data，但 request.js 拦截器已剥掉 axios wrapper，应为 res.data');
      }
    });

    it('store.login() 从 user 对象提取 role（非顶层解构）', () => {
      const storeSrc = fs.readFileSync(path.join(workspace, '{STORE_FILE}'), 'utf-8');
      // role 应该在 user 对象内，不在顶层
      expect(storeSrc).toContain('role');
      expect(storeSrc).toContain('user.');
    });
  });
});
```

**auth-flow 参数提取表**：

| 占位符 | 来源 |
|--------|------|
| `{LOGIN_PAGE}` | testScenario.input.loginPage（如 `src/pages/auth/login.vue`） |
| `{STORE_FILE}` | testScenario.input.storeFile（如 `src/stores/user.js`） |

🛑 auth-flow 的 `res.data.data` 检查是硬约束——store 源码中出现此模式则测试直接失败。因为 `request.js` 拦截器已剥 axios wrapper。
