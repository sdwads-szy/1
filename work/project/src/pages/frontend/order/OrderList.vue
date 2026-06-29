<template>
  <div class="page-container order-list-page">
    <div class="page-header">
      <h1 class="page-title">我的订单</h1>
    </div>

    <div class="page-content">
      <!-- 状态筛选 Tab -->
      <el-tabs
        v-model="activeStatus"
        @tab-change="handleStatusChange"
        class="order-tabs"
      >
        <el-tab-pane
          v-for="tab in statusTabs"
          :key="tab.value"
          :label="tab.label"
          :name="tab.value"
        />
      </el-tabs>

      <!-- 订单表格 -->
      <el-table
        :data="orderList"
        v-loading="loading"
        class="order-table"
        @row-click="handleRowClick"
        empty-text="暂无订单"
        stripe
      >
        <el-table-column
          prop="order_no"
          label="订单号"
          min-width="180"
          show-overflow-tooltip
        />
        <el-table-column
          prop="shopName"
          label="店铺"
          min-width="140"
          show-overflow-tooltip
        />
        <el-table-column
          prop="itemCount"
          label="商品数"
          width="80"
          align="center"
        />
        <el-table-column
          prop="pay_amount"
          label="实付金额"
          width="130"
          align="right"
        >
          <template #default="{ row }">
            <span class="price">¥{{ parseFloat(row.pay_amount).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="status"
          label="状态"
          width="100"
          align="center"
        >
          <template #default="{ row }">
            <el-tag
              :type="statusMap[row.status]?.type || 'info'"
              size="small"
              class="status-tag"
            >
              {{ statusMap[row.status]?.label || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="created_at"
          label="下单时间"
          width="170"
        >
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column
          label="操作"
          width="110"
          align="center"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              class="action-link"
              @click.stop="goDetail(row.id)"
            >
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空态 -->
      <div v-if="!loading && orderList.length === 0" class="empty-state">
        <el-empty description="暂无相关订单">
          <el-button type="primary" @click="$router.push('/')">去逛逛</el-button>
        </el-empty>
      </div>

      <!-- 分页 -->
      <div v-if="total > 0" class="pagination-wrapper">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          background
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { getOrderList } from '@/api/order';

const router = useRouter();

/** 状态 Tabs 配置 */
const statusTabs = [
  { label: '全部', value: '' },
  { label: '待付款', value: 'pending_pay' },
  { label: '已支付', value: 'paid' },
  { label: '已发货', value: 'shipped' },
  { label: '已收货', value: 'received' },
  { label: '已完成', value: 'completed' },
  { label: '已取消', value: 'cancelled' },
  { label: '退款中', value: 'refunding' },
];

/** 状态映射：标签样式 */
const statusMap = {
  pending_pay: { label: '待付款', type: 'warning' },
  paid: { label: '已支付', type: '' },
  shipped: { label: '已发货', type: '' },
  received: { label: '已收货', type: 'success' },
  completed: { label: '已完成', type: 'success' },
  cancelled: { label: '已取消', type: 'info' },
  refunding: { label: '退款中', type: 'danger' },
};

const activeStatus = ref('');
const loading = ref(false);
const orderList = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(10);

/** 格式化日期 */
function formatDate(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** 获取订单列表 */
async function fetchOrders() {
  loading.value = true;
  try {
    const params = {
      page: page.value,
      pageSize: pageSize.value,
    };
    if (activeStatus.value) {
      params.status = activeStatus.value;
    }
    const res = await getOrderList(params);
    orderList.value = res.data.list || [];
    total.value = res.data.total || 0;
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '加载订单失败');
    orderList.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

/** Tab 切换 */
function handleStatusChange() {
  page.value = 1;
  fetchOrders();
}

/** 分页变化 */
function handlePageChange(val) {
  page.value = val;
  fetchOrders();
}

function handleSizeChange(val) {
  pageSize.value = val;
  page.value = 1;
  fetchOrders();
}

/** 行点击 */
function handleRowClick(row) {
  goDetail(row.id);
}

/** 跳转详情 */
function goDetail(orderId) {
  router.push({ name: 'OrderDetail', params: { orderId } });
}

onMounted(() => {
  fetchOrders();
});
</script>

<style scoped>
.order-list-page {
  --order-primary: #f97316;
  --order-primary-light: #fff7ed;
  --order-primary-hover: #ea580c;
}

.page-header {
  padding: var(--app-space-xl) var(--app-space-xl) 0;
}

.page-title {
  font-size: var(--app-font-3xl);
  font-weight: 600;
  color: var(--app-text-primary);
  margin: 0;
}

.page-content {
  padding: 0 var(--app-space-xl) var(--app-space-xl);
}

/* Tabs 暖橙色主题 */
.order-tabs :deep(.el-tabs__active-bar) {
  background-color: var(--order-primary);
}

.order-tabs :deep(.el-tabs__item.is-active) {
  color: var(--order-primary);
  font-weight: 600;
}

.order-tabs :deep(.el-tabs__item:hover) {
  color: var(--order-primary-hover);
}

.order-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
}

/* 表格 */
.order-table {
  cursor: pointer;
}

.order-table :deep(.el-table__row:hover) {
  background-color: var(--order-primary-light);
}

.order-table :deep(.el-table__header th) {
  background-color: #fafafa;
  color: var(--app-text-regular);
  font-weight: 600;
}

.price {
  color: var(--order-primary);
  font-weight: 600;
  font-size: var(--app-font-base);
}

.action-link {
  color: var(--order-primary) !important;
}

.action-link:hover {
  color: var(--order-primary-hover) !important;
}

.status-tag {
  border-radius: var(--app-radius-sm);
}

/* 空态 */
.empty-state {
  padding: var(--app-space-4xl) 0;
}

/* 分页 */
.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--app-space-lg);
}

.pagination-wrapper :deep(.el-pagination.is-background .el-pager li.is-active) {
  background-color: var(--order-primary);
}

/* 响应式 */
@media (max-width: 768px) {
  .page-header {
    padding: var(--app-space-base) var(--app-space-base) 0;
  }

  .page-content {
    padding: 0 var(--app-space-base) var(--app-space-base);
  }

  .page-title {
    font-size: var(--app-font-xl);
  }

  .order-table :deep(.el-table) {
    font-size: var(--app-font-sm);
  }
}
</style>
