<template>
  <div class="onboarding-page">
    <!-- 顶部步骤条 -->
    <div class="stepper-bar">
      <div class="stepper">
        <div
          v-for="(step, idx) in steps"
          :key="idx"
          class="stepper-node"
          :class="{
            'is-active': currentStep === idx,
            'is-completed': currentStep > idx,
            'is-pending': currentStep < idx
          }"
        >
          <div class="stepper-circle">
            <el-icon v-if="currentStep > idx"><Check /></el-icon>
            <span v-else>{{ idx + 1 }}</span>
          </div>
          <span class="stepper-label">{{ step.label }}</span>
          <div
            v-if="idx < steps.length - 1"
            class="stepper-line"
            :class="{ 'is-done': currentStep > idx }"
          ></div>
        </div>
      </div>
    </div>

    <!-- 草稿恢复提示 -->
    <el-alert
      v-if="draftAvailable && !draftRestored"
      type="info"
      :closable="true"
      show-icon
      class="draft-alert"
      @close="dismissDraft"
    >
      <template #title>
        <span>检测到您上次保存的草稿</span>
        <el-button type="primary" link @click="restoreDraft" class="draft-restore-btn">继续填写</el-button>
      </template>
    </el-alert>

    <!-- 表单卡片 -->
    <div class="form-card">
      <!-- Step 1: 账户验证 -->
      <div v-show="currentStep === 0" class="step-content">
        <h3 class="step-title">账户验证</h3>
        <p class="step-desc">请输入联系人手机号并完成短信验证</p>
        <el-form
          ref="step1FormRef"
          :model="formData"
          :rules="step1Rules"
          label-position="top"
          class="step-form"
        >
          <el-form-item label="手机号" prop="mobile">
            <el-input
              v-model="formData.mobile"
              placeholder="请输入11位手机号"
              maxlength="11"
              :disabled="submitting"
            />
          </el-form-item>
          <el-form-item label="验证码" prop="code">
            <div class="sms-row">
              <el-input
                v-model="formData.code"
                placeholder="请输入6位验证码"
                maxlength="6"
                :disabled="submitting"
              />
              <el-button
                :disabled="smsCooldown > 0 || !isMobileValid"
                :loading="smsSending"
                @click="handleSendSms"
                class="sms-btn"
              >
                {{ smsCooldown > 0 ? `${smsCooldown}s` : '获取验证码' }}
              </el-button>
            </div>
          </el-form-item>
        </el-form>
      </div>

      <!-- Step 2: 企业资质 -->
      <div v-show="currentStep === 1" class="step-content">
        <h3 class="step-title">企业资质</h3>
        <p class="step-desc">请填写企业信息并上传营业执照</p>
        <el-form
          ref="step2FormRef"
          :model="formData"
          :rules="step2Rules"
          label-position="top"
          class="step-form"
        >
          <el-form-item label="统一社会信用代码" prop="creditCode">
            <el-input
              v-model="formData.creditCode"
              placeholder="18位统一社会信用代码"
              maxlength="18"
              :disabled="submitting"
              style="text-transform: uppercase"
            />
          </el-form-item>
          <el-form-item label="营业执照" prop="bizLicense">
            <div
              class="upload-zone"
              :class="{ 'has-file': formData.bizLicense, 'is-uploading': licenseUploading }"
              @click="!formData.bizLicense && triggerFileInput('bizLicense')"
            >
              <template v-if="!formData.bizLicense">
                <el-icon class="upload-icon"><UploadFilled /></el-icon>
                <p class="upload-text">点击上传或拖拽文件到此处</p>
                <p class="upload-hint">支持 JPG/PNG/PDF，最大 5MB</p>
              </template>
              <template v-else>
                <div class="upload-preview">
                  <el-icon class="upload-success-icon"><CircleCheckFilled /></el-icon>
                  <span class="upload-filename">{{ licenseFileName }}</span>
                  <el-button type="warning" link size="small" @click.stop="removeFile('bizLicense')">重新上传</el-button>
                </div>
              </template>
            </div>
          </el-form-item>
        </el-form>
      </div>

      <!-- Step 3: 店铺信息 -->
      <div v-show="currentStep === 2" class="step-content">
        <h3 class="step-title">店铺信息</h3>
        <p class="step-desc">设置您的店铺名称和Logo</p>
        <el-form
          ref="step3FormRef"
          :model="formData"
          :rules="step3Rules"
          label-position="top"
          class="step-form"
        >
          <el-form-item label="店铺名称" prop="shopName">
            <el-input
              v-model="formData.shopName"
              placeholder="2-30个字符"
              maxlength="30"
              show-word-limit
              :disabled="submitting"
            />
          </el-form-item>
          <el-form-item label="店铺Logo">
            <div
              class="upload-zone logo-zone"
              :class="{ 'has-file': formData.logo, 'is-uploading': logoUploading }"
              @click="!formData.logo && triggerFileInput('logo')"
            >
              <template v-if="!formData.logo">
                <el-icon class="upload-icon"><UploadFilled /></el-icon>
                <p class="upload-text">上传店铺Logo</p>
                <p class="upload-hint">建议尺寸 200×200px，最大 2MB</p>
              </template>
              <template v-else>
                <div class="upload-preview logo-preview">
                  <img :src="formData.logo" alt="店铺Logo" class="logo-thumb" />
                  <el-button type="warning" link size="small" @click.stop="removeFile('logo')">重新上传</el-button>
                </div>
              </template>
            </div>
          </el-form-item>
        </el-form>

        <!-- 提交确认提示 -->
        <el-alert type="warning" :closable="false" show-icon class="submit-tip">
          <template #title>
            确认提交入驻申请？提交后资料将进入审核，审核期间不可修改。
          </template>
        </el-alert>
      </div>
    </div>

    <!-- 底部操作栏 -->
    <div class="form-actions">
      <el-button
        :disabled="submitting"
        :loading="draftSaving"
        @click="saveDraft"
      >
        {{ draftSaving ? '保存中...' : '保存草稿' }}
      </el-button>
      <div class="form-actions-right">
        <el-button
          v-if="currentStep > 0"
          :disabled="submitting"
          @click="prevStep"
        >
          上一步
        </el-button>
        <el-button
          v-if="currentStep < steps.length - 1"
          type="primary"
          :disabled="submitting"
          @click="nextStep"
        >
          下一步
        </el-button>
        <el-button
          v-if="currentStep === steps.length - 1"
          type="primary"
          :loading="submitting"
          @click="handleSubmit"
        >
          {{ submitting ? '提交中...' : '提交审核' }}
        </el-button>
      </div>
    </div>

    <!-- 隐藏文件输入 -->
    <input
      ref="bizLicenseInput"
      type="file"
      accept="image/jpeg,image/png,application/pdf"
      style="display: none"
      @change="handleFileChange($event, 'bizLicense')"
    />
    <input
      ref="logoInput"
      type="file"
      accept="image/jpeg,image/png"
      style="display: none"
      @change="handleFileChange($event, 'logo')"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Check, UploadFilled, CircleCheckFilled } from '@element-plus/icons-vue';
import { sendSmsCode, submitMerchantRegister, getRegisterStatus, uploadFile } from '@/api/merchant-register';

const router = useRouter();

// ═══════════════════════════════════════════════
// 步骤配置
// ═══════════════════════════════════════════════
const steps = [
  { label: '账户验证', key: 'account' },
  { label: '企业资质', key: 'qualification' },
  { label: '店铺信息', key: 'shop' }
];

const currentStep = ref(0);

// ═══════════════════════════════════════════════
// 表单数据
// ═══════════════════════════════════════════════
const DRAFT_KEY = 'merchant_register_draft';

const defaultFormData = () => ({
  mobile: '',
  code: '',
  creditCode: '',
  bizLicense: '',
  shopName: '',
  logo: ''
});

const formData = reactive(defaultFormData());

// ═══════════════════════════════════════════════
// 表单校验规则
// ═══════════════════════════════════════════════
const step1Rules = {
  mobile: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确', trigger: 'blur' }
  ],
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { pattern: /^\d{6}$/, message: '验证码为6位数字', trigger: 'blur' }
  ]
};

const step2Rules = {
  creditCode: [
    { required: true, message: '请输入统一社会信用代码', trigger: 'blur' },
    { pattern: /^[A-Z0-9]{18}$/, message: '统一社会信用代码为18位大写字母或数字', trigger: 'blur' }
  ],
  bizLicense: [
    { required: true, message: '请上传营业执照', trigger: 'change' }
  ]
};

const step3Rules = {
  shopName: [
    { required: true, message: '请输入店铺名称', trigger: 'blur' },
    { min: 2, message: '店铺名称至少2个字符', trigger: 'blur' },
    { max: 64, message: '店铺名称不超过64个字符', trigger: 'blur' }
  ]
};

// ═══════════════════════════════════════════════
// 表单引用
// ═══════════════════════════════════════════════
const step1FormRef = ref(null);
const step2FormRef = ref(null);
const step3FormRef = ref(null);

// ═══════════════════════════════════════════════
// 短信验证码
// ═══════════════════════════════════════════════
const smsCooldown = ref(0);
const smsSending = ref(false);
let smsTimer = null;

const isMobileValid = computed(() => /^1[3-9]\d{9}$/.test(formData.mobile));

function startSmsCooldown() {
  smsCooldown.value = 60;
  smsTimer = setInterval(() => {
    smsCooldown.value--;
    if (smsCooldown.value <= 0) {
      clearInterval(smsTimer);
      smsTimer = null;
    }
  }, 1000);
}

async function handleSendSms() {
  if (!isMobileValid.value) {
    ElMessage.warning('请先输入正确的手机号');
    return;
  }
  smsSending.value = true;
  try {
    const res = await sendSmsCode({ mobile: formData.mobile });
    startSmsCooldown();
    if (res.data && res.data.mockCode) {
      ElMessage.success({ message: '[模拟] 验证码: ' + res.data.mockCode, duration: 10000 });
    } else {
      ElMessage.success('验证码已发送');
    }
  } catch (err) {
    const msg = err?.response?.data?.message || '发送失败，请稍后重试';
    ElMessage.error(msg);
  } finally {
    smsSending.value = false;
  }
}

// ═══════════════════════════════════════════════
// 文件上传
// ═══════════════════════════════════════════════
const bizLicenseInput = ref(null);
const logoInput = ref(null);
const licenseUploading = ref(false);
const logoUploading = ref(false);
const licenseFileName = ref('');

function triggerFileInput(field) {
  if (field === 'bizLicense') {
    bizLicenseInput.value?.click();
  } else if (field === 'logo') {
    logoInput.value?.click();
  }
}

async function handleFileChange(event, field) {
  const file = event.target.files?.[0];
  if (!file) return;

  // 文件大小校验
  const maxSize = field === 'bizLicense' ? 5 * 1024 * 1024 : 2 * 1024 * 1024;
  if (file.size > maxSize) {
    const sizeStr = field === 'bizLicense' ? '5MB' : '2MB';
    ElMessage.error(`文件大小超过限制（最大${sizeStr}），请重新选择`);
    event.target.value = '';
    return;
  }

  // 文件类型校验
  if (field === 'bizLicense') {
    const allowed = ['image/jpeg', 'image/png', 'application/pdf'];
    if (!allowed.includes(file.type)) {
      ElMessage.error('仅支持 JPG/PNG/PDF 格式');
      event.target.value = '';
      return;
    }
  } else if (field === 'logo') {
    const allowed = ['image/jpeg', 'image/png'];
    if (!allowed.includes(file.type)) {
      ElMessage.error('仅支持 JPG/PNG 格式');
      event.target.value = '';
      return;
    }
  }

  if (field === 'bizLicense') {
    licenseUploading.value = true;
  } else {
    logoUploading.value = true;
  }

  const fd = new FormData();
  fd.append('file', file);
  fd.append('type', field === 'bizLicense' ? 'file/merchant_license' : 'img/merchant_logo');

  try {
    const res = await uploadFile(fd);
    const url = res.data?.url || res.data?.path || '';
    formData[field] = url;

    if (field === 'bizLicense') {
      licenseFileName.value = file.name;
    }

    if (res.data?.mockHint) {
      ElMessage.info(res.data.mockHint);
    } else {
      ElMessage.success('上传成功');
    }

    // 触发校验
    if (field === 'bizLicense' && step2FormRef.value) {
      step2FormRef.value.validateField('bizLicense');
    }
  } catch (err) {
    const msg = err?.response?.data?.message || '上传失败，请重试';
    ElMessage.error('上传失败: ' + msg);
  } finally {
    if (field === 'bizLicense') {
      licenseUploading.value = false;
    } else {
      logoUploading.value = false;
    }
    event.target.value = '';
  }
}

function removeFile(field) {
  formData[field] = '';
  if (field === 'bizLicense') {
    licenseFileName.value = '';
  }
}

// ═══════════════════════════════════════════════
// 步骤导航
// ═══════════════════════════════════════════════
function getCurrentFormRef() {
  const refs = [step1FormRef, step2FormRef, step3FormRef];
  return refs[currentStep.value];
}

async function nextStep() {
  const formRef = getCurrentFormRef();
  if (!formRef || !formRef.value) {
    currentStep.value++;
    return;
  }
  try {
    await formRef.value.validate();
    currentStep.value++;
  } catch {
    ElMessage.warning('请完善标注字段后再次提交');
  }
}

function prevStep() {
  if (currentStep.value > 0) {
    currentStep.value--;
  }
}

// ═══════════════════════════════════════════════
// 提交
// ═══════════════════════════════════════════════
const submitting = ref(false);

async function handleSubmit() {
  // 先校验当前步骤
  if (step3FormRef.value) {
    try {
      await step3FormRef.value.validate();
    } catch {
      ElMessage.warning('请完善标注字段后再次提交');
      return;
    }
  }

  // 二次确认
  try {
    await ElMessageBox.confirm(
      '确认提交入驻申请？提交后资料将进入审核，审核期间不可修改。',
      '确认提交',
      { confirmButtonText: '确认提交', cancelButtonText: '再检查一下', type: 'warning' }
    );
  } catch {
    return;
  }

  submitting.value = true;
  try {
    const res = await submitMerchantRegister({
      mobile: formData.mobile,
      code: formData.code,
      creditCode: formData.creditCode.toUpperCase(),
      bizLicense: formData.bizLicense,
      shopName: formData.shopName,
      logo: formData.logo || undefined
    });

    if (res.data?.mockHint) {
      ElMessage.info(res.data.mockHint);
    }

    ElMessage.success('入驻申请已提交，我们将在 1-3 个工作日内完成审核，请耐心等待。');
    clearDraft();
    router.push({ name: 'MerchantRegisterStatus' });
  } catch (err) {
    const code = err?.response?.data?.code;
    const msg = err?.response?.data?.message;
    if (code === 'DUPLICATE_CREDIT_CODE') {
      ElMessage.error(msg || '该统一社会信用代码已被注册');
    } else if (code === 'DUPLICATE_SHOP_NAME') {
      ElMessage.error(msg || '店铺名已被占用');
    } else if (code === 'INVALID_CODE' || code === 'CODE_EXPIRED') {
      ElMessage.error(msg || '验证码无效或已过期，请重新获取');
    } else {
      ElMessage.error(msg || '提交失败，请检查网络后重试。草稿已自动保存。');
    }
  } finally {
    submitting.value = false;
  }
}

// ═══════════════════════════════════════════════
// 草稿管理
// ═══════════════════════════════════════════════
const draftAvailable = ref(false);
const draftRestored = ref(false);
const draftSaving = ref(false);
let draftSaveTimer = null;

function saveDraftToStorage() {
  try {
    const draft = { ...formData };
    localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
  } catch {
    // localStorage 满，静默失败
  }
}

function loadDraftFromStorage() {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    if (raw) {
      const draft = JSON.parse(raw);
      if (draft.mobile || draft.creditCode || draft.shopName) {
        draftAvailable.value = true;
      }
      return draft;
    }
  } catch {
    // ignore
  }
  return null;
}

function restoreDraft() {
  const draft = loadDraftFromStorage();
  if (draft) {
    Object.keys(defaultFormData()).forEach(key => {
      if (draft[key] !== undefined) {
        formData[key] = draft[key];
      }
    });
    if (draft.bizLicense) {
      licenseFileName.value = '营业执照';
    }
  }
  draftRestored.value = true;
  draftAvailable.value = false;
  ElMessage.success('草稿已恢复');
}

function dismissDraft() {
  draftAvailable.value = false;
}

function clearDraft() {
  localStorage.removeItem(DRAFT_KEY);
}

async function saveDraft() {
  draftSaving.value = true;
  saveDraftToStorage();
  // 模拟短暂延迟给用户反馈
  await new Promise(r => setTimeout(r, 300));
  draftSaving.value = false;
  ElMessage.success('草稿已保存');
}

// 自动保存：监听 formData 变化，防抖 500ms
watch(
  () => ({ ...formData }),
  () => {
    if (draftSaveTimer) clearTimeout(draftSaveTimer);
    draftSaveTimer = setTimeout(() => {
      saveDraftToStorage();
    }, 500);
  },
  { deep: true }
);

// ═══════════════════════════════════════════════
// 生命周期
// ═══════════════════════════════════════════════
onMounted(async () => {
  // 检查是否有草稿
  loadDraftFromStorage();

  // 检查是否已有入驻申请
  try {
    const res = await getRegisterStatus();
    if (res.data && res.data.status) {
      // 已有申请记录，跳转状态页
      router.replace({ name: 'MerchantRegisterStatus' });
    }
  } catch {
    // 无申请记录，正常进入表单
  }
});

onBeforeUnmount(() => {
  if (smsTimer) {
    clearInterval(smsTimer);
    smsTimer = null;
  }
  if (draftSaveTimer) {
    clearTimeout(draftSaveTimer);
    draftSaveTimer = null;
  }
});
</script>

<style scoped>
/* ═══════════════════════════════════════════
   页面布局
   ═══════════════════════════════════════════ */
.onboarding-page {
  max-width: var(--page-onboarding-max-width, 880px);
  margin: 0 auto;
  padding: var(--space-lg) var(--space-lg) var(--space-3xl);
  min-height: 100vh;
  background: var(--color-bg-page);
}

/* ═══════════════════════════════════════════
   步骤条
   ═══════════════════════════════════════════ */
.stepper-bar {
  position: sticky;
  top: 56px;
  z-index: var(--z-sticky, 100);
  background: var(--color-bg-page);
  padding: var(--space-lg) 0;
  margin-bottom: var(--space-lg);
}

.stepper {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
}

.stepper-node {
  display: flex;
  align-items: center;
  position: relative;
}

.stepper-circle {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-sm);
  font-weight: 600;
  transition: all var(--duration-fast) var(--ease-smooth);
  flex-shrink: 0;
}

.stepper-node.is-active .stepper-circle {
  background: var(--page-onboarding-step-active, var(--color-primary-500));
  color: #FFFFFF;
  font-weight: 700;
}

.stepper-node.is-completed .stepper-circle {
  background: var(--page-onboarding-step-completed, var(--color-success));
  color: #FFFFFF;
}

.stepper-node.is-pending .stepper-circle {
  background: transparent;
  border: 2px solid var(--page-onboarding-step-pending, var(--color-border));
  color: var(--color-text-tertiary);
}

.stepper-label {
  position: absolute;
  top: 40px;
  left: 50%;
  transform: translateX(-50%);
  white-space: nowrap;
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  transition: color var(--duration-fast);
}

.stepper-node.is-active .stepper-label,
.stepper-node.is-completed .stepper-label {
  color: var(--color-text-primary);
}

.stepper-line {
  width: 120px;
  height: 2px;
  background: var(--page-onboarding-step-pending, var(--color-border));
  margin: 0 16px;
  transition: background var(--duration-fast);
}

.stepper-line.is-done {
  background: var(--page-onboarding-step-completed, var(--color-success));
}

/* ═══════════════════════════════════════════
   草稿提示
   ═══════════════════════════════════════════ */
.draft-alert {
  margin-bottom: var(--space-lg);
  border-radius: var(--radius-sm);
}

.draft-restore-btn {
  margin-left: var(--space-sm);
  font-size: var(--font-size-sm);
}

/* ═══════════════════════════════════════════
   表单卡片
   ═══════════════════════════════════════════ */
.form-card {
  background: var(--color-bg-base);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  padding: var(--space-xl);
  border: 1px solid var(--color-border);
  margin-bottom: var(--space-lg);
}

.step-content {
  animation: fadeIn 150ms var(--ease-smooth);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.step-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-xs);
}

.step-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-lg);
}

.step-form {
  max-width: 520px;
}

/* ═══════════════════════════════════════════
   短信验证码行
   ═══════════════════════════════════════════ */
.sms-row {
  display: flex;
  gap: var(--space-sm);
  width: 100%;
}

.sms-row .el-input {
  flex: 1;
}

.sms-btn {
  min-width: 120px;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
}

/* ═══════════════════════════════════════════
   上传区域
   ═══════════════════════════════════════════ */
.upload-zone {
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-page);
  padding: var(--space-xl);
  text-align: center;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-smooth);
  min-height: 160px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.upload-zone:hover:not(.has-file) {
  border-color: var(--color-primary-400);
  background: var(--color-primary-50);
}

.upload-zone.is-uploading {
  opacity: 0.6;
  pointer-events: none;
}

.upload-zone.has-file {
  border-style: solid;
  border-color: var(--color-success);
  cursor: default;
}

.upload-icon {
  font-size: 48px;
  color: var(--color-text-tertiary);
  margin-bottom: var(--space-sm);
}

.upload-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-xs);
}

.upload-hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin: 0;
}

.upload-preview {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.upload-success-icon {
  color: var(--color-success);
  font-size: 20px;
}

.upload-filename {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Logo 上传区 */
.logo-zone {
  min-height: 120px;
  max-width: 300px;
}

.logo-preview {
  flex-direction: column;
  gap: var(--space-sm);
}

.logo-thumb {
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
}

/* ═══════════════════════════════════════════
   提交提示
   ═══════════════════════════════════════════ */
.submit-tip {
  margin-top: var(--space-lg);
  border-radius: var(--radius-sm);
}

/* ═══════════════════════════════════════════
   底部操作栏
   ═══════════════════════════════════════════ */
.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.form-actions-right {
  display: flex;
  gap: var(--space-sm);
}

/* ═══════════════════════════════════════════
   全局输入框圆角覆盖
   ═══════════════════════════════════════════ */
:deep(.el-input .el-input__wrapper) {
  border-radius: var(--radius-sm);
}

:deep(.el-button) {
  border-radius: var(--radius-sm);
}

:deep(.el-button--primary) {
  min-width: 100px;
}

/* ═══════════════════════════════════════════
   响应式
   ═══════════════════════════════════════════ */
@media (max-width: 768px) {
  .onboarding-page {
    padding: var(--space-md);
  }

  .stepper-line {
    width: 60px;
    margin: 0 8px;
  }

  .form-card {
    padding: var(--space-lg);
  }

  .form-actions {
    flex-direction: column-reverse;
    gap: var(--space-sm);
  }

  .form-actions-right {
    width: 100%;
    justify-content: flex-end;
  }

  .step-form {
    max-width: 100%;
  }
}
</style>
