<template>
  <div class="onboarding-container">
    <div class="onboarding-card">
      <div class="onboarding-header">
        <h2 class="onboarding-title">商家入驻</h2>
        <p class="onboarding-subtitle">注册商家账号，开启电商之旅</p>
      </div>

      <el-steps :active="1" align-center class="onboarding-steps">
        <el-step title="注册账号" description="创建商家账号" />
        <el-step title="资质上传" description="提交营业资质" />
        <el-step title="店铺信息" description="完善店铺资料" />
        <el-step title="等待审核" description="平台审核中" />
      </el-steps>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
        label-position="right"
        class="onboarding-form"
      >
        <el-form-item label="手机号" prop="phone">
          <el-input
            v-model="form.phone"
            placeholder="请输入手机号"
            maxlength="11"
            clearable
          />
        </el-form-item>

        <el-form-item label="验证码" prop="verifyCode">
          <div class="verify-code-row">
            <el-input
              v-model="form.verifyCode"
              placeholder="请输入验证码"
              maxlength="6"
              class="verify-input"
            />
            <el-button
              :disabled="codeCountdown > 0"
              :loading="sendingCode"
              @click="sendVerifyCode"
              class="verify-btn"
            >
              {{ codeCountdown > 0 ? `${codeCountdown}s后重发` : '获取验证码' }}
            </el-button>
          </div>
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码（6-20位）"
            show-password
            maxlength="20"
          />
        </el-form-item>

        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            show-password
            maxlength="20"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="submitting"
            @click="handleRegister"
            class="submit-btn"
          >
            注册并下一步
          </el-button>
        </el-form-item>
      </el-form>

      <div class="onboarding-footer">
        已有账号？<router-link to="/login" class="footer-link">立即登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 商家入驻 - 第一步：注册
 * 提交手机号、验证码、密码，注册成功后跳转资质上传页
 */
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { registerMerchant } from '@/api/merchant'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref(null)
const submitting = ref(false)
const sendingCode = ref(false)
const codeCountdown = ref(0)
let countdownTimer = null

const form = reactive({
  phone: '',
  verifyCode: '',
  password: '',
  confirmPassword: ''
})

const validateConfirmPassword = (_rule, value, callback) => {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确', trigger: 'blur' }
  ],
  verifyCode: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 6, message: '验证码为6位数字', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度6-20位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

function sendVerifyCode() {
  if (!/^1[3-9]\d{9}$/.test(form.phone)) {
    ElMessage.warning('请先输入正确的手机号')
    return
  }
  sendingCode.value = true
  // 模拟发送验证码（实际应调用发送验证码接口）
  setTimeout(() => {
    sendingCode.value = false
    ElMessage.success('验证码已发送')
    codeCountdown.value = 60
    countdownTimer = setInterval(() => {
      codeCountdown.value--
      if (codeCountdown.value <= 0) {
        clearInterval(countdownTimer)
        countdownTimer = null
      }
    }, 1000)
  }, 800)
}

async function handleRegister() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const res = await registerMerchant({
      phone: form.phone,
      verifyCode: form.verifyCode,
      password: form.password
    })
    const { token, shopId } = res
    if (token) {
      userStore.setToken(token)
    }
    ElMessage.success('注册成功')
    router.push({ name: 'MerchantQualification', state: { shopId } })
  } catch (err) {
    const msg = err?.response?.data?.message || err?.message || '注册失败，请稍后重试'
    ElMessage.error(msg)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.onboarding-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a2332 0%, #1e3a5f 50%, #1a2332 100%);
  padding: var(--app-space-xl, 24px);
}

.onboarding-card {
  width: 100%;
  max-width: 520px;
  background: var(--app-bg-container, #ffffff);
  border-radius: var(--app-radius-lg, 16px);
  box-shadow: var(--app-shadow-level-3, 0 12px 32px rgba(0,0,0,0.12));
  padding: 40px 36px;
}

.onboarding-header {
  text-align: center;
  margin-bottom: 28px;
}

.onboarding-title {
  font-size: var(--app-font-3xl, 1.5rem);
  font-weight: 700;
  color: #1e3a5f;
  margin: 0 0 8px 0;
}

.onboarding-subtitle {
  font-size: var(--app-font-base, 0.875rem);
  color: var(--app-text-secondary, #6b7280);
  margin: 0;
}

.onboarding-steps {
  margin-bottom: 32px;
}

.onboarding-steps :deep(.el-step__title) {
  font-size: var(--app-font-xs, 0.75rem);
}

.onboarding-steps :deep(.el-step__description) {
  font-size: var(--app-font-xs, 0.75rem);
}

.onboarding-form {
  margin-top: 8px;
}

.verify-code-row {
  display: flex;
  gap: var(--app-space-sm, 8px);
  width: 100%;
}

.verify-input {
  flex: 1;
}

.verify-btn {
  flex-shrink: 0;
  min-width: 120px;
}

.submit-btn {
  width: 100%;
  height: 44px;
  font-size: var(--app-font-lg, 1rem);
  font-weight: 600;
  background: #1e3a5f;
  border-color: #1e3a5f;
  border-radius: var(--app-radius-base, 8px);
  transition: all 0.15s var(--app-ease-standard, cubic-bezier(0.4,0,0.2,1));
}

.submit-btn:hover {
  background: #2c5282;
  border-color: #2c5282;
}

.submit-btn:active {
  background: #162d4a;
  border-color: #162d4a;
}

.onboarding-footer {
  text-align: center;
  margin-top: 20px;
  font-size: var(--app-font-sm, 0.8125rem);
  color: var(--app-text-secondary, #6b7280);
}

.footer-link {
  color: #1e3a5f;
  font-weight: 500;
  text-decoration: none;
}

.footer-link:hover {
  color: #2c5282;
  text-decoration: underline;
}

@media (max-width: 576px) {
  .onboarding-card {
    padding: 28px 20px;
  }
}
</style>
