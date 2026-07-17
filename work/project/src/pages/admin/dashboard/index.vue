<template>
  <div class="dashboard-page">
    <!-- 顶部筛选栏 -->
    <div class="filter-bar">
      <h2 class="page-title">数据看板</h2>
      <div class="filter-actions">
        <span class="last-update">最后更新: {{ lastUpdateTime }}</span>
        <el-button
          size="small"
          :loading="refreshing"
          @click="refreshData"
        >
          <el-icon><Refresh /></el-icon>
          <span>刷新数据</span>
        </el-button>
      </div>
    </div>

    <!-- 骨架屏加载态 -->
    <template v-if="loading">
      <div class="kpi-row skeleton-row">
        <div v-for="i in 4" :key="'kpi-sk-' + i" class="kpi-card kpi-skeleton">
          <div class="skeleton-line skeleton-label"></div>
          <div class="skeleton-line skeleton-value"></div>
          <div class="skeleton-line skeleton-sub"></div>
        </div>
      </div>
      <div class="chart-section">
        <div class="chart-card chart-skeleton">
          <div class="skeleton-line skeleton-title"></div>
          <div class="skeleton-chart-area">
            <div class="skeleton-grid-line"></div>
            <div class="skeleton-grid-line"></div>
            <div class="skeleton-grid-line"></div>
          </div>
        </div>
      </div>
    </template>

    <!-- 错误态 -->
    <div v-else-if="error" class="state-container error-state">
      <div class="state-icon">
        <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
          <circle cx="32" cy="32" r="28" stroke="var(--color-error)" stroke-width="2.5" stroke-dasharray="8 4" opacity="0.6"/>
          <path d="M20 20L44 44M44 20L20 44" stroke="var(--color-error)" stroke-width="2.5" stroke-linecap="round"/>
        </svg>
      </div>
      <h3 class="state-title">数据加载失败</h3>
      <p class="state-desc">{{ error }}</p>
      <el-button type="primary" @click="refreshData">重新加载</el-button>
    </div>

    <!-- 空状态 -->
    <div v-else-if="isEmpty" class="state-container empty-state">
      <div class="state-icon">
        <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
          <rect x="8" y="36" width="48" height="20" rx="3" stroke="var(--color-text-tertiary)" stroke-width="2" fill="none"/>
          <path d="M8 42L26 26L34 32L46 20L56 30" stroke="var(--color-text-tertiary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          <circle cx="46" cy="20" r="2" fill="var(--color-text-tertiary)"/>
        </svg>
      </div>
      <h3 class="state-title">暂无数据</h3>
      <p class="state-desc">请尝试调整筛选条件或扩大时间范围</p>
      <el-button @click="refreshData">重置筛选</el-button>
    </div>

    <!-- 数据内容 -->
    <div v-else class="dashboard-content">
      <!-- KPI 指标行 -->
      <div class="kpi-row">
        <div class="kpi-card">
          <div class="kpi-label">今日 GMV</div>
          <div class="kpi-value kpi-gmv">
            <span class="kpi-currency">¥</span>
            <span class="kpi-number" ref="gmvRef">{{ displayGmv }}</span>
          </div>
          <div class="kpi-sub">
            <span class="kpi-compare-label">支付订单</span>
            <span class="kpi-compare-value">{{ formatCount(dashboardData.todayPaidOrders) }}</span>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-label">今日订单数</div>
          <div class="kpi-value">
            <span class="kpi-number">{{ displayOrders }}</span>
            <span class="kpi-unit">单</span>
          </div>
          <div class="kpi-sub">
            <span class="kpi-compare-label">支付率</span>
            <span class="kpi-compare-value">{{ paymentRate }}</span>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-label">今日支付订单</div>
          <div class="kpi-value kpi-paid">
            <span class="kpi-number">{{ displayPaidOrders }}</span>
            <span class="kpi-unit">单</span>
          </div>
          <div class="kpi-sub">
            <span class="kpi-compare-label">客单价</span>
            <span class="kpi-compare-value">{{ avgOrderValue }}</span>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-label">退款率</div>
          <div class="kpi-value" :class="refundRateClass">
            <span class="kpi-number">{{ displayRefundRate }}</span>
          </div>
          <div class="kpi-sub">
            <span class="kpi-compare-label">阈值告警</span>
            <span class="kpi-compare-value" :class="{ 'trend-down': refundRateNum > 0.03 }">
              {{ refundRateNum > 0.03 ? '偏高' : '正常' }}
            </span>
          </div>
        </div>
      </div>

      <!-- 图表区 -->
      <div class="chart-section">
        <div class="chart-card">
          <div class="chart-header">
            <h3 class="chart-title">近 7 日运营趋势</h3>
            <div class="chart-legend">
              <span class="legend-item legend-gmv">
                <span class="legend-dot"></span>GMV
              </span>
              <span class="legend-item legend-orders">
                <span class="legend-dot"></span>订单数
              </span>
              <span class="legend-item legend-paid">
                <span class="legend-dot"></span>支付订单
              </span>
            </div>
          </div>
          <div ref="chartRef" class="chart-container"></div>
        </div>
      </div>

      <!-- 快捷入口 -->
      <div class="quick-nav-section">
        <h3 class="quick-nav-title">管理入口</h3>
        <div class="quick-nav-grid">
          <el-button @click="$router.push({name:'AdminMerchantsReview'})">商家审核</el-button>
          <el-button @click="$router.push({name:'AdminMerchants'})">商家管理</el-button>
          <el-button @click="$router.push({name:'ProductsReview'})">商品审核</el-button>
          <el-button @click="$router.push({name:'AdminOrders'})">全局订单</el-button>
          <el-button @click="$router.push({name:'AdminRefundArbitration'})">退款仲裁</el-button>
          <el-button @click="$router.push({name:'AdminFinance'})">财务结算</el-button>
          <el-button @click="$router.push({name:'AdminLogistics'})">物流监控</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { Refresh } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import { getAdminDashboard } from '@/api/admin-dashboard';

// ── 状态 ──
const loading = ref(true);
const error = ref('');
const refreshing = ref(false);
const isEmpty = computed(() => !loading.value && !error.value && !dashboardData.todayOrders);

const dashboardData = reactive({
  todayGmv: '0.00',
  todayOrders: 0,
  todayPaidOrders: 0,
  refundRate: '0.0000',
  trend: []
});

// 动画展示值
const displayGmv = ref('0');
const displayOrders = ref('0');
const displayPaidOrders = ref('0');
const displayRefundRate = ref('0.00%');

const lastUpdateTime = ref('--:--:--');

// ECharts 实例
const chartRef = ref(null);
let chartInstance = null;
let autoRefreshTimer = null;

// ── 计算属性 ──
const refundRateNum = computed(() => parseFloat(dashboardData.refundRate) || 0);

const refundRateClass = computed(() => {
  if (refundRateNum.value > 0.03) return 'trend-down';
  if (refundRateNum.value > 0.02) return 'trend-warn';
  return '';
});

const paymentRate = computed(() => {
  if (!dashboardData.todayOrders) return '—';
  const rate = (dashboardData.todayPaidOrders / dashboardData.todayOrders * 100);
  return rate.toFixed(1) + '%';
});

const avgOrderValue = computed(() => {
  if (!dashboardData.todayPaidOrders) return '—';
  const avg = parseFloat(dashboardData.todayGmv) / dashboardData.todayPaidOrders;
  return '¥' + formatGmvShort(avg);
});

// ── 格式化函数 ──
function formatCount(val) {
  const num = Number(val);
  if (num >= 10000) return (num / 10000).toFixed(1) + '万';
  return num.toLocaleString('zh-CN');
}

function formatGmv(val) {
  const num = parseFloat(val);
  if (num >= 10000) return (num / 10000).toFixed(2) + '万';
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatGmvShort(val) {
  const num = parseFloat(val);
  if (num >= 10000) return (num / 10000).toFixed(1) + '万';
  if (num >= 1000) return num.toLocaleString('zh-CN', { maximumFractionDigits: 0 });
  return num.toFixed(2);
}

function formatPercent(val) {
  return (parseFloat(val) * 100).toFixed(2) + '%';
}

function formatTime() {
  const now = new Date();
  return now.toTimeString().slice(0, 8);
}

// ── 数字动画 ──
function animateValue(callback, start, end, duration = 800) {
  const startTime = performance.now();
  function tick(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    callback(start + (end - start) * eased);
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

function runKpiAnimations() {
  const gmv = parseFloat(dashboardData.todayGmv);
  animateValue(
    (v) => { displayGmv.value = formatGmv(v); },
    0, gmv, 1000
  );
  animateValue(
    (v) => { displayOrders.value = formatCount(Math.round(v)); },
    0, dashboardData.todayOrders, 800
  );
  animateValue(
    (v) => { displayPaidOrders.value = formatCount(Math.round(v)); },
    0, dashboardData.todayPaidOrders, 800
  );
  animateValue(
    (v) => { displayRefundRate.value = (v * 100).toFixed(2) + '%'; },
    0, refundRateNum.value, 600
  );
}

// ── ECharts ──
function getChartColors() {
  const style = getComputedStyle(document.documentElement);
  return {
    gmv: style.getPropertyValue('--page-analytics-chart-1').trim() || 'hsl(25, 85%, 55%)',
    orders: style.getPropertyValue('--page-analytics-chart-2').trim() || 'hsl(205, 70%, 55%)',
    paid: style.getPropertyValue('--page-analytics-chart-3').trim() || 'hsl(175, 65%, 50%)',
    textPrimary: style.getPropertyValue('--color-text-primary').trim() || 'hsl(25, 9%, 12%)',
    textSecondary: style.getPropertyValue('--color-text-secondary').trim() || 'hsl(25, 7%, 42%)',
    textTertiary: style.getPropertyValue('--color-text-tertiary').trim() || 'hsl(25, 4%, 62%)',
    border: style.getPropertyValue('--color-border').trim() || 'hsl(25, 7%, 90%)',
    bgBase: style.getPropertyValue('--color-bg-base').trim() || '#FFFFFF'
  };
}

function buildChartOption(data) {
  const colors = getChartColors();
  const dates = data.map(d => d.stat_date.slice(5));
  const gmvValues = data.map(d => parseFloat(d.gmv));
  const orderValues = data.map(d => d.order_count);
  const paidValues = data.map(d => d.paid_order_count);

  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: colors.bgBase,
      borderColor: colors.border,
      borderWidth: 1,
      textStyle: { color: colors.textPrimary, fontSize: 13 },
      boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
      formatter: function (params) {
        let html = '<div style="font-weight:600;margin-bottom:6px">' + params[0].axisValue + '</div>';
        params.forEach(p => {
          const val = p.seriesName === 'GMV'
            ? '¥' + formatGmv(p.value)
            : formatCount(p.value);
          html += '<div style="display:flex;align-items:center;gap:6px;margin-top:4px">'
            + '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:' + p.color + '"></span>'
            + p.seriesName + ': ' + val
            + '</div>';
        });
        return html;
      }
    },
    legend: { show: false },
    grid: {
      left: '3%',
      right: '5%',
      top: '8%',
      bottom: '8%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: colors.border } },
      axisTick: { show: false },
      axisLabel: { color: colors.textSecondary, fontSize: 12 }
    },
    yAxis: [
      {
        type: 'value',
        name: 'GMV (元)',
        nameTextStyle: { color: colors.textTertiary, fontSize: 11 },
        axisLabel: {
          color: colors.textSecondary,
          fontSize: 11,
          formatter: (v) => v >= 10000 ? (v / 10000).toFixed(0) + '万' : v
        },
        splitLine: { lineStyle: { color: colors.border, type: 'dashed', opacity: 0.4 } }
      },
      {
        type: 'value',
        name: '订单数',
        nameTextStyle: { color: colors.textTertiary, fontSize: 11 },
        axisLabel: { color: colors.textSecondary, fontSize: 11 },
        splitLine: { show: false }
      }
    ],
    series: [
      {
        name: 'GMV',
        type: 'bar',
        data: gmvValues,
        itemStyle: {
          color: colors.gmv,
          borderRadius: [6, 6, 0, 0]
        },
        barMaxWidth: 32,
        emphasis: {
          itemStyle: { color: colors.gmv }
        }
      },
      {
        name: '订单数',
        type: 'line',
        yAxisIndex: 1,
        data: orderValues,
        smooth: true,
        symbol: 'circle',
        symbolSize: 7,
        lineStyle: { color: colors.orders, width: 2.5 },
        itemStyle: { color: colors.orders },
        emphasis: { symbolSize: 10 }
      },
      {
        name: '支付订单',
        type: 'line',
        yAxisIndex: 1,
        data: paidValues,
        smooth: true,
        symbol: 'diamond',
        symbolSize: 7,
        lineStyle: { color: colors.paid, width: 2.5, type: 'dashed' },
        itemStyle: { color: colors.paid },
        emphasis: { symbolSize: 10 }
      }
    ]
  };
}

function initChart(data) {
  if (!chartRef.value) return;

  if (chartInstance) {
    chartInstance.dispose();
    chartInstance = null;
  }

  chartInstance = echarts.init(chartRef.value);
  chartInstance.setOption(buildChartOption(data));

  window.addEventListener('resize', handleResize);
}

function handleResize() {
  chartInstance?.resize();
}

// ── 数据获取 ──
async function fetchDashboardData() {
  try {
    const res = await getAdminDashboard();
    const data = res.data || res;

    if (data.mockHint) {
      ElMessage.info(data.mockHint);
    }

    dashboardData.todayGmv = data.todayGmv || '0.00';
    dashboardData.todayOrders = data.todayOrders || 0;
    dashboardData.todayPaidOrders = data.todayPaidOrders || 0;
    dashboardData.refundRate = data.refundRate || '0.0000';
    dashboardData.trend = data.trend || [];

    lastUpdateTime.value = formatTime();
    error.value = '';

    await nextTick();

    if (dashboardData.trend.length > 0) {
      initChart(dashboardData.trend);
    }

    runKpiAnimations();
  } catch (err) {
    const msg = err?.response?.data?.message || err?.message || '网络连接异常，请检查网络后重试';
    error.value = msg;
    ElMessage.error('数据加载失败');
  } finally {
    loading.value = false;
    refreshing.value = false;
  }
}

async function refreshData() {
  refreshing.value = true;
  await fetchDashboardData();
}

// ── 自动刷新 ──
function startAutoRefresh() {
  stopAutoRefresh();
  autoRefreshTimer = setInterval(() => {
    fetchDashboardData();
  }, 30000);
}

function stopAutoRefresh() {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer);
    autoRefreshTimer = null;
  }
}

// ── 生命周期 ──
onMounted(() => {
  fetchDashboardData();
  startAutoRefresh();
});

onUnmounted(() => {
  stopAutoRefresh();
  if (chartInstance) {
    window.removeEventListener('resize', handleResize);
    chartInstance.dispose();
    chartInstance = null;
  }
});
</script>

<style scoped>
/* ── 页面容器 ── */
.dashboard-page {
  padding: var(--space-xl);
  max-width: 1400px;
  margin: 0 auto;
  min-height: 100vh;
  background: var(--color-bg-page);
}

/* ── 筛选栏 ── */
.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 var(--space-lg);
  background: var(--color-bg-base);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
  margin-bottom: var(--space-lg);
}

.page-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.filter-actions {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.last-update {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-feature-settings: "tnum";
}

/* ── KPI 行 ── */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
}

@media (max-width: 1200px) {
  .kpi-row {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .kpi-row {
    grid-template-columns: 1fr;
  }
  .dashboard-page {
    padding: var(--space-md);
  }
  .filter-bar {
    padding: 0 var(--space-md);
  }
}

/* ── KPI 卡片 ── */
.kpi-card {
  background: var(--color-bg-base);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-md);
  min-height: 120px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  box-shadow: var(--shadow-sm);
  transition: box-shadow var(--duration-fast) var(--ease-smooth),
              transform var(--duration-fast) var(--ease-smooth);
}

.kpi-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.kpi-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.kpi-value {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: var(--line-height-tight);
  font-feature-settings: "tnum";
  display: flex;
  align-items: baseline;
  gap: 2px;
}

.kpi-currency {
  font-size: var(--font-size-md);
  font-weight: 500;
  color: var(--color-text-secondary);
}

.kpi-unit {
  font-size: var(--font-size-sm);
  font-weight: 400;
  color: var(--color-text-tertiary);
  margin-left: 4px;
}

.kpi-gmv .kpi-number {
  color: var(--page-analytics-trend-up, hsl(145, 70%, 50%));
}

.kpi-paid .kpi-number {
  color: var(--page-analytics-chart-3, hsl(175, 65%, 50%));
}

.kpi-value.trend-down .kpi-number {
  color: var(--page-analytics-trend-down, hsl(0, 85%, 55%));
}

.kpi-value.trend-warn .kpi-number {
  color: var(--page-analytics-alert, hsl(38, 95%, 60%));
}

.kpi-sub {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: var(--font-size-xs);
}

.kpi-compare-label {
  color: var(--color-text-tertiary);
}

.kpi-compare-value {
  color: var(--color-text-secondary);
  font-weight: 500;
}

.kpi-compare-value.trend-down {
  color: var(--page-analytics-trend-down, hsl(0, 85%, 55%));
}

/* ── 图表区 ── */
.chart-section {
  margin-bottom: var(--space-lg);
}

.chart-card {
  background: var(--color-bg-base);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  min-height: 400px;
  box-shadow: var(--shadow-sm);
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-md);
  flex-wrap: wrap;
  gap: var(--space-sm);
}

.chart-title {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.chart-legend {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.legend-gmv .legend-dot {
  background: var(--page-analytics-chart-1, hsl(25, 85%, 55%));
}

.legend-orders .legend-dot {
  background: var(--page-analytics-chart-2, hsl(205, 70%, 55%));
}

.legend-paid .legend-dot {
  background: var(--page-analytics-chart-3, hsl(175, 65%, 50%));
}

.chart-container {
  width: 100%;
  height: 340px;
}

/* ── 状态容器 ── */
.state-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-3xl) var(--space-lg);
  background: var(--color-bg-base);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  min-height: 320px;
}

.state-icon {
  margin-bottom: var(--space-lg);
  opacity: 0.7;
}

.state-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-sm) 0;
}

.state-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-lg) 0;
  text-align: center;
  max-width: 360px;
}

/* ── 骨架屏 ── */
.skeleton-row .kpi-skeleton {
  cursor: default;
}

.kpi-skeleton:hover {
  transform: none;
  box-shadow: var(--shadow-sm);
}

.skeleton-line {
  background: linear-gradient(
    90deg,
    var(--color-border) 25%,
    var(--color-bg-page) 50%,
    var(--color-border) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.8s infinite;
  border-radius: var(--radius-sm);
}

.skeleton-label {
  width: 40%;
  height: 12px;
}

.skeleton-value {
  width: 70%;
  height: 28px;
  margin: var(--space-sm) 0;
}

.skeleton-sub {
  width: 50%;
  height: 14px;
}

.skeleton-title {
  width: 30%;
  height: 16px;
  margin-bottom: var(--space-md);
}

.chart-skeleton {
  cursor: default;
}

.skeleton-chart-area {
  width: 100%;
  height: 340px;
  display: flex;
  flex-direction: column;
  justify-content: space-around;
  padding: var(--space-lg) 0;
}

.skeleton-grid-line {
  width: 100%;
  height: 1px;
  background: var(--color-border);
  opacity: 0.3;
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.quick-nav-section {
  margin-top: var(--space-lg);
  padding: var(--space-lg);
  background: var(--color-bg-base);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}
.quick-nav-title {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-md) 0;
}
.quick-nav-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: var(--space-sm);
}

</style>
