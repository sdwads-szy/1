<template>
  <div class="page-container payment-page">
    <div class="payment-container">
      <!-- 加载态 -->
      <div v-if="loading" class="loading-state flex-center">
        <div class="loading-card card">
          <el-icon class="is-loading loading-spinner" :size="36"><Loading /></el-icon>
          <p>加载支付信息...</p>
        </div>
      </div>

      <!-- 错误态 -->
      <div v-else-if="error" class="error-state">
        <div class="card">
          <el-result icon="error" title="加载失败" :sub-title="error">
            <template #extra>
              <el-button type="primary" @click="fetchPaymentInfo">重新加载</el-button>
              <el-button @click="goBack">返回</el-button>
            </template>
          </el-result>
        </div>
      </div>

      <!-- 主体内容 -->
      <template v-else>
        <!-- 支付卡片 -->
        <div class="payment-card card">
          <!-- 头部 -->
          <div class="payment-header">
            <h1 class="payment-title">确认支付</h1>
            <div class="order-no">订单编号：{{ orderId }}</div>
          </div>

          <!-- 金额展示 -->
          <div class="amount-section">
            <div class="amount-label">支付金额</div>
            <div class="amount-value">
              <span class="currency">¥</span>
              {{ displayAmount }}
            </div>
          </div>

          <!-- 支付方式选择（支付前） -->
          <div v-if="!paying && !polling" class="method-section">
            <div class="section-label">选择支付方式</div>
            <div class="method-grid">
              <div
                class="method-item"
                :class="{ active: channel === 'wxpay' }"
                @click="channel = 'wxpay'"
              >
                <div class="method-icon wxpay-icon">
                  <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
                    <path d="M8.5 11a1 1 0 1 0 0-2 1 1 0 0 0 0 2zm4 0a1 1 0 1 0 0-2 1 1 0 0 0 0 2zm-8 2a1 1 0 1 0 0 2 1 1 0 0 0 0-2zm4 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2zm4 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2zm-7-4a9 9 0 1 1 0 6H2v-1.5L5 14l-.001-4L2 10.5V9h3.5z"/>
                  </svg>
                </div>
                <span>微信支付</span>
                <el-icon v-if="channel === 'wxpay'" class="check-icon" color="#f59e0b"><CircleCheckFilled /></el-icon>
              </div>
              <div
                class="method-item"
                :class="{ active: channel === 'alipay' }"
                @click="channel = 'alipay'"
              >
                <div class="method-icon alipay-icon">
                  <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
                    <path d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm4.5 7h-3.2c-.6 0-1 .4-1 1s.4 1 1 1h1.4c1.3 0 2.3 1 2.3 2.3 0 1.2-1 2.2-2.3 2.2H12v1.5h-1.5V15.5H9v-1.5h1.5V11H9V9.5h1.5V8H12v1.5h1.7c1.3 0 2.3 1 2.3 2.3 0 .6-.2 1.1-.6 1.4.6.4 1 1 1 1.8 0 1.3-1.1 2.5-2.5 2.5H9V16h4.9c.6 0 1-.4 1-1s-.4-1-1-1h-1.7C10.9 14 9 12.9 9 10.8 9 9.1 10.3 8 12 8h4.5v1z"/>
                  </svg>
                </div>
                <span>支付宝</span>
                <el-icon v-if="channel === 'alipay'" class="check-icon" color="#f59e0b"><CircleCheckFilled /></el-icon>
              </div>
            </div>
          </div>

          <!-- 二维码区域 -->
          <div v-if="qrcodeUrl" class="qrcode-section">
            <div class="qrcode-wrapper">
              <div class="qrcode-frame">
                <img :src="qrcodeUrl" alt="支付二维码" class="qrcode-img" />
              </div>
              <div class="qrcode-tips">
                <p class="tips-title">请使用{{ channel === 'wxpay' ? '微信' : '支付宝' }}扫一扫</p>
                <p class="countdown-text">
                  <el-icon><Clock /></el-icon>
                  二维码有效期剩余 {{ formatCountdown }}
                </p>
              </div>
            </div>
          </div>

          <!-- 轮询指示器 -->
          <div v-if="polling && !qrcodeUrl" class="polling-section flex-center">
            <el-icon class="is-loading polling-icon" :size="24"><Loading /></el-icon>
            <span>正在拉起支付...</span>
          </div>

          <!-- 操作按钮 -->
          <div class="action-section">
            <el-button
              v-if="!paying && !polling"
              type="primary"
              size="large"
              class="pay-btn"
              :loading="submitting"
              :disabled="!channel"
              @click="handlePay"
            >
              确认支付 ¥{{ displayAmount }}
            </el-button>
            <el-button
              v-if="qrcodeUrl || polling"
              size="large"
              class="cancel-btn"
              @click="handleCancel"
            >
              取消支付
            </el-button>
          </div>
        </div>

        <!-- 支付说明 -->
        <div class="payment-info card">
          <h3 class="info-title">
            <el-icon><InfoFilled /></el-icon>
            支付说明
          </h3>
          <ul class="info-list">
            <li>请在 <strong>{{ timeoutMinutes }} 分钟</strong>内完成支付，超时订单将自动取消</li>
            <li>支付成功后请勿关闭页面，系统将自动跳转</li>
            <li>如遇支付问题，请联系客服获取帮助</li>
          </ul>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
// Payment 页面：支付方式选择、扫码支付、状态轮询
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Loading, CircleCheckFilled, Clock, InfoFilled } from '@element-plus/icons-vue';
import { payPayment, getPaymentStatus } from '@/api/payment';

const route = useRoute();
const router = useRouter();

// 路由参数
const orderId = ref(route.params.orderId);
const queryAmount = route.query.amount ? parseFloat(route.query.amount) : null;

// 状态
const amount = ref(queryAmount || 0);
const channel = ref('wxpay');
const loading = ref(true);
const error = ref('');
const submitting = ref(false);
const paying = ref(false);
const qrcodeUrl = ref('');
const polling = ref(false);
const countdown = ref(300);

let pollTimer = null;
let countdownTimer = null;
const timeoutMinutes = 5;
const POLL_INTERVAL = 3000;
const MAX_POLL_FAILS = 5;

// 计算属性
const displayAmount = computed(() => {
  const num = Number(amount.value);
  return Number.isFinite(num) ? num.toFixed(2) : '0.00';
});

const formatCountdown = computed(() => {
  const m = Math.floor(countdown.value / 60);
  const s = countdown.value % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
});

// 获取支付信息
async function fetchPaymentInfo() {
  loading.value = true;
  error.value = '';
  try {
    const res = await getPaymentStatus(orderId.value);
    if (res.amount != null) {
      amount.value = parseFloat(res.amount);
    }
    // 已支付 → 直接跳结果页
    if (res.status === 'paid') {
      router.replace({
        name: 'PaymentResult',
        params: { orderId: orderId.value },
        query: { status: 'success' }
      });
      return;
    }
    // 已关闭 → 直接跳结果页
    if (res.status === 'closed') {
      router.replace({
        name: 'PaymentResult',
        params: { orderId: orderId.value },
        query: { status: 'failed' }
      });
      return;
    }
  } catch (e) {
    error.value = e?.response?.data?.message || '获取支付信息失败，请稍后重试';
  } finally {
    loading.value = false;
  }
}

// 发起支付
async function handlePay() {
  if (!channel.value) {
    ElMessage.warning('请选择支付方式');
    return;
  }
  submitting.value = true;
  try {
    const res = await payPayment(orderId.value, { channel: channel.value });
    paying.value = true;

    if (res.qrCode) {
      qrcodeUrl.value = res.qrCode;
      startPolling();
      startCountdown();
    } else if (res.payUrl) {
      // 跳转支付链接场景
      qrcodeUrl.value = res.payUrl;
      startPolling();
      startCountdown();
      // 新窗口打开支付链接
      window.open(res.payUrl, '_blank');
    } else {
      // 无二维码无链接，直接开始轮询
      startPolling();
      startCountdown();
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || '发起支付失败，请重试');
  } finally {
    submitting.value = false;
  }
}

// 开始轮询支付状态
function startPolling() {
  polling.value = true;
  let pollFailCount = 0;

  pollTimer = setInterval(async () => {
    try {
      const res = await getPaymentStatus(orderId.value);
      if (res.status === 'paid') {
        stopPolling();
        ElMessage.success('支付成功！');
        setTimeout(() => {
          router.replace({
            name: 'PaymentResult',
            params: { orderId: orderId.value },
            query: { status: 'success' }
          });
        }, 600);
      } else if (res.status === 'closed') {
        stopPolling();
        ElMessage.error('支付已关闭');
        router.replace({
          name: 'PaymentResult',
          params: { orderId: orderId.value },
          query: { status: 'failed' }
        });
      }
      pollFailCount = 0;
    } catch {
      pollFailCount++;
      if (pollFailCount >= MAX_POLL_FAILS) {
        stopPolling();
        ElMessage.warning('支付状态查询异常，请刷新页面后查看订单状态');
      }
    }
  }, POLL_INTERVAL);
}

// 开始倒计时
function startCountdown() {
  countdownTimer = setInterval(() => {
    countdown.value--;
    if (countdown.value <= 0) {
      stopPolling();
      ElMessage.warning('支付已超时');
      router.replace({
        name: 'PaymentResult',
        params: { orderId: orderId.value },
        query: { status: 'timeout' }
      });
    }
  }, 1000);
}

// 停止轮询与倒计时
function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
  if (countdownTimer) {
    clearInterval(countdownTimer);
    countdownTimer = null;
  }
  polling.value = false;
}

// 取消支付
async function handleCancel() {
  try {
    await ElMessageBox.confirm('确定要取消本次支付吗？', '取消支付', {
      confirmButtonText: '确定取消',
      cancelButtonText: '继续支付',
      type: 'warning'
    });
    stopPolling();
    router.replace({
      name: 'PaymentResult',
      params: { orderId: orderId.value },
      query: { status: 'cancelled' }
    });
  } catch {
    // 用户点击「继续支付」，不做任何操作
  }
}

// 返回上一页
function goBack() {
  router.back();
}

onMounted(() => {
  fetchPaymentInfo();
});

onUnmounted(() => {
  stopPolling();
});
</script>

<style scoped>
.payment-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #fff7ed 0%, #f5f5f7 30%);
}

.payment-container {
  max-width: 520px;
  margin: 0 auto;
  padding: var(--app-space-2xl) var(--app-space-base);
}

/* 加载态 */
.loading-card {
  padding: var(--app-space-3xl);
  text-align: center;
  color: var(--app-text-secondary);
}

.loading-spinner {
  color: #f59e0b;
  margin-bottom: var(--app-space-md);
}

/* 支付卡片 */
.payment-card {
  padding: var(--app-space-2xl);
}

.payment-header {
  text-align: center;
  margin-bottom: var(--app-space-xl);
}

.payment-title {
  font-size: var(--app-font-3xl);
  font-weight: 600;
  color: var(--app-text-primary);
  margin: 0 0 var(--app-space-sm);
}

.order-no {
  font-size: var(--app-font-sm);
  color: var(--app-text-secondary);
}

/* 金额展示 */
.amount-section {
  text-align: center;
  padding: var(--app-space-xl) 0;
  margin-bottom: var(--app-space-xl);
  border-bottom: 1px solid var(--app-border-light);
}

.amount-label {
  font-size: var(--app-font-sm);
  color: var(--app-text-secondary);
  margin-bottom: var(--app-space-sm);
}

.amount-value {
  font-size: 2.5rem;
  font-weight: 700;
  color: #ea580c;
  letter-spacing: -0.02em;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.currency {
  font-size: 1.5rem;
  font-weight: 500;
  vertical-align: top;
  margin-right: 2px;
}

/* 支付方式 */
.method-section {
  margin-bottom: var(--app-space-xl);
}

.section-label {
  font-size: var(--app-font-base);
  font-weight: 500;
  color: var(--app-text-primary);
  margin-bottom: var(--app-space-md);
}

.method-grid {
  display: flex;
  gap: var(--app-space-md);
}

.method-item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--app-space-sm);
  padding: var(--app-space-base);
  border: 2px solid var(--app-border-base);
  border-radius: var(--app-radius-base);
  cursor: pointer;
  transition: all 0.2s var(--app-ease-standard);
  position: relative;
}

.method-item:hover {
  border-color: #fbbf24;
  background: #fffbeb;
}

.method-item.active {
  border-color: #f59e0b;
  background: #fffbeb;
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.12);
}

.method-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--app-radius-base);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.wxpay-icon {
  background: #07c160;
  color: #fff;
  font-size: var(--app-font-sm);
  font-weight: 600;
}

.alipay-icon {
  background: #1677ff;
  color: #fff;
  font-size: var(--app-font-sm);
  font-weight: 600;
}

.check-icon {
  position: absolute;
  top: -6px;
  right: -6px;
  background: #fff;
  border-radius: 50%;
}

/* 二维码区域 */
.qrcode-section {
  text-align: center;
  margin-bottom: var(--app-space-xl);
}

.qrcode-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.qrcode-frame {
  width: 200px;
  height: 200px;
  border: 2px solid #fbbf24;
  border-radius: var(--app-radius-md);
  overflow: hidden;
  padding: var(--app-space-sm);
  background: #fff;
  box-shadow: 0 0 20px rgba(245, 158, 11, 0.15);
}

.qrcode-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.qrcode-tips {
  margin-top: var(--app-space-base);
}

.tips-title {
  font-size: var(--app-font-base);
  font-weight: 500;
  color: var(--app-text-primary);
  margin: 0 0 var(--app-space-xs);
}

.countdown-text {
  font-size: var(--app-font-sm);
  color: #ea580c;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin: 0;
}

/* 轮询指示 */
.polling-section {
  padding: var(--app-space-xl);
  color: var(--app-text-secondary);
  gap: var(--app-space-sm);
}

.polling-icon {
  color: #f59e0b;
}

/* 操作按钮 */
.action-section {
  display: flex;
  justify-content: center;
  gap: var(--app-space-md);
}

.pay-btn {
  width: 100%;
  height: 48px;
  font-size: var(--app-font-lg);
  font-weight: 600;
  border-radius: var(--app-radius-base);
  background: linear-gradient(135deg, #f59e0b 0%, #ea580c 100%);
  border: none;
}

.pay-btn:hover {
  background: linear-gradient(135deg, #fbbf24 0%, #f97316 100%);
}

.pay-btn:active {
  background: linear-gradient(135deg, #d97706 0%, #c2410c 100%);
}

.pay-btn.is-disabled {
  background: #f3f4f6;
  color: var(--app-text-disabled);
}

.cancel-btn {
  width: 100%;
  height: 48px;
  font-size: var(--app-font-base);
  border-radius: var(--app-radius-base);
}

/* 支付说明 */
.payment-info {
  margin-top: var(--app-space-lg);
  padding: var(--app-space-xl);
}

.info-title {
  display: flex;
  align-items: center;
  gap: var(--app-space-xs);
  font-size: var(--app-font-md);
  font-weight: 500;
  color: var(--app-text-primary);
  margin: 0 0 var(--app-space-md);
}

.info-list {
  margin: 0;
  padding-left: var(--app-space-lg);
  font-size: var(--app-font-sm);
  color: var(--app-text-secondary);
  line-height: 1.8;
}

.info-list li {
  margin-bottom: var(--app-space-xs);
}

.info-list strong {
  color: #ea580c;
}

/* 错误态 */
.error-state {
  padding-top: var(--app-space-4xl);
}
</style>
