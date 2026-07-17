import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import request from '@/utils/request';
import { useCartStore } from './cart';

/**
 * 用户状态管理
 * - token 持久化到 localStorage key='auth_token'
 * - 退出登录清空所有 store（含购物车）
 */
export const useUserStore = defineStore('user', () => {
  // ── State ──
  const token = ref(null);
  const userId = ref(null);
  const nickname = ref(null);
  const avatar = ref(null);
  const role = ref(null);
  const userInfo = ref(null);

  // ── Getters ──
  const isLoggedIn = computed(() => !!token.value);
  const isMerchant = computed(() => role.value === 'merchant');
  const isAdmin = computed(() => role.value === 'admin');
  const isUser = computed(() => role.value === 'user');

  // ── Actions ──

  /**
   * 登录（手机号 + 验证码/密码）
   * @param {Object} credentials - { mobile, code } 或 { mobile, password }
   */
  async function login(credentials) {
    const res = await request.post('/auth/login', credentials);
    if (res.success) {
      const payload = res.data;
      const { token: t, user } = payload;
      token.value = t;
      try { localStorage.setItem('auth_token', t); } catch { /* noop */ }
      userId.value = user && user.userId;
      role.value = user && user.role;
      nickname.value = user && user.nickname;
      avatar.value = user && user.avatar;
      userInfo.value = user || null;
    }
    return res;
  }

  /**
   * 注册
   * @param {Object} data - 注册表单数据
   */
  async function register(data) {
    const res = await request.post('/auth/register', data);
    return res;
  }

  /**
   * 刷新 token（主动调用，如页面恢复时）
   * 注：request.js 拦截器已自动处理 401 → refresh → 重试
   */
  async function refreshToken() {
    try {
      const res = await request.post('/auth/refresh');
      if (res.success) {
        const payload = res.data;
        const { token: t, user } = payload;
        token.value = t;
        try { localStorage.setItem('auth_token', t); } catch { /* noop */ }
        userId.value = user && user.userId;
        role.value = user && user.role;
      }
      return res;
    } catch {
      logout();
      return { success: false, message: '登录已过期，请重新登录' };
    }
  }

  /**
   * 获取当前用户个人信息
   */
  async function fetchProfile() {
    const res = await request.get('/user/profile');
    if (res.success) {
      const profile = res.data;
      userInfo.value = profile;
      nickname.value = (profile && profile.nickname) || null;
      avatar.value = (profile && profile.avatar) || null;
      role.value = (profile && profile.role) || role.value;
    }
    return res;
  }

  /**
   * 退出登录 — 清空所有 store 状态
   */
  function logout() {
    token.value = null;
    try { localStorage.removeItem('auth_token'); } catch { /* noop */ }
    userId.value = null;
    nickname.value = null;
    avatar.value = null;
    role.value = null;
    userInfo.value = null;
    // 同步清空购物车
    const cartStore = useCartStore();
    cartStore.clearCart();
  }

  return {
    // state
    token,
    userId,
    nickname,
    avatar,
    role,
    userInfo,
    // getters
    isLoggedIn,
    isMerchant,
    isAdmin,
    isUser,
    // actions
    login,
    register,
    refreshToken,
    fetchProfile,
    logout,
  };
});
