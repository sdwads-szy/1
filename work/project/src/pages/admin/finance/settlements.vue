<template>
  <div class="settlements-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ name: 'AdminDashboard' }">平台后台</el-breadcrumb-item>
        <el-breadcrumb-item>结算与提现管理</el-breadcrumb-item>
      </el-breadcrumb>
      <h1 class="page-title">结算与提现管理</h1>
    </div>

    <!-- Tab 切换 -->
    <el-tabs v-model="activeTab" class="settlements-tabs" @tab-change="handleTabChange">
      <!-- ========== 结算管理 ========== -->
      <el-tab-pane label="结算管理" name="settlements">
        <!-- 筛选栏 -->
        <div class="filter-bar">
          <el-radio-group v-model="settlementFilters.status" size="small" @change="loadSettlements">
            <el-radio-button value="">全部</el-radio-button>
            <el-radio-button value="pending">待确认</el-radio-button>
            <el-radio-button value="confirmed">已确认</el-radio-button>
            <el-radio-button value="paid">已打款</el-radio-button>
            <el-radio-button value="completed">已完成</el-radio-button>
            <el-radio-button value="clawed_back">已追索</el-radio-button>
          </el-radio-group>
        </div>

        <!-- 结算表格 -->
        <el-table
          v-loading="settlementLoading"
          :data="settlementList"
          stripe
          class="data-table"
          empty-text="暂无结算记录"
        >
          <el-table-column prop="id" label="ID" width="70" align="center" />
          <el-table-column prop="shopName" label="商家" min-width="160" show-overflow-tooltip />
          <el-table-column prop="period" label="结算周期" width="120" align="center" />
          <el-table-column prop="amount" label="结算金额" width="140" align="right">
            <template #default="{ row }">
              <span class="amount-cell">¥{{ formatAmount(row.amount) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="settlementStatusMap[row.status]?.type || 'info'" size="small" effect="plain">
                {{ settlementStatusMap[row.status]?.label || row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="paidAt" label="打款时间" width="180" align="center">
            <template #default="{ row }">
              {{ row.paidAt ? formatDateTime(row.paidAt) : '—' }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" align="center" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="row.status === 'confirmed'"
                type="primary"
                size="small"
                @click="openPayModal(row)"
              >
                打款
              </el-button>
              <span v-else class="no-action">—</span>
            </template>
          </el-table-column>
        </el-table>

        <!-- 结算分页 -->
        <div class="pagination-wrap">
          <el-pagination
            v-model:current-page="settlementPagination.page"
            v-model:page-size="settlementPagination.pageSize"
            :total="settlementPagination.total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @current-change="loadSettlements"
            @size-change="loadSettlements"
          />
        </div>
      </el-tab-pane>

      <!-- ========== 提现审批 ========== -->
      <el-tab-pane label="提现审批" name="withdrawals">
        <!-- 筛选栏 -->
        <div class="filter-bar">
          <el-radio-group v-model="withdrawalFilters.status" size="small" @change="loadWithdrawals">
            <el-radio-button value="">全部</el-radio-button>
            <el-radio-button value="pending">待审核</el-radio-button>
            <el-radio-button value="approved">已通过</el-radio-button>
            <el-radio-button value="paid">已打款</el-radio-button>
            <el-radio-button value="rejected">已驳回</el-radio-button>
          </el-radio-group>
        </div>

        <!-- 提现表格 -->
        <el-table
          v-loading="withdrawalLoading"
          :data="withdrawalList"
          stripe
          class="data-table"
          empty-text="暂无提现记录"
        >
          <el-table-column prop="id" label="ID" width="70" align="center" />
          <el-table-column prop="requestNo" label="提现单号" width="200" show-overflow-tooltip />
          <el-table-column prop="shopName" label="商家" min-width="140" show-overflow-tooltip />
          <el-table-column prop="amount" label="提现金额" width="140" align="right">
            <template #default="{ row }">
              <span class="amount-cell">¥{{ formatAmount(row.amount) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="bankAccount" label="收款账户" width="180" align="center">
            <template #default="{ row }">
              <el-tooltip :content="row.bankAccount || ''" placement="top" :disabled="!row.bankAccount">
                <span>{{ maskBankAccount(row.bankAccount) }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="withdrawalStatusMap[row.status]?.type || 'info'" size="small" effect="plain">
                {{ withdrawalStatusMap[row.status]?.label || row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="reviewReason" label="审核意见" min-width="140" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.reviewReason || '—' }}
            </template>
          </el-table-column>
          <el-table-column prop="createdAt" label="申请时间" width="180" align="center">
            <template #default="{ row }">
              {{ formatDateTime(row.createdAt) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160" align="center" fixed="right">
            <template #default="{ row }">
              <template v-if="row.status === 'pending'">
                <el-button type="success" size="small" @click="approveWithdrawalAction(row)">
                  通过
                </el-button>
                <el-button type="danger" size="small" @click="openRejectModal(row)">
                  驳回
                </el-button>
              </template>
              <span v-else class="no-action">—</span>
            </template>
          </el-table-column>
        </el-table>

        <!-- 提现分页 -->
        <div class="pagination-wrap">
          <el-pagination
            v-model:current-page="withdrawalPagination.page"
            v-model:page-size="withdrawalPagination.pageSize"
            :total="withdrawalPagination.total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @current-change="loadWithdrawals"
            @size-change="loadWithdrawals"
          />
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- ========== 打款确认弹窗 ========== -->
    <el-dialog
      v-model="payModal.visible"
      title="确认打款"
      width="480px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <div class="confirm-body">
        <el-descriptions :column="1" border size="default">
          <el-descriptions-item label="商家">{{ payModal.shopName }}</el-descriptions-item>
          <el-descriptions-item label="结算周期">{{ payModal.period }}</el-descriptions-item>
          <el-descriptions-item label="结算金额">
            <span class="amount-cell">¥{{ formatAmount(payModal.amount) }}</span>
          </el-descriptions-item>
        </el-descriptions>
        <el-alert
          v-if="Number(payModal.amount) >= 50000"
          type="warning"
          title="大额结算将在 1-3 个工作日审核后到账"
          :closable="false"
          show-icon
          style="margin-top: 16px"
        />
      </div>
      <template #footer>
        <el-button @click="payModal.visible = false">取消</el-button>
        <el-button type="primary" :loading="payModal.loading" @click="confirmPay">
          确认打款
        </el-button>
      </template>
    </el-dialog>

    <!-- ========== 驳回原因弹窗 ========== -->
    <el-dialog
      v-model="rejectModal.visible"
      title="驳回提现申请"
      width="480px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form :model="rejectModal" label-width="80px">
        <el-form-item label="提现单号">
          <span>{{ rejectModal.requestNo }}</span>
        </el-form-item>
        <el-form-item label="提现金额">
          <span class="amount-cell">¥{{ formatAmount(rejectModal.amount) }}</span>
        </el-form-item>
        <el-form-item
          label="驳回原因"
          required
          :error="rejectModal.error"
        >
          <el-input
            v-model="rejectModal.reason"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            placeholder="请填写驳回原因（必填）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectModal.visible = false">取消</el-button>
        <el-button
          type="danger"
          :loading="rejectModal.loading"
          :disabled="!rejectModal.reason.trim()"
          @click="confirmReject"
        >
          确认驳回
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { getAdminSettlements, paySettlement } from '@/api/admin-settlements';
import { getAdminWithdrawals, approveWithdrawal } from '@/api/admin-withdrawals';

// ==================== 状态映射 ====================

const settlementStatusMap = {
  pending: { label: '待确认', type: 'warning' },
  confirmed: { label: '已确认', type: '' },
  paid: { label: '已打款', type: 'success' },
  completed: { label: '已完成', type: 'success' },
  clawed_back: { label: '已追索', type: 'danger' }
};

const withdrawalStatusMap = {
  pending: { label: '待审核', type: 'warning' },
  approved: { label: '已通过', type: '' },
  paid: { label: '已打款', type: 'success' },
  rejected: { label: '已驳回', type: 'danger' }
};

// ==================== Tab ====================

const activeTab = ref('settlements');

function handleTabChange(tab) {
  if (tab === 'settlements') {
    loadSettlements();
  } else {
    loadWithdrawals();
  }
}

// ==================== 结算管理 ====================

const settlementLoading = ref(false);
const settlementList = ref([]);
const settlementFilters = reactive({ status: '' });
const settlementPagination = reactive({ page: 1, pageSize: 20, total: 0 });

async function loadSettlements() {
  settlementLoading.value = true;
  try {
    const params = {
      page: settlementPagination.page,
      pageSize: settlementPagination.pageSize
    };
    if (settlementFilters.status) {
      params.status = settlementFilters.status;
    }
    const res = await getAdminSettlements(params);
    if (res.data) {
      settlementList.value = res.data.list || [];
      settlementPagination.total = res.data.total || 0;
    }
  } catch (err) {
    ElMessage.error(err?.response?.data?.message || '结算数据加载失败，请检查网络连接后重试');
  } finally {
    settlementLoading.value = false;
  }
}

// ==================== 打款弹窗 ====================

const payModal = reactive({
  visible: false,
  loading: false,
  id: null,
  shopName: '',
  period: '',
  amount: ''
});

function openPayModal(row) {
  payModal.id = row.id;
  payModal.shopName = row.shopName || '';
  payModal.period = row.period || '';
  payModal.amount = row.amount || '0';
  payModal.visible = true;
}

async function confirmPay() {
  payModal.loading = true;
  try {
    const res = await paySettlement(payModal.id);
    if (res.data?.mockHint) {
      ElMessage.info(res.data.mockHint);
    }
    ElMessage.success('打款操作已提交');
    payModal.visible = false;
    loadSettlements();
  } catch (err) {
    const msg = err?.response?.data?.message || '打款操作失败，请稍后重试'; // eslint-disable-line
    ElMessage.error(msg);
  } finally {
    payModal.loading = false;
  }
}

// ==================== 提现审批 ====================

const withdrawalLoading = ref(false);
const withdrawalList = ref([]);
const withdrawalFilters = reactive({ status: '' });
const withdrawalPagination = reactive({ page: 1, pageSize: 20, total: 0 });

async function loadWithdrawals() {
  withdrawalLoading.value = true;
  try {
    const params = {
      page: withdrawalPagination.page,
      pageSize: withdrawalPagination.pageSize
    };
    if (withdrawalFilters.status) {
      params.status = withdrawalFilters.status;
    }
    const res = await getAdminWithdrawals(params);
    if (res.data) {
      withdrawalList.value = res.data.list || [];
      withdrawalPagination.total = res.data.total || 0;
    }
  } catch (err) {
    ElMessage.error(err?.response?.data?.message || '提现数据加载失败，请检查网络连接后重试');
  } finally {
    withdrawalLoading.value = false;
  }
}

// ==================== 通过提现 ====================

async function approveWithdrawalAction(row) {
  try {
    await ElMessageBox.confirm(
      `确认通过该提现申请？提现金额：¥${formatAmount(row.amount)}`,
      '确认通过',
      { confirmButtonText: '确认通过', cancelButtonText: '取消', type: 'success' }
    );
  } catch {
    return;
  }

  try {
    const res = await approveWithdrawal(row.id, { action: 'approve' });
    if (res.data?.mockHint) {
      ElMessage.info(res.data.mockHint);
    }
    ElMessage.success('提现申请已通过');
    loadWithdrawals();
  } catch (err) {
    const msg = err?.response?.data?.message || '操作失败，请稍后重试'; // eslint-disable-line
    ElMessage.error(msg);
  }
}

// ==================== 驳回弹窗 ====================

const rejectModal = reactive({
  visible: false,
  loading: false,
  id: null,
  requestNo: '',
  amount: '',
  reason: '',
  error: ''
});

function openRejectModal(row) {
  rejectModal.id = row.id;
  rejectModal.requestNo = row.requestNo || '';
  rejectModal.amount = row.amount || '0';
  rejectModal.reason = '';
  rejectModal.error = '';
  rejectModal.visible = true;
}

async function confirmReject() {
  if (!rejectModal.reason.trim()) {
    rejectModal.error = '驳回原因不能为空';
    return;
  }
  rejectModal.error = '';
  rejectModal.loading = true;
  try {
    const res = await approveWithdrawal(rejectModal.id, {
      action: 'reject',
      reason: rejectModal.reason.trim()
    });
    if (res.data?.mockHint) {
      ElMessage.info(res.data.mockHint);
    }
    ElMessage.success('提现申请已驳回');
    rejectModal.visible = false;
    loadWithdrawals();
  } catch (err) {
    const msg = err?.response?.data?.message || '操作失败，请稍后重试'; // eslint-disable-line
    ElMessage.error(msg);
  } finally {
    rejectModal.loading = false;
  }
}

// ==================== 工具函数 ====================

/**
 * 格式化金额（千分位 + 保留两位小数）
 */
function formatAmount(val) {
  if (val === null || val === undefined || val === '') return '0.00';
  const num = Number(val);
  if (isNaN(num)) return '0.00';
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/**
 * 格式化日期时间
 */
function formatDateTime(val) {
  if (!val) return '';
  const d = new Date(val);
  if (isNaN(d.getTime())) return val;
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

/**
 * 脱敏银行账号
 */
function maskBankAccount(account) {
  if (!account) return '—';
  if (account.includes('*')) return account;
  const str = String(account);
  if (str.length <= 4) return str;
  return str.slice(0, 4) + ' **** ' + str.slice(-4);
}

// ==================== 初始化 ====================

onMounted(() => {
  loadSettlements();
});
</script>

<style scoped>
/* ===== 页面容器 — merchant-settlement 风格 ===== */
.settlements-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-lg) var(--space-lg);
  background: var(--color-bg-page);
  min-height: 100%;
}

.page-header {
  margin-bottom: var(--space-md);
}

.page-title {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
  line-height: var(--line-height-tight);
}

/* ===== Tabs ===== */
.settlements-tabs {
  background: var(--color-bg-base);
  border-radius: var(--radius-md);
  padding: var(--space-md);
  box-shadow: var(--shadow-sm);
}

.settlements-tabs :deep(.el-tabs__header) {
  margin-bottom: var(--space-md);
}

/* ===== 筛选栏 ===== */
.filter-bar {
  margin-bottom: var(--space-md);
  padding-bottom: var(--space-sm);
}

/* ===== 表格 — 财务数据高密度 ===== */
.data-table {
  width: 100%;
  font-size: var(--font-size-sm);
}

.data-table :deep(.el-table__header th) {
  background: var(--color-bg-page);
  color: var(--color-text-secondary);
  font-weight: 600;
  font-size: var(--font-size-sm);
  padding: var(--space-sm) 0;
}

.data-table :deep(.el-table__body td) {
  padding: 10px 0;
  color: var(--color-text-primary);
}

.data-table :deep(.el-table__body tr:hover > td) {
  background: var(--color-bg-elevated);
}

/* ===== 金额列 — 等宽字体 + 右对齐 ===== */
.amount-cell {
  font-family: 'SF Mono', 'Menlo', 'Consolas', 'Courier New', monospace;
  font-variant-numeric: tabular-nums;
  font-weight: 500;
  color: var(--color-text-primary);
}

/* ===== 无操作占位 ===== */
.no-action {
  color: var(--color-text-tertiary);
  font-size: var(--font-size-xs);
}

/* ===== 分页 ===== */
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-md);
  padding-top: var(--space-sm);
}

/* ===== 确认弹窗 — merchant-settlement 模态框覆盖 ===== */
.confirm-body .el-descriptions {
  margin-bottom: 0;
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .settlements-page {
    padding: var(--space-md);
  }

  .filter-bar :deep(.el-radio-group) {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .data-table :deep(.el-table) {
    overflow-x: auto;
  }
}
</style>
