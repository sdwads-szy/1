<template>
  <div class="page-container">
    <!-- 面包屑 -->
    <el-breadcrumb separator="/" class="breadcrumb">
      <el-breadcrumb-item :to="{ name: 'AdminRefundList' }">退款管理</el-breadcrumb-item>
      <el-breadcrumb-item>退款详情</el-breadcrumb-item>
    </el-breadcrumb>

    <div class="page-header">
      <h1 class="page-title">退款详情</h1>
      <el-tag v-if="refund" :type="statusTagType(refund.status)" size="large" class="status-tag">
        {{ statusLabel(refund.status) }}
      </el-tag>
    </div>

    <div class="page-content" v-loading="loading">
      <template v-if="refund">
        <!-- 状态步骤条 -->
        <div class="info-card">
          <h3 class="card-title">退款进度</h3>
          <template v-if="refund.status !== 'rejected'">
            <el-steps :active="currentStep" align-center>
              <el-step title="已申请" :description="formatTime(refund.apply_at)" />
              <el-step title="已审核" :description="formatTime(refund.processed_at)" />
              <el-step title="处理中" />
              <el-step title="已完成" :description="formatTime(refund.completed_at)" />
            </el-steps>
          </template>
          <div v-else class="rejected-notice">
            <el-icon :size="22" color="#ef4444"><CircleCloseFilled /></el-icon>
            <span class="rejected-text">该退款申请已被拒绝，流程已终止</span>
          </div>
        </div>

        <!-- 基本信息 -->
        <div class="info-card">
          <h3 class="card-title">基本信息</h3>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="退款ID">{{ refund.id }}</el-descriptions-item>
            <el-descriptions-item label="订单ID">{{ refund.order_id }}</el-descriptions-item>
            <el-descriptions-item label="支付流水ID">{{ refund.payment_id }}</el-descriptions-item>
            <el-descriptions-item label="用户ID">{{ refund.user_id }}</el-descriptions-item>
            <el-descriptions-item label="商家ID">{{ refund.merchant_id }}</el-descriptions-item>
            <el-descriptions-item label="退款金额">
              <span class="amount-highlight">¥{{ formatAmount(refund.amount) }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="退款原因" :span="2">
              {{ refund.reason }}
            </el-descriptions-item>
            <el-descriptions-item label="申请时间">{{ formatTime(refund.apply_at) }}</el-descriptions-item>
            <el-descriptions-item label="处理时间">{{ formatTime(refund.processed_at) }}</el-descriptions-item>
            <el-descriptions-item label="完成时间">{{ formatTime(refund.completed_at) }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 凭证图片 -->
        <div class="info-card" v-if="evidenceImages.length">
          <h3 class="card-title">
            凭证图片
            <span class="card-subtitle">（{{ evidenceImages.length }} 张）</span>
          </h3>
          <div class="evidence-grid">
            <el-image
              v-for="(img, idx) in evidenceImages"
              :key="idx"
              :src="img"
              :preview-src-list="evidenceImages"
              :preview-teleported="true"
              :initial-index="idx"
              fit="cover"
              class="evidence-image"
            >
              <template #error>
                <div class="image-error">
                  <el-icon><PictureFilled /></el-icon>
                  <span>加载失败</span>
                </div>
              </template>
            </el-image>
          </div>
        </div>

        <!-- 操作区 -->
        <div class="action-bar">
          <el-button @click="handleBack">
            <el-icon><ArrowLeft /></el-icon>
            返回列表
          </el-button>
          <el-button
            v-if="refund.status === 'approved'"
            type="primary"
            :loading="executing"
            @click="handleExecute"
          >
            执行退款
          </el-button>
        </div>
      </template>

      <!-- 空态 -->
      <div v-else-if="!loading" class="empty-state">
        <el-empty description="退款单不存在或已被删除">
          <el-button type="primary" @click="handleBack">返回列表</el-button>
        </el-empty>
      </div>
    </div>

    <!-- 执行确认弹窗 -->
    <el-dialog
      v-model="executeDialogVisible"
      title="确认执行退款"
      width="440px"
      :close-on-click-modal="false"
    >
      <div class="dialog-body">
        <p>确定要对退款单 <strong>#{{ refund?.id }}</strong> 执行退款操作吗？</p>
        <p>退款金额：<strong class="amount-emphasis">¥{{ formatAmount(refund?.amount) }}</strong></p>
        <p class="warning-text">
          <el-icon><WarningFilled /></el-icon>
          执行后将触发实际退款流程，请谨慎操作。
        </p>
      </div>
      <template #footer>
        <el-button @click="executeDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="executing" @click="confirmExecute">
          确认执行
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 平台后台 - 退款详情页
 * 展示退款单完整信息、状态流转、凭证图片，支持执行退款操作
 */
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, CircleCloseFilled, PictureFilled, WarningFilled } from '@element-plus/icons-vue'
import { getRefundList, executeRefund } from '@/api/admin/refund'

const route = useRoute()
const router = useRouter()

// --- state ---
const loading = ref(false)
const refund = ref(null)
const executing = ref(false)
const executeDialogVisible = ref(false)

// --- constants ---
const statusMap = {
  applied: { label: '已申请', type: 'warning', step: 0 },
  approved: { label: '已审核', type: 'info', step: 1 },
  rejected: { label: '已拒绝', type: 'danger', step: -1 },
  processing: { label: '处理中', type: '', step: 2 },
  completed: { label: '已完成', type: 'success', step: 3 }
}

// --- computed ---
const currentStep = computed(() => {
  if (!refund.value) return 0
  return statusMap[refund.value.status]?.step ?? 0
})

const evidenceImages = computed(() => {
  if (!refund.value?.evidence_images) return []
  const images = refund.value.evidence_images
  if (Array.isArray(images)) return images
  if (typeof images === 'string') {
    try { return JSON.parse(images) } catch { return [] }
  }
  return []
})

// --- methods ---
function statusLabel(status) {
  return statusMap[status]?.label ?? status
}

function statusTagType(status) {
  return statusMap[status]?.type ?? 'info'
}

function formatAmount(val) {
  if (val == null) return '0.00'
  return parseFloat(val).toFixed(2)
}

function formatTime(val) {
  if (!val) return '-'
  return new Date(val).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

async function fetchDetail() {
  const id = parseInt(route.params.id)
  if (!id || isNaN(id)) {
    ElMessage.error('无效的退款ID')
    return
  }
  loading.value = true
  try {
    const res = await getRefundList({ id, page: 1, pageSize: 1 })
    const data = res.data ?? res
    const items = data.list ?? []
    refund.value = items.length ? items[0] : null
  } catch {
    ElMessage.error('获取退款详情失败')
  } finally {
    loading.value = false
  }
}

function handleBack() {
  router.push({ name: 'AdminRefundList' })
}

function handleExecute() {
  executeDialogVisible.value = true
}

async function confirmExecute() {
  if (!refund.value) return
  executing.value = true
  try {
    await executeRefund(refund.value.id)
    ElMessage.success('退款执行成功')
    executeDialogVisible.value = false
    fetchDetail()
  } catch {
    ElMessage.error('退款执行失败')
  } finally {
    executing.value = false
  }
}

// --- lifecycle ---
onMounted(() => {
  fetchDetail()
})
</script>

<style scoped>
.page-container {
  padding: var(--app-space-xl);
  min-height: 100%;
  background: var(--app-bg-page);
}

.breadcrumb {
  margin-bottom: var(--app-space-base);
}

.page-header {
  display: flex;
  align-items: center;
  gap: var(--app-space-base);
  margin-bottom: var(--app-space-xl);
}

.page-title {
  font-size: var(--app-font-2xl);
  font-weight: 600;
  color: #152233;
  margin: 0;
}

.status-tag {
  font-size: var(--app-font-base);
}

.page-content {
  display: flex;
  flex-direction: column;
  gap: var(--app-space-lg);
}

.info-card {
  background: var(--app-bg-container);
  border-radius: var(--app-radius-md);
  padding: var(--app-space-xl);
  box-shadow: var(--app-shadow-level-1);
}

.card-title {
  font-size: var(--app-font-lg);
  font-weight: 600;
  color: #152233;
  margin: 0 0 var(--app-space-base) 0;
  padding-bottom: var(--app-space-sm);
  border-bottom: 1px solid var(--app-border-light);
}

.card-subtitle {
  font-weight: 400;
  font-size: var(--app-font-sm);
  color: var(--app-text-secondary);
  margin-left: var(--app-space-xs);
}

.amount-highlight {
  font-size: var(--app-font-lg);
  font-weight: 600;
  color: #152233;
}

.rejected-notice {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--app-space-sm);
  padding: var(--app-space-xl);
  background: #fef2f2;
  border-radius: var(--app-radius-base);
  border: 1px solid #fecaca;
}

.rejected-text {
  font-size: var(--app-font-base);
  font-weight: 500;
  color: #991b1b;
}

.evidence-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: var(--app-space-md);
}

.evidence-image {
  width: 100%;
  aspect-ratio: 1;
  border-radius: var(--app-radius-base);
  overflow: hidden;
  cursor: pointer;
  border: 1px solid var(--app-border-light);
  background: var(--app-bg-disabled);
}

.image-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 100%;
  height: 100%;
  color: var(--app-text-secondary);
  font-size: var(--app-font-xs);
}

.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--app-space-md);
  padding: var(--app-space-base) 0;
}

.dialog-body p {
  margin-bottom: var(--app-space-sm);
  line-height: 1.6;
}

.amount-emphasis {
  color: #152233;
}

.warning-text {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--app-color-danger);
  font-size: var(--app-font-sm);
  margin-top: var(--app-space-sm) !important;
}

.empty-state {
  display: flex;
  justify-content: center;
  padding: var(--app-space-4xl) 0;
  background: var(--app-bg-container);
  border-radius: var(--app-radius-md);
}
</style>
