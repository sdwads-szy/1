<template>
  <div class="admin-order-detail">
    <!-- 面包屑 -->
    <div class="breadcrumb-bar">
      <el-breadcrumb separator=">">
        <el-breadcrumb-item :to="{ name: 'AdminOrderList' }">订单管理</el-breadcrumb-item>
        <el-breadcrumb-item>订单详情</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- 加载态 -->
    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="12" animated />
    </div>

    <!-- 错误态 -->
    <div v-else-if="errorMsg" class="error-state">
      <el-result icon="error" :title="errorMsg" :sub-title="'订单ID: ' + orderId">
        <template #extra>
          <el-button type="primary" @click="fetchDetail">重新加载</el-button>
          <el-button @click="goBack">返回列表</el-button>
        </template>
      </el-result>
    </div>

    <!-- 内容区 -->
    <template v-else-if="order">
      <!-- 状态横幅 -->
      <div class="status-banner" :class="'status--' + order.status">
        <div class="status-banner-left">
          <span class="status-dot"></span>
          <span class="status-text">{{ statusLabel(order.status) }}</span>
          <span v-if="isDisputed" class="dispute-tag">
            <el-icon><WarningFilled /></el-icon>
            纠纷订单
          </span>
        </div>
        <div class="status-banner-right">
          <span class="order-no-label">订单号</span>
          <strong class="order-no-value">{{ order.order_no }}</strong>
        </div>
      </div>

      <!-- 基本信息 & 金额信息 -->
      <div class="info-grid">
        <div class="info-card">
          <h3 class="card-title">
            <el-icon><Document /></el-icon>
            基本信息
          </h3>
          <div class="info-rows">
            <div class="info-row">
              <span class="info-label">订单ID</span>
              <span class="info-value">{{ order.id }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">用户ID</span>
              <span class="info-value">{{ order.user_id }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">店铺ID</span>
              <span class="info-value">{{ order.shop_id }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">支付方式</span>
              <span class="info-value">{{ payMethodLabel(order.pay_method) }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">下单时间</span>
              <span class="info-value">{{ formatTime(order.created_at) }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">更新时间</span>
              <span class="info-value">{{ formatTime(order.updated_at) }}</span>
            </div>
          </div>
        </div>

        <div class="info-card">
          <h3 class="card-title">
            <el-icon><Money /></el-icon>
            金额信息
          </h3>
          <div class="info-rows">
            <div class="info-row">
              <span class="info-label">原价总额</span>
              <span class="info-value amount">¥{{ toFixed2(order.total_amount) }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">优惠抵扣</span>
              <span class="info-value amount discount">-¥{{ toFixed2(order.discount_amount) }}</span>
            </div>
            <div class="info-row highlight">
              <span class="info-label">实付金额</span>
              <span class="info-value amount pay">¥{{ toFixed2(order.pay_amount) }}</span>
            </div>
            <div class="info-row" v-if="order.pay_time">
              <span class="info-label">支付时间</span>
              <span class="info-value">{{ formatTime(order.pay_time) }}</span>
            </div>
            <div class="info-row" v-if="order.ship_time">
              <span class="info-label">发货时间</span>
              <span class="info-value">{{ formatTime(order.ship_time) }}</span>
            </div>
            <div class="info-row" v-if="order.receive_time">
              <span class="info-label">收货时间</span>
              <span class="info-value">{{ formatTime(order.receive_time) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 订单商品 -->
      <div class="section-card">
        <h3 class="card-title">
          <el-icon><Goods /></el-icon>
          订单商品（{{ items.length }} 件）
        </h3>
        <el-table :data="items" size="small" class="items-table">
          <el-table-column type="index" width="60" label="#" />
          <el-table-column label="SKU ID" prop="sku_id" width="100" align="center" />
          <el-table-column label="规格" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">
              <template v-if="row.sku_snapshot">
                {{ parseSnapshot(row.sku_snapshot).spec_combo || '—' }}
              </template>
              <span v-else class="text-muted">—</span>
            </template>
          </el-table-column>
          <el-table-column label="单价" width="120" align="right">
            <template #default="{ row }">
              ¥{{ toFixed2(row.unit_price) }}
            </template>
          </el-table-column>
          <el-table-column label="数量" prop="quantity" width="80" align="center" />
          <el-table-column label="小计" width="120" align="right">
            <template #default="{ row }">
              <span class="amount">¥{{ toFixed2(row.unit_price * row.quantity) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 支付信息 -->
      <div v-if="payment" class="section-card">
        <h3 class="card-title">
          <el-icon><CreditCard /></el-icon>
          支付流水
        </h3>
        <div class="info-rows two-cols">
          <div class="info-row">
            <span class="info-label">流水ID</span>
            <span class="info-value">{{ payment.id }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">支付渠道</span>
            <span class="info-value">{{ payMethodLabel(payment.channel) }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">交易号</span>
            <span class="info-value mono">{{ payment.trade_no || '—' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">支付金额</span>
            <span class="info-value amount pay">¥{{ toFixed2(payment.amount) }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">支付状态</span>
            <span class="info-value">
              <el-tag :type="payment.status === 'paid' ? 'success' : payment.status === 'refunding' ? 'warning' : 'info'" size="small">
                {{ paymentStatusLabel(payment.status) }}
              </el-tag>
            </span>
          </div>
          <div class="info-row">
            <span class="info-label">支付时间</span>
            <span class="info-value">{{ formatTime(payment.paid_at) }}</span>
          </div>
        </div>
      </div>

      <!-- 退款信息（纠纷标记） -->
      <div v-if="refund" class="section-card dispute-card">
        <h3 class="card-title">
          <el-icon><WarningFilled /></el-icon>
          <span class="dispute-title">退款/纠纷记录</span>
          <el-tag type="danger" size="small" class="dispute-badge">纠纷</el-tag>
        </h3>
        <div class="info-rows two-cols">
          <div class="info-row">
            <span class="info-label">退款ID</span>
            <span class="info-value">{{ refund.id }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">退款状态</span>
            <span class="info-value">
              <el-tag :type="refundStatusTagType(refund.status)" size="small">
                {{ refundStatusLabel(refund.status) }}
              </el-tag>
            </span>
          </div>
          <div class="info-row">
            <span class="info-label">退款金额</span>
            <span class="info-value amount refund-amount">¥{{ toFixed2(refund.amount) }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">退款原因</span>
            <span class="info-value">{{ refund.reason }}</span>
          </div>
          <div class="info-row full-width">
            <span class="info-label">申请时间</span>
            <span class="info-value">{{ formatTime(refund.apply_at || refund.created_at) }}</span>
          </div>
          <div v-if="refund.evidence_images" class="info-row full-width">
            <span class="info-label">凭证图片</span>
            <span class="info-value">
              <template v-if="Array.isArray(refund.evidence_images) && refund.evidence_images.length">
                <el-image
                  v-for="(img, idx) in refund.evidence_images"
                  :key="idx"
                  :src="img"
                  :preview-src-list="refund.evidence_images"
                  fit="cover"
                  class="evidence-img"
                  :initial-index="idx"
                />
              </template>
              <span v-else class="text-muted">无</span>
            </span>
          </div>
        </div>
      </div>

      <!-- 状态时间线 -->
      <div v-if="timeline && timeline.length" class="section-card">
        <h3 class="card-title">
          <el-icon><Clock /></el-icon>
          状态流转
        </h3>
        <el-timeline>
          <el-timeline-item
            v-for="(entry, idx) in timeline"
            :key="idx"
            :timestamp="formatTime(entry.time || entry.created_at)"
            placement="top"
            :type="timelineItemType(entry.status)"
          >
            {{ entry.label || entry.status }}
            <span v-if="entry.remark" class="timeline-remark"> — {{ entry.remark }}</span>
          </el-timeline-item>
        </el-timeline>
      </div>
    </template>
  </div>
</template>

<script setup>
/**
 * AdminOrderDetail — 平台后台订单详情页
 * 展示订单全量信息、支付流水、纠纷标记、状态时间线
 * 🛑 passBy: "params" → 使用 route.params.id 读取订单ID
 */
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  Document, Money, Goods, CreditCard,
  WarningFilled, Clock
} from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { getOrderDetail } from '@/api/admin/order.js';

const route = useRoute();
const router = useRouter();

// 🛑 passBy: "params" → 从 route.params 读取
const orderId = computed(() => Number(route.params.id));

// ---------- 状态 ----------
const loading = ref(true);
const errorMsg = ref('');
const order = ref(null);
const items = ref([]);
const payment = ref(null);
const refund = ref(null);
const timeline = ref([]);

// ---------- 计算属性 ----------
const isDisputed = computed(() => !!refund.value);

// ---------- 常量 ----------
const STATUS_MAP = {
  pending_pay: '待支付',
  paid: '已支付',
  shipped: '已发货',
  received: '已收货',
  completed: '已完成',
  cancelled: '已取消',
  refunding: '退款中'
};

const PAY_METHOD_MAP = {
  wxpay: '微信支付',
  alipay: '支付宝'
};

const PAYMENT_STATUS_MAP = {
  pending: '待支付',
  paid: '已支付',
  refunding: '退款中',
  refunded: '已退款',
  closed: '已关闭'
};

const REFUND_STATUS_MAP = {
  applied: '已申请',
  approved: '已通过',
  rejected: '已驳回',
  processing: '处理中',
  completed: '已完成'
};

// ---------- 工具函数 ----------
function statusLabel(s) { return STATUS_MAP[s] || s; }
function payMethodLabel(m) { return PAY_METHOD_MAP[m] || m || '—'; }
function paymentStatusLabel(s) { return PAYMENT_STATUS_MAP[s] || s; }
function refundStatusLabel(s) { return REFUND_STATUS_MAP[s] || s; }
function toFixed2(v) { return parseFloat(v || 0).toFixed(2); }

function refundStatusTagType(s) {
  const map = { applied: 'warning', approved: 'success', rejected: 'danger', processing: 'info', completed: 'success' };
  return map[s] || 'info';
}

function timelineItemType(status) {
  if (/cancelled|rejected|refund/.test(status)) return 'danger';
  if (/completed|received/.test(status)) return 'success';
  if (/paid|shipped/.test(status)) return 'primary';
  return 'info';
}

function formatTime(ts) {
  if (!ts) return '—';
  const d = new Date(ts);
  if (isNaN(d.getTime())) return '—';
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function parseSnapshot(raw) {
  if (!raw) return {};
  if (typeof raw === 'object') return raw;
  try { return JSON.parse(raw); } catch { return {}; }
}

// ---------- 方法 ----------
async function fetchDetail() {
  loading.value = true;
  errorMsg.value = '';
  try {
    const res = await getOrderDetail(orderId.value);
    const data = res.data || {};
    order.value = data.order || null;
    items.value = data.items || [];
    payment.value = data.payment || null;
    refund.value = data.refund || null;
    timeline.value = data.timeline || [];

    if (!order.value) {
      errorMsg.value = '订单不存在';
    }
  } catch (e) {
    const msg = e?.response?.data?.message || '获取订单详情失败';
    errorMsg.value = msg;
    ElMessage.error(msg);
  } finally {
    loading.value = false;
  }
}

function goBack() {
  router.push({ name: 'AdminOrderList' });
}

// ---------- 生命周期 ----------
onMounted(() => {
  if (orderId.value) {
    fetchDetail();
  } else {
    errorMsg.value = '缺少订单ID参数';
    loading.value = false;
  }
});
</script>

<style scoped>
/* ===== 页面容器 ===== */
.admin-order-detail {
  padding: var(--app-space-xl, 24px);
  min-height: 100%;
  background: var(--app-bg-page, #eef1f6);
  max-width: 1200px;
}

/* ===== 面包屑 ===== */
.breadcrumb-bar {
  margin-bottom: var(--app-space-lg, 20px);
}

.breadcrumb-bar :deep(.el-breadcrumb__inner) {
  color: #1e3a5f;
  font-weight: 500;
}

.breadcrumb-bar :deep(.el-breadcrumb__inner.is-link:hover) {
  color: #2b4f7d;
}

/* ===== 加载/错误态 ===== */
.loading-state,
.error-state {
  background: var(--app-bg-container, #ffffff);
  border-radius: var(--app-radius-md, 12px);
  padding: var(--app-space-xl, 24px);
  box-shadow: var(--app-shadow-level-1, 0 1px 3px rgba(0,0,0,0.06));
}

/* ===== 状态横幅 ===== */
.status-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--app-bg-container, #ffffff);
  border-radius: var(--app-radius-md, 12px);
  padding: var(--app-space-lg, 20px) var(--app-space-xl, 24px);
  margin-bottom: var(--app-space-base, 16px);
  box-shadow: var(--app-shadow-level-1, 0 1px 3px rgba(0,0,0,0.06));
  border-left: 4px solid #1e3a5f;
}

.status-banner.status--completed {
  border-left-color: #22c55e;
}

.status-banner.status--cancelled,
.status-banner.status--refunding {
  border-left-color: #ef4444;
}

.status-banner-left {
  display: flex;
  align-items: center;
  gap: var(--app-space-sm, 8px);
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #1e3a5f;
}

.status--completed .status-dot { background: #22c55e; }
.status--cancelled .status-dot,
.status--refunding .status-dot { background: #ef4444; }

.status-text {
  font-size: var(--app-font-lg, 1rem);
  font-weight: 600;
  color: #1a2332;
}

.dispute-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: var(--app-space-sm, 8px);
  padding: 2px 10px;
  font-size: var(--app-font-xs, 0.75rem);
  font-weight: 600;
  color: #ef4444;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.25);
  border-radius: var(--app-radius-full, 9999px);
}

.status-banner-right {
  display: flex;
  align-items: center;
  gap: var(--app-space-sm, 8px);
}

.order-no-label {
  font-size: var(--app-font-sm, 0.8125rem);
  color: var(--app-text-secondary, #6b7280);
}

.order-no-value {
  font-size: var(--app-font-md, 0.9375rem);
  font-weight: 700;
  color: #1a2332;
  font-variant-numeric: tabular-nums;
}

/* ===== 信息网格 ===== */
.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--app-space-base, 16px);
  margin-bottom: var(--app-space-base, 16px);
}

@media (max-width: 768px) {
  .info-grid {
    grid-template-columns: 1fr;
  }
}

/* ===== 卡片 ===== */
.info-card,
.section-card {
  background: var(--app-bg-container, #ffffff);
  border-radius: var(--app-radius-md, 12px);
  padding: var(--app-space-lg, 20px) var(--app-space-xl, 24px);
  box-shadow: var(--app-shadow-level-1, 0 1px 3px rgba(0,0,0,0.06));
}

.section-card {
  margin-bottom: var(--app-space-base, 16px);
}

.card-title {
  display: flex;
  align-items: center;
  gap: var(--app-space-sm, 8px);
  margin: 0 0 var(--app-space-base, 16px);
  font-size: var(--app-font-lg, 1rem);
  font-weight: 600;
  color: #1a2332;
  padding-bottom: var(--app-space-md, 12px);
  border-bottom: 1px solid var(--app-border-light, #e5e7eb);
}

.card-title .el-icon {
  color: #1e3a5f;
}

/* ===== 纠纷卡片 ===== */
.dispute-card {
  border-left: 3px solid #ef4444;
}

.dispute-card .card-title .el-icon {
  color: #ef4444;
}

.dispute-title {
  color: #ef4444;
}

.dispute-badge {
  margin-left: auto;
}

/* ===== 信息行 ===== */
.info-rows {
  display: flex;
  flex-direction: column;
  gap: var(--app-space-sm, 8px);
}

.info-rows.two-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--app-space-sm, 8px) var(--app-space-xl, 24px);
}

@media (max-width: 576px) {
  .info-rows.two-cols {
    grid-template-columns: 1fr;
  }
}

.info-row {
  display: flex;
  align-items: baseline;
  padding: var(--app-space-xs, 4px) 0;
}

.info-row.full-width {
  grid-column: 1 / -1;
}

.info-row.highlight {
  background: #f4f6fa;
  padding: var(--app-space-sm, 8px) var(--app-space-md, 12px);
  border-radius: var(--app-radius-sm, 4px);
  margin: var(--app-space-xs, 4px) 0;
}

.info-label {
  flex-shrink: 0;
  width: 90px;
  font-size: var(--app-font-sm, 0.8125rem);
  color: var(--app-text-secondary, #6b7280);
}

.info-value {
  font-size: var(--app-font-base, 0.875rem);
  color: #1a2332;
  word-break: break-all;
}

.info-value.mono {
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: var(--app-font-sm, 0.8125rem);
}

.amount {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.amount.pay {
  color: #1e3a5f;
  font-size: var(--app-font-lg, 1rem);
}

.amount.discount {
  color: var(--app-text-secondary, #6b7280);
}

.amount.refund-amount {
  color: #ef4444;
}

.text-muted {
  color: var(--app-text-disabled, #b0b7c3);
}

/* ===== 证据图片 ===== */
.evidence-img {
  width: 64px;
  height: 64px;
  border-radius: var(--app-radius-sm, 4px);
  border: 1px solid var(--app-border-light, #e5e7eb);
  margin-right: var(--app-space-sm, 8px);
  cursor: pointer;
}

/* ===== 商品表格 ===== */
.items-table :deep(.el-table__header th) {
  background: #f0f3f8;
  color: #1a2332;
  font-weight: 600;
  font-size: var(--app-font-sm, 0.8125rem);
}

/* ===== 时间线 ===== */
.timeline-remark {
  font-size: var(--app-font-sm, 0.8125rem);
  color: var(--app-text-secondary, #6b7280);
}

/* ===== Element Plus 按钮覆写 ===== */
:deep(.el-button--primary) {
  --el-button-bg-color: #1e3a5f;
  --el-button-border-color: #1e3a5f;
  --el-button-hover-bg-color: #2b4f7d;
  --el-button-hover-border-color: #2b4f7d;
  --el-button-active-bg-color: #162d4a;
  --el-button-active-border-color: #162d4a;
}

:deep(.el-tag--primary) {
  --el-tag-bg-color: rgba(30, 58, 95, 0.1);
  --el-tag-border-color: rgba(30, 58, 95, 0.2);
  --el-tag-text-color: #1e3a5f;
}

:deep(.el-timeline-item__node--primary) {
  background-color: #1e3a5f;
  border-color: #1e3a5f;
}
</style>
