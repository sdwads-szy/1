<template>
  <div class="wallet-page">
    <div class="page-header">
      <el-button text @click="$router.push({name:'MerchantDashboard'})">← 返回看板</el-button>
    </div>
    <h1 class="page-title">结算与提现</h1>

    <!-- 余额卡片 -->
    <div class="balance-cards">
      <el-card
        v-for="card in balanceCards"
        :key="card.key"
        :class="['balance-card', { 'balance-card--available': card.highlight }]"
        shadow="never"
      >
        <template v-if="walletLoading">
          <el-skeleton :rows="2" animated />
        </template>
        <template v-else>
          <p class="balance-card__label">{{ card.label }}</p>
          <p class="balance-card__value">
            <span class="balance-card__symbol">¥</span>
            {{ card.displayValue }}
          </p>
        </template>
      </el-card>
    </div>

    <!-- 结算明细 -->
    <div class="section">
      <div class="section__header">
        <h2 class="section__title">结算明细</h2>
      </div>

      <!-- 加载态 -->
      <el-table v-if="settlementsLoading && settlements.length === 0" v-loading="true" :data="[]" stripe>
        <el-table-column prop="period" label="结算周期" />
        <el-table-column prop="amount" label="结算金额" />
        <el-table-column prop="status" label="状态" />
        <el-table-column prop="paidAt" label="打款时间" />
      </el-table>

      <!-- 空状态 -->
      <div v-else-if="!settlementsLoading && settlements.length === 0" class="empty-state">
        <el-empty description="暂无结算记录">
          <template #description>
            <p class="empty-state__title">暂无结算记录</p>
            <p class="empty-state__desc">您的店铺产生交易后，结算明细将显示在这里</p>
          </template>
        </el-empty>
      </div>

      <!-- 数据表格 -->
      <el-table v-else :data="settlements" stripe v-loading="settlementsLoading" class="data-table">
        <el-table-column prop="period" label="结算周期" width="140" />
        <el-table-column prop="amount" label="结算金额" align="right">
          <template #default="{ row }">
            <span class="amount-cell">¥{{ formatAmount(row.amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag
              :type="settlementStatusMap[row.status]?.type || 'info'"
              size="small"
              effect="plain"
            >
              {{ settlementStatusMap[row.status]?.text || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="paidAt" label="打款时间" width="180">
          <template #default="{ row }">
            {{ row.paidAt || '-' }}
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div v-if="settlementsTotal > settlementPageSize" class="pagination-wrapper">
        <el-pagination
          v-model:current-page="settlementPage"
          :page-size="settlementPageSize"
          :total="settlementsTotal"
          layout="total, prev, pager, next"
          @current-change="fetchSettlements"
        />
      </div>
    </div>

    <!-- 提现操作区 -->
    <div class="section withdraw-action">
      <el-button
        type="primary"
        size="large"
        class="withdraw-btn"
        :disabled="parseFloat(wallet.balance) <= 0"
        @click="openWithdrawModal"
      >
        提现
      </el-button>
      <span v-if="parseFloat(wallet.balance) <= 0 && !walletLoading" class="withdraw-hint">
        可提现金额不足
      </span>
    </div>

    <!-- 提现记录 -->
    <div class="section">
      <h2 class="section__title">提现记录</h2>

      <el-tabs v-model="withdrawalTab" class="withdrawal-tabs" @tab-change="handleWithdrawalTabChange">
        <el-tab-pane label="全部" name="all" />
        <el-tab-pane label="处理中" name="processing" />
        <el-tab-pane label="已到账" name="paid" />
        <el-tab-pane label="失败" name="failed" />
      </el-tabs>

      <!-- 加载态 -->
      <el-table v-if="withdrawalsLoading && withdrawals.length === 0" v-loading="true" :data="[]" stripe>
        <el-table-column prop="createdAt" label="申请时间" />
        <el-table-column prop="requestNo" label="提现单号" />
        <el-table-column prop="amount" label="金额" />
        <el-table-column prop="bankAccount" label="银行账号" />
        <el-table-column prop="status" label="状态" />
        <el-table-column prop="reviewReason" label="审核意见" />
      </el-table>

      <!-- 空状态 -->
      <div v-else-if="!withdrawalsLoading && withdrawals.length === 0" class="empty-state">
        <el-empty description="还没有提现记录">
          <template #description>
            <p class="empty-state__title">还没有提现记录</p>
            <p class="empty-state__desc">可提现金额大于 ¥1.00 时即可申请提现</p>
          </template>
          <template #default>
            <el-button type="primary" :disabled="parseFloat(wallet.balance) < 1" @click="openWithdrawModal">
              {{ parseFloat(wallet.balance) < 1 ? '余额不足' : '去提现' }}
            </el-button>
          </template>
        </el-empty>
      </div>

      <!-- 数据表格 -->
      <el-table v-else :data="withdrawals" stripe v-loading="withdrawalsLoading" class="data-table">
        <el-table-column prop="createdAt" label="申请时间" width="180" />
        <el-table-column prop="requestNo" label="提现单号" width="200" />
        <el-table-column prop="amount" label="金额" align="right" width="140">
          <template #default="{ row }">
            <span class="amount-cell">¥{{ formatAmount(row.amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="bankAccount" label="银行账号" width="200">
          <template #default="{ row }">
            <span class="bank-account-cell">{{ row.bankAccount || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag
              :type="withdrawalStatusMap[row.status]?.type || 'info'"
              size="small"
              effect="plain"
            >
              {{ withdrawalStatusMap[row.status]?.text || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reviewReason" label="审核意见" min-width="160">
          <template #default="{ row }">
            {{ row.reviewReason || '-' }}
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div v-if="withdrawalsTotal > withdrawalPageSize" class="pagination-wrapper">
        <el-pagination
          v-model:current-page="withdrawalPage"
          :page-size="withdrawalPageSize"
          :total="withdrawalsTotal"
          layout="total, prev, pager, next"
          @current-change="fetchWithdrawals"
        />
      </div>
    </div>

    <!-- 提现弹窗 -->
    <el-dialog
      v-model="withdrawModalVisible"
      title="申请提现"
      width="480px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form
        ref="withdrawFormRef"
        :model="withdrawForm"
        :rules="withdrawRules"
        label-width="100px"
        label-position="right"
      >
        <el-form-item label="提现金额" prop="amount">
          <el-input-number
            v-model="withdrawForm.amount"
            :precision="2"
            :min="0.01"
            :max="parseFloat(wallet.balance)"
            :controls="false"
            placeholder="请输入提现金额"
            style="width: 100%"
          >
            <template #prefix>¥</template>
          </el-input-number>
          <p class="form-hint">可提现余额：¥{{ formatAmount(wallet.balance) }}</p>
        </el-form-item>

        <el-form-item label="银行账号" prop="bankAccount">
          <el-input
            v-model="withdrawForm.bankAccount"
            placeholder="请输入收款银行账号"
            maxlength="30"
            show-word-limit
          />
        </el-form-item>

        <!-- 大额提现警示 -->
        <el-alert
          v-if="withdrawForm.amount >= 50000"
          type="warning"
          :closable="false"
          show-icon
          class="alert-large"
        >
          <template #title>
            大额提现将在 1-3 个工作日审核后到账
          </template>
        </el-alert>
      </el-form>

      <template #footer>
        <el-button @click="withdrawModalVisible = false">取消</el-button>
        <el-button
          type="primary"
          class="withdraw-btn"
          :loading="withdrawSubmitting"
          @click="handleWithdrawSubmit"
        >
          确认提现
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { getMerchantWallet } from '@/api/merchant-wallet';
import { getMerchantSettlements } from '@/api/merchant-settlements';
import { submitWithdrawal, getWithdrawals } from '@/api/merchant-withdrawals';

// ── 钱包余额 ──
const wallet = ref({ balance: '0.00', frozenBalance: '0.00', totalEarned: '0.00' });
const walletLoading = ref(false);

// ── 结算明细 ──
const settlements = ref([]);
const settlementsTotal = ref(0);
const settlementsLoading = ref(false);
const settlementPage = ref(1);
const settlementPageSize = ref(20);

// ── 提现记录 ──
const withdrawals = ref([]);
const withdrawalsTotal = ref(0);
const withdrawalsLoading = ref(false);
const withdrawalPage = ref(1);
const withdrawalPageSize = ref(20);
const withdrawalTab = ref('all');

// ── 提现弹窗 ──
const withdrawModalVisible = ref(false);
const withdrawSubmitting = ref(false);
const withdrawFormRef = ref(null);
const withdrawForm = reactive({
  amount: null,
  bankAccount: ''
});

// ── 状态映射 ──
const settlementStatusMap = {
  pending: { text: '待确认', type: 'warning' },
  confirmed: { text: '已确认', type: 'info' },
  paid: { text: '已打款', type: 'info' },
  completed: { text: '已完成', type: 'success' },
  clawed_back: { text: '已追索', type: 'danger' }
};

const withdrawalStatusMap = {
  pending: { text: '待审核', type: 'warning' },
  approved: { text: '已通过', type: 'info' },
  paid: { text: '已打款', type: 'success' },
  rejected: { text: '已驳回', type: 'danger' }
};

// ── 格式化金额 ──
function formatAmount(value) {
  const num = parseFloat(value);
  if (isNaN(num)) return '0.00';
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// ── 余额卡片数据 ──
const balanceCards = computed(() => {
  const pendingSettlements = settlements.value
    .filter(s => s.status === 'pending')
    .reduce((sum, s) => sum + parseFloat(s.amount || 0), 0);

  return [
    {
      label: '待结算',
      value: pendingSettlements.toFixed(2),
      displayValue: formatAmount(pendingSettlements),
      key: 'pending',
      highlight: false
    },
    {
      label: '可提现',
      value: wallet.value.balance,
      displayValue: formatAmount(wallet.value.balance),
      key: 'available',
      highlight: true
    },
    {
      label: '提现中',
      value: wallet.value.frozenBalance,
      displayValue: formatAmount(wallet.value.frozenBalance),
      key: 'frozen',
      highlight: false
    },
    {
      label: '已结算累计',
      value: wallet.value.totalEarned,
      displayValue: formatAmount(wallet.value.totalEarned),
      key: 'total',
      highlight: false
    }
  ];
});

// ── 提现表单校验 ──
const withdrawRules = {
  amount: [
    { required: true, message: '请输入提现金额', trigger: 'blur' },
    {
      type: 'number',
      min: 0.01,
      message: '提现金额必须大于 0',
      trigger: 'blur'
    },
    {
      validator: (_rule, value, callback) => {
        if (value > parseFloat(wallet.value.balance)) {
          callback(new Error('提现金额不能超过可用余额'));
        } else {
          callback();
        }
      },
      trigger: 'blur'
    }
  ],
  bankAccount: [
    { required: true, message: '请输入银行账号', trigger: 'blur' },
    { min: 1, message: '请输入有效的银行账号', trigger: 'blur' }
  ]
};

// ── 获取钱包余额 ──
async function fetchWallet() {
  walletLoading.value = true;
  try {
    const res = await getMerchantWallet();
    if (res.data) {
      wallet.value = {
        balance: res.data.balance || '0.00',
        frozenBalance: res.data.frozenBalance || '0.00',
        totalEarned: res.data.totalEarned || '0.00'
      };
    }
  } catch (err) {
    ElMessage.error('钱包数据加载失败，请检查网络连接后重试');
  } finally {
    walletLoading.value = false;
  }
}

// ── 获取结算单列表 ──
async function fetchSettlements(page = 1) {
  settlementsLoading.value = true;
  settlementPage.value = page;
  try {
    const res = await getMerchantSettlements({ page, pageSize: settlementPageSize.value });
    if (res.data) {
      settlements.value = res.data.list || [];
      settlementsTotal.value = res.data.total || 0;
    }
  } catch (err) {
    ElMessage.error('结算数据加载失败，请检查网络连接后重试');
  } finally {
    settlementsLoading.value = false;
  }
}

// ── 获取提现记录 ──
async function fetchWithdrawals(page = 1) {
  withdrawalsLoading.value = true;
  withdrawalPage.value = page;
  try {
    const params = { page, pageSize: withdrawalPageSize.value };
    if (withdrawalTab.value === 'processing') {
      params.status = 'pending,approved';
    } else if (withdrawalTab.value === 'paid') {
      params.status = 'paid';
    } else if (withdrawalTab.value === 'failed') {
      params.status = 'rejected';
    }
    const res = await getWithdrawals(params);
    if (res.data) {
      withdrawals.value = res.data.list || [];
      withdrawalsTotal.value = res.data.total || 0;
    }
  } catch (err) {
    ElMessage.error('提现记录加载失败，请检查网络连接后重试');
  } finally {
    withdrawalsLoading.value = false;
  }
}

// ── 提现 Tab 切换 ──
function handleWithdrawalTabChange() {
  withdrawalPage.value = 1;
  fetchWithdrawals(1);
}

// ── 打开提现弹窗 ──
function openWithdrawModal() {
  withdrawForm.amount = null;
  withdrawForm.bankAccount = '';
  withdrawModalVisible.value = true;
}

// ── 提交提现 ──
async function handleWithdrawSubmit() {
  const valid = await withdrawFormRef.value?.validate().catch(() => false);
  if (!valid) return;

  const amount = withdrawForm.amount;
  const bankAccount = withdrawForm.bankAccount;
  const last4 = bankAccount.slice(-4);

  // 二次确认
  let confirmMessage;
  if (amount >= 50000) {
    confirmMessage = `您正在申请大额提现 ${formatAmount(amount)}，预计 1-3 个工作日审核后到账。确认继续？`;
  } else {
    confirmMessage = `确认将 ${formatAmount(amount)} 提现至尾号 ${last4} 的银行账户？预计 1-2 个工作日到账。`;
  }

  try {
    await ElMessageBox.confirm(confirmMessage, '确认提现', {
      confirmButtonText: '确认提现',
      cancelButtonText: '取消',
      type: 'warning'
    });
  } catch {
    return;
  }

  withdrawSubmitting.value = true;
  try {
    const res = await submitWithdrawal({
      amount: String(amount),
      bankAccount
    });

    // mock 提示
    if (res.data?.mockHint) {
      ElMessage.info(res.data.mockHint);
    }

    ElMessage.success('提现申请已提交，预计 1-2 个工作日到账');
    withdrawModalVisible.value = false;

    // 刷新数据
    await Promise.all([fetchWallet(), fetchWithdrawals(1)]);
  } catch (err) {
    const msg = err?.response?.data?.message || err?.message || '提现申请提交失败，请稍后重试';
    if (err?.response?.status === 409) {
      ElMessage.warning('余额已变动，请刷新后重试');
      await fetchWallet();
    } else {
      ElMessage.error(msg + '。如持续失败请联系平台客服');
    }
  } finally {
    withdrawSubmitting.value = false;
  }
}

// ── 初始化 ──
onMounted(() => {
  Promise.all([
    fetchWallet(),
    fetchSettlements(1),
    fetchWithdrawals(1)
  ]);
});
</script>

<style scoped>
/* ── 页面级财务令牌 ── */
.wallet-page {
  --ps-amount-in: hsl(155, 75%, 42%);
  --ps-amount-in-bg: hsl(155, 60%, 95%);
  --ps-amount-out: hsl(15, 6%, 48%);
  --ps-amount-out-bg: hsl(15, 4%, 95%);
  --ps-status-pending: hsl(32, 90%, 52%);
  --ps-status-progress: hsl(210, 70%, 55%);
  --ps-balance-glow: rgba(34, 197, 94, 0.15);
  --ps-withdraw-highlight: hsl(15, 85%, 50%);

  max-width: 960px;
  margin: 0 auto;
  padding: var(--space-lg);
}

.page-title {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-lg) 0;
  line-height: var(--line-height-tight);
}

/* ── 余额卡片 ── */
.balance-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-md);
  margin-bottom: var(--space-xl);
}

.balance-card {
  min-height: 120px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-base);
  box-shadow: var(--shadow-sm);
  cursor: default;
}

.balance-card :deep(.el-card__body) {
  padding: var(--space-lg);
  display: flex;
  flex-direction: column;
  justify-content: center;
  height: 100%;
}

.balance-card--available {
  border-bottom: 3px solid var(--color-success);
  box-shadow: var(--shadow-sm), 0 0 24px -6px var(--ps-balance-glow);
}

.balance-card__label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-xs) 0;
  line-height: var(--line-height-tight);
}

.balance-card__value {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.5px;
  line-height: var(--line-height-tight);
  font-family: 'SF Mono', 'Menlo', 'Consolas', monospace;
}

.balance-card__symbol {
  font-size: var(--font-size-lg);
  font-weight: 400;
  color: var(--color-text-secondary);
  margin-right: 2px;
}

/* ── 分区 ── */
.section {
  background: var(--color-bg-base);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  margin-bottom: var(--space-lg);
  box-shadow: var(--shadow-sm);
}

.section__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-md);
}

.section__title {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
  line-height: var(--line-height-tight);
}

/* ── 数据表格 ── */
.data-table {
  width: 100%;
}

.data-table :deep(.el-table__header th) {
  background: var(--color-bg-page);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: 600;
  padding: var(--space-md) 0;
}

.data-table :deep(.el-table__body tr) {
  height: 44px;
}

.data-table :deep(.el-table__body tr:hover > td) {
  background: var(--color-bg-elevated);
  transition: background var(--duration-instant) var(--ease-smooth);
}

.data-table :deep(.el-table--striped .el-table__body tr.el-table__row--striped td) {
  background: rgba(245, 244, 243, 0.5);
}

.amount-cell {
  font-family: 'SF Mono', 'Menlo', 'Consolas', monospace;
  font-variant-numeric: tabular-nums;
  font-size: var(--font-size-sm);
  font-weight: 500;
}

/* ── 分页 ── */
.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-md);
  padding-top: var(--space-md);
  border-top: 1px solid var(--color-border);
}

/* ── 提现操作区 ── */
.withdraw-action {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.withdraw-btn {
  min-width: 160px;
  height: 48px;
  font-size: var(--font-size-md);
  background: var(--ps-withdraw-highlight);
  border-color: var(--ps-withdraw-highlight);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  transition: all var(--duration-fast) var(--ease-smooth);
}

.withdraw-btn:hover {
  background: var(--color-primary-700);
  border-color: var(--color-primary-700);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.withdraw-btn:active {
  background: var(--color-primary-800);
  border-color: var(--color-primary-800);
  transform: scale(0.98);
}

.withdraw-hint {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

/* ── 提现记录 Tab ── */
.withdrawal-tabs {
  margin-bottom: var(--space-md);
}

.withdrawal-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
}

/* ── 空状态 ── */
.empty-state {
  padding: var(--space-2xl) var(--space-lg);
  text-align: center;
}

.empty-state__title {
  font-size: var(--font-size-lg);
  color: var(--color-text-secondary);
  margin: var(--space-md) 0 var(--space-xs) 0;
}

.empty-state__desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  margin: 0 0 var(--space-md) 0;
}

/* ── 提现弹窗 ── */
.form-hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin: var(--space-xs) 0 0 0;
  line-height: var(--line-height-tight);
}

.alert-large {
  margin-top: var(--space-sm);
}

.bank-account-cell {
  font-family: 'SF Mono', 'Menlo', 'Consolas', monospace;
  font-size: var(--font-size-sm);
  letter-spacing: 0.5px;
}

/* ── 响应式 ── */
@media (max-width: 768px) {
  .wallet-page {
    padding: var(--space-md);
  }

  .balance-cards {
    grid-template-columns: repeat(2, 1fr);
  }

  .data-table {
    overflow-x: auto;
  }

  .withdraw-btn {
    min-width: auto;
    width: 100%;
  }

  .withdraw-action {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
