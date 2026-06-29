/**
 * 购物车全局状态 Store
 * 管理购物车商品列表、数量、总价，遵循 model_cart_item 契约
 */
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import request from '@/utils/request';

export const useCartStore = defineStore('cart', () => {
  // ==================== State ====================
  const items = ref([]);
  const loading = ref(false);
  const error = ref(null);

  // ==================== Getters ====================

  /** 购物车商品总数量 */
  const totalQuantity = computed(() => {
    return items.value.reduce((sum, item) => sum + (item.quantity || 0), 0);
  });

  /** 购物车商品总价（使用 parseFloat 处理 DECIMAL 字符串） */
  const totalPrice = computed(() => {
    return items.value.reduce((sum, item) => {
      const price = parseFloat(item.price) || 0;
      const quantity = item.quantity || 0;
      return sum + price * quantity;
    }, 0);
  });

  /** 购物车是否为空 */
  const isEmpty = computed(() => items.value.length === 0);

  /** 购物车中商品种类数 */
  const itemCount = computed(() => items.value.length);

  // ==================== Actions ====================

  /**
   * 从服务端获取购物车列表
   * @returns {Promise<Array>} 购物车商品数组
   */
  async function fetchCart() {
    loading.value = true;
    error.value = null;
    try {
      const res = await request.get('/cart');
      items.value = Array.isArray(res.data) ? res.data : [];
      return items.value;
    } catch (err) {
      error.value = err?.response?.data?.message || '获取购物车失败';
      items.value = [];
      return [];
    } finally {
      loading.value = false;
    }
  }

  /**
   * 添加商品到购物车
   * @param {number} productId - 商品 ID
   * @param {number} quantity - 数量，默认 1
   * @returns {Promise<object>} 添加后的购物车项
   */
  async function addToCart(productId, quantity = 1) {
    if (!Number.isFinite(productId) || productId <= 0) {
      throw new Error('无效的商品 ID');
    }
    if (!Number.isFinite(quantity) || quantity <= 0) {
      throw new Error('数量必须大于 0');
    }

    loading.value = true;
    error.value = null;
    try {
      const res = await request.post('/cart', { productId, quantity });
      // 添加成功后重新拉取购物车以保证数据一致
      await fetchCart();
      return res.data;
    } catch (err) {
      error.value = err?.response?.data?.message || '添加购物车失败';
      throw err;
    } finally {
      loading.value = false;
    }
  }

  /**
   * 从购物车移除指定商品
   * @param {number} cartItemId - 购物车项 ID
   * @returns {Promise<void>}
   */
  async function removeFromCart(cartItemId) {
    if (!Number.isFinite(cartItemId) || cartItemId <= 0) {
      throw new Error('无效的购物车项 ID');
    }

    loading.value = true;
    error.value = null;
    try {
      await request.delete(`/cart/${cartItemId}`);
      items.value = items.value.filter((item) => item.id !== cartItemId);
    } catch (err) {
      error.value = err?.response?.data?.message || '移除购物车失败';
      throw err;
    } finally {
      loading.value = false;
    }
  }

  /**
   * 更新购物车中商品数量
   * @param {number} cartItemId - 购物车项 ID
   * @param {number} quantity - 新数量（必须 >= 1）
   * @returns {Promise<object>} 更新后的购物车项
   */
  async function updateQuantity(cartItemId, quantity) {
    if (!Number.isFinite(cartItemId) || cartItemId <= 0) {
      throw new Error('无效的购物车项 ID');
    }
    if (!Number.isFinite(quantity) || quantity < 1) {
      throw new Error('数量必须大于等于 1');
    }

    loading.value = true;
    error.value = null;
    try {
      const res = await request.put(`/cart/${cartItemId}`, { quantity });
      // 同步更新本地数据
      const idx = items.value.findIndex((item) => item.id === cartItemId);
      if (idx !== -1) {
        items.value[idx] = { ...items.value[idx], quantity };
      }
      return res.data;
    } catch (err) {
      error.value = err?.response?.data?.message || '更新购物车失败';
      throw err;
    } finally {
      loading.value = false;
    }
  }

  /**
   * 清空购物车
   * @returns {Promise<void>}
   */
  async function clearCart() {
    loading.value = true;
    error.value = null;
    try {
      await request.delete('/cart');
      items.value = [];
    } catch (err) {
      error.value = err?.response?.data?.message || '清空购物车失败';
      throw err;
    } finally {
      loading.value = false;
    }
  }

  /** 重置状态（用于登出时调用） */
  function reset() {
    items.value = [];
    loading.value = false;
    error.value = null;
  }

  return {
    // state
    items,
    loading,
    error,
    // getters
    totalQuantity,
    totalPrice,
    isEmpty,
    itemCount,
    // actions
    fetchCart,
    addToCart,
    removeFromCart,
    updateQuantity,
    clearCart,
    reset,
  };
});
