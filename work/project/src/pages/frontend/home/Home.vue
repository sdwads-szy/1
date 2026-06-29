<template>
  <div class="page-container home-page">
    <!-- 搜索区 -->
    <section class="search-section">
      <div class="search-wrapper">
        <h1 class="search-title">发现好物</h1>
        <div class="search-input-group">
          <el-input
            v-model="searchQuery"
            size="large"
            placeholder="搜索商品..."
            clearable
            :prefix-icon="Search"
            @keyup.enter="handleSearch"
            @input="handleSearchInput"
            @focus="showSuggestions = true"
            @blur="handleSearchBlur"
          />
          <el-button
            type="primary"
            size="large"
            class="search-btn"
            @click="handleSearch"
          >
            搜索
          </el-button>
        </div>
        <!-- 搜索联想 -->
        <div
          v-if="showSuggestions && suggestions.length > 0"
          class="suggestions-dropdown"
        >
          <div
            v-for="item in suggestions"
            :key="item.text"
            class="suggestion-item"
            @mousedown.prevent="handleSuggestionClick(item)"
          >
            <el-icon class="suggestion-icon">
              <Search v-if="item.type === 'suggestion'" />
              <Clock v-else-if="item.type === 'history'" />
              <TrendCharts v-else />
            </el-icon>
            <span>{{ item.text }}</span>
            <span class="suggestion-type-tag">{{ suggestionTypeLabel(item.type) }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 类目导航区 -->
    <section class="category-section">
      <h2 class="section-title">
        <span>商品分类</span>
        <el-button
          v-if="categories.length > 0"
          type="primary"
          link
          size="small"
          @click="viewAllCategories"
        >
          全部分类
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </h2>

      <!-- 加载态 -->
      <div v-if="categoryLoading" class="category-grid">
        <div
          v-for="i in 8"
          :key="'cat-skel-' + i"
          class="category-card category-card--skeleton"
        >
          <div class="skeleton-icon"></div>
          <div class="skeleton-text"></div>
        </div>
      </div>

      <!-- 错误态 -->
      <div v-else-if="categoryError" class="error-block">
        <el-icon class="error-icon"><WarningFilled /></el-icon>
        <p>分类加载失败</p>
        <el-button size="small" @click="fetchCategories">重试</el-button>
      </div>

      <!-- 空态 -->
      <div v-else-if="categories.length === 0" class="empty-block">
        <el-icon class="empty-icon"><FolderOpened /></el-icon>
        <p>暂无分类</p>
      </div>

      <!-- 类目卡片网格 -->
      <div v-else class="category-grid">
        <div
          v-for="cat in displayCategories"
          :key="cat.id"
          class="category-card"
          @click="goToCategory(cat)"
        >
          <div class="category-card-icon">
            <el-icon :size="28">
              <component :is="categoryIcon(cat.name)" />
            </el-icon>
          </div>
          <span class="category-card-name">{{ cat.name }}</span>
          <span
            v-if="cat.children && cat.children.length"
            class="category-card-count"
          >
            {{ cat.children.length }}个子类
          </span>
        </div>
      </div>
    </section>

    <!-- 推荐商品区 -->
    <section class="recommend-section">
      <h2 class="section-title">
        <span>为你推荐</span>
        <el-button
          v-if="products.length > 0"
          type="primary"
          link
          size="small"
          @click="refreshRecommend"
        >
          换一批
          <el-icon><Refresh /></el-icon>
        </el-button>
      </h2>

      <!-- 加载态 -->
      <div v-if="productLoading" class="product-grid">
        <div
          v-for="i in 6"
          :key="'prod-skel-' + i"
          class="product-card product-card--skeleton"
        >
          <div class="skeleton-image"></div>
          <div class="skeleton-text skeleton-text--title"></div>
          <div class="skeleton-text skeleton-text--price"></div>
        </div>
      </div>

      <!-- 错误态 -->
      <div v-else-if="productError" class="error-block">
        <el-icon class="error-icon"><WarningFilled /></el-icon>
        <p>推荐加载失败</p>
        <el-button size="small" @click="fetchRecommendProducts">重试</el-button>
      </div>

      <!-- 空态 -->
      <div v-else-if="products.length === 0" class="empty-block">
        <el-icon class="empty-icon"><Goods /></el-icon>
        <p>暂无推荐商品</p>
      </div>

      <!-- 商品卡片网格 -->
      <div v-else class="product-grid">
        <div
          v-for="product in products"
          :key="product.id"
          class="product-card"
          @click="goToProduct(product)"
        >
          <div class="product-card-image">
            <img
              v-if="product.mainImage"
              :src="product.mainImage"
              :alt="product.title"
              loading="lazy"
              @error="handleImgError"
            />
            <div v-else class="product-card-image--placeholder">
              <el-icon :size="36"><Goods /></el-icon>
            </div>
          </div>
          <div class="product-card-body">
            <h3 class="product-card-title" :title="product.title">
              {{ product.title }}
            </h3>
            <div class="product-card-footer">
              <span class="product-card-price">
                <span class="price-symbol">¥</span>
                {{ formatPrice(product.minPrice) }}
              </span>
              <span
                v-if="product.sales"
                class="product-card-sales"
              >
                已售 {{ formatSales(product.sales) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
/**
 * Home 首页组件
 * - 搜索框 + 联想建议
 * - 类目导航网格
 * - 推荐商品展示
 */
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import {
  Search,
  Clock,
  TrendCharts,
  ArrowRight,
  WarningFilled,
  FolderOpened,
  Goods,
  Refresh,
  ShoppingCartFull,
  Iphone,
  Van,
  HomeFilled,
  Present,
  Reading,
  Suitcase
} from '@element-plus/icons-vue';
import { getCategoryTree } from '@/api/category';
import { getProductList } from '@/api/product';
import { getSearchSuggestions } from '@/api/search';

const router = useRouter();

/* ===== 搜索 ===== */
const searchQuery = ref('');
const showSuggestions = ref(false);
const suggestions = ref([]);

let debounceTimer = null;

function handleSearchInput(val) {
  if (debounceTimer) clearTimeout(debounceTimer);
  if (!val || val.trim().length === 0) {
    suggestions.value = [];
    return;
  }
  debounceTimer = setTimeout(async () => {
    try {
      const res = await getSearchSuggestions({ q: val.trim() });
      suggestions.value = Array.isArray(res) ? res : (res.data || []);
      showSuggestions.value = true;
    } catch {
      suggestions.value = [];
    }
  }, 300);
}

function handleSearchBlur() {
  setTimeout(() => {
    showSuggestions.value = false;
  }, 200);
}

function handleSearch() {
  const q = searchQuery.value.trim();
  if (!q) return;
  showSuggestions.value = false;
  router.push({ name: 'SearchResult', query: { q } });
}

function handleSuggestionClick(item) {
  searchQuery.value = item.text;
  showSuggestions.value = false;
  router.push({ name: 'SearchResult', query: { q: item.text } });
}

function suggestionTypeLabel(type) {
  const map = { history: '历史', hot: '热门', suggestion: '联想' };
  return map[type] || '';
}

/* ===== 类目 ===== */
const categories = ref([]);
const categoryLoading = ref(true);
const categoryError = ref(false);

const displayCategories = computed(() => {
  return categories.value.slice(0, 8);
});

async function fetchCategories() {
  categoryLoading.value = true;
  categoryError.value = false;
  try {
    const res = await getCategoryTree();
    const data = Array.isArray(res) ? res : (res.data || []);
    categories.value = data;
  } catch {
    categoryError.value = true;
  } finally {
    categoryLoading.value = false;
  }
}

function goToCategory(cat) {
  router.push({ name: 'ProductList', params: { categoryId: cat.id } });
}

function viewAllCategories() {
  if (categories.value.length > 0) {
    goToCategory(categories.value[0]);
  }
}

function categoryIcon(name) {
  const map = {
    '手机': Iphone,
    '数码': Iphone,
    '家电': HomeFilled,
    '服装': Suitcase,
    '美妆': Present,
    '食品': ShoppingCartFull,
    '图书': Reading,
    '汽车': Van
  };
  // 模糊匹配
  for (const [key, icon] of Object.entries(map)) {
    if ((name || '').includes(key)) return icon;
  }
  return Goods;
}

/* ===== 推荐商品 ===== */
const products = ref([]);
const productLoading = ref(true);
const productError = ref(false);

async function fetchRecommendProducts() {
  productLoading.value = true;
  productError.value = false;
  try {
    const res = await getProductList({ page: 1, pageSize: 6 });
    const data = res?.data || res;
    products.value = (data && data.list) ? data.list : (Array.isArray(data) ? data : []);
  } catch {
    productError.value = true;
  } finally {
    productLoading.value = false;
  }
}

function refreshRecommend() {
  const page = Math.floor(Math.random() * 5) + 1;
  productLoading.value = true;
  productError.value = false;
  getProductList({ page, pageSize: 6 })
    .then(res => {
      const data = res?.data || res;
      products.value = (data && data.list) ? data.list : (Array.isArray(data) ? data : []);
    })
    .catch(() => {
      productError.value = true;
    })
    .finally(() => {
      productLoading.value = false;
    });
}

function goToProduct(product) {
  router.push({ name: 'ProductDetail', params: { id: product.id } });
}

function formatPrice(val) {
  if (val == null) return '0.00';
  return parseFloat(val).toFixed(2);
}

function formatSales(val) {
  if (val == null) return '0';
  if (val >= 10000) return (val / 10000).toFixed(1) + '万';
  return String(val);
}

function handleImgError(e) {
  e.target.style.display = 'none';
}

onMounted(() => {
  fetchCategories();
  fetchRecommendProducts();
});
</script>

<style scoped>
/* ===== 页面容器 ===== */
.home-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--app-space-xl) var(--app-space-base);
  min-height: 100vh;
}

/* ===== 搜索区 ===== */
.search-section {
  padding: var(--app-space-3xl) 0 var(--app-space-2xl);
  text-align: center;
}

.search-wrapper {
  position: relative;
  max-width: 600px;
  margin: 0 auto;
}

.search-title {
  font-size: var(--app-font-3xl);
  font-weight: var(--app-font-weight-bold, 700);
  color: #c2410c;
  margin: 0 0 var(--app-space-xl);
  letter-spacing: 0.02em;
}

.search-input-group {
  display: flex;
  gap: 0;
  box-shadow: var(--app-shadow-level-2);
  border-radius: var(--app-radius-full);
  overflow: hidden;
}

.search-input-group :deep(.el-input__wrapper) {
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
  box-shadow: none;
  border: 1px solid var(--app-border-base);
  border-right: none;
  padding-left: var(--app-space-lg);
  background: var(--app-bg-container);
  transition: border-color 0.15s var(--app-ease-standard);
}

.search-input-group :deep(.el-input__wrapper:hover) {
  border-color: var(--app-border-dark);
}

.search-input-group :deep(.el-input__wrapper.is-focus) {
  border-color: #ea580c;
  box-shadow: 0 0 0 3px rgba(234, 88, 12, 0.12);
}

.search-btn {
  flex-shrink: 0;
  border-radius: 0 var(--app-radius-full) var(--app-radius-full) 0;
  padding: 0 var(--app-space-2xl);
  background: linear-gradient(135deg, #f97316, #ea580c);
  border: none;
  font-weight: var(--app-font-weight-medium, 500);
  transition: all 0.2s var(--app-ease-standard);
}

.search-btn:hover {
  background: linear-gradient(135deg, #fb923c, #f97316);
  transform: none;
}

.search-btn:active {
  background: linear-gradient(135deg, #ea580c, #c2410c);
}

/* 联想下拉 */
.suggestions-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 6px;
  background: var(--app-bg-container);
  border-radius: var(--app-radius-md);
  box-shadow: var(--app-shadow-level-2);
  overflow: hidden;
  z-index: 100;
  animation: fadeIn 0.15s var(--app-ease-decelerate);
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: var(--app-space-sm);
  padding: var(--app-space-sm) var(--app-space-base);
  cursor: pointer;
  font-size: var(--app-font-base);
  color: var(--app-text-regular);
  transition: background 0.12s var(--app-ease-standard);
}

.suggestion-item:hover {
  background: #fff7ed;
}

.suggestion-icon {
  color: var(--app-text-secondary);
  font-size: var(--app-font-md);
  flex-shrink: 0;
}

.suggestion-type-tag {
  margin-left: auto;
  font-size: var(--app-font-xs);
  color: var(--app-text-disabled);
  background: var(--app-bg-hover);
  padding: 1px 6px;
  border-radius: var(--app-radius-sm);
}

/* ===== 区块标题 ===== */
.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 0 0 var(--app-space-lg);
  font-size: var(--app-font-xl);
  font-weight: var(--app-font-weight-semibold, 600);
  color: var(--app-text-primary);
  position: relative;
  padding-left: var(--app-space-md);
}

.section-title::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 20px;
  border-radius: 2px;
  background: linear-gradient(180deg, #f97316, #ea580c);
}

/* ===== 类目区 ===== */
.category-section {
  margin-bottom: var(--app-space-3xl);
}

.category-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: var(--app-space-md);
}

.category-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--app-space-sm);
  padding: var(--app-space-lg) var(--app-space-sm);
  background: var(--app-bg-container);
  border-radius: var(--app-radius-md);
  border: 1px solid var(--app-border-light);
  cursor: pointer;
  transition: all 0.25s var(--app-ease-standard);
  text-align: center;
}

.category-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--app-shadow-level-2);
  border-color: #fdba74;
  background: #fff7ed;
}

.category-card:active {
  transform: translateY(0);
  box-shadow: var(--app-shadow-level-1);
}

.category-card-icon {
  width: 52px;
  height: 52px;
  border-radius: var(--app-radius-base);
  background: linear-gradient(135deg, #fff7ed, #fed7aa);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ea580c;
}

.category-card-name {
  font-size: var(--app-font-base);
  font-weight: var(--app-font-weight-medium, 500);
  color: var(--app-text-primary);
  line-height: 1.3;
}

.category-card-count {
  font-size: var(--app-font-xs);
  color: var(--app-text-secondary);
}

/* 骨架屏 */
.category-card--skeleton .skeleton-icon {
  width: 52px;
  height: 52px;
  border-radius: var(--app-radius-base);
  background: linear-gradient(90deg, #f5f5f5 25%, #ebebeb 50%, #f5f5f5 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.category-card--skeleton .skeleton-text {
  width: 56px;
  height: 14px;
  border-radius: 4px;
  background: linear-gradient(90deg, #f5f5f5 25%, #ebebeb 50%, #f5f5f5 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

/* ===== 推荐商品区 ===== */
.recommend-section {
  margin-bottom: var(--app-space-3xl);
}

.product-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--app-space-lg);
}

.product-card {
  background: var(--app-bg-container);
  border-radius: var(--app-radius-md);
  overflow: hidden;
  border: 1px solid var(--app-border-light);
  cursor: pointer;
  transition: all 0.25s var(--app-ease-standard);
}

.product-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--app-shadow-level-2);
  border-color: #fdba74;
}

.product-card:active {
  transform: translateY(0);
}

.product-card-image {
  width: 100%;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  background: #fafaf9;
}

.product-card-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.35s var(--app-ease-standard);
}

.product-card:hover .product-card-image img {
  transform: scale(1.05);
}

.product-card-image--placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--app-text-disabled);
  background: #fafaf9;
}

.product-card-body {
  padding: var(--app-space-md);
}

.product-card-title {
  font-size: var(--app-font-base);
  font-weight: var(--app-font-weight-medium, 500);
  color: var(--app-text-primary);
  margin: 0 0 var(--app-space-sm);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: calc(var(--app-font-base) * 1.4 * 2);
}

.product-card-footer {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--app-space-sm);
}

.product-card-price {
  font-size: var(--app-font-lg);
  font-weight: var(--app-font-weight-bold, 700);
  color: #ea580c;
}

.price-symbol {
  font-size: var(--app-font-sm);
  font-weight: var(--app-font-weight-medium, 500);
}

.product-card-sales {
  font-size: var(--app-font-xs);
  color: var(--app-text-secondary);
  white-space: nowrap;
}

/* 骨架屏 */
.product-card--skeleton .skeleton-image {
  width: 100%;
  aspect-ratio: 4 / 3;
  background: linear-gradient(90deg, #f5f5f5 25%, #ebebeb 50%, #f5f5f5 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.product-card--skeleton .skeleton-text {
  height: 14px;
  border-radius: 4px;
  margin-bottom: var(--app-space-sm);
  background: linear-gradient(90deg, #f5f5f5 25%, #ebebeb 50%, #f5f5f5 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.skeleton-text--title {
  width: 70%;
}

.skeleton-text--price {
  width: 40%;
}

/* ===== 通用状态块 ===== */
.error-block,
.empty-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--app-space-4xl) var(--app-space-base);
  color: var(--app-text-secondary);
  gap: var(--app-space-sm);
}

.error-icon {
  font-size: 2.5rem;
  color: var(--app-color-danger);
}

.empty-icon {
  font-size: 2.5rem;
  color: var(--app-text-disabled);
}

.error-block p,
.empty-block p {
  margin: 0;
  font-size: var(--app-font-base);
}

/* ===== 动画 ===== */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .home-page {
    padding: var(--app-space-base) var(--app-space-sm);
  }

  .search-section {
    padding: var(--app-space-xl) 0 var(--app-space-lg);
  }

  .search-title {
    font-size: var(--app-font-2xl);
  }

  .category-grid {
    grid-template-columns: repeat(4, 1fr);
    gap: var(--app-space-sm);
  }

  .category-card {
    padding: var(--app-space-md) var(--app-space-xs);
  }

  .category-card-icon {
    width: 44px;
    height: 44px;
  }

  .category-card-name {
    font-size: var(--app-font-sm);
  }

  .product-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: var(--app-space-sm);
  }
}

@media (max-width: 576px) {
  .search-input-group {
    flex-direction: column;
    box-shadow: none;
    gap: var(--app-space-sm);
  }

  .search-input-group :deep(.el-input__wrapper) {
    border-radius: var(--app-radius-full);
    border-right: 1px solid var(--app-border-base);
  }

  .search-btn {
    border-radius: var(--app-radius-full);
  }

  .category-grid {
    grid-template-columns: repeat(3, 1fr);
  }

  .product-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
