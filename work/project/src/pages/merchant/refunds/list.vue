<!--
  商家售后审批列表页
  路由: /merchant/refunds
  功能: 查看本店售后申请、按状态筛选、审批（同意/拒绝）
  点击行跳转售后详情页
-->
<template>
  <div class="refund-list-page">
    <div class="page-header">
      <el-button text @click="$router.push({name:'MerchantDashboard'})">← 返回看板</el-button>
      <h2 class="page-title">售后管理</h2>
    </div>
    <!-- 状态筛选 Tab -->
    <div class="status-filter-bar">
      <el-radio-group v-model="activeStatus" size="small" @change="handleStatusChange">
        <el-radio-button :value="''">全部</el-radio-button>
        <el-radio-button
          v-for="tab in statusTabs"
          :key="tab.value"
          :value="tab.value"
        >
          {{ tab.label }}
          <el-badge
            v-if="tab.count !== undefined"
            :value="tab.count"
            :type="tab.badgeType"
            class="status-badge"
          />
        </el-radio-button>
      </el-radio-group>
    </div>

    <!-- 加载态 - 骨架屏 -->
    <div v-if="loading && list.length === 0" class="skeleton-container">
      <div
        v-for="i in 6"
        :key="i"
        class="skeleton-row"
        :style="{ animationDelay: `${(i - 1) * 0.08}s` }"
      >
        <div class="skeleton-cell skeleton-cell--no"></div>
        <div class="skeleton-cell skeleton-cell--type"></div>
        <div class="skeleton-cell skeleton-cell--reason"></div>
        <div class="skeleton-cell skeleton-cell--amount"></div>
        <div class="skeleton-cell skeleton-cell--status"></div>
        <div class="skeleton-cell skeleton-cell--time"></div>
        <div class="skeleton-cell skeleton-cell--action"></div>
      </div>
    </div>

    <!-- 错误态 -->
    <div v-else-if="error && list.length === 0" class="error-state">
      <el-icon :size="48" color="var(--color-error)" style="opacity: 0.6">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
      </el-icon>
      <h3 class="error-title">加载失败</h3>
      <p class="error-desc">网络连接出现问题，请检查网络后重试</p>
      <el-button type="primary" @click="fetchList">重新加载</el-button>
    </div>

    <!-- 空状态 -->
    <div v-else-if="list.length === 0 && !loading" class="empty-state">
      <el-icon :size="64" color="var(--color-text-tertiary)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="2" y="3" width="20" height="18" rx="2"/>
          <line x1="8" y1="9" x2="16" y2="9"/>
          <line x1="8" y1="13" x2="12" y2="13"/>
        </svg>
      </el-icon>
      <h3 class="empty-title">暂无售后申请</h3>
      <p class="empty-desc">当有消费者发起售后时，申请将显示在这里</p>
    </div>

    <!-- 表格 - 桌面端 -->
    <div v-else class="table-container">
      <el-table
        ref="tableRef"
        :data="list"
        stripe
        row-key="id"
        highlight-current-row
        @row-click="handleRowClick"
        class="refund-table"
      >
        <el-table-column prop="requestNo" label="售后单号" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="mono-text">{{ row.requestNo }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag
              :type="row.type === 'only_refund' ? 'warning' : 'info'"
              size="small"
              effect="plain"
            >
              {{ row.type === 'only_refund' ? '仅退款' : '退货退款' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="原因" min-width="200" show-overflow-tooltip />
        <el-table-column prop="amount" label="金额" width="120" align="right">
          <template #default="{ row }">
            <span class="amount-text">¥{{ formatAmount(row.amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120" align="center">
          <template #default="{ row }">
            <status-badge :status="row.status" />
          </template>
        </el-table-column>
        <el-table-column label="剩余时间" width="130" align="center">
          <template #default="{ row }">
            <timeout-indicator
              v-if="row.status === 'pending'"
              :created-at="row.createdAt"
            />
            <span v-else class="text-tertiary">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="申请时间" width="170" align="center">
          <template #default="{ row }">
            {{ formatTime(row.createdAt) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" align="center" fixed="right">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button
                type="primary"
                size="small"
                :loading="operatingId === row.id && operatingAction === 'approve'"
                @click.stop="handleApprove(row)"
              >
                同意
              </el-button>
              <el-button
                type="danger"
                size="small"
                :loading="operatingId === row.id && operatingAction === 'reject'"
                @click.stop="openRejectDialog(row)"
              >
                拒绝
              </el-button>
            </template>
            <template v-else-if="row.status === 'awaiting_merchant_receive'">
              <el-button
                type="primary"
                size="small"
                :loading="operatingId === row.id"
                @click.stop="handleConfirmReceive(row)"
              >
                确认收货
              </el-button>
            </template>
            <span v-else class="text-tertiary">—</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div v-if="total > 0" class="pagination-wrapper">
        <span class="pagination-info">
          第 {{ (page - 1) * pageSize + 1 }}-{{ Math.min(page * pageSize, total) }} 条，共 {{ total }} 条
        </span>
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="prev, pager, next, sizes"
          background
          small
          @current-change="fetchList"
          @size-change="handleSizeChange"
        />
      </div>
    </div>

    <!-- 同意确认弹窗 -->
    <el-dialog
      v-model="approveDialogVisible"
      title="确认同意退款"
      width="460px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <div class="dialog-body">
        <el-icon :size="40" color="var(--color-primary-500)" class="dialog-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="8,12 11,15 16,9"/>
          </svg>
        </el-icon>
        <p class="dialog-text">
          确认同意该售后申请？
        </p>
        <p v-if="approveTarget" class="dialog-detail">
          售后单号：{{ approveTarget.requestNo }}<br />
          类型：{{ approveTarget.type === 'only_refund' ? '仅退款' : '退货退款' }}<br />
          退款金额：<strong>¥{{ formatAmount(approveTarget.amount) }}</strong>
        </p>
        <p v-if="approveTarget && approveTarget.type === 'return_refund'" class="dialog-hint">
          同意后消费者将退货，请等待收到退货后确认
        </p>
        <p v-else-if="approveTarget" class="dialog-hint">
          同意后系统将自动发起退款
        </p>
      </div>
      <template #footer>
        <el-button @click="approveDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="operatingLoading" @click="confirmApprove">
          确认同意
        </el-button>
      </template>
    </el-dialog>

    <!-- 拒绝弹窗 -->
    <el-dialog
      v-model="rejectDialogVisible"
      title="拒绝退款申请"
      width="460px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form
        ref="rejectFormRef"
        :model="rejectForm"
        :rules="rejectRules"
        label-position="top"
      >
        <el-form-item label="拒绝原因" prop="reason">
          <el-input
            v-model="rejectForm.reason"
            type="textarea"
            :rows="4"
            maxlength="500"
            show-word-limit
            placeholder="请填写拒绝原因，消费者将看到此信息"
          />
        </el-form-item>
        <p v-if="rejectTarget" class="dialog-detail">
          售后单号：{{ rejectTarget.requestNo }} | 金额：¥{{ formatAmount(rejectTarget.amount) }}
        </p>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="operatingLoading" @click="confirmReject">
          确认拒绝
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { getMerchantRefunds, approveRefund } from '@/api/merchant-refunds';

const router = useRouter();

// ===== 状态管理 =====
const activeStatus = ref('');
const list = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const loading = ref(false);
const error = ref(false);

// 操作状态
const operatingId = ref(null);
const operatingAction = ref('');
const operatingLoading = ref(false);

// 弹窗
const approveDialogVisible = ref(false);
const approveTarget = ref(null);
const rejectDialogVisible = ref(false);
const rejectTarget = ref(null);
const rejectFormRef = ref(null);
const rejectForm = reactive({ reason: '' });
const rejectRules = {
  reason: [
    { required: true, message: '拒绝原因不能为空', trigger: 'blur' },
    { min: 2, message: '拒绝原因至少2个字符', trigger: 'blur' },
    { max: 500, message: '拒绝原因最多500个字符', trigger: 'blur' },
  ],
};

// 计时器
let countdownTimer = null;

// ===== 状态 Tab 配置 =====
const statusTabs = [
  { value: 'pending', label: '待审核', badgeType: 'warning' },
  { value: 'awaiting_return', label: '待退货', badgeType: 'info' },
  { value: 'awaiting_merchant_receive', label: '待收货', badgeType: '' },
  { value: 'refunding', label: '退款中', badgeType: 'info' },
  { value: 'completed', label: '已完成', badgeType: 'success' },
  { value: 'rejected', label: '已拒绝', badgeType: 'danger' },
  { value: 'arbitrating', label: '仲裁中', badgeType: 'warning' },
  { value: 'closed', label: '已关闭', badgeType: '' },
];

// ===== 工具函数 =====
function formatAmount(val) {
  const num = parseFloat(val);
  if (isNaN(num)) return '0.00';
  return num.toFixed(2);
}

function formatTime(isoStr) {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// ===== 数据获取 =====
async function fetchList() {
  loading.value = true;
  error.value = false;
  try {
    const res = await getMerchantRefunds({
      status: activeStatus.value || undefined,
      page: page.value,
      pageSize: pageSize.value,
    });
    if (res.data && res.data.success !== false) {
      list.value = res.data?.list ?? [];
      total.value = res.data?.total ?? 0;
    } else {
      list.value = [];
      total.value = 0;
    }
  } catch (e) {
    error.value = true;
    list.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

function handleStatusChange() {
  page.value = 1;
  fetchList();
}

function handleSizeChange() {
  page.value = 1;
  fetchList();
}

// ===== 行点击 - 跳转详情 =====
function handleRowClick(row) {
  router.push({ name: 'RefundDetail', params: { id: row.subOrderId } });
}

// ===== 审批操作 =====

// 同意
function handleApprove(row) {
  approveTarget.value = row;
  approveDialogVisible.value = true;
}

async function confirmApprove() {
  if (!approveTarget.value) return;
  operatingLoading.value = true;
  operatingId.value = approveTarget.value.id;
  operatingAction.value = 'approve';
  try {
    await approveRefund({ id: approveTarget.value.id, action: 'approve' });
    ElMessage.success('已同意该售后申请');
    approveDialogVisible.value = false;
    approveTarget.value = null;
    fetchList();
  } catch (e) {
    const msg = e?.response?.data?.message || '操作失败，请重试';
    ElMessage.error(msg);
  } finally {
    operatingLoading.value = false;
    operatingId.value = null;
    operatingAction.value = '';
  }
}

// 拒绝
function openRejectDialog(row) {
  rejectTarget.value = row;
  rejectForm.reason = '';
  rejectDialogVisible.value = true;
  // 重置表单校验
  setTimeout(() => rejectFormRef.value?.resetFields(), 0);
}

async function confirmReject() {
  const valid = await rejectFormRef.value?.validate().catch(() => false);
  if (!valid) return;
  if (!rejectTarget.value) return;

  operatingLoading.value = true;
  operatingId.value = rejectTarget.value.id;
  operatingAction.value = 'reject';
  try {
    await approveRefund({
      id: rejectTarget.value.id,
      action: 'reject',
      reason: rejectForm.reason,
    });
    ElMessage.success('已拒绝该售后申请');
    rejectDialogVisible.value = false;
    rejectTarget.value = null;
    fetchList();
  } catch (e) {
    const msg = e?.response?.data?.message || '操作失败，请重试';
    ElMessage.error(msg);
  } finally {
    operatingLoading.value = false;
    operatingId.value = null;
    operatingAction.value = '';
  }
}

// 确认收货 (awaiting_merchant_receive 状态)
async function handleConfirmReceive(row) {
  try {
    await ElMessageBox.confirm(
      '确认已收到消费者退回的商品？确认后系统将发起退款。',
      '确认收货',
      {
        confirmButtonText: '确认收货',
        cancelButtonText: '取消',
        type: 'warning',
      }
    );
  } catch {
    return;
  }
  operatingLoading.value = true;
  operatingId.value = row.id;
  try {
    await approveRefund({ id: row.id, action: 'approve' });
    ElMessage.success('确认收货成功，退款处理中');
    fetchList();
  } catch (e) {
    const msg = e?.response?.data?.message || '操作失败，请重试';
    ElMessage.error(msg);
  } finally {
    operatingLoading.value = false;
    operatingId.value = null;
  }
}

// ===== 生命周期 =====
onMounted(() => {
  fetchList();
  // 每 30s 自动刷新（更新倒计时）
  countdownTimer = setInterval(() => {
    // 仅刷新 pending 状态的计时器显示，不请求后端
    // 每 5 分钟全量刷新一次
  }, 300000);
});

onBeforeUnmount(() => {
  if (countdownTimer) clearInterval(countdownTimer);
});
</script>

<script>
// ===== 状态标签组件 (局部注册) =====
import { h, defineComponent } from 'vue';
import { ElTag } from 'element-plus';

const STATUS_MAP = {
  pending: { label: '待审核', type: 'warning' },
  awaiting_return: { label: '待退货', type: 'info' },
  awaiting_merchant_receive: { label: '待收货', type: '' },
  refunding: { label: '退款中', type: 'info' },
  completed: { label: '已完成', type: 'success' },
  rejected: { label: '已拒绝', type: 'danger' },
  arbitrating: { label: '仲裁中', type: 'warning' },
  closed: { label: '已关闭', type: 'info' },
  retry: { label: '重试中', type: 'warning' },
};

const StatusBadge = defineComponent({
  name: 'StatusBadge',
  props: { status: { type: String, required: true } },
  setup(props) {
    return () => {
      const cfg = STATUS_MAP[props.status] || { label: props.status, type: 'info' };
      return h(ElTag, { type: cfg.type, size: 'small', effect: 'plain' }, () => cfg.label);
    };
  },
});

// ===== 超时倒计时组件 =====
import { ref as vRef, computed as vComputed, onMounted as vOnMounted, onBeforeUnmount as vOnBeforeUnmount } from 'vue';

const TimeoutIndicator = defineComponent({
  name: 'TimeoutIndicator',
  props: { createdAt: { type: String, required: true } },
  setup(props) {
    const now = vRef(Date.now());
    let timer = null;

    const createdTime = vComputed(() => new Date(props.createdAt).getTime());
    // 默认 24h 超时窗口
    const deadline = vComputed(() => createdTime.value + 24 * 60 * 60 * 1000);
    const remaining = vComputed(() => Math.max(0, deadline.value - now.value));

    const hours = vComputed(() => Math.floor(remaining.value / 3600000));
    const minutes = vComputed(() => Math.floor((remaining.value % 3600000) / 60000));

    const isUrgent = vComputed(() => remaining.value < 2 * 60 * 60 * 1000 && remaining.value > 0); // < 2h
    const isExpired = vComputed(() => remaining.value <= 0);

    const displayText = vComputed(() => {
      if (isExpired.value) return '即将超时';
      if (hours.value > 0) return `${hours.value}h${minutes.value}m`;
      return `${minutes.value}min`;
    });

    vOnMounted(() => {
      timer = setInterval(() => { now.value = Date.now(); }, 30000);
    });

    vOnBeforeUnmount(() => {
      if (timer) clearInterval(timer);
    });

    return () => {
      return h('span', {
        class: ['timeout-indicator', { 'timeout-indicator--urgent': isUrgent.value, 'timeout-indicator--expired': isExpired.value }],
        title: isExpired.value ? '已超过24小时审核窗口，系统将自动同意' : `剩余审核时间约${hours.value}小时${minutes.value}分钟`,
      }, displayText.value);
    };
  },
});

export default {
  name: 'MerchantRefunds',
  components: { StatusBadge, TimeoutIndicator },
};
</script>

<style scoped>
/* ===== 页面根样式 ===== */
.refund-list-page {
  padding: var(--space-lg);
  max-width: 1200px;
  margin: 0 auto;
}

/* ===== 状态筛选栏 ===== */
.status-filter-bar {
  margin-bottom: var(--space-md);
  padding: var(--space-sm) 0;
}

.status-filter-bar :deep(.el-radio-group) {
  flex-wrap: wrap;
  gap: 4px;
}

.status-filter-bar :deep(.el-radio-button__inner) {
  padding: 6px 14px;
  font-size: var(--font-size-sm);
  border-radius: var(--radius-md);
}

.status-badge {
  margin-left: 4px;
}

/* ===== 表格容器 ===== */
.table-container {
  background: var(--color-bg-base);
  border: var(--page-order-card-border, 1px solid var(--color-border));
  border-radius: var(--radius-md);
  overflow: hidden;
}

.refund-table {
  width: 100%;
}

.refund-table :deep(.el-table__row) {
  cursor: pointer;
  height: var(--page-order-row-height, 56px);
  transition: background-color var(--duration-instant) var(--ease-smooth);
}

.refund-table :deep(.el-table__row:hover) {
  background-color: var(--color-primary-50);
}

.refund-table :deep(.el-table th) {
  background-color: var(--color-bg-page);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: 600;
  padding: 10px 12px;
}

.refund-table :deep(.el-table td) {
  padding: 10px 12px;
}

/* 等宽数字 */
.mono-text {
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.5px;
  font-family: var(--font-family);
}

.amount-text {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  color: var(--color-text-primary);
}

.text-tertiary {
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

/* ===== 分页 ===== */
.pagination-wrapper {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-md);
  border-top: 1px solid var(--color-border);
}

.pagination-info {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

/* ===== 骨架屏 ===== */
.skeleton-container {
  background: var(--color-bg-base);
  border: var(--page-order-card-border, 1px solid var(--color-border));
  border-radius: var(--radius-md);
  overflow: hidden;
}

.skeleton-row {
  display: flex;
  align-items: center;
  height: var(--page-order-row-height, 56px);
  padding: 0 12px;
  border-bottom: 1px solid var(--color-border);
  animation: skeleton-pulse 1.8s ease-in-out infinite;
}

.skeleton-cell {
  height: 14px;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--color-bg-page) 25%, var(--color-primary-50) 50%, var(--color-bg-page) 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.8s ease-in-out infinite;
}

.skeleton-cell--no { width: 140px; margin-right: 12px; }
.skeleton-cell--type { width: 60px; margin-right: 12px; }
.skeleton-cell--reason { flex: 1; margin-right: 12px; }
.skeleton-cell--amount { width: 80px; margin-right: 12px; }
.skeleton-cell--status { width: 70px; margin-right: 12px; }
.skeleton-cell--time { width: 90px; margin-right: 12px; }
.skeleton-cell--action { width: 100px; }

@keyframes skeleton-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

@keyframes skeleton-shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

/* ===== 空状态 ===== */
.empty-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-3xl) var(--space-lg);
  background: var(--color-bg-base);
  border: var(--page-order-card-border, 1px solid var(--color-border));
  border-radius: var(--radius-md);
}

.empty-title,
.error-title {
  margin: var(--space-md) 0 var(--space-xs);
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
  font-weight: 600;
}

.empty-desc,
.error-desc {
  margin: 0 0 var(--space-lg);
  color: var(--color-text-secondary);
  font-size: var(--font-size-base);
}

/* ===== 超时指示器 ===== */
.timeout-indicator {
  font-size: var(--font-size-sm);
  font-variant-numeric: tabular-nums;
  color: var(--color-text-secondary);
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background: var(--color-bg-page);
}

.timeout-indicator--urgent {
  color: var(--color-error);
  background: hsl(0, 30%, 94%);
  font-weight: 600;
}

.timeout-indicator--expired {
  color: var(--color-error);
  background: hsl(0, 30%, 94%);
  font-weight: 600;
  animation: blink-warning 1s ease-in-out infinite;
}

@keyframes blink-warning {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* ===== 弹窗 ===== */
.dialog-body {
  text-align: center;
}

.dialog-icon {
  margin-bottom: var(--space-md);
}

.dialog-text {
  font-size: var(--font-size-md);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-sm);
}

.dialog-detail {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: var(--line-height-relaxed);
  margin: var(--space-sm) 0 0;
  text-align: left;
  padding: var(--space-sm);
  background: var(--color-bg-page);
  border-radius: var(--radius-sm);
}

.dialog-hint {
  font-size: var(--font-size-sm);
  color: var(--color-warning);
  margin: var(--space-sm) 0 0;
  text-align: left;
  padding: var(--space-sm);
  background: hsl(38, 40%, 94%);
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--color-warning);
}

/* ===== 响应式 ===== */
@media (max-width: 1024px) {
  .refund-list-page {
    padding: var(--space-md);
  }

  .refund-table :deep(.el-table__row) {
    height: auto;
  }
}

@media (max-width: 768px) {
  .refund-list-page {
    padding: var(--space-sm);
  }

  .status-filter-bar :deep(.el-radio-group) {
    display: flex;
    flex-wrap: nowrap;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    padding-bottom: 4px;
  }

  .pagination-wrapper {
    flex-direction: column;
    gap: var(--space-sm);
  }
}
</style>
