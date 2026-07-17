<!--
  全局搜索页 — 关键词搜索、筛选排序、分页
  来源: ←首页搜索栏; 去向: →商详
  UI风格: browse-search
-->
<template>
  <div class="search-page">
    <!-- 搜索头部 -->
    <header class="search-header">
      <div class="search-header-inner">
        <el-button class="back-btn" :icon="ArrowLeft" circle @click="router.back()" />
        <div class="search-input-wrap" :class="{ focused: inputFocused }">
          <el-icon class="search-prefix"><Search /></el-icon>
          <input
            ref="searchInputRef"
            v-model="keyword"
            type="text"
            class="search-input"
            placeholder="搜索你想要的商品…"
            @focus="inputFocused = true"
            @blur="inputFocused = false"
            @keyup.enter="triggerSearch"
          />
          <el-button
            v-if="keyword"
            class="clear-btn"
            :icon="Close"
            circle
            size="small"
            @click="clearKeyword"
          />
        </div>
        <el-button class="search-submit" type="primary" @click="triggerSearch">搜索</el-button>
      </div>
    </header>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="filter-bar-inner">
        <div class="filter-left">
          <el-select
            v-model="selectedCat"
            placeholder="全部分类"
            clearable
            size="small"
            @change="onFilterChange"
          >
            <el-option
              v-for="cat in categories"
              :key="cat.id"
              :label="cat.name"
              :value="cat.id"
            />
          </el-select>
        </div>
        <div class="filter-right">
          <el-radio-group
            v-model="sortBy"
            size="small"
            @change="onFilterChange"
          >
            <el-radio-button
              v-for="opt in sortOptions"
              :key="opt.value"
              :value="opt.value"
            >
              {{ opt.label }}
            </el-radio-button>
          </el-radio-group>
        </div>
      </div>
    </div>

    <!-- 结果区域 -->
    <section class="search-results">
      <!-- 结果摘要 -->
      <div v-if="!loading && !error && searched" class="result-summary">
        共 <strong>{{ total }}</strong> 件商品
      </div>

      <!-- 骨架屏 -->
      <div v-if="loading" class="product-grid">
        <div v-for="n in 8" :key="'s' + n" class="product-card-skeleton">
          <div class="skeleton-img"></div>
          <div class="skeleton-body">
            <div class="skeleton-line w80"></div>
            <div class="skeleton-line w60"></div>
            <div class="skeleton-line w40"></div>
          </div>
        </div>
      </div>

      <!-- 错误态 -->
      <div v-else-if="error" class="state-box">
        <div class="state-icon error-icon-bg">
          <el-icon :size="28"><WarningFilled /></el-icon>
        </div>
        <h3 class="state-title">商品加载失败</h3>
        <p class="state-desc">网络出了点小状况，刷新一下就好！</p>
        <div class="state-actions">
          <el-button type="primary" @click="fetchProducts">重新加载</el-button>
          <el-button @click="router.push({name:'Home'})">返回首页</el-button>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else-if="searched && productList.length === 0" class="state-box">
        <el-icon class="empty-icon" :size="64"><Search /></el-icon>
        <h3 class="state-title">没有找到相关商品</h3>
        <p class="state-desc">试试调整搜索词或筛选条件，好物就在不远处～</p>
        <div class="state-actions">
          <el-button type="primary" @click="clearFilters">清除筛选</el-button>
          <el-button @click="router.push({name:'Home'})">浏览全部商品</el-button>
        </div>
      </div>

      <!-- 商品网格 -->
      <template v-else>
        <div class="product-grid">
          <div
            v-for="product in productList"
            :key="product.id"
            class="product-card"
            @click="goProduct(product)"
          >
            <div class="card-img-wrap">
              <img
                :src="product.defaultImage || '/img/placeholder/product.svg'"
                :alt="product.name"
                loading="lazy"
              />
            </div>
            <div class="card-info">
              <p class="card-name">{{ product.name }}</p>
              <div class="card-price-row">
                <span class="card-price">&yen;{{ product.minPrice }}</span>
                <span class="card-sales">已售 {{ formatSales(product.sales) }}</span>
              </div>
              <p class="card-shop">{{ product.shopName }}</p>
            </div>
          </div>
        </div>

        <div v-if="total > pageSize" class="pagination-wrap">
          <el-pagination
            v-model:current-page="page"
            :page-size="pageSize"
            :total="total"
            layout="prev, pager, next"
            background
            @current-change="onPageChange"
          />
        </div>

        <p v-if="productList.length > 0 && page * pageSize >= total" class="end-hint">
          — 已经到底啦 —
        </p>
      </template>
    </section>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { Search, ArrowLeft, Close, WarningFilled } from '@element-plus/icons-vue'
import { getProducts, getCategories } from '@/api/products'

const router = useRouter()

const keyword = ref('')
const selectedCat = ref(null)
const sortBy = ref('default')
const productList = ref([])
const loading = ref(false)
const error = ref(false)
const searched = ref(false)
const page = ref(1)
const pageSize = 20
const total = ref(0)
const categories = ref([])
const inputFocused = ref(false)
const searchInputRef = ref(null)

let debounceTimer = null

const sortOptions = [
  { label: '默认', value: 'default' },
  { label: '价格↑', value: 'price_asc' },
  { label: '价格↓', value: 'price_desc' },
  { label: '销量', value: 'sales_desc' },
  { label: '最新', value: 'newest' }
]

function formatSales(n) {
  if (!n) return '0'
  if (n >= 10000) return (n / 10000).toFixed(1) + '万'
  return String(n)
}

async function fetchCategories() {
  try {
    const res = await getCategories()
    if (res.data?.success && res.data.data?.tree) {
      const flat = []
      function flatten(tree) {
        tree.forEach(cat => {
          flat.push({ id: cat.id, name: (cat.level === 2 ? '  ' : '') + cat.name })
          if (cat.children?.length) flatten(cat.children)
        })
      }
      flatten(res.data.data.tree)
      categories.value = flat
    }
  } catch {
    // 分类加载失败不阻塞
  }
}

async function fetchProducts() {
  loading.value = true
  error.value = false
  searched.value = true
  try {
    const params = { page: page.value, pageSize }
    if (keyword.value.trim()) params.q = keyword.value.trim()
    if (selectedCat.value) params.cat = selectedCat.value
    if (sortBy.value !== 'default') params.sort = sortBy.value

    const res = await getProducts(params)
    if (res.data?.success) {
      productList.value = res.data.data.list || []
      total.value = res.data.data.total || 0
    } else {
      error.value = true
    }
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

function debouncedSearch() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    page.value = 1
    fetchProducts()
  }, 300)
}

function triggerSearch() {
  clearTimeout(debounceTimer)
  page.value = 1
  fetchProducts()
}

function clearKeyword() {
  keyword.value = ''
  page.value = 1
  fetchProducts()
  nextTick(() => {
    searchInputRef.value?.focus()
  })
}

function onFilterChange() {
  page.value = 1
  fetchProducts()
}

function onPageChange(p) {
  page.value = p
  window.scrollTo({ top: 0, behavior: 'smooth' })
  fetchProducts()
}

function clearFilters() {
  keyword.value = ''
  selectedCat.value = null
  sortBy.value = 'default'
  page.value = 1
  fetchProducts()
}

function goProduct(product) {
  router.push({ name: 'ProductDetail', params: { id: product.id } })
}

watch(keyword, (newVal) => {
  if (newVal === '') {
    clearTimeout(debounceTimer)
    page.value = 1
    fetchProducts()
  } else {
    debouncedSearch()
  }
})

onMounted(() => {
  fetchCategories()
  fetchProducts()
})
</script>

<style scoped>
.search-page {
  min-height: 100vh;
  background: var(--color-bg-page, hsl(25, 5%, 97%));
  padding-bottom: var(--space-2xl, 48px);
}

/* ══ 搜索头部 ══ */
.search-header {
  position: sticky;
  top: 0;
  z-index: var(--z-sticky, 100);
  background: var(--color-bg-base, #FFFFFF);
  padding: var(--space-sm, 8px) 0;
  box-shadow: var(--shadow-sm, 0 1px 2px rgba(30,28,27,0.05));
}

.search-header-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--space-md, 16px);
  display: flex;
  align-items: center;
  gap: var(--space-sm, 8px);
}

.back-btn {
  flex-shrink: 0;
  border: none;
  background: transparent;
  color: var(--color-text-secondary, hsl(25, 7%, 42%));
}

.search-input-wrap {
  flex: 1;
  max-width: 640px;
  height: 44px;
  border-radius: var(--radius-full, 9999px);
  background: var(--color-bg-page, hsl(25, 5%, 97%));
  border: 1px solid var(--color-border, hsl(25, 7%, 90%));
  display: flex;
  align-items: center;
  padding: 0 var(--space-md, 16px);
  transition: border-color var(--duration-fast, 150ms) var(--ease-smooth, cubic-bezier(0.16,1,0.3,1)),
              box-shadow var(--duration-fast, 150ms) var(--ease-smooth, cubic-bezier(0.16,1,0.3,1));
}

.search-input-wrap.focused {
  border-color: var(--color-primary-500, hsl(25, 85%, 55%));
  box-shadow: 0 0 0 3px hsla(25, 85%, 55%, 0.2);
}

.search-prefix {
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
  font-size: 18px;
  flex-shrink: 0;
  margin-right: var(--space-sm, 8px);
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: var(--font-size-base, 14px);
  color: var(--color-text-primary, hsl(25, 9%, 12%));
  line-height: 1.5;
}

.search-input::placeholder {
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
}

.clear-btn {
  flex-shrink: 0;
  padding: 2px;
}

.search-submit {
  flex-shrink: 0;
  border-radius: var(--radius-full, 9999px);
  height: 36px;
  padding: 0 var(--space-lg, 24px);
}

/* ══ 筛选栏 ══ */
.filter-bar {
  background: var(--color-bg-base, #FFFFFF);
  border-bottom: 1px solid var(--color-border, hsl(25, 7%, 90%));
}

.filter-bar-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-sm, 8px) var(--space-md, 16px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md, 16px);
  flex-wrap: wrap;
}

/* ══ 结果区域 ══ */
.search-results {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-lg, 24px);
}

.result-summary {
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-secondary, hsl(25, 7%, 42%));
  margin-bottom: var(--space-md, 16px);
}

.result-summary strong {
  color: var(--color-primary-500, hsl(25, 85%, 55%));
  font-weight: 600;
}

/* ══ 商品网格 ══ */
.product-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-md, 16px);
}

@media (max-width: 1023px) {
  .product-grid { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 767px) {
  .product-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 639px) {
  .product-grid { grid-template-columns: 1fr; }
}

/* ══ 商品卡片 ══ */
.product-card {
  background: var(--color-bg-base, #FFFFFF);
  border: 1px solid var(--color-border, hsl(25, 7%, 90%));
  border-radius: var(--radius-md, 20px);
  overflow: hidden;
  cursor: pointer;
  transition: transform var(--duration-fast, 150ms) var(--ease-smooth, cubic-bezier(0.16,1,0.3,1)),
              box-shadow var(--duration-fast, 150ms) var(--ease-smooth, cubic-bezier(0.16,1,0.3,1)),
              border-color var(--duration-fast, 150ms) var(--ease-smooth, cubic-bezier(0.16,1,0.3,1));
}

.product-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-md, 0 4px 6px -1px rgba(30,28,27,0.08));
  border-color: var(--color-primary-200, hsl(25, 60%, 80%));
}

.product-card:active {
  transform: translateY(-2px);
}

.card-img-wrap {
  aspect-ratio: 1 / 1;
  overflow: hidden;
  background: var(--color-bg-page, hsl(25, 5%, 97%));
}

.card-img-wrap img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.card-info {
  padding: var(--space-sm, 8px) var(--space-md, 16px) var(--space-md, 16px);
}

.card-name {
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-primary, hsl(25, 9%, 12%));
  line-height: var(--line-height-normal, 1.5);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin: 0 0 8px;
  min-height: calc(var(--font-size-sm, 12.25px) * 1.5 * 2);
}

.card-price-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-sm, 8px);
  margin-bottom: 4px;
}

.card-price {
  font-size: var(--font-size-lg, 17.5px);
  font-weight: 600;
  color: var(--color-primary-600, hsl(25, 85%, 45%));
  line-height: var(--line-height-tight, 1.25);
}

.card-sales {
  font-size: var(--font-size-xs, 10.5px);
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
}

.card-shop {
  font-size: var(--font-size-xs, 10.5px);
  color: var(--color-text-secondary, hsl(25, 7%, 42%));
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ══ 骨架屏 ══ */
.product-card-skeleton {
  background: var(--color-bg-base, #FFFFFF);
  border: 1px solid var(--color-border, hsl(25, 7%, 90%));
  border-radius: var(--radius-md, 20px);
  overflow: hidden;
}

.skeleton-img {
  aspect-ratio: 1 / 1;
  background: var(--color-bg-page, hsl(25, 5%, 97%));
}

.skeleton-body {
  padding: var(--space-sm, 8px) var(--space-md, 16px) var(--space-md, 16px);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton-line {
  height: 12px;
  background: var(--color-bg-page, hsl(25, 5%, 97%));
  border-radius: 4px;
}

.skeleton-line.w80 { width: 80%; }
.skeleton-line.w60 { width: 60%; }
.skeleton-line.w40 { width: 40%; }

/* ══ 状态提示 ══ */
.state-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-3xl, 64px) var(--space-lg, 24px);
  text-align: center;
}

.error-icon-bg {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-full, 9999px);
  background: hsla(0, 80%, 52%, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-error, hsl(0, 80%, 52%));
  margin-bottom: var(--space-md, 16px);
}

.empty-icon {
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
  opacity: 0.5;
  margin-bottom: var(--space-md, 16px);
}

.state-title {
  font-size: var(--font-size-md, 15.75px);
  font-weight: 600;
  color: var(--color-text-primary, hsl(25, 9%, 12%));
  margin: 0 0 var(--space-sm, 8px);
}

.state-desc {
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-secondary, hsl(25, 7%, 42%));
  margin: 0 0 var(--space-lg, 24px);
}

.state-actions {
  display: flex;
  gap: var(--space-sm, 8px);
}

/* ══ 分页 ══ */
.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: var(--space-xl, 32px);
}

.end-hint {
  text-align: center;
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
  font-size: var(--font-size-xs, 10.5px);
  margin-top: var(--space-lg, 24px);
}
</style>
