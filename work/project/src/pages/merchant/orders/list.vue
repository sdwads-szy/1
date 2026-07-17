<template>
  <div class="merchant-orders-page">
    <div class="page-header">
      <el-button text @click="$router.push({name:'MerchantDashboard'})">← 返回看板</el-button>
      <h2 class="page-title">订单管理</h2>
    </div>

    <!-- 状态筛选 Tab -->
    <el-tabs
      v-model="activeStatus"
      @tab-change="handleStatusChange"
      class="status-tabs"
    >
      <el-tab-pane label="全部" name="" />
      <el-tab-pane label="待发货" name="paid" />
      <el-tab-pane label="已发货" name="shipped" />
      <el-tab-pane label="已完成" name="completed" />
      <el-tab-pane label="退款中" name="refunding" />
    </el-tabs>

    <!-- 加载骨架 -->
    <div v-if="loading" class="table-skeleton">
      <div
        v-for="i in 8"
        :key="i"
        class="skeleton-row"
      >
        <div class="skeleton-cell" style="width: 140px" />
        <div class="skeleton-cell" style="width: 200px" />
        <div class="skeleton-cell" style="width: 80px" />
        <div class="skeleton-cell" style="width: 80px" />
        <div class="skeleton-cell" style="width: 120px" />
        <div class="skeleton-cell" style="width: 80px" />
      </div>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-state">
      <el-icon :size="48" color="hsl(0, 80%, 52%, 0.6)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      </el-icon>
      <h3 class="error-title">加载失败</h3>
      <p class="error-desc">网络连接出现问题，请检查网络后重试</p>
      <div class="error-actions">
        <el-button type="primary" @click="fetchOrders">重新加载</el-button>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="orderList.length === 0" class="empty-state">
      <el-icon :size="64" color="hsl(25, 4%, 62%)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="2" y="3" width="20" height="18" rx="2" />
          <line x1="6" y1="9" x2="18" y2="9" />
          <line x1="6" y1="13" x2="14" y2="13" />
          <line x1="6" y1="17" x2="10" y2="17" />
        </svg>
      </el-icon>
      <h3 class="empty-title">暂无订单</h3>
      <p class="empty-desc">当有顾客下单时，订单将显示在这里</p>
    </div>

    <!-- 订单表格 -->
    <template v-else>
      <el-table
        :data="orderList"
        class="orders-table"
        stripe
        :header-cell-style="tableHeaderStyle"
        @row-click="handleRowClick"
      >
        <el-table-column
          prop="subOrderNo"
          label="子订单号"
          width="160"
        >
          <template #default="{ row }">
            <span class="order-no">{{ row.subOrderNo }}</span>
          </template>
        </el-table-column>

        <el-table-column
          label="商品信息"
          min-width="220"
        >
          <template #default="{ row }">
            <div class="goods-cell">
              <img
                v-if="row.items && row.items[0]"
                :src="assetUrl(row.items[0].snapshot?.image)"
                class="goods-thumb"
                @error="onImgError"
              />
              <div class="goods-info">
                <p class="goods-name">
                  {{ row.items && row.items[0] ? (row.items[0].snapshot?.spuName || '商品') : '商品' }}
                </p>
                <p class="goods-spec" v-if="row.items && row.items[0] && row.items[0].snapshot?.specName">
                  {{ row.items[0].snapshot.specName }}
                </p>
                <p class="goods-count" v-if="row.items && row.items.length > 1">
                  等 {{ row.items.length }} 件商品
                </p>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column
          prop="amount"
          label="金额"
          width="110"
          align="right"
        >
          <template #default="{ row }">
            <span class="amount-cell">¥{{ formatAmount(row.amount) }}</span>
          </template>
        </el-table-column>

        <el-table-column
          prop="status"
          label="状态"
          width="100"
          align="center"
        >
          <template #default="{ row }">
            <span :class="['status-badge', `status-${row.status}`]">
              {{ statusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column
          prop="createdAt"
          label="下单时间"
          width="170"
        >
          <template #default="{ row }">
            <span class="time-cell">{{ formatTime(row.createdAt) }}</span>
          </template>
        </el-table-column>

        <el-table-column
          label="操作"
          width="100"
          align="center"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'paid'"
              type="primary"
              size="small"
              @click.stop="goToShipping(row.id)"
            >
              发货
            </el-button>
            <span v-else class="no-action">—</span>
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
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { getMerchantOrders } from '@/api/merchant-orders';
import { ElMessage } from 'element-plus';

const router = useRouter();
const FILE_BASE_URL = import.meta.env.VITE_FILE_BASE_URL || '';

const activeStatus = ref('');
const loading = ref(true);
const error = ref(false);
const orderList = ref([]);

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
});

const tableHeaderStyle = {
  background: 'hsl(25, 5%, 97%)',
  color: 'hsl(25, 7%, 42%)',
  fontSize: '12.25px',
  fontWeight: 600
};

const statusMap = {
  paid: { label: '待发货', class: 'status-paid' },
  shipped: { label: '已发货', class: 'status-shipped' },
  completed: { label: '已完成', class: 'status-completed' },
  refunding: { label: '退款中', class: 'status-refunding' },
  refunded: { label: '已退款', class: 'status-refunded' }
};

function statusLabel(status) {
  return statusMap[status]?.label || status;
}

function assetUrl(path) {
  if (!path) return '';
  if (path.startsWith('http')) return path;
  return FILE_BASE_URL + path;
}

function onImgError(e) {
  e.target.style.display = 'none';
}

function formatAmount(val) {
  const num = parseFloat(val);
  return isNaN(num) ? '0.00' : num.toFixed(2);
}

function formatTime(val) {
  if (!val) return '';
  const d = new Date(val);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const h = String(d.getHours()).padStart(2, '0');
  const min = String(d.getMinutes()).padStart(2, '0');
  return `${y}-${m}-${day} ${h}:${min}`;
}

async function fetchOrders() {
  loading.value = true;
  error.value = false;
  try {
    const res = await getMerchantOrders({
      status: activeStatus.value || undefined,
      page: pagination.page,
      pageSize: pagination.pageSize
    });
    if (res.data && res.data.list) {
      orderList.value = res.data.list;
      pagination.total = res.data.total || 0;
      pagination.page = res.data.page || 1;
      pagination.pageSize = res.data.pageSize || 20;
    }
  } catch (err) {
    error.value = true;
    orderList.value = [];
  } finally {
    loading.value = false;
  }
}

function handleStatusChange() {
  pagination.page = 1;
  fetchOrders();
}

function handlePageChange() {
  fetchOrders();
}

function handleSizeChange() {
  pagination.page = 1;
  fetchOrders();
}

function goToShipping(subOrderId) {
  router.push({ name: 'MerchantShipping', params: { id: subOrderId } });
}

function handleRowClick(row) {
  // 预留：点击行查看订单详情
}

onMounted(() => {
  fetchOrders();
});
</script>

<style scoped>
.merchant-orders-page {
  --page-order-spacing-unit: 4px;
  padding: var(--space-lg);
  max-width: 1200px;
  margin: 0 auto;
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

.status-tabs {
  margin-bottom: var(--space-md);
}

/* 骨架屏 */
.table-skeleton {
  background: var(--color-bg-base);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.skeleton-row {
  display: flex;
  gap: var(--space-md);
  padding: 10px 12px;
  height: 56px;
  align-items: center;
  border-bottom: 1px solid var(--color-border);
}

.skeleton-row:last-child {
  border-bottom: none;
}

.skeleton-cell {
  height: 14px;
  background: linear-gradient(
    90deg,
    hsl(25, 43%, 90%) 0%,
    hsl(25, 5%, 97%) 50%,
    hsl(25, 43%, 90%) 100%
  );
  background-size: 200% 100%;
  animation: shimmer 1.8s infinite;
  border-radius: 4px;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* 错误状态 */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-3xl) var(--space-lg);
  text-align: center;
}

.error-title {
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
  margin: var(--space-md) 0 0;
  font-weight: 600;
}

.error-desc {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin: var(--space-sm) 0 var(--space-lg);
}

.error-actions {
  display: flex;
  gap: var(--space-sm);
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-3xl) var(--space-lg);
  text-align: center;
}

.empty-title {
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
  margin: var(--space-md) 0 0;
  font-weight: 600;
}

.empty-desc {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin: var(--space-sm) 0 0;
}

/* 表格 */
.orders-table {
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.orders-table :deep(.el-table__row) {
  height: 56px;
  cursor: default;
}

.orders-table :deep(.el-table__row:hover) {
  background-color: hsl(25, 26%, 95%);
}

.orders-table :deep(.el-table__cell) {
  padding: 10px 12px;
}

.order-no {
  font-family: var(--font-family);
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.5px;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.goods-cell {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.goods-thumb {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-sm);
  object-fit: cover;
  background: hsl(25, 26%, 95%);
  flex-shrink: 0;
}

.goods-info {
  min-width: 0;
}

.goods-name {
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

.goods-spec {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 2px 0 0;
}

.goods-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  margin: 2px 0 0;
}

.amount-cell {
  font-family: var(--font-family);
  font-variant-numeric: tabular-nums;
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
}

/* 状态标签 — order-management 风格 */
.status-badge {
  display: inline-block;
  min-width: 72px;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  text-align: center;
  line-height: var(--line-height-normal);
}

.status-paid {
  background: hsl(215, 25%, 94%);
  color: hsl(215, 50%, 35%);
}

.status-shipped {
  background: hsl(25, 26%, 95%);
  color: hsl(25, 81%, 35%);
}

.status-completed {
  background: hsl(145, 30%, 94%);
  color: hsl(145, 50%, 28%);
}

.status-refunding {
  background: hsl(0, 30%, 94%);
  color: hsl(0, 50%, 35%);
}

.status-refunded {
  background: hsl(215, 4%, 94%);
  color: hsl(215, 4%, 50%);
}

.time-cell {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.no-action {
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

/* 分页 */
.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: var(--space-lg);
}
</style>
