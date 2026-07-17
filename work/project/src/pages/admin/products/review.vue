<template>
  <div class="review-workspace">
    <!-- 页面标题栏 -->
    <div class="review-header">
      <div class="review-header-left">
        <el-breadcrumb separator="/">
          <el-breadcrumb-item :to="{ name: 'AdminDashboard' }">平台后台</el-breadcrumb-item>
          <el-breadcrumb-item>商品审核</el-breadcrumb-item>
        </el-breadcrumb>
        <h1 class="review-title">商品审核工作台</h1>
      </div>
    </div>

    <!-- 统计卡片行 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-card-label">待审核</div>
        <div class="stat-card-value stat-card-value--pending">{{ stats.pending }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-label">今日通过</div>
        <div class="stat-card-value stat-card-value--approved">{{ stats.todayApproved }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-label">今日驳回</div>
        <div class="stat-card-value stat-card-value--rejected">{{ stats.todayRejected }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-label">平均审核时长</div>
        <div class="stat-card-value stat-card-value--avg">{{ stats.avgDuration }}</div>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="filters.keyword"
          placeholder="搜索商品名称..."
          clearable
          :prefix-icon="Search"
          class="toolbar-search"
          @clear="handleSearch"
          @keyup.enter="handleSearch"
        />
        <el-select
          v-model="filters.status"
          placeholder="审核状态"
          clearable
          class="toolbar-select"
          @change="handleSearch"
        >
          <el-option label="待审核" value="draft" />
          <el-option label="已通过" value="listed" />
          <el-option label="已驳回" value="rejected" />
        </el-select>
        <el-date-picker
          v-model="filters.dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          class="toolbar-date"
          @change="handleSearch"
        />
      </div>
      <div class="toolbar-right">
        <el-checkbox v-model="filters.sensitiveOnly" @change="handleSearch">
          仅看含敏感词
        </el-checkbox>
        <el-button :icon="Refresh" @click="handleSearch">刷新</el-button>
      </div>
    </div>

    <!-- 审核表格 -->
    <div class="review-table-wrapper">
      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="productList"
        row-key="id"
        class="review-table"
        stripe
        @selection-change="handleSelectionChange"
        @row-click="handleRowClick"
      >
        <el-table-column type="selection" width="48" align="center" />
        <el-table-column label="商品信息" min-width="280">
          <template #default="{ row }">
            <div class="product-cell">
              <el-image
                :src="assetUrl(row.default_image)"
                class="product-cell-image"
                fit="cover"
              >
                <template #error>
                  <div class="product-cell-image-error">
                    <el-icon><PictureFilled /></el-icon>
                  </div>
                </template>
              </el-image>
              <div class="product-cell-info">
                <div class="product-cell-name">
                  {{ row.name }}
                  <el-tag
                    v-if="row.sensitive_words && row.sensitive_words.length"
                    type="danger"
                    size="small"
                    class="sensitive-badge"
                  >
                    含敏感词
                  </el-tag>
                </div>
                <div class="product-cell-shop">{{ row.shop_name || '店铺#' + row.shop_id }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="类目" width="120">
          <template #default="{ row }">
            <span class="text-secondary">{{ row.category_name || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="审核状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag
              :type="statusTagType(row.status)"
              size="small"
              class="review-status-tag"
            >
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="提交时间" width="170">
          <template #default="{ row }">
            <span class="text-tertiary text-xs">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right" align="center">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'draft'"
              type="primary"
              size="small"
              link
              @click.stop="openDetail(row)"
            >
              审核
            </el-button>
            <span v-else class="text-tertiary text-xs">-</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <div v-if="!loading && productList.length === 0" class="table-empty">
        <el-icon class="table-empty-icon" :size="48" :color="'var(--color-success)'">
          <CircleCheckFilled />
        </el-icon>
        <p class="table-empty-title">全部审核完毕</p>
        <p class="table-empty-desc">当前没有待审核的商品，辛苦了！</p>
        <el-button type="primary" @click="handleSearch">刷新列表</el-button>
      </div>

      <!-- 分页 -->
      <div v-if="total > 0" class="table-pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @change="fetchList"
        />
      </div>
    </div>

    <!-- 详情抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      title="商品审核详情"
      direction="rtl"
      size="420px"
      :before-close="handleDrawerClose"
      class="review-drawer"
    >
      <template v-if="currentProduct">
        <div class="drawer-body">
          <!-- 商品图片 -->
          <div class="drawer-image">
            <el-image
              :src="assetUrl(currentProduct.default_image)"
              fit="contain"
              class="drawer-image-el"
            >
              <template #error>
                <div class="drawer-image-error">
                  <el-icon :size="48"><PictureFilled /></el-icon>
                </div>
              </template>
            </el-image>
          </div>

          <!-- 基本信息 -->
          <div class="drawer-section">
            <div class="drawer-section-title">基本信息</div>
            <div class="drawer-field">
              <span class="drawer-field-label">商品名称</span>
              <span class="drawer-field-value">{{ currentProduct.name }}</span>
            </div>
            <div class="drawer-field">
              <span class="drawer-field-label">所属店铺</span>
              <span class="drawer-field-value">{{ currentProduct.shop_name || '店铺#' + currentProduct.shop_id }}</span>
            </div>
            <div class="drawer-field">
              <span class="drawer-field-label">商品类目</span>
              <span class="drawer-field-value">{{ currentProduct.category_name || '-' }}</span>
            </div>
          </div>

          <!-- 商品描述 -->
          <div class="drawer-section">
            <div class="drawer-section-title">商品描述</div>
            <div class="drawer-description" v-html="highlightedDescription"></div>
          </div>

          <div v-if="currentProduct.sensitive_words && currentProduct.sensitive_words.length" class="drawer-section">
            <el-alert
              title="敏感词检测"
              type="warning"
              :closable="false"
              show-icon
            >
              <template #default>
                <div class="sensitive-words-list">
                  检测到以下敏感词：
                  <el-tag
                    v-for="word in currentProduct.sensitive_words"
                    :key="word"
                    type="danger"
                    size="small"
                    class="sensitive-word-tag"
                  >
                    {{ word }}
                  </el-tag>
                </div>
              </template>
            </el-alert>
          </div>

          <!-- 驳回原因输入 -->
          <div v-if="reviewAction === 'reject'" class="drawer-section">
            <div class="drawer-section-title">驳回原因</div>
            <el-input
              v-model="rejectReason"
              type="textarea"
              :rows="3"
              maxlength="500"
              show-word-limit
              placeholder="请填写驳回原因，以便商家修改（必填）"
            />
          </div>
        </div>

        <!-- 底部操作按钮 -->
        <template #footer>
          <div class="drawer-footer" v-if="currentProduct.status === 'draft'">
            <el-button
              v-if="reviewAction !== 'reject'"
              type="danger"
              :icon="CircleCloseFilled"
              @click="reviewAction = 'reject'"
            >
              驳回
            </el-button>
            <div v-else class="drawer-footer-reject">
              <el-button @click="reviewAction = null">取消</el-button>
              <el-button
                type="danger"
                :loading="submitting"
                :disabled="!rejectReason.trim()"
                @click="submitReview('reject')"
              >
                确认驳回
              </el-button>
            </div>
            <el-button
              v-if="reviewAction !== 'reject'"
              type="success"
              :icon="CircleCheckFilled"
              :loading="submitting"
              @click="submitReview('approve')"
            >
              通过
            </el-button>
          </div>
          <div v-else class="drawer-footer-done">
            <span class="text-tertiary">该商品已完成审核</span>
          </div>
        </template>
      </template>
    </el-drawer>

    <!-- 批量操作栏 -->
    <transition name="batch-bar">
      <div v-if="selectedIds.length > 0" class="batch-bar">
        <div class="batch-bar-info">
          已选 <strong>{{ selectedIds.length }}</strong> 项
        </div>
        <div class="batch-bar-actions">
          <el-button
            type="success"
            size="small"
            :loading="batchSubmitting"
            @click="handleBatchReview('approve')"
          >
            批量通过
          </el-button>
          <el-button
            type="danger"
            size="small"
            :loading="batchSubmitting"
            @click="handleBatchReview('reject')"
          >
            批量驳回
          </el-button>
        </div>
      </div>
    </transition>

    <!-- 批量驳回原因对话框 -->
    <el-dialog
      v-model="batchRejectDialogVisible"
      title="批量驳回"
      width="480px"
      :close-on-click-modal="false"
    >
      <el-form label-position="top">
        <el-form-item label="驳回原因（将应用于所有选中商品）">
          <el-input
            v-model="batchRejectReason"
            type="textarea"
            :rows="4"
            maxlength="500"
            show-word-limit
            placeholder="请填写驳回原因，以便商家修改"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchRejectDialogVisible = false">取消</el-button>
        <el-button
          type="danger"
          :loading="batchSubmitting"
          :disabled="!batchRejectReason.trim()"
          @click="confirmBatchReject"
        >
          确认驳回 {{ selectedIds.length }} 项
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search,
  Refresh,
  PictureFilled,
  CircleCheckFilled,
  CircleCloseFilled
} from '@element-plus/icons-vue'
import { getReviewProducts, reviewProduct } from '@/api/admin-products'

// ==================== 状态 ====================
const loading = ref(false)
const submitting = ref(false)
const batchSubmitting = ref(false)
const productList = ref([])
const total = ref(0)
const selectedIds = ref([])
const tableRef = ref(null)

const stats = ref({
  pending: 0,
  todayApproved: 0,
  todayRejected: 0,
  avgDuration: '-'
})

const filters = ref({
  keyword: '',
  status: '',
  dateRange: null,
  sensitiveOnly: false
})

const pagination = ref({
  page: 1,
  pageSize: 20
})

// 详情抽屉
const drawerVisible = ref(false)
const currentProduct = ref(null)
const reviewAction = ref(null)
const rejectReason = ref('')

// 批量驳回
const batchRejectDialogVisible = ref(false)
const batchRejectReason = ref('')

// ==================== 计算属性 ====================
const highlightedDescription = computed(() => {
  if (!currentProduct.value) return ''
  let html = currentProduct.value.description || ''
  if (currentProduct.value.sensitive_words && currentProduct.value.sensitive_words.length) {
    currentProduct.value.sensitive_words.forEach(word => {
      const escaped = word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      html = html.replace(
        new RegExp(`(${escaped})`, 'gi'),
        '<mark class="sensitive-highlight">$1</mark>'
      )
    })
  }
  return html || '<span class="text-tertiary">暂无描述</span>'
})

// ==================== 方法 ====================

/** 图片路径拼接 */
function assetUrl(path) {
  if (!path) return ''
  if (path.startsWith('http')) return path
  const base = import.meta.env.VITE_FILE_BASE_URL || ''
  return base + path
}

/** 审核状态标签类型 */
function statusTagType(status) {
  const map = {
    draft: 'warning',
    listed: 'success',
    delisted: 'info',
    rejected: 'danger'
  }
  return map[status] || 'info'
}

/** 审核状态文案 */
function statusLabel(status) {
  const map = {
    draft: '待审核',
    listed: '已通过',
    delisted: '已下架',
    rejected: '已驳回'
  }
  return map[status] || status
}

/** 格式化时间 */
function formatTime(ts) {
  if (!ts) return '-'
  const d = new Date(ts)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${day} ${h}:${min}`
}

/** 获取审核列表 */
async function fetchList() {
  loading.value = true
  try {
    const params = {
      page: pagination.value.page,
      pageSize: pagination.value.pageSize
    }
    if (filters.value.keyword) params.keyword = filters.value.keyword
    if (filters.value.status) params.status = filters.value.status
    if (filters.value.sensitiveOnly) params.sensitiveOnly = true
    if (filters.value.dateRange && filters.value.dateRange.length === 2) {
      params.startDate = filters.value.dateRange[0].toISOString().split('T')[0]
      params.endDate = filters.value.dateRange[1].toISOString().split('T')[0]
    }

    const res = await getReviewProducts(params)
    productList.value = res.data.list || []
    total.value = res.data.total || 0
    if (res.data.stats) {
      stats.value = {
        pending: res.data.stats.pending ?? 0,
        todayApproved: res.data.stats.todayApproved ?? 0,
        todayRejected: res.data.stats.todayRejected ?? 0,
        avgDuration: res.data.stats.avgDuration || '-'
      }
    }
  } catch (err) {
    const msg = err?.response?.data?.message || '审核列表加载失败，请检查网络后重试。'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

/** 搜索 */
function handleSearch() {
  pagination.value.page = 1
  selectedIds.value = []
  fetchList()
}

/** 表格选择变化 */
function handleSelectionChange(selection) {
  selectedIds.value = selection
    .filter(item => item.status === 'draft')
    .map(item => item.id)
}

/** 行点击 */
function handleRowClick(row) {
  openDetail(row)
}

/** 打开详情 */
function openDetail(row) {
  currentProduct.value = { ...row }
  reviewAction.value = null
  rejectReason.value = ''
  drawerVisible.value = true
}

/** 关闭抽屉 */
function handleDrawerClose() {
  reviewAction.value = null
  rejectReason.value = ''
  drawerVisible.value = false
}

/** 提交审核 */
async function submitReview(action) {
  if (action === 'reject' && !rejectReason.value.trim()) {
    ElMessage.warning('请填写驳回原因')
    return
  }

  submitting.value = true
  try {
    const data = { action }
    if (action === 'reject') {
      data.reason = rejectReason.value.trim()
    }

    const res = await reviewProduct(currentProduct.value.id, data)

    if (action === 'approve') {
      ElMessage.success('已通过该审核项。')
    } else {
      ElMessage.success('已驳回，商家将收到驳回原因以便修改。')
    }

    // 更新本地列表
    const idx = productList.value.findIndex(p => p.id === currentProduct.value.id)
    if (idx >= 0) {
      productList.value[idx].status = res.data.status
    }

    // 更新统计
    if (action === 'approve') {
      stats.value.pending = Math.max(0, stats.value.pending - 1)
      stats.value.todayApproved += 1
    } else {
      stats.value.pending = Math.max(0, stats.value.pending - 1)
      stats.value.todayRejected += 1
    }

    drawerVisible.value = false
    reviewAction.value = null
    rejectReason.value = ''
  } catch (err) {
    const msg = err?.response?.data?.message || '审核操作失败，请重试。'
    const code = err?.response?.data?.code

    if (code === 'SENSITIVE_WORD') {
      // 提取敏感词并更新当前商品
      const match = msg.match(/\[([^\]]+)\]/)
      if (match && currentProduct.value) {
        currentProduct.value.sensitive_words = match[1].split(',').map(w => w.trim())
        ElMessage.warning('商品包含敏感词，请驳回或通知商家修改')
      } else {
        ElMessage.error(msg)
      }
    } else {
      ElMessage.error(msg)
    }
  } finally {
    submitting.value = false
  }
}

/** 批量审核 */
function handleBatchReview(action) {
  if (selectedIds.value.length === 0) return

  if (action === 'approve') {
    ElMessageBox.confirm(
      `确认批量通过 ${selectedIds.value.length} 项审核？此操作不可撤回。`,
      '批量通过确认',
      { confirmButtonText: '确认通过', cancelButtonText: '取消', type: 'warning' }
    ).then(() => executeBatchReview('approve'))
  } else {
    batchRejectReason.value = ''
    batchRejectDialogVisible.value = true
  }
}

/** 确认批量驳回 */
function confirmBatchReject() {
  if (!batchRejectReason.value.trim()) return
  batchRejectDialogVisible.value = false
  executeBatchReview('reject', batchRejectReason.value.trim())
}

/** 执行批量审核 */
async function executeBatchReview(action, reason) {
  batchSubmitting.value = true
  let successCount = 0
  let failCount = 0

  try {
    for (const id of selectedIds.value) {
      try {
        const data = { action }
        if (reason) data.reason = reason
        await reviewProduct(id, data)
        successCount++

        // 更新本地列表
        const idx = productList.value.findIndex(p => p.id === id)
        if (idx >= 0) {
          productList.value[idx].status = action === 'approve' ? 'listed' : 'rejected'
        }
      } catch {
        failCount++
      }
    }

    if (successCount > 0) {
      ElMessage.success(
        `批量${action === 'approve' ? '通过' : '驳回'}完成：成功 ${successCount} 项` +
        (failCount > 0 ? `，失败 ${failCount} 项` : '')
      )
    } else {
      ElMessage.error('批量操作全部失败，请重试')
    }

    selectedIds.value = []
    tableRef.value?.clearSelection()
    fetchList()
  } finally {
    batchSubmitting.value = false
  }
}

// ==================== 生命周期 ====================
onMounted(() => {
  fetchList()
})
</script>

<style scoped>
/* ===== 工作区底色 ===== */
.review-workspace {
  background: hsl(25, 4%, 96%);
  min-height: 100vh;
  padding: var(--space-lg);
}

/* ===== 标题栏 ===== */
.review-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-lg);
}

.review-header-left :deep(.el-breadcrumb) {
  margin-bottom: var(--space-xs);
}

.review-title {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
}

/* ===== 统计卡片 ===== */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
}

.stat-card {
  background: var(--color-bg-base);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: var(--space-md) var(--space-lg);
}

.stat-card-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-xs);
}

.stat-card-value {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.stat-card-value--pending {
  color: hsl(38, 90%, 50%);
}

.stat-card-value--approved {
  color: hsl(145, 60%, 40%);
}

.stat-card-value--rejected {
  color: hsl(0, 75%, 48%);
}

.stat-card-value--avg {
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
}

/* ===== 工具栏 ===== */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--color-bg-base);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: var(--space-sm) var(--space-md);
  margin-bottom: var(--space-md);
  flex-wrap: wrap;
  gap: var(--space-sm);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex: 1;
  min-width: 0;
}

.toolbar-search {
  width: 260px;
}

.toolbar-select {
  width: 140px;
}

.toolbar-date {
  width: 280px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  flex-shrink: 0;
}

/* ===== 表格 ===== */
.review-table-wrapper {
  background: var(--color-bg-base);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
}

.review-table {
  --el-table-row-hover-bg-color: var(--color-bg-page);
}

.review-table :deep(.el-table__header th) {
  background: var(--color-bg-page);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: 600;
  padding: var(--space-sm) var(--space-md);
  height: 44px;
}

.review-table :deep(.el-table__body td) {
  padding: var(--space-sm) var(--space-md);
  height: 44px;
  font-size: var(--font-size-sm);
}

.review-table :deep(.el-table__row.current-row) {
  background: var(--color-primary-50);
}

.review-table :deep(.el-table__row.current-row td:first-child) {
  border-left: 3px solid var(--color-primary-500);
}

/* 商品信息单元格 */
.product-cell {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.product-cell-image {
  width: 48px;
  height: 48px;
  border-radius: 4px;
  flex-shrink: 0;
}

.product-cell-image-error {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-page);
  color: var(--color-text-tertiary);
  border-radius: 4px;
}

.product-cell-info {
  min-width: 0;
  flex: 1;
}

.product-cell-name {
  font-weight: 600;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 240px;
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}

.product-cell-shop {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-top: 2px;
}

.sensitive-badge {
  flex-shrink: 0;
}

/* 审核状态标签 */
.review-status-tag {
  border-radius: 4px;
}

/* 文本工具类 */
.text-secondary {
  color: var(--color-text-secondary);
}

.text-tertiary {
  color: var(--color-text-tertiary);
}

.text-xs {
  font-size: var(--font-size-xs);
}

/* ===== 空状态 ===== */
.table-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-3xl) 0;
}

.table-empty-icon {
  margin-bottom: var(--space-md);
}

.table-empty-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-xs);
}

.table-empty-desc {
  font-size: var(--font-size-base);
  color: var(--color-text-tertiary);
  margin: 0 0 var(--space-lg);
}

/* ===== 分页 ===== */
.table-pagination {
  display: flex;
  justify-content: flex-end;
  padding: var(--space-md);
  border-top: 1px solid var(--color-border);
}

/* ===== 详情抽屉 ===== */
.review-drawer :deep(.el-drawer__header) {
  padding: var(--space-lg);
  margin-bottom: 0;
  border-bottom: 1px solid var(--color-border);
}

.review-drawer :deep(.el-drawer__body) {
  padding: 0;
  display: flex;
  flex-direction: column;
}

.review-drawer :deep(.el-drawer__footer) {
  padding: var(--space-lg);
  border-top: 1px solid var(--color-border);
}

.drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-lg);
}

.drawer-image {
  width: 100%;
  aspect-ratio: 1 / 1;
  border-radius: 8px;
  overflow: hidden;
  background: var(--color-bg-page);
  margin-bottom: var(--space-lg);
}

.drawer-image-el {
  width: 100%;
  height: 100%;
}

.drawer-image-error {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-page);
  color: var(--color-text-tertiary);
}

.drawer-section {
  margin-bottom: var(--space-lg);
}

.drawer-section-title {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: var(--space-sm);
  padding-bottom: var(--space-xs);
  border-bottom: 1px solid var(--color-border);
}

.drawer-field {
  display: flex;
  margin-bottom: var(--space-sm);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-normal);
}

.drawer-field-label {
  color: var(--color-text-tertiary);
  width: 80px;
  flex-shrink: 0;
}

.drawer-field-value {
  color: var(--color-text-primary);
  flex: 1;
  word-break: break-all;
}

.drawer-description {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: var(--line-height-relaxed);
  background: var(--color-bg-page);
  border-radius: 6px;
  padding: var(--space-sm) var(--space-md);
  max-height: 200px;
  overflow-y: auto;
}

.drawer-description :deep(.sensitive-highlight) {
  background: hsl(0, 80%, 52%);
  color: #fff;
  padding: 1px 4px;
  border-radius: 2px;
}

.sensitive-words-list {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-xs);
  margin-top: var(--space-xs);
  font-size: var(--font-size-sm);
}

.sensitive-word-tag {
  border-radius: 4px;
}

/* ===== 抽屉底部 ===== */
.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-sm);
}

.drawer-footer-reject {
  display: flex;
  gap: var(--space-sm);
}

.drawer-footer-done {
  display: flex;
  justify-content: center;
}

/* ===== 批量操作栏 ===== */
.batch-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: var(--z-sticky);
  background: hsl(25, 7%, 15%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-sm) var(--space-xl);
  box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.15);
}

.batch-bar-info {
  font-size: var(--font-size-base);
}

.batch-bar-info strong {
  font-weight: 700;
  color: var(--color-primary-400);
}

.batch-bar-actions {
  display: flex;
  gap: var(--space-sm);
}

/* 批量栏动画 */
.batch-bar-enter-active {
  transition: transform var(--duration-fast) var(--ease-smooth),
    opacity var(--duration-fast) var(--ease-smooth);
}

.batch-bar-leave-active {
  transition: transform var(--duration-fast) var(--ease-smooth),
    opacity var(--duration-instant) var(--ease-smooth);
}

.batch-bar-enter-from,
.batch-bar-leave-to {
  transform: translateY(100%);
  opacity: 0;
}

/* ===== 响应式 ===== */
@media (max-width: 1023px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-left {
    flex-wrap: wrap;
  }

  .toolbar-search {
    width: 100%;
  }

  .toolbar-date {
    width: 100%;
  }

  .review-drawer :deep(.el-drawer) {
    width: 100% !important;
  }
}

@media (max-width: 767px) {
  .stats-row {
    grid-template-columns: 1fr 1fr;
  }

  .review-workspace {
    padding: var(--space-sm);
  }
}
</style>
