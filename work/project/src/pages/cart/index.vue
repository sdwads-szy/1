<template>
  <div class="cart-page">
    <!-- 页头 -->
    <div class="cart-header">
      <!-- 来源: ProductDetail -->
      <el-button class="back-btn-cart" text @click="router.back()">← 返回</el-button>
      <h1>购物车</h1>
      <span v-if="!loading && cartItems.length" class="cart-header-count">
        共 {{ cartItems.length }} 件商品
      </span>
    </div>

    <!-- 失效商品警告 -->
    <el-alert
      v-if="unavailableWarnings.length"
      type="warning"
      :closable="true"
      @close="unavailableWarnings = []"
      class="cart-warning"
      show-icon
    >
      <template #title>
        以下商品已失效：{{ unavailableWarnings.join('、') }}
      </template>
    </el-alert>

    <!-- 加载态 — 骨架屏 -->
    <div v-if="loading" class="cart-skeleton">
      <div v-for="i in 3" :key="i" class="skeleton-shop">
        <el-skeleton animated class="skeleton-shop-header">
          <template #template>
            <div style="display:flex;align-items:center;gap:8px;padding:12px 0;">
              <el-skeleton-item variant="rect" style="width:18px;height:18px" />
              <el-skeleton-item variant="text" style="width:140px" />
            </div>
          </template>
        </el-skeleton>
        <div v-for="j in 2" :key="j" class="skeleton-row">
          <el-skeleton animated>
            <template #template>
              <div style="display:flex;align-items:center;gap:16px;padding:10px 0;">
                <el-skeleton-item variant="rect" style="width:18px;height:18px" />
                <el-skeleton-item variant="image" style="width:64px;height:64px" />
                <div style="flex:1">
                  <el-skeleton-item variant="text" style="width:60%;margin-bottom:6px" />
                  <el-skeleton-item variant="text" style="width:30%" />
                </div>
                <el-skeleton-item variant="text" style="width:60px" />
                <el-skeleton-item variant="rect" style="width:100px;height:28px" />
                <el-skeleton-item variant="text" style="width:70px" />
                <el-skeleton-item variant="text" style="width:40px" />
              </div>
            </template>
          </el-skeleton>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!cartItems.length" class="cart-empty">
      <el-icon :size="64" color="var(--color-text-tertiary)">
        <svg viewBox="0 0 64 64" fill="none">
          <rect x="12" y="20" width="40" height="36" rx="4" stroke="currentColor" stroke-width="2.5" />
          <path d="M20 20V16a12 12 0 0 1 24 0v4" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" />
          <line x1="22" y1="30" x2="28" y2="30" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
          <line x1="34" y1="30" x2="42" y2="30" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
          <line x1="22" y1="38" x2="28" y2="38" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
          <line x1="34" y1="38" x2="42" y2="38" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
        </svg>
      </el-icon>
      <h2>购物车是空的</h2>
      <p>去挑选心仪的商品吧</p>
      <el-button type="primary" @click="router.push('/')">去逛逛</el-button>
    </div>

    <!-- 内容区 -->
    <template v-else>
      <div class="cart-content">
        <div
          v-for="group in groupedItems"
          :key="group.shopId"
          class="cart-shop-group"
        >
          <!-- 店铺头部 -->
          <div class="shop-header">
            <el-checkbox
              :model-value="isShopAllChecked(group.shopId)"
              :indeterminate="isShopIndeterminate(group.shopId)"
              @change="(val) => handleShopCheck(group, val)"
            />
            <span class="shop-name">{{ group.shopName }}</span>
          </div>

          <!-- 商品行 -->
          <div class="shop-items">
            <div
              v-for="item in group.items"
              :key="item.id"
              class="cart-item"
            >
              <el-checkbox
                :model-value="item.checked"
                @change="() => handleItemCheck(item)"
              />

              <img
                :src="item.image"
                :alt="item.spuName"
                class="item-image"
                @error="(e) => e.target.src = 'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 64 64%22><rect fill=%22%23f0f0f0%22 width=%2264%22 height=%2264%22/><text x=%2232%22 y=%2236%22 text-anchor=%22middle%22 fill=%22%23ccc%22 font-size=%2210%22>无图</text></svg>'"
              />

              <div class="item-info">
                <p class="item-name">{{ item.spuName }}</p>
                <p class="item-spec">{{ item.specName }}</p>
                <span v-if="item.stock !== undefined && item.stock < 20" class="item-stock-warn">
                  仅剩 {{ item.stock }} 件
                </span>
              </div>

              <span class="item-price">¥{{ item.price }}</span>

              <div class="item-quantity">
                <el-input-number
                  :model-value="item.quantity"
                  :min="1"
                  :max="item.stock || 99999"
                  size="small"
                  controls-position="right"
                  @change="(val) => handleQuantityChange(item, val)"
                />
              </div>

              <span class="item-subtotal">
                ¥{{ (parseFloat(item.price) * item.quantity).toFixed(2) }}
              </span>

              <el-button
                type="danger"
                link
                class="item-remove"
                @click="handleRemove(item)"
              >
                删除
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部操作栏 -->
      <div class="cart-bottom">
        <div class="bottom-left">
          <el-checkbox
            v-model="selectAll"
            :indeterminate="selectAllIndeterminate"
            @change="handleSelectAll"
          >
            全选
          </el-checkbox>
        </div>
        <div class="bottom-right">
          <span class="total-label">合计：</span>
          <span class="total-price">¥{{ cartStore.checkedTotal }}</span>
          <el-button
            type="primary"
            size="large"
            :disabled="cartStore.checkedCount === 0"
            @click="goCheckout"
          >
            去结算 ({{ cartStore.checkedCount }})
          </el-button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useCartStore } from '@/stores/cart';

const router = useRouter();
const cartStore = useCartStore();

// ── 状态 ──
const loading = ref(true);
const unavailableWarnings = ref([]);

// ── 计算属性 ──
const cartItems = computed(() => cartStore.cartItems || []);

/** 按店铺分组 */
const groupedItems = computed(() => {
  const map = new Map();
  for (const item of cartItems.value) {
    const key = item.shopId;
    if (!map.has(key)) {
      map.set(key, {
        shopId: item.shopId,
        shopName: item.shopName || ('店铺 ' + item.shopId),
        items: []
      });
    }
    map.get(key).items.push(item);
  }
  return [...map.values()];
});

/** 全选状态 */
const selectAll = computed(() => {
  if (!cartItems.value.length) return false;
  return cartItems.value.every(item => item.checked);
});

const selectAllIndeterminate = computed(() => {
  if (!cartItems.value.length) return false;
  const checkedCount = cartItems.value.filter(item => item.checked).length;
  return checkedCount > 0 && checkedCount < cartItems.value.length;
});

// ── 店铺级勾选辅助 ──
const shopCheckedMap = computed(() => {
  const map = {};
  for (const group of groupedItems.value) {
    const items = group.items;
    const checked = items.filter(i => i.checked).length;
    map[group.shopId] = {
      allChecked: items.length > 0 && checked === items.length,
      indeterminate: checked > 0 && checked < items.length
    };
  }
  return map;
});

function isShopAllChecked(shopId) {
  return shopCheckedMap.value[shopId]?.allChecked || false;
}

function isShopIndeterminate(shopId) {
  return shopCheckedMap.value[shopId]?.indeterminate || false;
}

// ── 操作 ──

/** 单个商品勾选 */
async function handleItemCheck(item) {
  try {
    await cartStore.batchCheck([item.id], !item.checked);
  } catch {
    ElMessage.error('操作失败，请重试');
  }
}

/** 店铺级全选/取消 */
async function handleShopCheck(group, checked) {
  const ids = group.items.map(i => i.id);
  try {
    const res = await cartStore.batchCheck(ids, checked);
    checkUnavailable(res);
  } catch {
    ElMessage.error('操作失败，请重试');
  }
}

/** 全选/取消全选 */
async function handleSelectAll(checked) {
  const ids = cartItems.value.map(i => i.id);
  try {
    const res = await cartStore.batchCheck(ids, checked);
    checkUnavailable(res);
  } catch {
    ElMessage.error('操作失败，请重试');
  }
}

/** 修改数量 */
async function handleQuantityChange(item, val) {
  if (!val || val < 1) return;
  try {
    await cartStore.updateQuantity(item.id, val);
  } catch {
    ElMessage.error('修改数量失败');
  }
}

/** 删除商品 */
async function handleRemove(item) {
  try {
    await ElMessageBox.confirm(
      `确认将「${item.spuName}」从购物车中删除？`,
      '删除商品',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    );
    await cartStore.removeFromCart(item.id);
    ElMessage.success('已删除');
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('删除失败，请重试');
    }
  }
}

/** 去结算 */
function goCheckout() {
  if (cartStore.checkedCount === 0) {
    ElMessage.warning('请先选择要结算的商品');
    return;
  }
  router.push({ name: 'Checkout' });
}

/** 检查 batchCheck 返回的失效商品 */
function checkUnavailable(res) {
  if (!res) return;
  const unavailable = res?.unavailableItems || res?.data?.unavailableItems || [];
  if (unavailable.length) {
    unavailableWarnings.value = unavailable.map(
      u => u.spuName || u.name || '未知商品'
    );
  }
}

// ── 生命周期 ──
onMounted(async () => {
  try {
    await cartStore.fetchCart();
  } catch {
    ElMessage.error('加载购物车失败，请刷新重试');
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.cart-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-lg) var(--space-md);
  min-height: 60vh;
  background: var(--color-bg-page);
}

/* ── 页头 ── */
.cart-header {
  display: flex;
  align-items: baseline;
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
}

.cart-header h1 {
  font-size: var(--font-size-xl);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.cart-header-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

/* ── 警告条 ── */
.cart-warning {
  margin-bottom: var(--space-md);
  border-radius: var(--radius-md);
}

/* ── 骨架屏 ── */
.cart-skeleton {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.skeleton-shop {
  background: var(--color-bg-base);
  border: var(--page-order-card-border, 1px solid var(--color-border));
  border-radius: var(--radius-md);
  padding: 0 var(--space-md);
}

.skeleton-row {
  border-top: 1px solid var(--color-border);
  padding: 0;
}

/* ── 空状态 ── */
.cart-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-3xl) 0;
  background: var(--color-bg-base);
  border-radius: var(--radius-md);
  border: var(--page-order-card-border, 1px solid var(--color-border));
}

.cart-empty h2 {
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
  font-weight: 600;
  margin: var(--space-md) 0 var(--space-sm);
}

.cart-empty p {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-lg);
}

/* ── 店铺分组 ── */
.cart-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.cart-shop-group {
  background: var(--color-bg-base);
  border: var(--page-order-card-border, 1px solid var(--color-border));
  border-radius: var(--radius-md);
  overflow: hidden;
}

.shop-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  background: var(--color-bg-page);
  border-bottom: 1px solid var(--color-border);
  min-height: 44px;
}

.shop-name {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text-primary);
}

/* ── 商品行 ── */
.shop-items {
  display: flex;
  flex-direction: column;
}

.cart-item {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-sm) var(--space-md);
  min-height: var(--page-order-row-height, 56px);
  border-bottom: 1px solid var(--color-border);
  transition: background var(--duration-instant, 75ms) var(--ease-smooth, ease);
}

.cart-item:last-child {
  border-bottom: none;
}

.cart-item:hover {
  background: var(--color-primary-50);
}

.item-image {
  width: 64px;
  height: 64px;
  object-fit: cover;
  border-radius: var(--radius-sm, 10px);
  border: 1px solid var(--color-border);
  flex-shrink: 0;
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-name {
  font-size: var(--font-size-base);
  font-weight: 500;
  color: var(--color-text-primary);
  margin: 0 0 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 280px;
}

.item-spec {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0;
}

.item-stock-warn {
  display: inline-block;
  margin-top: 2px;
  font-size: var(--font-size-xs);
  color: var(--color-warning);
}

.item-price {
  font-size: var(--font-size-base);
  font-weight: 500;
  color: var(--color-text-primary);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  min-width: 70px;
  text-align: right;
}

.item-quantity {
  flex-shrink: 0;
  width: 110px;
}

.item-quantity :deep(.el-input-number) {
  width: 100%;
}

.item-subtotal {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text-primary);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  min-width: 80px;
  text-align: right;
}

.item-remove {
  flex-shrink: 0;
  font-size: var(--font-size-sm);
}

/* ── 底部操作栏 ── */
.cart-bottom {
  position: sticky;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-md) var(--space-lg);
  margin-top: var(--space-md);
  background: var(--color-bg-base);
  border: var(--page-order-card-border, 1px solid var(--color-border));
  border-radius: var(--radius-md);
  box-shadow: 0 -2px 8px rgba(0,0,0,0.04);
  z-index: var(--z-sticky, 100);
}

.bottom-left {
  display: flex;
  align-items: center;
}

.bottom-right {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.total-label {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
}

.total-price {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--color-primary-600);
  font-variant-numeric: tabular-nums;
  min-width: 100px;
  text-align: right;
}

/* ── 响应式 ── */
@media (max-width: 768px) {
  .cart-page {
    padding: var(--space-sm);
  }

  .cart-item {
    flex-wrap: wrap;
    gap: var(--space-sm);
    padding: var(--space-sm);
  }

  .item-image {
    width: 56px;
    height: 56px;
  }

  .item-name {
    max-width: 200px;
  }

  .item-price,
  .item-subtotal {
    min-width: auto;
  }

  .cart-bottom {
    flex-direction: column;
    gap: var(--space-sm);
    padding: var(--space-sm);
  }

  .bottom-right {
    width: 100%;
    justify-content: flex-end;
    flex-wrap: wrap;
  }
}
</style>
