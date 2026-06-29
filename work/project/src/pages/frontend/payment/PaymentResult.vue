<template>
  <div class="page-container result-page">
    <div class="result-container">
      <div class="result-card card">
        <!-- 支付成功 -->
        <template v-if="status === 'success'">
          <div class="result-icon-wrapper success">
            <div class="result-icon-circle">
              <svg viewBox="0 0 52 52" class="checkmark" width="52" height="52">
                <circle class="checkmark-circle" cx="26" cy="26" r="25" fill="none" />
                <path class="checkmark-check" fill="none" d="M14 27l7 7 16-16" />
              </svg>
            </div>
          </div>
          <h1 class="result-title success-text">支付成功</h1>
          <p class="result-desc">您已成功支付，商家将尽快为您发货</p>
          <div class="result-info">
            <div class="info-row">
              <span class="info-label">订单编号</span>
              <span class="info-value">{{ orderId }}</span>
            </div>
            <div class="info-row" v-if="paidAt">
              <span class="info-label">支付时间</span>
              <span class="info-value">{{ paidAt }}</span>
            </div>
          </div>
          <div class="result-actions">
            <el-button type="primary" size="large" class="action-btn primary-btn" @click="goOrderDetail">
              查看订单
            </el-button>
            <el-button size="large" class="action-btn" @click="goHome">返回首页</el-button>
          </div>
        </template>

        <!-- 支付处理中 -->
        <template v-else-if="status === 'processing'">
          <div class="result-icon-wrapper processing">
            <div class="result-icon-circle">
              <el-icon :size="36" class="is-loading processing-spin"><Loading /></el-icon>
            </div>
          </div>
          <h1 class="result-title">支付处理中</h1>
          <p class="result-desc">您的支付正在处理，请稍候片刻</p>
          <div class="result-info">
            <div class="info-row">
              <span class="info-label">订单编号</span>
              <span class="info-value">{{ orderId }}</span>
            </div>
          </div>
          <div class="result-actions">
            <el-button type="primary" size="large" class="action-btn primary-btn" :loading="checking" @click="checkAgain">
              刷新支付状态
            </el-button>
            <el-button size="large" class="action-btn" @click="goHome">返回首页</el-button>
          </div>
        </template>

        <!-- 支付失败 / 超时 / 取消 -->
        <template v-else>
          <div class="result-icon-wrapper fail">
            <div class="result-icon-circle">
              <svg viewBox="0 0 52 52" class="crossmark" width="52" height="52">
                <circle class="crossmark-circle" cx="26" cy="26" r="25" fill="none" />
                <path class="crossmark-cross" fill="none" d="M16 16l20 20M36 16l-20 20" />
              </svg>
            </div>
          </div>
          <h1 class="result-title fail-text">{{ failTitle }}</h1>
          <p class="result-desc">{{ failDesc }}</p>
          <div class="result-info">
            <div class="info-row">
              <span class="info-label">订单编号</span>
              <span class="info-value">{{ orderId }}</span>
            </div>
          </div>
          <div class="result-actions">
            <el-button
              v-if="showRetry"
              type="primary"
              size="large"
              class="action-btn primary-btn"
              @click="retryPay"
            >
              重新支付
            </el-button>
            <el-button size="large" class="action-btn" @click="goOrderDetail">查看订单</el-button>
            <el-button size="large" class="action-btn" @click="goHome">返回首页</el-button>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
// PaymentResult 页面：支付结果展示（成功/失败/超时/取消/处理中）
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Loading } from '@element-plus/icons-vue';
import { getPaymentStatus } from '@/api/payment';

const route = useRoute();
const router = useRouter();

// 路由参数
const orderId = ref(route.params.orderId);
const status = ref(route.query.status || 'processing');
const paidAt = ref(route.query.paidAt || '');
const checking = ref(false);

// 失败标题
const failTitle = computed(() => {
  const titles = {
    timeout: '支付超时',
    failed: '支付失败',
    cancelled: '支付已取消'
  };
  return titles[status.value] || '支付未完成';
});

// 失败描述
const failDesc = computed(() => {
  const descs = {
    timeout: '支付超时，该订单已自动取消。如需购买请重新下单',
    failed: '支付未成功，请重试或选择其他支付方式',
    cancelled: '您已取消本次支付，订单将保留一段时间'
  };
  return descs[status.value] || '支付未完成，请检查支付状态';
});

// 是否显示重试按钮
const showRetry = computed(() => ['timeout', 'failed'].includes(status.value));

// 刷新支付状态
async function checkAgain() {
  checking.value = true;
  try {
    const res = await getPaymentStatus(orderId.value);
    if (res.status === 'paid') {
      status.value = 'success';
      if (res.paidAt) paidAt.value = res.paidAt;
    } else if (res.status === 'closed') {
      status.value = 'failed';
    } else if (res.status === 'pending') {
      // 仍在处理中，维持当前状态
    }
  } catch {
    // 保持当前状态不变
  } finally {
    checking.value = false;
  }
}

// 重新支付
function retryPay() {
  router.replace({ name: 'Payment', params: { orderId: orderId.value } });
}

// 查看订单
function goOrderDetail() {
  router.push({ name: 'OrderDetail', params: { id: orderId.value } });
}

// 返回首页
function goHome() {
  router.push({ name: 'Home' });
}

// 支付成功时获取支付时间
onMounted(async () => {
  if (status.value === 'success' && !paidAt.value) {
    try {
      const res = await getPaymentStatus(orderId.value);
      if (res.paidAt) paidAt.value = res.paidAt;
    } catch {
      // 忽略
    }
  }
});
</script>

<style scoped>
.result-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #fff7ed 0%, #f5f5f7 40%);
}

.result-container {
  max-width: 480px;
  margin: 0 auto;
  padding: var(--app-space-4xl) var(--app-space-base);
}

.result-card {
  padding: var(--app-space-3xl) var(--app-space-2xl);
  text-align: center;
}

/* 图标区域 */
.result-icon-wrapper {
  margin-bottom: var(--app-space-xl);
}

.result-icon-circle {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
}

.result-icon-wrapper.success .result-icon-circle {
  background: #f0fdf4;
}

.result-icon-wrapper.processing .result-icon-circle {
  background: #fffbeb;
}

.result-icon-wrapper.fail .result-icon-circle {
  background: #fef2f2;
}

/* SVG 动画：对勾 */
.checkmark-circle {
  stroke: #22c55e;
  stroke-width: 2.5;
  stroke-dasharray: 166;
  stroke-dashoffset: 166;
  animation: stroke-circle 0.5s var(--app-ease-decelerate) forwards;
}

.checkmark-check {
  stroke: #22c55e;
  stroke-width: 2.5;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 48;
  stroke-dashoffset: 48;
  animation: stroke-check 0.3s var(--app-ease-decelerate) 0.3s forwards;
}

@keyframes stroke-circle {
  to { stroke-dashoffset: 0; }
}

@keyframes stroke-check {
  to { stroke-dashoffset: 0; }
}

/* SVG 动画：叉号 */
.crossmark-circle {
  stroke: #ef4444;
  stroke-width: 2.5;
  stroke-dasharray: 166;
  stroke-dashoffset: 166;
  animation: stroke-circle 0.5s var(--app-ease-decelerate) forwards;
}

.crossmark-cross {
  stroke: #ef4444;
  stroke-width: 2.5;
  stroke-linecap: round;
  stroke-dasharray: 48;
  stroke-dashoffset: 48;
  animation: stroke-check 0.3s var(--app-ease-decelerate) 0.3s forwards;
}

/* 处理中旋转 */
.processing-spin {
  color: #f59e0b;
}

/* 标题 */
.result-title {
  font-size: var(--app-font-3xl);
  font-weight: 600;
  color: var(--app-text-primary);
  margin: 0 0 var(--app-space-sm);
}

.success-text {
  color: #16a34a;
}

.fail-text {
  color: #dc2626;
}

.result-desc {
  font-size: var(--app-font-base);
  color: var(--app-text-secondary);
  margin: 0 0 var(--app-space-xl);
  line-height: 1.6;
}

/* 订单信息 */
.result-info {
  background: #f9fafb;
  border-radius: var(--app-radius-base);
  padding: var(--app-space-base) var(--app-space-lg);
  margin-bottom: var(--app-space-xl);
  text-align: left;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--app-space-sm) 0;
  font-size: var(--app-font-sm);
}

.info-row + .info-row {
  border-top: 1px solid var(--app-border-light);
}

.info-label {
  color: var(--app-text-secondary);
}

.info-value {
  color: var(--app-text-primary);
  font-weight: 500;
}

/* 操作按钮 */
.result-actions {
  display: flex;
  flex-direction: column;
  gap: var(--app-space-sm);
}

.action-btn {
  width: 100%;
  height: 44px;
  font-size: var(--app-font-base);
  border-radius: var(--app-radius-base);
}

.primary-btn {
  background: linear-gradient(135deg, #f59e0b 0%, #ea580c 100%);
  border: none;
  color: #fff;
  font-weight: 500;
}

.primary-btn:hover {
  background: linear-gradient(135deg, #fbbf24 0%, #f97316 100%);
}

.primary-btn:active {
  background: linear-gradient(135deg, #d97706 0%, #c2410c 100%);
}
</style>
