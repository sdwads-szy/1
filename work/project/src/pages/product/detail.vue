<!--
  商品详情页 — 主图轮播、SKU选择器、店铺卡片、加购
  来源: ←首页/搜索/分类; 去向: →购物车(加购成功)/结算
  UI风格: browse-search
-->
<template>
  <div class="detail-page">
    <!-- 导航栏 -->
    <header class="detail-header">
      <div class="detail-header-inner">
        <!-- 来源: Home / Search / Category -->
        <el-button class="back-btn" :icon="ArrowLeft" circle @click="router.back()" />
        <span class="header-title">商品详情</span>
        <div class="header-actions">
          <el-badge :value="cartCount" :hidden="cartCount === 0" :max="99">
            <el-button class="nav-btn" circle @click="goCart">
              <el-icon><ShoppingCart /></el-icon>
            </el-button>
          </el-badge>
        </div>
      </div>
    </header>

    <!-- 加载态 -->
    <div v-if="loading" class="detail-loading">
      <div class="skeleton-gallery"></div>
      <div class="skeleton-body-detail">
        <div class="skeleton-line w90"></div>
        <div class="skeleton-line w40"></div>
        <div class="skeleton-line w60"></div>
        <div class="skeleton-line w80"></div>
      </div>
    </div>

    <!-- 错误态 -->
    <div v-else-if="error" class="state-box">
      <div class="state-icon error-icon-bg">
        <el-icon :size="28"><WarningFilled /></el-icon>
      </div>
      <h3 class="state-title">{{ errorMsg }}</h3>
      <p class="state-desc">商品可能已下架或不存在</p>
      <el-button type="primary" @click="router.push({name:'Home'})">返回首页</el-button>
    </div>

    <!-- 商品内容 -->
    <template v-else>
      <!-- 图片轮播 -->
      <section class="gallery-section">
        <div class="gallery-main">
          <img
            :src="currentImage"
            :alt="spu.name"
            class="gallery-image"
          />
        </div>
        <div v-if="imageList.length > 1" class="gallery-thumbs">
          <div
            v-for="(img, idx) in imageList"
            :key="idx"
            class="thumb-item"
            :class="{ active: currentImageIndex === idx }"
            @click="currentImageIndex = idx"
          >
            <img :src="img" :alt="'图片' + (idx + 1)" loading="lazy" />
          </div>
        </div>
      </section>

      <!-- 价格与名称 -->
      <section class="info-section">
        <div class="price-area">
          <span class="current-price">&yen;{{ displayPrice }}</span>
          <span v-if="spu.sales" class="sales-info">已售 {{ formatSales(spu.sales) }}</span>
        </div>
        <h1 class="product-name">{{ spu.name }}</h1>
      </section>

      <!-- SKU 选择器 -->
      <section class="sku-section">
        <h3 class="section-label">规格</h3>
        <div class="sku-list">
          <button
            v-for="sku in skuList"
            :key="sku.id"
            class="sku-btn"
            :class="{
              active: selectedSku?.id === sku.id,
              disabled: sku.stock === 0
            }"
            :disabled="sku.stock === 0"
            @click="selectSku(sku)"
          >
            {{ sku.specName }}
          </button>
        </div>
        <p v-if="selectedSku" class="stock-hint">
          库存 {{ selectedSku.stock }} 件
        </p>
      </section>

      <!-- 数量 -->
      <section class="quantity-section">
        <h3 class="section-label">数量</h3>
        <el-input-number
          v-model="quantity"
          :min="1"
          :max="selectedSku ? selectedSku.stock : 1"
          :disabled="!selectedSku"
          size="default"
        />
      </section>

      <!-- 店铺卡片 -->
      <section v-if="shop" class="shop-section">
        <div class="shop-card">
          <img
            :src="shop.logo || '/img/placeholder/logo.svg'"
            :alt="shop.name"
            class="shop-logo"
          />
          <div class="shop-info">
            <p class="shop-name">{{ shop.name }}</p>
            <el-tag
              :type="shop.status === 'open' ? 'success' : 'warning'"
              size="small"
              effect="plain"
            >
              {{ shop.status === 'open' ? '营业中' : shop.status === 'closed' ? '已打烊' : '已冻结' }}
            </el-tag>
          </div>
        </div>
      </section>

      <!-- 商品描述 -->
      <section v-if="spu.description" class="desc-section">
        <h3 class="section-label">商品详情</h3>
        <div class="desc-content" v-html="spu.description"></div>
      </section>

      <!-- 底部操作栏 -->
      <div class="bottom-bar">
        <div class="bottom-bar-inner">
          <el-button class="cart-btn" :icon="ShoppingCart" @click="goCart">
            购物车
            <el-badge v-if="cartCount" :value="cartCount" class="cart-badge-inner" />
          </el-button>
          <el-button
            type="primary"
            class="add-cart-btn"
            :disabled="!selectedSku || addingToCart"
            :loading="addingToCart"
            @click="handleAddToCart"
          >
            加入购物车
          </el-button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, ShoppingCart, WarningFilled } from '@element-plus/icons-vue'
import { getProductDetail } from '@/api/products'
import { useCartStore } from '@/stores/cart'

const router = useRouter()
const route = useRoute()
const cartStore = useCartStore()

const productId = Number(route.params.id)

const spu = ref({})
const skuList = ref([])
const imageList = ref([])
const shop = ref(null)
const selectedSku = ref(null)
const quantity = ref(1)
const currentImageIndex = ref(0)
const loading = ref(true)
const error = ref(false)
const errorMsg = ref('商品不存在或已下架')
const addingToCart = ref(false)

const cartCount = computed(() => cartStore.cartCount)

const currentImage = computed(() => {
  if (selectedSku.value?.image) return selectedSku.value.image
  if (imageList.value.length > 0) return imageList.value[currentImageIndex.value]
  return spu.value.defaultImage || '/img/placeholder/product.svg'
})

const displayPrice = computed(() => {
  if (selectedSku.value) return selectedSku.value.price
  if (skuList.value.length > 0) {
    const prices = skuList.value.map(s => parseFloat(s.price))
    const min = Math.min(...prices)
    const max = Math.max(...prices)
    return min === max ? min.toFixed(2) : `${min.toFixed(2)} - ${max.toFixed(2)}`
  }
  return '0.00'
})

function formatSales(n) {
  if (!n) return '0'
  if (n >= 10000) return (n / 10000).toFixed(1) + '万'
  return String(n)
}

function selectSku(sku) {
  if (sku.stock === 0) return
  selectedSku.value = sku
  if (quantity.value > sku.stock) {
    quantity.value = sku.stock
  }
}

async function fetchDetail() {
  loading.value = true
  error.value = false
  try {
    const res = await getProductDetail({ id: productId })
    if (res.data?.success) {
      const data = res.data.data
      spu.value = data.spu || {}
      skuList.value = data.skus || []
      imageList.value = data.images || []
      shop.value = data.shop || null

      // 自动选中第一个有库存的 SKU
      const available = skuList.value.find(s => s.stock > 0)
      if (available) {
        selectedSku.value = available
      }
    } else {
      error.value = true
      errorMsg.value = '商品不存在或已下架'
    }
  } catch {
    error.value = true
    errorMsg.value = '商品加载失败'
  } finally {
    loading.value = false
  }
}

async function handleAddToCart() {
  if (!selectedSku.value) {
    ElMessage.warning('请选择商品规格')
    return
  }
  addingToCart.value = true
  try {
    await cartStore.addToCart(selectedSku.value.id, quantity.value, spu.value.shopId)
    ElMessage.success('已加入购物车')
    // 引导进入购物车
    setTimeout(() => {
      router.push({ name: 'Cart' })
    }, 800)
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || '加入购物车失败')
  } finally {
    addingToCart.value = false
  }
}

function goCart() {
  router.push({ name: 'Cart' })
}

function goCheckout() {
  if (!selectedSku.value) return
  router.push({ name: 'Checkout', query: { skuId: selectedSku.value.id, quantity: quantity.value } })
}

onMounted(() => {
  fetchDetail()
})
</script>

<style scoped>
.detail-page {
  min-height: 100vh;
  background: var(--color-bg-page, hsl(25, 5%, 97%));
  padding-bottom: 80px;
}

/* ══ 导航栏 ══ */
.detail-header {
  position: sticky;
  top: 0;
  z-index: var(--z-sticky, 100);
  background: var(--color-bg-base, #FFFFFF);
  box-shadow: var(--shadow-sm, 0 1px 2px rgba(30,28,27,0.05));
}

.detail-header-inner {
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

.header-title {
  flex: 1;
  font-size: var(--font-size-md, 15.75px);
  font-weight: 600;
  color: var(--color-text-primary, hsl(25, 9%, 12%));
}

.header-actions {
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

/* ══ 加载骨架 ══ */
.detail-loading {
  padding: var(--space-md, 16px);
}

.skeleton-gallery {
  width: 100%;
  aspect-ratio: 1 / 1;
  background: var(--color-bg-page, hsl(25, 5%, 97%));
  border-radius: var(--radius-md, 20px);
  margin-bottom: var(--space-md, 16px);
}

.skeleton-body-detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: var(--space-md, 16px);
  background: var(--color-bg-base, #FFFFFF);
  border-radius: var(--radius-md, 20px);
}

.skeleton-line {
  height: 16px;
  background: var(--color-bg-page, hsl(25, 5%, 97%));
  border-radius: 4px;
}

.skeleton-line.w90 { width: 90%; }
.skeleton-line.w80 { width: 80%; }
.skeleton-line.w60 { width: 60%; }
.skeleton-line.w40 { width: 40%; }

/* ══ 错误态 ══ */
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

/* ══ 图片画廊 ══ */
.gallery-section {
  background: var(--color-bg-base, #FFFFFF);
}

.gallery-main {
  width: 100%;
  aspect-ratio: 1 / 1;
  overflow: hidden;
  background: var(--color-bg-page, hsl(25, 5%, 97%));
}

.gallery-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.gallery-thumbs {
  display: flex;
  gap: var(--space-sm, 8px);
  padding: var(--space-sm, 8px) var(--space-md, 16px);
  overflow-x: auto;
}

.thumb-item {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-sm, 10px);
  overflow: hidden;
  border: 2px solid transparent;
  cursor: pointer;
  flex-shrink: 0;
  transition: border-color var(--duration-fast, 150ms);
}

.thumb-item.active {
  border-color: var(--color-primary-500, hsl(25, 85%, 55%));
}

.thumb-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* ══ 价格与名称 ══ */
.info-section {
  background: var(--color-bg-base, #FFFFFF);
  padding: var(--space-md, 16px);
  margin-top: var(--space-sm, 8px);
}

.price-area {
  display: flex;
  align-items: baseline;
  gap: var(--space-sm, 8px);
  margin-bottom: var(--space-sm, 8px);
}

.current-price {
  font-size: var(--font-size-2xl, 28px);
  font-weight: 700;
  color: var(--color-primary-600, hsl(25, 85%, 45%));
  line-height: var(--line-height-tight, 1.25);
}

.sales-info {
  font-size: var(--font-size-xs, 10.5px);
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
}

.product-name {
  font-size: var(--font-size-md, 15.75px);
  font-weight: 500;
  color: var(--color-text-primary, hsl(25, 9%, 12%));
  line-height: var(--line-height-normal, 1.5);
  margin: 0;
}

/* ══ SKU 选择器 ══ */
.sku-section {
  background: var(--color-bg-base, #FFFFFF);
  padding: var(--space-md, 16px);
  margin-top: var(--space-sm, 8px);
}

.section-label {
  font-size: var(--font-size-sm, 12.25px);
  font-weight: 600;
  color: var(--color-text-secondary, hsl(25, 7%, 42%));
  margin: 0 0 var(--space-sm, 8px);
}

.sku-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm, 8px);
}

.sku-btn {
  padding: 8px 18px;
  border: 1px solid var(--color-border, hsl(25, 7%, 90%));
  border-radius: var(--radius-full, 9999px);
  background: var(--color-bg-base, #FFFFFF);
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-primary, hsl(25, 9%, 12%));
  cursor: pointer;
  transition: all var(--duration-fast, 150ms) var(--ease-smooth, cubic-bezier(0.16,1,0.3,1));
  outline: none;
}

.sku-btn:hover:not(.disabled):not(.active) {
  border-color: var(--color-primary-300, hsl(25, 72%, 70%));
  color: var(--color-primary-500, hsl(25, 85%, 55%));
}

.sku-btn.active {
  background: var(--color-primary-500, hsl(25, 85%, 55%));
  color: #FFFFFF;
  border-color: var(--color-primary-500, hsl(25, 85%, 55%));
}

.sku-btn.disabled {
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
  cursor: not-allowed;
  text-decoration: line-through;
}

.stock-hint {
  font-size: var(--font-size-xs, 10.5px);
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
  margin: var(--space-sm, 8px) 0 0;
}

/* ══ 数量 ══ */
.quantity-section {
  background: var(--color-bg-base, #FFFFFF);
  padding: var(--space-md, 16px);
  margin-top: var(--space-sm, 8px);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* ══ 店铺卡片 ══ */
.shop-section {
  background: var(--color-bg-base, #FFFFFF);
  padding: var(--space-md, 16px);
  margin-top: var(--space-sm, 8px);
}

.shop-card {
  display: flex;
  align-items: center;
  gap: var(--space-md, 16px);
}

.shop-logo {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-full, 9999px);
  object-fit: cover;
  border: 1px solid var(--color-border, hsl(25, 7%, 90%));
}

.shop-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.shop-name {
  font-size: var(--font-size-base, 14px);
  font-weight: 500;
  color: var(--color-text-primary, hsl(25, 9%, 12%));
  margin: 0;
}

/* ══ 商品描述 ══ */
.desc-section {
  background: var(--color-bg-base, #FFFFFF);
  padding: var(--space-md, 16px);
  margin-top: var(--space-sm, 8px);
}

.desc-content {
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-secondary, hsl(25, 7%, 42%));
  line-height: var(--line-height-relaxed, 1.75);
}

.desc-content :deep(img) {
  max-width: 100%;
  border-radius: var(--radius-sm, 10px);
}

/* ══ 底部操作栏 ══ */
.bottom-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: var(--z-sticky, 100);
  background: var(--color-bg-base, #FFFFFF);
  box-shadow: 0 -2px 8px rgba(30,28,27,0.06);
  padding: var(--space-sm, 8px) var(--space-md, 16px);
  padding-bottom: max(var(--space-sm, 8px), env(safe-area-inset-bottom));
}

.bottom-bar-inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  gap: var(--space-sm, 8px);
}

.cart-btn {
  flex-shrink: 0;
  border: 1px solid var(--color-border, hsl(25, 7%, 90%));
  border-radius: var(--radius-md, 20px);
  padding: 8px 16px;
  height: 44px;
}

.cart-badge-inner {
  margin-left: 4px;
}

.add-cart-btn {
  flex: 1;
  height: 44px;
  border-radius: var(--radius-md, 20px);
  font-size: var(--font-size-md, 15.75px);
  font-weight: 600;
}
</style>
