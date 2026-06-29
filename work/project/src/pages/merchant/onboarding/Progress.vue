<template>
  <div class="onboarding-container">
    <div class="onboarding-card">
      <div class="onboarding-header">
        <h2 class="onboarding-title">入驻进度</h2>
        <p class="onboarding-subtitle">跟踪您的商家入驻审核进度</p>
      </div>

      <!-- 步骤条 -->
      <el-steps :active="currentStep" align-center class="progress-steps" :process-status="stepStatus">
        <el-step title="注册账号" description="创建商家账号" />
        <el-step title="资质上传" description="提交营业资质" />
        <el-step title="店铺信息" description="完善店铺资料" />
        <el-step title="平台审核" description="等待平台审核" />
        <el-step title="入驻完成" description="开始营业" />
      </el-steps>

      <!-- 状态卡片 -->
      <div class="status-card">
        <div class="status-row">
          <span class="status-label">店铺状态</span>
          <el-tag :type="statusTagType" size="large" effect="plain">
            {{ statusText }}
          </el-tag>
        </div>

        <div v-if="shopInfo" class="shop-preview">
          <div class="shop-preview-header">
            <el-avatar
              :src="shopInfo.logo"
              :size="56"
              shape="square"
              class="shop-logo"
            >
              <span class="logo-placeholder">{{ (shopInfo.name || '店')[0] }}</span>
            </el-avatar>
            <div class="shop-info-text">
              <h3 class="shop-name">{{ shopInfo.name || '未设置' }}</h3>
              <p class="shop-desc">{{ shopInfo.description || '暂无简介' }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 操作区 -->
      <div class="action-area">
        <template v-if="shopInfo?.status === 'pending'">
          <div class="pending-notice">
            <el-icon class="notice-icon"><Clock /></el-icon>
            <span>您的入驻申请正在审核中，通常需要 1-3 个工作日，请耐心等待</span>
          </div>
        </template>

        <template v-if="shopInfo?.status === 'active'">
          <div class="success-notice">
            <el-icon class="notice-icon"><CircleCheckFilled /></el-icon>
            <span>恭喜！您的店铺已通过审核，可以开始上架商品了</span>
          </div>
          <el-button type="primary" @click="goToDashboard" class="action-btn">
            进入商家后台
          </el-button>
        </template>

        <template v-if="shopInfo?.status === 'frozen'">
          <div class="frozen-notice">
            <el-icon class="notice-icon"><WarningFilled /></el-icon>
            <span>您的店铺已被冻结，如有疑问请联系平台客服</span>
          </div>
        </template>

        <div class="action-links">
          <el-button
            v-if="shopInfo?.status === 'pending'"
            type="primary"
            plain
            @click="goToShopEdit"
          >
            完善店铺信息
          </el-button>
          <el-button @click="refreshStatus" :loading="refreshing">
            刷新状态
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 商家入驻 - 第四步：进度查看
 * 轮询获取店铺审核状态，展示入驻进度
 */
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Clock, CircleCheckFilled, WarningFilled } from '@element-plus/icons-vue'
import { getShopInfo } from '@/api/merchant'

const router = useRouter()

const shopInfo = ref(null)
const refreshing = ref(false)
let pollTimer = null

const statusMap = {
  pending: { text: '审核中', type: 'warning', step: 4 },
  active: { text: '已通过', type: 'success', step: 5 },
  frozen: { text: '已冻结', type: 'danger', step: 4 },
  cleared: { text: '已注销', type: 'info', step: 3 }
}

const currentStep = computed(() => {
  if (!shopInfo.value) return 3
  const st = statusMap[shopInfo.value.status]
  return st ? st.step : 3
})

const stepStatus = computed(() => {
  if (!shopInfo.value) return 'process'
  if (shopInfo.value.status === 'active') return 'success'
  if (shopInfo.value.status === 'frozen') return 'error'
  return 'process'
})

const statusText = computed(() => {
  if (!shopInfo.value) return '加载中...'
  const st = statusMap[shopInfo.value.status]
  return st ? st.text : shopInfo.value.status
})

const statusTagType = computed(() => {
  if (!shopInfo.value) return 'info'
  const st = statusMap[shopInfo.value.status]
  return st ? st.type : 'info'
})

async function fetchStatus() {
  try {
    const data = await getShopInfo()
    if (data) {
      shopInfo.value = data
    }
  } catch (err) {
    // 静默失败，不影响轮询
  }
}

async function refreshStatus() {
  refreshing.value = true
  try {
    await fetchStatus()
    ElMessage.success('状态已刷新')
  } catch (err) {
    ElMessage.error('刷新失败')
  } finally {
    refreshing.value = false
  }
}

function goToShopEdit() {
  router.push({ name: 'MerchantShopEdit' })
}

function goToDashboard() {
  router.push({ name: 'MerchantDashboard' })
}

onMounted(() => {
  fetchStatus()
  // 审核中状态每 30 秒轮询一次
  pollTimer = setInterval(() => {
    if (shopInfo.value?.status === 'pending') {
      fetchStatus()
    }
  }, 30000)
})

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
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
  max-width: 560px;
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

.progress-steps {
  margin-bottom: 32px;
}

.progress-steps :deep(.el-step__title) {
  font-size: var(--app-font-xs, 0.75rem);
}

.progress-steps :deep(.el-step__description) {
  font-size: var(--app-font-xs, 0.75rem);
}

.status-card {
  background: var(--app-bg-hover, #f9fafb);
  border-radius: var(--app-radius-base, 8px);
  padding: var(--app-space-lg, 20px);
  margin-bottom: 24px;
}

.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.status-label {
  font-size: var(--app-font-base, 0.875rem);
  font-weight: 500;
  color: var(--app-text-regular, #374151);
}

.shop-preview {
  border-top: 1px solid var(--app-border-light, #e5e7eb);
  padding-top: 16px;
}

.shop-preview-header {
  display: flex;
  align-items: center;
  gap: var(--app-space-md, 12px);
}

.shop-logo {
  flex-shrink: 0;
  border-radius: var(--app-radius-sm, 4px);
}

.logo-placeholder {
  font-size: var(--app-font-xl, 1.125rem);
  font-weight: 600;
  color: #1e3a5f;
}

.shop-info-text {
  flex: 1;
  min-width: 0;
}

.shop-name {
  font-size: var(--app-font-lg, 1rem);
  font-weight: 600;
  color: var(--app-text-primary, #1a1a2e);
  margin: 0 0 4px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.shop-desc {
  font-size: var(--app-font-sm, 0.8125rem);
  color: var(--app-text-secondary, #6b7280);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.action-area {
  text-align: center;
}

.pending-notice,
.success-notice,
.frozen-notice {
  display: flex;
  align-items: flex-start;
  gap: var(--app-space-sm, 8px);
  padding: var(--app-space-md, 12px) var(--app-space-base, 16px);
  border-radius: var(--app-radius-base, 8px);
  font-size: var(--app-font-sm, 0.8125rem);
  margin-bottom: 20px;
  text-align: left;
}

.pending-notice {
  background: #fef3c7;
  color: #92400e;
}

.success-notice {
  background: #d1fae5;
  color: #065f46;
}

.frozen-notice {
  background: #fee2e2;
  color: #991b1b;
}

.notice-icon {
  flex-shrink: 0;
  margin-top: 2px;
  font-size: var(--app-font-lg, 1rem);
}

.action-btn {
  width: 100%;
  height: 44px;
  font-size: var(--app-font-base, 0.875rem);
  font-weight: 600;
  background: #1e3a5f;
  border-color: #1e3a5f;
  border-radius: var(--app-radius-base, 8px);
  margin-bottom: 12px;
  transition: all 0.15s var(--app-ease-standard, cubic-bezier(0.4,0,0.2,1));
}

.action-btn:hover {
  background: #2c5282;
  border-color: #2c5282;
}

.action-links {
  display: flex;
  gap: var(--app-space-sm, 8px);
  justify-content: center;
}

@media (max-width: 576px) {
  .onboarding-card {
    padding: 28px 20px;
  }
  .action-links {
    flex-direction: column;
  }
}
</style>
