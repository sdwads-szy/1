<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">退款管理</h1>
    </div>

    <div class="page-content">
      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-select
          v-model="filters.status"
          placeholder="退款状态"
          clearable
          style="width: 180px"
          @change="handleSearch"
        >
          <el-option label="全部" value="" />
          <el-option label="已申请" value="applied" />
          <el-option label="已审核" value="approved" />
          <el-option label="已拒绝" value="rejected" />
          <el-option label="处理中" value="processing" />
          <el-option label="已完成" value="completed" />
        </el-select>
        <el-button type="primary" @click="handleSearch">
          <el-icon><Search /></el-icon>
          搜索
        </el-button>
        <el-button @click="handleReset">重置</el-button>
      </div>

      <!-- 表格 -->
      <el-table
        v-loading="loading"
        :data="list"
        stripe
        border
        style="width: 100%"
        highlight-current-row
        @row-click="handleRowClick"
      >
        <el-table-column prop="id" label="退款ID" width="90" align="center" />
        <el-table-column prop="order_id" label="订单ID" width="100" align="center" />
        <el-table-column prop="user_id" label="用户ID" width="90" align="center" />
        <el-table-column prop="merchant_id" label="商家ID" width="90" align="center" />
        <el-table-column prop="reason" label="退款原因" min-width="180" show-overflow-tooltip />
        <el-table-column prop="amount" label="退款金额" width="130" align="right">
          <template #default="{ row }">
            <span class="amount-text">¥{{ formatAmount(row.amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="apply_at" label="申请时间" width="175" align="center">
          <template #default="{ row }">
            {{ formatTime(row.apply_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'approved'"
              type="primary"
              size="small"
              link
              @click.stop="handleExecute(row)"
            >
              执行退款
            </el-button>
            <el-button
              type="primary"
              size="small"
              link
              @click.stop="handleView(row)"
            >
              查看详情
            </el-button>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="暂无退款记录" />
        </template>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchList"
          @current-change="fetchList"
        />
      </div>
    </div>

    <!-- 执行退款确认弹窗 -->
    <el-dialog
      v-model="executeDialogVisible"
      title="确认执行退款"
      width="440px"
      :close-on-click-modal="false"
    >
      <div class="dialog-body">
        <p>确定要对退款单 <strong>#{{ executeTarget?.id }}</strong> 执行退款操作吗？</p>
        <p>退款金额：<strong class="amount-emphasis">¥{{ formatAmount(executeTarget?.amount) }}</strong></p>
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
 * 平台后台 - 退款管理列表页
 * 展示所有退款申请，支持状态筛选、查看详情、执行退款
 */
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, WarningFilled } from '@element-plus/icons-vue'
import { getRefundList, executeRefund } from '@/api/admin/refund'

const router = useRouter()

// --- state ---
const loading = ref(false)
const list = ref([])
const total = ref(0)
const executing = ref(false)
const executeDialogVisible = ref(false)
const executeTarget = ref(null)

const filters = reactive({
  status: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20
})

// --- constants ---
const statusMap = {
  applied: { label: '已申请', type: 'warning' },
  approved: { label: '已审核', type: 'info' },
  rejected: { label: '已拒绝', type: 'danger' },
  processing: { label: '处理中', type: '' },
  completed: { label: '已完成', type: 'success' }
}

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
    minute: '2-digit',
    second: '2-digit'
  })
}

async function fetchList() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      pageSize: pagination.pageSize
    }
    if (filters.status) {
      params.status = filters.status
    }
    const res = await getRefundList(params)
    const data = res.data ?? res
    list.value = data.list ?? []
    total.value = data.total ?? 0
  } catch {
    ElMessage.error('获取退款列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  fetchList()
}

function handleReset() {
  filters.status = ''
  pagination.page = 1
  fetchList()
}

function handleRowClick(row) {
  router.push({ name: 'AdminRefundDetail', params: { id: row.id } })
}

function handleView(row) {
  router.push({ name: 'AdminRefundDetail', params: { id: row.id } })
}

function handleExecute(row) {
  executeTarget.value = row
  executeDialogVisible.value = true
}

async function confirmExecute() {
  if (!executeTarget.value) return
  executing.value = true
  try {
    await executeRefund(executeTarget.value.id)
    ElMessage.success('退款执行成功')
    executeDialogVisible.value = false
    executeTarget.value = null
    fetchList()
  } catch {
    ElMessage.error('退款执行失败')
  } finally {
    executing.value = false
  }
}

// --- lifecycle ---
onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.page-container {
  padding: var(--app-space-xl);
  min-height: 100%;
  background: var(--app-bg-page);
}

.page-header {
  margin-bottom: var(--app-space-xl);
}

.page-title {
  font-size: var(--app-font-2xl);
  font-weight: 600;
  color: #152233;
  margin: 0;
}

.page-content {
  background: var(--app-bg-container);
  border-radius: var(--app-radius-md);
  padding: var(--app-space-xl);
  box-shadow: var(--app-shadow-level-1);
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: var(--app-space-md);
  margin-bottom: var(--app-space-lg);
  flex-wrap: wrap;
}

.amount-text {
  font-weight: 600;
  color: #152233;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--app-space-lg);
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

:deep(.el-table__row) {
  cursor: pointer;
}
</style>
