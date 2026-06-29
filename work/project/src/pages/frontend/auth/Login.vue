<template>
  <div class="login-page">
    <!-- 左侧品牌区 -->
    <div class="login-brand">
      <div class="brand-content">
        <div class="brand-logo">
          <svg viewBox="0 0 48 48" fill="none" class="logo-icon">
            <rect width="48" height="48" rx="12" fill="currentColor" fill-opacity="0.15" />
            <path d="M14 24l7 7 13-13" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <span class="brand-name">优选商城</span>
        </div>
        <p class="brand-slogan">品质生活，从这里开始</p>
      </div>
    </div>

    <!-- 右侧表单区 -->
    <div class="login-form-area">
      <div class="form-card">
        <h1 class="form-title">欢迎回来</h1>
        <p class="form-subtitle">使用手机号登录你的账号</p>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          @submit.prevent="handleLogin"
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

          <!-- 登录按钮 -->
          <el-form-item>
            <el-button
              type="primary"
              size="large"
              :loading="loading"
              class="login-btn"
              native-type="submit"
            >
              {{ loading ? '登录中...' : '登录' }}
            </el-button>
          </el-form-item>
        </el-form>

        <!-- 其他登录方式 -->
        <div class="divider">
          <span class="divider-text">其他登录方式</span>
        </div>

        <div class="oauth-actions">
          <el-button class="wechat-btn" size="large" @click="handleWechatLogin">
            <svg class="wechat-icon" viewBox="0 0 24 24" width="22" height="22">
              <path fill="#07C160" d="M8.691 2.188C3.891 2.188 0 5.476 0 9.53c0 2.212 1.17 4.203 2.99 5.55l-.747 2.237 2.585-1.29a9.77 9.77 0 001.863.53c.69.07 1.39.1 2.09.08-.05-.35-.08-.7-.08-1.06 0-3.94 3.66-7.15 8.16-7.5a5.34 5.34 0 00-.38-1.65C15.168 3.598 12.195 2.188 8.69 2.188zM5.86 7.09c.52 0 .94.38.94.84 0 .47-.42.85-.94.85-.51 0-.93-.38-.93-.85 0-.46.42-.84.93-.84zm5.57 0c.52 0 .94.38.94.84 0 .47-.42.85-.94.85-.52 0-.94-.38-.94-.85 0-.46.42-.84.94-.84z"/>
              <path fill="#07C160" d="M19.309 14.22c-4.2 0-7.62 2.93-7.62 6.55 0 3.62 3.42 6.56 7.62 6.56.67 0 1.32-.07 1.95-.22l2.04 1.02-.59-1.77c1.43-1.08 2.42-2.63 2.42-4.37 0-3.72-3.36-6.77-7.82-6.77zm-3.84 3.4c.41 0 .74.3.74.67 0 .36-.33.66-.74.66-.4 0-.73-.3-.73-.66 0-.37.33-.67.73-.67zm5.87.67c0 .36-.33.66-.74.66-.4 0-.73-.3-.73-.66 0-.37.33-.67.73-.67.41 0 .74.3.74.67zm1.84-1.84c.41 0 .74.3.74.67 0 .37-.33.66-.74.66-.4 0-.73-.29-.73-.66 0-.37.33-.67.73-.67z"/>
            </svg>
            <span>微信登录</span>
          </el-button>
        </div>

        <!-- 注册入口 -->
        <div class="form-footer">
          <span class="footer-text">还没有账号？</span>
          <el-link type="primary" :underline="false" @click="goRegister">注册新账号</el-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 买家端登录页 — 手机号+验证码登录 / 微信OAuth登录
 */
import { ref, reactive, computed, onBeforeUnmount, shallowRef } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Phone, Message } from '@element-plus/icons-vue';
import { login as loginApi, sendCode as sendCodeApi } from '@/api/auth';
import { useUserStore } from '@/stores/user';

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();

const PhoneIcon = shallowRef(Phone);
const MessageIcon = shallowRef(Message);

const formRef = ref(null);
const loading = ref(false);
const sendingCode = ref(false);
const codeSent = ref(false);
const countdown = ref(0);
let countdownTimer = null;

const form = reactive({
  phone: '',
  verifyCode: '',
});

const phoneValid = computed(() => /^1[3-9]\d{9}$/.test(form.phone));

const rules = {
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' },
  ],
  verifyCode: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 6, message: '验证码为6位数字', trigger: 'blur' },
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

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;

  loading.value = true;
  try {
    const res = await loginApi({ phone: form.phone, verifyCode: form.verifyCode });
    const data = res.data || res;

    // 🛑 使用 store action 写入 token（会同步写入 localStorage）
    userStore.setToken(data.token, data.refreshToken);
    if (data.userId != null) {
      userStore.userId = data.userId;
    }
    if (data.role) {
      userStore.userRole = data.role;
    }

    ElMessage.success('登录成功');

    // 跳转到登录前访问的页面或首页
    const redirect = route.query.redirect || '/';
    router.push(redirect);
  } catch (err) {
    ElMessage.error(err?.response?.data?.message || err?.message || '登录失败，请重试');
  } finally {
    loading.value = false;
  }
}

function handleWechatLogin() {
  // 微信OAuth：跳转微信授权页
  // 实际项目中由后端构造授权URL
  ElMessage.info('微信登录功能开发中，请使用手机号登录');
}

function goRegister() {
  router.push({ name: 'Register' });
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
.login-page {
  --buyer-primary: #f97316;
  --buyer-primary-light: #fff7ed;
  --buyer-primary-lighter: #ffedd5;
  --buyer-primary-dark: #ea580c;
  --buyer-primary-gradient: linear-gradient(135deg, #f97316 0%, #fb923c 50%, #fdba74 100%);

  display: flex;
  min-height: 100vh;
  background: #fafaf9;
}

/* ===== 左侧品牌区 ===== */
.login-brand {
  flex: 0 0 42%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--buyer-primary-gradient);
  position: relative;
  overflow: hidden;
}

.login-brand::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 30%, rgba(255,255,255,0.15) 0%, transparent 50%),
    radial-gradient(circle at 80% 70%, rgba(255,255,255,0.1) 0%, transparent 40%);
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
.login-form-area {
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

.form-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: #1c1917;
  margin: 0 0 8px;
}

.form-subtitle {
  font-size: var(--app-font-base, 0.875rem);
  color: #78716c;
  margin: 0 0 32px;
}

/* ===== 表单样式 ===== */
:deep(.el-form-item) {
  margin-bottom: 20px;
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

/* ===== 登录按钮 ===== */
.login-btn {
  width: 100%;
  height: 44px;
  border-radius: var(--app-radius-base, 8px);
  font-size: 1rem;
  font-weight: 600;
  background: var(--buyer-primary);
  border-color: var(--buyer-primary);
  letter-spacing: 2px;
  margin-top: 4px;
  transition: all 0.15s var(--app-ease-standard, cubic-bezier(0.4,0,0.2,1));
}

.login-btn:hover {
  background: var(--buyer-primary-dark);
  border-color: var(--buyer-primary-dark);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(249,115,22,0.35);
}

.login-btn:active {
  transform: translateY(0);
}

/* ===== 分割线 ===== */
.divider {
  display: flex;
  align-items: center;
  margin: 28px 0 20px;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #e7e5e4;
}

.divider-text {
  padding: 0 16px;
  font-size: 0.8125rem;
  color: #a8a29e;
}

/* ===== OAuth 按钮 ===== */
.oauth-actions {
  display: flex;
  justify-content: center;
}

.wechat-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 44px;
  padding: 0 28px;
  border-radius: var(--app-radius-base, 8px);
  border: 1px solid #e7e5e4;
  background: #fff;
  font-size: 0.9375rem;
  color: #44403c;
  transition: all 0.2s var(--app-ease-standard, cubic-bezier(0.4,0,0.2,1));
}

.wechat-btn:hover {
  border-color: #07C160;
  background: #f0fdf4;
  box-shadow: 0 2px 8px rgba(7,193,96,0.12);
}

.wechat-icon {
  flex-shrink: 0;
}

/* ===== 底部链接 ===== */
.form-footer {
  text-align: center;
  margin-top: 28px;
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
  .login-page {
    flex-direction: column;
  }

  .login-brand {
    flex: none;
    padding: 48px 24px;
    min-height: 200px;
  }

  .brand-name {
    font-size: 1.75rem;
  }

  .brand-slogan {
    font-size: 0.9375rem;
    letter-spacing: 2px;
  }

  .login-form-area {
    flex: 1;
    padding: 32px 20px;
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
