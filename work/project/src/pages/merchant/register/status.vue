<template>
  <div class="status-page">
    <div class="status-card">
      <!-- 加载中 -->
      <div v-if="loading" class="status-body">
        <el-skeleton :rows="5" animated />
      </div>

      <!-- 审核中 -->
      <template v-else-if="statusInfo.status === 'pending_review'">
        <div class="status-body">
          <div class="status-icon status-icon--pending">
            <el-icon :size="64"><Clock /></el-icon>
          </div>
          <h2 class="status-title">您的入驻申请正在审核中</h2>
          <p class="status-desc">通常 1-3 个工作日完成审核，审核结果将通过短信通知您。</p>

          <!-- 审核进度时间线 -->
          <div class="timeline">
            <div class="timeline-item is-done">
              <div class="timeline-dot">
                <el-icon><Check /></el-icon>
              </div>
              <div class="timeline-content">
                <span class="timeline-label">已提交</span>
              </div>
            </div>
            <div class="timeline-item is-active">
              <div class="timeline-dot">
                <span class="timeline-dot-inner"></span>
              </div>
              <div class="timeline-content">
                <span class="timeline-label">审核中</span>
              </div>
            </div>
            <div class="timeline-item">
              <div class="timeline-dot"></div>
              <div class="timeline-content">
                <span class="timeline-label">审核完成</span>
              </div>
            </div>
            <div class="timeline-item">
              <div class="timeline-dot"></div>
              <div class="timeline-content">
                <span class="timeline-label">开店经营</span>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- 审核通过 -->
      <template v-else-if="statusInfo.status === 'approved'">
        <div class="status-body">
          <div class="status-icon status-icon--approved">
            <el-icon :size="64"><CircleCheckFilled /></el-icon>
          </div>
          <h2 class="status-title">恭喜，您的店铺已通过审核！</h2>
          <p class="status-desc">审核已通过，您的店铺已成功开通。</p>
          <el-button type="primary" size="large" @click="goToDashboard" class="status-action-btn">
            进入商家后台
          </el-button>
        </div>
      </template>

      <!-- 审核拒绝 / 已禁用 -->
      <template v-else-if="statusInfo.status === 'disabled'">
        <div class="status-body">
          <div class="status-icon status-icon--rejected">
            <el-icon :size="64"><CircleCloseFilled /></el-icon>
          </div>
          <h2 class="status-title">审核未通过</h2>
          <p class="status-desc">
            <template v-if="statusInfo.reviewReason">
              原因：{{ statusInfo.reviewReason }}
            </template>
            <template v-else>
              您的入驻申请未通过审核，请修改后重新提交。
            </template>
          </p>
          <el-button type="primary" size="large" @click="goToRegister" class="status-action-btn">
            修改并重新提交
          </el-button>
        </div>
      </template>

      <!-- 无申请记录 -->
      <template v-else>
        <div class="status-body">
          <div class="status-icon status-icon--empty">
            <el-icon :size="64"><Shop /></el-icon>
          </div>
          <h2 class="status-title">欢迎入驻鹊桥商城</h2>
          <p class="status-desc">三步开启您的线上店铺：填写企业信息 → 提交审核 → 开店经营。</p>
          <el-button type="primary" size="large" @click="goToRegister" class="status-action-btn">
            开始入驻
          </el-button>
        </div>
      </template>

      <!-- 审核时间信息 -->
      <div v-if="statusInfo.reviewedAt && statusInfo.status !== 'pending_review'" class="status-meta">
        <span class="meta-label">审核时间：</span>
        <span class="meta-value">{{ formatTime(statusInfo.reviewedAt) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Clock, CircleCheckFilled, CircleCloseFilled, Check, Shop } from '@element-plus/icons-vue';
import { getRegisterStatus } from '@/api/merchant-register';

const router = useRouter();

// ═══════════════════════════════════════════════
// 状态
// ═══════════════════════════════════════════════
const loading = ref(true);
const statusInfo = reactive({
  status: '',
  reviewReason: '',
  reviewedAt: null
});

// ═══════════════════════════════════════════════
// 轮询
// ═══════════════════════════════════════════════
let pollTimer = null;
const POLL_INTERVAL = 10000; // 10秒轮询一次

async function fetchStatus() {
  try {
    const res = await getRegisterStatus();
    if (res.data) {
      statusInfo.status = res.data.status || '';
      statusInfo.reviewReason = res.data.reviewReason || '';
      statusInfo.reviewedAt = res.data.reviewedAt || null;

      // 终态则停止轮询
      if (statusInfo.status === 'approved' || statusInfo.status === 'disabled') {
        stopPolling();
      }
    }
  } catch (err) {
    const code = err?.response?.data?.code;
    if (code === 'NO_APPLICATION') {
      // 无申请记录，保持空状态
      statusInfo.status = '';
      stopPolling();
    } else {
      // 网络错误不覆盖已有数据
      if (!statusInfo.status) {
        ElMessage.error('获取审核状态失败，请刷新页面重试');
      }
    }
  } finally {
    loading.value = false;
  }
}

function startPolling() {
  stopPolling();
  pollTimer = setInterval(fetchStatus, POLL_INTERVAL);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

// ═══════════════════════════════════════════════
// 导航
// ═══════════════════════════════════════════════
function goToDashboard() {
  router.push({ name: 'MerchantDashboard' });
}

function goToRegister() {
  router.push({ name: 'MerchantRegister' });
}

// ═══════════════════════════════════════════════
// 工具
// ═══════════════════════════════════════════════
function formatTime(isoStr) {
  if (!isoStr) return '—';
  try {
    const d = new Date(isoStr);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day} ${hours}:${minutes}`;
  } catch {
    return isoStr;
  }
}

// ═══════════════════════════════════════════════
// 生命周期
// ═══════════════════════════════════════════════
onMounted(async () => {
  await fetchStatus();
  // 非终态开始轮询
  if (statusInfo.status === 'pending_review') {
    startPolling();
  }
});

onBeforeUnmount(() => {
  stopPolling();
});
</script>

<style scoped>
/* ═══════════════════════════════════════════
   页面布局
   ═══════════════════════════════════════════ */
.status-page {
  max-width: 640px;
  margin: 0 auto;
  padding: var(--space-3xl) var(--space-lg);
  min-height: calc(100vh - 56px);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  background: var(--color-bg-page);
}

.status-card {
  width: 100%;
  background: var(--color-bg-base);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  padding: var(--space-2xl);
  border: 1px solid var(--color-border);
  margin-top: var(--space-2xl);
}

.status-body {
  text-align: center;
  padding: var(--space-lg) 0;
}

/* ═══════════════════════════════════════════
   状态图标
   ═══════════════════════════════════════════ */
.status-icon {
  margin-bottom: var(--space-lg);
  display: inline-flex;
}

.status-icon--pending {
  color: var(--color-warning);
}

.status-icon--approved {
  color: var(--color-success);
}

.status-icon--rejected {
  color: var(--color-error);
}

.status-icon--empty {
  color: var(--color-primary-400);
}

/* ═══════════════════════════════════════════
   标题和描述
   ═══════════════════════════════════════════ */
.status-title {
  font-size: var(--font-size-xl);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-sm);
}

.status-desc {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  line-height: var(--line-height-relaxed);
  margin: 0 0 var(--space-lg);
  max-width: 420px;
  margin-left: auto;
  margin-right: auto;
}

.status-action-btn {
  margin-top: var(--space-md);
  min-width: 180px;
}

/* ═══════════════════════════════════════════
   审核进度时间线
   ═══════════════════════════════════════════ */
.timeline {
  margin-top: var(--space-xl);
  padding: 0 var(--space-lg);
}

.timeline-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-md);
  padding-bottom: var(--space-lg);
  position: relative;
}

.timeline-item:not(:last-child)::after {
  content: '';
  position: absolute;
  left: 15px;
  top: 32px;
  bottom: 0;
  width: 2px;
  background: var(--color-border);
}

.timeline-item.is-done:not(:last-child)::after {
  background: var(--color-success);
}

.timeline-dot {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 2px solid var(--color-border);
  background: var(--color-bg-base);
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

.timeline-item.is-done .timeline-dot {
  background: var(--color-success);
  border-color: var(--color-success);
  color: #FFFFFF;
}

.timeline-item.is-active .timeline-dot {
  border-color: var(--color-warning);
  background: var(--color-bg-base);
}

.timeline-dot-inner {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--color-warning);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.3); }
}

.timeline-content {
  padding-top: 4px;
}

.timeline-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.timeline-item.is-done .timeline-label,
.timeline-item.is-active .timeline-label {
  color: var(--color-text-primary);
  font-weight: 500;
}

/* ═══════════════════════════════════════════
   审核元信息
   ═══════════════════════════════════════════ */
.status-meta {
  text-align: center;
  padding-top: var(--space-lg);
  border-top: 1px solid var(--color-border);
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.meta-label {
  color: var(--color-text-tertiary);
}

.meta-value {
  color: var(--color-text-secondary);
}

/* ═══════════════════════════════════════════
   响应式
   ═══════════════════════════════════════════ */
@media (max-width: 768px) {
  .status-page {
    padding: var(--space-lg) var(--space-md);
  }

  .status-card {
    padding: var(--space-lg);
    margin-top: var(--space-lg);
  }

  .timeline {
    padding: 0;
  }
}
</style>
