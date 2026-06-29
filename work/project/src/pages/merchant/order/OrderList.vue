<template>
  <div class="page-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2 class="page-title">订单管理</h2>
    </div>

    <!-- 状态筛选 Tab -->
    <div class="filter-tabs">
      <el-radio-group v-model="filterStatus" @change="handleStatusChange" size="small">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="pending_pay">待支付</el-radio-button>
        <el-radio-button value="paid">已支付</el-radio-button>
        <el-radio-button value="shipped">已发货</el-radio-button>
        <el-radio-button value="received">已收货</el-radio-button>
        <el-radio-button value="completed">已完成</el-radio-button>
        <el-radio-button value="cancelled">已取消</el-radio-button>
        <el-radio-button value="refunding">退款中</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 订单表格 -->
    <div class="card">
      <el-table
        :data="orderList"
        v-loading="loading"
        stripe
        style="width: 100%"
        :header-cell-style="{ background: 'var(--app-bg-hover)', color: 'var(--app-text-primary)', fontWeight: 600, fontSize: 'var(--app-font-sm)' }"
        empty-text="暂无订单数据"
      >
        <el-table-column prop="order_no" label="订单编号" min-width="180" show-overflow-tooltip />
        <el-table-column prop="total_amount" label="原价金额" width="110" align="right">
          <template #default="{ row }">
            <span class="amount">¥{{ parseFloat(row.total_amount).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="discount_amount" label="优惠抵扣" width="110" align="right">
          <template #default="{ row }">
            <span class="amount discount">-¥{{ parseFloat(row.discount_amount || 0).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="pay_amount" label="实付金额" width="110" align="right">
          <template #default="{ row }">
            <span class="amount pay">¥{{ parseFloat(row.pay_amount).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="下单时间" width="170" align="center">
          <template #default="{ row }">
            <span class="time-text">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'paid'"
              type="primary"
              size="small"
              :loading="shippingId === row.id"
              @click="handleShip(row)"
            >
              发货
            </el-button>
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
          @size-change="fetchOrders"
          @current-change="fetchOrders"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { getMerchantOrders } from '@/api/merchant';
import { shipOrder } from '@/api/admin/order';

// 状态
const loading = ref(false);
const orderList = ref([]);
const filterStatus = ref('');
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const shippingId = ref(null);

// 状态标签映射
const statusLabelMap = {
  pending_pay: '待支付',
  paid: '已支付',
  shipped: '已发货',
  received: '已收货',
  completed: '已完成',
  cancelled: '已取消',
  refunding: '退款中'
};

const statusTagMap = {
  pending_pay: 'warning',
  paid: 'primary',
  shipped: 'success',
  received: '',
  completed: 'success',
  cancelled: 'info',
  refunding: 'danger'
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

async function fetchOrders() {
  loading.value = true;
  try {
    const params = { page: page.value, pageSize: pageSize.value };
    if (filterStatus.value) {
      params.status = filterStatus.value;
    }
    const res = await getMerchantOrders(params);
    orderList.value = res.data?.list ?? [];
    total.value = res.data?.total ?? 0;
  } catch {
    ElMessage.error('获取订单列表失败，请稍后重试');
  } finally {
    loading.value = false;
  }
}

function handleStatusChange() {
  page.value = 1;
  fetchOrders();
}

async function handleShip(row) {
  try {
    await ElMessageBox.confirm(
      `确认对订单「${row.order_no}」执行发货操作？`,
      '发货确认',
      { confirmButtonText: '确认发货', cancelButtonText: '取消', type: 'warning' }
    );
  } catch {
    return;
  }

  shippingId.value = row.id;
  try {
    await shipOrder(row.id);
    ElMessage.success('发货成功');
    fetchOrders();
  } catch {
    ElMessage.error('发货失败，请稍后重试');
  } finally {
    shippingId.value = null;
  }
}

onMounted(() => {
  fetchOrders();
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
  font-weight: 500;
  font-family: 'JetBrains Mono', 'Consolas', monospace;
}

.amount.pay {
  color: #2c3e50;
  font-weight: 600;
}

.amount.discount {
  color: #999;
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
