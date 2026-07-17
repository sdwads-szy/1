<template>
  <div class="logistics-monitor">
    <!-- 顶部筛选栏 -->
    <div class="filter-bar">
      <div class="filter-bar-left">
        <el-button text @click="$router.push({name:'AdminDashboard'})" class="back-btn">
          <el-icon><ArrowLeft /></el-icon>
          返回后台
        </el-button>
        <h2 class="page-title">物流监控</h2>
      </div>
      <div class="filter-bar-right">
        <span class="last-updated">最后更新: {{ lastUpdated }}</span>
        <el-button
          size="small"
          :loading="loading"
          @click="refreshData"
        >
          <el-icon v-if="!loading"><Refresh /></el-icon>
          刷新数据
        </el-button>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="content-area">
      <!-- 加载骨架屏（首次加载） -->
      <template v-if="loading && !hasData">
        <div class="kpi-row">
          <div class="kpi-card kpi-skeleton" v-for="n in 2" :key="n">
            <div class="skeleton-bar skeleton-label"></div>
            <div class="skeleton-bar skeleton-value"></div>
          </div>
        </div>
        <div class="table-card">
          <div class="skeleton-bar skeleton-title"></div>
          <div class="skeleton-table">
            <div class="skeleton-bar skeleton-header"></div>
            <div class="skeleton-bar skeleton-row" v-for="r in 5" :key="r"></div>
          </div>
        </div>
      </template>

      <!-- 错误态 -->
      <template v-else-if="error">
        <div class="state-empty">
          <div class="state-icon error-icon">
            <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
              <rect x="8" y="8" width="48" height="48" rx="8" stroke="var(--color-error)" stroke-width="2" fill="none"/>
              <path d="M22 22L42 42M42 22L22 42" stroke="var(--color-error)" stroke-width="2.5" stroke-linecap="round"/>
            </svg>
          </div>
          <h3 class="state-title">数据加载失败</h3>
          <p class="state-desc">网络连接异常，请检查网络后重试</p>
          <el-button type="primary" @click="refreshData">重新加载</el-button>
        </div>
      </template>

      <!-- 空状态 -->
      <template v-else-if="hasData && isEmpty">
        <div class="state-empty">
          <div class="state-icon">
            <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
              <rect x="8" y="20" width="48" height="36" rx="4" stroke="var(--color-text-tertiary)" stroke-width="1.5" fill="none"/>
              <path d="M8 28L28 36L48 28" stroke="var(--color-text-tertiary)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              <circle cx="46" cy="18" r="9" fill="var(--color-text-tertiary)" opacity="0.3"/>
            </svg>
          </div>
          <h3 class="state-title">暂无异常</h3>
          <p class="state-desc">当前所有物流商接口运行正常，无异常记录</p>
          <el-button @click="refreshData">刷新数据</el-button>
        </div>
      </template>

      <!-- 正常数据 -->
      <template v-else>
        <!-- KPI 概览行 -->
        <div class="kpi-row">
          <div class="kpi-card">
            <span class="kpi-label">异常物流单数</span>
            <span
              class="kpi-value"
              :class="{ 'kpi-alert': monitorData.abnormalShipments > 0 }"
            >
              {{ formatNumber(monitorData.abnormalShipments) }}
            </span>
            <span class="kpi-sub">
              {{ monitorData.abnormalShipments > 0 ? '需关注处理' : '状态正常' }}
            </span>
          </div>
          <div class="kpi-card">
            <span class="kpi-label">查询超时次数</span>
            <span
              class="kpi-value"
              :class="{ 'kpi-alert': monitorData.timeoutQueries > 0 }"
            >
              {{ formatNumber(monitorData.timeoutQueries) }}
            </span>
            <span class="kpi-sub">
              {{ monitorData.timeoutQueries > 0 ? '接口响应偏慢' : '状态正常' }}
            </span>
          </div>
        </div>

        <!-- 最近异常记录表格 -->
        <div class="table-card">
          <h3 class="section-title">最近异常记录</h3>
          <el-table
            :data="monitorData.recentErrors"
            stripe
            style="width: 100%"
            empty-text="暂无异常记录"
            :header-cell-style="tableHeaderStyle"
            max-height="480"
          >
            <el-table-column prop="shipmentId" label="物流单ID" width="120" align="center" />
            <el-table-column prop="trackingNo" label="快递单号" min-width="180" show-overflow-tooltip />
            <el-table-column label="异常信息" min-width="200" show-overflow-tooltip>
              <template #default="{ row }">
                <el-tag
                  :type="getErrorTagType(row.error)"
                  size="small"
                  effect="plain"
                >
                  {{ row.error }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="时间" width="180" align="center">
              <template #default="{ row }">
                {{ formatTime(row.time) }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { ElMessage } from 'element-plus';
import { Refresh, ArrowLeft } from '@element-plus/icons-vue';
import { getLogisticsMonitor } from '@/api/admin-logistics';

// ========== 状态 ==========
const loading = ref(false);
const error = ref(false);
const monitorData = ref({
  abnormalShipments: 0,
  timeoutQueries: 0,
  recentErrors: []
});
const hasData = ref(false);
const lastUpdated = ref('—');

// 自动刷新定时器
let autoRefreshTimer = null;
const AUTO_REFRESH_INTERVAL = 30000;

// ========== 计算属性 ==========
const isEmpty = computed(() => {
  return (
    monitorData.value.abnormalShipments === 0 &&
    monitorData.value.timeoutQueries === 0 &&
    monitorData.value.recentErrors.length === 0
  );
});

// ========== 方法 ==========

/** 格式化大数值 */
function formatNumber(num) {
  if (num == null) return '—';
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万';
  }
  return num.toLocaleString();
}

/** 格式化时间 */
function formatTime(timeStr) {
  if (!timeStr) return '—';
  const d = new Date(timeStr);
  if (isNaN(d.getTime())) return timeStr;
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

/** 获取异常标签类型 */
function getErrorTagType(errorText) {
  if (!errorText) return 'info';
  if (errorText.includes('超时')) return 'warning';
  if (errorText.includes('失败') || errorText.includes('异常')) return 'danger';
  return 'info';
}

/** 表格表头样式 */
const tableHeaderStyle = {
  background: 'var(--color-bg-page)',
  color: 'var(--color-text-secondary)',
  fontSize: 'var(--font-size-sm)',
  fontWeight: 600
};

/** 刷新数据 */
async function refreshData() {
  loading.value = true;
  error.value = false;
  try {
    const res = await getLogisticsMonitor();
    if (res.data) {
      monitorData.value = {
        abnormalShipments: res.data.abnormalShipments ?? 0,
        timeoutQueries: res.data.timeoutQueries ?? 0,
        recentErrors: res.data.recentErrors ?? []
      };
      hasData.value = true;
    }
    updateTimestamp();
  } catch (err) {
    error.value = true;
    ElMessage.error('物流监控数据加载失败');
  } finally {
    loading.value = false;
  }
}

/** 更新时间戳 */
function updateTimestamp() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  lastUpdated.value = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
}

/** 启动自动刷新 */
function startAutoRefresh() {
  stopAutoRefresh();
  autoRefreshTimer = setInterval(() => {
    refreshData();
  }, AUTO_REFRESH_INTERVAL);
}

/** 停止自动刷新 */
function stopAutoRefresh() {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer);
    autoRefreshTimer = null;
  }
}

// ========== 生命周期 ==========
onMounted(() => {
  refreshData();
  startAutoRefresh();
});

onUnmounted(() => {
  stopAutoRefresh();
});
</script>

<style scoped>
.logistics-monitor {
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--space-xl);
  min-height: 100vh;
  background: var(--color-bg-page);
}

/* ========== 筛选栏 ========== */
.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 var(--space-xl);
  background: var(--color-bg-base);
  border-bottom: 1px solid var(--color-border);
  position: sticky;
  top: 0;
  z-index: var(--z-sticky, 100);
  border-radius: var(--radius-md) var(--radius-md) 0 0;
}

.filter-bar-left {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.page-title {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
  line-height: var(--line-height-tight);
}

.filter-bar-right {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.last-updated {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-feature-settings: "tnum";
  letter-spacing: 0.5px;
}

/* ========== 内容区 ========== */
.content-area {
  background: var(--color-bg-base);
  border-radius: 0 0 var(--radius-md) var(--radius-md);
  border: 1px solid var(--color-border);
  border-top: none;
  padding: var(--space-xl);
}

/* ========== KPI 卡片行 ========== */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-lg);
  margin-bottom: var(--space-xl);
}

.kpi-card {
  background: var(--page-analytics-kpi-bg, var(--color-bg-base));
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-md);
  min-height: 120px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: box-shadow var(--duration-fast) var(--ease-smooth), transform var(--duration-fast) var(--ease-smooth);
  box-shadow: var(--shadow-sm);
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
}

.kpi-value.kpi-alert {
  color: var(--page-analytics-alert, hsl(38, 95%, 60%));
}

.kpi-sub {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

/* ========== 表格卡片 ========== */
.table-card {
  background: var(--color-bg-base);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  box-shadow: var(--shadow-sm);
}

.section-title {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-md) 0;
  line-height: var(--line-height-tight);
}

/* ========== 状态占位 ========== */
.state-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-3xl) var(--space-xl);
  text-align: center;
}

.state-icon {
  margin-bottom: var(--space-lg);
  opacity: 0.6;
}

.state-icon.error-icon {
  opacity: 1;
}

.state-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-sm) 0;
}

.state-desc {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-lg) 0;
  max-width: 360px;
  line-height: var(--line-height-normal);
}

/* ========== 骨架屏 ========== */
.kpi-skeleton {
  gap: var(--space-sm);
  padding: var(--space-md);
}

.skeleton-bar {
  background: linear-gradient(
    90deg,
    var(--color-border) 0%,
    var(--color-bg-page) 50%,
    var(--color-border) 100%
  );
  background-size: 200% 100%;
  animation: shimmer 1.8s ease-in-out infinite;
  border-radius: var(--radius-sm);
}

.skeleton-label {
  width: 40%;
  height: 12px;
}

.skeleton-value {
  width: 70%;
  height: 28px;
}

.skeleton-title {
  width: 30%;
  height: 16px;
  margin-bottom: var(--space-md);
}

.skeleton-header {
  width: 100%;
  height: 40px;
  margin-bottom: var(--space-sm);
}

.skeleton-row {
  width: 100%;
  height: 40px;
  margin-bottom: var(--space-xs);
}

.skeleton-table {
  padding: var(--space-sm) 0;
}

@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* ========== 表格覆盖 ========== */
:deep(.el-table) {
  font-size: var(--font-size-sm);
}

:deep(.el-table th.el-table__cell) {
  background: var(--color-bg-page);
  color: var(--color-text-secondary);
  font-weight: 600;
  font-size: var(--font-size-sm);
  height: 40px;
}

:deep(.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell) {
  background: var(--color-bg-page);
}

:deep(.el-table__body tr:hover > td.el-table__cell) {
  background: var(--color-primary-50);
}

:deep(.el-table__header) {
  position: sticky;
  top: 0;
  z-index: calc(var(--z-sticky, 100) - 1);
}

/* ========== 响应式 ========== */
@media (max-width: 768px) {
  .logistics-monitor {
    padding: var(--space-md);
  }

  .filter-bar {
    flex-direction: column;
    height: auto;
    padding: var(--space-md);
    gap: var(--space-sm);
  }

  .filter-bar-right {
    width: 100%;
    justify-content: space-between;
  }

  .kpi-row {
    grid-template-columns: 1fr;
  }

  .content-area {
    padding: var(--space-md);
  }
}
.back-btn { color: var(--color-text-secondary); font-size: var(--font-size-sm); }

</style>
