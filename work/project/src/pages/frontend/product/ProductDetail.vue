<template>
  <div class="page-container">
    <!-- 面包屑 -->
    <div class="breadcrumb">
      <span class="breadcrumb-link" @click="goBack">商品列表</span>
      <span class="breadcrumb-sep">/</span>
      <span class="breadcrumb-current">{{ product.title || '商品详情' }}</span>
    </div>

    <div v-loading="loading" class="detail-content" element-loading-background="rgba(255,255,255,0.7)">
      <!-- 左：图片区 -->
      <div class="gallery-section">
        <div class="main-image-wrap">
          <img
            v-if="currentImage"
            :src="currentImage"
            :alt="product.title"
            class="main-image"
          />
          <div v-else class="main-image-placeholder">
            <el-icon :size="64"><PictureFilled /></el-icon>
          </div>
        </div>
        <div v-if="imageList.length > 1" class="thumbnail-list">
          <div
            v-for="(img, idx) in imageList"
            :key="idx"
            class="thumbnail-item"
            :class="{ active: currentImage === img }"
            @click="currentImage = img"
          >
            <img :src="img" class="thumbnail-img" :alt="`缩略图 ${idx + 1}`" />
          </div>
        </div>
      </div>

      <!-- 右：信息区 -->
      <div class="info-section">
        <h1 class="product-title">{{ product.title }}</h1>

        <div class="price-area">
          <span class="current-price">¥{{ currentPrice.toFixed(2) }}</span>
          <span v-if="selectedSku" class="stock-info">
            库存：{{ selectedSku.stock }} 件
          </span>
          <span v-else-if="skuList.length === 0" class="stock-info stock-zero">
            暂无规格
          </span>
        </div>

        <div v-if="product.shopName" class="shop-info">
          <span class="shop-label">店铺：</span>
          <span class="shop-name">{{ product.shopName }}</span>
        </div>

        <!-- SKU 规格选择 -->
        <div
          v-for="(values, specName) in specMap"
          :key="specName"
          class="spec-group"
        >
          <div class="spec-label">{{ specName }}</div>
          <div class="spec-values">
            <span
              v-for="val in values"
              :key="val"
              class="spec-tag"
              :class="{
                active: selectedSpecs[specName] === val,
                disabled: isSpecDisabled(specName, val)
              }"
              @click="selectSpec(specName, val)"
            >
              {{ val }}
            </span>
          </div>
        </div>

        <!-- 数量选择 -->
        <div class="quantity-group">
          <span class="quantity-label">数量</span>
          <el-input-number
            v-model="quantity"
            :min="1"
            :max="maxQuantity"
            :disabled="!selectedSku || selectedSku.stock === 0"
            size="small"
            style="width: 140px"
          />
        </div>

        <!-- 操作按钮 -->
        <div class="action-group">
          <button
            class="btn-add-cart"
            :disabled="!canAddToCart || addingToCart"
            @click="handleAddToCart"
          >
            <el-icon v-if="addingToCart" class="is-loading"><Loading /></el-icon>
            <span>{{ addingToCart ? '加入中...' : '加入购物车' }}</span>
          </button>
          <button
            v-if="addedSuccess"
            class="btn-go-cart"
            @click="goToCart"
          >
            去购物车
          </button>
        </div>

        <!-- 商品描述 -->
        <div v-if="product.description" class="desc-section">
          <div class="desc-title">商品详情</div>
          <div class="desc-content" v-html="product.description"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * ProductDetail - 买家端商品详情页
 * 功能：图片轮播、SKU规格选择、加购
 * 主题：暖橙色
 */
import { ref, reactive, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { PictureFilled, Loading } from '@element-plus/icons-vue';
import { getProductDetail } from '@/api/product';
import { addToCart } from '@/api/cart';

const route = useRoute();
const router = useRouter();

// 商品数据
const product = ref({});
const skuList = ref([]);
const loading = ref(false);

// 图片
const currentImage = ref('');
const imageList = computed(() => {
  const imgs = [];
  if (product.value.mainImage) imgs.push(product.value.mainImage);
  skuList.value.forEach((sku) => {
    if (sku.image && !imgs.includes(sku.image)) {
      imgs.push(sku.image);
    }
  });
  return imgs;
});

// 规格解析：将 SKU 的 specCombo 聚合为 { 规格名: [可选值, ...] }
const specMap = computed(() => {
  const map = {};
  skuList.value.forEach((sku) => {
    let combo;
    try {
      combo =
        typeof sku.specCombo === 'string'
          ? JSON.parse(sku.specCombo)
          : sku.specCombo;
    } catch {
      return;
    }
    if (!combo || typeof combo !== 'object') return;
    Object.keys(combo).forEach((key) => {
      if (!map[key]) map[key] = new Set();
      map[key].add(combo[key]);
    });
  });
  const result = {};
  Object.keys(map).forEach((key) => {
    result[key] = [...map[key]];
  });
  return result;
});

const selectedSpecs = reactive({});

/**
 * 初始化：每个规格维度默认选中第一个值
 */
function initSelectedSpecs() {
  const keys = Object.keys(specMap.value);
  keys.forEach((key) => {
    if (!selectedSpecs[key]) {
      selectedSpecs[key] = specMap.value[key][0];
    }
  });
}

/**
 * 当前选中 SKU — 根据 selectedSpecs 匹配
 */
const selectedSku = computed(() => {
  const specKeys = Object.keys(selectedSpecs);
  if (specKeys.length === 0) {
    return skuList.value.length > 0 ? skuList.value[0] : null;
  }

  return (
    skuList.value.find((sku) => {
      let combo;
      try {
        combo =
          typeof sku.specCombo === 'string'
            ? JSON.parse(sku.specCombo)
            : sku.specCombo;
      } catch {
        return false;
      }
      if (!combo || typeof combo !== 'object') return false;
      return specKeys.every((key) => combo[key] === selectedSpecs[key]);
    }) || null
  );
});

/**
 * 当前显示价格
 */
const currentPrice = computed(() => {
  if (selectedSku.value) {
    return parseFloat(selectedSku.value.price) || 0;
  }
  if (skuList.value.length > 0) {
    const prices = skuList.value.map((s) => parseFloat(s.price) || 0);
    return Math.min(...prices);
  }
  return 0;
});

/**
 * 规格值是否禁用：该组合对应 SKU 库存为 0 或不存在
 */
function isSpecDisabled(specName, specValue) {
  const testSpecs = { ...selectedSpecs, [specName]: specValue };
  const specKeys = Object.keys(testSpecs);

  const matchingSku = skuList.value.find((sku) => {
    let combo;
    try {
      combo =
        typeof sku.specCombo === 'string'
          ? JSON.parse(sku.specCombo)
          : sku.specCombo;
    } catch {
      return false;
    }
    if (!combo || typeof combo !== 'object') return false;
    return specKeys.every((key) => combo[key] === testSpecs[key]);
  });

  if (!matchingSku) return true;
  return matchingSku.stock === 0;
}

/**
 * 选择规格值
 */
function selectSpec(specName, value) {
  if (isSpecDisabled(specName, value)) return;
  selectedSpecs[specName] = value;

  // 切换 SKU 时同步更新主图
  if (selectedSku.value && selectedSku.value.image) {
    currentImage.value = selectedSku.value.image;
  }

  // 重置数量
  if (quantity.value > (selectedSku.value?.stock || 1)) {
    quantity.value = selectedSku.value?.stock || 1;
  }
}

// 数量
const quantity = ref(1);
const maxQuantity = computed(() => {
  return selectedSku.value ? selectedSku.value.stock : 1;
});

// 加购状态
const addingToCart = ref(false);
const addedSuccess = ref(false);
const canAddToCart = computed(() => {
  return selectedSku.value && selectedSku.value.stock > 0;
});

/**
 * 获取商品详情
 */
async function fetchDetail() {
  loading.value = true;
  try {
    const productId = route.params.productId;
    if (!productId) {
      ElMessage.error('商品ID缺失');
      return;
    }
    const res = await getProductDetail({ id: productId });
    product.value = res.data;
    skuList.value = res.data.skus || [];

    // 设置默认主图
    if (product.value.mainImage) {
      currentImage.value = product.value.mainImage;
    } else if (skuList.value.length > 0 && skuList.value[0].image) {
      currentImage.value = skuList.value[0].image;
    }

    // 初始化规格选择
    initSelectedSpecs();
  } catch {
    ElMessage.error('获取商品详情失败');
  } finally {
    loading.value = false;
  }
}

/**
 * 加入购物车
 */
async function handleAddToCart() {
  if (!selectedSku.value) {
    ElMessage.warning('请选择商品规格');
    return;
  }
  if (selectedSku.value.stock === 0) {
    ElMessage.warning('该商品已售罄');
    return;
  }

  addingToCart.value = true;
  try {
    await addToCart({
      skuId: selectedSku.value.id,
      quantity: quantity.value
    });
    ElMessage.success('已加入购物车');
    addedSuccess.value = true;
  } catch {
    ElMessage.error('加入购物车失败，请重试');
  } finally {
    addingToCart.value = false;
  }
}

/**
 * 去购物车 — passBy: state (空数据，直接跳转)
 */
function goToCart() {
  router.push({ name: 'Cart' });
}

/**
 * 返回商品列表
 */
function goBack() {
  router.push({ name: 'ProductList' });
}

onMounted(() => {
  fetchDetail();
});
</script>

<style scoped>
/* ===== 暖橙色主题变量 ===== */
.page-container {
  --product-primary: #ff6b35;
  --product-primary-dark: #e85d2c;
  --product-primary-light: #fff3ed;
}

/* ===== 面包屑 ===== */
.breadcrumb {
  padding: 12px 0 20px;
  font-size: 0.8125rem;
  color: #9ca3af;
}

.breadcrumb-link {
  color: #6b7280;
  cursor: pointer;
  transition: color 0.15s;
}

.breadcrumb-link:hover {
  color: #ff6b35;
}

.breadcrumb-sep {
  margin: 0 8px;
  color: #d1d5db;
}

.breadcrumb-current {
  color: #1a1a2e;
  font-weight: 500;
}

/* ===== 详情区双栏布局 ===== */
.detail-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 40px;
  background: #fff;
  border-radius: 12px;
  padding: 32px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

/* ===== 图片区 ===== */
.gallery-section {
  position: sticky;
  top: 80px;
  align-self: start;
}

.main-image-wrap {
  width: 100%;
  padding-top: 100%;
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  background: #f9fafb;
  border: 1px solid #f0f0f0;
}

.main-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.main-image-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #d1d5db;
}

.thumbnail-list {
  display: flex;
  gap: 10px;
  margin-top: 12px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.thumbnail-item {
  width: 64px;
  height: 64px;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  border: 2px solid transparent;
  flex-shrink: 0;
  transition: border-color 0.15s, opacity 0.15s;
}

.thumbnail-item.active {
  border-color: #ff6b35;
}

.thumbnail-item:hover:not(.active) {
  border-color: #ffab82;
  opacity: 0.85;
}

.thumbnail-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* ===== 信息区 ===== */
.info-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.product-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1a1a2e;
  line-height: 1.35;
  margin: 0;
}

/* 价格区 */
.price-area {
  display: flex;
  align-items: baseline;
  gap: 16px;
  padding: 16px 20px;
  background: linear-gradient(135deg, #fff7f3, #ffffff);
  border-radius: 10px;
  border: 1px solid #ffedd5;
}

.current-price {
  font-size: 2rem;
  font-weight: 700;
  color: #ff6b35;
  font-family:
    -apple-system,
    BlinkMacSystemFont,
    'Segoe UI',
    sans-serif;
}

.stock-info {
  font-size: 0.8125rem;
  color: #6b7280;
}

.stock-zero {
  color: #ef4444;
}

/* 店铺 */
.shop-info {
  font-size: 0.875rem;
  color: #6b7280;
}

.shop-label {
  color: #9ca3af;
}

.shop-name {
  color: #374151;
}

/* 规格选择 */
.spec-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.spec-label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: #374151;
}

.spec-values {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.spec-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 48px;
  padding: 6px 16px;
  font-size: 0.8125rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  cursor: pointer;
  color: #374151;
  background: #fff;
  transition:
    border-color 0.15s,
    background 0.15s,
    color 0.15s;
  user-select: none;
}

.spec-tag:hover:not(.disabled):not(.active) {
  border-color: #ff6b35;
  color: #ff6b35;
}

.spec-tag.active {
  border-color: #ff6b35;
  background: #fff3ed;
  color: #ff6b35;
  font-weight: 500;
}

.spec-tag.disabled {
  border-color: #e5e7eb;
  color: #b0b7c3;
  cursor: not-allowed;
  background: #f9fafb;
  text-decoration: line-through;
}

/* 数量 */
.quantity-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.quantity-label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: #374151;
}

/* 操作按钮 */
.action-group {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 4px;
}

.btn-add-cart {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 46px;
  padding: 0 36px;
  font-size: 0.9375rem;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #ff6b35, #f97316);
  border: none;
  border-radius: 23px;
  cursor: pointer;
  transition:
    background 0.2s,
    box-shadow 0.2s,
    transform 0.15s;
  box-shadow: 0 4px 14px rgba(255, 107, 53, 0.3);
}

.btn-add-cart:hover:not(:disabled) {
  background: linear-gradient(135deg, #e85d2c, #ea580c);
  box-shadow: 0 6px 22px rgba(255, 107, 53, 0.4);
  transform: translateY(-1px);
}

.btn-add-cart:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(255, 107, 53, 0.3);
}

.btn-add-cart:disabled {
  background: #d1d5db;
  box-shadow: none;
  cursor: not-allowed;
  color: #f3f4f6;
}

.btn-go-cart {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 46px;
  padding: 0 28px;
  font-size: 0.9375rem;
  font-weight: 500;
  color: #ff6b35;
  background: #fff;
  border: 2px solid #ff6b35;
  border-radius: 23px;
  cursor: pointer;
  transition:
    background 0.2s,
    border-color 0.2s,
    color 0.2s;
}

.btn-go-cart:hover {
  background: #fff3ed;
  border-color: #e85d2c;
  color: #e85d2c;
}

/* 描述 */
.desc-section {
  margin-top: 12px;
  padding-top: 20px;
  border-top: 1px solid #f0f0f0;
}

.desc-title {
  font-size: 1rem;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 12px;
}

.desc-content {
  font-size: 0.875rem;
  color: #6b7280;
  line-height: 1.7;
}

.desc-content :deep(img) {
  max-width: 100%;
  border-radius: 8px;
}

/* ===== Element Plus 暖橙色覆盖 ===== */
:deep(.el-input-number .el-input.is-focus .el-input__wrapper) {
  box-shadow: 0 0 0 1px #ff6b35 inset;
}

:deep(.el-input-number .el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #ff6b35 inset;
}

/* ===== 响应式 ===== */
@media (max-width: 992px) {
  .detail-content {
    grid-template-columns: 1fr;
    gap: 24px;
    padding: 20px;
  }

  .gallery-section {
    position: static;
  }

  .main-image-wrap {
    padding-top: 75%;
    max-width: 500px;
    margin: 0 auto;
  }

  .thumbnail-list {
    justify-content: center;
  }

  .product-title {
    font-size: 1.25rem;
  }

  .current-price {
    font-size: 1.5rem;
  }
}

@media (max-width: 576px) {
  .detail-content {
    padding: 16px;
    gap: 16px;
  }

  .main-image-wrap {
    padding-top: 100%;
    max-width: 100%;
  }

  .action-group {
    flex-direction: column;
  }

  .btn-add-cart,
  .btn-go-cart {
    width: 100%;
  }

  .price-area {
    flex-direction: column;
    gap: 6px;
  }
}
</style>
