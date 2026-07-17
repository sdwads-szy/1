<template>
  <div class="admin-orders-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ name: 'AdminDashboard' }">平台后台</el-breadcrumb-item>
        <el-breadcrumb-item>全局订单</el-breadcrumb-item>
      </el-breadcrumb>
      <h1 class="page-title">全局订单</h1>
      <p class="page-subtitle">管理平台所有订单，支持多维度筛选与查询</p>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-input
        v-model="searchForm.orderNo"
        placeholder="搜索订单号"
        clearable
        class="filter-input"
        @keyup.enter="handleSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-select
        v-model="searchForm.status"
        placeholder="订单状态"
        clearable
        class="filter-select"
      >
        <el-option label="待付款" value="pending" />
        <el-option label="待发货" value="paid" />
        <el-option label="已发货" value="shipped" />
        <el-option label="已完成" value="completed" />
        <el-option label="已取消" value="cancelled" />
        <el-option label="退款中" value="refunding" />
        <el-option label="已退款" value="refunded" />
      </el-select>
      <el-input
        v-model="searchForm.shopId"
        placeholder="店铺ID"
        clearable
        class="filter-input filter-input--short"
        @keyup.enter="handleSearch"
      />
      <el-button type="primary" @click="handleSearch">搜索</el-button>
      <el-button @click="handleReset">重置</el-button>
    </div>

    <!-- 订单表格 — 桌面端 -->
    <div class="table-container">
      <el-table
        v-loading="loading"
        :data="tableData"
        stripe
        class="order-table"
        empty-text=" "
      >
        <el-table-column
          prop="orderNo"
          label="订单号"
          min-width="180"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <span class="order-no" :title="row.orderNo">
              {{ truncateOrderNo(row.orderNo) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column
          prop="userId"
          label="用户ID"
          width="100"
        />
        <el-table-column
          prop="totalAmount"
          label="金额"
          width="130"
          align="right"
        >
          <template #default="{ row }">
            <span class="amount">&yen;{{ formatAmount(row.totalAmount) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="status"
          label="状态"
          width="110"
          align="center"
        >
          <template #default="{ row }">
            <span class="status-badge" :class="'status-' + row.status">
              {{ statusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column
          prop="paidAt"
          label="支付时间"
          width="180"
        >
          <template #default="{ row }">
            {{ formatDateTime(row.paidAt) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="createdAt"
          label="创建时间"
          width="180"
        >
          <template #default="{ row }">
            {{ formatDateTime(row.createdAt) }}
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <div v-if="!loading && tableData.length === 0 && !loadError" class="empty-state">
        <el-icon class="empty-icon"><Document /></el-icon>
        <p class="empty-title">{{ emptyTitle }}</p>
        <p class="empty-desc">{{ emptyDesc }}</p>
        <el-button v-if="hasFilter" type="default" @click="handleReset">清除筛选</el-button>
      </div>

      <!-- 错误状态 -->
      <div v-if="loadError" class="error-state">
        <el-icon class="error-icon"><WarningFilled /></el-icon>
        <p class="error-title">加载失败</p>
        <p class="error-desc">网络连接出现问题，请检查网络后重试</p>
        <el-button type="primary" @click="fetchOrders">重新加载</el-button>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="total > 0" class="pagination-bar">
      <span class="pagination-info">第 {{ (page - 1) * pageSize + 1 }}-{{ Math.min(page * pageSize, total) }} 条，共 {{ total }} 条</span>
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="prev, pager, next, sizes, jumper"
        background
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { Search, Document, WarningFilled } from '@element-plus/icons-vue';
import { getAdminOrders } from '@/api/admin-orders';

// ── 状态 ──
const loading = ref(false);
const loadError = ref(false);
const tableData = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);

const searchForm = reactive({
  orderNo: '',
  status: '',
  shopId: ''
});

// ── 计算属性 ──
const hasFilter = computed(() => {
  return searchForm.orderNo !== '' || searchForm.status !== '' || searchForm.shopId !== '';
});

const emptyTitle = computed(() => {
  return hasFilter.value ? '没有符合条件的订单' : '暂无订单';
});

const emptyDesc = computed(() => {
  return hasFilter.value ? '试试调整筛选条件' : '当有顾客下单时，订单将显示在这里';
});

// ── 状态映射 ──
const STATUS_MAP = {
  pending:   { label: '待付款',   cssClass: 'status-pending' },
  paid:      { label: '待发货',   cssClass: 'status-paid' },
  shipped:   { label: '已发货',   cssClass: 'status-shipped' },
  completed: { label: '已完成',   cssClass: 'status-completed' },
  cancelled: { label: '已取消',   cssClass: 'status-cancelled' },
  refunding: { label: '退款中',   cssClass: 'status-refunding' },
  refunded:  { label: '已退款',   cssClass: 'status-refunded' }
};

function statusLabel(status) {
  return STATUS_MAP[status]?.label || status;
}

// ── 格式化 ──
function formatAmount(val) {
  const num = parseFloat(val);
  return isNaN(num) ? '0.00' : num.toFixed(2);
}

function formatDateTime(val) {
  if (!val) return '—';
  const d = new Date(val);
  if (isNaN(d.getTime())) return '—';
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function truncateOrderNo(orderNo) {
  if (!orderNo) return '';
  if (orderNo.length <= 16) return orderNo;
  return orderNo.slice(0, 8) + '…' + orderNo.slice(-4);
}

// ── 数据获取 ──
async function fetchOrders() {
  loading.value = true;
  loadError.value = false;
  try {
    const params = {
      page: page.value,
      pageSize: pageSize.value
    };
    if (searchForm.orderNo) params.orderNo = searchForm.orderNo;
    if (searchForm.status) params.status = searchForm.status;
    if (searchForm.shopId) params.shopId = Number(searchForm.shopId);

    const res = await getAdminOrders(params);
    const data = res.data || res;
    tableData.value = data.list || [];
    total.value = data.total || 0;
    page.value = data.page || 1;
    pageSize.value = data.pageSize || 20;
  } catch {
    loadError.value = true;
    tableData.value = [];
  } finally {
    loading.value = false;
  }
}

// ── 事件处理 ──
function handleSearch() {
  page.value = 1;
  fetchOrders();
}

function handleReset() {
  searchForm.orderNo = '';
  searchForm.status = '';
  searchForm.shopId = '';
  page.value = 1;
  fetchOrders();
}

function handlePageChange(val) {
  page.value = val;
  fetchOrders();
}

function handleSizeChange(val) {
  pageSize.value = val;
  page.value = 1;
  fetchOrders();
}

// ── 生命周期 ──
onMounted(() => {
  fetchOrders();
});
</script>

<style scoped>
/* ── 页面容器 ── */
.admin-orders-page {
  padding: var(--space-lg);
  max-width: 1200px;
  margin: 0 auto;
}

/* ── 页面标题 ── */
.page-header {
  margin-bottom: var(--space-lg);
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-xs) 0;
  line-height: var(--line-height-tight);
}

.page-subtitle {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin: 0;
}

/* ── 筛选栏 ── */
.filter-bar {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
  padding: var(--space-md);
  background: var(--color-bg-base);
  border: var(--page-order-card-border, 1px solid var(--color-border));
  border-radius: var(--radius-md);
  margin-bottom: var(--space-md);
}

.filter-input {
  width: 200px;
}

.filter-input--short {
  width: 140px;
}

.filter-select {
  width: 150px;
}

/* ── 表格容器 ── */
.table-container {
  background: var(--color-bg-base);
  border: var(--page-order-card-border, 1px solid var(--color-border));
  border-radius: var(--radius-md);
  overflow: hidden;
}

.order-table {
  width: 100%;
}

.order-table :deep(.el-table__header th) {
  background: var(--color-bg-page);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: 600;
  padding: 10px 12px;
  height: 44px;
  border-bottom: 1px solid var(--color-border);
}

.order-table :deep(.el-table__body td) {
  padding: 0 12px;
  height: var(--page-order-row-height, 56px);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
}

.order-table :deep(.el-table__body tr:hover > td) {
  background: var(--color-primary-50);
  transition: background var(--duration-instant) var(--ease-smooth);
}

.order-table :deep(.el-table__body tr) {
  border-bottom: 1px solid var(--color-border);
}

.order-table :deep(.el-table__body tr:last-child) {
  border-bottom: none;
}

/* 斑马纹 */
.order-table :deep(.el-table--striped .el-table__body tr.el-table__row--striped td) {
  background: var(--color-bg-page);
}

.order-table :deep(.el-table--striped .el-table__body tr.el-table__row--striped:hover td) {
  background: var(--color-primary-50);
}

/* 订单号 */
.order-no {
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.5px;
  font-family: var(--font-family);
  cursor: default;
}

/* 金额 */
.amount {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  font-size: var(--font-size-md);
  color: var(--color-text-primary);
}

/* ── 状态标签 ── */
.status-badge {
  display: inline-block;
  min-width: 72px;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  font-weight: 500;
  text-align: center;
  line-height: 1.5;
}

/* pending — 待付款: warning 系 */
.status-pending {
  background: hsl(38, 40%, 94%);
  color: hsl(38, 70%, 30%);
}

/* paid — 待发货: info 系 */
.status-paid {
  background: hsl(215, 25%, 94%);
  color: hsl(215, 50%, 35%);
}

/* shipped — 已发货: primary 系 */
.status-shipped {
  background: var(--color-primary-50);
  color: var(--color-primary-700);
}

/* completed — 已完成: success 系 */
.status-completed {
  background: hsl(145, 30%, 94%);
  color: hsl(145, 50%, 28%);
}

/* cancelled — 已取消: 无彩色 */
.status-cancelled {
  background: hsl(215, 4%, 94%);
  color: hsl(215, 4%, 50%);
}

/* refunding — 退款中: error 系 */
.status-refunding {
  background: hsl(0, 30%, 94%);
  color: hsl(0, 50%, 35%);
}

/* refunded — 已退款: error 系略浅 */
.status-refunded {
  background: hsl(0, 20%, 94%);
  color: hsl(0, 35%, 45%);
}

/* ── 空状态 ── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-3xl) var(--space-lg);
}

.empty-icon {
  font-size: 64px;
  color: var(--color-text-tertiary);
  margin-bottom: var(--space-md);
}

.empty-title {
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-xs) 0;
  font-weight: 600;
}

.empty-desc {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-lg) 0;
}

/* ── 错误状态 ── */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-3xl) var(--space-lg);
}

.error-icon {
  font-size: 48px;
  color: rgba(239, 68, 68, 0.6);
  margin-bottom: var(--space-md);
}

.error-title {
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-xs) 0;
  font-weight: 600;
}

.error-desc {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-lg) 0;
}

/* ── 分页栏 ── */
.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-md);
  margin-top: var(--space-md);
  padding: var(--space-md);
  background: var(--color-bg-base);
  border: var(--page-order-card-border, 1px solid var(--color-border));
  border-radius: var(--radius-md);
}

.pagination-info {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

/* ── 响应式 ── */
@media (max-width: 1024px) {
  .admin-orders-page {
    padding: var(--space-md);
  }

  .filter-input {
    width: 160px;
  }

  .filter-input--short {
    width: 120px;
  }

  .filter-select {
    width: 130px;
  }

  .pagination-bar {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 768px) {
  .admin-orders-page {
    padding: var(--space-sm);
  }

  .page-title {
    font-size: var(--font-size-xl);
  }

  .filter-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-input,
  .filter-input--short,
  .filter-select {
    width: 100%;
  }

  .pagination-bar {
    flex-direction: column;
    align-items: stretch;
    gap: var(--space-sm);
  }

  .pagination-info {
    text-align: center;
  }
}
</style>
