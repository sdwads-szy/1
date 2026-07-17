<template>
  <div class="pay-page">
    <!-- 加载 -->
    <template v-if="pageLoading">
      <div class="pay-card">
        <div class="skeleton-line skeleton-title"></div>
        <div class="skeleton-line"></div>
        <div class="skeleton-line skeleton-short"></div>
      </div>
    </template>

    <!-- 异常：缺少订单号 -->
    <template v-else-if="!orderNo">
      <div class="pay-card empty-state">
        <el-icon :size="48" color="var(--color-text-tertiary)"><WarningFilled /></el-icon>
        <h2 class="empty-title">缺少订单号</h2>
        <p class="empty-desc">未找到有效的订单号，请从下单页重新进入</p>
        <el-button type="primary" @click="goShopping">去逛逛</el-button>
      </div>
    </template>

    <!-- 支付成功 -->
    <template v-else-if="payStatus === 'success'">
      <div class="pay-card result-card">
        <div class="result-icon result-icon--success">
          <el-icon :size="48"><CircleCheckFilled /></el-icon>
        </div>
        <h2 class="result-title">支付成功</h2>
        <p class="result-order">订单号：{{ orderNo }}</p>
        <p v-if="orderAmount" class="result-amount">
          支付金额：<span class="amount-value">¥{{ orderAmount }}</span>
        </p>
        <div class="result-actions">
          <el-button type="primary" @click="goOrderDetail">查看订单详情</el-button>
          <el-button @click="goOrdersList">查看我的订单</el-button>
        </div>
      </div>
    </template>

    <!-- 支付失败 -->
    <template v-else-if="payStatus === 'failed'">
      <div class="pay-card result-card">
        <div class="result-icon result-icon--error">
          <el-icon :size="48"><CircleCloseFilled /></el-icon>
        </div>
        <h2 class="result-title">支付失败</h2>
        <p class="result-desc">订单 {{ orderNo }} 支付未成功，请重试</p>
        <div class="result-actions">
          <el-button type="primary" @click="retryPayment">重新支付</el-button>
          <el-button @click="goOrdersList">查看我的订单</el-button>
        </div>
      </div>
    </template>

    <!-- 支付超时 -->
    <template v-else-if="payStatus === 'timeout'">
      <div class="pay-card result-card">
        <div class="result-icon result-icon--warning">
          <el-icon :size="48"><Clock /></el-icon>
        </div>
        <h2 class="result-title">支付结果确认中</h2>
        <p class="result-desc">订单 {{ orderNo }} 支付状态确认超时，请稍后在订单列表中查看</p>
        <div class="result-actions">
          <el-button type="primary" @click="goOrdersList">查看我的订单</el-button>
          <el-button @click="retryPayment">重新支付</el-button>
        </div>
      </div>
    </template>

    <!-- 主流程：选择支付方式 / 支付中 -->
    <template v-else>
      <div class="pay-card">
        <!-- 订单摘要 -->
        <div class="order-summary">
          <p class="order-summary-label">订单号</p>
          <p class="order-summary-no">{{ orderNo }}</p>
          <p v-if="orderAmount" class="order-summary-amount">
            应付金额：<span class="amount-value">¥{{ orderAmount }}</span>
          </p>
        </div>
        <el-button text @click="router.push({name:'Checkout'})">返回结算页</el-button>

        <el-divider />

        <!-- 支付方式选择 -->
        <div v-if="payStep === 'select'" class="channel-section">
          <h4 class="channel-title">选择支付方式</h4>
          <div class="channel-list">
            <label
              v-for="ch in channels"
              :key="ch.value"
              class="channel-card"
              :class="{ 'channel-card--selected': selectedChannel === ch.value }"
            >
              <el-radio v-model="selectedChannel" :value="ch.value" class="channel-radio">
                <span class="channel-icon">{{ ch.icon }}</span>
                <span class="channel-label">{{ ch.label }}</span>
              </el-radio>
            </label>
          </div>

          <!-- mock 提示 -->
          <el-alert
            v-if="mockHint"
            :title="mockHint"
            type="info"
            :closable="false"
            show-icon
            style="margin-top: var(--space-md)"
          />

          <div class="channel-actions">
            <el-button
              type="primary"
              size="large"
              :loading="paying"
              :disabled="!selectedChannel || paying"
              @click="startPayment"
            >
              {{ paying ? '支付中...' : '确认支付' }}
            </el-button>
            <el-button size="large" @click="goOrdersList">取消</el-button>
          </div>
        </div>

        <!-- 支付中 -->
        <div v-else-if="payStep === 'paying'" class="paying-section">
          <div class="paying-spinner">
            <el-icon :size="48" class="is-loading" color="var(--color-primary-500)"><Loading /></el-icon>
          </div>
          <h4 class="paying-title">正在支付中...</h4>
          <p class="paying-desc">请稍候，正在确认支付结果</p>
          <div class="paying-progress">
            <el-progress
              :percentage="pollProgress"
              :stroke-width="6"
              :show-text="false"
              color="var(--color-primary-500)"
            />
            <p class="paying-progress-text">已等待 {{ pollSeconds }} 秒 / 最长 30 秒</p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Loading, CircleCheckFilled, CircleCloseFilled, Clock, WarningFilled } from '@element-plus/icons-vue'
import { initiatePayment, getPaymentStatus } from '@/api/payments'
import { getOrderDetail } from '@/api/orders'

const route = useRoute()
const router = useRouter()

// nav_checkout_pay targetRead: source=route.query
const orderNo = route.query.orderNo || ''

// ===== 状态 =====
const pageLoading = ref(true)
const orderAmount = ref('')
const payStep = ref('select') // select | paying
const payStatus = ref(null) // null | success | failed | timeout
const paying = ref(false)
const selectedChannel = ref('')
const mockHint = ref('')
const orderId = ref(null)
const pollSeconds = ref(0)
const MAX_POLL_SECONDS = 30
const POLL_INTERVAL = 2000
let pollTimer = null

// ===== 支付渠道 =====
const channels = [
  { value: 'wechat', label: '微信支付', icon: '💳' },
  { value: 'alipay', label: '支付宝', icon: '📱' },
  { value: 'unionpay', label: '银联支付', icon: '🏦' }
]

// ===== 计算 =====
const pollProgress = computed(() => {
  return Math.min(Math.round((pollSeconds.value / MAX_POLL_SECONDS) * 100), 100)
})

// ===== 方法 =====
function formatPrice(price) {
  const num = parseFloat(price)
  if (isNaN(num)) return '0.00'
  return num.toFixed(2)
}

function goShopping() {
  router.push({ name: 'Home' })
}

// nav_pay_orders_detail: trigger=click, passBy=params, code: router.push({name:'OrderDetail', params:{orderNo}})
function goOrderDetail() {
  if (orderNo) {
    router.push({ name: 'OrderDetail', params: { orderNo } })
  }
}

// nav_pay_orders_list: trigger=click, passBy=none, code: router.push({name:'OrderList'})
function goOrdersList() {
  router.push({ name: 'OrderList' })
}

function retryPayment() {
  payStatus.value = null
  payStep.value = 'select'
  pollSeconds.value = 0
  clearPollTimer()
}

function clearPollTimer() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function loadOrderInfo() {
  if (!orderNo) {
    pageLoading.value = false
    return
  }
  try {
    // 尝试通过 orderNo 获取订单信息（这里用列表接口带筛选简化）
    // 如果后端支持按 orderNo 查详情，可在此调用
    // 暂时仅依赖 orderNo
    pageLoading.value = false
  } catch {
    pageLoading.value = false
  }
}

async function startPayment() {
  if (!selectedChannel.value) {
    ElMessage.warning('请选择支付方式')
    return
  }

  paying.value = true
  try {
    const res = await initiatePayment({
      orderNo,
      channel: selectedChannel.value
    })

    // 检查 mock 提示
    if (res.data && res.data.mockHint) {
      mockHint.value = res.data.mockHint
      ElMessage.info(res.data.mockHint)
    }

    // 进入轮询阶段
    payStep.value = 'paying'
    startPolling()
  } catch (e) {
    const status = e?.response?.status
    const msg = e?.response?.data?.message || e?.message || '支付发起失败'

    if (status === 403) {
      ElMessage.error('无权操作此订单')
    } else if (status === 404) {
      ElMessage.error('订单不存在')
    } else if (status === 408) {
      ElMessage.warning('订单已超时，请重新下单')
      router.push({ name: 'OrderList' })
    } else if (status === 409) {
      ElMessage.warning('订单已支付')
      // 直接查状态
      payStep.value = 'paying'
      startPolling()
    } else {
      ElMessage.error(msg)
    }
  } finally {
    paying.value = false
  }
}

function startPolling() {
  pollSeconds.value = 0
  clearPollTimer()

  // 立即查一次
  checkPaymentStatus()

  pollTimer = setInterval(() => {
    pollSeconds.value += 2

    if (pollSeconds.value >= MAX_POLL_SECONDS) {
      clearPollTimer()
      payStatus.value = 'timeout'
      payStep.value = 'select'
      return
    }

    checkPaymentStatus()
  }, POLL_INTERVAL)
}

async function checkPaymentStatus() {
  try {
    const res = await getPaymentStatus(orderNo)
    const status = res.data?.status

    if (status === 'success') {
      clearPollTimer()
      payStatus.value = 'success'
      payStep.value = 'select'
      orderId.value = res.data?.orderId || null
      ElMessage.success('支付成功')
    } else if (status === 'failed') {
      clearPollTimer()
      payStatus.value = 'failed'
      payStep.value = 'select'
    }
    // pending: 继续轮询
  } catch {
    // 轮询失败不中断，继续
  }
}

// ===== 生命周期 =====
onMounted(() => {
  loadOrderInfo()
})

onUnmounted(() => {
  clearPollTimer()
})
</script>

<style scoped>
.pay-page {
  max-width: 560px;
  margin: 0 auto;
  padding: var(--space-xl) var(--space-lg);
  min-height: calc(100vh - 56px);
}

.pay-card {
  background: var(--color-bg-base);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-xl);
}

/* 订单摘要 */
.order-summary {
  text-align: center;
  padding-bottom: var(--space-sm);
}

.order-summary-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-xs);
}

.order-summary-no {
  font-size: var(--font-size-md);
  color: var(--color-text-primary);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.5px;
  margin: 0 0 var(--space-xs);
  word-break: break-all;
}

.order-summary-amount {
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  margin: var(--space-sm) 0 0;
}

.amount-value {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--color-error);
  font-variant-numeric: tabular-nums;
}

/* 支付方式 */
.channel-section {
  padding-top: var(--space-sm);
}

.channel-title {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-md);
}

.channel-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.channel-card {
  padding: var(--space-md);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-smooth),
              background-color var(--duration-fast) var(--ease-smooth);
}

.channel-card:hover {
  border-color: var(--color-primary-300);
  background: var(--color-primary-50);
}

.channel-card--selected {
  border-color: var(--color-primary-500);
  background: var(--color-primary-50);
}

.channel-radio {
  width: 100%;
}

.channel-icon {
  margin-right: var(--space-sm);
  font-size: var(--font-size-lg);
}

.channel-label {
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
}

.channel-actions {
  display: flex;
  gap: var(--space-md);
  margin-top: var(--space-xl);
  justify-content: center;
}

/* 支付中 */
.paying-section {
  text-align: center;
  padding: var(--space-xl) 0;
}

.paying-spinner {
  margin-bottom: var(--space-lg);
}

.paying-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-sm);
}

.paying-desc {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-xl);
}

.paying-progress {
  max-width: 320px;
  margin: 0 auto;
}

.paying-progress-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  margin-top: var(--space-sm);
}

/* 结果页 */
.result-card {
  text-align: center;
  padding: var(--space-2xl) var(--space-xl);
}

.result-icon {
  margin-bottom: var(--space-lg);
}

.result-icon--success {
  color: var(--color-success);
}

.result-icon--error {
  color: var(--color-error);
}

.result-icon--warning {
  color: var(--color-warning);
}

.result-title {
  font-size: var(--font-size-xl);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-sm);
}

.result-order {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.5px;
  margin: 0 0 var(--space-xs);
}

.result-amount {
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-xl);
}

.result-desc {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-xl);
}

.result-actions {
  display: flex;
  gap: var(--space-md);
  justify-content: center;
  flex-wrap: wrap;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: var(--space-3xl) var(--space-lg);
}

.empty-title {
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
  margin: var(--space-lg) 0 var(--space-sm);
  font-weight: 600;
}

.empty-desc {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-xl);
}

/* 骨架屏 */
.skeleton-line {
  height: 14px;
  background: var(--color-bg-page);
  border-radius: 4px;
  margin-bottom: var(--space-sm);
  animation: skeleton-shimmer 1.8s infinite;
  background: linear-gradient(
    90deg,
    var(--color-bg-page) 25%,
    var(--color-primary-50) 50%,
    var(--color-bg-page) 75%
  );
  background-size: 200% 100%;
}

.skeleton-title {
  width: 30%;
  height: 18px;
}

.skeleton-short {
  width: 60%;
}

@keyframes skeleton-shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

/* 移动端适配 */
@media (max-width: 768px) {
  .pay-page {
    padding: var(--space-sm);
  }

  .pay-card {
    padding: var(--space-lg);
  }

  .channel-actions {
    flex-direction: column;
  }

  .channel-actions .el-button {
    width: 100%;
  }

  .result-actions {
    flex-direction: column;
  }

  .result-actions .el-button {
    width: 100%;
  }
}
</style>
