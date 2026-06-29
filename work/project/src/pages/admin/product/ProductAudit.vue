<template>
  <div class="page-container">
    <!-- 页面标题区 -->
    <div class="page-header">
      <div class="page-header-left">
        <el-icon :size="22"><Checked /></el-icon>
        <h2 class="page-title">商品审核</h2>
        <el-tag v-if="total > 0" type="warning" size="small" class="pending-count">
          {{ total }} 件待处理
        </el-tag>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="filter-left">
        <el-radio-group v-model="filterStatus" @change="handleFilterChange" size="small">
          <el-radio-button value="pending_review">待审核</el-radio-button>
          <el-radio-button value="approved">已通过</el-radio-button>
          <el-radio-button value="rejected">已驳回</el-radio-button>
          <el-radio-button value="">全部</el-radio-button>
        </el-radio-group>
      </div>
      <div class="filter-right">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索商品标题"
          :prefix-icon="Search"
          clearable
          size="small"
          style="width: 240px"
          @clear="handleSearchClear"
          @keyup.enter="handleSearch"
        />
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="table-card">
      <el-table
        :data="list"
        v-loading="loading"
        element-loading-text="加载中..."
        element-loading-background="rgba(255,255,255,0.7)"
        stripe
        highlight-current-row
        style="width: 100%"
        @row-click="handleRowClick"
        :header-cell-style="{ background: '#f8f9fb', color: '#374151', fontWeight: 600, fontSize: '13px' }"
        :cell-style="{ cursor: 'pointer' }"
      >
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="title" label="商品标题" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="product-title-cell">
              <el-image
                v-if="row.main_image"
                :src="row.main_image"
                fit="cover"
                class="product-thumb"
                :preview-src-list="[row.main_image]"
              />
              <div v-else class="product-thumb-placeholder">
                <el-icon :size="20"><PictureFilled /></el-icon>
              </div>
              <span class="product-title-text">{{ row.title }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="shopName" label="所属店铺" width="160" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small" effect="plain">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="提交时间" width="180" align="center">
          <template #default="{ row }">
            <span class="time-text">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              link
              @click.stop="goDetail(row.id)"
            >
              审核
            </el-button>
          </template>
        </el-table-column>

        <!-- 空态 -->
        <template #empty>
          <div class="empty-state">
            <el-icon :size="48" color="#d1d5db"><FolderOpened /></el-icon>
            <p class="empty-text">暂无审核数据</p>
            <p class="empty-hint">所有商品已处理完毕</p>
          </div>
        </template>
      </el-table>
    </div>

    <!-- 分页 -->
    <div class="pagination-wrapper" v-if="total > 0">
      <span class="pagination-info">共 {{ total }} 条记录</span>
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="total"
        layout="sizes, prev, pager, next, jumper"
        background
        small
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup>
// 平台后台 - 商品审核队列
import { ref, reactive, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Checked, Search, PictureFilled, FolderOpened } from '@element-plus/icons-vue';
import { getAuditList } from '@/api/admin/product';

const router = useRouter();

// --- 状态 ---
const loading = ref(false);
const list = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const filterStatus = ref('pending_review');
const searchKeyword = ref('');

// --- 状态映射 ---
const STATUS_MAP = {
  draft: { label: '草稿', type: 'info' },
  pending_review: { label: '待审核', type: 'warning' },
  approved: { label: '已通过', type: 'success' },
  rejected: { label: '已驳回', type: 'danger' },
  listed: { label: '已上架', type: '' },
  delisted: { label: '已下架', type: 'info' }
};

function statusLabel(status) {
  return STATUS_MAP[status]?.label ?? status;
}

function statusTagType(status) {
  return STATUS_MAP[status]?.type ?? 'info';
}

// --- 工具方法 ---
function formatTime(ts) {
  if (!ts) return '-';
  const d = new Date(ts);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// --- 数据加载 ---
async function fetchList() {
  loading.value = true;
  try {
    const params = { page: page.value, pageSize: pageSize.value };
    if (filterStatus.value) params.status = filterStatus.value;
    if (searchKeyword.value.trim()) params.keyword = searchKeyword.value.trim();

    const res = await getAuditList(params);
    list.value = res.data?.list ?? [];
    total.value = res.data?.total ?? 0;
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || '加载审核列表失败');
    list.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

// --- 事件处理 ---
function handleFilterChange() {
  page.value = 1;
  fetchList();
}

function handleSearch() {
  page.value = 1;
  fetchList();
}

function handleSearchClear() {
  page.value = 1;
  fetchList();
}

function handlePageChange(p) {
  page.value = p;
  fetchList();
}

function handleSizeChange(s) {
  pageSize.value = s;
  page.value = 1;
  fetchList();
}

function handleRowClick(row) {
  goDetail(row.id);
}

function goDetail(id) {
  router.push({ name: 'AdminProductDetail', params: { id } });
}

// --- 生命周期 ---
onMounted(() => {
  fetchList();
});
</script>

<style scoped>
/* ========== 页面容器 ========== */
.page-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--app-space-xl, 24px);
}

/* ========== 页面标题区 ========== */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--app-space-lg, 20px);
}

.page-header-left {
  display: flex;
  align-items: center;
  gap: var(--app-space-sm, 8px);
  color: #1e3a5f;
}

.page-title {
  margin: 0;
  font-size: var(--app-font-3xl, 1.5rem);
  font-weight: 700;
  color: #1e3a5f;
  letter-spacing: -0.5px;
}

.pending-count {
  margin-left: var(--app-space-sm, 8px);
  font-weight: 600;
}

/* ========== 筛选栏 ========== */
.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--app-space-base, 16px);
  padding: var(--app-space-md, 12px) var(--app-space-base, 16px);
  background: var(--app-bg-container, #fff);
  border-radius: var(--app-radius-base, 8px);
  box-shadow: var(--app-shadow-level-1);
}

.filter-left,
.filter-right {
  display: flex;
  align-items: center;
  gap: var(--app-space-sm, 8px);
}

/* ========== 表格卡片 ========== */
.table-card {
  background: var(--app-bg-container, #fff);
  border-radius: var(--app-radius-base, 8px);
  box-shadow: var(--app-shadow-level-1);
  overflow: hidden;
}

/* ========== 商品标题列 ========== */
.product-title-cell {
  display: flex;
  align-items: center;
  gap: var(--app-space-sm, 8px);
}

.product-thumb {
  width: 48px;
  height: 48px;
  border-radius: var(--app-radius-sm, 4px);
  flex-shrink: 0;
  border: 1px solid var(--app-border-light, #e5e7eb);
}

.product-thumb-placeholder {
  width: 48px;
  height: 48px;
  border-radius: var(--app-radius-sm, 4px);
  flex-shrink: 0;
  background: var(--app-bg-disabled, #f3f4f6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--app-text-disabled, #b0b7c3);
  border: 1px dashed var(--app-border-light, #e5e7eb);
}

.product-title-text {
  font-weight: 500;
  color: var(--app-text-primary, #1a1a2e);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.time-text {
  font-size: var(--app-font-sm, 0.8125rem);
  color: var(--app-text-secondary, #6b7280);
}

/* ========== 空态 ========== */
.empty-state {
  padding: 48px 0;
  text-align: center;
}

.empty-text {
  margin: var(--app-space-base, 16px) 0 4px;
  font-size: var(--app-font-md, 0.9375rem);
  color: var(--app-text-secondary, #6b7280);
  font-weight: 500;
}

.empty-hint {
  margin: 0;
  font-size: var(--app-font-sm, 0.8125rem);
  color: var(--app-text-disabled, #b0b7c3);
}

/* ========== 分页 ========== */
.pagination-wrapper {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--app-space-base, 16px);
  padding: 0 4px;
}

.pagination-info {
  font-size: var(--app-font-sm, 0.8125rem);
  color: var(--app-text-secondary, #6b7280);
}

/* ========== 响应式 ========== */
@media (max-width: 768px) {
  .page-container {
    padding: var(--app-space-base, 16px);
  }

  .filter-bar {
    flex-direction: column;
    gap: var(--app-space-sm, 8px);
  }

  .filter-right {
    width: 100%;
  }

  .filter-right .el-input {
    width: 100% !important;
  }

  .pagination-wrapper {
    flex-direction: column;
    gap: var(--app-space-sm, 8px);
  }
}
</style>
