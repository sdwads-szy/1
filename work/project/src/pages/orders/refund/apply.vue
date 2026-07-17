<template>
  <div class="refund-apply-page">
    <div class="page-header">
      <el-button :icon="ArrowLeft" text @click="goBack">返回订单详情</el-button>
      <h2 class="page-title">申请售后</h2>
    </div>

    <!-- 加载态骨架 -->
    <div v-if="loading" class="skeleton-card">
      <el-skeleton :rows="8" animated />
    </div>

    <!-- 错误态 -->
    <div v-else-if="errorMsg" class="error-state">
      <div class="error-icon">
        <el-icon :size="48"><WarningFilled /></el-icon>
      </div>
      <h3 class="error-title">{{ errorMsg }}</h3>
      <p class="error-desc">请返回订单详情页重试</p>
      <el-button type="primary" @click="goBack">返回订单详情</el-button>
    </div>

    <!-- 表单 -->
    <div v-else class="form-card">
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
        label-position="left"
      >
        <!-- 售后类型 -->
        <el-form-item label="售后类型" prop="type">
          <el-radio-group v-model="form.type">
            <el-radio value="only_refund">仅退款</el-radio>
            <el-radio value="return_refund">退货退款</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 申请原因 -->
        <el-form-item label="申请原因" prop="reason">
          <el-input
            v-model="form.reason"
            type="textarea"
            :rows="4"
            maxlength="500"
            show-word-limit
            placeholder="请描述申请售后的原因，不超过500字"
          />
        </el-form-item>

        <!-- 退款金额 -->
        <el-form-item label="退款金额" prop="amount">
          <el-input-number
            v-model="form.amount"
            :min="0.01"
            :precision="2"
            :step="0.01"
            :max="999999.99"
            placeholder="请输入退款金额"
            style="width: 220px"
          />
          <span class="amount-unit">元</span>
          <span class="amount-hint">退款金额不可超过实付金额</span>
        </el-form-item>

        <!-- 凭证图片 -->
        <el-form-item label="凭证图片" prop="evidenceImages">
          <div class="upload-area">
            <div
              v-for="(img, index) in previewImages"
              :key="index"
              class="upload-thumb"
            >
              <img :src="img" alt="凭证" />
              <el-button
                class="thumb-remove"
                :icon="Close"
                circle
                size="small"
                type="danger"
                @click="removeImage(index)"
              />
            </div>
            <label
              v-if="previewImages.length < 5"
              class="upload-btn"
            >
              <input
                ref="fileInput"
                type="file"
                accept="image/*"
                multiple
                hidden
                @change="onFileChange"
              />
              <el-icon :size="28"><Plus /></el-icon>
              <span>上传凭证</span>
            </label>
          </div>
          <p class="upload-tip">最多上传5张图片，支持jpg/png格式</p>
        </el-form-item>

        <!-- 提交 -->
        <el-form-item>
          <el-button
            type="primary"
            :loading="submitting"
            @click="handleSubmit"
          >
            {{ submitting ? '提交中...' : '提交申请' }}
          </el-button>
          <el-button @click="goBack">取消</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { ArrowLeft, Close, Plus, WarningFilled } from '@element-plus/icons-vue';
import { applyRefund } from '@/api/refunds';

const route = useRoute();
const router = useRouter();

const formRef = ref(null);
const fileInput = ref(null);
const submitting = ref(false);
const loading = ref(false);
const errorMsg = ref('');
const previewImages = ref([]);
const selectedFiles = ref([]);

const subOrderId = Number(route.params.subOrderId);

const form = reactive({
  subOrderId: subOrderId,
  type: 'only_refund',
  reason: '',
  amount: null,
  evidenceImages: []
});

const rules = {
  type: [
    { required: true, message: '请选择售后类型', trigger: 'change' }
  ],
  reason: [
    { required: true, message: '请填写申请原因', trigger: 'blur' },
    { min: 1, max: 500, message: '申请原因长度为1-500个字符', trigger: 'blur' }
  ],
  amount: [
    { required: true, message: '请输入退款金额', trigger: 'blur' },
    {
      type: 'number',
      min: 0.01,
      message: '退款金额必须大于0.01元',
      trigger: 'blur'
    }
  ]
};

onMounted(() => {
  if (!subOrderId || isNaN(subOrderId)) {
    errorMsg.value = '缺少订单信息';
    return;
  }
});

function onFileChange(e) {
  const files = Array.from(e.target.files);
  const remaining = 5 - previewImages.value.length;
  const toAdd = files.slice(0, remaining);

  if (files.length > remaining) {
    ElMessage.warning(`最多上传5张图片，仅保留前${remaining}张`);
  }

  toAdd.forEach(file => {
    const url = URL.createObjectURL(file);
    previewImages.value.push(url);
    selectedFiles.value.push(file);
  });

  // 重置 input 以允许重复选择相同文件
  if (fileInput.value) {
    fileInput.value.value = '';
  }
}

function removeImage(index) {
  URL.revokeObjectURL(previewImages.value[index]);
  previewImages.value.splice(index, 1);
  selectedFiles.value.splice(index, 1);
}

function goBack() {
  router.push({ name: 'OrderDetail', params: { id: subOrderId } });
}

async function handleSubmit() {
  if (!formRef.value) return;

  try {
    await formRef.value.validate();
  } catch {
    ElMessage.warning('请完善申请信息');
    return;
  }

  submitting.value = true;

  try {
    // 构造 evidenceImages：若有真实文件则传文件名，否则空数组
    const evidenceImages = selectedFiles.value.length > 0
      ? selectedFiles.value.map(f => f.name)
      : [];

    const res = await applyRefund({
      subOrderId: form.subOrderId,
      type: form.type,
      reason: form.reason,
      amount: String(form.amount),
      evidenceImages
    });

    // mock 模式提示
    if (res.data?.mockHint) {
      ElMessage.info(res.data.mockHint);
    }

    ElMessage.success('售后申请已提交');

    // 跳转售后详情页
    const refundId = res.data?.id || res.data?.requestNo;
    router.push({ name: 'RefundDetail', params: { requestNo: refundId } });
  } catch (err) {
    const msg = err.response?.data?.message || err.message || '提交失败';
    ElMessage.error(msg);
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.refund-apply-page {
  max-width: 720px;
  margin: 0 auto;
  padding: var(--space-lg);
}

.page-header {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
}

.page-title {
  font-size: var(--font-size-xl);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.skeleton-card {
  background: var(--color-bg-base);
  border: var(--page-order-card-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
}

.error-state {
  background: var(--color-bg-base);
  border: var(--page-order-card-border);
  border-radius: var(--radius-md);
  padding: var(--space-2xl) var(--space-lg);
  text-align: center;
}

.error-icon {
  color: var(--color-error);
  opacity: 0.6;
  margin-bottom: var(--space-md);
}

.error-title {
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-sm);
}

.error-desc {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-lg);
}

.form-card {
  background: var(--color-bg-base);
  border: var(--page-order-card-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
}

.amount-unit {
  margin-left: var(--space-sm);
  color: var(--color-text-secondary);
  font-size: var(--font-size-base);
}

.amount-hint {
  margin-left: var(--space-md);
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

.upload-area {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}

.upload-thumb {
  position: relative;
  width: 80px;
  height: 80px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.upload-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumb-remove {
  position: absolute;
  top: -6px;
  right: -6px;
  z-index: 1;
}

.upload-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-smooth),
              color var(--duration-fast) var(--ease-smooth);
  gap: 2px;
  font-size: var(--font-size-xs);
}

.upload-btn:hover {
  border-color: var(--color-primary-400);
  color: var(--color-primary-500);
}

.upload-tip {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin: var(--space-xs) 0 0;
}
</style>
