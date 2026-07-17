<template>
  <div class="order-detail-page">
    <!-- Loading Skeleton -->
    <div v-if="loading" class="detail-loading">
      <div class="skeleton-header-block">
        <div class="skeleton-line w-30" />
        <div class="skeleton-line w-20" />
      </div>
      <div class="skeleton-section">
        <div class="skeleton-line w-40" />
        <div class="skeleton-line w-60" />
        <div class="skeleton-line w-25" />
      </div>
      <div class="skeleton-section">
        <div class="skeleton-item-row">
          <div class="skeleton-thumb" />
          <div class="skeleton-lines">
            <div class="skeleton-line w-50" />
            <div class="skeleton-line w-30" />
            <div class="skeleton-line w-20" />
          </div>
        </div>
      </div>
      <div class="skeleton-section">
        <div class="skeleton-line w-40" />
        <div class="skeleton-line w-80" />
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="detail-error">
      <el-result icon="error" :title="errorTitle" :sub-title="errorMessage">
        <template #extra>
          <el-button type="primary" @click="fetchDetail">重新加载</el-button>
          <el-button @click="router.back()">返回</el-button>
        </template>
      </el-result>
    </div>

    <!-- Order Detail Content -->
    <template v-else-if="orderData">
      <!-- Header -->
      <div class="detail-header">
        <el-page-header @back="router.back()" title="返回订单列表" />
        <div class="order-status-header">
          <h2 class="order-no-title">订单号：{{ orderData.order.orderNo }}</h2>
          <el-tag :type="getStatusTagType(orderData.order.status)" size="large" round>
            {{ getStatusLabel(orderData.order.status) }}
          </el-tag>
        </div>
      </div>

      <!-- Order Timeline -->
      <el-card class="detail-section">
        <template #header>
          <span class="section-title">订单进度</span>
        </template>
        <div class="order-timeline">
          <div
            v-for="(node, idx) in timelineNodes"
            :key="idx"
            class="timeline-node"
            :class="{ active: node.active, completed: node.completed }"
          >
            <div class="timeline-indicator">
              <div class="timeline-dot" />
              <div
                v-if="idx < timelineNodes.length - 1"
                class="timeline-line"
                :class="{ completed: node.completed }"
              />
            </div>
            <div class="timeline-body">
              <div class="timeline-title">{{ node.title }}</div>
              <div v-if="node.time" class="timeline-time">{{ node.time }}</div>
              <div v-if="node.desc" class="timeline-desc">{{ node.desc }}</div>
            </div>
          </div>
        </div>
      </el-card>

      <!-- Sub Orders -->
      <el-card
        v-for="(sub, idx) in orderData.subOrders"
        :key="idx"
        class="detail-section"
      >
        <template #header>
          <div class="sub-order-header">
            <span class="shop-name">{{ sub.shopName }}</span>
            <el-tag :type="getStatusTagType(sub.status)" size="small" round>
              {{ getStatusLabel(sub.status) }}
            </el-tag>
          </div>
        </template>
        <div
          v-for="item in sub.items"
          :key="item.skuId"
          class="order-item"
        >
          <el-image :src="item.snapshot?.image" class="item-thumb" fit="cover">
            <template #error>
              <div class="image-placeholder">{{ (item.snapshot?.spuName || '商品').charAt(0) }}</div>
            </template>
          </el-image>
          <div class="item-info">
            <div class="item-name">{{ item.snapshot?.spuName }}</div>
            <div class="item-spec">{{ item.snapshot?.specName }}</div>
          </div>
          <div class="item-price">¥{{ item.price }}</div>
          <div class="item-qty">×{{ item.quantity }}</div>
          <div class="item-subtotal">¥{{ calcSubtotal(item.price, item.quantity) }}</div>
        </div>
        <div class="sub-order-footer">
          <span class="sub-order-label">共{{ sub.items?.length || 0 }}件商品，小计：</span>
          <span class="sub-order-amount">¥{{ sub.amount }}</span>
        </div>
      </el-card>

      <!-- Shipment Info -->
      <el-card
        v-if="orderData.shipments && orderData.shipments.length > 0"
        class="detail-section"
      >
        <template #header>
          <span class="section-title">物流信息</span>
        </template>
        <div
          v-for="shipment in orderData.shipments"
          :key="shipment.subOrderId"
          class="shipment-block"
        >
          <div class="shipment-basic">
            <span class="shipment-carrier">{{ shipment.carrierCode || '物流承运商' }}</span>
            <span class="shipment-tracking">运单号：{{ shipment.trackingNo }}</span>
          </div>
          <el-timeline v-if="shipment.events && shipment.events.length > 0" class="shipment-timeline">
            <el-timeline-item
              v-for="(evt, ei) in shipment.events"
              :key="ei"
              :timestamp="evt.timestamp"
              placement="top"
              :color="ei === 0 ? 'var(--color-primary-500)' : 'var(--color-border)'"
            >
              {{ evt.event }}
            </el-timeline-item>
          </el-timeline>
          <div v-else class="shipment-empty">
            物流信息更新中，请耐心等待
          </div>
        </div>
      </el-card>

      <!-- Address -->
      <el-card v-if="orderData.address" class="detail-section">
        <template #header>
          <span class="section-title">收货信息</span>
        </template>
        <div class="address-info">
          <div class="address-row">
            <span class="address-label">收货人：</span>
            <span>{{ orderData.address.contactName }} {{ orderData.address.phone }}</span>
          </div>
          <div class="address-row">
            <span class="address-label">收货地址：</span>
            <span>{{ orderData.address.province }}{{ orderData.address.city }}{{ orderData.address.district }} {{ orderData.address.detail }}</span>
          </div>
        </div>
      </el-card>

      <!-- Price Summary -->
      <el-card class="detail-section">
        <template #header>
          <span class="section-title">价格明细</span>
        </template>
        <div class="price-summary">
          <div class="price-row">
            <span>商品总额</span>
            <span>¥{{ orderData.order.totalAmount }}</span>
          </div>
          <div class="price-row">
            <span>运费</span>
            <span>免运费</span>
          </div>
          <div class="price-row total">
            <span>实付款</span>
            <span class="total-amount">¥{{ orderData.order.totalAmount }}</span>
          </div>
        </div>
      </el-card>

      <!-- Bottom Actions -->
      <div class="detail-actions">
        <el-button
          v-if="orderData.order.status === 'shipped'"
          type="primary"
          @click="showConfirmDialog = true"
        >
          确认收货
        </el-button>
        <el-button
          v-if="['paid', 'shipped', 'completed'].includes(orderData.order.status)"
          @click="router.push({ name: 'RefundApply', params: { subOrderId: orderId } })"
        >
          申请售后
        </el-button>
        <el-button
          v-if="orderData.order.status === 'refunding'"
          @click="router.push({ name: 'RefundDetail', params: { requestNo: orderId } })"
        >
          查看售后进度
        </el-button>
        <el-button @click="router.push({name:'OrderList'})">返回订单列表</el-button>
        <el-button @click="router.push({name:'CheckoutPay'})">返回支付</el-button>
      </div>
    </template>

    <!-- Confirm Receive Dialog -->
    <el-dialog
      v-model="showConfirmDialog"
      title="确认收货"
      width="420px"
      :close-on-click-modal="false"
    >
      <p class="confirm-text">确认收货后，款项将打给商家</p>
      <p class="confirm-warning">确认收货后不可恢复</p>
      <template #footer>
        <el-button @click="showConfirmDialog = false">取消</el-button>
        <el-button type="primary" :loading="confirming" @click="handleConfirmReceive">
          确认收货
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { ElMessage } from 'element-plus';
import { getOrderDetail, confirmReceive } from '@/api/orders';

const router = useRouter();
const route = useRoute();

// ── Route param ──
const orderId = Number(route.params.id);

// ── State ──
const loading = ref(true);
const error = ref(false);
const errorTitle = ref('订单不存在');
const errorMessage = ref('');
const orderData = ref(null);
const showConfirmDialog = ref(false);
const confirming = ref(false);

// ── Status config ──
const statusLabelMap = {
  pending: '待付款',
  paid: '待发货',
  shipped: '已发货',
  completed: '已完成',
  cancelled: '已取消',
  refunding: '退款中',
  refunded: '已退款',
};

const statusTagTypeMap = {
  pending: 'warning',
  paid: '',
  shipped: 'primary',
  completed: 'success',
  cancelled: 'info',
  refunding: 'danger',
  refunded: 'danger',
};

function getStatusLabel(status) {
  return statusLabelMap[status] || status;
}

function getStatusTagType(status) {
  return statusTagTypeMap[status] || 'info';
}

function formatTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const h = String(d.getHours()).padStart(2, '0');
  const min = String(d.getMinutes()).padStart(2, '0');
  return `${y}-${m}-${day} ${h}:${min}`;
}

function calcSubtotal(price, qty) {
  return (parseFloat(price) * qty).toFixed(2);
}

// ── Timeline ──
const timelineNodes = computed(() => {
  if (!orderData.value) return [];
  const o = orderData.value.order;
  const status = o.status;

  // Cancelled path
  if (status === 'cancelled') {
    return [
      { title: '提交订单', time: formatTime(o.createdAt), desc: '', completed: true, active: false },
      { title: '订单已取消', time: formatTime(o.updatedAt), desc: '该订单已被取消', completed: false, active: true },
    ];
  }

  // Refund path
  if (status === 'refunding' || status === 'refunded') {
    const isDone = status === 'refunded';
    return [
      { title: '提交订单', time: formatTime(o.createdAt), desc: '', completed: true, active: false },
      { title: '已付款', time: formatTime(o.paidAt), desc: '', completed: true, active: false },
      { title: isDone ? '已退款' : '退款处理中', time: formatTime(o.updatedAt), desc: isDone ? '退款已到账' : '请耐心等待商家处理', completed: isDone, active: !isDone },
    ];
  }

  // Normal flow: pending → paid → shipped → completed
  const isPending = status === 'pending';
  const isPaid = status === 'paid';
  const isShipped = status === 'shipped';
  const isCompleted = status === 'completed';

  return [
    {
      title: '提交订单',
      time: formatTime(o.createdAt),
      desc: '',
      completed: true,
      active: false,
    },
    {
      title: '已付款',
      time: o.paidAt ? formatTime(o.paidAt) : '',
      desc: isPending ? '等待付款' : '',
      completed: !!o.paidAt && !isPending,
      active: isPending,
    },
    {
      title: '已发货',
      time: isShipped || isCompleted ? formatTime(o.updatedAt) : '',
      desc: isPaid ? '等待商家发货' : '',
      completed: isShipped || isCompleted,
      active: isPaid,
    },
    {
      title: '已完成',
      time: isCompleted ? formatTime(o.updatedAt) : '',
      desc: isCompleted ? '交易完成' : '',
      completed: isCompleted,
      active: isShipped,
    },
  ];
});

// ── Confirm Receive ──
async function handleConfirmReceive() {
  confirming.value = true;
  try {
    const res = await confirmReceive(orderId);
    ElMessage.success('收货确认成功');
    showConfirmDialog.value = false;
    if (orderData.value) {
      orderData.value.order.status = res.data?.status || 'completed';
    }
  } catch (e) {
    const msg = e?.response?.data?.message || '确认收货失败，请重试';
    ElMessage.error(msg);
  } finally {
    confirming.value = false;
  }
}

// ── Fetch ──
async function fetchDetail() {
  loading.value = true;
  error.value = false;
  try {
    const res = await getOrderDetail(orderId);
    orderData.value = res.data;
  } catch (e) {
    error.value = true;
    const status = e?.response?.status;
    if (status === 404) {
      errorTitle.value = '订单不存在';
      errorMessage.value = '该订单不存在或已被删除';
    } else if (status === 403) {
      errorTitle.value = '无权查看';
      errorMessage.value = '您无权查看此订单';
    } else {
      errorTitle.value = '加载失败';
      errorMessage.value = '网络连接出现问题，请检查网络后重试';
    }
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  fetchDetail();
});
</script>

<style scoped>
/* ── Page-level tokens ── */
.order-detail-page {
  --page-order-spacing-unit: 4px;
  --page-order-row-height: 56px;
  --page-order-card-border: 1px solid var(--color-border, hsl(25, 7%, 90%));
  --page-order-timeline-line: var(--color-border, hsl(25, 7%, 90%));
  --page-order-timeline-dot-active: var(--color-primary-500, hsl(25, 85%, 55%));
  --page-order-timeline-dot-inactive: var(--color-border, hsl(25, 7%, 90%));

  max-width: 800px;
  margin: 0 auto;
  padding: var(--space-lg, 24px);
  min-height: 60vh;
}

/* ── Skeleton ── */
.detail-loading {
  display: flex;
  flex-direction: column;
  gap: var(--space-md, 16px);
}

.skeleton-header-block {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm, 8px);
  padding: var(--space-md, 16px) 0;
}

.skeleton-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm, 8px);
  padding: var(--space-lg, 24px);
  background: var(--color-bg-base, #FFFFFF);
  border: var(--page-order-card-border);
  border-radius: var(--radius-md, 20px);
}

.skeleton-item-row {
  display: flex;
  gap: var(--space-md, 16px);
}

.skeleton-line {
  height: 14px;
  border-radius: 4px;
  background: linear-gradient(
    90deg,
    var(--color-primary-50, hsl(25, 26%, 95%)) 25%,
    var(--color-bg-base, #FFFFFF) 50%,
    var(--color-primary-50, hsl(25, 26%, 95%)) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.8s infinite;
}

.skeleton-thumb {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-sm, 10px);
  flex-shrink: 0;
  background: linear-gradient(
    90deg,
    var(--color-primary-50, hsl(25, 26%, 95%)) 25%,
    var(--color-bg-base, #FFFFFF) 50%,
    var(--color-primary-50, hsl(25, 26%, 95%)) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.8s infinite;
}

.skeleton-lines {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton-line.w-20 { width: 20%; }
.skeleton-line.w-25 { width: 25%; }
.skeleton-line.w-30 { width: 30%; }
.skeleton-line.w-40 { width: 40%; }
.skeleton-line.w-50 { width: 50%; }
.skeleton-line.w-60 { width: 60%; }
.skeleton-line.w-80 { width: 80%; }

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ── Error ── */
.detail-error {
  display: flex;
  justify-content: center;
  padding: var(--space-2xl, 48px) 0;
}

/* ── Header ── */
.detail-header {
  margin-bottom: var(--space-lg, 24px);
}

.detail-header :deep(.el-page-header) {
  margin-bottom: var(--space-md, 16px);
}

.order-status-header {
  display: flex;
  align-items: center;
  gap: var(--space-md, 16px);
}

.order-no-title {
  font-size: var(--font-size-lg, 17.5px);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.5px;
}

/* ── Sections ── */
.detail-section {
  margin-bottom: var(--space-md, 16px);
  border: var(--page-order-card-border) !important;
  border-radius: var(--radius-md, 20px) !important;
  box-shadow: none !important;
}

.detail-section :deep(.el-card__header) {
  background: var(--color-bg-page, hsl(25, 5%, 97%));
  padding: 12px var(--space-lg, 24px);
  border-bottom: var(--page-order-card-border);
}

.section-title {
  font-size: var(--font-size-base, 14px);
  font-weight: 600;
  color: var(--color-text-primary);
}

/* ── Timeline ── */
.order-timeline {
  padding: var(--space-sm, 8px) 0;
}

.timeline-node {
  display: flex;
  gap: var(--space-md, 16px);
  min-height: 48px;
}

.timeline-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 12px;
  flex-shrink: 0;
}

.timeline-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--page-order-timeline-dot-inactive);
  margin-top: 6px;
  flex-shrink: 0;
  transition: all var(--duration-normal, 225ms) var(--ease-smooth, ease);
}

.timeline-node.active .timeline-dot {
  width: 12px;
  height: 12px;
  background: var(--page-order-timeline-dot-active);
  margin-top: 4px;
  box-shadow: 0 0 0 6px hsla(25, 85%, 55%, 0.1);
  animation: dot-pulse 2s infinite;
}

.timeline-node.completed .timeline-dot {
  width: 10px;
  height: 10px;
  background: var(--page-order-timeline-dot-active);
  margin-top: 5px;
  box-shadow: 0 0 0 3px hsla(25, 85%, 55%, 0.15);
}

@keyframes dot-pulse {
  0%, 100% { box-shadow: 0 0 0 6px hsla(25, 85%, 55%, 0.1); }
  50% { box-shadow: 0 0 0 10px hsla(25, 85%, 55%, 0.05); }
}

.timeline-line {
  flex: 1;
  width: 2px;
  min-height: 48px;
  background: var(--page-order-timeline-line);
  margin: 2px 0;
}

.timeline-line.completed {
  background: var(--color-primary-300, hsl(25, 72%, 70%));
}

.timeline-body {
  padding-bottom: var(--space-md, 16px);
  flex: 1;
}

.timeline-title {
  font-size: var(--font-size-base, 14px);
  font-weight: 600;
  color: var(--color-text-secondary);
  line-height: var(--line-height-tight, 1.25);
}

.timeline-node.active .timeline-title,
.timeline-node.completed .timeline-title {
  color: var(--color-text-primary);
}

.timeline-time {
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-tertiary);
  margin-top: 2px;
}

.timeline-desc {
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-secondary);
  margin-top: 2px;
}

/* ── Sub Orders ── */
.sub-order-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm, 8px);
}

.shop-name {
  font-size: var(--font-size-base, 14px);
  font-weight: 600;
  color: var(--color-text-primary);
}

.order-item {
  display: flex;
  align-items: center;
  gap: var(--space-sm, 8px);
  padding: var(--space-sm, 8px) 0;
  border-bottom: 1px solid var(--color-border, hsl(25, 7%, 90%));
}

.order-item:last-child {
  border-bottom: none;
}

.item-thumb {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-sm, 10px);
  flex-shrink: 0;
}

.image-placeholder {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary-50, hsl(25, 26%, 95%));
  color: var(--color-primary-500);
  font-size: var(--font-size-lg, 17.5px);
  font-weight: 600;
  border-radius: var(--radius-sm, 10px);
}

.item-info {
  flex: 1;
  overflow: hidden;
}

.item-name {
  font-size: var(--font-size-base, 14px);
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-spec {
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-secondary);
  margin-top: 2px;
}

.item-price {
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-secondary);
  font-variant-numeric: tabular-nums;
  min-width: 60px;
  text-align: right;
}

.item-qty {
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-secondary);
  min-width: 36px;
  text-align: center;
}

.item-subtotal {
  font-size: var(--font-size-base, 14px);
  font-weight: 600;
  color: var(--color-text-primary);
  font-variant-numeric: tabular-nums;
  min-width: 80px;
  text-align: right;
}

.sub-order-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding-top: var(--space-sm, 8px);
  gap: var(--space-xs, 4px);
}

.sub-order-label {
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-secondary);
}

.sub-order-amount {
  font-size: var(--font-size-md, 15.75px);
  font-weight: 600;
  color: var(--color-text-primary);
  font-variant-numeric: tabular-nums;
}

/* ── Shipment ── */
.shipment-block {
  padding: var(--space-xs, 4px) 0;
}

.shipment-block + .shipment-block {
  margin-top: var(--space-md, 16px);
  padding-top: var(--space-md, 16px);
  border-top: var(--page-order-card-border);
}

.shipment-basic {
  display: flex;
  gap: var(--space-lg, 24px);
  padding-bottom: var(--space-sm, 8px);
  margin-bottom: var(--space-sm, 8px);
}

.shipment-carrier {
  font-size: var(--font-size-base, 14px);
  font-weight: 600;
  color: var(--color-text-primary);
}

.shipment-tracking {
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-secondary);
  font-variant-numeric: tabular-nums;
}

.shipment-timeline {
  padding-left: var(--space-sm, 8px);
}

.shipment-empty {
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-tertiary);
  padding: var(--space-sm, 8px) 0;
}

/* ── Address ── */
.address-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs, 4px);
}

.address-row {
  font-size: var(--font-size-base, 14px);
  color: var(--color-text-primary);
  line-height: var(--line-height-normal, 1.5);
}

.address-label {
  color: var(--color-text-secondary);
}

/* ── Price Summary ── */
.price-summary {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm, 8px);
}

.price-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--font-size-base, 14px);
  color: var(--color-text-secondary);
}

.price-row.total {
  padding-top: var(--space-sm, 8px);
  border-top: 1px solid var(--color-border, hsl(25, 7%, 90%));
  font-size: var(--font-size-md, 15.75px);
  font-weight: 600;
  color: var(--color-text-primary);
}

.total-amount {
  font-size: var(--font-size-lg, 17.5px);
  font-weight: 700;
  color: var(--color-primary-600);
  font-variant-numeric: tabular-nums;
}

/* ── Bottom Actions ── */
.detail-actions {
  display: flex;
  justify-content: center;
  gap: var(--space-md, 16px);
  padding: var(--space-lg, 24px) 0;
}

/* ── Confirm Dialog ── */
.confirm-text {
  font-size: var(--font-size-base, 14px);
  color: var(--color-text-primary);
  line-height: var(--line-height-relaxed, 1.75);
}

.confirm-warning {
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-tertiary);
  margin-top: var(--space-xs, 4px);
}

/* ── Responsive ── */
@media (max-width: 767px) {
  .order-detail-page {
    padding: var(--space-md, 16px);
  }

  .order-no-title {
    font-size: var(--font-size-base, 14px);
  }

  .order-item {
    flex-wrap: wrap;
  }

  .item-thumb,
  .image-placeholder {
    width: 48px;
    height: 48px;
  }

  .detail-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .detail-actions .el-button {
    width: 100%;
  }
}
</style>
