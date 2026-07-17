<template>
  <div class="checkout-page">
    <!-- 加载骨架屏 -->
    <template v-if="pageLoading">
      <div class="section skeleton-card">
        <div class="skeleton-line skeleton-title"></div>
        <div class="skeleton-line"></div>
        <div class="skeleton-line skeleton-short"></div>
      </div>
      <div class="section skeleton-card">
        <div class="skeleton-line skeleton-title"></div>
        <div class="skeleton-item" v-for="i in 2" :key="i">
          <div class="skeleton-img"></div>
          <div class="skeleton-text">
            <div class="skeleton-line"></div>
            <div class="skeleton-line skeleton-short"></div>
          </div>
        </div>
      </div>
    </template>

    <!-- 空购物车 -->
    <template v-else-if="checkedItems.length === 0">
      <div class="empty-state">
        <el-icon :size="64" color="var(--color-text-tertiary)"><ShoppingCart /></el-icon>
        <h2 class="empty-title">没有待结算的商品</h2>
        <p class="empty-desc">请先在购物车中勾选要购买的商品</p>
        <el-button type="primary" @click="goShopping">去逛逛</el-button>
      </div>
    </template>

    <!-- 主内容 -->
    <template v-else>
      <!-- 来源: ProductDetail -->
      <div class="checkout-back-nav">
        <el-button text @click="router.back()">← 返回商品详情</el-button>
      </div>
      <!-- 收货地址 -->
      <div class="section">
        <div class="section-header">
          <h3 class="section-title">收货地址</h3>
          <el-button type="primary" link @click="showAddressDialog = true">
            <el-icon><Plus /></el-icon>新增地址
          </el-button>
        </div>

        <template v-if="addresses.length === 0">
          <div class="address-empty">
            <p>暂无收货地址，请先添加</p>
            <el-button type="primary" @click="showAddressDialog = true">新增地址</el-button>
          </div>
        </template>

        <el-radio-group v-else v-model="selectedAddressId" class="address-list">
          <label
            v-for="addr in addresses"
            :key="addr.id"
            class="address-card"
            :class="{ 'address-card--selected': selectedAddressId === addr.id }"
          >
            <el-radio :value="addr.id" class="address-radio">
              <span class="address-contact">{{ addr.contactName }} {{ addr.phone }}</span>
            </el-radio>
            <p class="address-detail">
              {{ addr.province }}{{ addr.city }}{{ addr.district }} {{ addr.detail }}
            </p>
            <el-tag v-if="addr.isDefault" size="small" type="primary" effect="plain">默认</el-tag>
          </label>
        </el-radio-group>
      </div>

      <!-- 商品信息 -->
      <div class="section">
        <h3 class="section-title">商品信息</h3>
        <div class="item-list">
          <div v-for="item in checkedItems" :key="item.id" class="item-row">
            <img
              :src="item.image || '/img/public/placeholder/product.svg'"
              :alt="item.name"
              class="item-image"
              @error="onImageError"
            />
            <div class="item-info">
              <p class="item-name">{{ item.name || item.spuName || '商品' }}</p>
              <p v-if="item.specName" class="item-spec">{{ item.specName }}</p>
            </div>
            <div class="item-price">
              <span class="item-price-symbol">¥</span>
              <span class="item-price-value">{{ formatPrice(item.price) }}</span>
            </div>
            <span class="item-quantity">×{{ item.quantity }}</span>
          </div>
        </div>
      </div>

      <!-- 金额汇总 -->
      <div class="section summary-section">
        <div class="summary-row">
          <span class="summary-label">商品合计</span>
          <span class="summary-value">¥{{ formatPrice(checkedTotal) }}</span>
        </div>
        <div class="summary-row summary-total">
          <span class="summary-label">应付金额</span>
          <span class="summary-total-value">¥{{ formatPrice(checkedTotal) }}</span>
        </div>
      </div>

      <!-- 提交按钮 -->
      <div class="submit-bar">
        <el-button
          type="primary"
          size="large"
          :disabled="!selectedAddressId || submitting"
          :loading="submitting"
          @click="submitOrder"
          class="submit-btn"
        >
          {{ submitting ? '提交中...' : '提交订单' }}
        </el-button>
      </div>
    </template>

    <!-- 新增地址弹窗 -->
    <el-dialog
      v-model="showAddressDialog"
      title="新增收货地址"
      width="520px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form
        ref="addressFormRef"
        :model="addressForm"
        :rules="addressRules"
        label-width="80px"
        label-position="right"
      >
        <el-form-item label="收货人" prop="contactName">
          <el-input v-model="addressForm.contactName" placeholder="请输入收货人姓名" maxlength="32" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="addressForm.phone" placeholder="请输入收货人手机号" maxlength="11" />
        </el-form-item>
        <el-form-item label="所在地区" prop="region" required>
          <el-cascader
            v-model="addressForm.region"
            :options="regionOptions"
            placeholder="请选择省/市/区"
            class="region-cascader"
            clearable
          />
        </el-form-item>
        <el-form-item label="详细地址" prop="detail">
          <el-input
            v-model="addressForm.detail"
            type="textarea"
            :rows="2"
            placeholder="街道、门牌号等"
            maxlength="255"
          />
        </el-form-item>
        <el-form-item label="默认地址">
          <el-switch v-model="addressForm.isDefault" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddressDialog = false">取消</el-button>
        <el-button type="primary" :loading="addressSubmitting" @click="submitAddress">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ShoppingCart, Plus } from '@element-plus/icons-vue'
import { useCartStore } from '@/stores/cart'
import { createOrder } from '@/api/orders'
import { getAddresses, createAddress } from '@/api/user-addresses'

const router = useRouter()
const route = useRoute()

// 从 ProductDetail 立即购买传入的 query 参数
const skuId = route.query.skuId;
const checkoutQty = Number(route.query.quantity) || 1;
const cartStore = useCartStore()

// ===== 状态 =====
const pageLoading = ref(true)
const submitting = ref(false)
const addresses = ref([])
const selectedAddressId = ref(null)
const showAddressDialog = ref(false)
const addressSubmitting = ref(false)
const addressFormRef = ref(null)

const addressForm = ref({
  contactName: '',
  phone: '',
  region: [],
  detail: '',
  isDefault: false
})

// 省市区简化选项（实际项目可用完整数据）
const regionOptions = [
  {
    value: '广东省',
    label: '广东省',
    children: [
      {
        value: '深圳市',
        label: '深圳市',
        children: [
          { value: '南山区', label: '南山区' },
          { value: '福田区', label: '福田区' },
          { value: '宝安区', label: '宝安区' }
        ]
      },
      {
        value: '广州市',
        label: '广州市',
        children: [
          { value: '天河区', label: '天河区' },
          { value: '海珠区', label: '海珠区' }
        ]
      }
    ]
  },
  {
    value: '浙江省',
    label: '浙江省',
    children: [
      {
        value: '杭州市',
        label: '杭州市',
        children: [
          { value: '西湖区', label: '西湖区' },
          { value: '余杭区', label: '余杭区' }
        ]
      }
    ]
  },
  {
    value: '北京市',
    label: '北京市',
    children: [
      {
        value: '北京市',
        label: '北京市',
        children: [
          { value: '朝阳区', label: '朝阳区' },
          { value: '海淀区', label: '海淀区' }
        ]
      }
    ]
  },
  {
    value: '上海市',
    label: '上海市',
    children: [
      {
        value: '上海市',
        label: '上海市',
        children: [
          { value: '浦东新区', label: '浦东新区' },
          { value: '徐汇区', label: '徐汇区' }
        ]
      }
    ]
  }
]

const addressRules = {
  contactName: [
    { required: true, message: '请输入收货人姓名', trigger: 'blur' },
    { max: 32, message: '姓名不超过32个字符', trigger: 'blur' }
  ],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确', trigger: 'blur' }
  ],
  region: [
    { required: true, message: '请选择省/市/区', trigger: 'change' }
  ],
  detail: [
    { required: true, message: '请输入详细地址', trigger: 'blur' },
    { max: 255, message: '详细地址不超过255个字符', trigger: 'blur' }
  ]
}

// ===== 计算属性 =====
const checkedItems = computed(() => cartStore.checkedItems || [])
const checkedTotal = computed(() => cartStore.totalAmount || 0)

// ===== 方法 =====
function formatPrice(price) {
  const num = parseFloat(price)
  if (isNaN(num)) return '0.00'
  return num.toFixed(2)
}

function onImageError(e) {
  e.target.src = '/img/public/placeholder/product.svg'
}

function goShopping() {
  router.push({ name: 'Home' })
}

async function loadData() {
  pageLoading.value = true
  try {
    const [addrRes] = await Promise.all([
      getAddresses(),
      cartStore.fetchCart()
    ])
    addresses.value = addrRes.data.list || []
    // 默认选中默认地址
    const defaultAddr = addresses.value.find(a => a.isDefault)
    if (defaultAddr) {
      selectedAddressId.value = defaultAddr.id
    } else if (addresses.value.length > 0) {
      selectedAddressId.value = addresses.value[0].id
    }
  } catch (e) {
    ElMessage.error('加载数据失败，请刷新重试')
  } finally {
    pageLoading.value = false
  }
}

async function submitOrder() {
  if (!selectedAddressId.value) {
    ElMessage.warning('请选择收货地址')
    return
  }
  if (checkedItems.value.length === 0) {
    ElMessage.warning('购物车已勾选商品为空')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确认提交订单？应付金额 ¥${formatPrice(checkedTotal.value)}`,
      '确认下单',
      { confirmButtonText: '确认下单', cancelButtonText: '再想想', type: 'info' }
    )
  } catch {
    return
  }

  submitting.value = true
  try {
    const cartItemIds = checkedItems.value.map(item => item.id)
    const res = await createOrder({
      addressId: selectedAddressId.value,
      cartItemIds
    })

    if (res.data && res.data.orderNo) {
      ElMessage.success('下单成功')
      // nav_checkout_pay: submit_success → router.push with query
      router.push({ name: 'CheckoutPay', query: { orderNo: res.data.orderNo } })
    }
  } catch (e) {
    const msg = e?.response?.data?.message || e?.message || '下单失败，请重试'
    if (e?.response?.status === 422) {
      if (msg.includes('库存不足')) {
        ElMessage.warning(msg)
      } else if (msg.includes('暂停营业')) {
        ElMessage.warning(msg)
      } else {
        ElMessage.warning(msg)
      }
    } else if (e?.response?.status === 404) {
      ElMessage.error('收货地址不存在，请重新选择')
    } else {
      ElMessage.error(msg)
    }
  } finally {
    submitting.value = false
  }
}

async function submitAddress() {
  const valid = await addressFormRef.value.validate().catch(() => false)
  if (!valid) return

  addressSubmitting.value = true
  try {
    const [province, city, district] = addressForm.value.region
    const res = await createAddress({
      province,
      city,
      district,
      detail: addressForm.value.detail,
      phone: addressForm.value.phone,
      contactName: addressForm.value.contactName,
      isDefault: addressForm.value.isDefault
    })
    ElMessage.success('地址添加成功')
    showAddressDialog.value = false
    // 刷新地址列表
    const addrRes = await getAddresses()
    addresses.value = addrRes.data.list || []
    // 选中新地址
    if (res.data && res.data.addressId) {
      selectedAddressId.value = res.data.addressId
    }
    // 重置表单
    addressForm.value = { contactName: '', phone: '', region: [], detail: '', isDefault: false }
  } catch (e) {
    const msg = e?.response?.data?.message || '地址添加失败'
    ElMessage.error(msg)
  } finally {
    addressSubmitting.value = false
  }
}

// ===== 生命周期 =====
onMounted(() => {
  loadData()
})
</script>

<style scoped>
.checkout-page {
  max-width: 800px;
  margin: 0 auto;
  padding: var(--space-lg);
  min-height: calc(100vh - 56px);
}

/* 区块 */
.section {
  background: var(--color-bg-base);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  margin-bottom: var(--space-md);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-md);
}

.section-title {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.section-header .section-title {
  margin-bottom: 0;
}

/* 地址卡片 */
.address-empty {
  text-align: center;
  padding: var(--space-xl) 0;
  color: var(--color-text-tertiary);
}

.address-empty p {
  margin: 0 0 var(--space-md);
  font-size: var(--font-size-base);
}

.address-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  width: 100%;
}

.address-card {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: var(--space-sm);
  padding: var(--space-md);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-smooth),
              background-color var(--duration-fast) var(--ease-smooth);
}

.address-card:hover {
  border-color: var(--color-primary-300);
  background: var(--color-primary-50);
}

.address-card--selected {
  border-color: var(--color-primary-500);
  background: var(--color-primary-50);
}

.address-radio {
  width: 100%;
}

.address-contact {
  font-weight: 600;
  color: var(--color-text-primary);
}

.address-detail {
  margin: 4px 0 0 24px;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: var(--line-height-normal);
  width: 100%;
}

/* 商品列表 */
.item-list {
  display: flex;
  flex-direction: column;
}

.item-row {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md) 0;
  border-bottom: 1px solid var(--color-border);
}

.item-row:last-child {
  border-bottom: none;
}

.item-image {
  width: 64px;
  height: 64px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  background: var(--color-bg-page);
  flex-shrink: 0;
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-name {
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  line-height: var(--line-height-normal);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin: 0;
}

.item-spec {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 2px 0 0;
}

.item-price {
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
}

.item-price-symbol {
  font-size: var(--font-size-sm);
  color: var(--color-error);
}

.item-price-value {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-error);
}

.item-quantity {
  flex-shrink: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-variant-numeric: tabular-nums;
  min-width: 40px;
  text-align: right;
}

/* 金额汇总 */
.summary-section {
  text-align: right;
}

.summary-row {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: var(--space-lg);
  padding: 6px 0;
}

.summary-label {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
}

.summary-value {
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  font-variant-numeric: tabular-nums;
  min-width: 100px;
  text-align: right;
}

.summary-total {
  border-top: 1px solid var(--color-border);
  padding-top: var(--space-sm);
  margin-top: var(--space-sm);
}

.summary-total .summary-label {
  font-weight: 600;
  color: var(--color-text-primary);
}

.summary-total-value {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--color-error);
  font-variant-numeric: tabular-nums;
  min-width: 100px;
  text-align: right;
}

/* 提交按钮 */
.submit-bar {
  position: sticky;
  bottom: 0;
  background: var(--color-bg-base);
  border-top: 1px solid var(--color-border);
  padding: var(--space-md) var(--space-lg);
  margin: 0 calc(-1 * var(--space-lg));
  text-align: right;
  border-radius: 0 0 var(--radius-md) var(--radius-md);
}

.submit-btn {
  min-width: 160px;
  height: 44px;
  font-size: var(--font-size-md);
  border-radius: var(--radius-md);
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: var(--space-3xl) var(--space-lg);
}

.empty-title {
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
  margin: var(--space-lg) 0 var(--space-sm);
  font-weight: 600;
}

.empty-desc {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-xl);
}

/* 骨架屏 */
.skeleton-card {
  padding: var(--space-lg);
}

.skeleton-line {
  height: 14px;
  background: var(--color-bg-page);
  border-radius: 4px;
  margin-bottom: var(--space-sm);
  animation: skeleton-shimmer 1.8s infinite;
  background: linear-gradient(
    90deg,
    var(--color-bg-page) 25%,
    var(--color-primary-50) 50%,
    var(--color-bg-page) 75%
  );
  background-size: 200% 100%;
}

.skeleton-title {
  width: 30%;
  height: 18px;
}

.skeleton-short {
  width: 60%;
}

.skeleton-item {
  display: flex;
  gap: var(--space-md);
  padding: var(--space-md) 0;
}

.skeleton-img {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-sm);
  background: var(--color-bg-page);
  flex-shrink: 0;
  animation: skeleton-shimmer 1.8s infinite;
  background: linear-gradient(
    90deg,
    var(--color-bg-page) 25%,
    var(--color-primary-50) 50%,
    var(--color-bg-page) 75%
  );
  background-size: 200% 100%;
}

.skeleton-text {
  flex: 1;
  padding-top: 8px;
}

@keyframes skeleton-shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

/* 级联选择器 */
.region-cascader {
  width: 100%;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .checkout-page {
    padding: var(--space-sm);
  }

  .section {
    padding: var(--space-md);
  }

  .submit-bar {
    margin: 0 calc(-1 * var(--space-md));
    padding: var(--space-md);
  }

  .submit-btn {
    width: 100%;
  }

  .item-row {
    flex-wrap: wrap;
  }

  .item-price {
    margin-left: auto;
  }
}
</style>
