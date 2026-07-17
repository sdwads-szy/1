<template>
  <div class="admin-login-page">
    <div class="login-card">
      <!-- 品牌标识 -->
      <div class="login-brand">
        <div class="login-logo">鹊桥</div>
        <h1 class="login-title">欢迎回来</h1>
        <p class="login-subtitle">请输入您的后台账户信息</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="mobile">
          <el-input
            v-model="form.mobile"
            placeholder="请输入手机号"
            :prefix-icon="Cellphone"
            maxlength="11"
            size="large"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            show-password
            size="large"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            native-type="submit"
            :loading="loading"
            class="login-btn"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>

      <p class="login-footer">
        没有后台账户？请联系平台管理员开通
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Cellphone, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  mobile: '',
  password: ''
})

const rules = {
  mobile: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ]
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await userStore.login({ mobile: form.mobile, password: form.password })
    ElMessage.success('登录成功')

    // 根据角色跳转对应后台首页
    if (userStore.role === 'merchant') {
      router.push({ name: 'MerchantDashboard' })
    } else if (userStore.role === 'admin') {
      router.push({ name: 'AdminDashboard' })
    } else {
      // 消费者账号 — 无后台权限
      ElMessage.error('该账号无后台管理权限，请使用商家或管理员账号登录')
      userStore.logout()
    }
  } catch (err) {
    const responseData = err?.response?.data
    const msg = responseData?.message || err?.message || '登录失败，请检查网络连接后重试'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* ══ 页面背景 — Layer 1 柔和光斑 ══ */
.admin-login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: hsl(25, 5%, 97%);
  background-image: radial-gradient(ellipse at 30% 20%, hsl(215, 60%, 92%) 0%, transparent 60%);
  padding: 24px;
  box-sizing: border-box;
}

/* ══ 认证卡片 — 居中单列 ══ */
.login-card {
  background: hsl(215, 3%, 99%);
  border-radius: 30px;
  box-shadow: 0 4px 6px -1px rgba(30,28,27,0.08), 0 2px 4px -1px rgba(30,28,27,0.05);
  padding: 32px;
  max-width: 420px;
  width: 100%;
}

/* ══ 品牌区 ══ */
.login-brand {
  text-align: center;
  margin-bottom: 24px;
}

.login-logo {
  display: inline-block;
  font-size: 28px;
  font-weight: 700;
  color: hsl(25, 70%, 48%);
  letter-spacing: 2px;
  margin-bottom: 8px;
}

.login-title {
  font-size: 21px;
  font-weight: 700;
  color: hsl(25, 9%, 12%);
  margin: 0 0 4px;
  line-height: 1.25;
}

.login-subtitle {
  font-size: 12.25px;
  color: hsl(25, 4%, 62%);
  margin: 0;
  line-height: 1.5;
}

/* ══ 按钮 — 账户页沉稳强调色 ══ */
.login-btn {
  width: 100%;
  min-height: 44px;
  background: hsl(25, 70%, 48%);
  border-color: hsl(25, 70%, 48%);
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  transition: background-color 150ms cubic-bezier(0.16, 1, 0.3, 1),
              box-shadow 150ms cubic-bezier(0.16, 1, 0.3, 1),
              transform 150ms cubic-bezier(0.16, 1, 0.3, 1);
}

.login-btn:hover {
  background: hsl(25, 70%, 40%);
  border-color: hsl(25, 70%, 40%);
  box-shadow: 0 4px 6px -1px rgba(30,28,27,0.08), 0 2px 4px -1px rgba(30,28,27,0.05);
  transform: translateY(-1px);
}

.login-btn:active {
  background: hsl(25, 70%, 36%);
  border-color: hsl(25, 70%, 36%);
  box-shadow: 0 1px 2px rgba(30,28,27,0.05), 0 1px 3px rgba(30,28,27,0.08);
  transform: translateY(0) scale(0.98);
}

/* ══ 底部提示 ══ */
.login-footer {
  text-align: center;
  font-size: 12.25px;
  color: hsl(25, 4%, 62%);
  margin: 16px 0 0;
  line-height: 1.5;
}

/* ══ 移动端沉浸式 ══ */
@media (max-width: 480px) {
  .admin-login-page {
    background-image: none;
    padding: 0;
  }

  .login-card {
    border-radius: 0;
    box-shadow: none;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    max-width: 100%;
    padding: 24px;
  }
}
</style>
