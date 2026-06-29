<template>
  <div class="page-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2 class="page-title">退款审核</h2>
    </div>

    <!-- 状态筛选 Tab -->
    <div class="filter-tabs">
      <el-radio-group v-model="filterStatus" @change="handleStatusChange" size="small">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="applied">待审核</el-radio-button>
        <el-radio-button value="approved">已同意</el-radio-button>
        <el-radio-button value="rejected">已拒绝</el-radio-button>
        <el-radio-button value="processing">处理中</el-radio-button>
        <el-radio-button value="completed">已完成</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 退款表格 -->
    <div class="card">
      <el-table
        :data="refundList"
        v-loading="loading"
        stripe
        style="width: 100%"
        :header-cell-style="{ background: 'var(--app-bg-hover)', color: 'var(--app-text-primary)', fontWeight: 600, fontSize: 'var(--app-font-sm)' }"
        empty-text="暂无退款数据"
      >
        <el-table-column prop="id" label="退款编号" width="100" align="center" />
        <el-table-column prop="order_id" label="关联订单ID" width="110" align="center" />
        <el-table-column prop="reason" label="退款原因" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="reason-text">{{ row.reason }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="退款金额" width="120" align="right">
          <template #default="{ row }">
            <span class="amount">¥{{ parseFloat(row.amount).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="apply_at" label="申请时间" width="170" align="center">
          <template #default="{ row }">
            <span class="time-text">{{ formatTime(row.apply_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" align="center" fixed="right">
          <template #default="{ row }">
            <template v-if="row.status === 'applied'">
              <el-button
                type="success"
                size="small"
                :loading="processingId === row.id && pendingAction === 'approved'"
                @click="handleApprove(row)"
              >
                同意
              </el-button>
              <el-button
                type="danger"
                size="small"
                :loading="processingId === row.id && pendingAction === 'rejected'"
                @click="handleReject(row)"
              >
                拒绝
              </el-button>
            </template>
            <span v-else class="text-secondary">—</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @size-change="fetchRefunds"
          @current-change="fetchRefunds"
        />
      </div>
    </div>

    <!-- 拒绝原因弹窗 -->
    <el-dialog
      v-model="rejectDialogVisible"
      title="拒绝退款"
      width="460px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form
        ref="rejectFormRef"
        :model="rejectForm"
        :rules="rejectRules"
        label-width="80px"
        @submit.prevent
      >
        <el-form-item label="拒绝原因" prop="note">
          <el-input
            v-model="rejectForm.note"
            type="textarea"
            :rows="4"
            maxlength="500"
            show-word-limit
            placeholder="请输入拒绝原因"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button
          type="danger"
          :loading="processingId !== null"
          @click="confirmReject"
        >
          确认拒绝
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { getMerchantRefunds } from '@/api/merchant';
import { approveRefund } from '@/api/admin/refund';

// 状态
const loading = ref(false);
const refundList = ref([]);
const filterStatus = ref('');
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const processingId = ref(null);
const pendingAction = ref(null);

// 拒绝弹窗
const rejectDialogVisible = ref(false);
const rejectFormRef = ref(null);
const currentRefund = ref(null);
const rejectForm = reactive({ note: '' });
const rejectRules = {
  note: [{ required: true, message: '请输入拒绝原因', trigger: 'blur' }]
};

// 状态映射
const statusLabelMap = {
  applied: '待审核',
  approved: '已同意',
  rejected: '已拒绝',
  processing: '处理中',
  completed: '已完成'
};

const statusTagMap = {
  applied: 'warning',
  approved: 'success',
  rejected: 'danger',
  processing: 'primary',
  completed: 'info'
};

function statusLabel(status) {
  return statusLabelMap[status] || status;
}

function statusTagType(status) {
  return statusTagMap[status] || 'info';
}

function formatTime(ts) {
  if (!ts) return '—';
  const d = new Date(ts);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

async function fetchRefunds() {
  loading.value = true;
  try {
    const params = { page: page.value, pageSize: pageSize.value };
    if (filterStatus.value) {
      params.status = filterStatus.value;
    }
    const res = await getMerchantRefunds(params);
    refundList.value = res.data?.list ?? [];
    total.value = res.data?.total ?? 0;
  } catch {
    ElMessage.error('获取退款列表失败，请稍后重试');
  } finally {
    loading.value = false;
  }
}

function handleStatusChange() {
  page.value = 1;
  fetchRefunds();
}

async function handleApprove(row) {
  try {
    await ElMessageBox.confirm(
      `确认同意退款编号「${row.id}」的申请，退款金额 ¥${parseFloat(row.amount).toFixed(2)}？`,
      '同意退款',
      { confirmButtonText: '确认同意', cancelButtonText: '取消', type: 'warning' }
    );
  } catch {
    return;
  }

  processingId.value = row.id;
  pendingAction.value = 'approved';
  try {
    await approveRefund(row.id, { action: 'approved', note: '' });
    ElMessage.success('已同意退款');
    fetchRefunds();
  } catch {
    ElMessage.error('操作失败，请稍后重试');
  } finally {
    processingId.value = null;
    pendingAction.value = null;
  }
}

function handleReject(row) {
  currentRefund.value = row;
  rejectForm.note = '';
  rejectDialogVisible.value = true;
}

async function confirmReject() {
  const valid = await rejectFormRef.value?.validate().catch(() => false);
  if (!valid) return;

  const row = currentRefund.value;
  if (!row) return;

  processingId.value = row.id;
  pendingAction.value = 'rejected';
  try {
    await approveRefund(row.id, { action: 'rejected', note: rejectForm.note });
    ElMessage.success('已拒绝退款');
    rejectDialogVisible.value = false;
    fetchRefunds();
  } catch {
    ElMessage.error('操作失败，请稍后重试');
  } finally {
    processingId.value = null;
    pendingAction.value = null;
  }
}

onMounted(() => {
  fetchRefunds();
});
</script>

<style scoped>
.page-container {
  padding: var(--app-space-xl);
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: var(--app-space-lg);
}

.page-title {
  font-size: var(--app-font-3xl);
  font-weight: 600;
  color: #1e2f4a;
  margin: 0;
}

.filter-tabs {
  margin-bottom: var(--app-space-base);
}

.filter-tabs :deep(.el-radio-button__inner) {
  border-color: #c8d0d8;
  color: #3b4f66;
}

.filter-tabs :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background-color: #2c3e50;
  border-color: #2c3e50;
  color: #fff;
}

.card {
  background: var(--app-bg-container);
  border-radius: var(--app-radius-md);
  box-shadow: var(--app-shadow-level-1);
  overflow: hidden;
}

.amount {
  font-weight: 600;
  color: #c0392b;
  font-family: 'JetBrains Mono', 'Consolas', monospace;
}

.reason-text {
  color: var(--app-text-regular);
  line-height: 1.5;
}

.time-text {
  font-size: var(--app-font-xs);
  color: var(--app-text-secondary);
}

.text-secondary {
  color: var(--app-text-secondary);
  font-size: var(--app-font-xs);
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding: var(--app-space-base) var(--app-space-xl);
  border-top: 1px solid var(--app-border-light);
}
</style>
