<template>
  <div class="page-container address-edit-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <el-button
          class="back-btn"
          :icon="ArrowLeft"
          text
          @click="goBack"
        />
        <h1 class="page-title">{{ isCreate ? '新增收货地址' : '编辑收货地址' }}</h1>
      </div>
    </div>

    <div class="page-content">
      <!-- 加载态（编辑模式拉取数据时） -->
      <div v-if="fetching" class="state-wrapper flex-center">
        <el-icon class="loading-icon"><Loading /></el-icon>
        <span>加载地址信息...</span>
      </div>

      <!-- 表单 -->
      <div v-else class="form-card card">
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-width="80px"
          label-position="top"
          class="address-form"
        >
          <div class="form-row">
            <el-form-item label="收货人" prop="name" class="form-half">
              <el-input
                v-model="form.name"
                placeholder="请输入收货人姓名"
                maxlength="50"
                clearable
              />
            </el-form-item>
            <el-form-item label="手机号码" prop="phone" class="form-half">
              <el-input
                v-model="form.phone"
                placeholder="请输入手机号码"
                maxlength="20"
                clearable
              />
            </el-form-item>
          </div>

          <div class="form-row form-row-three">
            <el-form-item label="省份" prop="province">
              <el-input
                v-model="form.province"
                placeholder="省份"
                maxlength="50"
                clearable
              />
            </el-form-item>
            <el-form-item label="城市" prop="city">
              <el-input
                v-model="form.city"
                placeholder="城市"
                maxlength="50"
                clearable
              />
            </el-form-item>
            <el-form-item label="区/县" prop="district">
              <el-input
                v-model="form.district"
                placeholder="区/县"
                maxlength="50"
                clearable
              />
            </el-form-item>
          </div>

          <el-form-item label="详细地址" prop="detail">
            <el-input
              v-model="form.detail"
              type="textarea"
              :rows="2"
              placeholder="街道、门牌号等详细地址"
              maxlength="255"
              show-word-limit
            />
          </el-form-item>

          <el-form-item label="设为默认地址">
            <el-switch
              v-model="form.is_default"
              active-text="默认地址"
              :active-value="1"
              :inactive-value="0"
            />
          </el-form-item>

          <div class="form-actions">
            <el-button @click="goBack">取消</el-button>
            <el-button type="primary" :loading="saving" @click="handleSave">
              保存地址
            </el-button>
          </div>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Loading, ArrowLeft } from '@element-plus/icons-vue';
import { getAddresses, createAddress, updateAddress } from '@/api/user';

const router = useRouter();
const route = useRoute();

// --- 路由参数 ---
const editId = computed(() => {
  const id = route.params.id;
  if (id === 'new') return null;
  return parseInt(id);
});

const isCreate = computed(() => editId.value === null);

// --- 状态 ---
const fetching = ref(false);
const saving = ref(false);
const formRef = ref(null);

const form = reactive({
  name: '',
  phone: '',
  province: '',
  city: '',
  district: '',
  detail: '',
  is_default: 0
});

// --- 表单校验 ---
const phonePattern = /^1[3-9]\d{9}$/;

const rules = {
  name: [
    { required: true, message: '请输入收货人姓名', trigger: 'blur' },
    { max: 50, message: '收货人姓名不超过50个字符', trigger: 'blur' }
  ],
  phone: [
    { required: true, message: '请输入手机号码', trigger: 'blur' },
    {
      pattern: phonePattern,
      message: '请输入正确的11位手机号码',
      trigger: 'blur'
    }
  ],
  province: [
    { required: true, message: '请输入省份', trigger: 'blur' }
  ],
  city: [
    { required: true, message: '请输入城市', trigger: 'blur' }
  ],
  district: [
    { required: true, message: '请输入区/县', trigger: 'blur' }
  ],
  detail: [
    { required: true, message: '请输入详细地址', trigger: 'blur' },
    { max: 255, message: '详细地址不超过255个字符', trigger: 'blur' }
  ]
};

// --- 方法 ---
async function fetchAddressData() {
  if (isCreate.value) return;

  fetching.value = true;
  try {
    const res = await getAddresses();
    const data = res.data || res;
    const list = Array.isArray(data) ? data : (data.list || []);
    const addr = list.find(item => item.id === editId.value);

    if (!addr) {
      ElMessage.error('地址不存在');
      router.push({ name: 'AddressList' });
      return;
    }

    Object.assign(form, {
      name: addr.name || '',
      phone: addr.phone || '',
      province: addr.province || '',
      city: addr.city || '',
      district: addr.district || '',
      detail: addr.detail || '',
      is_default: addr.is_default === true || addr.is_default === 1 ? 1 : 0
    });
  } catch (err) {
    const msg = err?.response?.data?.message || '加载地址失败';
    ElMessage.error(msg);
  } finally {
    fetching.value = false;
  }
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;

  saving.value = true;

  const payload = {
    name: form.name,
    phone: form.phone,
    province: form.province,
    city: form.city,
    district: form.district,
    detail: form.detail,
    is_default: form.is_default
  };

  try {
    if (isCreate.value) {
      await createAddress(payload);
      ElMessage.success('地址添加成功');
    } else {
      await updateAddress(editId.value, payload);
      ElMessage.success('地址更新成功');
    }
    router.push({ name: 'AddressList' });
  } catch (err) {
    const msg = err?.response?.data?.message || '保存失败，请重试';
    ElMessage.error(msg);
  } finally {
    saving.value = false;
  }
}

function goBack() {
  router.push({ name: 'AddressList' });
}

// --- 生命周期 ---
onMounted(() => {
  fetchAddressData();
});
</script>

<style scoped>
.address-edit-page {
  max-width: 640px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--app-space-xl) 0 var(--app-space-lg);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--app-space-xs);
}

.back-btn {
  font-size: 20px;
  color: var(--app-text-secondary);
}

.page-title {
  font-size: var(--app-font-3xl);
  font-weight: 700;
  color: var(--app-text-primary);
  margin: 0;
}

.state-wrapper {
  flex-direction: column;
  gap: var(--app-space-sm);
  padding: var(--app-space-4xl) 0;
  color: var(--app-text-secondary);
}

.loading-icon {
  font-size: 32px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 表单卡片 */
.form-card {
  padding: var(--app-space-2xl);
  border-top: 3px solid #f97316;
}

.address-form {
  max-width: 100%;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--app-space-base);
}

.form-row-three {
  grid-template-columns: 1fr 1fr 1fr;
}

@media (max-width: 576px) {
  .form-row,
  .form-row-three {
    grid-template-columns: 1fr;
  }
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--app-space-sm);
  margin-top: var(--app-space-xl);
  padding-top: var(--app-space-lg);
  border-top: 1px solid var(--app-border-light);
}
</style>
