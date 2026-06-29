<template>
  <div class="dashboard">
    <!-- 页面头部 -->
    <div class="dashboard-header">
      <div class="header-left">
        <h1 class="page-title">
          <el-icon :size="28"><DataAnalysis /></el-icon>
          经营数据大屏
        </h1>
        <span class="page-subtitle">实时监控平台核心经营指标</span>
      </div>
      <div class="header-right">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          :shortcuts="dateShortcuts"
          :disabled-date="disabledDate"
          size="large"
          class="date-picker"
          @change="onDateChange"
        />
        <el-button
          :icon="Refresh"
          :loading="loading"
          size="large"
          round
          class="refresh-btn"
          @click="fetchAllData"
        >
          刷新
        </el-button>
      </div>
    </div>

    <!-- 加载骨架 -->
    <template v-if="loading && !hasAnyData">
      <div class="kpi-grid">
        <div v-for="i in 6" :key="'sk-kpi-' + i" class="kpi-card skeleton">
          <div class="skeleton-pulse skeleton-label"></div>
          <div class="skeleton-pulse skeleton-value"></div>
          <div class="skeleton-pulse skeleton-sub"></div>
        </div>
      </div>
      <div class="charts-row">
        <div v-for="i in 4" :key="'sk-chart-' + i" class="chart-card skeleton-chart">
          <div class="skeleton-pulse skeleton-chart-area"></div>
        </div>
      </div>
    </template>

    <!-- 错误态 -->
    <template v-else-if="error && !hasAnyData">
      <div class="error-state">
        <el-icon :size="64" color="#ef4444"><WarningFilled /></el-icon>
        <p class="error-text">{{ error }}</p>
        <el-button type="primary" size="large" round @click="fetchAllData">
          <el-icon><Refresh /></el-icon> 重新加载
        </el-button>
      </div>
    </template>

    <!-- 主内容 -->
    <template v-else>
      <!-- KPI 指标卡 -->
      <div class="kpi-grid">
        <div class="kpi-card kpi-orders">
          <div class="kpi-icon">
            <el-icon :size="32"><Document /></el-icon>
          </div>
          <div class="kpi-info">
            <span class="kpi-label">总订单数</span>
            <span class="kpi-value">{{ formatNumber(orderData?.totalOrders) }}</span>
            <span class="kpi-sub">
              <el-icon :size="14"><TrendCharts /></el-icon>
              统计周期内
            </span>
          </div>
        </div>

        <div class="kpi-card kpi-amount">
          <div class="kpi-icon">
            <el-icon :size="32"><Money /></el-icon>
          </div>
          <div class="kpi-info">
            <span class="kpi-label">订单总额</span>
            <span class="kpi-value">¥{{ formatAmount(orderData?.totalAmount) }}</span>
            <span class="kpi-sub">
              <el-icon :size="14"><TrendCharts /></el-icon>
              统计周期内
            </span>
          </div>
        </div>

        <div class="kpi-card kpi-payments">
          <div class="kpi-icon">
            <el-icon :size="32"><CreditCard /></el-icon>
          </div>
          <div class="kpi-info">
            <span class="kpi-label">支付笔数</span>
            <span class="kpi-value">{{ formatNumber(paymentData?.totalPayments) }}</span>
            <span class="kpi-sub">
              <el-icon :size="14"><TrendCharts /></el-icon>
              支付总额 ¥{{ formatAmount(paymentData?.totalAmount) }}
            </span>
          </div>
        </div>

        <div class="kpi-card kpi-refunds">
          <div class="kpi-icon">
            <el-icon :size="32"><Wallet /></el-icon>
          </div>
          <div class="kpi-info">
            <span class="kpi-label">退款笔数</span>
            <span class="kpi-value">{{ formatNumber(refundData?.totalRefunds) }}</span>
            <span class="kpi-sub">
              <el-icon :size="14"><TrendCharts /></el-icon>
              退款总额 ¥{{ formatAmount(refundData?.totalAmount) }}
            </span>
          </div>
        </div>

        <div class="kpi-card kpi-rate">
          <div class="kpi-icon">
            <el-icon :size="32"><PieChart /></el-icon>
          </div>
          <div class="kpi-info">
            <span class="kpi-label">退款率</span>
            <span class="kpi-value" :class="rateClass">{{ formatPercent(refundData?.refundRate) }}</span>
            <span class="kpi-sub">
              <el-icon :size="14"><TrendCharts /></el-icon>
              {{ rateDesc }}
            </span>
          </div>
        </div>

        <div class="kpi-card kpi-time">
          <div class="kpi-icon">
            <el-icon :size="32"><Clock /></el-icon>
          </div>
          <div class="kpi-info">
            <span class="kpi-label">数据更新时间</span>
            <span class="kpi-value kpi-time-value">{{ lastUpdateTime }}</span>
            <span class="kpi-sub">
              <el-icon :size="14"><TrendCharts /></el-icon>
              实时刷新
            </span>
          </div>
        </div>
      </div>

      <!-- 图表区域 第一行 -->
      <div class="charts-row">
        <div class="chart-card chart-card--wide">
          <div class="chart-card-header">
            <h3><el-icon :size="18"><Histogram /></el-icon> 订单状态分布</h3>
            <span class="chart-card-tip">各状态订单数量占比</span>
          </div>
          <div class="chart-body">
            <div v-if="!orderData?.byStatus?.length" class="chart-empty">暂无数据</div>
            <div v-else ref="orderStatusChartRef" class="chart-instance"></div>
          </div>
        </div>

        <div class="chart-card chart-card--narrow">
          <div class="chart-card-header">
            <h3><el-icon :size="18"><PieChart /></el-icon> 支付渠道分布</h3>
            <span class="chart-card-tip">各渠道支付金额占比</span>
          </div>
          <div class="chart-body">
            <div v-if="!paymentData?.byChannel?.length" class="chart-empty">暂无数据</div>
            <div v-else ref="paymentChannelChartRef" class="chart-instance"></div>
          </div>
        </div>
      </div>

      <!-- 图表区域 第二行 -->
      <div class="charts-row">
        <div class="chart-card chart-card--narrow">
          <div class="chart-card-header">
            <h3><el-icon :size="18"><Warning /></el-icon> 退款原因分布</h3>
            <span class="chart-card-tip">各退款原因数量统计</span>
          </div>
          <div class="chart-body">
            <div v-if="!refundData?.byReason?.length" class="chart-empty">暂无数据</div>
            <div v-else ref="refundReasonChartRef" class="chart-instance"></div>
          </div>
        </div>

        <div class="chart-card chart-card--wide">
          <div class="chart-card-header">
            <h3><el-icon :size="18"><TrendCharts /></el-icon> 订单趋势（按日期）</h3>
            <span class="chart-card-tip">每日订单量与金额变化</span>
          </div>
          <div class="chart-body">
            <div v-if="!orderData?.byDate?.length" class="chart-empty">暂无数据</div>
            <div v-else ref="orderTrendChartRef" class="chart-instance"></div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
/**
 * AdminDashboard — 平台后台经营数据大屏
 * 展示订单漏斗、支付汇总、退款统计，深蓝灰数据大屏风格
 */
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue';
import {
  DataAnalysis, Refresh, Document, Money, CreditCard,
  Wallet, PieChart, Clock, TrendCharts, Histogram,
  Warning, WarningFilled
} from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import { getOrderReports, getPaymentReports, getRefundReports } from '@/api/admin/reports';

/* ==================== 日期筛选 ==================== */

const dateRange = ref([
  new Date(Date.now() - 30 * 24 * 3600 * 1000),
  new Date()
]);

const dateShortcuts = [
  { text: '最近7天', value: () => { const e = new Date(); const s = new Date(); s.setDate(s.getDate() - 7); return [s, e]; } },
  { text: '最近30天', value: () => { const e = new Date(); const s = new Date(); s.setDate(s.getDate() - 30); return [s, e]; } },
  { text: '最近90天', value: () => { const e = new Date(); const s = new Date(); s.setDate(s.getDate() - 90); return [s, e]; } },
  { text: '本月', value: () => { const e = new Date(); const s = new Date(); s.setDate(1); return [s, e]; } },
  { text: '上月', value: () => { const e = new Date(); e.setDate(0); const s = new Date(); s.setDate(0); s.setDate(1); return [s, e]; } }
];

function disabledDate(time) {
  return time.getTime() > Date.now();
}

function getDateParams() {
  if (!dateRange.value || dateRange.value.length !== 2) {
    return {};
  }
  const [start, end] = dateRange.value;
  const fmt = (d) => {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  };
  return { startDate: fmt(start), endDate: fmt(end) };
}

/* ==================== 数据状态 ==================== */

const loading = ref(false);
const error = ref(null);
const orderData = ref(null);
const paymentData = ref(null);
const refundData = ref(null);
const lastUpdateTime = ref('--');

const hasAnyData = computed(() => orderData.value || paymentData.value || refundData.value);

const rateClass = computed(() => {
  const rate = refundData.value?.refundRate;
  if (rate == null) return '';
  if (rate < 0.05) return 'rate-good';
  if (rate < 0.15) return 'rate-warn';
  return 'rate-bad';
});

const rateDesc = computed(() => {
  const rate = refundData.value?.refundRate;
  if (rate == null) return '--';
  if (rate < 0.05) return '健康';
  if (rate < 0.15) return '关注';
  return '偏高';
});

/* ==================== 数据获取 ==================== */

async function fetchAllData() {
  loading.value = true;
  error.value = null;

  const params = getDateParams();

  try {
    const [orderRes, paymentRes, refundRes] = await Promise.allSettled([
      getOrderReports(params),
      getPaymentReports(params),
      getRefundReports(params)
    ]);

    if (orderRes.status === 'fulfilled') {
      orderData.value = orderRes.value.data ?? orderRes.value;
    } else {
      ElMessage.warning('订单报表加载失败');
    }

    if (paymentRes.status === 'fulfilled') {
      paymentData.value = paymentRes.value.data ?? paymentRes.value;
    } else {
      ElMessage.warning('支付报表加载失败');
    }

    if (refundRes.status === 'fulfilled') {
      refundData.value = refundRes.value.data ?? refundRes.value;
    } else {
      ElMessage.warning('退款报表加载失败');
    }

    const now = new Date();
    lastUpdateTime.value = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;

    await nextTick();
    renderAllCharts();
  } catch (err) {
    error.value = err?.response?.data?.message || err?.message || '数据加载失败，请检查网络后重试';
  } finally {
    loading.value = false;
  }
}

function onDateChange() {
  fetchAllData();
}

/* ==================== 图表引用与实例 ==================== */

const orderStatusChartRef = ref(null);
const paymentChannelChartRef = ref(null);
const refundReasonChartRef = ref(null);
const orderTrendChartRef = ref(null);

const chartInstances = {};

function disposeChart(key) {
  if (chartInstances[key]) {
    chartInstances[key].dispose();
    delete chartInstances[key];
  }
}

function disposeAllCharts() {
  Object.keys(chartInstances).forEach(disposeChart);
}

function initChart(refKey, domRef) {
  disposeChart(refKey);
  const dom = domRef.value;
  if (!dom) return null;
  const instance = echarts.init(dom);
  chartInstances[refKey] = instance;
  return instance;
}

function renderAllCharts() {
  renderOrderStatusChart();
  renderPaymentChannelChart();
  renderRefundReasonChart();
  renderOrderTrendChart();
}

/* ==================== 图表配置 ==================== */

const chartTextColor = '#8899aa';
const chartAxisColor = '#1e3050';

function makeChartOption(extra) {
  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(13,25,48,0.95)',
      borderColor: '#1e3a5f',
      textStyle: { color: '#e0e6ed', fontSize: 13 },
      ...(extra.tooltip || {})
    },
    legend: {
      textStyle: { color: chartTextColor, fontSize: 12 },
      ...(extra.legend || {})
    },
    grid: {
      left: '3%',
      right: '5%',
      bottom: '8%',
      top: '15%',
      containLabel: true,
      ...(extra.grid || {})
    },
    xAxis: {
      type: 'category',
      axisLine: { lineStyle: { color: chartAxisColor } },
      axisTick: { show: false },
      axisLabel: { color: chartTextColor, fontSize: 11 },
      ...(extra.xAxis || {})
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: chartTextColor, fontSize: 11 },
      ...(extra.yAxis || {})
    },
    series: extra.series || [],
    ...(extra.rest || {})
  };
}

function renderOrderStatusChart() {
  const data = orderData.value?.byStatus;
  if (!data || !data.length) return;

  const instance = initChart('orderStatus', orderStatusChartRef);
  if (!instance) return;

  const names = data.map(d => d.status ?? d.name ?? '');
  const values = data.map(d => d.count ?? d.value ?? 0);

  const option = makeChartOption({
    tooltip: { trigger: 'axis' },
    xAxis: { data: names },
    yAxis: {},
    series: [{
      name: '订单数',
      type: 'bar',
      data: values,
      barWidth: 40,
      itemStyle: {
        borderRadius: [4, 4, 0, 0],
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#409eff' },
          { offset: 1, color: '#1a3a6e' }
        ])
      },
      emphasis: {
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#66b1ff' },
            { offset: 1, color: '#409eff' }
          ])
        }
      }
    }]
  });

  instance.setOption(option);
}

function renderPaymentChannelChart() {
  const data = paymentData.value?.byChannel;
  if (!data || !data.length) return;

  const instance = initChart('paymentChannel', paymentChannelChartRef);
  if (!instance) return;

  const pieData = data.map(d => ({
    name: d.channel ?? d.name ?? '',
    value: parseFloat(d.amount ?? d.value ?? 0)
  }));

  const colors = ['#409eff', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6'];

  const option = {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(13,25,48,0.95)',
      borderColor: '#1e3a5f',
      textStyle: { color: '#e0e6ed', fontSize: 13 },
      formatter: '{b}: ¥{c} ({d}%)'
    },
    legend: {
      bottom: '0%',
      textStyle: { color: chartTextColor, fontSize: 12 }
    },
    color: colors,
    series: [{
      type: 'pie',
      radius: ['50%', '78%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 4,
        borderColor: '#0f1d35',
        borderWidth: 3
      },
      label: {
        show: false
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 16,
          fontWeight: 'bold',
          color: '#e0e6ed'
        },
        scaleSize: 8
      },
      data: pieData
    }]
  };

  instance.setOption(option);
}

function renderRefundReasonChart() {
  const data = refundData.value?.byReason;
  if (!data || !data.length) return;

  const instance = initChart('refundReason', refundReasonChartRef);
  if (!instance) return;

  const names = data.map(d => d.reason ?? d.name ?? '');
  const values = data.map(d => d.count ?? d.value ?? 0);

  const option = makeChartOption({
    tooltip: { trigger: 'axis' },
    xAxis: { data: names, axisLabel: { rotate: names.length > 4 ? 30 : 0 } },
    yAxis: {},
    series: [{
      name: '退款数',
      type: 'bar',
      data: values,
      barWidth: 32,
      itemStyle: {
        borderRadius: [4, 4, 0, 0],
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#f59e0b' },
          { offset: 1, color: '#8b4500' }
        ])
      }
    }]
  });

  instance.setOption(option);
}

function renderOrderTrendChart() {
  const data = orderData.value?.byDate;
  if (!data || !data.length) return;

  const instance = initChart('orderTrend', orderTrendChartRef);
  if (!instance) return;

  const dates = data.map(d => d.date ?? '');
  const counts = data.map(d => d.count ?? d.orders ?? 0);
  const amounts = data.map(d => parseFloat(d.amount ?? 0));

  const option = makeChartOption({
    tooltip: {
      trigger: 'axis',
      formatter: function(params) {
        const d = params[0]?.name ?? '';
        let html = `<div style="font-weight:600;margin-bottom:4px">${d}</div>`;
        params.forEach(p => {
          const val = p.seriesName === '订单金额'
            ? '¥' + (Number(p.value) || 0).toLocaleString()
            : (p.value ?? 0);
          html += `<div>${p.marker} ${p.seriesName}: <b>${val}</b></div>`;
        });
        return html;
      }
    },
    legend: { top: '0%' },
    xAxis: { data: dates, boundaryGap: false },
    yAxis: [
      {
        type: 'value',
        name: '订单数',
        nameTextStyle: { color: chartTextColor },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } },
        axisLabel: { color: chartTextColor },
        axisLine: { show: false },
        axisTick: { show: false }
      },
      {
        type: 'value',
        name: '金额(元)',
        nameTextStyle: { color: chartTextColor },
        splitLine: { show: false },
        axisLabel: { color: chartTextColor, formatter: '¥{value}' },
        axisLine: { show: false },
        axisTick: { show: false }
      }
    ],
    series: [
      {
        name: '订单数',
        type: 'line',
        data: counts,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { width: 2.5, color: '#409eff' },
        itemStyle: { color: '#409eff' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64,158,255,0.25)' },
            { offset: 1, color: 'rgba(64,158,255,0.01)' }
          ])
        }
      },
      {
        name: '订单金额',
        type: 'line',
        yAxisIndex: 1,
        data: amounts,
        smooth: true,
        symbol: 'diamond',
        symbolSize: 7,
        lineStyle: { width: 2.5, color: '#22c55e' },
        itemStyle: { color: '#22c55e' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(34,197,94,0.2)' },
            { offset: 1, color: 'rgba(34,197,94,0.01)' }
          ])
        }
      }
    ]
  });

  instance.setOption(option);
}

/* ==================== 格式化工具 ==================== */

function formatNumber(val) {
  if (val == null) return '--';
  return Number(val).toLocaleString();
}

function formatAmount(val) {
  if (val == null) return '--';
  const n = parseFloat(val);
  if (Number.isNaN(n)) return '--';
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatPercent(val) {
  if (val == null) return '--';
  const n = parseFloat(val);
  if (Number.isNaN(n)) return '--';
  return (n * 100).toFixed(1) + '%';
}

/* ==================== 响应式图表 ==================== */

function handleResize() {
  Object.values(chartInstances).forEach(inst => {
    if (inst && !inst.isDisposed()) {
      inst.resize();
    }
  });
}

/* ==================== 生命周期 ==================== */

let resizeObserver = null;

onMounted(() => {
  fetchAllData();
  window.addEventListener('resize', handleResize);

  resizeObserver = new ResizeObserver(() => {
    handleResize();
  });
  const container = document.querySelector('.dashboard');
  if (container) {
    resizeObserver.observe(container);
  }
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize);
  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }
  disposeAllCharts();
});
</script>

<style scoped>
/* ==================== 大屏容器 ==================== */
.dashboard {
  min-height: 100vh;
  padding: 24px 28px;
  background: linear-gradient(160deg, #060e1e 0%, #0a1628 30%, #0d1a30 60%, #09101f 100%);
  color: #e0e6ed;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans SC', sans-serif;
}

/* ==================== 页面头部 ==================== */
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
  flex-wrap: wrap;
  gap: 16px;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 16px;
  flex-wrap: wrap;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #e0e6ed;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  letter-spacing: 0.02em;
}

.page-title .el-icon {
  color: #409eff;
}

.page-subtitle {
  font-size: 0.8125rem;
  color: #5a7088;
  letter-spacing: 0.04em;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.date-picker {
  width: 280px;
}

.date-picker :deep(.el-range-input) {
  background: transparent;
  color: #e0e6ed;
}

.date-picker :deep(.el-range-separator) {
  color: #5a7088;
}

.refresh-btn {
  border: 1px solid rgba(64,158,255,0.35);
  background: rgba(64,158,255,0.08);
  color: #409eff;
  transition: all 0.2s ease;
}

.refresh-btn:hover {
  background: rgba(64,158,255,0.18);
  border-color: rgba(64,158,255,0.6);
  box-shadow: 0 0 12px rgba(64,158,255,0.15);
}

/* ==================== KPI 指标卡 ==================== */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 18px;
  margin-bottom: 24px;
}

.kpi-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 22px;
  background: linear-gradient(135deg, rgba(15,29,53,0.9) 0%, rgba(18,32,66,0.85) 100%);
  border: 1px solid rgba(30,58,95,0.5);
  border-radius: 12px;
  position: relative;
  overflow: hidden;
  transition: all 0.25s ease;
}

.kpi-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(64,158,255,0.4), transparent);
  opacity: 0;
  transition: opacity 0.25s ease;
}

.kpi-card:hover {
  transform: translateY(-2px);
  border-color: rgba(64,158,255,0.5);
  box-shadow: 0 8px 32px rgba(0,0,0,0.35), 0 0 16px rgba(64,158,255,0.06);
}

.kpi-card:hover::before {
  opacity: 1;
}

.kpi-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.kpi-orders .kpi-icon {
  background: rgba(64,158,255,0.12);
  color: #409eff;
}

.kpi-amount .kpi-icon {
  background: rgba(34,197,94,0.12);
  color: #22c55e;
}

.kpi-payments .kpi-icon {
  background: rgba(139,92,246,0.12);
  color: #8b5cf6;
}

.kpi-refunds .kpi-icon {
  background: rgba(245,158,11,0.12);
  color: #f59e0b;
}

.kpi-rate .kpi-icon {
  background: rgba(239,68,68,0.12);
  color: #ef4444;
}

.kpi-time .kpi-icon {
  background: rgba(100,180,200,0.12);
  color: #64b4c8;
}

.kpi-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.kpi-label {
  font-size: 0.75rem;
  color: #5a7088;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.kpi-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #e0e6ed;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.kpi-time-value {
  font-size: 1.25rem;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
}

.kpi-sub {
  font-size: 0.75rem;
  color: #4a6078;
  display: flex;
  align-items: center;
  gap: 4px;
}

.rate-good { color: #22c55e !important; }
.rate-warn { color: #f59e0b !important; }
.rate-bad  { color: #ef4444 !important; }

/* ==================== 图表区域 ==================== */
.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  margin-bottom: 18px;
}

.chart-card {
  background: linear-gradient(135deg, rgba(15,29,53,0.9) 0%, rgba(18,32,66,0.85) 100%);
  border: 1px solid rgba(30,58,95,0.5);
  border-radius: 12px;
  padding: 20px;
  transition: border-color 0.25s ease;
  overflow: hidden;
}

.chart-card:hover {
  border-color: rgba(64,158,255,0.45);
}

.chart-card--wide {
  /* default */
}

.chart-card--narrow {
  /* default */
}

.chart-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.chart-card-header h3 {
  font-size: 0.9375rem;
  font-weight: 600;
  color: #c8d6e5;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.chart-card-header h3 .el-icon {
  color: #409eff;
}

.chart-card-tip {
  font-size: 0.75rem;
  color: #4a6078;
}

.chart-body {
  position: relative;
}

.chart-instance {
  width: 100%;
  height: 340px;
}

.chart-empty {
  height: 340px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #4a6078;
  font-size: 0.875rem;
}

/* ==================== 骨架屏 ==================== */
.skeleton {
  pointer-events: none;
}

.skeleton-pulse {
  background: linear-gradient(90deg, rgba(64,158,255,0.06) 25%, rgba(64,158,255,0.12) 50%, rgba(64,158,255,0.06) 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s ease-in-out infinite;
  border-radius: 6px;
}

.skeleton-label {
  width: 60%;
  height: 14px;
}

.skeleton-value {
  width: 80%;
  height: 32px;
  margin: 10px 0;
}

.skeleton-sub {
  width: 50%;
  height: 12px;
}

.skeleton-chart {
  pointer-events: none;
}

.skeleton-chart-area {
  width: 100%;
  height: 340px;
  border-radius: 8px;
}

@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ==================== 错误态 ==================== */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  gap: 16px;
}

.error-text {
  font-size: 0.9375rem;
  color: #8899aa;
  max-width: 400px;
  text-align: center;
}

/* ==================== 响应式 ==================== */
@media (max-width: 1200px) {
  .charts-row {
    grid-template-columns: 1fr;
  }

  .kpi-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .dashboard {
    padding: 16px 12px;
  }

  .dashboard-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-right {
    width: 100%;
    flex-direction: column;
  }

  .date-picker {
    width: 100%;
  }

  .kpi-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .kpi-card {
    padding: 14px 16px;
    gap: 12px;
  }

  .kpi-icon {
    width: 44px;
    height: 44px;
    border-radius: 10px;
  }

  .kpi-value {
    font-size: 1.25rem;
  }

  .chart-instance {
    height: 260px;
  }

  .chart-empty {
    height: 260px;
  }

  .skeleton-chart-area {
    height: 260px;
  }
}

@media (max-width: 480px) {
  .kpi-grid {
    grid-template-columns: 1fr;
  }

  .chart-instance {
    height: 220px;
  }

  .chart-empty {
    height: 220px;
  }

  .skeleton-chart-area {
    height: 220px;
  }
}

/* ==================== 滚动条美化 ==================== */
.dashboard::-webkit-scrollbar {
  width: 6px;
}

.dashboard::-webkit-scrollbar-track {
  background: rgba(255,255,255,0.02);
}

.dashboard::-webkit-scrollbar-thumb {
  background: rgba(64,158,255,0.2);
  border-radius: 3px;
}

.dashboard::-webkit-scrollbar-thumb:hover {
  background: rgba(64,158,255,0.35);
}
</style>
