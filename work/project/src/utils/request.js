import axios from 'axios';
import { ElMessage } from 'element-plus';

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' }
});

/** Request interceptor — attach auth token */
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

/** Response interceptor — unwrap data, handle errors */
request.interceptors.response.use(
  (res) => {
    const body = res.data;
    if (body.success) {
      return body.data;
    }
    ElMessage.error(body.message || '请求失败');
    return Promise.reject(new Error(body.message || '请求失败'));
  },
  (error) => {
    const status = error.response?.status;
    if (status === 401) {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
    } else if (status === 403) {
      ElMessage.error('无权访问');
    } else if (status === 500) {
      ElMessage.error('服务器错误，请稍后重试');
    } else {
      ElMessage.error(error.response?.data?.message || error.message || '网络错误');
    }
    return Promise.reject(error);
  }
);

export default request;
