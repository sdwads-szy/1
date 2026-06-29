<template>
  <div class="admin-detail-page">
    <!-- 面包屑 -->
    <div class="breadcrumb-bar">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ name: 'AdminMerchantList' }">
          <el-icon><Shop /></el-icon>
          商家审核
        </el-breadcrumb-item>
        <el-breadcrumb-item>商家详情</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- 加载态 -->
    <div v-if="loading" class="loading-card">
      <el-skeleton :rows="6" animated />
    </div>

    <!-- 错误态 -->
    <div v-else-if="loadError" class="error-card">
      <el-result icon="error" title="加载失败" :sub-title="loadError">
        <template #extra>
          <el-button type="primary" @click="fetchDetail">重新加载</el-button>
          <el-button @click="goBack">返回列表</el-button>
        </template>
      </el-result>
    </div>

    <!-- 主体内容 -->
    <template v-else>
      <!-- 店铺信息卡片 -->
      <div class="info-card">
        <div class="card-header">
          <div class="card-header-left">
            <el-icon class="card-icon"><Document /></el-icon>
            <h3 class="card-title">店铺信息</h3>
          </div>
          <el-tag
            :type="shopStatusTag(shop.status)"
            size="default"
            effect="plain"
          >
            {{ shopStatusLabel(shop.status) }}
          </el-tag>
        </div>

        <div class="card-body shop-info-grid">
          <div class="info-item">
            <span class="info-label">商家ID</span>
            <span class="info-value mono">{{ shop.id }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">店铺名称</span>
            <span class="info-value strong">{{ shop.name || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">关联用户ID</span>
            <span class="info-value mono">{{ shop.user_id }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">佣金比例</span>
            <span class="info-value">{{ formatPercent(shop.commission_rate) }}</span>
          </div>
          <div class="info-item full-width" v-if="shop.description">
            <span class="info-label">店铺简介</span>
            <span class="info-value">{{ shop.description }}</span>
          </div>
          <div class="info-item" v-if="shop.logo">
            <span class="info-label">店铺Logo</span>
            <div class="info-value">
              <el-image
                :src="shop.logo"
                fit="cover"
                class="shop-logo-img"
                :preview-src-list="[shop.logo]"
                preview-teleported
              >
                <template #error>
                  <div class="image-error">
                    <el-icon><PictureFilled /></el-icon>
                  </div>
                </template>
              </el-image>
            </div>
          </div>
          <div class="info-item">
            <span class="info-label">注册时间</span>
            <span class="info-value">{{ formatDateTime(shop.created_at) }}</span>
          </div>
        </div>
      </div>

      <!-- 资质信息卡片 -->
      <div class="info-card">
        <div class="card-header">
          <div class="card-header-left">
            <el-icon class="card-icon"><Checked /></el-icon>
            <h3 class="card-title">资质信息</h3>
          </div>
          <el-tag
            :type="qualStatusTag(qualification.status)"
            size="default"
            effect="plain"
          >
            {{ qualStatusLabel(qualification.status) }}
          </el-tag>
        </div>

        <div class="card-body qual-grid">
          <!-- 营业执照 -->
          <div class="qual-image-item">
            <div class="qual-label">营业执照</div>
            <div class="qual-image-wrapper">
              <el-image
                :src="qualification.business_license"
                fit="contain"
                class="qual-img"
                :preview-src-list="[qualification.business_license]"
                preview-teleported
              >
                <template #error>
                  <div class="image-error">
                    <el-icon><PictureFilled /></el-icon>
                    <span>加载失败</span>
                  </div>
                </template>
              </el-image>
            </div>
          </div>

          <!-- 法人身份证 -->
          <div class="qual-image-item">
            <div class="qual-label">法人身份证</div>
            <div class="qual-image-wrapper">
              <el-image
                :src="qualification.legal_person_id"
                fit="contain"
                class="qual-img"
                :preview-src-list="[qualification.legal_person_id]"
                preview-teleported
              >
                <template #error>
                  <div class="image-error">
                    <el-icon><PictureFilled /></el-icon>
                    <span>加载失败</span>
                  </div>
                </template>
              </el-image>
            </div>
          </div>

          <!-- 银行账户 -->
          <div class="info-item full-width">
            <span class="info-label">银行账户</span>
            <span class="info-value mono masked">
              {{ qualification.bank_account || '***' }}
              <el-tooltip
                content="银行账户已加密存储"
                placement="top"
              >
                <el-icon class="lock-icon"><Lock /></el-icon>
              </el-tooltip>
            </span>
          </div>

          <!-- OCR识别结果 -->
          <div class="info-item full-width" v-if="qualification.ocrResult">
            <span class="info-label">OCR识别结果</span>
            <div class="ocr-result-box">
              <pre class="ocr-content">{{ formatOCR(qualification.ocrResult) }}</pre>
            </div>
          </div>

          <!-- 审核信息 -->
          <div class="info-item" v-if="qualification.reviewer_id">
            <span class="info-label">审核人ID</span>
            <span class="info-value mono">{{ qualification.reviewer_id }}</span>
          </div>
          <div class="info-item full-width" v-if="qualification.review_note">
            <span class="info-label">审核备注</span>
            <span class="info-value review-note">{{ qualification.review_note }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">提交时间</span>
            <span class="info-value">{{ formatDateTime(qualification.created_at) }}</span>
          </div>
        </div>
      </div>

      <!-- 审核操作卡片 -->
      <div class="action-card" v-if="qualification.status === 'pending'">
        <div class="card-header">
          <div class="card-header-left">
            <el-icon class="card-icon"><EditPen /></el-icon>
            <h3 class="card-title">资质审核</h3>
          </div>
        </div>

        <div class="card-body">
          <el-form
            ref="reviewFormRef"
            :model="reviewForm"
            :rules="reviewRules"
            label-width="80px"
            label-position="top"
            class="review-form"
          >
            <el-form-item label="审核结果" prop="result">
              <el-radio-group v-model="reviewForm.result">
                <el-radio value="approved" class="review-radio">
                  <span class="radio-label approved-label">
                    <el-icon><CircleCheckFilled /></el-icon>
                    通过
                  </span>
                </el-radio>
                <el-radio value="rejected" class="review-radio">
                  <span class="radio-label rejected-label">
                    <el-icon><CircleCloseFilled /></el-icon>
                    驳回
                  </span>
                </el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item
              label="审核备注"
              prop="note"
              v-if="reviewForm.result === 'rejected'"
            >
              <el-input
                v-model="reviewForm.note"
                type="textarea"
                :rows="3"
                placeholder="请输入驳回原因…"
                maxlength="500"
                show-word-limit
              />
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                :loading="reviewing"
                @click="handleReview"
                class="submit-btn"
              >
                {{ reviewing ? '提交中…' : '确认审核' }}
              </el-button>
              <el-button @click="resetReviewForm" :disabled="reviewing">
                重置
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </div>

      <!-- 激活操作卡片 -->
      <div
        class="action-card"
        v-if="shop.status === 'pending' && qualification.status === 'approved'"
      >
        <div class="card-header">
          <div class="card-header-left">
            <el-icon class="card-icon"><VideoPlay /></el-icon>
            <h3 class="card-title">激活店铺</h3>
          </div>
        </div>

        <div class="card-body">
          <p class="activate-hint">
            资质已审核通过，可激活该商家店铺。激活后商家即可正常经营。
          </p>
          <el-button
            type="success"
            :loading="activating"
            @click="handleActivate"
            size="large"
          >
            <el-icon><VideoPlay /></el-icon>
            {{ activating ? '激活中…' : '激活店铺' }}
          </el-button>
        </div>
      </div>

      <!-- 底部操作栏 -->
      <div class="bottom-bar">
        <el-button @click="goBack" size="default">
          <el-icon><ArrowLeft /></el-icon>
          返回列表
        </el-button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  Shop,
  Document,
  Checked,
  EditPen,
  VideoPlay,
  ArrowLeft,
  PictureFilled,
  Lock,
  CircleCheckFilled,
  CircleCloseFilled
} from '@element-plus/icons-vue';
import {
  getMerchantDetail,
  reviewMerchant,
  activateMerchant
} from '@/api/admin/merchant.js';

const route = useRoute();
const router = useRouter();

// 状态
const loading = ref(true);
const loadError = ref('');
const reviewing = ref(false);
const activating = ref(false);
const reviewFormRef = ref(null);

const shop = ref({});
const qualification = ref({});

const reviewForm = reactive({
  result: '',
  note: ''
});

const reviewRules = {
  result: [
    { required: true, message: '请选择审核结果', trigger: 'change' }
  ],
  note: [
    { required: true, message: '驳回时必须填写审核备注', trigger: 'blur' },
    { min: 5, message: '备注不少于5个字符', trigger: 'blur' }
  ]
};

// 店铺状态映射
const shopStatusMap = {
  pending: { label: '待审核', tag: 'warning' },
  active: { label: '已激活', tag: 'success' },
  frozen: { label: '已冻结', tag: 'info' },
  cleared: { label: '已清退', tag: 'danger' }
};

function shopStatusLabel(status) {
  return shopStatusMap[status]?.label || status || '-';
}

function shopStatusTag(status) {
  return shopStatusMap[status]?.tag || 'info';
}

// 资质状态映射
const qualStatusMap = {
  pending: { label: '待审核', tag: 'warning' },
  approved: { label: '已通过', tag: 'success' },
  rejected: { label: '已驳回', tag: 'danger' }
};

function qualStatusLabel(status) {
  return qualStatusMap[status]?.label || status || '-';
}

function qualStatusTag(status) {
  return qualStatusMap[status]?.tag || 'info';
}

// 日期格式化
function formatDateTime(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const h = String(d.getHours()).padStart(2, '0');
  const min = String(d.getMinutes()).padStart(2, '0');
  const s = String(d.getSeconds()).padStart(2, '0');
  return `${y}-${m}-${day} ${h}:${min}:${s}`;
}

// 佣金格式化
function formatPercent(val) {
  if (val === null || val === undefined) return '-';
  return parseFloat(val).toFixed(2) + '%';
}

// OCR结果格式化
function formatOCR(ocr) {
  if (!ocr) return '';
  if (typeof ocr === 'string') {
    try {
      const parsed = JSON.parse(ocr);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return ocr;
    }
  }
  return JSON.stringify(ocr, null, 2);
}

// 加载详情
async function fetchDetail() {
  loading.value = true;
  loadError.value = '';
  try {
    const id = route.params.id;
    if (!id) {
      loadError.value = '缺少商家ID参数';
      loading.value = false;
      return;
    }
    const res = await getMerchantDetail(Number(id));
    if (res && res.data) {
      shop.value = res.data.shop || {};
      qualification.value = res.data.qualification || {};
    } else {
      loadError.value = '未找到该商家信息';
    }
  } catch (err) {
    const msg = err?.response?.data?.message || err?.message || '网络异常';
    loadError.value = msg;
  } finally {
    loading.value = false;
  }
}

// 审核操作
async function handleReview() {
  const valid = await reviewFormRef.value?.validate().catch(() => false);
  if (!valid) return;

  // 驳回时需填写备注
  if (reviewForm.result === 'rejected' && !reviewForm.note) {
    ElMessage.warning('驳回时必须填写审核备注');
    return;
  }

  const actionText = reviewForm.result === 'approved' ? '通过' : '驳回';
  try {
    await ElMessageBox.confirm(
      `确认${actionText}该商家的资质审核？`,
      '审核确认',
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

  reviewing.value = true;
  try {
    const id = route.params.id;
    const payload = { result: reviewForm.result };
    if (reviewForm.note) {
      payload.note = reviewForm.note;
    }
    await reviewMerchant(Number(id), payload);
    ElMessage.success(`资质审核已${actionText}`);
    resetReviewForm();
    await fetchDetail();
  } catch (err) {
    const msg = err?.response?.data?.message || `审核${actionText}失败，请稍后重试`;
    ElMessage.error(msg);
  } finally {
    reviewing.value = false;
  }
}

// 激活操作
async function handleActivate() {
  try {
    await ElMessageBox.confirm(
      '确认激活该商家店铺？激活后商家即可正常经营。',
      '激活确认',
      {
        confirmButtonText: '确认激活',
        cancelButtonText: '取消',
        type: 'success',
        distinguishCancelAndClose: true
      }
    );
  } catch {
    return;
  }

  activating.value = true;
  try {
    const id = route.params.id;
    await activateMerchant(Number(id));
    ElMessage.success('店铺已成功激活');
    await fetchDetail();
  } catch (err) {
    const msg = err?.response?.data?.message || '激活失败，请稍后重试';
    ElMessage.error(msg);
  } finally {
    activating.value = false;
  }
}

// 重置审核表单
function resetReviewForm() {
  reviewForm.result = '';
  reviewForm.note = '';
  reviewFormRef.value?.resetFields();
}

// 返回列表
function goBack() {
  router.push({ name: 'AdminMerchantList' });
}

onMounted(() => {
  fetchDetail();
});
</script>

<style scoped>
/* ===== 页面容器 ===== */
.admin-detail-page {
  padding: var(--app-space-xl, 24px);
  min-height: calc(100vh - 56px);
  background: #f0f2f5;
  max-width: 960px;
  margin: 0 auto;
}

/* ===== 面包屑 ===== */
.breadcrumb-bar {
  margin-bottom: 20px;
}

.breadcrumb-bar :deep(.el-breadcrumb__inner) {
  color: #475569;
  font-size: 14px;
  font-weight: 500;
  transition: color 0.15s;
}

.breadcrumb-bar :deep(.el-breadcrumb__inner.is-link:hover) {
  color: #1e3a5f;
}

.breadcrumb-bar :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
  color: #1e293b;
  font-weight: 600;
}

/* ===== 加载/错误卡片 ===== */
.loading-card,
.error-card {
  background: #ffffff;
  border-radius: var(--app-radius-md, 12px);
  box-shadow: var(--app-shadow-level-1, 0 1px 3px rgba(0,0,0,0.06));
  padding: 32px 24px;
}

/* ===== 信息卡片通用 ===== */
.info-card,
.action-card {
  background: #ffffff;
  border-radius: var(--app-radius-md, 12px);
  box-shadow: var(--app-shadow-level-1, 0 1px 3px rgba(0,0,0,0.06));
  margin-bottom: 16px;
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid #f0f2f5;
  background: #fafbfd;
}

.card-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.card-icon {
  font-size: 18px;
  color: #1e3a5f;
}

.card-title {
  margin: 0;
  font-size: var(--app-font-lg, 1rem);
  font-weight: 600;
  color: #1e293b;
}

.card-body {
  padding: 20px 24px;
}

/* ===== 店铺信息网格 ===== */
.shop-info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px 32px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item.full-width {
  grid-column: 1 / -1;
}

.info-label {
  font-size: var(--app-font-sm, 0.8125rem);
  color: var(--app-text-secondary, #6b7280);
  font-weight: 500;
}

.info-value {
  font-size: var(--app-font-base, 0.875rem);
  color: var(--app-text-regular, #374151);
  word-break: break-all;
}

.info-value.strong {
  font-weight: 600;
  color: var(--app-text-primary, #1a1a2e);
  font-size: var(--app-font-md, 0.9375rem);
}

.info-value.mono {
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 13px;
}

.info-value.masked {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--app-text-secondary, #6b7280);
}

.lock-icon {
  font-size: 14px;
  color: #94a3b8;
  cursor: help;
}

.shop-logo-img {
  width: 80px;
  height: 80px;
  border-radius: var(--app-radius-base, 8px);
  border: 1px solid var(--app-border-light, #e5e7eb);
  object-fit: cover;
}

.image-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  background: #f8fafc;
  color: #94a3b8;
  font-size: 24px;
  gap: 4px;
}

/* ===== 资质信息 ===== */
.qual-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px 24px;
}

.qual-image-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.qual-label {
  font-size: var(--app-font-sm, 0.8125rem);
  color: var(--app-text-secondary, #6b7280);
  font-weight: 500;
}

.qual-image-wrapper {
  border: 1px solid var(--app-border-light, #e5e7eb);
  border-radius: var(--app-radius-base, 8px);
  overflow: hidden;
  background: #f8fafc;
  height: 220px;
}

.qual-img {
  width: 100%;
  height: 100%;
}

/* OCR结果 */
.ocr-result-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: var(--app-radius-sm, 4px);
  padding: 12px 16px;
  max-height: 200px;
  overflow-y: auto;
}

.ocr-content {
  margin: 0;
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.6;
  color: #334155;
  white-space: pre-wrap;
  word-break: break-all;
}

.review-note {
  background: #fffbeb;
  border-left: 3px solid #f59e0b;
  padding: 10px 14px;
  border-radius: 0 4px 4px 0;
  color: #92400e;
}

/* ===== 审核表单 ===== */
.review-form {
  max-width: 520px;
}

.review-radio {
  margin-right: 32px;
}

.review-radio :deep(.el-radio__label) {
  padding-left: 4px;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 500;
}

.approved-label {
  color: #22c55e;
}

.rejected-label {
  color: #ef4444;
}

.submit-btn {
  min-width: 120px;
}

/* ===== 激活卡片 ===== */
.activate-hint {
  margin: 0 0 16px 0;
  font-size: var(--app-font-base, 0.875rem);
  color: var(--app-text-secondary, #6b7280);
  line-height: 1.6;
}

/* ===== 底部操作栏 ===== */
.bottom-bar {
  display: flex;
  justify-content: flex-start;
  padding: 4px 0;
  margin-top: 4px;
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .admin-detail-page {
    padding: 12px;
  }

  .shop-info-grid,
  .qual-grid {
    grid-template-columns: 1fr;
  }

  .card-body {
    padding: 16px;
  }

  .card-header {
    padding: 12px 16px;
    flex-wrap: wrap;
    gap: 8px;
  }

  .qual-image-wrapper {
    height: 180px;
  }

  .review-radio {
    margin-right: 16px;
  }
}
</style>
