<template>
  <div class="page-container order-detail-page">
    <!-- 顶部导航 -->
    <div class="detail-header">
      <el-button
        link
        class="back-btn"
        @click="$router.back()"
      >
        <el-icon><ArrowLeft /></el-icon>
        <span>返回</span>
      </el-button>
      <h1 class="detail-title">订单详情</h1>
    </div>

    <div v-loading="loading" class="detail-content">
      <template v-if="!loading && order">
        <!-- 订单状态卡片 -->
        <div class="card status-card">
          <div class="status-row">
            <span class="order-no">订单号：{{ order.order_no }}</span>
            <el-tag
              :type="statusMap[order.status]?.type || 'info'"
              size="default"
              class="status-tag"
            >
              {{ statusMap[order.status]?.label || order.status }}
            </el-tag>
          </div>
          <p class="status-hint">{{ statusHint }}</p>
        </div>

        <!-- 收货地址 -->
        <div v-if="order.address" class="card address-card">
          <div class="card-title">
            <el-icon class="card-icon"><LocationFilled /></el-icon>
            <span>收货地址</span>
          </div>
          <div class="address-body">
            <p class="address-contact">{{ order.address.name }} {{ order.address.phone }}</p>
            <p class="address-detail">
              {{ order.address.province }}{{ order.address.city }}{{ order.address.district }}
              {{ order.address.detail }}
            </p>
          </div>
        </div>

        <!-- 商品列表 -->
        <div class="card items-card">
          <div class="card-title">
            <el-icon class="card-icon"><Goods /></el-icon>
            <span>商品信息</span>
          </div>
          <div
            v-for="item in order.items"
            :key="item.id"
            class="item-row"
          >
            <div class="item-image">
              <img
                :src="item.sku_snapshot?.image || placeholderImage"
                :alt="item.sku_snapshot?.title"
              />
            </div>
            <div class="item-info">
              <p class="item-title">{{ item.sku_snapshot?.title || '商品' }}</p>
              <p class="item-spec">{{ item.sku_snapshot?.spec_combo || '' }}</p>
            </div>
            <div class="item-price-qty">
              <span class="item-price">¥{{ parseFloat(item.unit_price).toFixed(2) }}</span>
              <span class="item-qty">×{{ item.quantity }}</span>
            </div>
          </div>
        </div>

        <!-- 金额明细 -->
        <div class="card amount-card">
          <div class="card-title">
            <el-icon class="card-icon"><Money /></el-icon>
            <span>金额明细</span>
          </div>
          <div class="amount-row">
            <span class="amount-label">商品总额</span>
            <span class="amount-value">¥{{ parseFloat(order.total_amount).toFixed(2) }}</span>
          </div>
          <div v-if="parseFloat(order.discount_amount) > 0" class="amount-row discount-row">
            <span class="amount-label">优惠券抵扣</span>
            <span class="amount-value">-¥{{ parseFloat(order.discount_amount).toFixed(2) }}</span>
          </div>
          <div class="amount-row total-row">
            <span class="amount-label">实付金额</span>
            <span class="amount-value total-price">¥{{ parseFloat(order.pay_amount).toFixed(2) }}</span>
          </div>
          <div v-if="order.pay_method" class="amount-row">
            <span class="amount-label">支付方式</span>
            <span class="amount-value">{{ payMethodMap[order.pay_method] || order.pay_method }}</span>
          </div>
        </div>

        <!-- 物流时间线 -->
        <div class="card timeline-card">
          <div class="card-title">
            <el-icon class="card-icon"><Clock /></el-icon>
            <span>订单轨迹</span>
          </div>
          <el-timeline class="order-timeline">
            <el-timeline-item
              v-for="(event, idx) in timelineEvents"
              :key="idx"
              :timestamp="event.time"
              :color="event.active ? '#f97316' : '#d1d5db'"
              :icon="event.active ? undefined : null"
              :hollow="!event.active"
              placement="top"
            >
              <p :class="['timeline-title', { 'timeline-active': event.active }]">
                {{ event.title }}
              </p>
            </el-timeline-item>
          </el-timeline>
        </div>
      </template>

      <!-- 加载失败 -->
      <div v-if="!loading && loadError" class="error-state">
        <el-result
          icon="error"
          title="加载失败"
          :sub-title="loadError"
        >
          <template #extra>
            <el-button type="primary" @click="fetchDetail">重新加载</el-button>
            <el-button @click="$router.back()">返回</el-button>
          </template>
        </el-result>
      </div>
    </div>

    <!-- 底部操作栏 -->
    <div v-if="!loading && order && actionButtons.length > 0" class="action-bar">
      <div class="action-bar-inner">
        <el-button
          v-for="btn in actionButtons"
          :key="btn.key"
          :type="btn.type"
          :plain="btn.plain"
          :disabled="btn.disabled"
          :loading="btn.loading"
          @click="btn.handler"
          class="action-btn"
        >
          {{ btn.label }}
        </el-button>
      </div>
    </div>

    <!-- 取消确认弹窗 -->
    <el-dialog
      v-model="cancelDialogVisible"
      title="取消订单"
      width="400px"
      :close-on-click-modal="false"
      center
    >
      <p class="dialog-text">确定要取消该订单吗？取消后不可恢复。</p>
      <template #footer>
        <el-button @click="cancelDialogVisible = false">再想想</el-button>
        <el-button
          type="primary"
          :loading="cancelling"
          @click="handleCancelOrder"
        >
          确定取消
        </el-button>
      </template>
    </el-dialog>

    <!-- 确认收货弹窗 -->
    <el-dialog
      v-model="receiveDialogVisible"
      title="确认收货"
      width="400px"
      :close-on-click-modal="false"
      center
    >
      <p class="dialog-text">请确认已收到商品，确认后订单将进入完成状态。</p>
      <template #footer>
        <el-button @click="receiveDialogVisible = false">再等等</el-button>
        <el-button
          type="primary"
          :loading="receiving"
          @click="handleReceiveOrder"
        >
          确认收货
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { ArrowLeft, LocationFilled, Goods, Money, Clock } from '@element-plus/icons-vue';
import { getOrderDetail, cancelOrder, receiveOrder } from '@/api/order';

const route = useRoute();
const router = useRouter();

const placeholderImage = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI2YzZjRmNiIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBkb21pbmFudC1iYXNlbGluZT0ibWlkZGxlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmaWxsPSIjOWNhM2FmIiBmb250LXNpemU9IjE0Ij7lm77niYc8L3RleHQ+PC9zdmc+';

/** 状态映射 */
const statusMap = {
  pending_pay: { label: '待付款', type: 'warning' },
  paid: { label: '已支付', type: '' },
  shipped: { label: '已发货', type: '' },
  received: { label: '已收货', type: 'success' },
  completed: { label: '已完成', type: 'success' },
  cancelled: { label: '已取消', type: 'info' },
  refunding: { label: '退款中', type: 'danger' },
};

/** 状态提示文案 */
const statusHintMap = {
  pending_pay: '订单待支付，请尽快完成支付',
  paid: '订单已支付，等待商家发货',
  shipped: '商品已发货，请注意查收',
  received: '已确认收货',
  completed: '订单已完成',
  cancelled: '订单已取消',
  refunding: '退款处理中，请耐心等待',
};

/** 支付方式映射 */
const payMethodMap = {
  wxpay: '微信支付',
  alipay: '支付宝',
};

const loading = ref(false);
const loadError = ref('');
const order = ref(null);

/** 时间线事件 */
const timelineEvents = computed(() => {
  if (!order.value) return [];
  const o = order.value;
  const events = [];

  const addEvent = (title, time, active) => {
    if (time) {
      events.push({ title, time: formatDate(time), active });
    } else {
      events.push({ title, time: '-', active: false });
    }
  };

  const now = new Date();
  const hasCreated = !!o.created_at;
  const hasPaid = !!o.pay_time;
  const hasShipped = !!o.ship_time;
  const hasReceived = !!o.receive_time;
  const isTerminal = ['cancelled', 'completed'].includes(o.status);
  const isRefunding = o.status === 'refunding';

  addEvent('提交订单', o.created_at, hasCreated);
  addEvent('支付成功', o.pay_time, hasPaid && !isTerminal);
  addEvent('商家发货', o.ship_time, hasShipped && !isTerminal);
  addEvent('确认收货', o.receive_time, hasReceived);

  if (o.status === 'completed') {
    addEvent('订单完成', o.receive_time || o.updated_at, true);
  } else if (o.status === 'cancelled') {
    addEvent('订单取消', o.updated_at, true);
  } else if (o.status === 'refunding') {
    addEvent('申请退款', o.updated_at, true);
  }

  return events;
});

/** 状态提示 */
const statusHint = computed(() => {
  if (!order.value) return '';
  return statusHintMap[order.value.status] || '';
});

/** 操作按钮 */
const actionButtons = computed(() => {
  if (!order.value) return [];
  const status = order.value.status;
  const buttons = [];

  if (status === 'pending_pay') {
    buttons.push({
      key: 'cancel',
      label: '取消订单',
      type: 'default',
      plain: true,
      handler: () => { cancelDialogVisible.value = true; },
    });
    buttons.push({
      key: 'pay',
      label: '去支付',
      type: 'primary',
      handler: goPay,
    });
  }

  if (status === 'paid') {
    buttons.push({
      key: 'refund',
      label: '申请退款',
      type: 'warning',
      plain: true,
      handler: goRefundApply,
    });
  }

  if (status === 'shipped') {
    buttons.push({
      key: 'receive',
      label: '确认收货',
      type: 'primary',
      handler: () => { receiveDialogVisible.value = true; },
    });
  }

  if (status === 'received') {
    buttons.push({
      key: 'refund',
      label: '申请退款',
      type: 'warning',
      plain: true,
      handler: goRefundApply,
    });
  }

  return buttons;
});

const cancelDialogVisible = ref(false);
const cancelling = ref(false);
const receiveDialogVisible = ref(false);
const receiving = ref(false);

/** 格式化日期 */
function formatDate(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

/** 获取订单详情 */
async function fetchDetail() {
  const orderId = Number(route.params.orderId);
  if (!orderId) {
    loadError.value = '订单ID无效';
    return;
  }

  loading.value = true;
  loadError.value = '';

  try {
    const res = await getOrderDetail(orderId);
    order.value = res.data;
  } catch (err) {
    const msg = err.response?.data?.message || '加载订单详情失败';
    loadError.value = msg;
    order.value = null;
  } finally {
    loading.value = false;
  }
}

/** 去支付 */
function goPay() {
  const o = order.value;
  router.push({
    name: 'Payment',
    params: { orderId: o.id },
    query: o.payment?.id ? { paymentId: o.payment.id } : {},
  });
}

/** 申请退款 */
function goRefundApply() {
  router.push({
    name: 'RefundApply',
    params: { orderId: order.value.id },
  });
}

/** 取消订单 */
async function handleCancelOrder() {
  cancelling.value = true;
  try {
    await cancelOrder(order.value.id);
    ElMessage.success('订单已取消');
    cancelDialogVisible.value = false;
    fetchDetail();
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '取消失败');
  } finally {
    cancelling.value = false;
  }
}

/** 确认收货 */
async function handleReceiveOrder() {
  receiving.value = true;
  try {
    await receiveOrder(order.value.id);
    ElMessage.success('已确认收货');
    receiveDialogVisible.value = false;
    fetchDetail();
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '确认收货失败');
  } finally {
    receiving.value = false;
  }
}

onMounted(() => {
  fetchDetail();
});
</script>

<style scoped>
.order-detail-page {
  --order-primary: #f97316;
  --order-primary-light: #fff7ed;
  --order-primary-hover: #ea580c;
  --order-primary-bg: #fff7ed;
  min-height: 100vh;
  background: var(--app-bg-page);
  padding-bottom: 80px;
}

/* 顶部导航 */
.detail-header {
  display: flex;
  align-items: center;
  gap: var(--app-space-sm);
  padding: var(--app-space-base) var(--app-space-xl);
  background: var(--app-bg-container);
  border-bottom: 1px solid var(--app-border-light);
  position: sticky;
  top: 0;
  z-index: 10;
}

.back-btn {
  color: var(--app-text-regular) !important;
  font-size: var(--app-font-base);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.back-btn:hover {
  color: var(--order-primary) !important;
}

.detail-title {
  font-size: var(--app-font-lg);
  font-weight: 600;
  color: var(--app-text-primary);
  margin: 0;
}

/* 内容区 */
.detail-content {
  max-width: 720px;
  margin: 0 auto;
  padding: var(--app-space-base) var(--app-space-lg);
}

/* 卡片通用 */
.card {
  background: var(--app-bg-container);
  border-radius: var(--app-radius-md);
  padding: var(--app-space-base) var(--app-space-lg);
  margin-bottom: var(--app-space-md);
  box-shadow: var(--app-shadow-level-1);
}

.card-title {
  display: flex;
  align-items: center;
  gap: var(--app-space-xs);
  font-size: var(--app-font-md);
  font-weight: 600;
  color: var(--app-text-primary);
  margin-bottom: var(--app-space-md);
  padding-bottom: var(--app-space-sm);
  border-bottom: 1px solid var(--app-border-light);
}

.card-icon {
  color: var(--order-primary);
  font-size: 16px;
}

/* 状态卡片 */
.status-card {
  border-left: 4px solid var(--order-primary);
}

.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.order-no {
  font-size: var(--app-font-sm);
  color: var(--app-text-secondary);
}

.status-tag {
  border-radius: var(--app-radius-sm);
  font-weight: 500;
}

.status-hint {
  margin-top: var(--app-space-sm);
  font-size: var(--app-font-sm);
  color: var(--app-text-secondary);
}

/* 地址卡片 */
.address-body {
  padding-left: 24px;
}

.address-contact {
  font-size: var(--app-font-base);
  font-weight: 500;
  color: var(--app-text-primary);
  margin: 0 0 4px;
}

.address-detail {
  font-size: var(--app-font-sm);
  color: var(--app-text-secondary);
  margin: 0;
  line-height: 1.5;
}

/* 商品列表 */
.item-row {
  display: flex;
  align-items: center;
  gap: var(--app-space-md);
  padding: var(--app-space-md) 0;
  border-bottom: 1px solid var(--app-border-light);
}

.item-row:last-child {
  border-bottom: none;
}

.item-image {
  width: 72px;
  height: 72px;
  border-radius: var(--app-radius-base);
  overflow: hidden;
  flex-shrink: 0;
  background: var(--app-bg-disabled);
}

.item-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-title {
  font-size: var(--app-font-base);
  color: var(--app-text-primary);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.item-spec {
  font-size: var(--app-font-xs);
  color: var(--app-text-secondary);
  margin: 4px 0 0;
}

.item-price-qty {
  text-align: right;
  flex-shrink: 0;
}

.item-price {
  font-size: var(--app-font-base);
  color: var(--app-text-primary);
  font-weight: 500;
}

.item-qty {
  font-size: var(--app-font-xs);
  color: var(--app-text-secondary);
  margin-left: 4px;
}

/* 金额明细 */
.amount-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
}

.amount-label {
  font-size: var(--app-font-base);
  color: var(--app-text-secondary);
}

.amount-value {
  font-size: var(--app-font-base);
  color: var(--app-text-primary);
}

.discount-row .amount-value {
  color: var(--app-color-success);
}

.total-row {
  border-top: 1px dashed var(--app-border-light);
  padding-top: var(--app-space-sm);
  margin-top: var(--app-space-xs);
}

.total-row .amount-label {
  font-weight: 600;
  color: var(--app-text-primary);
}

.total-price {
  font-size: var(--app-font-xl);
  font-weight: 700;
  color: var(--order-primary);
}

/* 时间线 */
.order-timeline {
  padding-left: 8px;
}

.timeline-title {
  font-size: var(--app-font-sm);
  color: var(--app-text-secondary);
  margin: 0;
}

.timeline-active {
  color: var(--app-text-primary);
  font-weight: 600;
}

/* 错误态 */
.error-state {
  padding: var(--app-space-4xl) 0;
}

/* 底部操作栏 */
.action-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: var(--app-bg-container);
  border-top: 1px solid var(--app-border-light);
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.04);
  z-index: 100;
  padding: var(--app-space-md) var(--app-space-lg);
}

.action-bar-inner {
  max-width: 720px;
  margin: 0 auto;
  display: flex;
  justify-content: flex-end;
  gap: var(--app-space-md);
}

.action-btn {
  min-width: 100px;
  border-radius: var(--app-radius-base);
}

.action-btn:deep(.el-button--primary) {
  background-color: var(--order-primary);
  border-color: var(--order-primary);
}

.action-btn:deep(.el-button--primary:hover) {
  background-color: var(--order-primary-hover);
  border-color: var(--order-primary-hover);
}

/* 弹窗文案 */
.dialog-text {
  text-align: center;
  color: var(--app-text-regular);
  font-size: var(--app-font-base);
  line-height: 1.6;
}

/* 响应式 */
@media (max-width: 768px) {
  .detail-header {
    padding: var(--app-space-sm) var(--app-space-base);
  }

  .detail-content {
    padding: var(--app-space-sm) var(--app-space-base);
  }

  .card {
    padding: var(--app-space-md);
    border-radius: var(--app-radius-base);
  }

  .action-bar {
    padding: var(--app-space-sm) var(--app-space-base);
  }

  .action-bar-inner {
    gap: var(--app-space-sm);
  }

  .action-btn {
    min-width: 80px;
    font-size: var(--app-font-sm);
  }

  .item-image {
    width: 60px;
    height: 60px;
  }
}
</style>
