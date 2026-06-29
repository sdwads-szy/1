<template>
  <div class="admin-order-list">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">订单管理</h1>
      <p class="page-subtitle">平台后台 · 全量订单查询与管理</p>
    </div>

    <!-- 筛选卡片 -->
    <div class="filter-card">
      <el-form :model="filters" inline class="filter-form">
        <el-form-item label="订单号">
          <el-input
            v-model="filters.order_no"
            placeholder="输入订单号"
            clearable
            style="width: 200px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="订单状态">
          <el-select
            v-model="filters.status"
            placeholder="全部状态"
            clearable
            style="width: 160px"
          >
            <el-option
              v-for="s in statusOptions"
              :key="s.value"
              :label="s.label"
              :value="s.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="店铺ID">
          <el-input
            v-model.number="filters.shop_id"
            placeholder="店铺ID"
            clearable
            style="width: 140px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="下单时间">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 260px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 表格卡片 -->
    <div class="table-card">
      <el-table
        v-loading="loading"
        :data="list"
        stripe
        highlight-current-row
        @row-click="handleRowClick"
        class="order-table"
      >
        <el-table-column label="订单号" prop="order_no" min-width="200" show-overflow-tooltip />
        <el-table-column label="用户ID" prop="user_id" width="100" align="center" />
        <el-table-column label="店铺ID" prop="shop_id" width="100" align="center" />
        <el-table-column label="原价总额" prop="total_amount" width="120" align="right">
          <template #default="{ row }">
            <span class="amount">¥{{ parseFloat(row.total_amount || 0).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="实付金额" prop="pay_amount" width="120" align="right">
          <template #default="{ row }">
            <span class="amount pay-amount">¥{{ parseFloat(row.pay_amount || 0).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" prop="status" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="支付方式" prop="pay_method" width="100" align="center">
          <template #default="{ row }">
            <span v-if="row.pay_method">{{ payMethodLabel(row.pay_method) }}</span>
            <span v-else class="text-muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="下单时间" prop="created_at" width="180" align="center">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>

      <!-- 空态 -->
      <div v-if="!loading && list.length === 0" class="empty-state">
        <el-empty description="暂无订单数据" />
      </div>

      <!-- 分页 -->
      <div v-if="total > 0" class="pagination-wrap">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSearch"
          @current-change="handleSearch"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * AdminOrderList — 平台后台订单列表页
 * 多条件筛选：订单号/状态/店铺ID/时间范围
 * 点击行跳转详情（params 传递 id）
 */
import { ref, reactive, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { Search, Refresh } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { getOrderList } from '@/api/admin/order.js';

const router = useRouter();

// ---------- 状态 ----------
const list = ref([]);
const total = ref(0);
const loading = ref(false);

const filters = reactive({
  order_no: '',
  status: '',
  shop_id: null
});

const dateRange = ref([]);

const pagination = reactive({
  page: 1,
  pageSize: 20
});

// ---------- 常量 ----------
const STATUS_MAP = {
  pending_pay: '待支付',
  paid: '已支付',
  shipped: '已发货',
  received: '已收货',
  completed: '已完成',
  cancelled: '已取消',
  refunding: '退款中'
};

const statusOptions = Object.entries(STATUS_MAP).map(([value, label]) => ({ value, label }));

const PAY_METHOD_MAP = {
  wxpay: '微信支付',
  alipay: '支付宝'
};

// ---------- 工具函数 ----------
function statusLabel(status) {
  return STATUS_MAP[status] || status;
}

function statusTagType(status) {
  const map = {
    pending_pay: 'warning',
    paid: 'primary',
    shipped: 'info',
    received: '',
    completed: 'success',
    cancelled: 'danger',
    refunding: 'danger'
  };
  return map[status] || 'info';
}

function payMethodLabel(method) {
  return PAY_METHOD_MAP[method] || method;
}

function formatTime(ts) {
  if (!ts) return '—';
  const d = new Date(ts);
  if (isNaN(d.getTime())) return '—';
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// ---------- 方法 ----------
async function fetchList() {
  loading.value = true;
  try {
    const params = {
      page: pagination.page,
      pageSize: pagination.pageSize
    };
    if (filters.order_no) params.orderNo = filters.order_no;
    if (filters.status) params.status = filters.status;
    if (filters.shop_id) params.shopId = filters.shop_id;
    if (dateRange.value && dateRange.value.length === 2) {
      params.startDate = dateRange.value[0];
      params.endDate = dateRange.value[1];
    }
    const res = await getOrderList(params);
    list.value = res.data?.list || [];
    total.value = res.data?.total || 0;
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || '获取订单列表失败');
    list.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  pagination.page = 1;
  fetchList();
}

function handleReset() {
  filters.order_no = '';
  filters.status = '';
  filters.shop_id = null;
  dateRange.value = [];
  pagination.page = 1;
  fetchList();
}

// 🛑 passBy: "params" → router.push 使用 params
function handleRowClick(row) {
  router.push({ name: 'AdminOrderDetail', params: { id: row.id } });
}

// ---------- 生命周期 ----------
onMounted(() => {
  fetchList();
});
</script>

<style scoped>
/* ===== 页面容器 ===== */
.admin-order-list {
  padding: var(--app-space-xl, 24px);
  min-height: 100%;
  background: var(--app-bg-page, #eef1f6);
}

.page-header {
  margin-bottom: var(--app-space-lg, 20px);
}

.page-title {
  margin: 0;
  font-size: var(--app-font-3xl, 1.5rem);
  font-weight: 700;
  color: #1a2332;
}

.page-subtitle {
  margin: 4px 0 0;
  font-size: var(--app-font-sm, 0.8125rem);
  color: var(--app-text-secondary, #6b7280);
}

/* ===== 筛选卡片 ===== */
.filter-card {
  background: var(--app-bg-container, #ffffff);
  border-radius: var(--app-radius-md, 12px);
  padding: var(--app-space-lg, 20px) var(--app-space-xl, 24px);
  margin-bottom: var(--app-space-base, 16px);
  box-shadow: var(--app-shadow-level-1, 0 1px 3px rgba(0,0,0,0.06));
  border-left: 3px solid #1e3a5f;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 0;
}

.filter-form :deep(.el-form-item) {
  margin-bottom: 0;
  margin-right: var(--app-space-base, 16px);
}

.filter-form :deep(.el-form-item:last-child) {
  margin-right: 0;
}

/* ===== 表格卡片 ===== */
.table-card {
  background: var(--app-bg-container, #ffffff);
  border-radius: var(--app-radius-md, 12px);
  padding: var(--app-space-base, 16px) var(--app-space-xl, 24px);
  box-shadow: var(--app-shadow-level-1, 0 1px 3px rgba(0,0,0,0.06));
}

.order-table {
  width: 100%;
}

.order-table :deep(.el-table__header th) {
  background: #f0f3f8;
  color: #1a2332;
  font-weight: 600;
  font-size: var(--app-font-sm, 0.8125rem);
  border-bottom: 2px solid #c8d0db;
}

.order-table :deep(.el-table__body tr) {
  cursor: pointer;
  transition: background-color 0.15s var(--app-ease-standard, ease);
}

.order-table :deep(.el-table__body tr:hover) {
  background: #f4f6fa;
}

.order-table :deep(.el-table__body tr.current-row) {
  background: #e8ecf4;
}

.amount {
  font-variant-numeric: tabular-nums;
  font-weight: 500;
}

.pay-amount {
  color: #1e3a5f;
  font-weight: 600;
}

.text-muted {
  color: var(--app-text-disabled, #b0b7c3);
}

/* ===== 空态 ===== */
.empty-state {
  padding: var(--app-space-3xl, 40px) 0;
}

/* ===== 分页 ===== */
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--app-space-base, 16px);
  padding-top: var(--app-space-md, 12px);
  border-top: 1px solid var(--app-border-light, #e5e7eb);
}

/* ===== Element Plus 按钮覆写（深蓝灰） ===== */
:deep(.el-button--primary) {
  --el-button-bg-color: #1e3a5f;
  --el-button-border-color: #1e3a5f;
  --el-button-hover-bg-color: #2b4f7d;
  --el-button-hover-border-color: #2b4f7d;
  --el-button-active-bg-color: #162d4a;
  --el-button-active-border-color: #162d4a;
}

:deep(.el-tag--primary) {
  --el-tag-bg-color: rgba(30, 58, 95, 0.1);
  --el-tag-border-color: rgba(30, 58, 95, 0.2);
  --el-tag-text-color: #1e3a5f;
}

:deep(.el-pagination .el-pager li.is-active) {
  background-color: #1e3a5f;
  border-color: #1e3a5f;
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #1e3a5f inset;
}

:deep(.el-select .el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #1e3a5f inset;
}
</style>
