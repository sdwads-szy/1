import axios from 'axios';

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// ── 请求拦截：注入 access_token ──
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── 响应拦截：401 自动 refresh + 重试原请求（最多 1 次）──
let isRefreshing = false;
let refreshQueue = [];

function resolveQueue(token) {
  refreshQueue.forEach((cb) => cb(token));
  refreshQueue = [];
}

request.interceptors.response.use(
  // 成功：直接返回 response.data（{ success, code, message, data }）
  (response) => response.data,

  async (error) => {
    const { config, response } = error;

    // 非 401 或已重试过 → 直接 reject
    if (response?.status !== 401 || config._retry) {
      const msg = response?.data?.message || error.message;
      return Promise.reject(new Error(msg));
    }

    // 正在刷新 → 将请求排队，等拿到新 token 后重放
    if (isRefreshing) {
      return new Promise((resolve) => {
        refreshQueue.push((token) => {
          config.headers.Authorization = `Bearer ${token}`;
          resolve(request(config));
        });
      });
    }

    config._retry = true;
    isRefreshing = true;

    try {
      // refresh_token 存储在 HttpOnly Cookie 中，浏览器自动携带
      const { data } = await axios.post(
        '/api/auth/refresh',
        {},
        { withCredentials: true }
      );

      const newToken =
        data?.data?.token ||
        data?.data?.accessToken ||
        data?.token;

      if (!newToken) throw new Error('REFRESH_FAILED');

      localStorage.setItem('auth_token', newToken);
      request.defaults.headers.common.Authorization = `Bearer ${newToken}`;
      resolveQueue(newToken);

      config.headers.Authorization = `Bearer ${newToken}`;
      return request(config);
    } catch {
      // refresh 失败 → 清除登录态，跳转登录页
      localStorage.removeItem('auth_token');
      localStorage.removeItem('refresh_token');

      const { pathname, search } = window.location;
      if (!pathname.startsWith('/auth/login')) {
        window.location.href =
          '/auth/login?redirect=' + encodeURIComponent(pathname + search);
      }

      return Promise.reject(new Error('登录已过期，请重新登录'));
    } finally {
      isRefreshing = false;
    }
  }
);

export default request;
