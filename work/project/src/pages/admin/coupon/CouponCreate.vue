<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-left">
        <el-button :icon="ArrowLeft" text @click="handleBack">返回</el-button>
        <h2 class="page-title">创建优惠券</h2>
      </div>
    </div>

    <div class="page-content">
      <div class="form-card card">
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-width="140px"
          label-position="right"
          style="max-width: 600px;"
          @submit.prevent
        >
          <el-form-item label="券标题" prop="title">
            <el-input
              v-model="form.title"
              placeholder="请输入优惠券标题"
              maxlength="100"
              show-word-limit
            />
          </el-form-item>

          <el-form-item label="优惠金额" prop="amount">
            <el-input-number
              v-model="form.amount"
              :precision="2"
              :step="0.01"
              :min="0.01"
              :max="99999.99"
              placeholder="请输入优惠金额"
              style="width: 100%;"
            />
            <div class="form-tip">单位：元，最小 0.01 元</div>
          </el-form-item>

          <el-form-item label="最低订单金额" prop="minOrder">
            <el-input-number
              v-model="form.minOrder"
              :precision="2"
              :step="0.01"
              :min="0"
              :max="999999.99"
              placeholder="最低订单金额门槛"
              style="width: 100%;"
            />
            <div class="form-tip">0 表示无门槛</div>
          </el-form-item>

          <el-form-item label="生效时间" prop="validFrom">
            <el-date-picker
              v-model="form.validFrom"
              type="datetime"
              placeholder="选择生效时间"
              value-format="YYYY-MM-DD HH:mm:ss"
              style="width: 100%;"
            />
          </el-form-item>

          <el-form-item label="失效时间" prop="validTo">
            <el-date-picker
              v-model="form.validTo"
              type="datetime"
              placeholder="选择失效时间"
              value-format="YYYY-MM-DD HH:mm:ss"
              style="width: 100%;"
            />
          </el-form-item>

          <el-form-item>
            <div class="form-actions">
              <el-button @click="handleBack">取消</el-button>
              <el-button type="primary" :loading="submitting" @click="handleSubmit">
                确认创建
              </el-button>
            </div>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 平台后台 - 创建优惠券页
 * 功能：填写优惠券信息并提交创建
 */
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { ArrowLeft } from '@element-plus/icons-vue';
import { createCoupon } from '@/api/admin/coupon.js';

const router = useRouter();

/* ──────── 表单引用 ──────── */
const formRef = ref(null);
const submitting = ref(false);

/* ──────── 表单数据 ──────── */
const form = reactive({
  title: '',
  amount: null,
  minOrder: 0,
  validFrom: '',
  validTo: ''
});

/* ──────── 校验规则 ──────── */
const rules = {
  title: [
    { required: true, message: '请输入券标题', trigger: 'blur' },
    { max: 100, message: '券标题不能超过 100 个字符', trigger: 'blur' }
  ],
  amount: [
    { required: true, message: '请输入优惠金额', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value === null || value === undefined || value === '') {
          callback(new Error('请输入优惠金额'));
        } else if (Number(value) <= 0) {
          callback(new Error('优惠金额必须大于 0'));
        } else {
          callback();
        }
      },
      trigger: 'blur'
    }
  ],
  validFrom: [
    { required: true, message: '请选择生效时间', trigger: 'change' }
  ],
  validTo: [
    { required: true, message: '请选择失效时间', trigger: 'change' },
    {
      validator: (_rule, value, callback) => {
        if (!value) {
          callback(new Error('请选择失效时间'));
        } else if (form.validFrom && new Date(value) <= new Date(form.validFrom)) {
          callback(new Error('失效时间必须晚于生效时间'));
        } else {
          callback();
        }
      },
      trigger: 'change'
    }
  ]
};

/* ──────── 操作 ──────── */
function handleBack() {
  router.push({ name: 'AdminCouponList' });
}

async function handleSubmit() {
  if (!formRef.value) return;

  try {
    await formRef.value.validate();
  } catch {
    return;
  }

  submitting.value = true;
  try {
    const payload = {
      title: form.title,
      amount: String(form.amount),
      minOrder: String(form.minOrder ?? 0),
      validFrom: form.validFrom,
      validTo: form.validTo
    };

    const res = await createCoupon(payload);
    if (res?.success !== false) {
      ElMessage.success('优惠券创建成功');
      router.push({ name: 'AdminCouponList' });
    } else {
      ElMessage.error(res?.message || '创建失败');
    }
  } catch (err) {
    ElMessage.error('创建失败，请稍后重试');
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.page-container {
  padding: var(--spacing-xl, 24px);
  max-width: 900px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: var(--spacing-lg, 20px);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm, 8px);
}

.page-title {
  font-size: var(--font-size-2xl, 1.25rem);
  font-weight: 600;
  color: var(--color-text-primary, #1a1a2e);
  margin: 0;
}

.page-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-base, 16px);
}

.form-card {
  padding: var(--spacing-2xl, 32px);
}

.form-tip {
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-placeholder, #c0c4cc);
  line-height: 1.5;
}

.form-actions {
  display: flex;
  gap: var(--spacing-sm, 8px);
}
</style>
