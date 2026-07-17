<template>
  <div class="dashboard-page">
    <!-- 页面标题栏 -->
    <div class="page-header">
      <h2 class="page-title">经营数据看板</h2>
      <div class="header-right">
        <span v-if="isDegraded" class="degraded-badge">
          <svg class="badge-icon" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
          </svg>
          数据可能延迟
        </span>
        <span class="update-time">
          更新于 {{ lastUpdateTime }}
          <span class="polling-dot" :class="{ active: polling && !isDegraded, degraded: isDegraded }"></span>
        </span>
      </div>
    </div>

    <!-- 快捷导航 -->
    <el-row :gutter="12" class="quick-nav-row">
      <el-col :span="6">
        <el-button class="quick-nav-btn" @click="$router.push({name:'MerchantProducts'})">
          📦 商品管理
        </el-button>
      </el-col>
      <el-col :span="6">
        <el-button class="quick-nav-btn" @click="$router.push({name:'MerchantOrders'})">
          📋 订单管理
        </el-button>
      </el-col>
      <el-col :span="6">
        <el-button class="quick-nav-btn" @click="$router.push({name:'MerchantRefunds'})">
          🔄 售后管理
        </el-button>
      </el-col>
      <el-col :span="6">
        <el-button class="quick-nav-btn" @click="$router.push({name:'MerchantWallet'})">
          💰 钱包
        </el-button>
      </el-col>
    </el-row>

    <!-- 数据降级提示 -->
    <el-alert
      v-if="isDegraded"
      type="warning"
      :closable="false"
      show-icon
      class="degraded-alert"
    >
      <template #title>
        <span>实时数据获取失败，当前显示最近一次缓存数据。</span>
        <el-button type="warning" link @click="fetchData(true)">点击刷新</el-button>
      </template>
    </el-alert>

    <!-- 首次加载：骨架屏 -->
    <template v-if="firstLoading">
      <el-row :gutter="16" class="metrics-row">
        <el-col :xs="12" :md="8" v-for="n in 3" :key="n">
          <div class="metric-card-skeleton">
            <div class="skeleton-inner">
              <div class="skeleton-circle"></div>
              <div class="skeleton-lines">
                <div class="skeleton-line short"></div>
                <div class="skeleton-line long"></div>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
      <div class="chart-card-skeleton">
        <div class="skeleton-line" style="width:120px;margin-bottom:20px"></div>
        <div class="skeleton-chart"></div>
      </div>
    </template>

    <!-- 首次加载失败：错误状态 -->
    <template v-else-if="loadError && !hasData">
      <el-result icon="error" title="数据加载失败" sub-title="请检查网络连接后重试">
        <template #extra>
          <el-button type="primary" @click="fetchData(true)">重新加载</el-button>
        </template>
      </el-result>
    </template>

    <!-- 正常内容 -->
    <template v-else>
      <!-- 指标卡片 -->
      <el-row :gutter="16" class="metrics-row">
        <el-col :xs="12" :md="8">
          <el-card class="metric-card" shadow="never">
            <div class="metric-inner">
              <div class="metric-icon gmv-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="12" y1="1" x2="12" y2="23"></line>
                  <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
                </svg>
              </div>
              <div class="metric-body">
                <div class="metric-label">今日 GMV</div>
                <div class="metric-value amount-in">{{ formatAmount(todayGmv) }}</div>
                <div class="metric-sub" v-if="gmvChange !== null">
                  <span :class="gmvChange >= 0 ? 'change-up' : 'change-down'">
                    {{ gmvChange >= 0 ? '↑' : '↓' }} {{ Math.abs(gmvChange).toFixed(1) }}%
                  </span>
                  <span class="change-label">较昨日</span>
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="12" :md="8">
          <el-card class="metric-card" shadow="never">
            <div class="metric-inner">
              <div class="metric-icon order-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                  <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
              </div>
              <div class="metric-body">
                <div class="metric-label">今日订单数</div>
                <div class="metric-value">{{ formatNumber(todayOrders) }}</div>
                <div class="metric-sub" v-if="orderChange !== null">
                  <span :class="orderChange >= 0 ? 'change-up' : 'change-down'">
                    {{ orderChange >= 0 ? '↑' : '↓' }} {{ Math.abs(orderChange).toFixed(1) }}%
                  </span>
                  <span class="change-label">较昨日</span>
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="24" :md="8">
          <el-card class="metric-card" shadow="never">
            <div class="metric-inner">
              <div class="metric-icon avg-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                </svg>
              </div>
              <div class="metric-body">
                <div class="metric-label">近7天日均 GMV</div>
                <div class="metric-value amount-in">{{ formatAmount(avgGmv) }}</div>
                <div class="metric-sub">
                  <span class="change-label">日均 {{ formatNumber(avgOrders) }} 单</span>
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 趋势图 -->
      <el-card class="chart-card" shadow="never">
        <template #header>
          <div class="chart-header">
            <span class="chart-title">近7天趋势</span>
            <div class="chart-legend-custom">
              <span class="legend-tag"><i class="legend-dot gmv"></i> GMV</span>
              <span class="legend-tag"><i class="legend-dot order"></i> 订单数</span>
            </div>
          </div>
        </template>
        <div ref="chartRef" class="chart-container"></div>
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import * as echarts from 'echarts';
import { getMerchantDashboard } from '@/api/merchant-dashboard.js';

/* ==================== 状态 ==================== */
const firstLoading = ref(true);
const loadError = ref(false);
const isDegraded = ref(false);
const polling = ref(true);
const hasData = ref(false);
const dashboardData = ref(null);
const lastUpdateTime = ref('--');
const chartRef = ref(null);

let chartInstance = null;
let pollingTimer = null;
let resizeObserver = null;

/* ==================== 计算属性 ==================== */
const todayGmv = computed(() => dashboardData.value?.todayGmv ?? '0.00');
const todayOrders = computed(() => dashboardData.value?.todayOrders ?? 0);
const trend = computed(() => dashboardData.value?.trend ?? []);

/** 近7天日均 GMV */
const avgGmv = computed(() => {
  const arr = trend.value;
  if (!arr.length) return '0.00';
  const sum = arr.reduce((s, d) => s + parseFloat(d.gmv || 0), 0);
  return (sum / arr.length).toFixed(2);
});

/** 近7天日均订单数 */
const avgOrders = computed(() => {
  const arr = trend.value;
  if (!arr.length) return 0;
  const sum = arr.reduce((s, d) => s + (d.orderCount || 0), 0);
  return Math.round(sum / arr.length);
});

/** GMV 较昨日变化百分比 */
const gmvChange = computed(() => {
  const arr = trend.value;
  if (arr.length < 2) return null;
  const yesterday = parseFloat(arr[arr.length - 2].gmv || 0);
  const today = parseFloat(arr[arr.length - 1].gmv || 0);
  if (yesterday === 0) return today > 0 ? 100 : 0;
  return ((today - yesterday) / yesterday) * 100;
});

/** 订单数较昨日变化百分比 */
const orderChange = computed(() => {
  const arr = trend.value;
  if (arr.length < 2) return null;
  const yesterday = arr[arr.length - 2].orderCount || 0;
  const today = arr[arr.length - 1].orderCount || 0;
  if (yesterday === 0) return today > 0 ? 100 : 0;
  return ((today - yesterday) / yesterday) * 100;
});

/* ==================== 工具函数 ==================== */

/** 格式化金额：千分位 + 2位小数 */
function formatAmount(val) {
  const num = parseFloat(val);
  if (isNaN(num)) return '¥0.00';
  return '¥' + num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** 格式化整数：千分位 */
function formatNumber(val) {
  const num = parseInt(val, 10);
  if (isNaN(num)) return '0';
  return num.toLocaleString('zh-CN');
}

/** 格式化时间为 HH:mm:ss */
function formatTime() {
  const now = new Date();
  return now.toTimeString().slice(0, 8);
}

/* ==================== ECharts 初始化 ==================== */

function initChart() {
  if (!chartRef.value) return;
  if (chartInstance) {
    chartInstance.dispose();
    chartInstance = null;
  }

  chartInstance = echarts.init(chartRef.value);

  // 自适应
  resizeObserver = new ResizeObserver(() => {
    chartInstance?.resize();
  });
  resizeObserver.observe(chartRef.value);

  renderChart();
}

function renderChart() {
  if (!chartInstance) return;

  const arr = trend.value;
  if (!arr.length) {
    chartInstance.clear();
    return;
  }

  const dates = arr.map(d => {
    const parts = d.statDate.split('-');
    return parts.length === 3 ? parts[1] + '/' + parts[2] : d.statDate;
  });
  const gmvData = arr.map(d => parseFloat(d.gmv || 0));
  const orderData = arr.map(d => d.orderCount || 0);

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: '#ffffff',
      borderColor: 'hsl(25, 7%, 90%)',
      textStyle: { color: 'hsl(25, 9%, 12%)', fontSize: 13 },
      formatter: function (params) {
        let html = '<div style="font-weight:600;margin-bottom:6px">' + params[0].axisValue + '</div>';
        params.forEach(p => {
          const val = p.seriesName === 'GMV'
            ? '¥' + p.value.toLocaleString('zh-CN', { minimumFractionDigits: 2 })
            : p.value + ' 单';
          html += '<div style="display:flex;align-items:center;gap:6px;margin-top:4px">'
            + '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:' + p.color + '"></span>'
            + p.seriesName + '：' + val
            + '</div>';
        });
        return html;
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '8%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: 'hsl(25, 7%, 90%)' } },
      axisTick: { show: false },
      axisLabel: { color: 'hsl(25, 4%, 62%)', fontSize: 12 }
    },
    yAxis: [
      {
        type: 'value',
        name: 'GMV',
        nameTextStyle: { color: 'hsl(25, 4%, 62%)', fontSize: 11 },
        axisLabel: {
          color: 'hsl(25, 4%, 62%)',
          fontSize: 11,
          formatter: function (v) {
            if (v >= 10000) return (v / 10000).toFixed(1) + 'w';
            if (v >= 1000) return (v / 1000).toFixed(1) + 'k';
            return v;
          }
        },
        splitLine: { lineStyle: { color: 'hsl(25, 7%, 93%)', type: 'dashed' } }
      },
      {
        type: 'value',
        name: '订单数',
        nameTextStyle: { color: 'hsl(25, 4%, 62%)', fontSize: 11 },
        axisLabel: { color: 'hsl(25, 4%, 62%)', fontSize: 11 },
        splitLine: { show: false }
      }
    ],
    series: [
      {
        name: 'GMV',
        type: 'bar',
        data: gmvData,
        barWidth: '40%',
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'hsl(25, 85%, 62%)' },
            { offset: 1, color: 'hsl(25, 75%, 70%)' }
          ]),
          borderRadius: [6, 6, 0, 0]
        },
        emphasis: {
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'hsl(25, 85%, 55%)' },
              { offset: 1, color: 'hsl(25, 75%, 60%)' }
            ])
          }
        }
      },
      {
        name: '订单数',
        type: 'line',
        yAxisIndex: 1,
        data: orderData,
        lineStyle: { color: 'hsl(155, 75%, 42%)', width: 2.5 },
        itemStyle: { color: 'hsl(155, 75%, 42%)', borderColor: '#fff', borderWidth: 2 },
        symbol: 'circle',
        symbolSize: 8,
        smooth: true
      }
    ]
  };

  chartInstance.setOption(option, true);
}

function disposeChart() {
  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }
  if (chartInstance) {
    chartInstance.dispose();
    chartInstance = null;
  }
}

/* ==================== 数据获取 ==================== */

async function fetchData(isManual = false) {
  if (isManual) {
    loadError.value = false;
  }

  try {
    const res = await getMerchantDashboard();
    if (res && res.success !== false) {
      const data = res.data || res;
      dashboardData.value = data;
      hasData.value = true;
      isDegraded.value = false;
      loadError.value = false;
      lastUpdateTime.value = formatTime();

      await nextTick();
      if (!chartInstance && chartRef.value) {
        initChart();
      } else {
        renderChart();
      }
    } else {
      throw new Error('API returned unsuccessful response');
    }
  } catch (err) {
    console.error('[Dashboard] fetch error:', err);
    loadError.value = true;

    if (hasData.value) {
      // 已有缓存数据 → 降级模式
      isDegraded.value = true;
    }
  } finally {
    firstLoading.value = false;
  }
}

function startPolling() {
  stopPolling();
  polling.value = true;
  pollingTimer = setInterval(() => {
    fetchData(false);
  }, 5000);
}

function stopPolling() {
  polling.value = false;
  if (pollingTimer) {
    clearInterval(pollingTimer);
    pollingTimer = null;
  }
}

/* ==================== 生命周期 ==================== */
onMounted(async () => {
  await fetchData(true);
  startPolling();

  // 页面可见性变化：隐藏时暂停轮询
  document.addEventListener('visibilitychange', handleVisibility);
});

onUnmounted(() => {
  stopPolling();
  disposeChart();
  document.removeEventListener('visibilitychange', handleVisibility);
});

function handleVisibility() {
  if (document.hidden) {
    stopPolling();
  } else {
    fetchData(false);
    startPolling();
  }
}
</script>

<style scoped>
/* ==================== 页面容器 ==================== */
.dashboard-page {
  max-width: 960px;
  margin: 0 auto;
  padding: var(--space-lg, 24px);
  background: var(--color-bg-page, hsl(25, 5%, 97%));
  min-height: 100vh;
}

/* ==================== 页面标题栏 ==================== */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-lg, 24px);
}

.page-title {
  margin: 0;
  font-size: var(--font-size-xl, 21px);
  font-weight: 700;
  color: var(--color-text-primary, hsl(25, 9%, 12%));
  letter-spacing: -0.3px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--space-md, 16px);
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
}

.degraded-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: var(--radius-full, 9999px);
  background: hsl(38, 90%, 92%);
  color: hsl(38, 90%, 35%);
  font-weight: 500;
}

.badge-icon {
  width: 14px;
  height: 14px;
}

.update-time {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.polling-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-text-tertiary, hsl(25, 4%, 62%));
  transition: background var(--duration-fast, 150ms) var(--ease-smooth, cubic-bezier(0.16, 1, 0.3, 1));
}

.polling-dot.active {
  background: hsl(155, 75%, 42%);
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.4);
}

.polling-dot.degraded {
  background: hsl(38, 95%, 50%);
  box-shadow: 0 0 6px rgba(245, 158, 11, 0.4);
}

/* ==================== 降级提示 ==================== */
.degraded-alert {
  margin-bottom: var(--space-md, 16px);
  border-radius: var(--radius-md, 20px);
}

/* ==================== 指标卡片行 ==================== */
.metrics-row {
  margin-bottom: var(--space-md, 16px);
}

.metric-card {
  border-radius: var(--radius-md, 20px);
  border: 1px solid var(--color-border, hsl(25, 7%, 90%));
  transition: box-shadow var(--duration-fast, 150ms) var(--ease-smooth, cubic-bezier(0.16, 1, 0.3, 1));
}

.metric-card:hover {
  box-shadow: var(--shadow-md, 0 4px 12px rgba(30, 28, 27, 0.08));
}

.metric-card :deep(.el-card__body) {
  padding: var(--space-lg, 24px);
}

.metric-inner {
  display: flex;
  align-items: flex-start;
  gap: var(--space-md, 16px);
}

/* 图标容器 */
.metric-icon {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  border-radius: var(--radius-sm, 10px);
  display: flex;
  align-items: center;
  justify-content: center;
}

.metric-icon svg {
  width: 22px;
  height: 22px;
}

.gmv-icon {
  background: hsl(25, 60%, 93%);
  color: hsl(25, 85%, 50%);
}

.order-icon {
  background: hsl(210, 60%, 93%);
  color: hsl(210, 70%, 50%);
}

.avg-icon {
  background: hsl(155, 60%, 93%);
  color: hsl(155, 75%, 38%);
}

/* 指标内容 */
.metric-body {
  flex: 1;
  min-width: 0;
}

.metric-label {
  font-size: var(--font-size-xs, 10.5px);
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.metric-value {
  font-size: var(--font-size-2xl, 28px);
  font-weight: 700;
  color: var(--color-text-primary, hsl(25, 9%, 12%));
  letter-spacing: -0.5px;
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}

.metric-value.amount-in {
  color: var(--page-settlement-amount-in, hsl(155, 75%, 42%));
}

.metric-sub {
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--font-size-xs, 10.5px);
}

.change-up {
  color: hsl(155, 75%, 42%);
  font-weight: 600;
}

.change-down {
  color: hsl(0, 80%, 52%);
  font-weight: 600;
}

.change-label {
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
}

/* ==================== 骨架屏 ==================== */
.metric-card-skeleton {
  background: var(--color-bg-base, #ffffff);
  border: 1px solid var(--color-border, hsl(25, 7%, 90%));
  border-radius: var(--radius-md, 20px);
  padding: var(--space-lg, 24px);
}

.skeleton-inner {
  display: flex;
  align-items: flex-start;
  gap: var(--space-md, 16px);
}

.skeleton-circle {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-sm, 10px);
  background: linear-gradient(90deg, hsl(25, 5%, 93%) 25%, hsl(25, 5%, 97%) 50%, hsl(25, 5%, 93%) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.8s ease-in-out infinite;
  flex-shrink: 0;
}

.skeleton-lines {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton-line {
  height: 12px;
  border-radius: 6px;
  background: linear-gradient(90deg, hsl(25, 5%, 93%) 25%, hsl(25, 5%, 97%) 50%, hsl(25, 5%, 93%) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.8s ease-in-out infinite;
}

.skeleton-line.short {
  width: 55%;
}

.skeleton-line.long {
  width: 85%;
  height: 18px;
}

.chart-card-skeleton {
  background: var(--color-bg-base, #ffffff);
  border: 1px solid var(--color-border, hsl(25, 7%, 90%));
  border-radius: var(--radius-md, 20px);
  padding: var(--space-lg, 24px);
}

.skeleton-chart {
  height: 320px;
  border-radius: var(--radius-sm, 10px);
  background: linear-gradient(90deg, hsl(25, 5%, 93%) 25%, hsl(25, 5%, 97%) 50%, hsl(25, 5%, 93%) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.8s ease-in-out infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ==================== 趋势图卡片 ==================== */
.chart-card {
  border-radius: var(--radius-md, 20px);
  border: 1px solid var(--color-border, hsl(25, 7%, 90%));
}

.chart-card :deep(.el-card__header) {
  padding: var(--space-md, 16px) var(--space-lg, 24px);
  border-bottom: 1px solid var(--color-border, hsl(25, 7%, 90%));
}

.chart-card :deep(.el-card__body) {
  padding: var(--space-md, 16px);
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chart-title {
  font-size: var(--font-size-md, 15.75px);
  font-weight: 600;
  color: var(--color-text-primary, hsl(25, 9%, 12%));
}

.chart-legend-custom {
  display: flex;
  gap: var(--space-md, 16px);
}

.legend-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: var(--font-size-xs, 10.5px);
  color: var(--color-text-secondary, hsl(25, 7%, 42%));
}

.legend-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend-dot.gmv {
  background: hsl(25, 85%, 62%);
}

.legend-dot.order {
  background: hsl(155, 75%, 42%);
}

/* 图表容器 */
.chart-container {
  width: 100%;
  height: 360px;
}

/* ==================== 错误状态（覆盖 el-result 默认样式） ==================== */
.dashboard-page :deep(.el-result) {
  padding: var(--space-3xl, 64px) 0;
}

.dashboard-page :deep(.el-result__title) {
  color: var(--color-text-primary, hsl(25, 9%, 12%));
}

.dashboard-page :deep(.el-result__subtitle) {
  color: var(--color-text-secondary, hsl(25, 7%, 42%));
}

/* ==================== 响应式 ==================== */
@media (max-width: 768px) {
  .dashboard-page {
    padding: var(--space-md, 16px);
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-sm, 8px);
  }

  .metric-value {
    font-size: var(--font-size-xl, 21px);
  }

  .chart-container {
    height: 260px;
  }

  .header-right {
    flex-wrap: wrap;
  }
}
</style>
