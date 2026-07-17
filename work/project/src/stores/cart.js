import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import request from '@/utils/request';

/**
 * 购物车状态管理
 * - badge 实时计算勾选/总数量，供导航栏徽标使用
 * - 退出登录时由 userStore.logout() 触发清空
 */
export const useCartStore = defineStore('cart', () => {
  // ── State ──
  const items = ref([]);

  // ── Getters ──

  /** 购物车商品总数（用于导航栏 badge） */
  const count = computed(() =>
    items.value.reduce((sum, item) => sum + (item.quantity || 0), 0)
  );

  /** 已勾选商品数 */
  const checkedCount = computed(() =>
    items.value.filter((item) => item.checked).length
  );

  /** 已勾选商品列表 */
  const checkedItems = computed(() =>
    items.value.filter((item) => item.checked)
  );

  /** 已勾选商品总金额 */
  const totalAmount = computed(() =>
    checkedItems.value.reduce(
      (sum, item) => sum + (item.price || 0) * (item.quantity || 0),
      0
    )
  );

  // ── Actions ──

  /**
   * 获取购物车列表
   */
  async function fetchCart() {
    const res = await request.get('/cart');
    if (res.data.success) {
      items.value = res.data.data || [];
    }
    return res.data;
  }

  /**
   * 加入购物车
   * @param {number} skuId
   * @param {number} quantity
   * @param {number} shopId
   */
  async function addToCart(skuId, quantity, shopId) {
    const res = await request.post('/cart', { skuId, quantity, shopId });
    if (res.data.success) {
      await fetchCart();
    }
    return res.data;
  }

  /**
   * 更新购物车商品数量
   * @param {number} cartItemId
   * @param {number} quantity
   */
  async function updateQuantity(cartItemId, quantity) {
    const res = await request.put(`/cart/${cartItemId}`, { quantity });
    if (res.data.success) {
      await fetchCart();
    }
    return res.data;
  }

  /**
   * 从购物车移除
   * @param {number} cartItemId
   */
  async function removeItem(cartItemId) {
    const res = await request.delete(`/cart/${cartItemId}`);
    if (res.data.success) {
      await fetchCart();
    }
    return res.data;
  }

  /**
   * 切换勾选状态
   * @param {number} cartItemId
   */
  async function toggleChecked(cartItemId) {
    const item = items.value.find((i) => i.id === cartItemId);
    if (!item) return;
    const res = await request.patch(`/cart/${cartItemId}`, {
      checked: !item.checked,
    });
    if (res.data.success) {
      await fetchCart();
    }
    return res.data;
  }

  /**
   * 批量勾选/取消勾选
   * @param {number[]} cartItemIds
   * @param {boolean} checked
   */
  async function batchCheck(cartItemIds, checked) {
    const res = await request.patch('/cart/batch-check', {
      cartItemIds,
      checked,
    });
    if (res.data.success) {
      await fetchCart();
    }
    return res.data;
  }

  /**
   * 清空购物车状态（退出登录时由 userStore 调用）
   */
  function clearCart() {
    items.value = [];
  }

  return {
    // state
    items,
    // getters
    count,
    checkedCount,
    checkedItems,
    totalAmount,
    // actions
    fetchCart,
    addToCart,
    updateQuantity,
    removeItem,
    toggleChecked,
    batchCheck,
    clearCart,
  };
});
