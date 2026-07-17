<!--
  分类浏览页 — 按类目筛选商品、排序、分页
  来源: ←首页分类icon; 去向: →商详
  UI风格: browse-search
-->
<template>
  <div class="category-page">
    <!-- 头部导航 -->
    <header class="cat-header">
      <div class="cat-header-inner">
        <el-button class="back-btn" :icon="ArrowLeft" circle @click="router.back()" />
        <h1 class="cat-title">{{ categoryName || '分类浏览' }}</h1>
        <div class="header-spacer"></div>
      </div>
    </header>

    <!-- 排序栏 -->
    <div class="sort-bar">
      <div class="sort-bar-inner">
        <el-radio-group
          v-model="sortBy"
          size="small"
          @change="onSortChange"
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

    <!-- 结果区域 -->
    <section class="cat-results">
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
      <div v-else-if="productList.length === 0" class="state-box">
        <el-icon class="empty-icon" :size="64"><Goods /></el-icon>
        <h3 class="state-title">该分类暂无商品</h3>
        <p class="state-desc">商家正在紧急上架中，敬请期待～</p>
        <el-button @click="router.push({name:'Home'})">浏览全部商品</el-button>
      </div>

      <!-- 商品列表 -->
      <template v-else>
        <div class="result-summary">
          共 <strong>{{ total }}</strong> 件商品
        </div>

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
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, WarningFilled, Goods } from '@element-plus/icons-vue'
import { getProducts, getCategories } from '@/api/products'

const router = useRouter()
const route = useRoute()

const categoryId = Number(route.params.id)

const categoryName = ref('')
const sortBy = ref('default')
const productList = ref([])
const loading = ref(true)
const error = ref(false)
const page = ref(1)
const pageSize = 20
const total = ref(0)

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

function findCategoryName(tree) {
  for (const cat of tree) {
    if (cat.id === categoryId) return cat.name
    if (cat.children?.length) {
      const found = findCategoryName(cat.children)
      if (found) return found
    }
  }
  return ''
}

async function fetchCategoryName() {
  try {
    const res = await getCategories()
    if (res.data?.success && res.data.data?.tree) {
      categoryName.value = findCategoryName(res.data.data.tree)
    }
  } catch {
    // 分类名加载失败不阻塞
  }
}

async function fetchProducts() {
  loading.value = true
  error.value = false
  try {
    const params = { page: page.value, pageSize, cat: categoryId }
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

function onSortChange() {
  page.value = 1
  fetchProducts()
}

function onPageChange(p) {
  page.value = p
  window.scrollTo({ top: 0, behavior: 'smooth' })
  fetchProducts()
}

function goProduct(product) {
  router.push({ name: 'ProductDetail', params: { id: product.id } })
}

onMounted(() => {
  fetchCategoryName()
  fetchProducts()
})
</script>

<style scoped>
.category-page {
  min-height: 100vh;
  background: var(--color-bg-page, hsl(25, 5%, 97%));
  padding-bottom: var(--space-2xl, 48px);
}

/* ══ 头部 ══ */
.cat-header {
  position: sticky;
  top: 0;
  z-index: var(--z-sticky, 100);
  background: var(--color-bg-base, #FFFFFF);
  box-shadow: var(--shadow-sm, 0 1px 2px rgba(30,28,27,0.05));
}

.cat-header-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--space-md, 16px);
  height: 56px;
  display: flex;
  align-items: center;
  gap: var(--space-md, 16px);
}

.back-btn {
  flex-shrink: 0;
  border: none;
  background: transparent;
  color: var(--color-text-secondary, hsl(25, 7%, 42%));
}

.cat-title {
  flex: 1;
  font-size: var(--font-size-lg, 17.5px);
  font-weight: 600;
  color: var(--color-text-primary, hsl(25, 9%, 12%));
  margin: 0;
  text-align: center;
}

.header-spacer {
  width: 40px;
  flex-shrink: 0;
}

/* ══ 排序栏 ══ */
.sort-bar {
  background: var(--color-bg-base, #FFFFFF);
  border-bottom: 1px solid var(--color-border, hsl(25, 7%, 90%));
}

.sort-bar-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-sm, 8px) var(--space-md, 16px);
  display: flex;
  align-items: center;
}

/* ══ 结果区域 ══ */
.cat-results {
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
