<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">商品管理</h1>
        <span class="product-count" v-if="total > 0">共 {{ total }} 件商品</span>
      </div>
      <el-button type="primary" size="large" @click="goToPublish">
        <el-icon><Plus /></el-icon>
        <span>发布商品</span>
      </el-button>
    </div>

    <!-- 状态筛选 -->
    <div class="filter-section">
      <el-radio-group
        v-model="statusFilter"
        size="default"
        class="status-filter"
        @change="handleFilterChange"
      >
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="draft">
          草稿
          <span class="filter-count" v-if="counts.draft">{{ counts.draft }}</span>
        </el-radio-button>
        <el-radio-button value="pending_review">
          待审核
          <span class="filter-count" v-if="counts.pending_review">{{ counts.pending_review }}</span>
        </el-radio-button>
        <el-radio-button value="approved">
          已通过
          <span class="filter-count" v-if="counts.approved">{{ counts.approved }}</span>
        </el-radio-button>
        <el-radio-button value="listed">
          已上架
          <span class="filter-count" v-if="counts.listed">{{ counts.listed }}</span>
        </el-radio-button>
        <el-radio-button value="delisted">
          已下架
          <span class="filter-count" v-if="counts.delisted">{{ counts.delisted }}</span>
        </el-radio-button>
      </el-radio-group>
    </div>

    <!-- 商品表格 -->
    <div class="table-section">
      <el-table
        :data="productList"
        v-loading="loading"
        stripe
        row-key="id"
        class="product-table"
        empty-text="暂无商品，点击上方按钮发布第一件商品"
      >
        <el-table-column type="index" label="#" width="55" align="center" />

        <el-table-column label="商品信息" min-width="260">
          <template #default="{ row }">
            <div class="product-info">
              <el-image
                v-if="row.main_image"
                :src="row.main_image"
                fit="cover"
                class="product-thumb"
                :preview-teleported="true"
              />
              <div v-else class="product-thumb-placeholder">
                <el-icon><Picture /></el-icon>
              </div>
              <div class="product-meta">
                <span class="product-title">{{ row.title }}</span>
                <span class="product-id">ID: {{ row.id }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag
              :type="statusTagType(row.status)"
              size="default"
              effect="light"
              class="status-tag"
            >
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="价格区间" width="180" align="right">
          <template #default="{ row }">
            <template v-if="row.minPrice !== undefined && row.maxPrice !== undefined">
              <span class="price-text">¥{{ parseFloat(row.minPrice).toFixed(2) }}</span>
              <span class="price-sep"> ~ </span>
              <span class="price-text">¥{{ parseFloat(row.maxPrice).toFixed(2) }}</span>
            </template>
            <span v-else class="text-muted">暂未设置</span>
          </template>
        </el-table-column>

        <el-table-column label="总库存" width="90" align="center">
          <template #default="{ row }">
            <span :class="{ 'text-warning': row.totalStock !== undefined && row.totalStock < 10 }">
              {{ row.totalStock !== undefined ? row.totalStock : '-' }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="创建时间" width="170" align="center">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-btns">
              <el-button type="primary" link size="small" @click="goToEdit(row)">
                编辑
              </el-button>
              <el-button
                v-if="row.status === 'listed'"
                type="warning"
                link
                size="small"
                :loading="actionLoading === row.id"
                @click="handleDelist(row)"
              >
                下架
              </el-button>
              <el-button
                v-if="row.status === 'delisted' || row.status === 'approved'"
                type="success"
                link
                size="small"
                :loading="actionLoading === row.id"
                @click="handleList(row)"
              >
                上架
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 分页 -->
    <div class="pagination-wrap" v-if="total > 0">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        background
        @size-change="fetchProducts"
        @current-change="fetchProducts"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, Picture } from '@element-plus/icons-vue';
import { getProductList, listProduct, delistProduct } from '@/api/merchant.js';

const router = useRouter();

/* ===== 状态 ===== */
const loading = ref(false);
const actionLoading = ref(null);
const productList = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const statusFilter = ref('');
const counts = reactive({});

/* ===== 状态映射 ===== */
const statusMap = {
  draft: '草稿',
  pending_review: '待审核',
  approved: '已通过',
  rejected: '已驳回',
  listed: '已上架',
  delisted: '已下架',
};

const statusTagMap = {
  draft: 'info',
  pending_review: 'warning',
  approved: 'success',
  rejected: 'danger',
  listed: '',
  delisted: 'info',
};

function statusLabel(status) {
  return statusMap[status] || status;
}

function statusTagType(status) {
  return statusTagMap[status] || 'info';
}

function formatTime(timestamp) {
  if (!timestamp) return '-';
  const d = new Date(timestamp);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/* ===== 数据获取 ===== */
async function fetchProducts() {
  loading.value = true;
  try {
    const params = { page: page.value, pageSize: pageSize.value };
    if (statusFilter.value) {
      params.status = statusFilter.value;
    }
    const res = await getProductList(params);
    const data = res.data || res;
    productList.value = data.list || [];
    total.value = data.total || 0;
  } catch (err) {
    ElMessage.error('加载商品列表失败');
  } finally {
    loading.value = false;
  }
}

function handleFilterChange() {
  page.value = 1;
  fetchProducts();
}

/* ===== 操作 ===== */
async function handleList(row) {
  actionLoading.value = row.id;
  try {
    await listProduct(row.id);
    ElMessage.success('商品已上架');
    await fetchProducts();
  } catch (err) {
    ElMessage.error('上架失败');
  } finally {
    actionLoading.value = null;
  }
}

async function handleDelist(row) {
  actionLoading.value = row.id;
  try {
    await ElMessageBox.confirm(
      `确定要将「${row.title}」下架吗？下架后用户将无法看到该商品。`,
      '确认下架',
      { confirmButtonText: '确定下架', cancelButtonText: '取消', type: 'warning' }
    );
    await delistProduct(row.id);
    ElMessage.success('商品已下架');
    await fetchProducts();
  } catch (err) {
    if (err !== 'cancel' && err?.message !== 'cancel') {
      ElMessage.error('下架失败');
    }
  } finally {
    actionLoading.value = null;
  }
}

/* ===== 导航 ===== */
function goToPublish() {
  router.push({ name: 'ProductPublish' });
}

function goToEdit(row) {
  router.push({ name: 'ProductPublish', query: { productId: row.id } });
}

/* ===== 生命周期 ===== */
onMounted(() => {
  fetchProducts();
});
</script>

<style scoped>
.page-container {
  padding: var(--app-space-xl, 24px);
  min-height: 100%;
  background: var(--app-bg-page, #f0f2f5);
}

/* ——— 页面头部 ——— */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--app-space-xl, 24px);
  background: linear-gradient(135deg, #1a2332 0%, #1e2d3d 100%);
  border-radius: var(--app-radius-md, 12px);
  margin-bottom: var(--app-space-lg, 20px);
  color: #fff;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: var(--app-space-md, 12px);
}

.page-title {
  font-size: var(--app-font-2xl, 1.25rem);
  font-weight: 700;
  color: #fff;
  margin: 0;
  letter-spacing: 0.5px;
}

.product-count {
  font-size: var(--app-font-sm, 0.8125rem);
  color: rgba(255, 255, 255, 0.6);
}

.page-header :deep(.el-button--primary) {
  background: #3b82f6;
  border-color: #3b82f6;
  font-weight: 600;
  padding: 10px 24px;
}

.page-header :deep(.el-button--primary):hover {
  background: #2563eb;
  border-color: #2563eb;
}

/* ——— 筛选区 ——— */
.filter-section {
  background: var(--app-bg-container, #fff);
  padding: var(--app-space-base, 16px) var(--app-space-xl, 24px);
  border-radius: var(--app-radius-base, 8px);
  margin-bottom: var(--app-space-base, 16px);
  box-shadow: var(--app-shadow-level-1, 0 1px 3px rgba(0,0,0,0.06));
}

.status-filter {
  flex-wrap: wrap;
}

.status-filter :deep(.el-radio-button__inner) {
  padding: 8px 18px;
  border-radius: 6px !important;
  border: 1px solid var(--app-border-light, #e5e7eb);
  font-size: var(--app-font-sm, 0.8125rem);
  transition: all 0.2s var(--app-ease-standard, ease);
}

.status-filter :deep(.el-radio-button) {
  margin-right: 6px;
}

.status-filter :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #1e3a5f;
  border-color: #1e3a5f;
  color: #fff;
  font-weight: 600;
  box-shadow: 0 2px 6px rgba(30, 58, 95, 0.3);
}

.filter-count {
  margin-left: 4px;
  font-size: var(--app-font-xs, 0.75rem);
  opacity: 0.8;
}

/* ——— 表格区 ——— */
.table-section {
  background: var(--app-bg-container, #fff);
  border-radius: var(--app-radius-base, 8px);
  overflow: hidden;
  box-shadow: var(--app-shadow-level-1, 0 1px 3px rgba(0,0,0,0.06));
}

.product-table :deep(.el-table__header th) {
  background: #f8f9fb;
  color: #374151;
  font-weight: 600;
  font-size: var(--app-font-sm, 0.8125rem);
  border-bottom: 2px solid #d1d5db;
}

.product-table :deep(.el-table__row:hover > td) {
  background: #f0f4ff !important;
}

/* 商品信息 */
.product-info {
  display: flex;
  align-items: center;
  gap: var(--app-space-md, 12px);
}

.product-thumb {
  width: 56px;
  height: 56px;
  border-radius: var(--app-radius-sm, 4px);
  flex-shrink: 0;
  border: 1px solid var(--app-border-light, #e5e7eb);
}

.product-thumb-placeholder {
  width: 56px;
  height: 56px;
  border-radius: var(--app-radius-sm, 4px);
  flex-shrink: 0;
  background: #f3f4f6;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  font-size: 20px;
  border: 1px solid var(--app-border-light, #e5e7eb);
}

.product-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow: hidden;
}

.product-title {
  font-size: var(--app-font-base, 0.875rem);
  font-weight: 500;
  color: var(--app-text-primary, #1a1a2e);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.product-id {
  font-size: var(--app-font-xs, 0.75rem);
  color: var(--app-text-secondary, #6b7280);
}

/* 状态标签 */
.status-tag {
  font-weight: 500;
  min-width: 64px;
  text-align: center;
}

/* 价格 */
.price-text {
  font-weight: 600;
  color: #1a1a2e;
  font-variant-numeric: tabular-nums;
}

.price-sep {
  color: #9ca3af;
  font-size: var(--app-font-xs, 0.75rem);
}

.text-muted {
  color: var(--app-text-secondary, #6b7280);
  font-size: var(--app-font-sm, 0.8125rem);
}

.text-warning {
  color: #f59e0b;
  font-weight: 600;
}

/* 操作按钮 */
.action-btns {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

/* 分页 */
.pagination-wrap {
  display: flex;
  justify-content: center;
  padding: var(--app-space-lg, 20px) 0;
}
</style>
