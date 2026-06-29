<template>
  <div class="refund-status-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1 class="page-title">我的退款</h1>
      <p class="page-subtitle">查看退款申请的处理进度</p>
    </div>

    <!-- 加载态 -->
    <div v-if="loading" class="loading-area">
      <el-skeleton :rows="4" animated />
      <el-skeleton :rows="4" animated style="margin-top: 16px" />
    </div>

    <!-- 空态 -->
    <div v-else-if="list.length === 0" class="empty-area">
      <div class="empty-icon">
        <el-icon :size="64"><Receipt /></el-icon>
      </div>
      <p class="empty-title">暂无退款记录</p>
      <p class="empty-desc">您还没有发起过退款申请</p>
      <el-button type="primary" size="default" @click="goOrders" class="empty-btn">
        查看我的订单
      </el-button>
    </div>

    <!-- 退款列表 -->
    <div v-else class="list-area">
      <div
        v-for="item in list"
        :key="item.id"
        class="refund-card"
        :class="{ 'is-expanded': expandedId === item.id }"
        @click="toggleDetail(item)"
      >
        <!-- 卡片头部：概览 -->
        <div class="card-header">
          <div class="card-info">
            <span class="card-label">订单号</span>
            <span class="card-value order-no">{{ item.order_id }}</span>
            <el-divider direction="vertical" />
            <span class="card-label">退款金额</span>
            <span class="card-value amount">¥{{ formatAmount(item.amount) }}</span>
          </div>
          <div class="card-right">
            <el-tag
              :type="statusTagType(item.status)"
              :class="['status-tag', 'tag-' + item.status]"
              size="default"
              effect="plain"
              round
            >
              {{ statusLabel(item.status) }}
            </el-tag>
            <el-icon class="expand-icon" :class="{ rotated: expandedId === item.id }">
              <ArrowDown />
            </el-icon>
          </div>
        </div>

        <!-- 状态进度条 -->
        <div class="card-progress">
          <template v-if="item.status !== 'rejected'">
            <el-steps
              :active="activeStep(item.status)"
              :process-status="stepProcessStatus(item.status)"
              finish-status="success"
              align-center
            >
              <el-step title="已申请" :description="formatTime(item.apply_at)" />
              <el-step title="已审核" :description="item.status === 'applied' ? '等待中' : formatTime(item.processed_at)" />
              <el-step title="处理中" :description="item.status === 'processing' ? '进行中' : (item.status === 'applied' || item.status === 'approved' ? '等待中' : formatTime(item.processed_at))" />
              <el-step title="已完成" :description="item.status === 'completed' ? formatTime(item.completed_at) : '等待中'" />
            </el-steps>
          </template>
          <template v-else>
            <div class="rejected-notice">
              <el-icon :size="20"><CircleCloseFilled /></el-icon>
              <span>退款申请已被拒绝</span>
            </div>
          </template>
        </div>

        <!-- 展开详情 -->
        <el-collapse-transition>
          <div v-if="expandedId === item.id" class="card-detail">
            <el-divider />
            <div class="detail-grid">
              <div class="detail-item">
                <span class="detail-label">退款编号</span>
                <span class="detail-value">{{ item.id }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">申请时间</span>
                <span class="detail-value">{{ formatTime(item.apply_at) }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">当前状态</span>
                <el-tag :type="statusTagType(item.status)" size="small" round>
                  {{ statusLabel(item.status) }}
                </el-tag>
              </div>
              <div class="detail-item full-width">
                <span class="detail-label">退款原因</span>
                <span class="detail-value">{{ item.reason || '暂无' }}</span>
              </div>
              <div v-if="item.merchantNote" class="detail-item full-width">
                <span class="detail-label">商家备注</span>
                <span class="detail-value">{{ item.merchantNote }}</span>
              </div>
              <div v-if="item.evidence_images && item.evidence_images.length" class="detail-item full-width">
                <span class="detail-label">凭证图片</span>
                <div class="evidence-imgs">
                  <el-image
                    v-for="(url, idx) in item.evidence_images"
                    :key="idx"
                    :src="url"
                    :preview-src-list="item.evidence_images"
                    :initial-index="idx"
                    fit="cover"
                    class="evidence-thumb"
                    lazy
                  />
                </div>
              </div>
            </div>
          </div>
        </el-collapse-transition>
      </div>

      <!-- 分页 -->
      <div v-if="total > pageSize" class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          background
          @current-change="fetchList"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ArrowDown, Receipt, CircleCloseFilled } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { getRefundList, getRefundDetail } from '@/api/refund';

const router = useRouter();

/* ---- 状态 ---- */
const list = ref([]);
const loading = ref(true);
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);
const expandedId = ref(null);

/* ---- 工具函数 ---- */
const formatAmount = (val) => {
  const n = parseFloat(val);
  return Number.isFinite(n) ? n.toFixed(2) : '0.00';
};

const formatTime = (val) => {
  if (!val) return '';
  try {
    const d = new Date(val);
    if (isNaN(d.getTime())) return '';
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const h = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    return `${y}-${m}-${day} ${h}:${min}`;
  } catch {
    return '';
  }
};

const statusLabel = (s) => {
  const map = {
    applied: '待审核',
    approved: '已通过',
    rejected: '已拒绝',
    processing: '处理中',
    completed: '已完成'
  };
  return map[s] || s;
};

const statusTagType = (s) => {
  const map = {
    applied: 'warning',
    approved: 'success',
    rejected: 'danger',
    processing: '',
    completed: 'success'
  };
  return map[s] || 'info';
};

const activeStep = (s) => {
  const map = { applied: 0, approved: 1, processing: 2, completed: 3 };
  return map[s] ?? 0;
};

const stepProcessStatus = (s) => {
  if (s === 'completed') return 'success';
  if (s === 'processing') return 'finish';
  return 'process';
};

/* ---- 数据获取 ---- */
const fetchList = async () => {
  loading.value = true;
  try {
    const res = await getRefundList({ page: page.value, pageSize: pageSize.value });
    const data = res?.data || res;
    list.value = data?.list || [];
    total.value = data?.total || 0;
  } catch (err) {
    const msg = err?.response?.data?.message || '加载退款列表失败';
    ElMessage.error(msg);
    list.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
};

/* ---- 展开/收起详情 ---- */
const detailCache = ref({});

const toggleDetail = async (item) => {
  if (expandedId.value === item.id) {
    expandedId.value = null;
    return;
  }
  expandedId.value = item.id;

  /* 如有缓存则直接用，否则拉取详情补充字段 */
  if (detailCache.value[item.id]) {
    Object.assign(item, detailCache.value[item.id]);
    return;
  }

  try {
    const res = await getRefundDetail(item.id);
    const detail = res?.data || res;
    const merged = { ...item, ...detail };
    detailCache.value[item.id] = merged;
    /* 更新 list 中对应项 */
    const idx = list.value.findIndex(r => r.id === item.id);
    if (idx > -1) {
      list.value[idx] = merged;
    }
  } catch {
    /* 详情加载失败不阻断，使用列表已有字段 */
  }
};

/* ---- 导航 ---- */
const goOrders = () => {
  router.push({ name: 'OrderList' });
};

/* ---- 生命周期 ---- */
onMounted(() => {
  fetchList();
});
</script>

<style scoped>
/* ========== 页面级布局 ========== */
.refund-status-page {
  max-width: 900px;
  margin: 0 auto;
  padding: var(--app-space-xl, 24px) var(--app-space-base, 16px) var(--app-space-2xl, 32px);
}

/* ========== 页面头部 ========== */
.page-header {
  margin-bottom: var(--app-space-xl, 24px);
  text-align: center;
}

.page-title {
  font-size: var(--app-font-3xl, 1.5rem);
  font-weight: 700;
  color: var(--app-text-primary, #1a1a2e);
  margin: 0 0 var(--app-space-xs, 4px);
}

.page-subtitle {
  font-size: var(--app-font-base, 0.875rem);
  color: var(--app-text-secondary, #6b7280);
  margin: 0;
}

/* ========== 空态 ========== */
.empty-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--app-space-4xl, 48px) var(--app-space-base, 16px);
  text-align: center;
}

.empty-icon {
  color: #fed7aa;
  margin-bottom: var(--app-space-lg, 20px);
}

.empty-title {
  font-size: var(--app-font-lg, 1rem);
  font-weight: 600;
  color: var(--app-text-primary, #1a1a2e);
  margin: 0 0 var(--app-space-xs, 4px);
}

.empty-desc {
  font-size: var(--app-font-base, 0.875rem);
  color: var(--app-text-secondary, #6b7280);
  margin: 0 0 var(--app-space-lg, 20px);
}

.empty-btn {
  background: linear-gradient(135deg, #f97316, #ea580c) !important;
  border: none !important;
  font-weight: 600;
}

/* ========== 加载态 ========== */
.loading-area {
  padding: var(--app-space-base, 16px) 0;
}

/* ========== 列表区域 ========== */
.list-area {
  display: flex;
  flex-direction: column;
  gap: var(--app-space-md, 12px);
}

/* ========== 退款卡片 ========== */
.refund-card {
  background: var(--app-bg-container, #ffffff);
  border-radius: var(--app-radius-md, 12px);
  border: 1px solid var(--app-border-light, #e5e7eb);
  box-shadow: var(--app-shadow-level-1, 0 1px 3px rgba(0,0,0,0.06));
  padding: var(--app-space-base, 16px) var(--app-space-lg, 20px);
  cursor: pointer;
  transition: box-shadow 0.2s var(--app-ease-standard, cubic-bezier(0.4,0,0.2,1)),
              border-color 0.2s var(--app-ease-standard, cubic-bezier(0.4,0,0.2,1));
}

.refund-card:hover {
  border-color: #fed7aa;
  box-shadow: var(--app-shadow-level-2, 0 4px 12px rgba(0,0,0,0.08));
}

.refund-card.is-expanded {
  border-color: #f97316;
  box-shadow: 0 0 0 1px rgba(249, 115, 22, 0.2), var(--app-shadow-level-2, 0 4px 12px rgba(0,0,0,0.08));
}

/* ---- 卡片头部 ---- */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--app-space-sm, 8px);
}

.card-info {
  display: flex;
  align-items: center;
  gap: var(--app-space-sm, 8px);
  flex-wrap: wrap;
}

.card-label {
  font-size: var(--app-font-xs, 0.75rem);
  color: var(--app-text-secondary, #6b7280);
}

.card-value {
  font-size: var(--app-font-base, 0.875rem);
  font-weight: 500;
  color: var(--app-text-primary, #1a1a2e);
}

.order-no {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  color: var(--app-text-regular, #374151);
}

.amount {
  color: #f97316;
  font-weight: 700;
  font-size: var(--app-font-md, 0.9375rem);
}

.card-right {
  display: flex;
  align-items: center;
  gap: var(--app-space-sm, 8px);
}

/* 状态标签颜色覆盖 */
.status-tag.tag-applied {
  --el-color-warning: #f97316;
  --el-color-warning-light-3: #fdba74;
  --el-color-warning-light-5: #fed7aa;
  --el-color-warning-light-7: #ffedd5;
  --el-color-warning-light-9: #fff7ed;
  color: #c2410c;
  background: #fff7ed;
  border-color: #fed7aa;
}

.status-tag.tag-processing {
  --el-color-info: #f97316;
  color: #c2410c;
  background: #fff7ed;
  border-color: #fed7aa;
}

.status-tag.tag-rejected {
  color: #dc2626;
  background: #fef2f2;
  border-color: #fecaca;
}

.expand-icon {
  font-size: var(--app-font-lg, 1rem);
  color: var(--app-text-secondary, #6b7280);
  transition: transform 0.25s var(--app-ease-standard, cubic-bezier(0.4,0,0.2,1));
}

.expand-icon.rotated {
  transform: rotate(180deg);
}

/* ---- 进度条 ---- */
.card-progress {
  margin-top: var(--app-space-base, 16px);
  padding: var(--app-space-sm, 8px) 0;
}

.card-progress :deep(.el-step__title) {
  font-size: var(--app-font-xs, 0.75rem);
  font-weight: 600;
}

.card-progress :deep(.el-step__description) {
  font-size: var(--app-font-xs, 0.75rem);
  color: var(--app-text-secondary, #6b7280);
}

.card-progress :deep(.el-step__head.is-process),
.card-progress :deep(.el-step__head.is-finish) {
  color: #f97316;
  border-color: #f97316;
}

.card-progress :deep(.el-step__head.is-success) {
  color: #22c55e;
  border-color: #22c55e;
}

.card-progress :deep(.el-step__line) {
  background: #fed7aa;
}

.card-progress :deep(.el-step__line.is-finish),
.card-progress :deep(.el-step__line.is-success) {
  background: #f97316;
}

/* 拒绝提示 */
.rejected-notice {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--app-space-sm, 8px);
  color: #dc2626;
  font-weight: 600;
  font-size: var(--app-font-base, 0.875rem);
  padding: var(--app-space-md, 12px);
  background: #fef2f2;
  border-radius: var(--app-radius-base, 8px);
  border: 1px solid #fecaca;
}

/* ---- 展开详情 ---- */
.card-detail {
  overflow: hidden;
}

.card-detail .el-divider {
  margin: var(--app-space-md, 12px) 0;
}

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--app-space-md, 12px) var(--app-space-xl, 24px);
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.detail-item.full-width {
  grid-column: 1 / -1;
}

.detail-label {
  font-size: var(--app-font-xs, 0.75rem);
  color: var(--app-text-secondary, #6b7280);
}

.detail-value {
  font-size: var(--app-font-base, 0.875rem);
  color: var(--app-text-primary, #1a1a2e);
  word-break: break-all;
}

.evidence-imgs {
  display: flex;
  gap: var(--app-space-sm, 8px);
  flex-wrap: wrap;
  margin-top: var(--app-space-xs, 4px);
}

.evidence-thumb {
  width: 80px;
  height: 80px;
  border-radius: var(--app-radius-base, 8px);
  border: 1px solid var(--app-border-light, #e5e7eb);
  object-fit: cover;
  cursor: pointer;
  transition: transform 0.15s;
}

.evidence-thumb:hover {
  transform: scale(1.05);
}

/* ========== 分页 ========== */
.pagination-wrap {
  display: flex;
  justify-content: center;
  padding-top: var(--app-space-xl, 24px);
}

/* ========== 响应式 ========== */
@media (max-width: 768px) {
  .refund-status-page {
    padding: var(--app-space-base, 16px);
  }

  .card-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .card-right {
    width: 100%;
    justify-content: space-between;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }

  .page-title {
    font-size: var(--app-font-2xl, 1.25rem);
  }

  .card-progress :deep(.el-step__title) {
    font-size: 0.6875rem;
  }

  .card-progress :deep(.el-step__description) {
    font-size: 0.625rem;
  }
}
</style>
