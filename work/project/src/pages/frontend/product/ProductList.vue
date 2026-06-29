<template>
  <div class="page-container">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="filter-left">
        <div class="price-filter">
          <span class="filter-label">价格</span>
          <el-input-number
            v-model="filterForm.priceMin"
            :min="0"
            :precision="2"
            placeholder="最低价"
            size="small"
            controls-position="right"
            style="width: 130px"
          />
          <span class="price-separator">—</span>
          <el-input-number
            v-model="filterForm.priceMax"
            :min="0"
            :precision="2"
            placeholder="最高价"
            size="small"
            controls-position="right"
            style="width: 130px"
          />
        </div>
      </div>
      <div class="filter-right">
        <el-select
          v-model="filterForm.sort"
          placeholder="排序"
          size="small"
          style="width: 150px"
          @change="handleSortChange"
        >
          <el-option label="综合排序" value="default" />
          <el-option label="价格从低到高" value="price_asc" />
          <el-option label="价格从高到低" value="price_desc" />
          <el-option label="销量优先" value="sales_desc" />
        </el-select>
      </div>
    </div>

    <!-- 商品网格 -->
    <div v-loading="loading" class="product-grid" element-loading-background="rgba(255,255,255,0.7)">
      <div
        v-for="product in productList"
        :key="product.id"
        class="product-card"
        @click="goDetail(product.id)"
      >
        <div class="card-image-wrap">
          <img
            v-if="product.mainImage"
            :src="product.mainImage"
            :alt="product.title"
            class="card-image"
            loading="lazy"
          />
          <div v-else class="card-image-placeholder">
            <el-icon :size="40"><PictureFilled /></el-icon>
          </div>
        </div>
        <div class="card-info">
          <h3 class="card-title text-ellipsis" :title="product.title">
            {{ product.title }}
          </h3>
          <div class="card-bottom">
            <span class="card-price">
              ¥{{ parseFloat(product.minPrice || 0).toFixed(2) }}
            </span>
            <span class="card-sales">已售 {{ product.sales || 0 }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 空态 -->
    <div v-if="!loading && productList.length === 0" class="empty-state">
      <el-empty description="暂无商品" />
    </div>

    <!-- 分页 -->
    <div v-if="total > 0" class="pagination-wrap">
      <el-pagination
        v-model:current-page="pagination.page"
        :page-size="pagination.pageSize"
        :total="total"
        :page-sizes="[12, 24, 48]"
        layout="total, sizes, prev, pager, next"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup>
/**
 * ProductList - 买家端商品列表页
 * 功能：商品筛选、排序、分页、卡片网格展示
 * 主题：暖橙色
 */
import { ref, reactive, watch, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { PictureFilled } from '@element-plus/icons-vue';
import { getProductList } from '@/api/product';

const router = useRouter();

// 筛选表单
const filterForm = reactive({
  sort: 'default',
  priceMin: null,
  priceMax: null
});

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 12
});

// 数据
const productList = ref([]);
const total = ref(0);
const loading = ref(false);

/**
 * 构建请求参数（过滤空值）
 */
function buildParams() {
  const params = {
    page: pagination.page,
    pageSize: pagination.pageSize
  };
  if (filterForm.sort && filterForm.sort !== 'default') {
    params.sort = filterForm.sort;
  }
  if (filterForm.priceMin != null && filterForm.priceMin !== '') {
    params.priceMin = filterForm.priceMin;
  }
  if (filterForm.priceMax != null && filterForm.priceMax !== '') {
    params.priceMax = filterForm.priceMax;
  }
  return params;
}

/**
 * 获取商品列表
 */
async function fetchProducts() {
  loading.value = true;
  try {
    const params = buildParams();
    const res = await getProductList(params);
    productList.value = res.data.list || [];
    total.value = res.data.total || 0;
  } catch {
    productList.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

/**
 * 跳转商品详情 — passBy: params
 */
function goDetail(productId) {
  router.push({ name: 'ProductDetail', params: { productId } });
}

function handleSortChange() {
  pagination.page = 1;
  fetchProducts();
}

function handlePageChange() {
  fetchProducts();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function handleSizeChange() {
  pagination.page = 1;
  fetchProducts();
}

// 价格筛选防抖 500ms
let priceTimer = null;
watch(
  () => [filterForm.priceMin, filterForm.priceMax],
  () => {
    if (priceTimer) clearTimeout(priceTimer);
    priceTimer = setTimeout(() => {
      pagination.page = 1;
      fetchProducts();
    }, 500);
  }
);

onMounted(() => {
  fetchProducts();
});
</script>

<style scoped>
/* ===== 暖橙色主题变量 ===== */
.page-container {
  --product-primary: #ff6b35;
  --product-primary-dark: #e85d2c;
  --product-primary-light: #fff3ed;
  --product-primary-lightest: #fffaf7;
}

/* ===== 筛选栏 ===== */
.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  padding: 16px 20px;
  margin-bottom: 20px;
  background: #fff;
  border-radius: var(--app-radius-md, 12px);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.filter-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.price-filter {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  font-size: 13px;
  color: #6b7280;
  white-space: nowrap;
  font-weight: 500;
}

.price-separator {
  color: #9ca3af;
  font-size: 13px;
}

.filter-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ===== 商品网格 ===== */
.product-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 20px;
  min-height: 300px;
}

/* ===== 商品卡片 ===== */
.product-card {
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  transition:
    transform 0.25s cubic-bezier(0.4, 0, 0.2, 1),
    box-shadow 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.product-card:hover {
  transform: translateY(-6px);
  box-shadow:
    0 8px 28px rgba(255, 107, 53, 0.15),
    0 2px 8px rgba(0, 0, 0, 0.06);
}

.card-image-wrap {
  width: 100%;
  padding-top: 100%;
  position: relative;
  background: #f9fafb;
  overflow: hidden;
}

.card-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.product-card:hover .card-image {
  transform: scale(1.06);
}

.card-image-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #d1d5db;
  background: #f9fafb;
}

.card-info {
  padding: 14px 16px;
}

.card-title {
  font-size: 0.9375rem;
  font-weight: 500;
  color: #1a1a2e;
  line-height: 1.4;
  margin: 0 0 10px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-bottom {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.card-price {
  font-size: 1.25rem;
  font-weight: 700;
  color: #ff6b35;
  font-family:
    -apple-system,
    BlinkMacSystemFont,
    'Segoe UI',
    sans-serif;
}

.card-sales {
  font-size: 0.75rem;
  color: #9ca3af;
}

/* ===== 分页 ===== */
.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 32px;
  padding: 16px 0 8px;
}

/* ===== 空态 ===== */
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

/* ===== Element Plus 暖橙色覆盖 ===== */
:deep(.el-select .el-input.is-focus .el-input__wrapper) {
  box-shadow: 0 0 0 1px #ff6b35 inset;
}

:deep(.el-select .el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #ff6b35 inset;
}

:deep(.el-input-number .el-input.is-focus .el-input__wrapper) {
  box-shadow: 0 0 0 1px #ff6b35 inset;
}

:deep(.el-input-number .el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #ff6b35 inset;
}

:deep(.el-pagination .el-pager li.is-active) {
  background-color: #ff6b35;
  color: #fff;
}

:deep(.el-pagination .el-pager li:hover) {
  color: #ff6b35;
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .filter-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-left {
    flex-direction: column;
    align-items: stretch;
  }

  .price-filter {
    flex-wrap: wrap;
  }

  .product-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  .card-info {
    padding: 10px 12px;
  }

  .card-title {
    font-size: 0.8125rem;
  }

  .card-price {
    font-size: 1rem;
  }
}

@media (max-width: 480px) {
  .product-grid {
    gap: 8px;
  }

  .card-info {
    padding: 8px 10px;
  }
}
</style>
