<template>
  <div class="review-workbench">
    <!-- 顶部标题栏 -->
    <div class="workbench-header">
      <div class="header-left">
        <el-button text @click="goBack" class="back-btn">
          <el-icon><ArrowLeft /></el-icon>
          返回后台
        </el-button>
        <h2 class="page-title">商家入驻审核</h2>
      </div>
      <el-button @click="goToMerchantList" class="view-all-btn">
        查看全部商家
        <el-icon><ArrowRight /></el-icon>
      </el-button>
    </div>

    <!-- 统计卡片行 -->
    <div class="stats-row">
      <div class="stat-card">
        <span class="stat-label">待审核</span>
        <span class="stat-value">{{ stats.pending }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">今日通过</span>
        <span class="stat-value">{{ stats.todayApproved }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">今日驳回</span>
        <span class="stat-value">{{ stats.todayRejected }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">平均审核时长</span>
        <span class="stat-value">{{ stats.avgDuration }}</span>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索商家名称 / 信用代码 / 联系人…"
        clearable
        :prefix-icon="Search"
        class="search-input"
        @clear="fetchList"
        @keyup.enter="fetchList"
      />
      <el-select v-model="dateRange" placeholder="申请时间" clearable class="date-select">
        <el-option label="今天" value="today" />
        <el-option label="最近3天" value="3days" />
        <el-option label="最近7天" value="7days" />
        <el-option label="最近30天" value="30days" />
      </el-select>
    </div>

    <!-- 审核列表 -->
    <div class="table-wrapper">
      <!-- 加载骨架 -->
      <template v-if="loading">
        <div class="skeleton-list">
          <div v-for="i in 8" :key="i" class="skeleton-row">
            <div class="skeleton-cell skeleton-check"></div>
            <div class="skeleton-cell skeleton-name"></div>
            <div class="skeleton-cell skeleton-code"></div>
            <div class="skeleton-cell skeleton-contact"></div>
            <div class="skeleton-cell skeleton-time"></div>
            <div class="skeleton-cell skeleton-status"></div>
          </div>
        </div>
      </template>

      <!-- 空态 -->
      <template v-else-if="!loading && tableData.length === 0">
        <div class="empty-state">
          <el-icon :size="64" color="var(--color-success)"><CircleCheckFilled /></el-icon>
          <h3>全部审核完毕</h3>
          <p>当前没有待审核的项目，辛苦了！</p>
          <el-button type="primary" @click="goToMerchantList">查看审核记录</el-button>
        </div>
      </template>

      <!-- 错误态 -->
      <template v-else-if="loadError">
        <div class="error-state">
          <el-icon :size="48" color="var(--color-error)"><WarningFilled /></el-icon>
          <h3>审核列表加载失败</h3>
          <p>网络连接异常，请检查网络后重试</p>
          <el-button type="primary" @click="fetchList">重新加载</el-button>
          <el-button @click="goBack">返回首页</el-button>
        </div>
      </template>

      <!-- 正常表格 -->
      <template v-else>
        <el-table
          ref="tableRef"
          :data="tableData"
          row-key="id"
          @row-click="openDetail"
          @selection-change="handleSelectionChange"
          highlight-current-row
          class="review-table"
        >
          <el-table-column type="selection" width="48" />
          <el-table-column label="商家 / 店铺" min-width="180">
            <template #default="{ row }">
              <div class="merchant-cell">
                <span class="merchant-name">{{ row.contactName }}</span>
                <span class="shop-name">{{ row.shopName || '—' }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="信用代码" min-width="180">
            <template #default="{ row }">
              <span class="mono-text">{{ row.creditCode }}</span>
            </template>
          </el-table-column>
          <el-table-column label="联系人" min-width="140">
            <template #default="{ row }">
              <div class="contact-cell">
                <span>{{ row.contactName }}</span>
                <span class="contact-mobile">{{ row.contactMobile }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="申请时间" width="170">
            <template #default="{ row }">
              <span class="time-text">{{ formatTime(row.createdAt) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag
                :type="statusTagType(row.status)"
                size="small"
                class="status-tag"
              >
                {{ statusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click.stop="openDetail(row)">
                审核
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-wrapper">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.pageSize"
            :total="pagination.total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @change="fetchList"
          />
        </div>
      </template>
    </div>

    <!-- 审核详情抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      :title="'商家入驻审核 · ' + (currentMerchant?.contactName || '')"
      size="420px"
      :close-on-click-modal="false"
      class="review-drawer"
    >
      <template v-if="currentMerchant">
        <div class="drawer-content">
          <!-- 商家基本信息 -->
          <section class="info-section">
            <h4 class="section-title">商家信息</h4>
            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">商家ID</span>
                <span class="info-value">{{ currentMerchant.id }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">用户ID</span>
                <span class="info-value">{{ currentMerchant.userId }}</span>
              </div>
              <div class="info-item full-width">
                <span class="info-label">统一社会信用代码</span>
                <span class="info-value mono-text">{{ currentMerchant.creditCode }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">联系人</span>
                <span class="info-value">{{ currentMerchant.contactName }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">联系电话</span>
                <span class="info-value">{{ currentMerchant.contactMobile }}</span>
              </div>
              <div class="info-item full-width">
                <span class="info-label">营业执照</span>
                <div class="license-preview">
                  <el-image
                    v-if="currentMerchant.bizLicense"
                    :src="currentMerchant.bizLicense"
                    fit="contain"
                    class="license-img"
                    :preview-src-list="[currentMerchant.bizLicense]"
                  >
                    <template #error>
                      <div class="img-placeholder">
                        <el-icon :size="32"><PictureFilled /></el-icon>
                        <span>营业执照加载失败</span>
                      </div>
                    </template>
                  </el-image>
                  <div v-else class="img-placeholder">
                    <el-icon :size="32"><PictureFilled /></el-icon>
                    <span>暂无营业执照</span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <!-- 店铺信息 -->
          <section class="info-section">
            <h4 class="section-title">店铺信息</h4>
            <div class="info-grid">
              <div class="info-item full-width">
                <span class="info-label">店铺名称</span>
                <span class="info-value">{{ currentMerchant.shopName || '—' }}</span>
              </div>
              <div class="info-item full-width">
                <span class="info-label">申请时间</span>
                <span class="info-value">{{ formatTime(currentMerchant.createdAt) }}</span>
              </div>
            </div>
          </section>

          <!-- 审核意见输入 -->
          <section class="info-section">
            <h4 class="section-title">审核意见</h4>
            <el-input
              v-model="reviewReason"
              type="textarea"
              :rows="4"
              maxlength="500"
              show-word-limit
              placeholder="请输入审核意见（驳回时必填）"
            />
          </section>
        </div>
      </template>

      <!-- 抽屉底部操作栏 -->
      <template #footer>
        <div class="drawer-footer">
          <el-button
            type="success"
            :loading="submitting"
            @click="handleApprove"
            class="action-btn approve-btn"
          >
            <el-icon><Select /></el-icon>
            通过
          </el-button>
          <el-button
            type="danger"
            :loading="submitting"
            @click="handleReject"
            class="action-btn reject-btn"
          >
            <el-icon><CloseBold /></el-icon>
            驳回
          </el-button>
        </div>
      </template>
    </el-drawer>

    <!-- 批量操作栏 -->
    <transition name="batch-bar">
      <div v-if="selectedRows.length > 0" class="batch-bar">
        <span class="batch-info">已选 {{ selectedRows.length }} 项</span>
        <div class="batch-actions">
          <el-button text class="batch-btn" @click="batchApprove">批量通过</el-button>
          <el-button text class="batch-btn batch-reject" @click="showBatchRejectDialog">批量驳回</el-button>
        </div>
      </div>
    </transition>

    <!-- 批量驳回理由对话框 -->
    <el-dialog
      v-model="batchRejectDialogVisible"
      title="批量驳回"
      width="480px"
      :close-on-click-modal="false"
    >
      <p class="dialog-tip">确认批量驳回 {{ selectedRows.length }} 项审核？请填写驳回理由。</p>
      <el-input
        v-model="batchRejectReason"
        type="textarea"
        :rows="4"
        maxlength="500"
        show-word-limit
        placeholder="请填写驳回理由，以便商家修改后重新提交"
      />
      <template #footer>
        <el-button @click="batchRejectDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="batchSubmitting" @click="confirmBatchReject">
          确认驳回
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  ArrowLeft,
  ArrowRight,
  Search,
  CircleCheckFilled,
  WarningFilled,
  PictureFilled,
  Select,
  CloseBold
} from '@element-plus/icons-vue';
import { getAdminMerchants, reviewMerchant } from '@/api/admin-merchants.js';

const router = useRouter();

// 状态
const loading = ref(false);
const loadError = ref(false);
const tableData = ref([]);
const tableRef = ref(null);
const searchKeyword = ref('');
const dateRange = ref('');

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
});

const stats = reactive({
  pending: 0,
  todayApproved: 0,
  todayRejected: 0,
  avgDuration: '—'
});

// 抽屉
const drawerVisible = ref(false);
const currentMerchant = ref(null);
const reviewReason = ref('');
const submitting = ref(false);

// 批量
const selectedRows = ref([]);
const batchRejectDialogVisible = ref(false);
const batchRejectReason = ref('');
const batchSubmitting = ref(false);

// 状态映射
const STATUS_MAP = {
  pending_review: { label: '待审核', type: 'warning' },
  approved: { label: '已通过', type: 'success' },
  disabled: { label: '已禁用', type: 'danger' }
};

function statusLabel(status) {
  return STATUS_MAP[status]?.label || status;
}

function statusTagType(status) {
  return STATUS_MAP[status]?.type || 'info';
}

function formatTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// 获取待审核列表
async function fetchList() {
  loading.value = true;
  loadError.value = false;
  try {
    const params = {
      status: 'pending_review',
      page: pagination.page,
      pageSize: pagination.pageSize
    };
    if (searchKeyword.value) {
      params.keyword = searchKeyword.value;
    }
    if (dateRange.value) {
      params.dateRange = dateRange.value;
    }
    const res = await getAdminMerchants(params);
    if (res.data) {
      tableData.value = res.data.list || [];
      pagination.total = res.data.total || 0;
      stats.pending = res.data.total || 0;
    }
  } catch (err) {
    loadError.value = true;
    console.error('获取审核列表失败:', err);
  } finally {
    loading.value = false;
  }
}

// 选择变更
function handleSelectionChange(rows) {
  selectedRows.value = rows;
}

// 打开详情抽屉
function openDetail(row) {
  currentMerchant.value = row;
  reviewReason.value = '';
  drawerVisible.value = true;
}

// 审核 - 通过
async function handleApprove() {
  if (!currentMerchant.value) return;
  try {
    await ElMessageBox.confirm(
      `确认通过「${currentMerchant.value.contactName}」的入驻申请？`,
      '确认通过',
      { confirmButtonText: '确认通过', cancelButtonText: '取消', type: 'success' }
    );
  } catch {
    return;
  }
  submitting.value = true;
  try {
    await reviewMerchant({
      id: currentMerchant.value.id,
      action: 'approve',
      reason: reviewReason.value || undefined
    });
    ElMessage.success('已通过该审核项。');
    drawerVisible.value = false;
    currentMerchant.value = null;
    reviewReason.value = '';
    await fetchList();
  } catch (err) {
    const msg = err?.response?.data?.message || '审核操作失败，请重试';
    ElMessage.error(msg);
  } finally {
    submitting.value = false;
  }
}

// 审核 - 驳回
async function handleReject() {
  if (!currentMerchant.value) return;
  if (!reviewReason.value.trim()) {
    ElMessage.warning('驳回时必须填写审核意见');
    return;
  }
  try {
    await ElMessageBox.confirm(
      `确认驳回「${currentMerchant.value.contactName}」的入驻申请？此操作不可撤回。`,
      '确认驳回',
      { confirmButtonText: '确认驳回', cancelButtonText: '取消', type: 'warning' }
    );
  } catch {
    return;
  }
  submitting.value = true;
  try {
    await reviewMerchant({
      id: currentMerchant.value.id,
      action: 'reject',
      reason: reviewReason.value
    });
    ElMessage.success('已驳回，请填写驳回理由以便商家修改。');
    drawerVisible.value = false;
    currentMerchant.value = null;
    reviewReason.value = '';
    await fetchList();
  } catch (err) {
    const msg = err?.response?.data?.message || '审核操作失败，请重试';
    ElMessage.error(msg);
  } finally {
    submitting.value = false;
  }
}

// 批量通过
async function batchApprove() {
  if (selectedRows.value.length === 0) return;
  try {
    await ElMessageBox.confirm(
      `确认批量通过 ${selectedRows.value.length} 项审核？此操作不可撤回。`,
      '批量通过确认',
      { confirmButtonText: '确认通过', cancelButtonText: '取消', type: 'success' }
    );
  } catch {
    return;
  }
  batchSubmitting.value = true;
  const ids = selectedRows.value.map((r) => r.id);
  let successCount = 0;
  for (const id of ids) {
    try {
      await reviewMerchant({ id, action: 'approve' });
      successCount++;
    } catch (err) {
      console.error(`审核商家 ${id} 失败:`, err);
    }
  }
  batchSubmitting.value = false;
  if (successCount > 0) {
    ElMessage.success(`批量通过完成：${successCount}/${ids.length} 项已通过`);
  } else {
    ElMessage.error('批量审核操作失败，请重试');
  }
  selectedRows.value = [];
  await fetchList();
}

// 批量驳回对话框
function showBatchRejectDialog() {
  batchRejectReason.value = '';
  batchRejectDialogVisible.value = true;
}

// 确认批量驳回
async function confirmBatchReject() {
  if (!batchRejectReason.value.trim()) {
    ElMessage.warning('批量驳回时必须填写理由');
    return;
  }
  batchSubmitting.value = true;
  const ids = selectedRows.value.map((r) => r.id);
  let successCount = 0;
  for (const id of ids) {
    try {
      await reviewMerchant({ id, action: 'reject', reason: batchRejectReason.value });
      successCount++;
    } catch (err) {
      console.error(`驳回商家 ${id} 失败:`, err);
    }
  }
  batchSubmitting.value = false;
  batchRejectDialogVisible.value = false;
  if (successCount > 0) {
    ElMessage.success(`批量驳回完成：${successCount}/${ids.length} 项已驳回`);
  } else {
    ElMessage.error('批量驳回操作失败，请重试');
  }
  selectedRows.value = [];
  await fetchList();
}

// 导航
function goBack() {
  router.push({ name: 'AdminDashboard' });
}

function goToMerchantList() {
  router.push({ name: 'AdminMerchants' });
}

onMounted(() => {
  fetchList();
});
</script>

<style scoped>
/* ===== 工作台布局 ===== */
.review-workbench {
  padding: var(--space-lg);
  max-width: 1440px;
  margin: 0 auto;
  background: var(--page-review-bg-workspace, hsl(25, 4%, 96%));
  min-height: 100vh;
}

/* ===== 顶部标题栏 ===== */
.workbench-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-lg);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.back-btn {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.page-title {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
}

.view-all-btn {
  border-radius: var(--radius-md);
}

/* ===== 统计卡片行 ===== */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
}

.stat-card {
  background: var(--color-bg-base);
  border: 1px solid var(--color-border);
  border-radius: var(--page-review-radius-card, 8px);
  padding: var(--space-md) var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.stat-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.stat-value {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-primary);
}

/* ===== 工具栏 ===== */
.toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  margin-bottom: var(--space-md);
}

.search-input {
  max-width: 360px;
}

.date-select {
  width: 150px;
}

/* ===== 表格容器 ===== */
.table-wrapper {
  background: var(--color-bg-base);
  border: 1px solid var(--color-border);
  border-radius: var(--page-review-radius-card, 8px);
  overflow: hidden;
}

/* ===== 表格样式 ===== */
.review-table {
  width: 100%;
}

.review-table :deep(.el-table__header th) {
  background: var(--color-bg-page);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: 600;
  padding: var(--space-sm) var(--space-md);
}

.review-table :deep(.el-table__body tr) {
  cursor: pointer;
}

.review-table :deep(.el-table__body tr:hover) {
  background: var(--color-bg-page);
}

.review-table :deep(.el-table__body tr.current-row) {
  background: var(--color-primary-50);
}

.review-table :deep(.el-table__body td) {
  padding: var(--space-sm) var(--space-md);
}

/* 商家单元格 */
.merchant-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.merchant-name {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
}

.shop-name {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

/* 联系人单元格 */
.contact-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.contact-mobile {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

/* 等宽文本 */
.mono-text {
  font-family: 'SF Mono', 'Consolas', 'Menlo', monospace;
  font-size: var(--font-size-sm);
  letter-spacing: 0.02em;
}

.time-text {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

/* 状态标签 */
.status-tag {
  border-radius: var(--page-review-radius-tag, 4px);
  font-size: var(--font-size-xs);
}

/* 分页 */
.pagination-wrapper {
  padding: var(--space-md);
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid var(--color-border);
}

/* ===== 空态 / 错误态 ===== */
.empty-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-3xl) var(--space-lg);
  text-align: center;
  gap: var(--space-sm);
}

.empty-state h3,
.error-state h3 {
  margin: var(--space-sm) 0 0;
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
}

.empty-state p,
.error-state p {
  margin: 0;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-base);
}

/* ===== 骨架屏 ===== */
.skeleton-list {
  padding: var(--space-sm);
}

.skeleton-row {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-sm) var(--space-md);
  height: 44px;
}

.skeleton-cell {
  background: linear-gradient(90deg, var(--color-bg-page) 25%, hsl(25, 3%, 94%) 50%, var(--color-bg-page) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.8s ease-in-out infinite;
  border-radius: 4px;
}

.skeleton-check { width: 16px; height: 16px; border-radius: 4px; }
.skeleton-name { flex: 2; height: 14px; }
.skeleton-code { flex: 2; height: 14px; }
.skeleton-contact { flex: 1.5; height: 14px; }
.skeleton-time { flex: 1.5; height: 14px; }
.skeleton-status { width: 60px; height: 22px; border-radius: 4px; }

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ===== 抽屉 ===== */
.review-drawer :deep(.el-drawer__header) {
  padding: var(--space-lg);
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 0;
}

.review-drawer :deep(.el-drawer__body) {
  padding: 0;
  display: flex;
  flex-direction: column;
}

.drawer-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-lg);
}

.info-section {
  margin-bottom: var(--space-lg);
}

.section-title {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-md);
  padding-bottom: var(--space-sm);
  border-bottom: 1px solid var(--color-border);
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-md);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item.full-width {
  grid-column: 1 / -1;
}

.info-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.info-value {
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
}

.license-preview {
  margin-top: var(--space-xs);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.license-img {
  width: 100%;
  max-height: 200px;
  display: block;
}

.img-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  padding: var(--space-2xl);
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
  background: var(--color-bg-page);
}

/* 抽屉底部 */
.drawer-footer {
  display: flex;
  gap: var(--space-md);
  padding: var(--space-lg);
  border-top: 1px solid var(--color-border);
}

.action-btn {
  flex: 1;
  height: 44px;
  font-size: var(--font-size-md);
  font-weight: 600;
  border-radius: var(--radius-md);
}

/* ===== 批量操作栏 ===== */
.batch-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: var(--z-sticky, 100);
  background: var(--page-review-batch-bar-bg, hsl(25, 7%, 15%));
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-md) var(--space-lg);
}

.batch-info {
  font-size: var(--font-size-base);
}

.batch-actions {
  display: flex;
  gap: var(--space-md);
}

.batch-btn {
  color: #ffffff;
  font-size: var(--font-size-base);
}

.batch-btn:hover {
  color: var(--color-primary-300);
}

.batch-reject {
  color: hsl(0, 85%, 75%);
}

.batch-reject:hover {
  color: hsl(0, 85%, 60%);
}

/* 批量操作栏过渡 */
.batch-bar-enter-active {
  transition: all var(--duration-fast, 150ms) var(--ease-smooth, cubic-bezier(0.16, 1, 0.3, 1));
}

.batch-bar-leave-active {
  transition: all var(--duration-instant, 75ms);
}

.batch-bar-enter-from,
.batch-bar-leave-to {
  transform: translateY(100%);
  opacity: 0;
}

/* 对话框提示 */
.dialog-tip {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-md);
  line-height: var(--line-height-normal);
}

/* 响应式 */
@media (max-width: 1023px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .toolbar {
    flex-wrap: wrap;
  }

  .search-input {
    max-width: 100%;
    flex: 1;
  }
}

@media (max-width: 767px) {
  .stats-row {
    grid-template-columns: 1fr;
  }

  .review-workbench {
    padding: var(--space-md);
  }

  .workbench-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-sm);
  }
}
</style>
