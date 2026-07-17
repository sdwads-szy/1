<template>
  <div class="arbitration-workspace">
    <!-- 统计卡片行 -->
    <div class="page-header">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ name: 'AdminDashboard' }">平台后台</el-breadcrumb-item>
        <el-breadcrumb-item>退款仲裁</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <div class="stats-row">
      <div class="stat-card">
        <span class="stat-label">待仲裁</span>
        <span class="stat-value">{{ stats.arbitrating }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">今日裁决</span>
        <span class="stat-value">{{ stats.todayRuled }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">强制退款</span>
        <span class="stat-value stat-value--success">{{ stats.forceRefund }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">驳回申请</span>
        <span class="stat-value stat-value--error">{{ stats.dismissed }}</span>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-select
          v-model="filterStatus"
          placeholder="仲裁状态"
          clearable
          size="default"
          style="width: 180px"
        >
          <el-option label="全部状态" value="" />
          <el-option label="待仲裁" value="arbitrating" />
          <el-option label="已驳回待介入" value="rejected" />
        </el-select>
        <el-button type="primary" @click="handleFilter">查询</el-button>
      </div>
      <div class="toolbar-right">
        <el-checkbox v-model="onlyUrgent" size="default">仅看加急</el-checkbox>
      </div>
    </div>

    <!-- 主内容区：左右分栏 -->
    <div class="content-split">
      <!-- 左侧列表 -->
      <div class="list-panel" :class="{ 'list-panel--full': !selectedRow }">
        <el-table
          ref="tableRef"
          :data="list"
          stripe
          highlight-current-row
          @row-click="handleRowClick"
          @selection-change="handleSelectionChange"
          v-loading="loading"
          element-loading-text="加载仲裁工单中..."
          empty-text="全部仲裁工单已处理完毕"
          row-key="id"
          size="small"
        >
          <el-table-column type="selection" width="48" />
          <el-table-column prop="requestNo" label="售后单号" min-width="160">
            <template #default="{ row }">
              <span class="cell-request-no">{{ row.requestNo }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="type" label="售后类型" width="100">
            <template #default="{ row }">
              <el-tag
                :type="row.type === 'only_refund' ? 'warning' : 'info'"
                size="small"
                class="review-tag"
              >
                {{ row.type === 'only_refund' ? '仅退款' : '退货退款' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="reason" label="申请原因" min-width="180" show-overflow-tooltip />
          <el-table-column prop="amount" label="退款金额" width="110" align="right">
            <template #default="{ row }">
              <span class="cell-amount">¥{{ Number(row.amount).toFixed(2) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.status)" size="small" class="review-tag">
                {{ statusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="createdAt" label="申请时间" width="160" />
        </el-table>

        <!-- 分页 -->
        <div class="pagination-wrap">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.pageSize"
            :total="pagination.total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @current-change="fetchList"
            @size-change="fetchList"
          />
        </div>
      </div>

      <!-- 右侧详情面板 -->
      <transition name="panel-slide">
        <div v-if="selectedRow" class="detail-panel">
          <div class="detail-header">
            <h3 class="detail-title">仲裁详情</h3>
            <el-button
              text
              @click="closeDetail"
              class="detail-close-btn"
            >
              <el-icon><Close /></el-icon>
            </el-button>
          </div>

          <div class="detail-body">
            <div class="detail-section">
              <h4 class="section-title">售后信息</h4>
              <div class="info-grid">
                <div class="info-item">
                  <span class="info-label">售后单号</span>
                  <span class="info-value">{{ selectedRow.requestNo }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">关联子订单</span>
                  <span class="info-value">#{{ selectedRow.subOrderId }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">申请人ID</span>
                  <span class="info-value">{{ selectedRow.userId }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">售后类型</span>
                  <span class="info-value">{{ selectedRow.type === 'only_refund' ? '仅退款' : '退货退款' }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">申请金额</span>
                  <span class="info-value info-value--amount">¥{{ Number(selectedRow.amount).toFixed(2) }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">当前状态</span>
                  <el-tag :type="statusTagType(selectedRow.status)" size="small" class="review-tag">
                    {{ statusLabel(selectedRow.status) }}
                  </el-tag>
                </div>
                <div class="info-item">
                  <span class="info-label">申请时间</span>
                  <span class="info-value">{{ selectedRow.createdAt }}</span>
                </div>
              </div>
            </div>

            <div class="detail-section">
              <h4 class="section-title">申请原因</h4>
              <p class="reason-text">{{ selectedRow.reason }}</p>
            </div>

            <div class="detail-section">
              <h4 class="section-title">商家审核意见</h4>
              <p class="reason-text" :class="{ 'reason-text--empty': !selectedRow.merchantReviewReason }">
                {{ selectedRow.merchantReviewReason || '商家未提供审核意见' }}
              </p>
            </div>

            <!-- 裁决表单：仅 arbitrating 状态显示 -->
            <div v-if="selectedRow.status === 'arbitrating'" class="detail-section">
              <h4 class="section-title">平台裁决</h4>
              <el-form
                ref="arbitrateFormRef"
                :model="arbitrateForm"
                :rules="arbitrateRules"
                label-position="top"
              >
                <el-form-item label="裁决结果" prop="ruling">
                  <el-radio-group v-model="arbitrateForm.ruling">
                    <el-radio value="force_refund">强制退款</el-radio>
                    <el-radio value="dismiss">驳回申请</el-radio>
                  </el-radio-group>
                </el-form-item>
                <el-form-item label="裁决理由" prop="reason">
                  <el-input
                    v-model="arbitrateForm.reason"
                    type="textarea"
                    :rows="3"
                    maxlength="500"
                    show-word-limit
                    placeholder="请详细说明裁决理由，不超过500字"
                  />
                </el-form-item>
              </el-form>
            </div>

            <!-- 已裁决状态：展示裁决结果 -->
            <div v-else-if="selectedRow.status !== 'arbitrating' && selectedRow.arbitrationRuling" class="detail-section">
              <h4 class="section-title">裁决记录</h4>
              <p class="reason-text">{{ selectedRow.arbitrationRuling }}</p>
            </div>
          </div>

          <!-- 底部操作栏 -->
          <div v-if="selectedRow.status === 'arbitrating'" class="detail-footer">
            <el-button
              type="success"
              @click="handleArbitrate('force_refund')"
              :loading="submitting"
            >
              通过 · 强制退款
            </el-button>
            <el-button
              type="danger"
              @click="handleArbitrate('dismiss')"
              :loading="submitting"
            >
              驳回申请
            </el-button>
          </div>
        </div>
      </transition>
    </div>

    <!-- 批量操作栏 -->
    <transition name="batch-slide">
      <div v-if="selectedRows.length > 0" class="batch-bar">
        <span class="batch-info">已选 {{ selectedRows.length }} 项</span>
        <div class="batch-actions">
          <el-button
            text
            class="batch-btn"
            @click="batchArbitrate('force_refund')"
            :disabled="!canBatchArbitrate"
          >
            批量强制退款
          </el-button>
          <el-button
            text
            class="batch-btn"
            @click="batchArbitrate('dismiss')"
            :disabled="!canBatchArbitrate"
          >
            批量驳回
          </el-button>
        </div>
      </div>
    </transition>

    <!-- 批量裁决理由对话框 -->
    <el-dialog
      v-model="batchDialogVisible"
      title="批量裁决"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="batchFormRef"
        :model="batchForm"
        :rules="batchRules"
        label-position="top"
      >
        <el-form-item label="裁决理由（将应用于所有选中项）" prop="reason">
          <el-input
            v-model="batchForm.reason"
            type="textarea"
            :rows="4"
            maxlength="500"
            show-word-limit
            placeholder="请输入统一的裁决理由"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchDialogVisible = false">取消</el-button>
        <el-button
          :type="batchRuling === 'force_refund' ? 'success' : 'danger'"
          @click="confirmBatchArbitrate"
          :loading="batchSubmitting"
        >
          确认{{ batchRuling === 'force_refund' ? '强制退款' : '驳回' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Close } from '@element-plus/icons-vue';
import { getArbitrationList, arbitrateRefund } from '@/api/admin-refunds';

// ==================== 状态 ====================
const loading = ref(false);
const submitting = ref(false);
const batchSubmitting = ref(false);
const list = ref([]);
const tableRef = ref(null);
const arbitrateFormRef = ref(null);
const batchFormRef = ref(null);

const filterStatus = ref('arbitrating');
const onlyUrgent = ref(false);
const selectedRows = ref([]);
const selectedRow = ref(null);

const batchDialogVisible = ref(false);
const batchRuling = ref('');

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
});

const stats = reactive({
  arbitrating: 0,
  todayRuled: 0,
  forceRefund: 0,
  dismissed: 0
});

const arbitrateForm = reactive({
  ruling: 'force_refund',
  reason: ''
});

const batchForm = reactive({
  reason: ''
});

// ==================== 表单校验规则 ====================
const arbitrateRules = {
  ruling: [{ required: true, message: '请选择裁决结果', trigger: 'change' }],
  reason: [
    { required: true, message: '请输入裁决理由', trigger: 'blur' },
    { min: 1, max: 500, message: '裁决理由长度在1-500字符之间', trigger: 'blur' }
  ]
};

const batchRules = {
  reason: [
    { required: true, message: '请输入裁决理由', trigger: 'blur' },
    { min: 1, max: 500, message: '裁决理由长度在1-500字符之间', trigger: 'blur' }
  ]
};

// ==================== 计算属性 ====================
const canBatchArbitrate = computed(() => {
  return selectedRows.value.length > 0 && selectedRows.value.every(r => r.status === 'arbitrating');
});

// ==================== 状态映射 ====================
function statusTagType(status) {
  const map = {
    arbitrating: 'warning',
    refunding: '',
    completed: 'success',
    rejected: 'danger',
    closed: 'info',
    retry: 'warning',
    pending: '',
    awaiting_return: '',
    awaiting_merchant_receive: ''
  };
  return map[status] || '';
}

function statusLabel(status) {
  const map = {
    pending: '待审核',
    awaiting_return: '待退货',
    awaiting_merchant_receive: '待商家收货',
    refunding: '退款中',
    completed: '已完成',
    rejected: '已驳回',
    arbitrating: '待仲裁',
    closed: '已关闭',
    retry: '退款重试'
  };
  return map[status] || status;
}

// ==================== 数据获取 ====================
async function fetchList() {
  loading.value = true;
  try {
    const params = {
      page: pagination.page,
      pageSize: pagination.pageSize
    };
    if (filterStatus.value) {
      params.status = filterStatus.value;
    }
    const res = await getArbitrationList(params);
    if (res.data && res.data.success !== false) {
      const data = res.data.data || res.data;
      list.value = data.list || [];
      pagination.total = data.total || 0;
      pagination.page = data.page || pagination.page;
      pagination.pageSize = data.pageSize || pagination.pageSize;
    }
  } catch (err) {
    ElMessage.error('仲裁工单列表加载失败，请检查网络后重试。');
  } finally {
    loading.value = false;
  }
}

// ==================== 交互处理 ====================
function handleFilter() {
  pagination.page = 1;
  closeDetail();
  fetchList();
}

function handleRowClick(row) {
  selectedRow.value = row;
  arbitrateForm.ruling = 'force_refund';
  arbitrateForm.reason = '';
  arbitrateFormRef.value?.resetFields();
}

function closeDetail() {
  selectedRow.value = null;
  arbitrateForm.ruling = 'force_refund';
  arbitrateForm.reason = '';
}

function handleSelectionChange(rows) {
  selectedRows.value = rows;
}

async function handleArbitrate(ruling) {
  if (ruling !== arbitrateForm.ruling) {
    arbitrateForm.ruling = ruling;
  }

  try {
    await arbitrateFormRef.value?.validate();
  } catch {
    return;
  }

  try {
    await ElMessageBox.confirm(
      ruling === 'force_refund'
        ? '确认强制退款？此操作将立即进入退款流程。'
        : '确认驳回该售后申请？请确保裁决理由充分。',
      '确认裁决',
      {
        confirmButtonText: ruling === 'force_refund' ? '确认强制退款' : '确认驳回',
        cancelButtonText: '取消',
        type: ruling === 'force_refund' ? 'success' : 'warning'
      }
    );
  } catch {
    return;
  }

  submitting.value = true;
  try {
    await arbitrateRefund({
      id: selectedRow.value.id,
      ruling,
      reason: arbitrateForm.reason
    });
    ElMessage.success(ruling === 'force_refund' ? '已裁决：强制退款，退款流程已启动。' : '已裁决：驳回申请。');

    // 更新内存中的行状态（乐观更新）
    const idx = list.value.findIndex(item => item.id === selectedRow.value.id);
    if (idx !== -1) {
      list.value[idx].status = ruling === 'force_refund' ? 'refunding' : 'closed';
      list.value[idx].arbitrationRuling = arbitrateForm.reason;
    }
    closeDetail();
  } catch (err) {
    const msg = err?.response?.data?.message || err?.message || '裁决操作失败，请重试。';
    ElMessage.error(msg);
  } finally {
    submitting.value = false;
  }
}

function batchArbitrate(ruling) {
  batchRuling.value = ruling;
  batchForm.reason = '';
  batchDialogVisible.value = true;
}

async function confirmBatchArbitrate() {
  try {
    await batchFormRef.value?.validate();
  } catch {
    return;
  }

  const count = selectedRows.value.length;
  try {
    await ElMessageBox.confirm(
      `确认批量${batchRuling.value === 'force_refund' ? '强制退款' : '驳回'} ${count} 项售后申请？此操作不可撤回。`,
      '批量裁决确认',
      {
        confirmButtonText: `确认${batchRuling.value === 'force_refund' ? '强制退款' : '驳回'} ${count} 项`,
        cancelButtonText: '取消',
        type: batchRuling.value === 'force_refund' ? 'success' : 'warning'
      }
    );
  } catch {
    return;
  }

  batchSubmitting.value = true;
  const arbitratingItems = selectedRows.value.filter(r => r.status === 'arbitrating');
  let successCount = 0;
  let failCount = 0;

  try {
    const promises = arbitratingItems.map(item =>
      arbitrateRefund({
        id: item.id,
        ruling: batchRuling.value,
        reason: batchForm.reason
      }).then(() => {
        successCount++;
        const idx = list.value.findIndex(i => i.id === item.id);
        if (idx !== -1) {
          list.value[idx].status = batchRuling.value === 'force_refund' ? 'refunding' : 'closed';
          list.value[idx].arbitrationRuling = batchForm.reason;
        }
      }).catch(() => {
        failCount++;
      })
    );

    await Promise.allSettled(promises);

    if (failCount === 0) {
      ElMessage.success(`批量裁决完成：成功 ${successCount} 项。`);
    } else {
      ElMessage.warning(`批量裁决完成：成功 ${successCount} 项，失败 ${failCount} 项。`);
    }
  } catch (err) {
    ElMessage.error('批量裁决操作失败，请重试。');
  } finally {
    batchSubmitting.value = false;
    batchDialogVisible.value = false;
    tableRef.value?.clearSelection();
  }
}

// ==================== 生命周期 ====================
onMounted(() => {
  fetchList();
});
</script>

<style scoped>
.arbitration-workspace {
  max-width: 1440px;
  margin: 0 auto;
  padding: var(--space-lg);
  background: var(--page-review-bg-workspace, hsl(25, 4%, 96%));
  min-height: 100vh;
}

/* ══ 统计卡片 ══ */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
}

.stat-card {
  background: var(--color-bg-base, #fff);
  border: 1px solid var(--color-border, hsl(25, 7%, 90%));
  border-radius: var(--page-review-radius-card, 8px);
  padding: var(--space-md);
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.stat-label {
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-secondary, hsl(25, 7%, 42%));
}

.stat-value {
  font-size: var(--font-size-2xl, 28px);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-primary, hsl(25, 9%, 12%));
}

.stat-value--success {
  color: var(--color-success, hsl(145, 70%, 42%));
}

.stat-value--error {
  color: var(--color-error, hsl(0, 80%, 52%));
}

/* ══ 工具栏 ══ */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-md);
  padding: var(--space-md);
  background: var(--color-bg-base, #fff);
  border: 1px solid var(--color-border, hsl(25, 7%, 90%));
  border-radius: var(--page-review-radius-card, 8px);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.toolbar-right {
  display: flex;
  align-items: center;
}

/* ══ 内容分栏 ══ */
.content-split {
  display: flex;
  gap: var(--space-md);
  min-height: 400px;
}

.list-panel {
  flex: 1;
  background: var(--color-bg-base, #fff);
  border: 1px solid var(--color-border, hsl(25, 7%, 90%));
  border-radius: var(--page-review-radius-card, 8px);
  overflow: hidden;
  transition: flex 0.225s cubic-bezier(0.16, 1, 0.3, 1);
}

.list-panel--full {
  flex: 1;
}

/* ══ 表格覆盖 ══ */
:deep(.el-table) {
  --el-table-row-hover-bg-color: var(--color-bg-page, hsl(25, 5%, 97%));
}

:deep(.el-table th) {
  background: var(--color-bg-page, hsl(25, 5%, 97%));
  color: var(--color-text-secondary, hsl(25, 7%, 42%));
  font-size: var(--font-size-sm, 12.25px);
  font-weight: 600;
  padding: var(--space-sm) 0;
}

:deep(.el-table td) {
  padding: var(--space-sm) 0;
  font-size: var(--font-size-sm, 12.25px);
}

:deep(.el-table .el-table__row--striped) {
  background: var(--color-bg-page, hsl(25, 5%, 97%));
}

.cell-request-no {
  font-weight: 600;
  color: var(--color-primary-600, hsl(25, 85%, 45%));
}

.cell-amount {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.review-tag {
  border-radius: var(--page-review-radius-tag, 4px) !important;
}

/* ══ 分页 ══ */
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  padding: var(--space-md);
  border-top: 1px solid var(--color-border, hsl(25, 7%, 90%));
}

/* ══ 详情面板 ══ */
.detail-panel {
  width: 420px;
  flex-shrink: 0;
  background: var(--color-bg-base, #fff);
  border: 1px solid var(--color-border, hsl(25, 7%, 90%));
  border-radius: var(--page-review-radius-card, 8px);
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 220px);
  overflow: hidden;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-lg);
  border-bottom: 1px solid var(--color-border, hsl(25, 7%, 90%));
  flex-shrink: 0;
}

.detail-title {
  font-size: var(--font-size-md, 15.75px);
  font-weight: 600;
  margin: 0;
  color: var(--color-text-primary, hsl(25, 9%, 12%));
}

.detail-close-btn {
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
}

.detail-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-lg);
}

.detail-section {
  margin-bottom: var(--space-lg);
}

.section-title {
  font-size: var(--font-size-sm, 12.25px);
  font-weight: 600;
  color: var(--color-text-secondary, hsl(25, 7%, 42%));
  margin: 0 0 var(--space-sm) 0;
  padding-bottom: var(--space-xs);
  border-bottom: 1px solid var(--color-border, hsl(25, 7%, 90%));
}

.info-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-label {
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
}

.info-value {
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-primary, hsl(25, 9%, 12%));
  font-weight: 500;
}

.info-value--amount {
  font-weight: 700;
  color: var(--color-error, hsl(0, 80%, 52%));
}

.reason-text {
  font-size: var(--font-size-base, 14px);
  color: var(--color-text-primary, hsl(25, 9%, 12%));
  line-height: var(--line-height-normal, 1.5);
  margin: 0;
  white-space: pre-wrap;
}

.reason-text--empty {
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
  font-style: italic;
}

.detail-footer {
  padding: var(--space-lg);
  border-top: 1px solid var(--color-border, hsl(25, 7%, 90%));
  display: flex;
  gap: var(--space-sm);
  flex-shrink: 0;
}

.detail-footer .el-button {
  flex: 1;
}

/* ══ 面板滑入动画 ══ */
.panel-slide-enter-active {
  transition: all 0.225s cubic-bezier(0.16, 1, 0.3, 1);
}

.panel-slide-leave-active {
  transition: all 0.15s ease-in;
}

.panel-slide-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.panel-slide-leave-to {
  opacity: 0;
  transform: translateX(10px);
}

/* ══ 批量操作栏 ══ */
.batch-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: var(--z-sticky, 100);
  background: var(--page-review-batch-bar-bg, hsl(25, 7%, 15%));
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-md) var(--space-lg);
}

.batch-info {
  color: #ffffff;
  font-size: var(--font-size-base, 14px);
}

.batch-actions {
  display: flex;
  gap: var(--space-md);
}

.batch-btn {
  color: #ffffff !important;
}

.batch-btn.is-disabled {
  color: rgba(255, 255, 255, 0.35) !important;
}

/* ══ 批量栏动画 ══ */
.batch-slide-enter-active {
  transition: all 0.15s cubic-bezier(0.16, 1, 0.3, 1);
}

.batch-slide-leave-active {
  transition: all 0.1s ease-in;
}

.batch-slide-enter-from,
.batch-slide-leave-to {
  opacity: 0;
  transform: translateY(100%);
}

/* ══ 响应式 ══ */
@media (max-width: 1023px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .content-split {
    flex-direction: column;
  }

  .detail-panel {
    width: 100%;
    max-height: none;
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    z-index: var(--z-drawer, 200);
    border-radius: 0;
  }
}

@media (max-width: 767px) {
  .stats-row {
    grid-template-columns: 1fr 1fr;
  }

  .toolbar {
    flex-direction: column;
    gap: var(--space-sm);
    align-items: flex-start;
  }

  .arbitration-workspace {
    padding: var(--space-sm);
  }
}
.page-header { margin-bottom: var(--space-md); }

</style>
