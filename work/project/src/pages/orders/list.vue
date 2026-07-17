<template>
  <div class="orders-page">
    <div class="orders-header">
      <h1 class="page-title">我的订单</h1>
      <el-button @click="router.push({name:'CheckoutPay'})">返回支付</el-button>
    </div>

    <!-- Status Tabs -->
    <el-tabs v-model="activeStatus" @tab-change="handleStatusChange" class="orders-tabs">
      <el-tab-pane
        v-for="tab in statusTabs"
        :key="tab.value"
        :label="tab.label"
        :name="tab.value"
      />
    </el-tabs>

    <!-- Loading Skeleton -->
    <div v-if="loading" class="orders-loading">
      <div v-if="!isMobile" class="skeleton-table">
        <div class="skeleton-header">
          <div v-for="i in 6" :key="'h' + i" class="skeleton-cell" :style="{ width: columnWidths[i - 1] }" />
        </div>
        <div v-for="row in 8" :key="'r' + row" class="skeleton-row">
          <div v-for="i in 6" :key="'c' + i" class="skeleton-cell" :style="{ width: columnWidths[i - 1] }" />
        </div>
      </div>
      <div v-else class="skeleton-cards">
        <div v-for="i in 4" :key="'sc' + i" class="skeleton-card">
          <div class="skeleton-thumb" />
          <div class="skeleton-lines">
            <div class="skeleton-line w-60" />
            <div class="skeleton-line w-40" />
            <div class="skeleton-line w-30" />
          </div>
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="orders-error">
      <el-result icon="error" title="加载失败" sub-title="网络连接出现问题，请检查网络后重试">
        <template #extra>
          <el-button type="primary" @click="fetchOrders">重新加载</el-button>
          <el-button @click="router.push('/')">返回首页</el-button>
        </template>
      </el-result>
    </div>

    <!-- Empty State -->
    <div v-else-if="orders.length === 0" class="orders-empty">
      <el-empty :description="emptyDescription">
        <el-button v-if="activeStatus === ''" type="primary" @click="router.push('/')">去逛逛</el-button>
        <el-button v-else @click="handleClearFilter">查看全部订单</el-button>
      </el-empty>
    </div>

    <!-- Orders List -->
    <template v-else>
      <!-- Desktop: Table -->
      <div v-if="!isMobile" class="orders-table-wrapper">
        <el-table
          :data="orders"
          style="width: 100%"
          row-class-name="order-row"
          @row-click="handleRowClick"
        >
          <el-table-column prop="orderNo" label="订单号" width="180">
            <template #default="{ row }">
              <span class="order-no" :title="row.orderNo">{{ truncateOrderNo(row.orderNo) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="商品" min-width="220">
            <template #default="{ row }">
              <div class="goods-cell">
                <el-image :src="row.firstItemImage" class="goods-thumb" fit="cover">
                  <template #error>
                    <div class="image-placeholder">{{ (row.firstItemName || '商').charAt(0) }}</div>
                  </template>
                </el-image>
                <div class="goods-info">
                  <span class="goods-name">{{ row.firstItemName }}</span>
                  <span v-if="row.totalItemCount > 1" class="goods-more">等{{ row.totalItemCount }}件</span>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="金额" width="130" align="right">
            <template #default="{ row }">
              <span class="order-amount">¥{{ row.totalAmount }}</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="getStatusTagType(row.status)" size="small" round>
                {{ getStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="下单时间" width="170">
            <template #default="{ row }">
              <span class="order-time">{{ formatTime(row.createdAt) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" align="center">
            <template #default="{ row }">
              <div class="actions-cell" @click.stop>
                <el-button
                  v-for="action in getActions(row)"
                  :key="action.key"
                  :type="action.type"
                  size="small"
                  :link="action.link"
                  @click="action.handler(row)"
                >
                  {{ action.label }}
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- Mobile: Cards -->
      <div v-else class="orders-cards">
        <div
          v-for="order in orders"
          :key="order.id"
          class="order-card"
          @click="handleRowClick(order)"
        >
          <div class="card-header">
            <span class="card-order-no">{{ truncateOrderNo(order.orderNo) }}</span>
            <el-tag :type="getStatusTagType(order.status)" size="small" round>
              {{ getStatusLabel(order.status) }}
            </el-tag>
          </div>
          <div class="card-body">
            <el-image :src="order.firstItemImage" class="card-thumb" fit="cover">
              <template #error>
                <div class="image-placeholder small">{{ (order.firstItemName || '商').charAt(0) }}</div>
              </template>
            </el-image>
            <div class="card-goods">
              <span class="card-goods-name">{{ order.firstItemName }}</span>
              <span v-if="order.totalItemCount > 1" class="card-goods-more">等{{ order.totalItemCount }}件</span>
            </div>
            <div class="card-amount">¥{{ order.totalAmount }}</div>
          </div>
          <div class="card-footer">
            <span class="card-time">{{ formatTime(order.createdAt) }}</span>
            <div class="card-actions" @click.stop>
              <el-button
                v-for="action in getActions(order)"
                :key="action.key"
                :type="action.type"
                size="small"
                :link="action.link"
                @click="action.handler(order)"
              >
                {{ action.label }}
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- Pagination -->
      <div class="orders-pagination">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </template>

    <!-- Confirm Receive Dialog (from list) -->
    <el-dialog v-model="confirmDialogVisible" title="确认收货" width="400px" :close-on-click-modal="false">
      <p class="confirm-text">确认收货后，款项将打给商家</p>
      <p class="confirm-warning">确认收货后不可恢复</p>
      <template #footer>
        <el-button @click="confirmDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="confirming" @click="doConfirmReceive">确认收货</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { getOrders, confirmReceive } from '@/api/orders';

const router = useRouter();

// ── Responsive ──
const windowWidth = ref(window.innerWidth);
const isMobile = computed(() => windowWidth.value < 768);

function onResize() {
  windowWidth.value = window.innerWidth;
}

onMounted(() => window.addEventListener('resize', onResize));
onUnmounted(() => window.removeEventListener('resize', onResize));

// ── State ──
const loading = ref(true);
const error = ref(false);
const orders = ref([]);
const activeStatus = ref('');
const currentPage = ref(1);
const pageSize = ref(20);
const total = ref(0);

// ── Confirm from list ──
const confirmDialogVisible = ref(false);
const confirming = ref(false);
const confirmingOrder = ref(null);

// ── Status config ──
const statusTabs = [
  { label: '全部', value: '' },
  { label: '待付款', value: 'pending' },
  { label: '待发货', value: 'paid' },
  { label: '已发货', value: 'shipped' },
  { label: '已完成', value: 'completed' },
  { label: '已取消', value: 'cancelled' },
  { label: '退款中', value: 'refunding' },
  { label: '已退款', value: 'refunded' },
];

const statusLabelMap = {
  pending: '待付款',
  paid: '待发货',
  shipped: '已发货',
  completed: '已完成',
  cancelled: '已取消',
  refunding: '退款中',
  refunded: '已退款',
};

const statusTagTypeMap = {
  pending: 'warning',
  paid: '',
  shipped: 'primary',
  completed: 'success',
  cancelled: 'info',
  refunding: 'danger',
  refunded: 'danger',
};

const columnWidths = ['180px', '220px', '130px', '100px', '170px', '150px'];

const emptyDescription = computed(() => {
  if (activeStatus.value === '') return '还没有订单';
  return '没有符合条件的订单';
});

// ── Helpers ──
function getStatusLabel(status) {
  return statusLabelMap[status] || status;
}

function getStatusTagType(status) {
  return statusTagTypeMap[status] || 'info';
}

function formatTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const h = String(d.getHours()).padStart(2, '0');
  const min = String(d.getMinutes()).padStart(2, '0');
  return `${y}-${m}-${day} ${h}:${min}`;
}

function truncateOrderNo(no) {
  if (!no) return '';
  if (no.length <= 12) return no;
  return no.slice(0, 8) + '...' + no.slice(-4);
}

function processOrders(list) {
  return list.map((order) => {
    const allItems = [];
    (order.subOrders || []).forEach((sub) => {
      (sub.items || []).forEach((item) => allItems.push(item));
    });
    const firstItem = allItems[0];
    return {
      ...order,
      firstItemImage: firstItem?.snapshot?.image || '',
      firstItemName: firstItem?.snapshot?.spuName || '商品',
      totalItemCount: allItems.length,
    };
  });
}

// ── Actions per status ──
function getActions(order) {
  const actions = [];
  if (order.status === 'pending') {
    actions.push({
      key: 'pay',
      label: '立即付款',
      type: 'primary',
      link: false,
      handler: (o) => router.push({ name: 'OrderDetail', params: { id: o.id } }),
    });
  }
  if (order.status === 'shipped') {
    actions.push({
      key: 'confirm',
      label: '确认收货',
      type: 'primary',
      link: false,
      handler: (o) => openConfirmDialog(o),
    });
  }
  if (['paid', 'shipped', 'completed'].includes(order.status)) {
    actions.push({
      key: 'refund',
      label: '申请售后',
      type: 'default',
      link: true,
      handler: (o) => router.push({ name: 'RefundApply', params: { id: o.id } }),
    });
  }
  if (order.status === 'refunding') {
    actions.push({
      key: 'refundDetail',
      label: '查看售后',
      type: 'default',
      link: true,
      handler: (o) => router.push({ name: 'RefundDetail', params: { id: o.id } }),
    });
  }
  return actions;
}

function openConfirmDialog(order) {
  confirmingOrder.value = order;
  confirmDialogVisible.value = true;
}

async function doConfirmReceive() {
  if (!confirmingOrder.value) return;
  confirming.value = true;
  try {
    await confirmReceive(confirmingOrder.value.id);
    ElMessage.success('收货确认成功');
    confirmDialogVisible.value = false;
    confirmingOrder.value = null;
    await fetchOrders();
  } catch (e) {
    const msg = e?.response?.data?.message || '确认收货失败，请重试';
    ElMessage.error(msg);
  } finally {
    confirming.value = false;
  }
}

// ── Event handlers ──
function handleRowClick(row) {
  router.push({ name: 'OrderDetail', params: { id: row.id } });
}

function handleStatusChange() {
  currentPage.value = 1;
  fetchOrders();
}

function handlePageChange(page) {
  currentPage.value = page;
  fetchOrders();
}

function handleClearFilter() {
  activeStatus.value = '';
  currentPage.value = 1;
  fetchOrders();
}

// ── Data fetching ──
async function fetchOrders() {
  loading.value = true;
  error.value = false;
  try {
    const res = await getOrders({
      status: activeStatus.value || undefined,
      page: currentPage.value,
      pageSize: pageSize.value,
    });
    const data = res.data;
    orders.value = processOrders(data.list || []);
    total.value = data.total || 0;
  } catch (e) {
    error.value = true;
    orders.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  fetchOrders();
});
</script>

<style scoped>
/* ── Page-level tokens ── */
.orders-page {
  --page-order-spacing-unit: 4px;
  --page-order-row-height: 56px;
  --page-order-card-border: 1px solid var(--color-border, hsl(25, 7%, 90%));

  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-lg, 24px);
  min-height: 60vh;
}

.orders-header {
  margin-bottom: var(--space-md, 16px);
}

.page-title {
  font-size: var(--font-size-xl, 21px);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
  line-height: var(--line-height-tight, 1.25);
}

/* ── Tabs ── */
.orders-tabs {
  margin-bottom: var(--space-md, 16px);
}

.orders-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
}

/* ── Skeleton ── */
.skeleton-table {
  background: var(--color-bg-base, #FFFFFF);
  border: var(--page-order-card-border);
  border-radius: var(--radius-md, 20px);
  overflow: hidden;
}

.skeleton-header,
.skeleton-row {
  display: flex;
  align-items: center;
  height: var(--page-order-row-height);
  padding: 0 var(--space-md, 16px);
  gap: var(--space-sm, 8px);
}

.skeleton-header {
  background: var(--color-bg-page, hsl(25, 5%, 97%));
  border-bottom: var(--page-order-card-border);
}

.skeleton-row {
  border-bottom: var(--page-order-card-border);
}

.skeleton-row:last-child {
  border-bottom: none;
}

.skeleton-cell {
  height: 14px;
  border-radius: 4px;
  background: linear-gradient(
    90deg,
    var(--color-primary-50, hsl(25, 26%, 95%)) 25%,
    var(--color-bg-base, #FFFFFF) 50%,
    var(--color-primary-50, hsl(25, 26%, 95%)) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.8s infinite;
  flex-shrink: 0;
}

.skeleton-cards {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm, 8px);
}

.skeleton-card {
  display: flex;
  align-items: center;
  gap: var(--space-md, 16px);
  padding: var(--space-sm, 8px);
  background: var(--color-bg-base, #FFFFFF);
  border: var(--page-order-card-border);
  border-radius: var(--radius-md, 20px);
}

.skeleton-thumb {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-sm, 10px);
  background: linear-gradient(
    90deg,
    var(--color-primary-50, hsl(25, 26%, 95%)) 25%,
    var(--color-bg-base, #FFFFFF) 50%,
    var(--color-primary-50, hsl(25, 26%, 95%)) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.8s infinite;
  flex-shrink: 0;
}

.skeleton-lines {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton-line {
  height: 12px;
  border-radius: 4px;
  background: linear-gradient(
    90deg,
    var(--color-primary-50, hsl(25, 26%, 95%)) 25%,
    var(--color-bg-base, #FFFFFF) 50%,
    var(--color-primary-50, hsl(25, 26%, 95%)) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.8s infinite;
}

.skeleton-line.w-60 { width: 60%; }
.skeleton-line.w-40 { width: 40%; }
.skeleton-line.w-30 { width: 30%; }

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ── Error ── */
.orders-error {
  display: flex;
  justify-content: center;
  padding: var(--space-2xl, 48px) 0;
}

/* ── Empty ── */
.orders-empty {
  padding: var(--space-2xl, 48px) 0;
}

/* ── Table (Desktop) ── */
.orders-table-wrapper {
  background: var(--color-bg-base, #FFFFFF);
  border: var(--page-order-card-border);
  border-radius: var(--radius-md, 20px);
  overflow: hidden;
}

.orders-table-wrapper :deep(.el-table) {
  --el-table-border-color: transparent;
}

.orders-table-wrapper :deep(.el-table th.el-table__cell) {
  background: var(--color-bg-page, hsl(25, 5%, 97%));
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm, 12.25px);
  font-weight: 600;
  height: var(--page-order-row-height);
  padding: 10px 12px;
  border-bottom: var(--page-order-card-border);
}

.orders-table-wrapper :deep(.el-table tr) {
  cursor: pointer;
}

.orders-table-wrapper :deep(.el-table td.el-table__cell) {
  height: var(--page-order-row-height);
  padding: 10px 12px;
  border-bottom: var(--page-order-card-border);
}

.orders-table-wrapper :deep(.el-table tr:hover > td.el-table__cell) {
  background: var(--color-primary-50, hsl(25, 26%, 95%));
  transition: background var(--duration-instant, 75ms);
}

.order-no {
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.5px;
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-secondary);
}

.goods-cell {
  display: flex;
  align-items: center;
  gap: var(--space-sm, 8px);
}

.goods-thumb {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-sm, 10px);
  flex-shrink: 0;
}

.goods-info {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.goods-name {
  font-size: var(--font-size-base, 14px);
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 160px;
}

.goods-more {
  font-size: var(--font-size-xs, 10.5px);
  color: var(--color-text-tertiary);
}

.image-placeholder {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary-50, hsl(25, 26%, 95%));
  color: var(--color-primary-500);
  font-size: var(--font-size-md, 15.75px);
  font-weight: 600;
  border-radius: var(--radius-sm, 10px);
}

.image-placeholder.small {
  width: 48px;
  height: 48px;
}

.order-amount {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  font-size: var(--font-size-md, 15.75px);
  color: var(--color-text-primary);
}

.order-time {
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-secondary);
}

.actions-cell {
  display: flex;
  gap: var(--space-xs, 4px);
  justify-content: center;
  flex-wrap: wrap;
}

.actions-cell .el-button {
  padding: 4px 12px;
  font-size: var(--font-size-sm, 12.25px);
  min-width: 64px;
}

/* ── Cards (Mobile) ── */
.orders-cards {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm, 8px);
}

.order-card {
  background: var(--color-bg-base, #FFFFFF);
  border: var(--page-order-card-border);
  border-radius: var(--radius-md, 20px);
  padding: var(--space-sm, 8px);
  cursor: pointer;
  transition: background var(--duration-instant, 75ms);
}

.order-card:active {
  background: var(--color-primary-50, hsl(25, 26%, 95%));
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: var(--space-xs, 4px);
  margin-bottom: var(--space-xs, 4px);
  border-bottom: var(--page-order-card-border);
}

.card-order-no {
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-secondary);
  font-variant-numeric: tabular-nums;
}

.card-body {
  display: flex;
  align-items: center;
  gap: var(--space-sm, 8px);
  padding: var(--space-xs, 4px) 0;
}

.card-thumb {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-sm, 10px);
  flex-shrink: 0;
}

.card-goods {
  flex: 1;
  overflow: hidden;
}

.card-goods-name {
  font-size: var(--font-size-base, 14px);
  color: var(--color-text-primary);
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-goods-more {
  font-size: var(--font-size-xs, 10.5px);
  color: var(--color-text-tertiary);
}

.card-amount {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  font-size: var(--font-size-md, 15.75px);
  white-space: nowrap;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: var(--space-xs, 4px);
  margin-top: var(--space-xs, 4px);
  border-top: var(--page-order-card-border);
}

.card-time {
  font-size: var(--font-size-xs, 10.5px);
  color: var(--color-text-secondary);
}

.card-actions {
  display: flex;
  gap: var(--space-xs, 4px);
}

/* ── Pagination ── */
.orders-pagination {
  display: flex;
  justify-content: center;
  padding: var(--space-lg, 24px) 0;
}

/* ── Confirm Dialog ── */
.confirm-text {
  font-size: var(--font-size-base, 14px);
  color: var(--color-text-primary);
  line-height: var(--line-height-relaxed, 1.75);
}

.confirm-warning {
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-tertiary);
  margin-top: var(--space-xs, 4px);
}
</style>
