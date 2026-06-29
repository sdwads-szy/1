<template>
  <div class="cart-page">
    <!-- 顶部导航 -->
    <header class="cart-header">
      <div class="header-content">
        <h1 class="page-title">购物车</h1>
      </div>
    </header>

    <!-- 加载态 -->
    <div v-if="loading" class="state-container">
      <el-skeleton :rows="5" animated />
    </div>

    <!-- 错误态 -->
    <div v-else-if="error" class="state-container">
      <div class="state-box">
        <el-icon :size="56" color="#f97316"><WarningFilled /></el-icon>
        <p class="state-text">{{ error }}</p>
        <el-button type="primary" @click="fetchCartList" :loading="loading" round>重新加载</el-button>
      </div>
    </div>

    <!-- 空态 -->
    <div v-else-if="cartItems.length === 0" class="state-container">
      <div class="state-box">
        <el-icon :size="72" color="#d1d5db"><ShoppingCart /></el-icon>
        <p class="state-text">购物车是空的</p>
        <p class="state-hint">快去挑选喜欢的商品吧</p>
        <el-button type="primary" @click="goHome" round>去逛逛</el-button>
      </div>
    </div>

    <!-- 列表态 -->
    <template v-else>
      <div class="cart-list">
        <div
          v-for="item in cartItems"
          :key="item.cartId"
          class="cart-item"
        >
          <!-- 勾选框 -->
          <el-checkbox
            :model-value="item.selected"
            @change="(val) => onToggleSelect(item.cartId, val)"
            class="item-checkbox"
          />

          <!-- 商品图片 -->
          <div class="item-image">
            <el-image
              :src="item.image || defaultImage"
              fit="cover"
              lazy
              class="item-img"
            >
              <template #error>
                <div class="image-placeholder">
                  <el-icon :size="32" color="#d1d5db"><PictureFilled /></el-icon>
                </div>
              </template>
            </el-image>
          </div>

          <!-- 商品信息 -->
          <div class="item-info">
            <p class="item-title">{{ item.productTitle }}</p>
            <p class="item-spec">{{ item.specCombo }}</p>
            <div class="item-bottom">
              <span class="item-price">¥{{ parseFloat(item.price).toFixed(2) }}</span>
              <!-- 数量控制 -->
              <div class="quantity-control">
                <el-button
                  :disabled="item.quantity <= 1"
                  @click="onQuantityChange(item, item.quantity - 1)"
                  size="small"
                  circle
                  class="qty-btn"
                >
                  <el-icon><Minus /></el-icon>
                </el-button>
                <span class="qty-value">{{ item.quantity }}</span>
                <el-button
                  :disabled="item.quantity >= Math.min(item.stock, 99)"
                  @click="onQuantityChange(item, item.quantity + 1)"
                  size="small"
                  circle
                  class="qty-btn"
                >
                  <el-icon><Plus /></el-icon>
                </el-button>
              </div>
            </div>
          </div>

          <!-- 删除按钮 -->
          <el-button
            @click="onDeleteItem(item)"
            type="danger"
            link
            class="delete-btn"
          >
            <el-icon :size="18"><Delete /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- 底部结算栏 -->
      <div class="cart-footer">
        <div class="footer-left">
          <el-checkbox
            :model-value="isAllSelected"
            :indeterminate="isIndeterminate"
            @change="onToggleAll"
            size="large"
          >
            全选
          </el-checkbox>
        </div>
        <div class="footer-right">
          <div class="total-info">
            <span class="total-label">合计：</span>
            <span class="total-price">¥{{ totalPrice.toFixed(2) }}</span>
          </div>
          <el-button
            type="primary"
            :disabled="selectedCount === 0"
            @click="onCheckout"
            round
            size="large"
            class="checkout-btn"
          >
            去结算（{{ selectedCount }}）
          </el-button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
/**
 * 购物车页面 — 商品列表 / 数量修改 / 删除 / 全选 / 合计 / 结算跳转
 * 暖橙色主题
 */
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { WarningFilled, ShoppingCart, PictureFilled, Minus, Plus, Delete } from '@element-plus/icons-vue';
import { getCartList, updateCartItem, deleteCartItem } from '@/api/cart';

const router = useRouter();

const defaultImage = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgdmlld0JveD0iMCAwIDIwMCAyMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjIwMCIgaGVpZ2h0PSIyMDAiIGZpbGw9IiNmM2Y0ZjYiLz48L3N2Zz4=';

// --- state ---
const cartItems = ref([]);
const loading = ref(true);
const error = ref('');
const quantityLoading = ref({});

// --- computed ---
const selectedItems = computed(() => cartItems.value.filter((i) => i.selected));
const selectedCount = computed(() => selectedItems.value.length);
const isAllSelected = computed(() => cartItems.value.length > 0 && cartItems.value.every((i) => i.selected));
const isIndeterminate = computed(() => selectedCount.value > 0 && selectedCount.value < cartItems.value.length);

const totalPrice = computed(() => {
  return selectedItems.value.reduce((sum, item) => {
    return sum + parseFloat(item.price) * item.quantity;
  }, 0);
});

// --- methods ---
async function fetchCartList() {
  loading.value = true;
  error.value = '';
  try {
    const res = await getCartList();
    const data = res.data ?? res;
    cartItems.value = (data.items ?? []).map((item) => ({
      ...item,
      selected: item.selected ?? false,
    }));
  } catch (e) {
    error.value = e?.response?.data?.message || e?.message || '加载购物车失败，请稍后重试';
  } finally {
    loading.value = false;
  }
}

async function onQuantityChange(item, newQuantity) {
  if (newQuantity < 1 || newQuantity > Math.min(item.stock, 99)) return;
  const cartId = item.cartId;
  quantityLoading.value[cartId] = true;
  try {
    await updateCartItem(cartId, { quantity: newQuantity });
    item.quantity = newQuantity;
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || '修改数量失败');
  } finally {
    quantityLoading.value[cartId] = false;
  }
}

async function onDeleteItem(item) {
  try {
    await ElMessageBox.confirm(
      `确定要删除「${item.productTitle}」吗？`,
      '确认删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    );
  } catch {
    return;
  }

  try {
    await deleteCartItem(item.cartId);
    cartItems.value = cartItems.value.filter((i) => i.cartId !== item.cartId);
    ElMessage.success('已删除');
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || '删除失败');
  }
}

function onToggleSelect(cartId, val) {
  const item = cartItems.value.find((i) => i.cartId === cartId);
  if (item) item.selected = val;
}

function onToggleAll(val) {
  cartItems.value.forEach((i) => (i.selected = val));
}

function onCheckout() {
  const ids = selectedItems.value.map((i) => i.cartId);
  router.push({ name: 'Checkout', query: { cartItemIds: ids.join(',') } });
}

function goHome() {
  router.push({ name: 'Home' });
}

// --- lifecycle ---
onMounted(() => {
  fetchCartList();
});
</script>

<style scoped>
/* ========== 暖橙色主题变量 ========== */
.cart-page {
  --cart-primary: #f97316;
  --cart-primary-light: #fff7ed;
  --cart-primary-dark: #ea580c;
  --cart-accent: #fbbf24;

  min-height: 100vh;
  background: #f5f5f7;
  padding-bottom: 90px;
}

/* ========== 头部 ========== */
.cart-header {
  background: linear-gradient(135deg, #f97316, #fb923c);
  padding: var(--app-space-xl, 24px) var(--app-space-base, 16px);
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
}

.page-title {
  font-size: var(--app-font-3xl, 1.5rem);
  font-weight: 700;
  color: #fff;
  margin: 0;
  letter-spacing: 0.5px;
}

/* ========== 通用状态容器 ========== */
.state-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--app-space-xl, 24px) var(--app-space-base, 16px);
}

.state-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px var(--app-space-xl, 24px);
  background: #fff;
  border-radius: var(--app-radius-md, 12px);
  box-shadow: var(--app-shadow-level-1, 0 1px 3px rgba(0,0,0,0.06));
}

.state-text {
  font-size: var(--app-font-lg, 1rem);
  color: var(--app-text-primary, #1a1a2e);
  margin: var(--app-space-base, 16px) 0 var(--app-space-sm, 8px);
  font-weight: 500;
}

.state-hint {
  font-size: var(--app-font-sm, 0.8125rem);
  color: var(--app-text-secondary, #6b7280);
  margin: 0 0 var(--app-space-lg, 20px);
}

.state-box .el-button--primary {
  background: var(--cart-primary);
  border-color: var(--cart-primary);
}

.state-box .el-button--primary:hover {
  background: var(--cart-primary-dark);
  border-color: var(--cart-primary-dark);
}

/* ========== 购物车列表 ========== */
.cart-list {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--app-space-base, 16px);
  display: flex;
  flex-direction: column;
  gap: var(--app-space-sm, 8px);
}

.cart-item {
  display: flex;
  align-items: center;
  gap: var(--app-space-md, 12px);
  padding: var(--app-space-md, 12px);
  background: #fff;
  border-radius: var(--app-radius-md, 12px);
  box-shadow: var(--app-shadow-level-1, 0 1px 3px rgba(0,0,0,0.06));
  transition: box-shadow 0.2s var(--app-ease-standard, cubic-bezier(0.4,0,0.2,1));
}

.cart-item:hover {
  box-shadow: var(--app-shadow-level-2, 0 4px 12px rgba(0,0,0,0.08));
}

.item-checkbox {
  flex-shrink: 0;
}

.item-checkbox :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: var(--cart-primary);
  border-color: var(--cart-primary);
}

/* 图片 */
.item-image {
  flex-shrink: 0;
  width: 90px;
  height: 90px;
  border-radius: var(--app-radius-base, 8px);
  overflow: hidden;
  background: #f9fafb;
}

.item-img {
  width: 100%;
  height: 100%;
}

.image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f9fafb;
}

/* 信息区 */
.item-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--app-space-xs, 4px);
}

.item-title {
  font-size: var(--app-font-base, 0.875rem);
  font-weight: 500;
  color: var(--app-text-primary, #1a1a2e);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.4;
}

.item-spec {
  font-size: var(--app-font-xs, 0.75rem);
  color: var(--app-text-secondary, #6b7280);
  margin: 0;
  background: #f3f4f6;
  padding: 2px 8px;
  border-radius: var(--app-radius-sm, 4px);
  display: inline-block;
  align-self: flex-start;
}

.item-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--app-space-xs, 4px);
}

.item-price {
  font-size: var(--app-font-md, 0.9375rem);
  font-weight: 700;
  color: var(--cart-primary);
}

/* 数量控制 */
.quantity-control {
  display: flex;
  align-items: center;
  gap: 2px;
}

.qty-btn {
  width: 28px;
  height: 28px;
  min-width: 28px;
  padding: 0;
  border: 1px solid var(--app-border-light, #e5e7eb);
  background: #fff;
  color: var(--app-text-regular, #374151);
  font-size: var(--app-font-xs, 0.75rem);
  transition: all 0.15s var(--app-ease-standard, cubic-bezier(0.4,0,0.2,1));
}

.qty-btn:hover:not(:disabled) {
  border-color: var(--cart-primary);
  color: var(--cart-primary);
}

.qty-btn:disabled {
  color: var(--app-text-disabled, #b0b7c3);
  background: var(--app-bg-disabled, #f3f4f6);
  cursor: not-allowed;
}

.qty-value {
  font-size: var(--app-font-base, 0.875rem);
  font-weight: 600;
  color: var(--app-text-primary, #1a1a2e);
  min-width: 32px;
  text-align: center;
  user-select: none;
}

/* 删除按钮 */
.delete-btn {
  flex-shrink: 0;
  color: var(--app-text-secondary, #6b7280);
  transition: color 0.15s;
}

.delete-btn:hover {
  color: #ef4444;
}

/* ========== 底部结算栏 ========== */
.cart-footer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: #fff;
  border-top: 1px solid var(--app-border-light, #e5e7eb);
  padding: var(--app-space-md, 12px) var(--app-space-base, 16px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  z-index: 10;
  box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.04);
}

.footer-left {
  flex-shrink: 0;
}

.footer-left :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: var(--cart-primary);
  border-color: var(--cart-primary);
}

.footer-left :deep(.el-checkbox__input.is-indeterminate .el-checkbox__inner) {
  background-color: var(--cart-primary);
  border-color: var(--cart-primary);
}

.footer-right {
  display: flex;
  align-items: center;
  gap: var(--app-space-md, 12px);
}

.total-info {
  display: flex;
  align-items: baseline;
  gap: 2px;
}

.total-label {
  font-size: var(--app-font-sm, 0.8125rem);
  color: var(--app-text-secondary, #6b7280);
}

.total-price {
  font-size: var(--app-font-xl, 1.125rem);
  font-weight: 700;
  color: var(--cart-primary);
}

.checkout-btn {
  background: linear-gradient(135deg, #f97316, #fb923c) !important;
  border: none !important;
  font-weight: 600;
  letter-spacing: 0.5px;
  box-shadow: 0 2px 8px rgba(249, 115, 22, 0.35);
  transition: box-shadow 0.2s var(--app-ease-standard, cubic-bezier(0.4,0,0.2,1)), transform 0.15s var(--app-ease-standard, cubic-bezier(0.4,0,0.2,1));
}

.checkout-btn:hover:not(:disabled) {
  box-shadow: 0 4px 16px rgba(249, 115, 22, 0.45);
  transform: translateY(-1px);
}

.checkout-btn:active:not(:disabled) {
  transform: translateY(0);
}

.checkout-btn:disabled {
  background: var(--app-bg-disabled, #f3f4f6) !important;
  color: var(--app-text-disabled, #b0b7c3) !important;
  box-shadow: none;
}

/* ========== 响应式 ========== */
@media (max-width: 768px) {
  .cart-item {
    padding: var(--app-space-sm, 8px);
    gap: var(--app-space-sm, 8px);
  }

  .item-image {
    width: 72px;
    height: 72px;
  }

  .item-title {
    font-size: var(--app-font-sm, 0.8125rem);
  }

  .item-price {
    font-size: var(--app-font-base, 0.875rem);
  }

  .cart-footer {
    padding: var(--app-space-sm, 8px) var(--app-space-md, 12px);
  }

  .total-price {
    font-size: var(--app-font-lg, 1rem);
  }

  .checkout-btn {
    font-size: var(--app-font-sm, 0.8125rem);
    padding: 10px 18px;
  }
}
</style>
