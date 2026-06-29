<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">优惠券管理</h2>
      <el-button type="primary" @click="handleCreate">
        <el-icon style="margin-right: 4px;"><Plus /></el-icon>
        创建优惠券
      </el-button>
    </div>

    <div class="page-content">
      <!-- 筛选区 -->
      <div class="filter-bar card">
        <div class="filter-left">
          <el-select
            v-model="filterStatus"
            placeholder="券状态"
            clearable
            style="width: 160px;"
            @change="handleSearch"
          >
            <el-option label="全部" value="" />
            <el-option label="启用" value="active" />
            <el-option label="已禁用" value="disabled" />
          </el-select>
          <el-button type="primary" @click="handleSearch">查询</el-button>
        </div>
      </div>

      <!-- 表格卡片 -->
      <div class="card table-card">
        <el-table
          v-loading="loading"
          :data="list"
          stripe
          style="width: 100%;"
          :header-cell-style="{ background: 'var(--color-bg-page)', color: 'var(--color-text-primary)', fontWeight: 600 }"
        >
          <el-table-column prop="id" label="ID" width="70" align="center" />
          <el-table-column prop="title" label="券标题" min-width="160" show-overflow-tooltip />
          <el-table-column label="优惠金额" width="120" align="right">
            <template #default="{ row }">
              <span class="amount-text">¥{{ parseFloat(row.amount).toFixed(2) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="最低订单金额" width="140" align="right">
            <template #default="{ row }">
              <span>¥{{ parseFloat(row.min_order).toFixed(2) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="生效时间" width="175">
            <template #default="{ row }">
              {{ formatDateTime(row.valid_from) }}
            </template>
          </el-table-column>
          <el-table-column label="失效时间" width="175">
            <template #default="{ row }">
              {{ formatDateTime(row.valid_to) }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag
                :type="row.status === 'active' ? 'success' : 'info'"
                size="small"
              >
                {{ row.status === 'active' ? '启用' : '已禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="175">
            <template #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right" align="center">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click="handleGrant(row)">
                发放
              </el-button>
            </template>
          </el-table-column>

          <!-- 空态 -->
          <template #empty>
            <div class="empty-state">
              <el-empty description="暂无优惠券数据">
                <el-button type="primary" @click="handleCreate">创建优惠券</el-button>
              </el-empty>
            </div>
          </template>
        </el-table>

        <!-- 分页 -->
        <div v-if="total > 0" class="pagination-wrapper">
          <el-pagination
            v-model:current-page="page"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50]"
            :total="total"
            layout="total, sizes, prev, pager, next"
            @size-change="handlePageSizeChange"
            @current-change="handlePageChange"
          />
        </div>
      </div>
    </div>

    <!-- 发放弹窗 -->
    <el-dialog
      v-model="grantDialogVisible"
      title="发放优惠券"
      width="480px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form :model="grantForm" label-width="110px">
        <el-form-item label="优惠券">
          <span class="grant-coupon-title">{{ grantTarget?.title }}</span>
        </el-form-item>
        <el-form-item label="用户ID列表">
          <el-input
            v-model="grantForm.userIdsText"
            type="textarea"
            :rows="5"
            placeholder="输入用户ID，多个以逗号分隔。留空则发放给所有用户"
          />
          <div class="form-tip">留空则向所有用户发放该优惠券</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="grantDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="grantLoading" @click="confirmGrant">
          确认发放
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 平台后台 - 优惠券列表页
 * 功能：优惠券列表展示、状态筛选、创建入口、发放操作
 */
import { ref, reactive, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Plus } from '@element-plus/icons-vue';
import { getCouponList, grantCoupon } from '@/api/admin/coupon.js';

const router = useRouter();

/* ──────── 列表状态 ──────── */
const loading = ref(false);
const list = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const filterStatus = ref('');

/* ──────── 发放弹窗状态 ──────── */
const grantDialogVisible = ref(false);
const grantLoading = ref(false);
const grantTarget = ref(null);
const grantForm = reactive({
  userIdsText: ''
});

/* ──────── 工具函数 ──────── */
function formatDateTime(str) {
  if (!str) return '-';
  try {
    const d = new Date(str);
    if (isNaN(d.getTime())) return str;
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const h = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    const s = String(d.getSeconds()).padStart(2, '0');
    return `${y}-${m}-${day} ${h}:${min}:${s}`;
  } catch {
    return str;
  }
}

/* ──────── 数据获取 ──────── */
async function fetchList() {
  loading.value = true;
  try {
    const params = { page: page.value, pageSize: pageSize.value };
    if (filterStatus.value) {
      params.status = filterStatus.value;
    }
    const res = await getCouponList(params);
    if (res?.success !== false) {
      list.value = res?.data?.list ?? [];
      total.value = res?.data?.total ?? 0;
    } else {
      ElMessage.error(res?.message || '获取优惠券列表失败');
    }
  } catch (err) {
    ElMessage.error('获取优惠券列表失败，请稍后重试');
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  page.value = 1;
  fetchList();
}

function handlePageChange(newPage) {
  page.value = newPage;
  fetchList();
}

function handlePageSizeChange(newSize) {
  pageSize.value = newSize;
  page.value = 1;
  fetchList();
}

/* ──────── 跳转创建页 ──────── */
function handleCreate() {
  router.push({ name: 'AdminCouponCreate' });
}

/* ──────── 发放操作 ──────── */
function handleGrant(row) {
  grantTarget.value = row;
  grantForm.userIdsText = '';
  grantDialogVisible.value = true;
}

async function confirmGrant() {
  if (!grantTarget.value) return;

  const rawText = grantForm.userIdsText.trim();
  let userIds = [];
  if (rawText) {
    const parts = rawText.split(',').map(s => s.trim()).filter(Boolean);
    userIds = parts.map(Number).filter(n => Number.isFinite(n) && n > 0);
    if (userIds.length === 0 && rawText.length > 0) {
      ElMessage.warning('请输入有效的用户ID（正整数，逗号分隔）');
      return;
    }
  }

  grantLoading.value = true;
  try {
    const res = await grantCoupon(grantTarget.value.id, { userIds });
    if (res?.success !== false) {
      const count = res?.data?.grantedCount ?? 0;
      ElMessage.success(`成功发放，${count} 位用户已领取`);
      grantDialogVisible.value = false;
    } else {
      ElMessage.error(res?.message || '发放失败');
    }
  } catch (err) {
    ElMessage.error('发放失败，请稍后重试');
  } finally {
    grantLoading.value = false;
  }
}

/* ──────── 生命周期 ──────── */
onMounted(() => {
  fetchList();
});
</script>

<style scoped>
.page-container {
  padding: var(--spacing-xl, 24px);
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg, 20px);
}

.page-title {
  font-size: var(--font-size-2xl, 1.25rem);
  font-weight: 600;
  color: var(--color-text-primary, #1a1a2e);
  margin: 0;
}

.page-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-base, 16px);
}

.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-base, 16px);
}

.filter-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm, 8px);
}

.table-card {
  padding: 0;
  overflow: hidden;
}

.amount-text {
  color: var(--color-danger, #ef4444);
  font-weight: 500;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding: var(--spacing-base, 16px);
  border-top: 1px solid var(--color-border-lighter, #f0f0f0);
}

.empty-state {
  padding: var(--spacing-2xl, 32px) 0;
}

.form-tip {
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-placeholder, #c0c4cc);
  margin-top: 4px;
}

.grant-coupon-title {
  font-weight: 500;
  color: var(--color-text-primary, #1a1a2e);
}
</style>
