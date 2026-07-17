<!--
  首页 — 商品瀑布流、分类icon区
  来源: ←搜索页/商详返回; 去向: →搜索页/商详/分类
  UI风格: browse-search
-->
<template>
  <div class="home-page">
    <!-- 吸顶导航栏 -->
    <header class="top-nav">
      <div class="nav-inner">
        <div class="nav-logo">鹊桥商城</div>
        <div class="nav-search" @click="goSearch">
          <el-icon class="search-icon"><Search /></el-icon>
          <span class="search-placeholder">搜索你想要的商品…</span>
        </div>
        <div class="nav-actions">
          <el-badge :value="cartCount" :hidden="cartCount === 0" :max="99">
            <el-button class="nav-btn" circle aria-label="购物车" @click="goCart">
              <el-icon><ShoppingCart /></el-icon>
            </el-button>
          </el-badge>
        </div>
      </div>
    </header>

    <!-- 分类导航条 -->
    <section class="category-strip">
      <div class="category-list">
        <div
          v-for="cat in categories"
          :key="cat.id"
          class="category-item"
          @click="goCategory(cat)"
        >
          <img
            :src="cat.icon || '/img/placeholder/logo.svg'"
            :alt="cat.name"
            class="category-icon"
            loading="lazy"
          />
          <span class="category-name">{{ cat.name }}</span>
        </div>
      </div>
    </section>

    <!-- 商品区域 -->
    <section class="product-section">
      <div class="section-header">
        <h2 class="section-title">为你推荐</h2>
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
          <el-button @click="router.push('/')">返回首页</el-button>
        </div>
      </div>

      <!-- 商品列表 -->
      <template v-else>
        <div v-if="productList.length === 0" class="state-box">
          <div class="state-icon">
            <el-icon :size="48"><Goods /></el-icon>
          </div>
          <h3 class="state-title">暂无商品</h3>
          <p class="state-desc">商家正在紧急上架中，敬请期待～</p>
        </div>

        <div v-else class="product-grid">
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
      </template>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Search, ShoppingCart, WarningFilled, Goods } from '@element-plus/icons-vue'
import { getProducts, getCategories } from '@/api/products'
import { useCartStore } from '@/stores/cart'

const router = useRouter()
const cartStore = useCartStore()

const categories = ref([])
const productList = ref([])
const loading = ref(true)
const error = ref(false)
const page = ref(1)
const pageSize = 20
const total = ref(0)

const cartCount = computed(() => cartStore.cartCount)

function formatSales(n) {
  if (!n) return '0'
  if (n >= 10000) return (n / 10000).toFixed(1) + '万'
  return String(n)
}

async function fetchCategories() {
  try {
    const res = await getCategories()
    if (res.data?.success && res.data.data?.tree) {
      categories.value = res.data.data.tree.filter(c => c.level === 1)
    }
  } catch {
    // 分类加载失败不阻塞主流程
  }
}

async function fetchProducts() {
  loading.value = true
  error.value = false
  try {
    const res = await getProducts({ page: page.value, pageSize })
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

function onPageChange(p) {
  page.value = p
  window.scrollTo({ top: 0, behavior: 'smooth' })
  fetchProducts()
}

function goSearch() {
  router.push({ name: 'Search', query: { keyword: '' } })
}

function goCategory(cat) {
  router.push({ name: 'Category', params: { id: cat.id } })
}

function goProduct(product) {
  router.push({ name: 'ProductDetail', params: { id: product.id } })
}

function goCart() {
  router.push({ name: 'Cart' })
}

onMounted(() => {
  fetchCategories()
  fetchProducts()
})
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  background: var(--color-bg-page, hsl(25, 5%, 97%));
  padding-bottom: var(--space-2xl, 48px);
}

/* ══ 导航栏 ══ */
.top-nav {
  position: sticky;
  top: 0;
  z-index: var(--z-sticky, 100);
  background: var(--color-bg-base, #FFFFFF);
  box-shadow: var(--shadow-sm, 0 1px 2px rgba(30,28,27,0.05));
  height: 56px;
  display: flex;
  align-items: center;
}

.nav-inner {
  display: flex;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--space-lg, 24px);
  width: 100%;
  gap: var(--space-md, 16px);
}

.nav-logo {
  font-size: var(--font-size-xl, 21px);
  font-weight: 700;
  color: var(--color-primary-500, hsl(25, 85%, 55%));
  white-space: nowrap;
  flex-shrink: 0;
}

.nav-search {
  flex: 1;
  max-width: 560px;
  height: 44px;
  border-radius: var(--radius-full, 9999px);
  background: var(--color-bg-page, hsl(25, 5%, 97%));
  border: 1px solid var(--color-border, hsl(25, 7%, 90%));
  display: flex;
  align-items: center;
  padding: 0 var(--space-md, 16px);
  cursor: pointer;
  transition: border-color var(--duration-fast, 150ms) var(--ease-smooth, cubic-bezier(0.16,1,0.3,1)),
              box-shadow var(--duration-fast, 150ms) var(--ease-smooth, cubic-bezier(0.16,1,0.3,1));
}

.nav-search:hover {
  border-color: var(--color-primary-300, hsl(25, 72%, 70%));
  box-shadow: var(--shadow-md, 0 4px 6px -1px rgba(30,28,27,0.08));
}

.search-icon {
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
  margin-right: var(--space-sm, 8px);
  font-size: 18px;
  flex-shrink: 0;
}

.search-placeholder {
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
  font-size: var(--font-size-sm, 12.25px);
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: var(--space-sm, 8px);
  flex-shrink: 0;
}

.nav-btn {
  border: 1px solid var(--color-border, hsl(25, 7%, 90%));
  color: var(--color-text-secondary, hsl(25, 7%, 42%));
  background: var(--color-bg-base, #FFFFFF);
}

.nav-btn:hover {
  color: var(--color-primary-500, hsl(25, 85%, 55%));
  border-color: var(--color-primary-300, hsl(25, 72%, 70%));
}

/* ══ 分类导航 ══ */
.category-strip {
  background: var(--color-bg-base, #FFFFFF);
  padding: var(--space-md, 16px) 0;
  border-bottom: 1px solid var(--color-border, hsl(25, 7%, 90%));
}

.category-list {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--space-lg, 24px);
  display: flex;
  justify-content: space-around;
  gap: var(--space-sm, 8px);
  flex-wrap: wrap;
}

.category-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: var(--space-xs, 4px);
  border-radius: var(--radius-sm, 10px);
  transition: background var(--duration-fast, 150ms) var(--ease-smooth, cubic-bezier(0.16,1,0.3,1));
  min-width: 64px;
}

.category-item:hover {
  background: var(--color-primary-50, hsl(25, 26%, 95%));
}

.category-icon {
  width: 36px;
  height: 36px;
  object-fit: contain;
  border-radius: var(--radius-sm, 10px);
}

.category-name {
  font-size: var(--font-size-xs, 10.5px);
  color: var(--color-text-secondary, hsl(25, 7%, 42%));
  line-height: var(--line-height-tight, 1.25);
  text-align: center;
}

/* ══ 商品区域 ══ */
.product-section {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-lg, 24px);
}

.section-header {
  margin-bottom: var(--space-md, 16px);
}

.section-title {
  font-size: var(--font-size-lg, 17.5px);
  font-weight: 600;
  color: var(--color-text-primary, hsl(25, 9%, 12%));
  margin: 0;
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

.state-icon {
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
  opacity: 0.5;
  margin-bottom: var(--space-md, 16px);
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
</style>
