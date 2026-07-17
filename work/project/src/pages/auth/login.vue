<template>
  <div class="auth-page">
    <div class="auth-card">
      <!-- Logo 区域 -->
      <div class="auth-logo">
        <svg class="auth-logo-icon" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect width="48" height="48" rx="12" fill="var(--color-primary-500)" />
          <path d="M14 32C14 26.477 18.477 22 24 22C29.523 22 34 26.477 34 32" stroke="white" stroke-width="2.5" stroke-linecap="round" />
          <circle cx="24" cy="16" r="5" stroke="white" stroke-width="2.5" />
        </svg>
        <span class="auth-brand">鹊桥</span>
      </div>

      <!-- Tab 切换 -->
      <div class="auth-tabs">
        <button
          :class="['auth-tab', { active: activeTab === 'login' }]"
          @click="switchTab('login')"
        >
          登录
        </button>
        <button
          :class="['auth-tab', { active: activeTab === 'register' }]"
          @click="switchTab('register')"
        >
          注册
        </button>
      </div>

      <!-- ========== 登录面板 ========== -->
      <div v-if="activeTab === 'login'" class="auth-panel">
        <h2 class="auth-title">欢迎回来</h2>
        <p class="auth-subtitle">请输入您的账户信息</p>

        <el-form
          ref="loginFormRef"
          :model="loginForm"
          :rules="loginRules"
          label-position="top"
          @submit.prevent="handleLogin"
        >
          <el-form-item prop="mobile">
            <el-input
              v-model="loginForm.mobile"
              placeholder="手机号"
              maxlength="11"
              :prefix-icon="PhoneIcon"
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="密码"
              show-password
              :prefix-icon="LockIcon"
              @keyup.enter="handleLogin"
            />
          </el-form-item>

          <div class="auth-extra">
            <a class="auth-link" href="#">忘记密码？</a>
          </div>

          <el-button
            class="auth-submit"
            type="primary"
            :loading="loginLoading"
            :disabled="loginLoading"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form>

        <p class="auth-switch">
          还没有账户？
          <button class="auth-switch-btn" @click="switchTab('register')">立即注册</button>
        </p>
      </div>

      <!-- ========== 注册面板 ========== -->
      <div v-if="activeTab === 'register'" class="auth-panel">
        <h2 class="auth-title">创建账户</h2>
        <p class="auth-subtitle">填写以下信息，加入鹊桥</p>

        <el-form
          ref="registerFormRef"
          :model="registerForm"
          :rules="registerRules"
          label-position="top"
          @submit.prevent="handleRegister"
        >
          <el-form-item prop="mobile">
            <el-input
              v-model="registerForm.mobile"
              placeholder="手机号"
              maxlength="11"
              :prefix-icon="PhoneIcon"
            />
          </el-form-item>

          <el-form-item prop="code">
            <div class="auth-code-row">
              <el-input
                v-model="registerForm.code"
                placeholder="验证码"
                maxlength="6"
                :prefix-icon="MessageIcon"
              />
              <el-button
                class="auth-code-btn"
                :disabled="codeCooldown > 0"
                @click="handleSendCode"
              >
                {{ codeCooldown > 0 ? `${codeCooldown}秒后重发` : '发送验证码' }}
              </el-button>
            </div>
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="registerForm.password"
              type="password"
              placeholder="设置密码（至少8位，含数字和字母）"
              show-password
              :prefix-icon="LockIcon"
            />
          </el-form-item>

          <!-- 密码强度指示器 -->
          <div v-if="registerForm.password" class="auth-password-strength">
            <div class="strength-bar">
              <div
                v-for="i in 4"
                :key="i"
                :class="['strength-segment', `level-${passwordStrength.level}`]"
                :style="{ opacity: i <= passwordStrength.segments ? 1 : 0.2 }"
              />
            </div>
            <span :class="['strength-text', `text-${passwordStrength.level}`]">
              {{ passwordStrength.text }}
            </span>
          </div>

          <el-form-item prop="agreed">
            <el-checkbox v-model="registerForm.agreed">
              <span class="auth-agreement-text">
                我已阅读并同意
                <a class="auth-link" href="#">《用户协议》</a>
                和
                <a class="auth-link" href="#">《隐私政策》</a>
              </span>
            </el-checkbox>
          </el-form-item>

          <el-button
            class="auth-submit"
            type="primary"
            :loading="registerLoading"
            :disabled="registerLoading"
            @click="handleRegister"
          >
            注册
          </el-button>
        </el-form>

        <p class="auth-switch">
          已有账户？
          <button class="auth-switch-btn" @click="switchTab('login')">立即登录</button>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, shallowRef, markRaw } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { ElMessage } from 'element-plus';
import { useUserStore } from '@/stores/user';

// ── SVG Icons (shallowRef to avoid reactive proxying) ──
const PhoneIcon = shallowRef(markRaw({
  render() {
    return null;
  }
}));

// Re-assign with proper h() render functions
import { h } from 'vue';
PhoneIcon.value = markRaw({
  render() {
    return h('svg', {
      viewBox: '0 0 24 24',
      width: '16',
      height: '16',
      fill: 'none',
      stroke: 'currentColor',
      'stroke-width': '2',
      'stroke-linecap': 'round',
      'stroke-linejoin': 'round',
    }, [
      h('rect', { x: '5', y: '2', width: '14', height: '20', rx: '2', ry: '2' }),
      h('line', { x1: '12', y1: '18', x2: '12.01', y2: '18' }),
    ]);
  },
});

const LockIcon = shallowRef(markRaw({
  render() {
    return h('svg', {
      viewBox: '0 0 24 24',
      width: '16',
      height: '16',
      fill: 'none',
      stroke: 'currentColor',
      'stroke-width': '2',
      'stroke-linecap': 'round',
      'stroke-linejoin': 'round',
    }, [
      h('rect', { x: '3', y: '11', width: '18', height: '11', rx: '2', ry: '2' }),
      h('path', { d: 'M7 11V7a5 5 0 0 1 10 0v4' }),
    ]);
  },
}));

const MessageIcon = shallowRef(markRaw({
  render() {
    return h('svg', {
      viewBox: '0 0 24 24',
      width: '16',
      height: '16',
      fill: 'none',
      stroke: 'currentColor',
      'stroke-width': '2',
      'stroke-linecap': 'round',
      'stroke-linejoin': 'round',
    }, [
      h('path', { d: 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z' }),
    ]);
  },
}));

// ── Router & Store ──
const router = useRouter();
const route = useRoute();
const userStore = useUserStore();

// ── Tab State ──
const activeTab = ref('login');

function switchTab(tab) {
  activeTab.value = tab;
}

// ── Login Form ──
const loginFormRef = ref(null);
const loginLoading = ref(false);
const loginForm = reactive({
  mobile: '',
  password: '',
});

const loginRules = {
  mobile: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' },
  ],
};

async function handleLogin() {
  if (!loginFormRef.value) return;

  try {
    await loginFormRef.value.validate();
  } catch {
    return;
  }

  loginLoading.value = true;
  try {
    await userStore.login({
      mobile: loginForm.mobile,
      password: loginForm.password,
    });

    ElMessage.success('登录成功');

    // 登录成功后回跳来源页
    const redirectPath = route.query.redirect;
    if (redirectPath) {
      router.push(redirectPath);
    } else if (userStore.role === 'merchant') {
      router.push({ name: 'MerchantDashboard' });
    } else if (userStore.role === 'admin') {
      router.push({ name: 'AdminDashboard' });
    } else {
      router.push('/');
    }
  } catch (err) {
    const code = err?.response?.data?.code;
    const msg = err?.response?.data?.message;

    if (code === 'PHONE_NOT_FOUND') {
      ElMessage.error(msg || '手机号未注册');
    } else if (code === 'PASSWORD_WRONG') {
      ElMessage.error(msg || '密码不正确，请重试');
      loginForm.password = '';
    } else if (code === 'ACCOUNT_DISABLED') {
      ElMessage.error(msg || '账号已被禁用，请联系客服');
    } else {
      ElMessage.error(msg || '网络连接失败，请检查网络后重试');
    }
  } finally {
    loginLoading.value = false;
  }
}

// ── Register Form ──
const registerFormRef = ref(null);
const registerLoading = ref(false);
const codeCooldown = ref(0);
let cooldownTimer = null;

const registerForm = reactive({
  mobile: '',
  code: '',
  password: '',
  agreed: false,
});

const validatePassword = (_rule, value, callback) => {
  if (!value) {
    callback(new Error('请设置密码'));
    return;
  }
  if (value.length < 8) {
    callback(new Error('密码至少8位'));
    return;
  }
  if (!/[a-zA-Z]/.test(value) || !/\d/.test(value)) {
    callback(new Error('密码必须包含数字和字母'));
    return;
  }
  callback();
};

const registerRules = {
  mobile: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' },
  ],
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { pattern: /^\d{6}$/, message: '验证码为6位数字', trigger: 'blur' },
  ],
  password: [
    { required: true, validator: validatePassword, trigger: 'blur' },
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

// ── Password Strength ──
const passwordStrength = computed(() => {
  const pwd = registerForm.password;
  if (!pwd) return { level: '', segments: 0, text: '' };

  const hasDigit = /\d/.test(pwd);
  const hasLetter = /[a-zA-Z]/.test(pwd);
  const hasUpper = /[A-Z]/.test(pwd);
  const hasLower = /[a-z]/.test(pwd);
  const hasSymbol = /[^a-zA-Z0-9]/.test(pwd);

  if (pwd.length < 6) {
    return { level: 'error', segments: 1, text: '密码太短' };
  }
  if (pwd.length < 8 || !hasDigit || !hasLetter) {
    return { level: 'warning', segments: 2, text: '密码强度一般' };
  }
  if (pwd.length >= 10 && hasUpper && hasLower && hasDigit && hasSymbol) {
    return { level: 'success', segments: 4, text: '密码强度优秀' };
  }
  return { level: 'success', segments: 3, text: '密码强度良好' };
});

function handleSendCode() {
  // 先校验手机号
  if (!registerForm.mobile || !/^1[3-9]\d{9}$/.test(registerForm.mobile)) {
    ElMessage.warning('请先输入正确的手机号');
    return;
  }

  // 启动倒计时
  codeCooldown.value = 60;
  if (cooldownTimer) clearInterval(cooldownTimer);
  cooldownTimer = setInterval(() => {
    codeCooldown.value--;
    if (codeCooldown.value <= 0) {
      clearInterval(cooldownTimer);
      cooldownTimer = null;
    }
  }, 1000);

  // 后端 mock 模式下验证码为 123456，提示用户
  ElMessage.success({ message: '[模拟] 验证码: 123456', duration: 10000 });
}

async function handleRegister() {
  if (!registerFormRef.value) return;

  try {
    await registerFormRef.value.validate();
  } catch {
    return;
  }

  registerLoading.value = true;
  try {
    await userStore.register({
      mobile: registerForm.mobile,
      code: registerForm.code,
      password: registerForm.password,
    });

    ElMessage.success('注册成功！欢迎加入鹊桥');

    // 注册成功后回跳来源页
    const redirectPath = route.query.redirect || '/';
    router.push(redirectPath);
  } catch (err) {
    const code = err?.response?.data?.code;
    const msg = err?.response?.data?.message;

    if (code === 'PHONE_EXISTS') {
      ElMessage.error(msg || '该手机号已注册，请直接登录');
    } else if (code === 'INVALID_CODE') {
      ElMessage.error(msg || '验证码不正确，请重新输入');
      registerForm.code = '';
    } else if (code === 'CODE_EXPIRED') {
      ElMessage.error(msg || '验证码已过期，请重新获取');
      registerForm.code = '';
    } else if (code === 'WEAK_PASSWORD') {
      ElMessage.error(msg || '密码强度不足，至少8位含数字和字母');
    } else if (code === 'CODE_RATE_LIMIT') {
      ElMessage.error(msg || '验证码发送过于频繁，请60秒后再试');
    } else {
      ElMessage.error(msg || '网络连接失败，请检查网络后重试');
    }
  } finally {
    registerLoading.value = false;
  }
}
</script>

<style scoped>
/* ── 页面背景 (Layer 1 光斑) ── */
.auth-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background-color: hsl(25, 5%, 97%);
  background-image: radial-gradient(ellipse at 30% 20%, hsl(25, 20%, 92%) 0%, transparent 60%);
  padding: var(--space-lg);
}

/* ── 认证卡片 ── */
.auth-card {
  background: hsl(25, 3%, 99%);
  border-radius: var(--radius-lg, 30px);
  box-shadow: var(--shadow-md, 0 4px 6px -1px rgba(30,28,27,0.08), 0 2px 4px -1px rgba(30,28,27,0.05));
  padding: var(--space-xl, 32px);
  max-width: 420px;
  width: 100%;
}

/* ── Logo ── */
.auth-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm, 8px);
  margin-bottom: var(--space-lg, 24px);
}

.auth-logo-icon {
  width: 48px;
  height: 48px;
}

.auth-brand {
  font-size: var(--font-size-xl, 21px);
  font-weight: 700;
  color: var(--color-text-primary, hsl(25, 9%, 12%));
  letter-spacing: 0.5px;
}

/* ── Tab 切换 ── */
.auth-tabs {
  display: flex;
  border-bottom: 1px solid hsl(25, 5%, 86%);
  margin-bottom: var(--space-lg, 24px);
}

.auth-tab {
  flex: 1;
  padding: var(--space-sm, 8px) 0;
  border: none;
  background: transparent;
  font-size: var(--font-size-md, 15.75px);
  font-weight: 500;
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
  cursor: pointer;
  position: relative;
  transition: color var(--duration-fast, 150ms) var(--ease-smooth, cubic-bezier(0.16, 1, 0.3, 1));
  font-family: inherit;
}

.auth-tab.active {
  color: var(--color-primary-500, hsl(25, 85%, 55%));
  font-weight: 600;
}

.auth-tab.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 50%;
  transform: translateX(-50%);
  width: 40px;
  height: 2px;
  background: var(--color-primary-500, hsl(25, 85%, 55%));
  border-radius: 1px;
}

.auth-tab:hover:not(.active) {
  color: var(--color-text-secondary, hsl(25, 7%, 42%));
}

/* ── 面板 ── */
.auth-panel {
  animation: fadeInUp var(--duration-fast, 150ms) var(--ease-smooth, cubic-bezier(0.16, 1, 0.3, 1));
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ── 标题 ── */
.auth-title {
  font-size: var(--font-size-xl, 21px);
  font-weight: 700;
  color: var(--color-text-primary, hsl(25, 9%, 12%));
  margin: 0 0 var(--space-xs, 4px);
  text-align: center;
}

.auth-subtitle {
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
  margin: 0 0 var(--space-lg, 24px);
  text-align: center;
  line-height: var(--line-height-normal, 1.5);
}

/* ── 表单 ── */
.auth-panel :deep(.el-form-item) {
  margin-bottom: var(--space-md, 16px);
}

.auth-panel :deep(.el-form-item__label) {
  display: none;
}

.auth-panel :deep(.el-input__wrapper) {
  min-height: 44px;
  border-radius: var(--radius-md, 20px);
  border-color: var(--color-border, hsl(25, 7%, 90%));
  box-shadow: none;
  transition: border-color var(--duration-fast, 150ms) var(--ease-smooth, cubic-bezier(0.16, 1, 0.3, 1)),
    box-shadow var(--duration-fast, 150ms) var(--ease-smooth, cubic-bezier(0.16, 1, 0.3, 1));
}

.auth-panel :deep(.el-input__wrapper:hover) {
  border-color: var(--color-primary-300, hsl(25, 72%, 70%));
}

.auth-panel :deep(.el-input.is-focus .el-input__wrapper) {
  border-color: var(--color-primary-500, hsl(25, 85%, 55%));
  box-shadow: 0 0 0 3px hsla(25, 80%, 45%, 0.12);
}

.auth-panel :deep(.el-input.is-error .el-input__wrapper) {
  border-color: var(--color-error, hsl(0, 80%, 52%));
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.15);
}

.auth-panel :deep(.el-input__inner) {
  font-size: var(--font-size-base, 14px);
  line-height: var(--line-height-normal, 1.5);
}

.auth-panel :deep(.el-input__prefix-inner) {
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
}

/* ── 额外链接行 ── */
.auth-extra {
  display: flex;
  justify-content: flex-end;
  margin-top: calc(-1 * var(--space-sm, 8px));
  margin-bottom: var(--space-md, 16px);
}

.auth-link {
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-secondary, hsl(25, 7%, 42%));
  text-decoration: none;
  cursor: pointer;
  transition: color var(--duration-fast, 150ms);
}

.auth-link:hover {
  color: var(--color-primary-500, hsl(25, 85%, 55%));
}

/* ── 验证码行 ── */
.auth-code-row {
  display: flex;
  gap: var(--space-sm, 8px);
  width: 100%;
}

.auth-code-row :deep(.el-input) {
  flex: 1;
}

.auth-code-btn {
  min-width: 110px;
  height: 44px;
  border-radius: var(--radius-md, 20px);
  font-size: var(--font-size-sm, 12.25px);
  white-space: nowrap;
}

/* ── 密码强度指示器 ── */
.auth-password-strength {
  margin-top: calc(-1 * var(--space-sm, 8px));
  margin-bottom: var(--space-md, 16px);
}

.strength-bar {
  display: flex;
  gap: 4px;
  margin-bottom: 4px;
}

.strength-segment {
  flex: 1;
  height: 3px;
  border-radius: 2px;
  transition: opacity var(--duration-fast, 150ms), background-color var(--duration-fast, 150ms);
}

.strength-segment.level-error {
  background-color: var(--color-error, hsl(0, 80%, 52%));
}

.strength-segment.level-warning {
  background-color: var(--color-warning, hsl(38, 95%, 50%));
}

.strength-segment.level-success {
  background-color: var(--color-success, hsl(145, 70%, 42%));
}

.strength-text {
  font-size: var(--font-size-xs, 10.5px);
  line-height: var(--line-height-tight, 1.25);
}

.strength-text.text-error {
  color: var(--color-error, hsl(0, 80%, 52%));
}

.strength-text.text-warning {
  color: var(--color-warning, hsl(38, 95%, 50%));
}

.strength-text.text-success {
  color: var(--color-success, hsl(145, 70%, 42%));
}

/* ── 协议复选框 ── */
.auth-agreement-text {
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-secondary, hsl(25, 7%, 42%));
}

/* ── 提交按钮 ── */
.auth-submit {
  width: 100%;
  min-height: 44px;
  border-radius: var(--radius-md, 20px);
  font-size: var(--font-size-base, 14px);
  font-weight: 600;
  margin-top: var(--space-sm, 8px);
  background-color: hsl(25, 70%, 48%);
  border-color: hsl(25, 70%, 48%);
}

.auth-submit:hover:not(:disabled) {
  background-color: hsl(25, 70%, 40%);
  border-color: hsl(25, 70%, 40%);
}

.auth-submit:active:not(:disabled) {
  background-color: hsl(25, 70%, 36%);
  border-color: hsl(25, 70%, 36%);
}

/* ── 底部切换 ── */
.auth-switch {
  text-align: center;
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
  margin-top: var(--space-lg, 24px);
  margin-bottom: 0;
}

.auth-switch-btn {
  border: none;
  background: transparent;
  color: var(--color-primary-500, hsl(25, 85%, 55%));
  font-size: var(--font-size-sm, 12.25px);
  font-weight: 500;
  cursor: pointer;
  padding: 0;
  font-family: inherit;
  transition: color var(--duration-fast, 150ms);
}

.auth-switch-btn:hover {
  color: var(--color-primary-600, hsl(25, 85%, 45%));
  text-decoration: underline;
}

/* ── 响应式 ── */
@media (max-width: 480px) {
  .auth-page {
    padding: 0;
    background-image: none;
    align-items: flex-start;
  }

  .auth-card {
    border-radius: 0;
    box-shadow: none;
    max-width: 100%;
    min-height: 100vh;
    padding: var(--space-xl, 32px) var(--space-lg, 24px);
  }
}

@media (min-width: 481px) and (max-width: 767px) {
  .auth-card {
    max-width: 90vw;
  }
}
</style>
