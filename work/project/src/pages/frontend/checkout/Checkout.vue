<template>
  <div class="page-container checkout-page">
    <div class="page-content">
      <!-- 面包屑 -->
      <div class="breadcrumb">
        <span class="breadcrumb-link" @click="router.push('/cart')">购物车</span>
        <el-icon class="breadcrumb-sep"><ArrowRight /></el-icon>
        <span class="breadcrumb-current">确认订单</span>
      </div>

      <!-- 全局错误 -->
      <el-alert
        v-if="pageError"
        :title="pageError"
        type="error"
        show-icon
        :closable="false"
        style="margin-bottom: 20px"
      >
        <template #default>
          <el-button type="primary" link @click="initPage">重试</el-button>
        </template>
      </el-alert>

      <template v-if="!pageError">
        <!-- 地址区域 -->
        <div class="checkout-section">
          <div class="section-header">
            <h3 class="section-title">
              <el-icon class="section-icon"><LocationFilled /></el-icon>
              收货地址
            </h3>
            <el-button type="primary" link @click="openAddressDialog(null)">
              <el-icon><Plus /></el-icon>
              新增地址
            </el-button>
          </div>

          <div v-if="addressLoading" class="section-loading">
            <el-skeleton :rows="2" animated />
          </div>

          <div v-else-if="addresses.length === 0" class="section-empty">
            <el-empty description="暂无收货地址，请先添加" :image-size="80">
              <el-button type="primary" @click="openAddressDialog(null)">添加地址</el-button>
            </el-empty>
          </div>

          <div v-else class="address-list">
            <div
              v-for="addr in addresses"
              :key="addr.id"
              class="address-card"
              :class="{ active: selectedAddressId === addr.id }"
              @click="selectAddress(addr)"
            >
              <div class="address-body">
                <div class="address-contact">
                  <span class="address-name">{{ addr.name }}</span>
                  <span class="address-phone">{{ addr.phone }}</span>
                  <el-tag v-if="addr.isDefault" size="small" type="warning" effect="light" round>
                    默认
                  </el-tag>
                </div>
                <div class="address-detail">
                  {{ addr.province }}{{ addr.city }}{{ addr.district }} {{ addr.detail }}
                </div>
              </div>
              <div class="address-actions">
                <el-button type="primary" link size="small" @click.stop="openAddressDialog(addr)">
                  编辑
                </el-button>
                <div v-if="selectedAddressId === addr.id" class="address-check">
                  <el-icon :size="20"><CircleCheckFilled /></el-icon>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 商品清单 -->
        <div class="checkout-section">
          <div class="section-header">
            <h3 class="section-title">
              <el-icon class="section-icon"><GoodsFilled /></el-icon>
              商品清单
            </h3>
            <span class="section-count">共 {{ orderItems.length }} 件</span>
          </div>

          <div v-if="itemsLoading" class="section-loading">
            <el-skeleton :rows="3" animated />
          </div>

          <div v-else class="order-items">
            <div
              v-for="item in orderItems"
              :key="item.id"
              class="order-item"
            >
              <div class="item-image">
                <el-image
                  :src="item.image"
                  fit="cover"
                  style="width: 80px; height: 80px; border-radius: 8px"
                >
                  <template #error>
                    <div class="image-placeholder">
                      <el-icon :size="28"><PictureFilled /></el-icon>
                    </div>
                  </template>
                </el-image>
              </div>
              <div class="item-info">
                <div class="item-title">{{ item.title }}</div>
                <div class="item-spec" v-if="item.specCombo">{{ item.specCombo }}</div>
                <div class="item-price-row">
                  <span class="item-price">¥{{ parseFloat(item.price).toFixed(2) }}</span>
                  <span class="item-quantity">× {{ item.quantity }}</span>
                </div>
              </div>
              <div class="item-subtotal">
                ¥{{ (parseFloat(item.price) * item.quantity).toFixed(2) }}
              </div>
            </div>
          </div>
        </div>

        <!-- 支付方式 -->
        <div class="checkout-section">
          <div class="section-header">
            <h3 class="section-title">
              <el-icon class="section-icon"><WalletFilled /></el-icon>
              支付方式
            </h3>
          </div>
          <div class="pay-methods">
            <div
              class="pay-method-card"
              :class="{ active: payChannel === 'wxpay' }"
              @click="payChannel = 'wxpay'"
            >
              <span class="pay-icon pay-icon-wx">微信</span>
              <span>微信支付</span>
            </div>
            <div
              class="pay-method-card"
              :class="{ active: payChannel === 'alipay' }"
              @click="payChannel = 'alipay'"
            >
              <span class="pay-icon pay-icon-ali">支</span>
              <span>支付宝</span>
            </div>
          </div>
        </div>

        <!-- 优惠券 -->
        <div class="checkout-section">
          <div class="section-header">
            <h3 class="section-title">
              <el-icon class="section-icon"><TicketFilled /></el-icon>
              优惠券
            </h3>
          </div>

          <div v-if="couponLoading" class="section-loading">
            <el-skeleton :rows="1" animated />
          </div>

          <div v-else-if="availableCoupons.length === 0" class="section-empty-text">
            暂无可用优惠券
          </div>

          <div v-else class="coupon-list">
            <div
              v-for="coupon in availableCoupons"
              :key="coupon.id"
              class="coupon-card"
              :class="{ active: selectedCouponId === coupon.id }"
              @click="toggleCoupon(coupon)"
            >
              <div class="coupon-left">
                <div class="coupon-amount">
                  <span class="coupon-currency">¥</span>
                  {{ parseFloat(coupon.amount).toFixed(0) }}
                </div>
                <div class="coupon-condition">满{{ parseFloat(coupon.minOrder).toFixed(0) }}可用</div>
              </div>
              <div class="coupon-divider"></div>
              <div class="coupon-right">
                <div class="coupon-title">{{ coupon.title }}</div>
              </div>
              <div v-if="selectedCouponId === coupon.id" class="coupon-check">
                <el-icon :size="18"><CircleCheckFilled /></el-icon>
              </div>
            </div>
          </div>
        </div>

        <!-- 金额汇总 -->
        <div class="checkout-section amount-summary">
          <div class="amount-row">
            <span class="amount-label">商品总价</span>
            <span class="amount-value">¥{{ totalAmount.toFixed(2) }}</span>
          </div>
          <div v-if="discountAmount > 0" class="amount-row amount-discount">
            <span class="amount-label">优惠券抵扣</span>
            <span class="amount-value discount">-¥{{ discountAmount.toFixed(2) }}</span>
          </div>
          <el-divider style="margin: 12px 0" />
          <div class="amount-row amount-total">
            <span class="amount-label">实付金额</span>
            <span class="amount-value total">¥{{ payAmount.toFixed(2) }}</span>
          </div>
        </div>

        <!-- 提交 -->
        <div class="checkout-footer">
          <el-button size="large" @click="router.back">返回购物车</el-button>
          <el-button
            type="primary"
            size="large"
            :loading="submitting"
            :disabled="!canSubmit"
            class="submit-btn"
            @click="submitOrder"
          >
            <template v-if="!submitting">提交订单 ¥{{ payAmount.toFixed(2) }}</template>
            <template v-else>提交中…</template>
          </el-button>
        </div>
      </template>
    </div>

    <!-- 地址弹窗 -->
    <el-dialog
      v-model="showAddressDialog"
      :title="editingAddress ? '编辑地址' : '新增收货地址'"
      width="500px"
      destroy-on-close
      :close-on-click-modal="false"
    >
      <el-form
        ref="addressFormRef"
        :model="addressForm"
        :rules="addressRules"
        label-width="80px"
        label-position="left"
        size="default"
      >
        <el-form-item label="收货人" prop="name">
          <el-input v-model="addressForm.name" placeholder="请输入收货人姓名" maxlength="20" show-word-limit />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="addressForm.phone" placeholder="请输入手机号" maxlength="11" />
        </el-form-item>
        <el-form-item label="所在地区" required>
          <div class="region-row">
            <el-form-item prop="province" class="region-item">
              <el-input v-model="addressForm.province" placeholder="省" maxlength="20" />
            </el-form-item>
            <el-form-item prop="city" class="region-item">
              <el-input v-model="addressForm.city" placeholder="市" maxlength="20" />
            </el-form-item>
            <el-form-item prop="district" class="region-item">
              <el-input v-model="addressForm.district" placeholder="区" maxlength="20" />
            </el-form-item>
          </div>
        </el-form-item>
        <el-form-item label="详细地址" prop="detail">
          <el-input v-model="addressForm.detail" placeholder="街道、门牌号等" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="默认地址">
          <el-switch v-model="addressForm.isDefault" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddressDialog = false">取消</el-button>
        <el-button type="primary" :loading="addressSaving" @click="saveAddress">
          {{ editingAddress ? '保存修改' : '添加地址' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  ArrowRight, Plus, LocationFilled, GoodsFilled, WalletFilled, TicketFilled,
  CircleCheckFilled, PictureFilled
} from '@element-plus/icons-vue';
import { getAddresses, createAddress, updateAddress } from '@/api/user';
import { createOrder } from '@/api/order';
import { getMyCoupons } from '@/api/coupon';
import { useCartStore } from '@/stores/cart';

// ── 路由 ──
const router = useRouter();
const route = useRoute();

// ── 购物车 Store ──
const cartStore = useCartStore();

// ── 选中商品ID（从路由 query 解析） ──
const cartItemIdsRaw = route.query.cartItemIds;
const selectedCartItemIds = cartItemIdsRaw
  ? String(cartItemIdsRaw).split(',').map(Number).filter(id => !isNaN(id))
  : [];

// ── 页面级状态 ──
const pageError = ref('');
const itemsLoading = ref(false);
const addressLoading = ref(false);
const couponLoading = ref(false);
const submitting = ref(false);

// ── 地址 ──
const addresses = ref([]);
const selectedAddressId = ref(null);

// ── 订单商品 ──
const orderItems = ref([]);

// ── 支付方式 ──
const payChannel = ref('wxpay');

// ── 优惠券 ──
const availableCoupons = ref([]);
const selectedCouponId = ref(null);

// ── 地址弹窗 ──
const showAddressDialog = ref(false);
const editingAddress = ref(null);
const addressSaving = ref(false);
const addressFormRef = ref(null);

const emptyAddressForm = () => ({
  name: '',
  phone: '',
  province: '',
  city: '',
  district: '',
  detail: '',
  isDefault: false
});

const addressForm = reactive(emptyAddressForm());

const addressRules = {
  name: [
    { required: true, message: '请输入收货人姓名', trigger: 'blur' },
    { min: 2, max: 20, message: '姓名长度 2-20 个字符', trigger: 'blur' }
  ],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确', trigger: 'blur' }
  ],
  province: [{ required: true, message: '请输入省份', trigger: 'blur' }],
  city: [{ required: true, message: '请输入城市', trigger: 'blur' }],
  district: [{ required: true, message: '请输入区/县', trigger: 'blur' }],
  detail: [
    { required: true, message: '请输入详细地址', trigger: 'blur' },
    { min: 2, max: 100, message: '详细地址长度 2-100 个字符', trigger: 'blur' }
  ]
};

// ── 计算属性 ──
const totalAmount = computed(() => {
  return orderItems.value.reduce((sum, item) => {
    return sum + parseFloat(item.price) * item.quantity;
  }, 0);
});

const selectedCoupon = computed(() => {
  if (!selectedCouponId.value) return null;
  return availableCoupons.value.find(c => c.id === selectedCouponId.value) || null;
});

const discountAmount = computed(() => {
  const coupon = selectedCoupon.value;
  if (!coupon) return 0;
  const amount = parseFloat(coupon.amount);
  return Math.min(amount, totalAmount.value);
});

const payAmount = computed(() => {
  return Math.max(0, totalAmount.value - discountAmount.value);
});

const canSubmit = computed(() => {
  return (
    selectedAddressId.value !== null &&
    orderItems.value.length > 0 &&
    !submitting.value
  );
});

// ── 加载数据 ──
async function loadCartItems() {
  if (selectedCartItemIds.length === 0) {
    pageError.value = '未选择结算商品，请返回购物车重新选择';
    return;
  }
  itemsLoading.value = true;
  try {
    // 确保购物车数据已加载
    if (!cartStore.items || cartStore.items.length === 0) {
      await cartStore.fetchItems?.();
    }
    // 筛选选中的商品
    const cartItems = cartStore.items || [];
    const idSet = new Set(selectedCartItemIds);
    orderItems.value = cartItems.filter(item => idSet.has(item.id));

    if (orderItems.value.length === 0) {
      pageError.value = '所选商品已失效，请返回购物车重新选择';
    }
  } catch (e) {
    pageError.value = '加载商品信息失败';
  } finally {
    itemsLoading.value = false;
  }
}

async function loadAddresses() {
  addressLoading.value = true;
  try {
    const res = await getAddresses();
    // res 可能是数组或 { data: [...] } 取决于拦截器处理
    addresses.value = Array.isArray(res) ? res : (res.data || []);
    // 默认选中默认地址或第一个
    if (addresses.value.length > 0) {
      const defaultAddr = addresses.value.find(a => a.isDefault);
      selectedAddressId.value = defaultAddr ? defaultAddr.id : addresses.value[0].id;
    }
  } catch (e) {
    // 地址加载失败不阻塞页面
    addresses.value = [];
  } finally {
    addressLoading.value = false;
  }
}

async function loadCoupons() {
  couponLoading.value = true;
  try {
    const res = await getMyCoupons({ orderAmount: totalAmount.value });
    const data = Array.isArray(res) ? res : (res.data || []);
    const list = Array.isArray(data) ? data : (data.list || []);
    // 只展示满足最低消费的券
    availableCoupons.value = list.filter(c => totalAmount.value >= parseFloat(c.minOrder));
  } catch (e) {
    availableCoupons.value = [];
  } finally {
    couponLoading.value = false;
  }
}

async function initPage() {
  if (selectedCartItemIds.length === 0) {
    pageError.value = '未选择结算商品，请返回购物车重新选择';
    return;
  }
  pageError.value = '';
  await Promise.all([
    loadCartItems(),
    loadAddresses()
  ]);
  // 总金额确定后再加载优惠券
  if (!pageError.value) {
    await loadCoupons();
  }
}

// ── 地址操作 ──
function selectAddress(addr) {
  selectedAddressId.value = addr.id;
}

function openAddressDialog(addr) {
  if (addr) {
    editingAddress.value = addr;
    Object.assign(addressForm, {
      name: addr.name,
      phone: addr.phone,
      province: addr.province,
      city: addr.city,
      district: addr.district,
      detail: addr.detail,
      isDefault: !!addr.isDefault
    });
  } else {
    editingAddress.value = null;
    Object.assign(addressForm, emptyAddressForm());
  }
  showAddressDialog.value = true;
}

async function saveAddress() {
  const valid = await addressFormRef.value?.validate().catch(() => false);
  if (!valid) return;

  addressSaving.value = true;
  try {
    const payload = {
      name: addressForm.name,
      phone: addressForm.phone,
      province: addressForm.province,
      city: addressForm.city,
      district: addressForm.district,
      detail: addressForm.detail,
      isDefault: addressForm.isDefault
    };

    if (editingAddress.value) {
      await updateAddress(editingAddress.value.id, payload);
      ElMessage.success('地址修改成功');
    } else {
      await createAddress(payload);
      ElMessage.success('地址添加成功');
    }

    showAddressDialog.value = false;
    await loadAddresses();
  } catch (e) {
    ElMessage.error(editingAddress.value ? '地址修改失败' : '地址添加失败');
  } finally {
    addressSaving.value = false;
  }
}

// ── 优惠券操作 ──
function toggleCoupon(coupon) {
  if (totalAmount.value < parseFloat(coupon.minOrder)) {
    ElMessage.warning(`该优惠券需满 ¥${parseFloat(coupon.minOrder).toFixed(0)} 才能使用`);
    return;
  }
  if (selectedCouponId.value === coupon.id) {
    selectedCouponId.value = null;
  } else {
    selectedCouponId.value = coupon.id;
  }
}

// ── 提交订单 ──
async function submitOrder() {
  if (!canSubmit.value) return;

  try {
    await ElMessageBox.confirm(
      `实付金额 ¥${payAmount.value.toFixed(2)}，确认提交订单？`,
      '确认下单',
      {
        confirmButtonText: '确认支付',
        cancelButtonText: '再想想',
        type: 'warning'
      }
    );
  } catch {
    return;
  }

  submitting.value = true;
  try {
    const payload = {
      addressId: selectedAddressId.value,
      cartItemIds: selectedCartItemIds,
      payChannel: payChannel.value
    };
    if (selectedCouponId.value) {
      payload.couponId = selectedCouponId.value;
    }

    const res = await createOrder(payload);
    const result = res.data ?? res;

    // 从购物车中移除已下单商品
    try {
      await cartStore.removeItems?.(selectedCartItemIds);
    } catch {
      // 静默失败，不影响主流程
    }

    ElMessage.success('下单成功，正在跳转支付…');

    // 跳转支付页：params 传 orderId，query 传 paymentId
    router.push({
      name: 'Payment',
      params: { orderId: result.orderId },
      query: { paymentId: result.paymentId }
    });
  } catch (e) {
    const msg = e?.response?.data?.message || e?.message || '下单失败，请重试';
    ElMessage.error(msg);
  } finally {
    submitting.value = false;
  }
}

// ── 监听总金额变化，重新加载可用券 ──
watch(totalAmount, (newVal) => {
  if (newVal > 0 && !pageError.value) {
    loadCoupons();
  }
}, { immediate: false });

// ── 生命周期 ──
onMounted(() => {
  initPage();
});
</script>

<style scoped>
/* ── 页面容器 ── */
.checkout-page {
  background: var(--app-bg-page);
  min-height: 100vh;
  padding-bottom: 100px;
}

.page-content {
  max-width: 860px;
  margin: 0 auto;
  padding: var(--app-space-xl) var(--app-space-base);
}

/* ── 面包屑 ── */
.breadcrumb {
  display: flex;
  align-items: center;
  gap: var(--app-space-sm);
  margin-bottom: var(--app-space-lg);
  font-size: var(--app-font-sm);
  color: var(--app-text-secondary);
}

.breadcrumb-link {
  cursor: pointer;
  color: var(--app-text-secondary);
  transition: color 0.15s var(--app-ease-standard);
}

.breadcrumb-link:hover {
  color: var(--app-color-primary);
}

.breadcrumb-sep {
  font-size: var(--app-font-xs);
}

.breadcrumb-current {
  color: var(--app-text-primary);
  font-weight: var(--font-weight-medium, 500);
}

/* ── 区块卡片 ── */
.checkout-section {
  background: var(--app-bg-container);
  border-radius: var(--app-radius-md);
  padding: var(--app-space-xl);
  margin-bottom: var(--app-space-base);
  box-shadow: var(--app-shadow-level-1);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--app-space-base);
}

.section-title {
  display: flex;
  align-items: center;
  gap: var(--app-space-sm);
  margin: 0;
  font-size: var(--app-font-lg);
  font-weight: var(--font-weight-semibold, 600);
  color: var(--app-text-primary);
}

.section-icon {
  color: #f59e0b;
}

.section-count {
  font-size: var(--app-font-sm);
  color: var(--app-text-secondary);
}

.section-loading {
  padding: var(--app-space-base) 0;
}

.section-empty {
  padding: var(--app-space-xl) 0;
}

.section-empty-text {
  padding: var(--app-space-base) 0;
  text-align: center;
  font-size: var(--app-font-sm);
  color: var(--app-text-secondary);
}

/* ── 地址卡片 ── */
.address-list {
  display: flex;
  flex-direction: column;
  gap: var(--app-space-sm);
}

.address-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--app-space-md) var(--app-space-base);
  border: 2px solid var(--app-border-light);
  border-radius: var(--app-radius-base);
  cursor: pointer;
  transition: all 0.2s var(--app-ease-standard);
}

.address-card:hover {
  border-color: #fbbf24;
  background: #fffbeb;
}

.address-card.active {
  border-color: #f59e0b;
  background: #fffbeb;
}

.address-body {
  flex: 1;
  min-width: 0;
}

.address-contact {
  display: flex;
  align-items: center;
  gap: var(--app-space-sm);
  margin-bottom: 4px;
}

.address-name {
  font-size: var(--app-font-base);
  font-weight: var(--font-weight-medium, 500);
  color: var(--app-text-primary);
}

.address-phone {
  font-size: var(--app-font-sm);
  color: var(--app-text-secondary);
}

.address-detail {
  font-size: var(--app-font-sm);
  color: var(--app-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.address-actions {
  display: flex;
  align-items: center;
  gap: var(--app-space-sm);
  flex-shrink: 0;
  margin-left: var(--app-space-base);
}

.address-check {
  color: #f59e0b;
  display: flex;
  align-items: center;
}

/* ── 商品清单 ── */
.order-items {
  display: flex;
  flex-direction: column;
  gap: var(--app-space-md);
}

.order-item {
  display: flex;
  align-items: center;
  gap: var(--app-space-md);
  padding: var(--app-space-md);
  background: var(--app-bg-hover);
  border-radius: var(--app-radius-base);
}

.item-image {
  flex-shrink: 0;
}

.image-placeholder {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--app-bg-disabled);
  border-radius: 8px;
  color: var(--app-text-disabled);
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-title {
  font-size: var(--app-font-base);
  font-weight: var(--font-weight-medium, 500);
  color: var(--app-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 4px;
}

.item-spec {
  font-size: var(--app-font-xs);
  color: var(--app-text-secondary);
  margin-bottom: 6px;
}

.item-price-row {
  display: flex;
  align-items: baseline;
  gap: var(--app-space-sm);
}

.item-price {
  font-size: var(--app-font-sm);
  color: #f59e0b;
  font-weight: var(--font-weight-semibold, 600);
}

.item-quantity {
  font-size: var(--app-font-xs);
  color: var(--app-text-secondary);
}

.item-subtotal {
  font-size: var(--app-font-base);
  font-weight: var(--font-weight-semibold, 600);
  color: var(--app-text-primary);
  flex-shrink: 0;
}

/* ── 支付方式 ── */
.pay-methods {
  display: flex;
  gap: var(--app-space-md);
}

.pay-method-card {
  display: flex;
  align-items: center;
  gap: var(--app-space-sm);
  padding: var(--app-space-md) var(--app-space-lg);
  border: 2px solid var(--app-border-light);
  border-radius: var(--app-radius-base);
  cursor: pointer;
  font-size: var(--app-font-base);
  color: var(--app-text-regular);
  transition: all 0.2s var(--app-ease-standard);
  user-select: none;
}

.pay-method-card:hover {
  border-color: #fbbf24;
}

.pay-method-card.active {
  border-color: #f59e0b;
  background: #fffbeb;
  color: #d97706;
}

.pay-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  font-size: var(--app-font-xs);
  font-weight: var(--font-weight-bold, 700);
  color: #fff;
}

.pay-icon-wx {
  background: #07c160;
}

.pay-icon-ali {
  background: #1677ff;
}

/* ── 优惠券 ── */
.coupon-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--app-space-md);
}

.coupon-card {
  display: flex;
  align-items: stretch;
  border: 2px solid var(--app-border-light);
  border-radius: var(--app-radius-base);
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s var(--app-ease-standard);
  position: relative;
  min-width: 200px;
  background: #fff;
}

.coupon-card:hover {
  border-color: #fbbf24;
  box-shadow: var(--app-shadow-level-1);
}

.coupon-card.active {
  border-color: #f59e0b;
  background: #fffbeb;
}

.coupon-left {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 90px;
  padding: var(--app-space-md);
  background: linear-gradient(135deg, #fef3c7, #fde68a);
  flex-shrink: 0;
}

.coupon-card.active .coupon-left {
  background: linear-gradient(135deg, #fde68a, #fbbf24);
}

.coupon-amount {
  font-size: 28px;
  font-weight: var(--font-weight-bold, 700);
  color: #d97706;
  line-height: 1;
}

.coupon-currency {
  font-size: 16px;
}

.coupon-condition {
  font-size: var(--app-font-xs);
  color: #92400e;
  margin-top: 4px;
}

.coupon-divider {
  width: 1px;
  background: repeating-linear-gradient(
    to bottom,
    var(--app-border-light) 0px,
    var(--app-border-light) 4px,
    transparent 4px,
    transparent 8px
  );
}

.coupon-right {
  display: flex;
  align-items: center;
  padding: var(--app-space-md) var(--app-space-base);
  flex: 1;
  min-width: 0;
}

.coupon-title {
  font-size: var(--app-font-sm);
  color: var(--app-text-regular);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.coupon-check {
  position: absolute;
  top: 6px;
  right: 6px;
  color: #f59e0b;
}

/* ── 金额汇总 ── */
.amount-summary {
  padding: var(--app-space-lg) var(--app-space-xl);
}

.amount-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}

.amount-label {
  font-size: var(--app-font-base);
  color: var(--app-text-secondary);
}

.amount-value {
  font-size: var(--app-font-base);
  color: var(--app-text-primary);
  font-weight: var(--font-weight-medium, 500);
}

.amount-discount .amount-label {
  color: #d97706;
}

.amount-value.discount {
  color: #d97706;
  font-weight: var(--font-weight-semibold, 600);
}

.amount-total {
  padding-top: 4px;
}

.amount-total .amount-label {
  font-size: var(--app-font-md);
  font-weight: var(--font-weight-semibold, 600);
  color: var(--app-text-primary);
}

.amount-value.total {
  font-size: var(--app-font-3xl);
  font-weight: var(--font-weight-bold, 700);
  color: #d97706;
}

/* ── 提交按钮 ── */
.checkout-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--app-space-md);
  padding-top: var(--app-space-base);
}

.submit-btn {
  min-width: 200px;
  --el-color-primary: #f59e0b;
  --el-color-primary-light-3: #fbbf24;
  --el-color-primary-dark-2: #d97706;
  background: linear-gradient(135deg, #f59e0b, #d97706);
  border-color: #d97706;
  font-weight: var(--font-weight-semibold, 600);
  font-size: var(--app-font-lg);
  height: 48px;
  letter-spacing: 0.5px;
  transition: all 0.2s var(--app-ease-standard);
}

.submit-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  border-color: #f59e0b;
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(245, 158, 11, 0.35);
}

.submit-btn:active:not(:disabled) {
  transform: translateY(0);
}

.submit-btn:disabled {
  background: var(--app-bg-disabled);
  border-color: var(--app-border-base);
  color: var(--app-text-disabled);
}

/* ── 地址表单 ── */
.region-row {
  display: flex;
  gap: var(--app-space-sm);
  width: 100%;
}

.region-item {
  flex: 1;
  margin-bottom: 0;
}

.region-item :deep(.el-form-item__content) {
  margin-left: 0 !important;
}

/* ── 响应式 ── */
@media (max-width: 768px) {
  .page-content {
    padding: var(--app-space-base);
  }

  .checkout-section {
    padding: var(--app-space-base);
    border-radius: var(--app-radius-base);
  }

  .checkout-footer {
    flex-direction: column-reverse;
    gap: var(--app-space-sm);
  }

  .submit-btn {
    width: 100%;
  }

  .coupon-list {
    flex-direction: column;
  }

  .coupon-card {
    min-width: auto;
  }

  .pay-methods {
    flex-direction: column;
  }

  .region-row {
    flex-direction: column;
    gap: 0;
  }

  .item-subtotal {
    font-size: var(--app-font-sm);
  }
}
</style>
