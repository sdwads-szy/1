<template>
  <div class="shipping-page">
    <div class="page-header">
      <el-button
        :icon="ArrowLeft"
        text
        @click="goBack"
        class="back-btn"
      >
        返回订单列表
      </el-button>
      <h2 class="page-title">录入物流信息</h2>
    </div>

    <div class="form-card">
      <div class="form-header">
        <p class="form-subtitle">
          子订单号：<span class="order-no-highlight">{{ subOrderId }}</span>
        </p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
        label-position="left"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="物流单号" prop="trackingNo">
          <el-input
            v-model="form.trackingNo"
            placeholder="请输入物流运单号"
            maxlength="64"
            clearable
          />
        </el-form-item>

        <el-form-item label="承运商" prop="carrierCode">
          <el-select
            v-model="form.carrierCode"
            placeholder="请选择物流承运商"
            class="carrier-select"
          >
            <el-option
              v-for="carrier in carrierOptions"
              :key="carrier.value"
              :label="carrier.label"
              :value="carrier.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item>
          <div class="form-actions">
            <el-button @click="goBack">取消</el-button>
            <el-button
              type="primary"
              :loading="submitting"
              @click="handleSubmit"
            >
              {{ submitting ? '提交中...' : '确认发货' }}
            </el-button>
          </div>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { shipOrder } from '@/api/merchant-orders';
import { ElMessage } from 'element-plus';
import { ArrowLeft } from '@element-plus/icons-vue';

const router = useRouter();
const route = useRoute();

// Navigation contract: targetRead — 从 route.params 读取子订单 ID
const subOrderId = Number(route.params.id);

const formRef = ref(null);
const submitting = ref(false);

const form = reactive({
  trackingNo: '',
  carrierCode: ''
});

const carrierOptions = [
  { value: 'SF', label: '顺丰速运' },
  { value: 'ZTO', label: '中通快递' },
  { value: 'YTO', label: '圆通速递' },
  { value: 'STO', label: '申通快递' },
  { value: 'EMS', label: '邮政EMS' }
];

const rules = {
  trackingNo: [
    { required: true, message: '请输入物流运单号', trigger: 'blur' },
    { min: 1, max: 64, message: '物流单号长度在 1 到 64 个字符', trigger: 'blur' }
  ],
  carrierCode: [
    { required: true, message: '请选择物流承运商', trigger: 'change' }
  ]
};

function goBack() {
  router.push({ name: 'MerchantOrders' });
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;

  submitting.value = true;
  try {
    const res = await shipOrder({
      id: subOrderId,
      trackingNo: form.trackingNo.trim(),
      carrierCode: form.carrierCode
    });

    // 检查 mock 提示
    if (res.data && res.data.mockHint) {
      ElMessage.info(res.data.mockHint);
    }

    ElMessage.success('发货成功');
    router.push({ name: 'MerchantOrders' });
  } catch (err) {
    const msg = err?.response?.data?.message || '发货失败，请重试';
    ElMessage.error(msg);
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.shipping-page {
  padding: var(--space-lg);
  max-width: 640px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: var(--space-lg);
}

.back-btn {
  margin-bottom: var(--space-sm);
  padding-left: 0;
}

.page-title {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
  line-height: var(--line-height-tight);
}

.form-card {
  background: var(--color-bg-base);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
}

.form-header {
  margin-bottom: var(--space-lg);
  padding-bottom: var(--space-md);
  border-bottom: 1px solid var(--color-border);
}

.form-subtitle {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin: 0;
}

.order-no-highlight {
  font-family: var(--font-family);
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.5px;
  color: var(--color-text-primary);
  font-weight: 600;
}

.carrier-select {
  width: 100%;
}

.form-actions {
  display: flex;
  gap: var(--space-sm);
  justify-content: flex-end;
  width: 100%;
}
</style>
