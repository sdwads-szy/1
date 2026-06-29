/**
 * 用户全局状态 Store
 * 管理登录态、用户信息、角色，遵循 auth_bearer 契约
 */
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import request from '@/utils/request';

export const useUserStore = defineStore('user', () => {
  // ==================== State ====================
  const token = ref(localStorage.getItem('auth_token') || '');
  const refreshTokenValue = ref(localStorage.getItem('refresh_token') || '');
  const user = ref(null);
  const loading = ref(false);

  // ==================== Getters ====================
  const isLoggedIn = computed(() => !!token.value);
  const userId = computed(() => user.value?.userId ?? null);
  const role = computed(() => user.value?.role || 'user');
  const isAdmin = computed(() => role.value === 'admin');
  const username = computed(() => user.value?.username || '');

  // ==================== Actions ====================

  /**
   * 设置 token 并持久化到 localStorage
   * @param {string} newToken - JWT access token
   */
  function setToken(newToken) {
    token.value = newToken;
    if (newToken) {
      localStorage.setItem('auth_token', newToken);
    } else {
      localStorage.removeItem('auth_token');
    }
  }

  /**
   * 设置 refreshToken 并持久化到 localStorage
   * @param {string} newToken - JWT refresh token
   */
  function setRefreshToken(newToken) {
    refreshTokenValue.value = newToken;
    if (newToken) {
      localStorage.setItem('refresh_token', newToken);
    } else {
      localStorage.removeItem('refresh_token');
    }
  }

  /**
   * 设置用户信息
   * @param {object|null} userInfo - 用户信息对象
   * @param {number} userInfo.userId
   * @param {string} userInfo.username
   * @param {string} userInfo.role
   */
  function setUser(userInfo) {
    user.value = userInfo;
  }

  /**
   * 登录：发送凭证，存储 token 和用户信息
   * @param {object} credentials
   * @param {string} credentials.username
   * @param {string} credentials.password
   * @returns {Promise<object>} 用户信息
   */
  async function login(credentials) {
    loading.value = true;
    try {
      const res = await request.post('/auth/login', credentials);
      const { token: newToken, refreshToken: newRefreshToken, user: userInfo } = res.data;
      setToken(newToken);
      if (newRefreshToken) setRefreshToken(newRefreshToken);
      setUser(userInfo);
      return userInfo;
    } finally {
      loading.value = false;
    }
  }

  /**
   * 退出登录：清除 token 和用户信息
   */
  async function logout() {
    try {
      await request.post('/auth/logout');
    } catch {
      // 即使服务端请求失败，也要清除本地状态
    } finally {
      setToken('');
      setRefreshToken('');
      setUser(null);
    }
  }

  /**
   * 从服务端获取当前用户信息（用于页面刷新恢复登录态）
   * @returns {Promise<object|null>} 用户信息，未登录返回 null
   */
  async function fetchUserInfo() {
    if (!token.value) return null;
    loading.value = true;
    try {
      const res = await request.get('/auth/me');
      const userInfo = res.data;
      setUser(userInfo);
      return userInfo;
    } catch (err) {
      // token 过期或无效，清除登录态
      if (err?.response?.status === 401) {
        setToken('');
        setRefreshToken('');
        setUser(null);
      }
      return null;
    } finally {
      loading.value = false;
    }
  }

  /**
   * 使用 refreshToken 刷新 access token
   * @returns {Promise<boolean>} 是否刷新成功
   */
  async function refreshAccessToken() {
    if (!refreshTokenValue.value) return false;
    try {
      const res = await request.post('/auth/refresh', {
        refreshToken: refreshTokenValue.value,
      });
      const { token: newToken, refreshToken: newRefreshToken } = res.data;
      setToken(newToken);
      if (newRefreshToken) setRefreshToken(newRefreshToken);
      return true;
    } catch {
      setToken('');
      setRefreshToken('');
      setUser(null);
      return false;
    }
  }

  return {
    // state
    token,
    refreshToken: refreshTokenValue,
    user,
    loading,
    // getters
    isLoggedIn,
    userId,
    role,
    isAdmin,
    username,
    // actions
    setToken,
    setRefreshToken,
    setUser,
    login,
    logout,
    fetchUserInfo,
    refreshAccessToken,
  };
});
