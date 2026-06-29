<template>
  <div class="page-container">
    <!-- 顶部导航栏 -->
    <div class="detail-topbar">
      <el-button
        :icon="ArrowLeft"
        size="default"
        @click="goBack"
        class="back-btn"
      >
        返回审核队列
      </el-button>
      <el-divider direction="vertical" />
      <span class="topbar-title">商品审核详情</span>
      <el-tag v-if="product" :type="statusTagType(product.status)" size="small" effect="dark" class="topbar-status">
        {{ statusLabel(product.status) }}
      </el-tag>
    </div>

    <!-- 加载态 -->
    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="6" animated />
    </div>

    <!-- 错误态 -->
    <div v-else-if="loadError" class="error-state">
      <el-icon :size="48" color="var(--app-color-danger, #ef4444)"><WarningFilled /></el-icon>
      <p class="error-text">{{ loadError }}</p>
      <el-button type="primary" @click="fetchDetail">重新加载</el-button>
    </div>

    <!-- 主体内容 -->
    <template v-else-if="product">
      <div class="detail-grid">
        <!-- 左侧：商品信息 + SKU 列表 -->
        <div class="detail-main">
          <!-- 商品基本信息卡片 -->
          <div class="info-card">
            <div class="card-header">
              <h3 class="card-title">
                <el-icon :size="18"><Goods /></el-icon>
                商品信息
              </h3>
            </div>
            <div class="card-body">
              <div class="info-main-image">
                <el-image
                  v-if="product.main_image"
                  :src="product.main_image"
                  fit="contain"
                  class="main-image"
                  :preview-src-list="[product.main_image]"
                />
                <div v-else class="main-image-placeholder">
                  <el-icon :size="40"><PictureFilled /></el-icon>
                  <span>暂无主图</span>
                </div>
              </div>

              <div class="info-fields">
                <div class="info-row">
                  <span class="info-label">商品标题</span>
                  <span class="info-value info-value-title">{{ product.title }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">商品ID</span>
                  <span class="info-value">{{ product.id }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">所属店铺</span>
                  <span class="info-value">{{ product.shopName || '-' }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">商品类目</span>
                  <span class="info-value">{{ product.categoryName || '-' }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">提交时间</span>
                  <span class="info-value">{{ formatTime(product.created_at) }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">更新时间</span>
                  <span class="info-value">{{ formatTime(product.updated_at) }}</span>
                </div>
                <div class="info-row info-row-desc">
                  <span class="info-label">商品描述</span>
                  <div class="info-value desc-content" v-html="product.description || '暂无描述'"></div>
                </div>
              </div>
            </div>
          </div>

          <!-- SKU 列表卡片 -->
          <div class="info-card" v-if="skus && skus.length > 0">
            <div class="card-header">
              <h3 class="card-title">
                <el-icon :size="18"><List /></el-icon>
                SKU 规格（{{ skus.length }}）
              </h3>
            </div>
            <div class="card-body">
              <el-table :data="skus" size="small" stripe>
                <el-table-column prop="spec_combo" label="规格组合" min-width="180" show-overflow-tooltip />
                <el-table-column prop="price" label="价格" width="120" align="right">
                  <template #default="{ row }">
                    <span class="price-text">¥{{ parseFloat(row.price).toFixed(2) }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="stock" label="库存" width="100" align="center" />
                <el-table-column label="图片" width="100" align="center">
                  <template #default="{ row }">
                    <el-image
                      v-if="row.image"
                      :src="row.image"
                      fit="cover"
                      class="sku-thumb"
                      :preview-src-list="[row.image]"
                    />
                    <span v-else class="no-image-text">-</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>

          <!-- 快照历史卡片 -->
          <div class="info-card" v-if="snapshots && snapshots.length > 0">
            <div class="card-header">
              <h3 class="card-title">
                <el-icon :size="18"><Clock /></el-icon>
                编辑快照（{{ snapshots.length }}）
              </h3>
            </div>
            <div class="card-body">
              <el-timeline>
                <el-timeline-item
                  v-for="snap in snapshots"
                  :key="snap.id"
                  :timestamp="formatTime(snap.created_at)"
                  placement="top"
                  :type="snap.version === 1 ? 'primary' : 'info'"
                  size="normal"
                >
                  <div class="snapshot-item">
                    <el-tag size="small" :type="snap.version === 1 ? '' : 'info'">
                      v{{ snap.version }}
                    </el-tag>
                    <el-popover
                      placement="right"
                      :width="420"
                      trigger="click"
                      :title="`快照 v${snap.version}`"
                    >
                      <template #reference>
                        <el-button size="small" link type="primary">查看快照内容</el-button>
                      </template>
                      <div class="snapshot-json">
                        <pre>{{ JSON.stringify(snap.snapshot, null, 2) }}</pre>
                      </div>
                    </el-popover>
                  </div>
                </el-timeline-item>
              </el-timeline>
            </div>
          </div>
        </div>

        <!-- 右侧：审核日志 + 审核操作 -->
        <div class="detail-side">
          <!-- 审核操作卡片 -->
          <div class="info-card review-action-card" v-if="product.status === 'pending_review'">
            <div class="card-header card-header-accent">
              <h3 class="card-title">
                <el-icon :size="18"><EditPen /></el-icon>
                审核操作
              </h3>
            </div>
            <div class="card-body">
              <el-form
                ref="reviewFormRef"
                :model="reviewForm"
                :rules="reviewRules"
                label-position="top"
                size="default"
              >
                <el-form-item label="审核结果" prop="result">
                  <el-radio-group v-model="reviewForm.result">
                    <el-radio value="approved" class="review-radio-approve">
                      <span class="radio-label-approve">
                        <el-icon :size="16"><CircleCheck /></el-icon>
                        通过
                      </span>
                    </el-radio>
                    <el-radio value="rejected" class="review-radio-reject">
                      <span class="radio-label-reject">
                        <el-icon :size="16"><CircleClose /></el-icon>
                        驳回
                      </span>
                    </el-radio>
                  </el-radio-group>
                </el-form-item>

                <el-form-item label="审核意见" prop="reason">
                  <el-input
                    v-model="reviewForm.reason"
                    type="textarea"
                    :rows="4"
                    :placeholder="reviewForm.result === 'rejected' ? '请填写驳回原因（必填）' : '审核备注（选填）'"
                    maxlength="500"
                    show-word-limit
                  />
                </el-form-item>

                <el-form-item>
                  <el-button
                    type="primary"
                    :loading="submitting"
                    @click="handleReview"
                    style="width: 100%"
                    size="default"
                  >
                    <el-icon :size="16" v-if="!submitting"><Select /></el-icon>
                    {{ submitting ? '提交中...' : '确认审核' }}
                  </el-button>
                </el-form-item>
              </el-form>
            </div>
          </div>

          <!-- 审核已处理提示 -->
          <div class="info-card review-done-card" v-else-if="product.status === 'approved' || product.status === 'rejected'">
            <div class="card-body review-done-body">
              <el-icon :size="40" :color="product.status === 'approved' ? '#22c55e' : '#ef4444'">
                <CircleCheck v-if="product.status === 'approved'" />
                <CircleClose v-else />
              </el-icon>
              <p class="review-done-text">
                {{ product.status === 'approved' ? '该商品已审核通过' : '该商品已被驳回' }}
              </p>
              <p class="review-done-hint">
                可在左侧审核日志中查看详情
              </p>
            </div>
          </div>

          <!-- 审核日志卡片 -->
          <div class="info-card">
            <div class="card-header">
              <h3 class="card-title">
                <el-icon :size="18"><Document /></el-icon>
                审核日志
              </h3>
            </div>
            <div class="card-body">
              <template v-if="auditLogs && auditLogs.length > 0">
                <el-timeline>
                  <el-timeline-item
                    v-for="log in auditLogs"
                    :key="log.id"
                    :timestamp="formatTime(log.created_at)"
                    placement="top"
                    :type="log.result === 'approved' ? 'success' : 'danger'"
                    :icon="log.result === 'approved' ? CircleCheck : CircleClose"
                    size="normal"
                  >
                    <div class="audit-log-item">
                      <div class="audit-log-header">
                        <el-tag
                          :type="log.result === 'approved' ? 'success' : 'danger'"
                          size="small"
                          effect="dark"
                        >
                          {{ log.result === 'approved' ? '通过' : '驳回' }}
                        </el-tag>
                        <span class="auditor-name">审核员 #{{ log.auditor_id }}</span>
                      </div>
                      <p v-if="log.reason" class="audit-log-reason">{{ log.reason }}</p>
                      <p v-else class="audit-log-no-reason">无备注</p>
                    </div>
                  </el-timeline-item>
                </el-timeline>
              </template>
              <div v-else class="empty-state-sm">
                <el-icon :size="32" color="#d1d5db"><FolderOpened /></el-icon>
                <p class="empty-text-sm">暂无审核记录</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
// 平台后台 - 商品审核详情（含快照、审核日志、审核操作）
import { ref, reactive, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  ArrowLeft,
  Goods,
  List,
  Clock,
  EditPen,
  Document,
  PictureFilled,
  FolderOpened,
  CircleCheck,
  CircleClose,
  Select,
  WarningFilled
} from '@element-plus/icons-vue';
import { getAuditDetail, reviewProduct } from '@/api/admin/product';

const router = useRouter();
const route = useRoute();

// --- 状态 ---
const loading = ref(true);
const loadError = ref('');
const submitting = ref(false);
const product = ref(null);
const skus = ref([]);
const snapshots = ref([]);
const auditLogs = ref([]);

const reviewFormRef = ref(null);
const reviewForm = reactive({
  result: 'approved',
  reason: ''
});

// 驳回时原因必填
const reviewRules = {
  result: [{ required: true, message: '请选择审核结果', trigger: 'change' }],
  reason: [
    {
      validator: (_rule, value, callback) => {
        if (reviewForm.result === 'rejected' && !value?.trim()) {
          callback(new Error('驳回时必须填写审核意见'));
        } else {
          callback();
        }
      },
      trigger: 'blur'
    }
  ]
};

// --- 状态映射 ---
const STATUS_MAP = {
  draft: { label: '草稿', type: 'info' },
  pending_review: { label: '待审核', type: 'warning' },
  approved: { label: '已通过', type: 'success' },
  rejected: { label: '已驳回', type: 'danger' },
  listed: { label: '已上架', type: '' },
  delisted: { label: '已下架', type: 'info' }
};

function statusLabel(status) {
  return STATUS_MAP[status]?.label ?? status;
}

function statusTagType(status) {
  return STATUS_MAP[status]?.type ?? 'info';
}

// --- 工具方法 ---
function formatTime(ts) {
  if (!ts) return '-';
  const d = new Date(ts);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// --- 数据加载 ---
async function fetchDetail() {
  loading.value = true;
  loadError.value = '';

  const id = route.params.id;
  if (!id) {
    loadError.value = '缺少商品ID参数';
    loading.value = false;
    return;
  }

  try {
    const res = await getAuditDetail(id);
    const data = res.data ?? {};
    product.value = data.product ?? null;
    skus.value = data.skus ?? [];
    snapshots.value = data.snapshots ?? [];
    auditLogs.value = data.auditLogs ?? [];
  } catch (e) {
    loadError.value = e?.response?.data?.message || '加载商品详情失败';
  } finally {
    loading.value = false;
  }
}

// --- 审核操作 ---
async function handleReview() {
  if (!reviewFormRef.value) return;

  try {
    await reviewFormRef.value.validate();
  } catch {
    return;
  }

  const actionText = reviewForm.result === 'approved' ? '通过' : '驳回';

  try {
    await ElMessageBox.confirm(
      reviewForm.result === 'approved'
        ? '确认审核通过该商品？通过后商品将进入待上架状态。'
        : `确认驳回该商品？驳回后商家需重新编辑提交。`,
      `确认${actionText}`,
      {
        confirmButtonText: `确认${actionText}`,
        cancelButtonText: '取消',
        type: reviewForm.result === 'approved' ? 'success' : 'warning',
        distinguishCancelAndClose: true
      }
    );
  } catch {
    return;
  }

  submitting.value = true;
  try {
    const id = route.params.id;
    await reviewProduct(id, {
      result: reviewForm.result,
      reason: reviewForm.reason.trim() || undefined
    });

    ElMessage.success(`商品审核${actionText}成功`);

    // 刷新数据
    await fetchDetail();

    // 重置表单
    reviewForm.result = 'approved';
    reviewForm.reason = '';
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || `审核${actionText}失败，请重试`);
  } finally {
    submitting.value = false;
  }
}

// --- 导航 ---
function goBack() {
  router.push({ name: 'AdminProductAudit' });
}

// --- 生命周期 ---
onMounted(() => {
  fetchDetail();
});
</script>

<style scoped>
/* ========== 页面容器 ========== */
.page-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--app-space-xl, 24px);
}

/* ========== 顶部导航栏 ========== */
.detail-topbar {
  display: flex;
  align-items: center;
  gap: var(--app-space-sm, 8px);
  margin-bottom: var(--app-space-lg, 20px);
  padding: var(--app-space-md, 12px) var(--app-space-base, 16px);
  background: var(--app-bg-container, #fff);
  border-radius: var(--app-radius-base, 8px);
  box-shadow: var(--app-shadow-level-1);
}

.back-btn {
  color: #1e3a5f;
  font-weight: 500;
}

.topbar-title {
  font-size: var(--app-font-lg, 1rem);
  font-weight: 600;
  color: #1e3a5f;
}

.topbar-status {
  margin-left: auto;
}

/* ========== 加载/错误态 ========== */
.loading-state {
  background: var(--app-bg-container, #fff);
  border-radius: var(--app-radius-base, 8px);
  padding: var(--app-space-xl, 24px);
  box-shadow: var(--app-shadow-level-1);
}

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--app-space-base, 16px);
  padding: 64px 24px;
  background: var(--app-bg-container, #fff);
  border-radius: var(--app-radius-base, 8px);
  box-shadow: var(--app-shadow-level-1);
}

.error-text {
  font-size: var(--app-font-md, 0.9375rem);
  color: var(--app-text-secondary, #6b7280);
  margin: 0;
}

/* ========== 双栏布局 ========== */
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: var(--app-space-lg, 20px);
  align-items: start;
}

@media (max-width: 992px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
}

/* ========== 信息卡片 ========== */
.info-card {
  background: var(--app-bg-container, #fff);
  border-radius: var(--app-radius-base, 8px);
  box-shadow: var(--app-shadow-level-1);
  overflow: hidden;
  margin-bottom: var(--app-space-lg, 20px);
}

.info-card:last-child {
  margin-bottom: 0;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--app-space-base, 16px) var(--app-space-xl, 24px);
  border-bottom: 1px solid var(--app-border-light, #e5e7eb);
  background: #f8f9fb;
}

.card-header-accent {
  background: linear-gradient(135deg, #1e3a5f 0%, #2d5a8e 100%);
  border-bottom: none;
}

.card-header-accent .card-title {
  color: #fff;
}

.card-title {
  margin: 0;
  font-size: var(--app-font-lg, 1rem);
  font-weight: 600;
  color: #1e3a5f;
  display: flex;
  align-items: center;
  gap: var(--app-space-xs, 4px);
}

.card-body {
  padding: var(--app-space-xl, 24px);
}

/* ========== 商品信息 ========== */
.info-main-image {
  margin-bottom: var(--app-space-lg, 20px);
  text-align: center;
}

.main-image {
  max-width: 100%;
  max-height: 360px;
  border-radius: var(--app-radius-sm, 4px);
  border: 1px solid var(--app-border-light, #e5e7eb);
}

.main-image-placeholder {
  width: 100%;
  height: 200px;
  background: var(--app-bg-disabled, #f3f4f6);
  border-radius: var(--app-radius-sm, 4px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--app-space-sm, 8px);
  color: var(--app-text-disabled, #b0b7c3);
  font-size: var(--app-font-sm, 0.8125rem);
  border: 1px dashed var(--app-border-base, #d1d5db);
}

.info-fields {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.info-row {
  display: flex;
  align-items: flex-start;
  padding: var(--app-space-sm, 8px) 0;
  border-bottom: 1px solid var(--app-border-light, #e5e7eb);
}

.info-row:last-child {
  border-bottom: none;
}

.info-row-desc {
  flex-direction: column;
  gap: var(--app-space-xs, 4px);
}

.info-label {
  flex-shrink: 0;
  width: 100px;
  font-size: var(--app-font-sm, 0.8125rem);
  color: var(--app-text-secondary, #6b7280);
  font-weight: 500;
}

.info-value {
  flex: 1;
  font-size: var(--app-font-base, 0.875rem);
  color: var(--app-text-primary, #1a1a2e);
  word-break: break-all;
}

.info-value-title {
  font-weight: 600;
  font-size: var(--app-font-md, 0.9375rem);
}

.desc-content {
  line-height: 1.6;
  max-height: 200px;
  overflow-y: auto;
}

.desc-content :deep(img) {
  max-width: 100%;
}

/* ========== SKU 缩略图 ========== */
.sku-thumb {
  width: 48px;
  height: 48px;
  border-radius: var(--app-radius-sm, 4px);
  border: 1px solid var(--app-border-light, #e5e7eb);
}

.no-image-text {
  color: var(--app-text-disabled, #b0b7c3);
  font-size: var(--app-font-xs, 0.75rem);
}

.price-text {
  font-weight: 600;
  color: #e03131;
}

/* ========== 快照 ========== */
.snapshot-item {
  display: flex;
  align-items: center;
  gap: var(--app-space-sm, 8px);
}

.snapshot-json {
  max-height: 400px;
  overflow: auto;
}

.snapshot-json pre {
  margin: 0;
  font-size: var(--app-font-xs, 0.75rem);
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
}

/* ========== 审核操作 ========== */
.review-action-card {
  position: sticky;
  top: 80px;
}

.review-radio-approve,
.review-radio-reject {
  margin-right: var(--app-space-xl, 24px);
  height: 36px;
  line-height: 36px;
}

.radio-label-approve {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #22c55e;
  font-weight: 500;
}

.radio-label-reject {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #ef4444;
  font-weight: 500;
}

/* ========== 已审核提示 ========== */
.review-done-card {
  position: sticky;
  top: 80px;
}

.review-done-body {
  text-align: center;
  padding: var(--app-space-2xl, 32px) var(--app-space-xl, 24px);
}

.review-done-text {
  margin: var(--app-space-md, 12px) 0 4px;
  font-size: var(--app-font-md, 0.9375rem);
  font-weight: 600;
  color: var(--app-text-primary, #1a1a2e);
}

.review-done-hint {
  margin: 0;
  font-size: var(--app-font-sm, 0.8125rem);
  color: var(--app-text-secondary, #6b7280);
}

/* ========== 审核日志 ========== */
.audit-log-item {
  padding: 2px 0;
}

.audit-log-header {
  display: flex;
  align-items: center;
  gap: var(--app-space-sm, 8px);
  margin-bottom: var(--app-space-xs, 4px);
}

.auditor-name {
  font-size: var(--app-font-sm, 0.8125rem);
  color: var(--app-text-secondary, #6b7280);
}

.audit-log-reason {
  margin: var(--app-space-xs, 4px) 0 0;
  font-size: var(--app-font-base, 0.875rem);
  color: var(--app-text-regular, #374151);
  line-height: 1.5;
  padding: var(--app-space-sm, 8px);
  background: var(--app-bg-hover, #f9fafb);
  border-radius: var(--app-radius-sm, 4px);
}

.audit-log-no-reason {
  margin: var(--app-space-xs, 4px) 0 0;
  font-size: var(--app-font-sm, 0.8125rem);
  color: var(--app-text-disabled, #b0b7c3);
  font-style: italic;
}

/* ========== 空态（小） ========== */
.empty-state-sm {
  padding: 24px 0;
  text-align: center;
}

.empty-text-sm {
  margin: var(--app-space-sm, 8px) 0 0;
  font-size: var(--app-font-sm, 0.8125rem);
  color: var(--app-text-disabled, #b0b7c3);
}

/* ========== 响应式 ========== */
@media (max-width: 768px) {
  .page-container {
    padding: var(--app-space-base, 16px);
  }

  .detail-topbar {
    flex-wrap: wrap;
  }

  .card-body {
    padding: var(--app-space-base, 16px);
  }

  .info-label {
    width: 80px;
  }

  .review-action-card,
  .review-done-card {
    position: static;
  }
}
</style>
