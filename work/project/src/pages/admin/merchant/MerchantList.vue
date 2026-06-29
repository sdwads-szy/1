<template>
  <div class="admin-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <el-icon class="header-icon"><Shop /></el-icon>
        <h1 class="header-title">商家审核管理</h1>
      </div>
      <div class="header-right">
        <span class="header-count" v-if="total > 0">共 {{ total }} 条记录</span>
      </div>
    </div>

    <!-- 状态筛选 -->
    <div class="filter-card">
      <div class="filter-label">店铺状态：</div>
      <el-radio-group
        v-model="filterStatus"
        @change="handleStatusChange"
        class="status-filter"
      >
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="pending">
          <span class="filter-dot pending"></span>待审核
        </el-radio-button>
        <el-radio-button value="active">
          <span class="filter-dot active"></span>已激活
        </el-radio-button>
        <el-radio-button value="frozen">
          <span class="filter-dot frozen"></span>已冻结
        </el-radio-button>
        <el-radio-button value="cleared">
          <span class="filter-dot cleared"></span>已清退
        </el-radio-button>
      </el-radio-group>
    </div>

    <!-- 表格卡片 -->
    <div class="table-card">
      <el-table
        :data="tableData"
        v-loading="loading"
        element-loading-text="加载中…"
        element-loading-background="rgba(255,255,255,0.7)"
        @row-click="handleRowClick"
        highlight-current-row
        style="width: 100%"
        :header-cell-style="tableHeaderStyle"
        empty-text="暂无商家数据"
      >
        <el-table-column
          prop="shopId"
          label="商家ID"
          width="90"
          align="center"
        />
        <el-table-column
          prop="shopName"
          label="店铺名称"
          min-width="200"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <span class="shop-name-cell">{{ row.shopName }}</span>
          </template>
        </el-table-column>
        <el-table-column
          label="手机号"
          width="140"
        >
          <template #default="{ row }">
            <span class="phone-cell">{{ row.phone || '***' }}</span>
          </template>
        </el-table-column>
        <el-table-column
          label="店铺状态"
          width="110"
          align="center"
        >
          <template #default="{ row }">
            <el-tag
              :type="shopStatusTag(row.status)"
              size="small"
              effect="plain"
              class="status-tag"
            >
              {{ shopStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="资质状态"
          width="110"
          align="center"
        >
          <template #default="{ row }">
            <el-tag
              :type="qualStatusTag(row.qualificationStatus)"
              size="small"
              effect="plain"
              class="status-tag"
            >
              {{ qualStatusLabel(row.qualificationStatus) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="注册时间"
          width="175"
        >
          <template #default="{ row }">
            <span class="time-cell">{{ formatDateTime(row.createdAt) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          label="操作"
          width="80"
          align="center"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              size="small"
              @click.stop="handleRowClick(row)"
            >
              审核
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper" v-if="total > 0">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handlePageSizeChange"
          @current-change="handlePageChange"
          background
        />
      </div>
    </div>

    <!-- 空态（无筛选结果） -->
    <div class="empty-card" v-if="!loading && tableData.length === 0">
      <el-empty description="暂无符合条件的商家" :image-size="120">
        <el-button type="primary" @click="handleStatusChange('')">查看全部</el-button>
      </el-empty>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Shop } from '@element-plus/icons-vue';
import { getMerchantList } from '@/api/admin/merchant.js';

const router = useRouter();

// 状态
const loading = ref(false);
const tableData = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const filterStatus = ref('');

// 表格头部样式
const tableHeaderStyle = {
  background: '#f8f9fc',
  color: '#1e293b',
  fontWeight: 600,
  fontSize: '13px',
  borderBottom: '2px solid #e2e8f0',
  height: '48px'
};

// 店铺状态映射
const shopStatusMap = {
  pending: { label: '待审核', tag: 'warning' },
  active: { label: '已激活', tag: 'success' },
  frozen: { label: '已冻结', tag: 'info' },
  cleared: { label: '已清退', tag: 'danger' }
};

function shopStatusLabel(status) {
  return shopStatusMap[status]?.label || status || '-';
}

function shopStatusTag(status) {
  return shopStatusMap[status]?.tag || 'info';
}

// 资质状态映射
const qualStatusMap = {
  pending: { label: '待审核', tag: 'warning' },
  approved: { label: '已通过', tag: 'success' },
  rejected: { label: '已驳回', tag: 'danger' }
};

function qualStatusLabel(status) {
  return qualStatusMap[status]?.label || status || '-';
}

function qualStatusTag(status) {
  return qualStatusMap[status]?.tag || 'info';
}

// 日期格式化
function formatDateTime(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const h = String(d.getHours()).padStart(2, '0');
  const min = String(d.getMinutes()).padStart(2, '0');
  const s = String(d.getSeconds()).padStart(2, '0');
  return `${y}-${m}-${day} ${h}:${min}:${s}`;
}

// 加载列表
async function fetchList() {
  loading.value = true;
  try {
    const params = { page: page.value, pageSize: pageSize.value };
    if (filterStatus.value) {
      params.status = filterStatus.value;
    }
    const res = await getMerchantList(params);
    if (res && res.data) {
      tableData.value = res.data.list || [];
      total.value = res.data.total || 0;
    } else {
      tableData.value = [];
      total.value = 0;
    }
  } catch (err) {
    ElMessage.error('加载商家列表失败，请稍后重试');
    tableData.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

// 状态筛选
function handleStatusChange() {
  page.value = 1;
  fetchList();
}

// 分页
function handlePageChange(newPage) {
  page.value = newPage;
  fetchList();
}

function handlePageSizeChange(newSize) {
  pageSize.value = newSize;
  page.value = 1;
  fetchList();
}

// 点击行 → 跳转详情
function handleRowClick(row) {
  if (!row || !row.shopId) return;
  router.push({
    name: 'AdminMerchantDetail',
    params: { id: String(row.shopId) }
  });
}

onMounted(() => {
  fetchList();
});
</script>

<style scoped>
/* ===== 页面容器 ===== */
.admin-page {
  padding: var(--app-space-xl, 24px);
  min-height: calc(100vh - 56px);
  background: #f0f2f5;
}

/* ===== 页面标题 ===== */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding: 20px 24px;
  background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
  border-radius: var(--app-radius-md, 12px);
  box-shadow: var(--app-shadow-level-1, 0 1px 3px rgba(0,0,0,0.06));
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon {
  font-size: 24px;
  color: rgba(255, 255, 255, 0.9);
}

.header-title {
  margin: 0;
  font-size: var(--app-font-2xl, 1.25rem);
  font-weight: 600;
  color: #ffffff;
  letter-spacing: 0.5px;
}

.header-right {
  display: flex;
  align-items: center;
}

.header-count {
  font-size: var(--app-font-sm, 0.8125rem);
  color: rgba(255, 255, 255, 0.75);
  background: rgba(255, 255, 255, 0.12);
  padding: 4px 14px;
  border-radius: 20px;
}

/* ===== 筛选卡片 ===== */
.filter-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  margin-bottom: 16px;
  background: #ffffff;
  border-radius: var(--app-radius-base, 8px);
  box-shadow: var(--app-shadow-level-1, 0 1px 3px rgba(0,0,0,0.06));
}

.filter-label {
  font-size: var(--app-font-base, 0.875rem);
  font-weight: 500;
  color: var(--app-text-regular, #374151);
  white-space: nowrap;
}

.status-filter :deep(.el-radio-button__inner) {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 7px 16px;
  font-size: 13px;
  border-radius: 0;
}

.filter-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.filter-dot.pending { background: #f59e0b; }
.filter-dot.active  { background: #22c55e; }
.filter-dot.frozen  { background: #3b82f6; }
.filter-dot.cleared { background: #ef4444; }

/* ===== 表格卡片 ===== */
.table-card {
  background: #ffffff;
  border-radius: var(--app-radius-md, 12px);
  box-shadow: var(--app-shadow-level-1, 0 1px 3px rgba(0,0,0,0.06));
  overflow: hidden;
}

.table-card :deep(.el-table) {
  --el-table-border-color: #eef0f4;
  --el-table-row-hover-bg-color: #f8fafd;
}

.table-card :deep(.el-table .el-table__row) {
  cursor: pointer;
  transition: background 0.12s ease;
}

.table-card :deep(.el-table .el-table__row:hover) {
  background: #f1f5f9;
}

.table-card :deep(.el-table .current-row) {
  background: #eef4ff !important;
}

.table-card :deep(.el-table td) {
  padding: 12px 0;
  font-size: var(--app-font-base, 0.875rem);
  color: var(--app-text-regular, #374151);
}

.shop-name-cell {
  font-weight: 500;
  color: var(--app-text-primary, #1a1a2e);
}

.phone-cell {
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  color: var(--app-text-secondary, #6b7280);
  font-size: 13px;
}

.time-cell {
  color: var(--app-text-secondary, #6b7280);
  font-size: 13px;
}

.status-tag {
  font-weight: 500;
  min-width: 62px;
  text-align: center;
}

/* ===== 分页 ===== */
.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding: 16px 20px;
  border-top: 1px solid #f0f2f5;
}

/* ===== 空态 ===== */
.empty-card {
  background: #ffffff;
  border-radius: var(--app-radius-md, 12px);
  box-shadow: var(--app-shadow-level-1, 0 1px 3px rgba(0,0,0,0.06));
  padding: 48px 24px;
  text-align: center;
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .admin-page {
    padding: 12px;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    padding: 16px;
  }

  .filter-card {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .status-filter {
    flex-wrap: wrap;
  }

  .status-filter :deep(.el-radio-button__inner) {
    padding: 6px 10px;
    font-size: 12px;
  }
}
</style>
