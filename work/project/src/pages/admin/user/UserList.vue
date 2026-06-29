<template>
  <div class="user-list-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2 class="page-title">用户管理</h2>
      <p class="page-subtitle">平台用户审核、封禁与角色管理</p>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-value">{{ stats.total }}</div>
        <div class="stat-label">用户总数</div>
      </div>
      <div class="stat-card stat-card--active">
        <div class="stat-value">{{ stats.active }}</div>
        <div class="stat-label">活跃用户</div>
      </div>
      <div class="stat-card stat-card--banned">
        <div class="stat-value">{{ stats.banned }}</div>
        <div class="stat-label">已封禁</div>
      </div>
      <div class="stat-card stat-card--merchant">
        <div class="stat-value">{{ stats.merchant }}</div>
        <div class="stat-label">商家</div>
      </div>
    </div>

    <!-- 筛选区域 -->
    <div class="filter-card">
      <el-form :model="filterForm" inline>
        <el-form-item label="手机号">
          <el-input
            v-model="filterForm.phone"
            placeholder="输入手机号搜索"
            clearable
            class="filter-input"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="filterForm.status"
            placeholder="全部状态"
            clearable
            class="filter-select"
          >
            <el-option label="活跃" value="active" />
            <el-option label="已封禁" value="banned" />
          </el-select>
        </el-form-item>
        <el-form-item label="角色">
          <el-select
            v-model="filterForm.role"
            placeholder="全部角色"
            clearable
            class="filter-select"
          >
            <el-option label="普通用户" value="user" />
            <el-option label="商家" value="merchant" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 用户表格 -->
    <div class="table-card">
      <el-table
        v-loading="loading"
        :data="tableData"
        stripe
        class="user-table"
        @row-click="handleRowClick"
      >
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="phone" label="手机号" min-width="140" />
        <el-table-column prop="nickname" label="昵称" min-width="140">
          <template #default="{ row }">
            <span>{{ row.nickname || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="role" label="角色" width="120" align="center">
          <template #default="{ row }">
            <el-tag
              :type="roleTagType(row.role)"
              size="small"
              effect="dark"
            >
              {{ roleLabel(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <span class="status-dot" :class="'status-dot--' + row.status"></span>
            {{ row.status === 'active' ? '活跃' : '已封禁' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="180" align="center">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'active'"
              type="danger"
              size="small"
              link
              @click.stop="handleBan(row)"
            >
              封禁
            </el-button>
            <el-button
              v-else
              type="success"
              size="small"
              link
              @click.stop="handleUnban(row)"
            >
              解封
            </el-button>
            <el-button
              type="primary"
              size="small"
              link
              @click.stop="handleRoleChange(row)"
            >
              变更角色
            </el-button>
            <el-button
              type="primary"
              size="small"
              link
              @click.stop="handleViewDetail(row)"
            >
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @size-change="fetchList"
          @current-change="fetchList"
        />
      </div>
    </div>

    <!-- 角色变更弹窗 -->
    <el-dialog
      v-model="roleDialogVisible"
      title="变更用户角色"
      width="420px"
      :close-on-click-modal="false"
    >
      <div class="role-dialog-content">
        <p class="role-dialog-info">
          用户：<strong>{{ selectedUser?.nickname || selectedUser?.phone }}</strong>
        </p>
        <p class="role-dialog-info">
          当前角色：
          <el-tag :type="roleTagType(selectedUser?.role)" size="small" effect="dark">
            {{ roleLabel(selectedUser?.role) }}
          </el-tag>
        </p>
        <el-form class="role-form">
          <el-form-item label="新角色">
            <el-select v-model="newRole" placeholder="请选择角色" class="w-full">
              <el-option label="普通用户 (user)" value="user" />
              <el-option label="商家 (merchant)" value="merchant" />
              <el-option label="管理员 (admin)" value="admin" />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="roleDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="roleSubmitting"
          @click="submitRoleChange"
        >
          确认变更
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { getUserList, banUser, unbanUser, updateUserRole } from '@/api/admin/user';

const router = useRouter();

/* ===== 筛选 ===== */
const filterForm = reactive({
  phone: '',
  status: '',
  role: ''
});

function handleSearch() {
  pagination.page = 1;
  fetchList();
}

function handleReset() {
  filterForm.phone = '';
  filterForm.status = '';
  filterForm.role = '';
  pagination.page = 1;
  fetchList();
}

/* ===== 表格数据 ===== */
const loading = ref(false);
const tableData = ref([]);
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
});

const stats = reactive({
  total: 0,
  active: 0,
  banned: 0,
  merchant: 0
});

async function fetchList() {
  loading.value = true;
  try {
    const params = {
      page: pagination.page,
      pageSize: pagination.pageSize
    };
    if (filterForm.phone) params.phone = filterForm.phone;
    if (filterForm.status) params.status = filterForm.status;
    if (filterForm.role) params.role = filterForm.role;

    const res = await getUserList(params);
    const data = res.data || res;
    tableData.value = data.list || [];
    pagination.total = data.total || 0;

    // 简易统计（实际可从后端单独获取）
    stats.total = data.total || 0;
    stats.active = (data.list || []).filter(u => u.status === 'active').length;
    stats.banned = (data.list || []).filter(u => u.status === 'banned').length;
    stats.merchant = (data.list || []).filter(u => u.role === 'merchant').length;
  } catch (e) {
    ElMessage.error('获取用户列表失败');
  } finally {
    loading.value = false;
  }
}

/* ===== 操作 ===== */
function handleViewDetail(row) {
  router.push({ name: 'AdminUserDetail', params: { id: row.id } });
}

function handleRowClick(row) {
  router.push({ name: 'AdminUserDetail', params: { id: row.id } });
}

async function handleBan(row) {
  try {
    await ElMessageBox.confirm(
      `确定封禁用户「${row.nickname || row.phone}」吗？封禁后该用户将无法登录。`,
      '封禁确认',
      { confirmButtonText: '确认封禁', cancelButtonText: '取消', type: 'warning' }
    );
    await banUser(row.id);
    ElMessage.success('封禁成功');
    fetchList();
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e?.response?.data?.message || '封禁失败');
    }
  }
}

async function handleUnban(row) {
  try {
    await ElMessageBox.confirm(
      `确定解封用户「${row.nickname || row.phone}」吗？`,
      '解封确认',
      { confirmButtonText: '确认解封', cancelButtonText: '取消', type: 'info' }
    );
    await unbanUser(row.id);
    ElMessage.success('解封成功');
    fetchList();
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e?.response?.data?.message || '解封失败');
    }
  }
}

/* ===== 角色变更 ===== */
const roleDialogVisible = ref(false);
const selectedUser = ref(null);
const newRole = ref('');
const roleSubmitting = ref(false);

function handleRoleChange(row) {
  selectedUser.value = row;
  newRole.value = row.role;
  roleDialogVisible.value = true;
}

async function submitRoleChange() {
  if (!newRole.value) {
    ElMessage.warning('请选择新角色');
    return;
  }
  if (newRole.value === selectedUser.value.role) {
    ElMessage.warning('角色未变更');
    return;
  }
  roleSubmitting.value = true;
  try {
    await updateUserRole(selectedUser.value.id, { role: newRole.value });
    ElMessage.success('角色变更成功');
    roleDialogVisible.value = false;
    fetchList();
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || '角色变更失败');
  } finally {
    roleSubmitting.value = false;
  }
}

/* ===== 工具函数 ===== */
function roleLabel(role) {
  const map = { user: '普通用户', merchant: '商家', admin: '管理员' };
  return map[role] || role;
}

function roleTagType(role) {
  const map = { user: '', merchant: 'warning', admin: 'danger' };
  return map[role] || '';
}

function formatDate(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/* ===== 生命周期 ===== */
onMounted(() => {
  fetchList();
});
</script>

<style scoped>
.user-list-page {
  padding: 24px;
  min-height: 100vh;
  background: #0f1923;
}

/* 页面标题 */
.page-header {
  margin-bottom: 24px;
}

.page-title {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  color: #e8edf2;
  letter-spacing: 0.5px;
}

.page-subtitle {
  margin: 6px 0 0;
  font-size: 13px;
  color: #6b7c8e;
}

/* 统计卡片 */
.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: #152233;
  border: 1px solid #1e3044;
  border-radius: 10px;
  padding: 20px 24px;
  text-align: center;
  transition: border-color 0.2s, transform 0.2s;
}

.stat-card:hover {
  border-color: #2d4a6a;
  transform: translateY(-2px);
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #e8edf2;
  line-height: 1.2;
}

.stat-label {
  margin-top: 6px;
  font-size: 13px;
  color: #6b7c8e;
}

.stat-card--active .stat-value { color: #22c55e; }
.stat-card--banned .stat-value { color: #ef4444; }
.stat-card--merchant .stat-value { color: #f59e0b; }

/* 筛选区域 */
.filter-card {
  background: #152233;
  border: 1px solid #1e3044;
  border-radius: 10px;
  padding: 16px 20px 4px;
  margin-bottom: 16px;
}

.filter-input,
.filter-select {
  width: 180px;
}

/* 表格卡片 */
.table-card {
  background: #152233;
  border: 1px solid #1e3044;
  border-radius: 10px;
  overflow: hidden;
}

/* 表格样式 - 深色主题 */
.user-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: #0d1a28;
  --el-table-row-hover-bg-color: rgba(59, 130, 246, 0.06);
  --el-table-border-color: #1e3044;
  --el-table-text-color: #c8d6e5;
  --el-table-header-text-color: #8899aa;
}

.user-table :deep(.el-table__header-wrapper) {
  border-bottom: 2px solid #1e3044;
}

.user-table :deep(.el-table__header th) {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background-color: #0d1a28 !important;
}

.user-table :deep(.el-table__body tr) {
  cursor: pointer;
  transition: background-color 0.15s;
}

.user-table :deep(.el-table__body tr:hover) {
  background-color: rgba(59, 130, 246, 0.06) !important;
}

.user-table :deep(.el-table__body td) {
  border-bottom-color: #1a2b3c;
}

/* 状态圆点 */
.status-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}

.status-dot--active {
  background: #22c55e;
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.5);
}

.status-dot--banned {
  background: #ef4444;
  box-shadow: 0 0 6px rgba(239, 68, 68, 0.5);
}

/* 分页 */
.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding: 16px 20px;
  border-top: 1px solid #1e3044;
}

/* 角色弹窗 */
.role-dialog-content {
  padding: 8px 0;
}

.role-dialog-info {
  margin: 0 0 12px;
  font-size: 14px;
  color: #374151;
}

.role-form {
  margin-top: 16px;
}

.w-full {
  width: 100%;
}

/* 覆盖 Element Plus 暗色主题 - 筛选表单 */
.filter-card :deep(.el-form-item__label) {
  color: #8899aa;
  font-size: 13px;
}

.filter-card :deep(.el-input__wrapper) {
  background-color: #0d1a28;
  border-color: #1e3044;
  box-shadow: none;
}

.filter-card :deep(.el-input__wrapper:hover) {
  border-color: #2d4a6a;
}

.filter-card :deep(.el-input__wrapper.is-focus) {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.15);
}

.filter-card :deep(.el-input__inner) {
  color: #c8d6e5;
}

.filter-card :deep(.el-input__inner::placeholder) {
  color: #4a5a6a;
}

.filter-card :deep(.el-select .el-input__wrapper) {
  background-color: #0d1a28;
}

/* 分页暗色 */
.pagination-wrapper :deep(.el-pagination) {
  --el-pagination-bg-color: transparent;
  --el-pagination-text-color: #8899aa;
  --el-pagination-button-bg-color: #0d1a28;
  --el-pagination-button-color: #8899aa;
  --el-pagination-button-disabled-bg-color: #0d1a28;
  --el-pagination-button-disabled-color: #3a4a5a;
  --el-pagination-hover-color: #409eff;
}

.pagination-wrapper :deep(.el-pagination .btn-prev),
.pagination-wrapper :deep(.el-pagination .btn-next),
.pagination-wrapper :deep(.el-pagination .el-pager li) {
  background-color: #0d1a28 !important;
  border: 1px solid #1e3044;
  color: #8899aa;
}

.pagination-wrapper :deep(.el-pagination .el-pager li.is-active) {
  background-color: #409eff !important;
  border-color: #409eff;
  color: #fff;
}

/* 弹窗内覆盖为亮色（因为 el-dialog 默认白色背景） */
.role-dialog-content :deep(.el-select .el-input__wrapper) {
  background-color: #fff;
}

.role-dialog-content :deep(.el-input__inner) {
  color: #374151;
}
</style>
