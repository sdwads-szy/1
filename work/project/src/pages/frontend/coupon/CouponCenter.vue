<!--
  CouponCenter.vue — 买家端领券中心
  暖橙色主题，双Tab：可领券 / 我的券
  状态覆盖：loading / empty / error / 未登录 / 已领取 / 已过期
-->
<template>
  <div class="coupon-center">
    <!-- 页面标题区 -->
    <div class="coupon-hero">
      <div class="hero-content">
        <h1 class="hero-title">领券中心</h1>
        <p class="hero-subtitle">精选优惠券，下单更划算</p>
      </div>
    </div>

    <!-- Tab 切换 -->
    <div class="coupon-tabs">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'available' }"
        @click="activeTab = 'available'"
      >
        可领券
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'my' }"
        @click="handleTabChange('my')"
      >
        我的券
        <span v-if="isLoggedIn && myCoupons.length > 0" class="tab-count">
          {{ myCoupons.length }}
        </span>
      </button>
    </div>

    <!-- ==================== 可领券 Tab ==================== -->
    <div v-show="activeTab === 'available'" class="tab-content">
      <!-- 加载态 -->
      <div v-if="loading.available" class="state-box">
        <span class="state-icon spinner"></span>
        <p class="state-text">加载优惠券中...</p>
      </div>

      <!-- 错误态 -->
      <div v-else-if="error.available" class="state-box">
        <span class="state-icon">⚠</span>
        <p class="state-text">{{ error.available }}</p>
        <el-button type="primary" size="small" @click="loadAvailableCoupons">
          重新加载
        </el-button>
      </div>

      <!-- 空态 -->
      <div v-else-if="availableCoupons.length === 0" class="state-box">
        <span class="state-icon">🎫</span>
        <p class="state-text">暂无可用优惠券</p>
        <p class="state-hint">商家正在准备新的优惠活动，敬请期待</p>
        <el-button type="primary" size="small" @click="router.push('/')">
          去逛逛
        </el-button>
      </div>

      <!-- 券卡片网格 -->
      <div v-else class="coupon-grid">
        <div
          v-for="coupon in availableCoupons"
          :key="coupon.id"
          class="coupon-card"
          :class="{ 'is-claimed': claimedIds.has(coupon.id) }"
        >
          <!-- 金额区 -->
          <div class="card-amount">
            <span class="card-currency">¥</span>
            <span class="card-value">{{ formatAmountInt(coupon.amount) }}</span>
          </div>

          <!-- 分割线 -->
          <div class="card-divider"></div>

          <!-- 信息区 -->
          <div class="card-body">
            <h3 class="card-title">{{ coupon.title }}</h3>
            <p class="card-condition">
              {{ formatCondition(coupon.min_order) }}
            </p>
            <p class="card-validity">
              {{ formatDate(coupon.valid_from) }} ~ {{ formatDate(coupon.valid_to) }}
            </p>
          </div>

          <!-- 操作区 -->
          <div class="card-action">
            <el-button
              v-if="claimedIds.has(coupon.id)"
              disabled
              size="small"
              class="btn-claimed"
            >
              已领取
            </el-button>
            <el-button
              v-else
              type="primary"
              size="small"
              :loading="loading.claim[coupon.id]"
              @click="handleClaim(coupon)"
              class="btn-claim"
            >
              立即领取
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- ==================== 我的券 Tab ==================== -->
    <div v-show="activeTab === 'my'" class="tab-content">
      <!-- 未登录 -->
      <div v-if="!isLoggedIn" class="state-box">
        <span class="state-icon">🔒</span>
        <p class="state-text">登录后查看我的优惠券</p>
        <el-button
          type="primary"
          size="small"
          @click="router.push({ path: '/login', query: { redirect: '/coupons' } })"
        >
          去登录
        </el-button>
      </div>

      <!-- 加载态 -->
      <div v-else-if="loading.my" class="state-box">
        <span class="state-icon spinner"></span>
        <p class="state-text">加载我的优惠券...</p>
      </div>

      <!-- 错误态 -->
      <div v-else-if="error.my" class="state-box">
        <span class="state-icon">⚠</span>
        <p class="state-text">{{ error.my }}</p>
        <el-button type="primary" size="small" @click="loadMyCoupons">
          重新加载
        </el-button>
      </div>

      <!-- 空态 -->
      <div v-else-if="myCoupons.length === 0" class="state-box">
        <span class="state-icon">🎫</span>
        <p class="state-text">还没有领取优惠券</p>
        <el-button
          type="primary"
          size="small"
          @click="activeTab = 'available'"
        >
          去领券
        </el-button>
      </div>

      <!-- 我的券列表 -->
      <div v-else class="my-coupon-list">
        <div
          v-for="item in sortedMyCoupons"
          :key="item.id"
          class="my-coupon-card"
          :class="item.status"
        >
          <!-- 金额 -->
          <div class="my-card-amount">
            <span class="my-currency">¥</span>
            <span class="my-value">{{ formatAmountInt(item.amount) }}</span>
          </div>

          <div class="my-card-divider"></div>

          <!-- 信息 -->
          <div class="my-card-body">
            <h4 class="my-card-title">{{ item.title }}</h4>
            <p class="my-card-condition">
              {{ formatCondition(item.min_order) }}
            </p>
          </div>

          <!-- 状态标签 -->
          <div class="my-card-status">
            <el-tag
              v-if="item.status === 'available'"
              type="success"
              size="small"
              effect="plain"
            >
              可使用
            </el-tag>
            <el-tag
              v-else-if="item.status === 'used'"
              type="info"
              size="small"
              effect="plain"
            >
              已使用
            </el-tag>
            <el-tag
              v-else
              type="info"
              size="small"
              effect="plain"
            >
              已过期
            </el-tag>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * CouponCenter — 买家领券中心
 *
 * 功能:
 *   - 可领券 Tab: 展示所有 active 状态优惠券，支持一键领取
 *   - 我的券 Tab: 展示当前用户已领券（available/used/expired）
 *
 * 状态覆盖:
 *   loading | error | empty | 未登录 | 已领取 | 已过期
 */
import { ref, computed, onMounted, reactive, watch } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { getAvailableCoupons, claimCoupon, getMyCoupons } from '@/api/coupon';
import { useUserStore } from '@/stores/user';

const router = useRouter();
const userStore = useUserStore();

// ── 基础状态 ──────────────────────────────────────────────
const activeTab = ref('available');
const availableCoupons = ref([]);
const myCoupons = ref([]);
const claimedIds = reactive(new Set());

const loading = reactive({
  available: false,
  my: false,
  claim: {},
});

const error = reactive({
  available: '',
  my: '',
});

const isLoggedIn = computed(() => !!userStore.token);

// ── 计算属性 ──────────────────────────────────────────────

/** 我的券排序：可使用 → 已使用 → 已过期 */
const sortedMyCoupons = computed(() => {
  const order = { available: 0, used: 1, expired: 2 };
  return [...myCoupons.value].sort(
    (a, b) => (order[a.status] ?? 3) - (order[b.status] ?? 3),
  );
});

// ── 数据加载 ──────────────────────────────────────────────

async function loadAvailableCoupons() {
  loading.available = true;
  error.available = '';
  try {
    const res = await getAvailableCoupons();
    availableCoupons.value = res.data?.list ?? [];
  } catch (err) {
    error.available = err?.response?.data?.message || err?.message || '加载失败，请重试';
  } finally {
    loading.available = false;
  }
}

async function loadMyCoupons() {
  if (!isLoggedIn.value) return;
  loading.my = true;
  error.my = '';
  try {
    const res = await getMyCoupons();
    const list = res.data?.list ?? [];
    myCoupons.value = list;
    // 同步 claimedIds：标记已领取的券
    list.forEach((item) => {
      const cid = item.coupon_id;
      if (cid) claimedIds.add(cid);
    });
  } catch (err) {
    error.my = err?.response?.data?.message || err?.message || '加载失败，请重试';
  } finally {
    loading.my = false;
  }
}

// ── 操作 ──────────────────────────────────────────────────

async function handleClaim(coupon) {
  if (!isLoggedIn.value) {
    router.push({ path: '/login', query: { redirect: '/coupons' } });
    return;
  }

  loading.claim = { ...loading.claim, [coupon.id]: true };
  try {
    await claimCoupon(coupon.id);
    claimedIds.add(coupon.id);
    ElMessage.success('领取成功！');
    // 刷新我的券列表（后台静默更新）
    loadMyCoupons();
  } catch (err) {
    const status = err?.response?.status;
    const msg = err?.response?.data?.message || err?.message || '领取失败';

    if (status === 409) {
      // 重复领取
      claimedIds.add(coupon.id);
      ElMessage.info('该优惠券已领取');
    } else if (status === 401) {
      ElMessage.warning('请先登录');
      router.push({ path: '/login', query: { redirect: '/coupons' } });
    } else {
      ElMessage.error(msg);
    }
  } finally {
    loading.claim = { ...loading.claim, [coupon.id]: false };
  }
}

function handleTabChange(tab) {
  activeTab.value = tab;
  if (tab === 'my' && isLoggedIn.value && myCoupons.value.length === 0 && !loading.my) {
    loadMyCoupons();
  }
}

// ── 格式化工具 ────────────────────────────────────────────

/**
 * 金额整数部分（券面值大字展示）
 * DECIMAL 字段后端返回字符串，parseFloat 转换
 */
function formatAmountInt(raw) {
  const n = parseFloat(raw);
  if (Number.isNaN(n)) return '0';
  return String(Math.floor(n));
}

/** 最低消费门槛文案 */
function formatCondition(raw) {
  const n = parseFloat(raw);
  if (Number.isNaN(n) || n <= 0) return '无门槛';
  return `满 ¥${n.toFixed(2)} 可用`;
}

/** 日期格式化: ISO → YYYY.MM.DD */
function formatDate(str) {
  if (!str) return '';
  const d = new Date(str);
  if (Number.isNaN(d.getTime())) return '';
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}.${m}.${day}`;
}

// ── 生命周期 ──────────────────────────────────────────────

onMounted(() => {
  loadAvailableCoupons();
});

// Tab 切换到「我的券」时如果已登录则加载
watch(activeTab, (val) => {
  if (val === 'my' && isLoggedIn.value && myCoupons.value.length === 0 && !loading.my) {
    loadMyCoupons();
  }
});
</script>

<style scoped>
/* ==================== 页面容器 ==================== */
.coupon-center {
  min-height: 100vh;
  background: #faf7f4;
  padding-bottom: var(--app-space-3xl, 40px);
}

/* ==================== Hero 标题区 ==================== */
.coupon-hero {
  background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 40%, #fed7aa 100%);
  padding: var(--app-space-3xl, 40px) var(--app-space-xl, 24px);
  text-align: center;
}

.hero-title {
  font-size: var(--app-font-3xl, 1.5rem);
  font-weight: 700;
  color: #c2410c;
  margin: 0 0 8px;
  letter-spacing: 0.02em;
}

.hero-subtitle {
  font-size: var(--app-font-base, 0.875rem);
  color: #9a3412;
  margin: 0;
  opacity: 0.75;
}

/* ==================== Tab 栏 ==================== */
.coupon-tabs {
  display: flex;
  justify-content: center;
  gap: 0;
  background: #fff;
  border-bottom: 1px solid var(--app-border-light, #e5e7eb);
  position: sticky;
  top: 56px;
  z-index: 10;
}

.tab-btn {
  position: relative;
  padding: 14px 32px;
  font-size: var(--app-font-md, 0.9375rem);
  font-weight: 500;
  color: var(--app-text-secondary, #6b7280);
  background: none;
  border: none;
  cursor: pointer;
  transition: color 0.2s var(--app-ease-standard, cubic-bezier(0.4, 0, 0.2, 1));
  outline: none;
  display: flex;
  align-items: center;
  gap: 6px;
}

.tab-btn:hover {
  color: #f97316;
}

.tab-btn.active {
  color: #f97316;
}

.tab-btn.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 32px;
  height: 3px;
  background: #f97316;
  border-radius: 2px 2px 0 0;
}

.tab-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  font-size: var(--app-font-xs, 0.75rem);
  font-weight: 600;
  color: #fff;
  background: #f97316;
  border-radius: var(--app-radius-full, 9999px);
  line-height: 1;
}

/* ==================== Tab 内容区 ==================== */
.tab-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--app-space-xl, 24px) var(--app-space-xl, 24px);
}

/* ==================== 通用状态盒子 ==================== */
.state-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 24px;
  text-align: center;
}

.state-icon {
  font-size: 48px;
  margin-bottom: 16px;
  line-height: 1;
}

.state-icon.spinner {
  display: inline-block;
  width: 40px;
  height: 40px;
  border: 3px solid #fed7aa;
  border-top-color: #f97316;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.state-text {
  font-size: var(--app-font-md, 0.9375rem);
  color: var(--app-text-regular, #374151);
  margin: 0 0 4px;
}

.state-hint {
  font-size: var(--app-font-sm, 0.8125rem);
  color: var(--app-text-secondary, #6b7280);
  margin: 0 0 20px;
}

/* ==================== 可领券网格 ==================== */
.coupon-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 20px;
}

@media (max-width: 768px) {
  .coupon-grid {
    grid-template-columns: 1fr;
  }
}

/* ==================== 券卡片 ==================== */
.coupon-card {
  background: #fff;
  border-radius: var(--app-radius-md, 12px);
  overflow: hidden;
  box-shadow: var(--app-shadow-level-1, 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04));
  transition: transform 0.25s var(--app-ease-standard, cubic-bezier(0.4, 0, 0.2, 1)),
    box-shadow 0.25s var(--app-ease-standard, cubic-bezier(0.4, 0, 0.2, 1));
  display: flex;
  flex-direction: column;
}

.coupon-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--app-shadow-level-2, 0 4px 12px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04));
}

.coupon-card.is-claimed {
  opacity: 0.7;
}

.coupon-card.is-claimed:hover {
  transform: none;
  box-shadow: var(--app-shadow-level-1, 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04));
}

/* 金额 + 信息 水平排列 */
.coupon-card .card-amount,
.coupon-card .card-body,
.coupon-card .card-divider {
  /* 占位 */
}

.coupon-card {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
}

/* 金额区 */
.card-amount {
  flex: 0 0 130px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 8px;
  background: linear-gradient(180deg, #fff7ed 0%, #ffedd5 100%);
}

.card-currency {
  font-size: var(--app-font-xl, 1.125rem);
  font-weight: 600;
  color: #f97316;
  align-self: flex-start;
  margin-top: 4px;
}

.card-value {
  font-size: 40px;
  font-weight: 700;
  color: #f97316;
  line-height: 1;
}

/* 虚线分割 */
.card-divider {
  width: 0;
  border-left: 1.5px dashed #fed7aa;
  margin: 16px 0;
  align-self: stretch;
}

/* 信息区 */
.card-body {
  flex: 1;
  padding: 20px 16px 12px;
  min-width: 0;
}

.card-title {
  font-size: var(--app-font-lg, 1rem);
  font-weight: 600;
  color: var(--app-text-primary, #1a1a2e);
  margin: 0 0 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-condition {
  font-size: var(--app-font-sm, 0.8125rem);
  color: var(--app-text-secondary, #6b7280);
  margin: 0 0 4px;
}

.card-validity {
  font-size: var(--app-font-xs, 0.75rem);
  color: var(--app-text-secondary, #6b7280);
  margin: 0;
}

/* 操作区 */
.card-action {
  flex: 0 0 100%;
  display: flex;
  justify-content: flex-end;
  padding: 0 16px 16px;
}

.btn-claim {
  --el-color-primary: #f97316;
  --el-color-primary-light-3: #ea580c;
  --el-color-primary-dark-2: #c2410c;
  border-radius: var(--app-radius-full, 9999px);
  font-weight: 500;
}

.btn-claimed {
  border-radius: var(--app-radius-full, 9999px);
}

/* ==================== 我的券列表 ==================== */
.my-coupon-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.my-coupon-card {
  background: #fff;
  border-radius: var(--app-radius-base, 8px);
  box-shadow: var(--app-shadow-level-1, 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04));
  display: flex;
  align-items: center;
  padding: 0;
  overflow: hidden;
  transition: box-shadow 0.2s var(--app-ease-standard, cubic-bezier(0.4, 0, 0.2, 1));
}

.my-coupon-card:hover {
  box-shadow: var(--app-shadow-level-2, 0 4px 12px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04));
}

/* 已使用 / 已过期半透明 */
.my-coupon-card.used,
.my-coupon-card.expired {
  opacity: 0.6;
}

.my-coupon-card.used .my-card-amount,
.my-coupon-card.expired .my-card-amount {
  background: #f3f4f6;
}

.my-coupon-card.used .my-currency,
.my-coupon-card.used .my-value,
.my-coupon-card.expired .my-currency,
.my-coupon-card.expired .my-value {
  color: #9ca3af;
}

/* 金额 */
.my-card-amount {
  flex: 0 0 100px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px 8px;
  background: linear-gradient(180deg, #fff7ed 0%, #ffedd5 100%);
  align-self: stretch;
}

.my-currency {
  font-size: var(--app-font-base, 0.875rem);
  font-weight: 600;
  color: #f97316;
  align-self: flex-start;
  margin-top: 4px;
}

.my-value {
  font-size: 32px;
  font-weight: 700;
  color: #f97316;
  line-height: 1;
}

/* 虚线分割 */
.my-card-divider {
  width: 0;
  border-left: 1.5px dashed #fed7aa;
  margin: 12px 0;
  align-self: stretch;
}

/* 信息 */
.my-card-body {
  flex: 1;
  padding: 16px;
  min-width: 0;
}

.my-card-title {
  font-size: var(--app-font-md, 0.9375rem);
  font-weight: 600;
  color: var(--app-text-primary, #1a1a2e);
  margin: 0 0 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.my-card-condition {
  font-size: var(--app-font-sm, 0.8125rem);
  color: var(--app-text-secondary, #6b7280);
  margin: 0;
}

/* 状态标签 */
.my-card-status {
  flex: 0 0 auto;
  padding: 16px;
}

/* ==================== 响应式 ==================== */
@media (max-width: 576px) {
  .coupon-grid {
    grid-template-columns: 1fr;
  }

  .card-amount {
    flex: 0 0 100px;
  }

  .card-value {
    font-size: 32px;
  }

  .my-card-amount {
    flex: 0 0 80px;
  }

  .my-value {
    font-size: 24px;
  }

  .tab-btn {
    padding: 12px 20px;
    font-size: var(--app-font-base, 0.875rem);
  }

  .coupon-hero {
    padding: var(--app-space-xl, 24px) var(--app-space-base, 16px);
  }

  .hero-title {
    font-size: var(--app-font-2xl, 1.25rem);
  }
}
</style>
