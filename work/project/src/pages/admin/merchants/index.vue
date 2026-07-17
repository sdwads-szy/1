<template>
  <div class="merchant-management">
    <!-- 顶部标题栏 -->
    <div class="page-header">
      <div class="header-left">
        <el-button text @click="goBack" class="back-btn">
          <el-icon><ArrowLeft /></el-icon>
          返回后台
        </el-button>
        <h2 class="page-title">商家管理</h2>
      </div>
      <el-button @click="goToReview" class="review-link-btn">
        <el-icon><Back /></el-icon>
        返回审核工作台
      </el-button>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="filter-left">
        <el-radio-group v-model="statusFilter" @change="handleFilterChange" size="default">
          <el-radio-button value="">全部</el-radio-button>
          <el-radio-button value="approved">已开通</el-radio-button>
          <el-radio-button value="pending_review">待审核</el-radio-button>
          <el-radio-button value="disabled">已禁用</el-radio-button>
        </el-radio-group>
      </div>
      <div class="filter-right">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索商家名称 / 信用代码…"
          clearable
          :prefix-icon="Search"
          class="search-input"
          @clear="handleSearch"
          @keyup.enter="handleSearch"
        />
      </div>
    </div>

    <!-- 列表容器 -->
    <div class="table-wrapper">
      <!-- 加载骨架 -->
      <template v-if="loading">
        <div class="skeleton-list">
          <div v-for="i in 8" :key="i" class="skeleton-row">
            <div class="skeleton-cell skeleton-name"></div>
            <div class="skeleton-cell skeleton-code"></div>
            <div class="skeleton-cell skeleton-contact"></div>
            <div class="skeleton-cell skeleton-status"></div>
            <div class="skeleton-cell skeleton-action"></div>
          </div>
        </div>
      </template>

      <!-- 空态 -->
      <template v-else-if="!loading && tableData.length === 0">
        <div class="empty-state">
          <el-icon :size="48" color="var(--color-text-tertiary)"><FolderOpened /></el-icon>
          <h3>没有匹配的商家</h3>
          <p>尝试调整筛选条件或清除筛选</p>
          <el-button @click="clearFilter">清除筛选</el-button>
        </div>
      </template>

      <!-- 错误态 -->
      <template v-else-if="loadError">
        <div class="error-state">
          <el-icon :size="48" color="var(--color-error)"><WarningFilled /></el-icon>
          <h3>商家列表加载失败</h3>
          <p>网络连接异常，请检查网络后重试</p>
          <el-button type="primary" @click="fetchList">重新加载</el-button>
          <el-button @click="goBack">返回首页</el-button>
        </div>
      </template>

      <!-- 正常表格 -->
      <template v-else>
        <el-table
          :data="tableData"
          row-key="id"
          class="merchant-table"
          stripe
        >
          <el-table-column label="商家 / 店铺" min-width="200">
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
          <el-table-column label="入驻时间" width="170">
            <template #default="{ row }">
              <span class="time-text">{{ formatTime(row.createdAt) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="110">
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
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <template v-if="row.status === 'approved'">
                <el-button
                  type="warning"
                  size="small"
                  :loading="actionLoading[row.id]"
                  @click="handleFreeze(row)"
                >
                  冻结
                </el-button>
              </template>
              <template v-else-if="row.status === 'disabled'">
                <el-button
                  type="success"
                  size="small"
                  :loading="actionLoading[row.id]"
                  @click="handleUnfreeze(row)"
                >
                  解冻
                </el-button>
              </template>
              <template v-else>
                <el-button
                  size="small"
                  :loading="actionLoading[row.id]"
                  @click="goToReviewMerchant(row.id)"
                >
                  去审核
                </el-button>
              </template>
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
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  ArrowLeft,
  Back,
  Search,
  FolderOpened,
  WarningFilled
} from '@element-plus/icons-vue';
import { getAdminMerchants, freezeMerchant } from '@/api/admin-merchants.js';

const router = useRouter();

// 状态
const loading = ref(false);
const loadError = ref(false);
const tableData = ref([]);
const statusFilter = ref('');
const searchKeyword = ref('');
const actionLoading = reactive({});

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
});

// 状态映射
const STATUS_MAP = {
  pending_review: { label: '待审核', type: 'warning' },
  approved: { label: '已开通', type: 'success' },
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

// 获取商家列表
async function fetchList() {
  loading.value = true;
  loadError.value = false;
  try {
    const params = {
      page: pagination.page,
      pageSize: pagination.pageSize
    };
    if (statusFilter.value) {
      params.status = statusFilter.value;
    }
    if (searchKeyword.value) {
      params.keyword = searchKeyword.value;
    }
    const res = await getAdminMerchants(params);
    if (res.data) {
      tableData.value = res.data.list || [];
      pagination.total = res.data.total || 0;
    }
  } catch (err) {
    loadError.value = true;
    console.error('获取商家列表失败:', err);
  } finally {
    loading.value = false;
  }
}

// 筛选变更
function handleFilterChange() {
  pagination.page = 1;
  fetchList();
}

// 搜索
function handleSearch() {
  pagination.page = 1;
  fetchList();
}

// 清除筛选
function clearFilter() {
  statusFilter.value = '';
  searchKeyword.value = '';
  pagination.page = 1;
  fetchList();
}

// 冻结商家
async function handleFreeze(row) {
  try {
    await ElMessageBox.confirm(
      `确认冻结「${row.contactName}」的商家账号？冻结后其店铺商品将立即下架，用户将无法访问该店铺。`,
      '冻结确认',
      {
        confirmButtonText: '确认冻结',
        cancelButtonText: '取消',
        type: 'warning'
      }
    );
  } catch {
    return;
  }
  actionLoading[row.id] = true;
  try {
    await freezeMerchant({ id: row.id, action: 'freeze' });
    ElMessage.success(`商家「${row.contactName}」已冻结`);
    await fetchList();
  } catch (err) {
    const msg = err?.response?.data?.message || '冻结操作失败，请重试';
    ElMessage.error(msg);
  } finally {
    actionLoading[row.id] = false;
  }
}

// 解冻商家
async function handleUnfreeze(row) {
  actionLoading[row.id] = true;
  try {
    await freezeMerchant({ id: row.id, action: 'unfreeze' });
    ElMessage.success(`商家「${row.contactName}」已解冻`);
    await fetchList();
  } catch (err) {
    const msg = err?.response?.data?.message || '解冻操作失败，请重试';
    ElMessage.error(msg);
  } finally {
    actionLoading[row.id] = false;
  }
}

// 导航
function goBack() {
  router.push({ name: 'AdminDashboard' });
}

function goToReview() {
  router.push({ name: 'AdminMerchantsReview' });
}

function goToReviewMerchant(id) {
  router.push({ name: 'AdminMerchantsReview' });
}

onMounted(() => {
  fetchList();
});
</script>

<style scoped>
/* ===== 页面布局 ===== */
.merchant-management {
  padding: var(--space-lg);
  max-width: 1440px;
  margin: 0 auto;
  background: var(--page-review-bg-workspace, hsl(25, 4%, 96%));
  min-height: 100vh;
}

/* ===== 顶部标题栏 ===== */
.page-header {
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

.review-link-btn {
  border-radius: var(--radius-md);
}

/* ===== 筛选栏 ===== */
.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-md);
  background: var(--color-bg-base);
  border: 1px solid var(--color-border);
  border-radius: var(--page-review-radius-card, 8px);
  padding: var(--space-md);
}

.filter-left {
  display: flex;
  align-items: center;
}

.filter-right {
  display: flex;
  align-items: center;
}

.search-input {
  width: 280px;
}

/* ===== 表格容器 ===== */
.table-wrapper {
  background: var(--color-bg-base);
  border: 1px solid var(--color-border);
  border-radius: var(--page-review-radius-card, 8px);
  overflow: hidden;
}

/* ===== 表格样式 ===== */
.merchant-table {
  width: 100%;
}

.merchant-table :deep(.el-table__header th) {
  background: var(--color-bg-page);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: 600;
  padding: var(--space-sm) var(--space-md);
}

.merchant-table :deep(.el-table__body td) {
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

.skeleton-name { flex: 2; height: 14px; }
.skeleton-code { flex: 2; height: 14px; }
.skeleton-contact { flex: 1.5; height: 14px; }
.skeleton-status { width: 60px; height: 22px; border-radius: 4px; }
.skeleton-action { width: 60px; height: 28px; border-radius: 6px; }

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* 响应式 */
@media (max-width: 1023px) {
  .filter-bar {
    flex-direction: column;
    gap: var(--space-md);
    align-items: stretch;
  }

  .filter-right {
    width: 100%;
  }

  .search-input {
    width: 100%;
  }
}

@media (max-width: 767px) {
  .merchant-management {
    padding: var(--space-md);
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-sm);
  }
}
</style>
