<template>
  <div class="search-page">
    <!-- 顶部搜索栏 -->
    <header class="search-header">
      <div class="search-header-inner">
        <el-button class="back-btn" text @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <div class="search-input-wrapper" ref="searchWrapperRef">
          <el-input
            v-model="keyword"
            ref="searchInputRef"
            size="large"
            placeholder="搜索商品"
            clearable
            @keyup.enter="doSearch"
            @input="onKeywordInput"
            @focus="onFocus"
            @clear="onClear"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-button type="primary" class="search-btn" @click="doSearch">搜索</el-button>

          <!-- 联想建议下拉 -->
          <div v-if="showSuggestions" class="suggestions-panel">
            <div v-if="suggestionsLoading" class="suggestions-loading">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>搜索中...</span>
            </div>
            <template v-else-if="suggestionList.length > 0">
              <div
                v-for="(item, idx) in suggestionList"
                :key="idx"
                class="suggestion-item"
                @mousedown.prevent="selectSuggestion(item.text)"
              >
                <el-icon class="suggestion-icon">
                  <Clock v-if="item.type === 'history'" />
                  <Star v-else-if="item.type === 'hot'" />
                  <Search v-else />
                </el-icon>
                <span class="suggestion-text">{{ item.text }}</span>
                <span class="suggestion-type-tag">{{ typeLabel(item.type) }}</span>
              </div>
            </template>
            <div v-else class="suggestions-empty">暂无搜索建议</div>
          </div>
        </div>
      </div>
    </header>

    <!-- 主体内容区 -->
    <div class="search-body">
      <!-- 筛选栏 -->
      <div class="filter-bar">
        <div class="filter-row">
          <span class="filter-label">排序：</span>
          <div class="sort-options">
            <span
              v-for="opt in sortOptions"
              :key="opt.value"
              class="sort-chip"
              :class="{ active: currentSort === opt.value }"
              @click="changeSort(opt.value)"
            >{{ opt.label }}</span>
          </div>
          <div class="price-filter">
            <span class="filter-label">价格：</span>
            <el-input-number
              v-model="priceMin"
              :min="0"
              :max="999999"
              :step="10"
              size="small"
              placeholder="最低"
              controls-position="right"
              class="price-input"
            />
            <span class="price-separator">—</span>
            <el-input-number
              v-model="priceMax"
              :min="0"
              :max="999999"
              :step="10"
              size="small"
              placeholder="最高"
              controls-position="right"
              class="price-input"
            />
            <el-button size="small" class="price-confirm" @click="doSearch">确定</el-button>
          </div>
        </div>
      </div>

      <!-- 热搜词（无搜索词时显示） -->
      <div v-if="!isSearching && !hasResults && hotTags.length > 0" class="hot-search-section">
        <div class="hot-search-header">
          <el-icon class="hot-icon"><TrendCharts /></el-icon>
          <span>热门搜索</span>
        </div>
        <div class="hot-tags">
          <span
            v-for="(tag, idx) in hotTags"
            :key="idx"
            class="hot-tag"
            :class="{ 'hot-top': idx < 3 }"
            @click="selectSuggestion(tag)"
          >
            <span v-if="idx < 3" class="hot-rank">{{ idx + 1 }}</span>
            {{ tag }}
          </span>
        </div>
      </div>

      <!-- 搜索结果统计 -->
      <div v-if="isSearching" class="results-header">
        <span v-if="!loading">共找到 <em class="result-count">{{ total }}</em> 件商品</span>
      </div>

      <!-- 加载态 -->
      <div v-if="loading" class="loading-area">
        <el-skeleton :rows="3" animated />
        <div class="product-grid-skeleton">
          <el-skeleton v-for="i in 8" :key="i" animated class="product-card-skeleton">
            <template #template>
              <div class="skeleton-img"></div>
              <div class="skeleton-info">
                <el-skeleton-item variant="text" style="width:80%;height:16px;margin-bottom:8px" />
                <el-skeleton-item variant="text" style="width:50%;height:20px;margin-bottom:6px" />
                <el-skeleton-item variant="text" style="width:30%;height:14px" />
              </div>
            </template>
          </el-skeleton>
        </div>
      </div>

      <!-- 空态 -->
      <div v-else-if="isSearching && !loading && products.length === 0" class="empty-area">
        <el-empty description="未找到相关商品">
          <template #image>
            <el-icon :size="72" color="#d1d5db"><Search /></el-icon>
          </template>
          <p class="empty-hint">试试更换关键词或调整筛选条件</p>
          <el-button type="primary" @click="clearAll">清除筛选</el-button>
        </el-empty>
      </div>

      <!-- 商品结果网格 -->
      <div v-else-if="isSearching && products.length > 0" class="product-grid">
        <div
          v-for="product in products"
          :key="product.id"
          class="product-card"
          @click="goToDetail(product.id)"
        >
          <div class="product-img-box">
            <el-image
              :src="product.mainImage"
              fit="cover"
              class="product-img"
              lazy
            >
              <template #error>
                <div class="img-placeholder">
                  <el-icon :size="40"><PictureFilled /></el-icon>
                </div>
              </template>
              <template #placeholder>
                <div class="img-placeholder img-loading">
                  <el-icon :size="24" class="is-loading"><Loading /></el-icon>
                </div>
              </template>
            </el-image>
          </div>
          <div class="product-info">
            <p class="product-title">{{ product.title }}</p>
            <p class="product-price">
              <span class="price-symbol">¥</span>
              <span class="price-value">{{ formatPrice(product.minPrice) }}</span>
            </p>
            <p class="product-shop">{{ product.shopName }}</p>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="isSearching && total > pageSize" class="pagination-wrapper">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          :pager-count="5"
          layout="prev, pager, next"
          background
          @current-change="onPageChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { ArrowLeft, Search, Clock, Star, Loading, TrendCharts, PictureFilled } from '@element-plus/icons-vue';
import { searchProducts, getSuggestions } from '@/api/search.js';

const router = useRouter();
const route = useRoute();

// ===== 搜索状态 =====
const keyword = ref('');
const isSearching = ref(false);
const loading = ref(false);
const products = ref([]);
const total = ref(0);

// ===== 筛选状态 =====
const currentSort = ref('relevance');
const priceMin = ref(null);
const priceMax = ref(null);
const page = ref(1);
const pageSize = ref(20);

const sortOptions = [
  { label: '综合排序', value: 'relevance' },
  { label: '价格从低到高', value: 'price_asc' },
  { label: '价格从高到低', value: 'price_desc' },
  { label: '最新上架', value: 'newest' },
];

// ===== 联想建议状态 =====
const searchInputRef = ref(null);
const searchWrapperRef = ref(null);
const showSuggestions = ref(false);
const suggestionList = ref([]);
const suggestionsLoading = ref(false);
let debounceTimer = null;

// ===== 热搜词 =====
const hotTags = ref([]);

const hasResults = computed(() => products.value.length > 0);

// ===== 方法 =====
function typeLabel(type) {
  const map = { history: '历史', hot: '热门', suggestion: '推荐' };
  return map[type] || '';
}

function formatPrice(price) {
  if (price == null) return '0.00';
  return parseFloat(price).toFixed(2);
}

function goBack() {
  router.back();
}

function goToDetail(productId) {
  router.push({ name: 'ProductDetail', params: { productId } });
}

function buildSearchParams() {
  const params = {
    q: keyword.value.trim(),
    page: page.value,
    pageSize: pageSize.value,
  };
  if (currentSort.value !== 'relevance') {
    params.sort = currentSort.value;
  }
  if (priceMin.value != null && priceMin.value > 0) {
    params.priceMin = priceMin.value;
  }
  if (priceMax.value != null && priceMax.value > 0) {
    params.priceMax = priceMax.value;
  }
  return params;
}

async function doSearch() {
  const q = keyword.value.trim();
  if (!q) {
    isSearching.value = false;
    products.value = [];
    total.value = 0;
    return;
  }
  isSearching.value = true;
  loading.value = true;
  page.value = 1;
  showSuggestions.value = false;
  try {
    const params = buildSearchParams();
    const res = await searchProducts(params);
    products.value = res.products || [];
    total.value = res.total || 0;
    if (res.suggestions && res.suggestions.length > 0 && !hotTags.value.length) {
      hotTags.value = res.suggestions.filter(s => s.type === 'hot').map(s => s.text);
    }
  } catch {
    products.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

async function onPageChange(newPage) {
  page.value = newPage;
  loading.value = true;
  try {
    const params = buildSearchParams();
    const res = await searchProducts(params);
    products.value = res.products || [];
    total.value = res.total || 0;
  } catch {
    products.value = [];
  } finally {
    loading.value = false;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

function changeSort(sort) {
  currentSort.value = sort;
  doSearch();
}

async function onKeywordInput(val) {
  if (debounceTimer) clearTimeout(debounceTimer);
  if (!val || !val.trim()) {
    showSuggestions.value = false;
    suggestionList.value = [];
    return;
  }
  debounceTimer = setTimeout(async () => {
    suggestionsLoading.value = true;
    showSuggestions.value = true;
    try {
      const res = await getSuggestions({ q: val.trim() });
      suggestionList.value = (Array.isArray(res) ? res : res?.suggestions) || [];
    } catch {
      suggestionList.value = [];
    } finally {
      suggestionsLoading.value = false;
    }
  }, 300);
}

function onFocus() {
  if (keyword.value.trim() && suggestionList.value.length > 0) {
    showSuggestions.value = true;
  }
}

function onClear() {
  showSuggestions.value = false;
  suggestionList.value = [];
  isSearching.value = false;
  products.value = [];
  total.value = 0;
}

function selectSuggestion(text) {
  keyword.value = text;
  showSuggestions.value = false;
  doSearch();
  nextTick(() => searchInputRef.value?.blur());
}

function clearAll() {
  keyword.value = '';
  currentSort.value = 'relevance';
  priceMin.value = null;
  priceMax.value = null;
  page.value = 1;
  isSearching.value = false;
  products.value = [];
  total.value = 0;
  showSuggestions.value = false;
}

function handleClickOutside(e) {
  if (searchWrapperRef.value && !searchWrapperRef.value.contains(e.target)) {
    showSuggestions.value = false;
  }
}

// ===== 生命周期 =====
onMounted(() => {
  document.addEventListener('click', handleClickOutside);
  const q = route.query.q;
  if (q) {
    keyword.value = q;
    doSearch();
  }
});

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside);
  if (debounceTimer) clearTimeout(debounceTimer);
});

// 监听路由 query 变化（从首页再次搜索）
watch(() => route.query.q, (newQ) => {
  if (newQ && newQ !== keyword.value) {
    keyword.value = newQ;
    doSearch();
  }
});
</script>

<style scoped>
/* ===== 暖橙色主色调 ===== */
.search-page {
  --search-primary: #f97316;
  --search-primary-light: #fff7ed;
  --search-primary-lighter: #ffedd5;
  --search-primary-dark: #ea580c;
  --search-primary-darkest: #c2410c;
  min-height: 100vh;
  background: var(--app-bg-page, #f5f5f7);
  padding-bottom: var(--app-space-3xl, 40px);
}

/* ===== 顶部搜索栏 ===== */
.search-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: #fff;
  box-shadow: var(--app-shadow-level-1);
  padding: var(--app-space-sm, 8px) 0;
}

.search-header-inner {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: var(--app-space-sm, 8px);
  padding: 0 var(--app-space-base, 16px);
}

.back-btn {
  flex-shrink: 0;
  font-size: var(--app-font-xl, 1.125rem);
  color: var(--app-text-secondary, #6b7280);
}

.back-btn:hover {
  color: var(--search-primary);
}

.search-input-wrapper {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
  gap: 0;
}

.search-input-wrapper :deep(.el-input) {
  flex: 1;
}

.search-input-wrapper :deep(.el-input__wrapper) {
  border-radius: var(--app-radius-base, 8px) 0 0 var(--app-radius-base, 8px);
  border-right: none;
  box-shadow: 0 0 0 1px var(--app-border-base, #d1d5db) inset;
  transition: all 0.15s var(--app-ease-standard);
}

.search-input-wrapper :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--search-primary-light) inset;
}

.search-input-wrapper :deep(.el-input.is-focus .el-input__wrapper) {
  box-shadow: 0 0 0 2px var(--search-primary) inset;
}

.search-btn {
  flex-shrink: 0;
  height: 40px;
  border-radius: 0 var(--app-radius-base, 8px) var(--app-radius-base, 8px) 0;
  background: var(--search-primary);
  border-color: var(--search-primary);
  font-size: var(--app-font-base, 0.875rem);
  padding: 0 24px;
  transition: all 0.15s var(--app-ease-standard);
}

.search-btn:hover {
  background: var(--search-primary-dark);
  border-color: var(--search-primary-dark);
}

.search-btn:active {
  background: var(--search-primary-darkest);
  border-color: var(--search-primary-darkest);
}

/* ===== 联想建议面板 ===== */
.suggestions-panel {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 74px; /* 留出搜索按钮宽度 */
  background: #fff;
  border-radius: var(--app-radius-base, 8px);
  box-shadow: var(--app-shadow-level-3);
  z-index: 200;
  max-height: 360px;
  overflow-y: auto;
  padding: var(--app-space-xs, 4px) 0;
}

.suggestions-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--app-space-sm, 8px);
  padding: var(--app-space-xl, 24px);
  color: var(--app-text-secondary, #6b7280);
  font-size: var(--app-font-sm, 0.8125rem);
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: var(--app-space-sm, 8px);
  padding: var(--app-space-sm, 8px) var(--app-space-base, 16px);
  cursor: pointer;
  transition: background 0.15s var(--app-ease-standard);
  font-size: var(--app-font-base, 0.875rem);
}

.suggestion-item:hover {
  background: var(--search-primary-light);
}

.suggestion-icon {
  color: var(--app-text-secondary, #6b7280);
  font-size: var(--app-font-base, 0.875rem);
  flex-shrink: 0;
}

.suggestion-text {
  flex: 1;
  color: var(--app-text-primary, #1a1a2e);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.suggestion-type-tag {
  flex-shrink: 0;
  font-size: var(--app-font-xs, 0.75rem);
  color: var(--app-text-disabled, #b0b7c3);
  background: var(--app-bg-disabled, #f3f4f6);
  padding: 2px 6px;
  border-radius: var(--app-radius-sm, 4px);
}

.suggestions-empty {
  padding: var(--app-space-xl, 24px);
  text-align: center;
  color: var(--app-text-secondary, #6b7280);
  font-size: var(--app-font-sm, 0.8125rem);
}

/* ===== 主体内容 ===== */
.search-body {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--app-space-lg, 20px) var(--app-space-base, 16px);
}

/* ===== 筛选栏 ===== */
.filter-bar {
  background: #fff;
  border-radius: var(--app-radius-base, 8px);
  padding: var(--app-space-md, 12px) var(--app-space-base, 16px);
  margin-bottom: var(--app-space-base, 16px);
  box-shadow: var(--app-shadow-level-1);
}

.filter-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--app-space-base, 16px);
}

.filter-label {
  font-size: var(--app-font-sm, 0.8125rem);
  color: var(--app-text-secondary, #6b7280);
  flex-shrink: 0;
}

.sort-options {
  display: flex;
  gap: var(--app-space-xs, 4px);
}

.sort-chip {
  display: inline-block;
  padding: 4px 14px;
  font-size: var(--app-font-sm, 0.8125rem);
  border-radius: var(--app-radius-full, 9999px);
  cursor: pointer;
  color: var(--app-text-regular, #374151);
  background: var(--app-bg-hover, #f9fafb);
  transition: all 0.15s var(--app-ease-standard);
  user-select: none;
}

.sort-chip:hover {
  color: var(--search-primary);
  background: var(--search-primary-light);
}

.sort-chip.active {
  color: #fff;
  background: var(--search-primary);
}

.price-filter {
  display: flex;
  align-items: center;
  gap: var(--app-space-xs, 4px);
  margin-left: auto;
}

.price-input {
  width: 110px;
}

.price-input :deep(.el-input__wrapper) {
  border-radius: var(--app-radius-sm, 4px);
}

.price-separator {
  color: var(--app-text-secondary, #6b7280);
  font-size: var(--app-font-sm, 0.8125rem);
}

.price-confirm {
  border-radius: var(--app-radius-sm, 4px);
  background: var(--search-primary);
  border-color: var(--search-primary);
  color: #fff;
  font-size: var(--app-font-xs, 0.75rem);
  height: 32px;
  padding: 0 14px;
}

.price-confirm:hover {
  background: var(--search-primary-dark);
  border-color: var(--search-primary-dark);
}

/* ===== 热搜词 ===== */
.hot-search-section {
  background: #fff;
  border-radius: var(--app-radius-base, 8px);
  padding: var(--app-space-xl, 24px);
  margin-bottom: var(--app-space-base, 16px);
  box-shadow: var(--app-shadow-level-1);
}

.hot-search-header {
  display: flex;
  align-items: center;
  gap: var(--app-space-sm, 8px);
  font-size: var(--app-font-lg, 1rem);
  font-weight: 600;
  color: var(--app-text-primary, #1a1a2e);
  margin-bottom: var(--app-space-base, 16px);
}

.hot-icon {
  color: var(--search-primary);
  font-size: var(--app-font-xl, 1.125rem);
}

.hot-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--app-space-sm, 8px);
}

.hot-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 16px;
  border-radius: var(--app-radius-full, 9999px);
  background: var(--app-bg-hover, #f9fafb);
  color: var(--app-text-regular, #374151);
  font-size: var(--app-font-sm, 0.8125rem);
  cursor: pointer;
  transition: all 0.15s var(--app-ease-standard);
  user-select: none;
}

.hot-tag:hover {
  background: var(--search-primary-lighter);
  color: var(--search-primary-dark);
  transform: translateY(-1px);
}

.hot-tag.hot-top {
  background: var(--search-primary-light);
  color: var(--search-primary-dark);
  font-weight: 500;
}

.hot-rank {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 4px;
  background: var(--search-primary);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
}

/* ===== 搜索结果头部 ===== */
.results-header {
  margin-bottom: var(--app-space-md, 12px);
  font-size: var(--app-font-sm, 0.8125rem);
  color: var(--app-text-secondary, #6b7280);
}

.result-count {
  color: var(--search-primary);
  font-weight: 600;
  font-style: normal;
}

/* ===== 加载态 ===== */
.loading-area {
  padding: var(--app-space-base, 16px) 0;
}

.product-grid-skeleton {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--app-space-lg, 20px);
  margin-top: var(--app-space-base, 16px);
}

.product-card-skeleton {
  background: #fff;
  border-radius: var(--app-radius-base, 8px);
  padding: var(--app-space-md, 12px);
}

.skeleton-img {
  width: 100%;
  aspect-ratio: 1;
  background: var(--app-bg-disabled, #f3f4f6);
  border-radius: var(--app-radius-sm, 4px);
  margin-bottom: var(--app-space-md, 12px);
}

.skeleton-info {
  padding: 0 var(--app-space-xs, 4px);
}

/* ===== 空态 ===== */
.empty-area {
  background: #fff;
  border-radius: var(--app-radius-base, 8px);
  padding: var(--app-space-4xl, 48px) var(--app-space-base, 16px);
  box-shadow: var(--app-shadow-level-1);
  text-align: center;
}

.empty-hint {
  color: var(--app-text-secondary, #6b7280);
  font-size: var(--app-font-sm, 0.8125rem);
  margin: var(--app-space-sm, 8px) 0 var(--app-space-base, 16px);
}

/* ===== 商品网格 ===== */
.product-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--app-space-lg, 20px);
}

.product-card {
  background: #fff;
  border-radius: var(--app-radius-md, 12px);
  overflow: hidden;
  cursor: pointer;
  box-shadow: var(--app-shadow-level-1);
  transition: all 0.25s var(--app-ease-standard);
}

.product-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--app-shadow-level-2);
}

.product-card:active {
  transform: translateY(0);
  box-shadow: var(--app-shadow-level-1);
}

.product-img-box {
  width: 100%;
  aspect-ratio: 1;
  overflow: hidden;
  background: var(--app-bg-hover, #f9fafb);
}

.product-img {
  width: 100%;
  height: 100%;
}

.product-img :deep(img) {
  transition: transform 0.3s var(--app-ease-standard);
}

.product-card:hover .product-img :deep(img) {
  transform: scale(1.04);
}

.img-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--app-bg-disabled, #f3f4f6);
  color: var(--app-text-disabled, #b0b7c3);
}

.img-loading {
  background: var(--app-bg-hover, #f9fafb);
}

.product-info {
  padding: var(--app-space-md, 12px);
}

.product-title {
  font-size: var(--app-font-base, 0.875rem);
  color: var(--app-text-primary, #1a1a2e);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin: 0 0 var(--app-space-sm, 8px);
  min-height: 2.8em;
}

.product-price {
  margin: 0 0 var(--app-space-xs, 4px);
  display: flex;
  align-items: baseline;
  gap: 2px;
}

.price-symbol {
  font-size: var(--app-font-sm, 0.8125rem);
  color: var(--search-primary-dark);
  font-weight: 600;
}

.price-value {
  font-size: var(--app-font-2xl, 1.25rem);
  color: var(--search-primary-dark);
  font-weight: 700;
  line-height: 1;
}

.product-shop {
  margin: 0;
  font-size: var(--app-font-xs, 0.75rem);
  color: var(--app-text-secondary, #6b7280);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ===== 分页 ===== */
.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: var(--app-space-2xl, 32px);
}

.pagination-wrapper :deep(.el-pagination.is-background .el-pager li.is-active) {
  background-color: var(--search-primary);
}

.pagination-wrapper :deep(.el-pagination.is-background .el-pager li:not(.is-disabled):hover) {
  color: var(--search-primary);
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .search-header-inner {
    padding: 0 var(--app-space-sm, 8px);
  }

  .filter-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .price-filter {
    margin-left: 0;
    width: 100%;
    flex-wrap: wrap;
  }

  .price-input {
    width: 100px;
  }

  .product-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: var(--app-space-sm, 8px);
  }

  .product-info {
    padding: var(--app-space-sm, 8px);
  }

  .product-title {
    font-size: var(--app-font-sm, 0.8125rem);
    -webkit-line-clamp: 2;
  }

  .price-value {
    font-size: var(--app-font-lg, 1rem);
  }

  .suggestions-panel {
    right: 64px;
  }
}

@media (max-width: 576px) {
  .product-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: var(--app-space-sm, 8px);
  }

  .sort-options {
    flex-wrap: wrap;
  }

  .search-btn {
    padding: 0 16px;
    font-size: var(--app-font-sm, 0.8125rem);
  }
}
</style>
