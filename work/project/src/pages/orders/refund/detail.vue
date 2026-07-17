<template>
  <div class="refund-detail-page">
    <!-- 返回导航 -->
    <div class="page-header">
      <el-button :icon="ArrowLeft" text @click="goBack">返回订单详情</el-button>
    </div>

    <!-- 加载态骨架 -->
    <div v-if="loading" class="skeleton-card">
      <el-skeleton :rows="10" animated />
    </div>

    <!-- 错误态 -->
    <div v-else-if="errorMsg" class="error-state">
      <div class="error-icon">
        <el-icon :size="48"><WarningFilled /></el-icon>
      </div>
      <h3 class="error-title">{{ errorMsg }}</h3>
      <p class="error-desc">请返回订单列表重试</p>
      <el-button type="primary" @click="router.push({ name: 'OrderList' })">返回订单列表</el-button>
    </div>

    <!-- 售后详情 -->
    <template v-else-if="refund">
      <!-- 状态卡片 -->
      <div class="status-card">
        <div class="status-header">
          <span class="status-label">售后单号</span>
          <span class="status-no">{{ refund.requestNo }}</span>
          <el-tag
            :type="statusTagType"
            class="status-badge"
            effect="plain"
          >
            <span class="status-dot" :class="statusDotClass"></span>
            {{ statusLabel }}
          </el-tag>
        </div>

        <!-- 进度步骤条 -->
        <div class="progress-steps">
          <div
            v-for="(step, index) in steps"
            :key="index"
            class="step-item"
            :class="{
              'step-done': step.done,
              'step-active': step.active,
              'step-pending': !step.done && !step.active
            }"
          >
            <div class="step-dot">
              <el-icon v-if="step.done" :size="14"><Check /></el-icon>
              <span v-else-if="step.active" class="step-dot-inner"></span>
              <span v-else class="step-dot-empty"></span>
            </div>
            <div class="step-content">
              <span class="step-name">{{ step.label }}</span>
              <span v-if="step.time" class="step-time">{{ step.time }}</span>
            </div>
            <div
              v-if="index < steps.length - 1"
              class="step-line"
              :class="{ 'step-line-done': step.done }"
            ></div>
          </div>
        </div>
      </div>

      <!-- 信息卡片 -->
      <div class="info-card">
        <h3 class="card-title">售后信息</h3>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">售后类型</span>
            <span class="info-value">{{ refund.type === 'only_refund' ? '仅退款' : '退货退款' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">退款金额</span>
            <span class="info-value info-amount">¥{{ Number(refund.amount).toFixed(2) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">申请时间</span>
            <span class="info-value">{{ formatTime(refund.createdAt) }}</span>
          </div>
          <div class="info-item info-item-full">
            <span class="info-label">申请原因</span>
            <span class="info-value">{{ refund.reason }}</span>
          </div>
          <div v-if="refund.merchantReviewReason" class="info-item info-item-full">
            <span class="info-label">商家意见</span>
            <span class="info-value">{{ refund.merchantReviewReason }}</span>
          </div>
          <div v-if="refund.arbitrationRuling" class="info-item info-item-full">
            <span class="info-label">平台裁决</span>
            <span class="info-value">{{ refund.arbitrationRuling }}</span>
          </div>
        </div>

        <!-- 凭证图片 -->
        <div v-if="refund.evidenceImages && refund.evidenceImages.length" class="evidence-section">
          <span class="info-label">凭证图片</span>
          <div class="evidence-list">
            <img
              v-for="(img, idx) in refund.evidenceImages"
              :key="idx"
              :src="img"
              class="evidence-img"
              @click="previewImage(img)"
              alt="凭证"
            />
          </div>
        </div>
      </div>

      <!-- 操作日志 -->
      <div v-if="logs && logs.length" class="info-card">
        <h3 class="card-title">处理记录</h3>
        <div class="log-timeline">
          <div
            v-for="(log, index) in logs"
            :key="index"
            class="log-item"
          >
            <div class="log-dot"></div>
            <div class="log-content">
              <span class="log-action">{{ log.detail }}</span>
              <span class="log-time">{{ formatTime(log.createdAt) }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ArrowLeft, Check, WarningFilled } from '@element-plus/icons-vue';
import { getRefundDetail } from '@/api/refunds';

const route = useRoute();
const router = useRouter();

const loading = ref(true);
const errorMsg = ref('');
const refund = ref(null);
const logs = ref([]);

const refundId = computed(() => Number(route.params.requestNo));

// 状态标签映射
const statusLabel = computed(() => {
  const map = {
    pending: '待审核',
    awaiting_return: '待退货',
    awaiting_merchant_receive: '待商家收货',
    refunding: '退款中',
    completed: '已完成',
    rejected: '已拒绝',
    arbitrating: '仲裁中',
    closed: '已关闭',
    retry: '退款重试中'
  };
  return refund.value ? (map[refund.value.status] || refund.value.status) : '';
});

const statusTagType = computed(() => {
  const map = {
    pending: 'warning',
    awaiting_return: 'info',
    awaiting_merchant_receive: '',
    refunding: '',
    completed: 'success',
    rejected: 'danger',
    arbitrating: 'warning',
    closed: 'info',
    retry: 'warning'
  };
  return refund.value ? (map[refund.value.status] || 'info') : 'info';
});

const statusDotClass = computed(() => {
  const map = {
    completed: 'dot-success',
    rejected: 'dot-error',
    closed: 'dot-neutral',
    refunding: 'dot-primary',
    pending: 'dot-warning',
    awaiting_return: 'dot-info',
    awaiting_merchant_receive: 'dot-primary',
    arbitrating: 'dot-warning',
    retry: 'dot-warning'
  };
  return refund.value ? (map[refund.value.status] || 'dot-info') : 'dot-info';
});

// 进度步骤
const steps = computed(() => {
  if (!refund.value) return [];

  const s = refund.value.status;
  const t = refund.value.type;
  const isReturn = t === 'return_refund';

  // 判断各步骤完成状态
  const isPending = s === 'pending';
  const isRejected = s === 'rejected';
  const isArbitrating = s === 'arbitrating';
  const isClosed = s === 'closed';

  const stepDefs = [
    { key: 'apply', label: '提交申请', done: s !== 'pending' || ['completed', 'refunding', 'awaiting_return', 'awaiting_merchant_receive', 'rejected', 'arbitrating', 'closed', 'retry'].includes(s), active: s === 'pending', time: formatTime(refund.value.createdAt) },
    { key: 'review', label: '商家审核', done: ['awaiting_return', 'awaiting_merchant_receive', 'refunding', 'completed', 'rejected', 'arbitrating', 'closed', 'retry'].includes(s), active: s === 'pending' },
  ];

  if (isReturn && s !== 'rejected' && s !== 'closed' && s !== 'arbitrating') {
    stepDefs.push({ key: 'return', label: '买家退货', done: ['awaiting_merchant_receive', 'refunding', 'completed'].includes(s), active: s === 'awaiting_return' });
    stepDefs.push({ key: 'receive', label: '商家收货', done: ['refunding', 'completed'].includes(s), active: s === 'awaiting_merchant_receive' });
  }

  stepDefs.push({ key: 'refund', label: '退款处理', done: s === 'completed', active: ['refunding', 'retry'].includes(s) });

  if (s === 'rejected') {
    stepDefs.push({ key: 'result', label: '已拒绝', done: true, active: false });
  } else if (s === 'arbitrating') {
    stepDefs.push({ key: 'arbitrate', label: '平台仲裁', done: false, active: true });
  } else if (s === 'closed') {
    stepDefs.push({ key: 'closed', label: '已关闭', done: true, active: false });
  } else if (s === 'completed') {
    stepDefs[stepDefs.length - 1] = { key: 'done', label: '已完成', done: true, active: false };
  }

  return stepDefs;
});

function goBack() {
  if (refund.value?.subOrderId) {
    router.push({ name: 'OrderDetail', params: { id: refund.value.subOrderId } });
  } else if (route.params.requestNo) {
    router.push({ name: 'RefundApply', params: { subOrderId: route.params.requestNo } });
  } else {
    router.push({ name: 'OrderList' });
  }
}

function formatTime(t) {
  if (!t) return '';
  const d = new Date(t);
  if (isNaN(d.getTime())) return t;
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function previewImage(url) {
  window.open(url, '_blank');
}

onMounted(async () => {
  if (!refundId.value || isNaN(refundId.value)) {
    errorMsg.value = '售后单信息缺失';
    loading.value = false;
    return;
  }

  try {
    const res = await getRefundDetail(refundId.value);

    if (res.data?.mockHint) {
      // mock 提示已经在 request 拦截器处理，这里作为兜底
    }

    refund.value = res.data?.refund || res.data;
    logs.value = res.data?.logs || [];
  } catch (err) {
    const status = err.response?.status;
    const msg = err.response?.data?.message || err.message || '加载失败';

    if (status === 404) {
      errorMsg.value = '售后单不存在';
    } else if (status === 403) {
      errorMsg.value = '无权查看此售后单';
    } else {
      errorMsg.value = msg;
    }
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.refund-detail-page {
  max-width: 720px;
  margin: 0 auto;
  padding: var(--space-lg);
}

.page-header {
  margin-bottom: var(--space-md);
}

.skeleton-card {
  background: var(--color-bg-base);
  border: var(--page-order-card-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
}

.error-state {
  background: var(--color-bg-base);
  border: var(--page-order-card-border);
  border-radius: var(--radius-md);
  padding: var(--space-2xl) var(--space-lg);
  text-align: center;
}

.error-icon {
  color: var(--color-error);
  opacity: 0.6;
  margin-bottom: var(--space-md);
}

.error-title {
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-sm);
}

.error-desc {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-lg);
}

/* 状态卡片 */
.status-card {
  background: var(--color-bg-base);
  border: var(--page-order-card-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  margin-bottom: var(--space-md);
}

.status-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-lg);
  flex-wrap: wrap;
}

.status-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.status-no {
  font-family: var(--font-family);
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.5px;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  font-weight: 500;
}

.status-badge {
  margin-left: auto;
  min-width: 72px;
  justify-content: center;
}

.status-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  margin-right: 4px;
}

.dot-success { background: var(--color-success); }
.dot-error { background: var(--color-error); }
.dot-neutral { background: var(--color-text-tertiary); }
.dot-primary { background: var(--color-primary-500); }
.dot-warning { background: var(--color-warning); }
.dot-info { background: var(--color-info); }

/* 进度步骤条 */
.progress-steps {
  display: flex;
  align-items: flex-start;
  position: relative;
}

.step-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  min-width: 0;
}

.step-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 1;
  background: var(--color-bg-base);
  margin-bottom: var(--space-sm);
}

.step-done .step-dot {
  background: var(--color-primary-500);
  color: #fff;
  box-shadow: 0 0 0 3px hsla(25, 85%, 55%, 0.15);
}

.step-active .step-dot {
  border: 2px solid var(--color-primary-500);
  box-shadow: 0 0 0 6px hsla(25, 85%, 55%, 0.1);
}

.step-active .step-dot-inner {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-primary-500);
}

.step-pending .step-dot {
  border: 2px solid var(--color-border);
}

.step-pending .step-dot-empty {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-border);
}

.step-content {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.step-name {
  font-size: var(--font-size-xs);
  font-weight: 500;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.step-done .step-name {
  color: var(--color-text-primary);
  font-weight: 600;
}

.step-active .step-name {
  color: var(--color-primary-600);
  font-weight: 600;
}

.step-time {
  font-size: 10px;
  color: var(--color-text-tertiary);
}

.step-line {
  position: absolute;
  top: 14px;
  left: calc(50% + 14px);
  width: calc(100% - 28px);
  height: 2px;
  background: var(--color-border);
  z-index: 0;
}

.step-line-done {
  background: var(--color-primary-300);
}

/* 信息卡片 */
.info-card {
  background: var(--color-bg-base);
  border: var(--page-order-card-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  margin-bottom: var(--space-md);
}

.card-title {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-md);
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-md);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.info-item-full {
  grid-column: 1 / -1;
}

.info-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.info-value {
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  line-height: var(--line-height-normal);
}

.info-amount {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  color: var(--color-error);
  font-size: var(--font-size-md);
}

.evidence-section {
  margin-top: var(--space-md);
  padding-top: var(--space-md);
  border-top: 1px solid var(--color-border);
}

.evidence-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
  margin-top: var(--space-sm);
}

.evidence-img {
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-smooth);
}

.evidence-img:hover {
  border-color: var(--color-primary-400);
}

/* 操作日志 */
.log-timeline {
  padding-left: var(--space-sm);
}

.log-item {
  display: flex;
  gap: var(--space-md);
  padding-bottom: var(--space-md);
  position: relative;
}

.log-item:not(:last-child)::after {
  content: '';
  position: absolute;
  left: 4px;
  top: 16px;
  bottom: 0;
  width: 2px;
  background: var(--color-border);
}

.log-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-primary-500);
  flex-shrink: 0;
  margin-top: 5px;
}

.log-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}

.log-action {
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
}

.log-time {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}
</style>
