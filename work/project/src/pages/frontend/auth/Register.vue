<template>
  <div class="register-page">
    <!-- 左侧品牌区 -->
    <div class="register-brand">
      <div class="brand-content">
        <div class="brand-logo">
          <svg viewBox="0 0 48 48" fill="none" class="logo-icon">
            <rect width="48" height="48" rx="12" fill="currentColor" fill-opacity="0.15" />
            <path d="M16 24h16M24 16v16" stroke="currentColor" stroke-width="3" stroke-linecap="round" />
          </svg>
          <span class="brand-name">优选商城</span>
        </div>
        <p class="brand-slogan">加入我们，开启品质生活</p>
      </div>
    </div>

    <!-- 右侧表单区 -->
    <div class="register-form-area">
      <div class="form-card">
        <!-- 返回按钮 -->
        <button class="back-btn" @click="goLogin">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
          <span>返回登录</span>
        </button>

        <h1 class="form-title">创建账号</h1>
        <p class="form-subtitle">注册后即可享受专属优惠</p>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          @submit.prevent="handleRegister"
        >
          <!-- 手机号 -->
          <el-form-item prop="phone" label="手机号">
            <el-input
              v-model="form.phone"
              placeholder="请输入手机号"
              maxlength="11"
              :prefix-icon="PhoneIcon"
              size="large"
              clearable
            />
          </el-form-item>

          <!-- 验证码 -->
          <el-form-item prop="verifyCode" label="验证码">
            <div class="verify-code-row">
              <el-input
                v-model="form.verifyCode"
                placeholder="请输入验证码"
                maxlength="6"
                :prefix-icon="MessageIcon"
                size="large"
                clearable
              />
              <el-button
                :type="codeSent ? 'default' : 'primary'"
                size="large"
                :disabled="codeSent || !phoneValid"
                :loading="sendingCode"
                class="send-code-btn"
                @click="handleSendCode"
              >
                {{ codeBtnText }}
              </el-button>
            </div>
          </el-form-item>

          <!-- 昵称 -->
          <el-form-item prop="nickname" label="昵称">
            <el-input
              v-model="form.nickname"
              placeholder="给自己取个昵称吧"
              maxlength="20"
              :prefix-icon="UserIcon"
              size="large"
              show-word-limit
              clearable
            />
          </el-form-item>

          <!-- 密码 -->
          <el-form-item prop="password" label="设置密码">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请设置6-20位密码"
              :prefix-icon="LockIcon"
              size="large"
              show-password
              clearable
            />
          </el-form-item>

          <!-- 确认密码 -->
          <el-form-item prop="confirmPassword" label="确认密码">
            <el-input
              v-model="form.confirmPassword"
              type="password"
              placeholder="请再次输入密码"
              :prefix-icon="LockIcon"
              size="large"
              show-password
              clearable
            />
          </el-form-item>

          <!-- 协议勾选 -->
          <el-form-item prop="agreed">
            <el-checkbox v-model="form.agreed" class="agreement-check">
              <span class="agreement-text">
                我已阅读并同意
                <el-link type="primary" :underline="false">《用户协议》</el-link>
                和
                <el-link type="primary" :underline="false">《隐私政策》</el-link>
              </span>
            </el-checkbox>
          </el-form-item>

          <!-- 注册按钮 -->
          <el-form-item>
            <el-button
              type="primary"
              size="large"
              :loading="loading"
              class="register-btn"
              native-type="submit"
            >
              {{ loading ? '注册中...' : '注册' }}
            </el-button>
          </el-form-item>
        </el-form>

        <!-- 底部链接 -->
        <div class="form-footer">
          <span class="footer-text">已有账号？</span>
          <el-link type="primary" :underline="false" @click="goLogin">去登录</el-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 买家端注册页 — 手机号+验证码注册
 */
import { ref, reactive, computed, onBeforeUnmount, shallowRef } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Phone, Message, User, Lock } from '@element-plus/icons-vue';
import { login as loginApi, sendCode as sendCodeApi } from '@/api/auth';
import { useUserStore } from '@/stores/user';

const router = useRouter();
const userStore = useUserStore();

const PhoneIcon = shallowRef(Phone);
const MessageIcon = shallowRef(Message);
const UserIcon = shallowRef(User);
const LockIcon = shallowRef(Lock);

const formRef = ref(null);
const loading = ref(false);
const sendingCode = ref(false);
const codeSent = ref(false);
const countdown = ref(0);
let countdownTimer = null;

const form = reactive({
  phone: '',
  verifyCode: '',
  nickname: '',
  password: '',
  confirmPassword: '',
  agreed: false,
});

const phoneValid = computed(() => /^1[3-9]\d{9}$/.test(form.phone));

const validateConfirmPassword = (_rule, value, callback) => {
  if (!value) {
    callback(new Error('请再次输入密码'));
  } else if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'));
  } else {
    callback();
  }
};

const rules = {
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' },
  ],
  verifyCode: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 6, message: '验证码为6位数字', trigger: 'blur' },
  ],
  nickname: [
    { required: true, message: '请输入昵称', trigger: 'blur' },
    { min: 2, max: 20, message: '昵称长度为2-20个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请设置密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度为6-20位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' },
  ],
  agreed: [
    {
      validator: (_rule, value, callback) => {
        if (!value) {
          callback(new Error('请阅读并同意用户协议和隐私政策'));
        } else {
          callback();
        }
      },
      trigger: 'change',
    },
  ],
};

const codeBtnText = computed(() => {
  if (sendingCode.value) return '发送中...';
  if (codeSent.value && countdown.value > 0) return `${countdown.value}s 后重发`;
  return '获取验证码';
});

function startCountdown() {
  codeSent.value = true;
  countdown.value = 60;
  countdownTimer = setInterval(() => {
    countdown.value--;
    if (countdown.value <= 0) {
      clearInterval(countdownTimer);
      countdownTimer = null;
      codeSent.value = false;
    }
  }, 1000);
}

async function handleSendCode() {
  if (!phoneValid.value) {
    ElMessage.warning('请先输入正确的手机号');
    return;
  }
  sendingCode.value = true;
  try {
    await sendCodeApi({ phone: form.phone });
    ElMessage.success('验证码已发送');
    startCountdown();
  } catch (err) {
    ElMessage.error(err?.response?.data?.message || err?.message || '发送验证码失败');
  } finally {
    sendingCode.value = false;
  }
}

async function handleRegister() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;

  loading.value = true;
  try {
    // 注册使用同一 login 接口（后端根据 isNewUser 判断）
    const res = await loginApi({
      phone: form.phone,
      verifyCode: form.verifyCode,
      nickname: form.nickname,
      password: form.password,
    });
    const data = res.data || res;

    // 🛑 使用 store action 写入 token（会同步写入 localStorage）
    userStore.setToken(data.token, data.refreshToken);
    if (data.userId != null) {
      userStore.userId = data.userId;
    }
    if (data.role) {
      userStore.userRole = data.role;
    }

    ElMessage.success('注册成功，欢迎加入！');
    router.push('/');
  } catch (err) {
    ElMessage.error(err?.response?.data?.message || err?.message || '注册失败，请重试');
  } finally {
    loading.value = false;
  }
}

function goLogin() {
  router.push({ name: 'Login' });
}

onBeforeUnmount(() => {
  if (countdownTimer) {
    clearInterval(countdownTimer);
    countdownTimer = null;
  }
});
</script>

<style scoped>
/* ===== 买家暖橙主题变量 ===== */
.register-page {
  --buyer-primary: #f97316;
  --buyer-primary-light: #fff7ed;
  --buyer-primary-lighter: #ffedd5;
  --buyer-primary-dark: #ea580c;
  --buyer-primary-gradient: linear-gradient(135deg, #ea580c 0%, #f97316 50%, #fb923c 100%);

  display: flex;
  min-height: 100vh;
  background: #fafaf9;
}

/* ===== 左侧品牌区 ===== */
.register-brand {
  flex: 0 0 42%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--buyer-primary-gradient);
  position: relative;
  overflow: hidden;
}

.register-brand::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 30% 40%, rgba(255,255,255,0.12) 0%, transparent 45%),
    radial-gradient(circle at 70% 60%, rgba(255,255,255,0.08) 0%, transparent 40%);
}

.brand-content {
  position: relative;
  z-index: 1;
  text-align: center;
  color: #fff;
}

.brand-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-bottom: 16px;
}

.logo-icon {
  width: 56px;
  height: 56px;
  color: #fff;
}

.brand-name {
  font-size: 2.25rem;
  font-weight: 700;
  letter-spacing: 2px;
}

.brand-slogan {
  font-size: 1.125rem;
  opacity: 0.9;
  letter-spacing: 4px;
}

/* ===== 右侧表单区 ===== */
.register-form-area {
  flex: 0 0 58%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.form-card {
  width: 100%;
  max-width: 420px;
}

/* ===== 返回按钮 ===== */
.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: none;
  color: #78716c;
  font-size: 0.875rem;
  cursor: pointer;
  padding: 4px 0;
  margin-bottom: 16px;
  transition: color 0.15s;
}

.back-btn:hover {
  color: var(--buyer-primary);
}

.form-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: #1c1917;
  margin: 0 0 8px;
}

.form-subtitle {
  font-size: var(--app-font-base, 0.875rem);
  color: #78716c;
  margin: 0 0 28px;
}

/* ===== 表单样式 ===== */
:deep(.el-form-item) {
  margin-bottom: 18px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
  color: #44403c;
  padding-bottom: 6px;
}

:deep(.el-input__wrapper) {
  border-radius: var(--app-radius-base, 8px);
  box-shadow: 0 0 0 1px #e7e5e4 inset;
  transition: box-shadow 0.15s var(--app-ease-standard, cubic-bezier(0.4,0,0.2,1));
}

:deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #d6d3d1 inset;
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--buyer-primary) inset, 0 0 0 3px rgba(249,115,22,0.12);
}

/* ===== 验证码行 ===== */
.verify-code-row {
  display: flex;
  gap: 12px;
}

.verify-code-row .el-input {
  flex: 1;
}

.send-code-btn {
  flex-shrink: 0;
  min-width: 120px;
  height: 40px;
  border-radius: var(--app-radius-base, 8px);
  font-size: 0.8125rem;
}

.send-code-btn.el-button--primary {
  background: var(--buyer-primary);
  border-color: var(--buyer-primary);
}

.send-code-btn.el-button--primary:hover {
  background: var(--buyer-primary-dark);
  border-color: var(--buyer-primary-dark);
}

/* ===== 协议勾选 ===== */
.agreement-check {
  margin-top: 4px;
}

.agreement-text {
  font-size: 0.8125rem;
  color: #78716c;
  line-height: 1.5;
}

:deep(.el-link.el-link--primary) {
  color: var(--buyer-primary);
  font-size: 0.8125rem;
}

/* ===== 注册按钮 ===== */
.register-btn {
  width: 100%;
  height: 44px;
  border-radius: var(--app-radius-base, 8px);
  font-size: 1rem;
  font-weight: 600;
  background: var(--buyer-primary);
  border-color: var(--buyer-primary);
  letter-spacing: 2px;
  margin-top: 8px;
  transition: all 0.15s var(--app-ease-standard, cubic-bezier(0.4,0,0.2,1));
}

.register-btn:hover {
  background: var(--buyer-primary-dark);
  border-color: var(--buyer-primary-dark);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(249,115,22,0.35);
}

.register-btn:active {
  transform: translateY(0);
}

/* ===== 底部链接 ===== */
.form-footer {
  text-align: center;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #f5f5f4;
}

.footer-text {
  font-size: 0.875rem;
  color: #78716c;
}

:deep(.el-link.el-link--primary) {
  color: var(--buyer-primary);
  font-weight: 500;
}

:deep(.el-link.el-link--primary:hover) {
  color: var(--buyer-primary-dark);
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .register-page {
    flex-direction: column;
  }

  .register-brand {
    flex: none;
    padding: 40px 24px;
    min-height: 180px;
  }

  .brand-name {
    font-size: 1.75rem;
  }

  .brand-slogan {
    font-size: 0.9375rem;
    letter-spacing: 2px;
  }

  .register-form-area {
    flex: 1;
    padding: 28px 20px;
  }

  .form-title {
    font-size: 1.5rem;
  }

  .verify-code-row {
    flex-direction: column;
    gap: 8px;
  }

  .send-code-btn {
    width: 100%;
    min-width: unset;
  }
}
</style>
