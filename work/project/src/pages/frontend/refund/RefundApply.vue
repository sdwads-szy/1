<template>
  <div class="refund-apply-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <el-button
        class="back-btn"
        :icon="ArrowLeft"
        text
        size="default"
        @click="goBack"
      >
        返回订单详情
      </el-button>
      <div class="header-content">
        <h1 class="page-title">申请退款</h1>
        <p class="page-subtitle">
          订单号：<span class="order-id-highlight">{{ orderId }}</span>
        </p>
      </div>
    </div>

    <!-- 表单卡片 -->
    <div class="form-card">
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        hide-required-asterisk
        @submit.prevent
      >
        <el-form-item label="退款原因" prop="reason">
          <el-input
            v-model="form.reason"
            type="textarea"
            :rows="4"
            maxlength="500"
            show-word-limit
            placeholder="请详细描述退款原因，以便商家快速处理（不超过500字）"
          />
        </el-form-item>

        <el-form-item label="退款金额（元）" prop="amount">
          <el-input-number
            v-model="form.amount"
            :precision="2"
            :min="0.01"
            :max="999999.99"
            :step="0.01"
            placeholder="请输入退款金额"
            controls-position="right"
            style="width: 100%"
          />
          <div class="form-tip">
            <el-icon><InfoFilled /></el-icon>
            <span>退款金额不可超过原订单实付金额，请如实填写</span>
          </div>
        </el-form-item>

        <el-form-item label="凭证图片（选填）" prop="evidence_images">
          <el-upload
            ref="uploadRef"
            v-model:file-list="fileList"
            list-type="picture-card"
            :auto-upload="true"
            :limit="6"
            :http-request="customUpload"
            :on-exceed="handleExceed"
            :on-remove="handleRemove"
            :on-error="handleUploadError"
            :before-upload="beforeUpload"
            accept="image/jpeg,image/png,image/webp"
          >
            <el-icon><Plus /></el-icon>
            <template #tip>
              <div class="form-tip" style="margin-top: 8px">
                <el-icon><InfoFilled /></el-icon>
                <span>最多上传 6 张图片，支持 JPG / PNG / WebP 格式，单张不超过 5MB</span>
              </div>
            </template>
          </el-upload>
        </el-form-item>

        <el-divider />

        <!-- 操作按钮 -->
        <div class="form-actions">
          <el-button size="large" @click="goBack" :disabled="submitting">
            取消
          </el-button>
          <el-button
            type="primary"
            size="large"
            :loading="submitting"
            @click="handleSubmit"
            class="submit-btn"
          >
            {{ submitting ? '提交中...' : '提交退款申请' }}
          </el-button>
        </div>
      </el-form>
    </div>

    <!-- 温馨提示 -->
    <div class="tips-card">
      <div class="tips-header">
        <el-icon><Warning /></el-icon>
        <span>温馨提示</span>
      </div>
      <ul class="tips-list">
        <li>提交申请后，商家将在 1-3 个工作日内审核</li>
        <li>请确保退款原因和凭证真实有效，虚假申请可能导致账号受限</li>
        <li>审核通过后，退款将原路返回至您的支付账户</li>
        <li>如有疑问，可联系平台客服获取帮助</li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ArrowLeft, Plus, InfoFilled, Warning } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { createRefund } from '@/api/refund';
import request from '@/utils/request';

const route = useRoute();
const router = useRouter();

const formRef = ref(null);
const uploadRef = ref(null);
const submitting = ref(false);
const fileList = ref([]);
const evidenceUrls = ref([]);

/* ---- 路由参数 ---- */
const orderId = computed(() => {
  const id = route.params.orderId;
  if (!id) {
    ElMessage.error('缺少订单参数，请从订单详情页进入');
    return '';
  }
  return String(id);
});

/* ---- 表单 ---- */
const form = reactive({
  reason: '',
  amount: null,
  evidence_images: []
});

const validateAmount = (_rule, value, callback) => {
  if (value === null || value === undefined || value === '') {
    callback(new Error('请输入退款金额'));
  } else if (!Number.isFinite(Number(value)) || Number(value) <= 0) {
    callback(new Error('退款金额必须大于 0'));
  } else {
    callback();
  }
};

const rules = {
  reason: [
    { required: true, message: '请填写退款原因', trigger: 'blur' },
    { min: 5, message: '退款原因不少于 5 个字', trigger: 'blur' },
    { max: 500, message: '退款原因不超过 500 个字', trigger: 'blur' }
  ],
  amount: [
    { required: true, validator: validateAmount, trigger: 'blur' }
  ]
};

/* ---- 图片上传 ---- */
const beforeUpload = (file) => {
  const isValidType = ['image/jpeg', 'image/png', 'image/webp'].includes(file.type);
  if (!isValidType) {
    ElMessage.error('仅支持 JPG / PNG / WebP 格式的图片');
    return false;
  }
  const isLt5M = file.size / 1024 / 1024 < 5;
  if (!isLt5M) {
    ElMessage.error('图片大小不能超过 5MB');
    return false;
  }
  return true;
};

const customUpload = async (options) => {
  const { file, onSuccess, onError } = options;
  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await request({
      url: '/upload',
      method: 'post',
      data: formData,
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    const url = res?.data?.url || res?.url || '';
    if (url) {
      evidenceUrls.value.push(url);
    }
    onSuccess(res);
  } catch (err) {
    ElMessage.error(err?.response?.data?.message || '图片上传失败，请重试');
    onError(err);
  }
};

const handleRemove = (uploadFile) => {
  const removedUrl = uploadFile?.response?.data?.url
    || uploadFile?.response?.url
    || uploadFile?.url;
  if (removedUrl) {
    const idx = evidenceUrls.value.indexOf(removedUrl);
    if (idx > -1) evidenceUrls.value.splice(idx, 1);
  }
};

const handleExceed = () => {
  ElMessage.warning('最多上传 6 张凭证图片');
};

const handleUploadError = () => {
  ElMessage.error('图片上传失败，请重试');
};

/* ---- 导航 ---- */
const goBack = () => {
  if (window.history.length > 1) {
    router.back();
  } else {
    router.push({ name: 'OrderDetail', params: { orderId: orderId.value } });
  }
};

/* ---- 提交 ---- */
const handleSubmit = async () => {
  if (submitting.value) return;

  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;

  /* 二次确认 */
  try {
    await ElMessageBox.confirm(
      `确认提交退款申请？金额：¥${Number(form.amount).toFixed(2)}`,
      '确认退款',
      {
        confirmButtonText: '确认提交',
        cancelButtonText: '再想想',
        type: 'warning',
        confirmButtonClass: 'el-button--warning'
      }
    );
  } catch {
    return;
  }

  /* 检查是否有未完成的上传 */
  const uploadingFiles = fileList.value.filter(f => f.status === 'uploading');
  if (uploadingFiles.length > 0) {
    ElMessage.warning('请等待图片上传完成后再提交');
    return;
  }

  submitting.value = true;

  try {
    await createRefund({
      order_id: Number(orderId.value),
      reason: form.reason.trim(),
      amount: Number(form.amount),
      evidence_images: [...evidenceUrls.value]
    });

    ElMessage.success('退款申请已提交，请耐心等待商家审核');

    /* 跳转到退款状态页 */
    setTimeout(() => {
      router.push({ name: 'RefundStatus' });
    }, 800);
  } catch (err) {
    const msg = err?.response?.data?.message || '提交失败，请重试';
    ElMessage.error(msg);
  } finally {
    submitting.value = false;
  }
};

onMounted(() => {
  if (!orderId.value) {
    ElMessage.error('缺少订单参数');
    router.replace({ name: 'Home' });
  }
});
</script>

<style scoped>
/* ========== 页面级布局 ========== */
.refund-apply-page {
  max-width: 720px;
  margin: 0 auto;
  padding: var(--app-space-xl, 24px) var(--app-space-base, 16px) var(--app-space-2xl, 32px);
}

/* ========== 页面头部 ========== */
.page-header {
  margin-bottom: var(--app-space-xl, 24px);
}

.back-btn {
  margin-bottom: var(--app-space-md, 12px);
  padding-left: 0;
  color: var(--app-text-secondary, #6b7280);
  font-size: var(--app-font-base, 0.875rem);
  transition: color 0.15s var(--app-ease-standard, cubic-bezier(0.4,0,0.2,1));
}

.back-btn:hover {
  color: #f97316;
}

.header-content {
  padding-left: 4px;
}

.page-title {
  font-size: var(--app-font-3xl, 1.5rem);
  font-weight: 700;
  color: var(--app-text-primary, #1a1a2e);
  margin: 0 0 var(--app-space-xs, 4px);
  line-height: 1.25;
}

.page-subtitle {
  font-size: var(--app-font-base, 0.875rem);
  color: var(--app-text-secondary, #6b7280);
  margin: 0;
}

.order-id-highlight {
  color: #f97316;
  font-weight: 600;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

/* ========== 表单卡片 ========== */
.form-card {
  background: var(--app-bg-container, #ffffff);
  border-radius: var(--app-radius-md, 12px);
  padding: var(--app-space-xl, 24px) var(--app-space-xl, 24px) var(--app-space-base, 16px);
  box-shadow: var(--app-shadow-level-1, 0 1px 3px rgba(0,0,0,0.06));
  border: 1px solid var(--app-border-light, #e5e7eb);
}

/* ========== 表单微调 ========== */
.form-card :deep(.el-form-item__label) {
  font-weight: 600;
  color: var(--app-text-primary, #1a1a2e);
  font-size: var(--app-font-base, 0.875rem);
  padding-bottom: var(--app-space-xs, 4px);
}

.form-tip {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: var(--app-space-xs, 4px);
  font-size: var(--app-font-xs, 0.75rem);
  color: var(--app-text-secondary, #6b7280);
  line-height: 1.5;
}

.form-tip .el-icon {
  flex-shrink: 0;
  font-size: var(--app-font-sm, 0.8125rem);
}

/* ========== 上传组件微调 ========== */
.form-card :deep(.el-upload--picture-card),
.form-card :deep(.el-upload-list--picture-card .el-upload-list__item) {
  width: 100px;
  height: 100px;
  border-radius: var(--app-radius-base, 8px);
  border: 1px dashed var(--app-border-base, #d1d5db);
  transition: border-color 0.2s, background 0.2s;
}

.form-card :deep(.el-upload--picture-card:hover) {
  border-color: #f97316;
  background: #fff7ed;
}

/* ========== 操作按钮 ========== */
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--app-space-sm, 8px);
  padding-top: var(--app-space-xs, 4px);
}

.submit-btn {
  background: linear-gradient(135deg, #f97316, #ea580c) !important;
  border: none !important;
  box-shadow: 0 2px 8px rgba(249, 115, 22, 0.35);
  transition: box-shadow 0.2s, transform 0.15s;
  font-weight: 600;
}

.submit-btn:hover {
  box-shadow: 0 4px 16px rgba(249, 115, 22, 0.5);
  transform: translateY(-1px);
}

.submit-btn:active {
  transform: translateY(0);
  box-shadow: 0 2px 6px rgba(249, 115, 22, 0.3);
}

.submit-btn.is-loading {
  background: linear-gradient(135deg, #fb923c, #f97316) !important;
}

/* ========== 温馨提示 ========== */
.tips-card {
  margin-top: var(--app-space-lg, 20px);
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: var(--app-radius-base, 8px);
  padding: var(--app-space-base, 16px) var(--app-space-lg, 20px);
}

.tips-header {
  display: flex;
  align-items: center;
  gap: var(--app-space-xs, 4px);
  font-size: var(--app-font-sm, 0.8125rem);
  font-weight: 600;
  color: #c2410c;
  margin-bottom: var(--app-space-sm, 8px);
}

.tips-header .el-icon {
  font-size: var(--app-font-lg, 1rem);
}

.tips-list {
  margin: 0;
  padding-left: var(--app-space-lg, 20px);
  list-style: disc;
}

.tips-list li {
  font-size: var(--app-font-xs, 0.75rem);
  color: #9a3412;
  line-height: 1.8;
}

/* ========== 响应式 ========== */
@media (max-width: 768px) {
  .refund-apply-page {
    padding: var(--app-space-base, 16px);
  }

  .form-card {
    padding: var(--app-space-base, 16px);
    border-radius: var(--app-radius-base, 8px);
  }

  .form-actions {
    flex-direction: column-reverse;
    gap: var(--app-space-sm, 8px);
  }

  .form-actions .el-button {
    width: 100%;
  }

  .page-title {
    font-size: var(--app-font-2xl, 1.25rem);
  }
}
</style>
