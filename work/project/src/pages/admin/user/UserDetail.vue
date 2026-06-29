<template>
  <div class="user-detail-page">
    <!-- 面包屑 -->
    <div class="breadcrumb-area">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item>
          <span class="breadcrumb-link" @click="goBack">用户管理</span>
        </el-breadcrumb-item>
        <el-breadcrumb-item>用户详情</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">用户详情</h2>
        <p class="page-subtitle">查看用户完整信息与状态</p>
      </div>
      <div class="header-right">
        <el-button @click="goBack">返回列表</el-button>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="loading-area">
      <el-skeleton :rows="8" animated />
    </div>

    <!-- 详情内容 -->
    <template v-else-if="user">
      <!-- 基本信息卡片 -->
      <div class="detail-card">
        <div class="card-header">
          <h3 class="card-title">基本信息</h3>
          <div class="card-badge">
            <span class="status-dot" :class="'status-dot--' + user.status"></span>
            <el-tag
              :type="user.status === 'active' ? 'success' : 'danger'"
              size="small"
              effect="dark"
            >
              {{ user.status === 'active' ? '活跃' : '已封禁' }}
            </el-tag>
          </div>
        </div>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">用户 ID</span>
            <span class="info-value">{{ user.id }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">手机号</span>
            <span class="info-value">{{ user.phone }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">昵称</span>
            <span class="info-value">{{ user.nickname || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">角色</span>
            <span class="info-value">
              <el-tag
                :type="roleTagType(user.role)"
                size="small"
                effect="dark"
              >
                {{ roleLabel(user.role) }}
              </el-tag>
            </span>
          </div>
          <div class="info-item">
            <span class="info-label">头像</span>
            <span class="info-value">
              <el-avatar
                v-if="user.avatar"
                :src="user.avatar"
                :size="48"
                shape="square"
              />
              <span v-else class="no-avatar">未设置</span>
            </span>
          </div>
          <div class="info-item">
            <span class="info-label">注册时间</span>
            <span class="info-value">{{ formatDate(user.created_at) }}</span>
          </div>
        </div>
      </div>

      <!-- 操作卡片 -->
      <div class="detail-card">
        <div class="card-header">
          <h3 class="card-title">账号操作</h3>
        </div>
        <div class="action-row">
          <div class="action-item">
            <div class="action-info">
              <span class="action-label">角色变更</span>
              <span class="action-desc">修改用户角色权限</span>
            </div>
            <el-select
              v-model="editRole"
              :disabled="roleSaving"
              class="action-select"
              @change="handleRoleSave"
            >
              <el-option label="普通用户 (user)" value="user" />
              <el-option label="商家 (merchant)" value="merchant" />
              <el-option label="管理员 (admin)" value="admin" />
            </el-select>
          </div>
          <div class="action-item">
            <div class="action-info">
              <span class="action-label">
                {{ user.status === 'active' ? '封禁账号' : '解封账号' }}
              </span>
              <span class="action-desc">
                {{ user.status === 'active' ? '封禁后用户将无法登录' : '恢复用户正常访问权限' }}
              </span>
            </div>
            <el-button
              v-if="user.status === 'active'"
              type="danger"
              :loading="statusSaving"
              @click="handleBan"
            >
              封禁
            </el-button>
            <el-button
              v-else
              type="success"
              :loading="statusSaving"
              @click="handleUnban"
            >
              解封
            </el-button>
          </div>
        </div>
      </div>
    </template>

    <!-- 用户不存在 -->
    <div v-else class="empty-area">
      <el-empty description="用户不存在或已被删除" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { getUserList, banUser, unbanUser, updateUserRole } from '@/api/admin/user';

const route = useRoute();
const router = useRouter();

const userId = ref(null);
const loading = ref(false);
const user = ref(null);
const editRole = ref('');
const roleSaving = ref(false);
const statusSaving = ref(false);

/* ===== 数据获取 ===== */
async function fetchUser() {
  const id = route.params.id;
  if (!id) {
    ElMessage.error('缺少用户 ID');
    return;
  }
  userId.value = Number(id);
  loading.value = true;
  try {
    const res = await getUserList({ page: 1, pageSize: 1 });
    const data = res.data || res;
    const list = data.list || [];
    user.value = list.find(u => u.id === userId.value) || null;
    if (user.value) {
      editRole.value = user.value.role;
    }
  } catch (e) {
    ElMessage.error('获取用户信息失败');
  } finally {
    loading.value = false;
  }
}

/* ===== 操作 ===== */
function goBack() {
  router.push({ name: 'AdminUserList' });
}

async function handleRoleSave(newRole) {
  if (!newRole) return;
  if (newRole === user.value.role) {
    ElMessage.warning('角色未变更');
    return;
  }
  roleSaving.value = true;
  try {
    await updateUserRole(userId.value, { role: newRole });
    ElMessage.success('角色变更成功');
    user.value.role = newRole;
  } catch (e) {
    editRole.value = user.value.role;
    ElMessage.error(e?.response?.data?.message || '角色变更失败');
  } finally {
    roleSaving.value = false;
  }
}

async function handleBan() {
  try {
    await ElMessageBox.confirm(
      `确定封禁用户「${user.value.nickname || user.value.phone}」吗？封禁后该用户将无法登录。`,
      '封禁确认',
      { confirmButtonText: '确认封禁', cancelButtonText: '取消', type: 'warning' }
    );
    statusSaving.value = true;
    await banUser(userId.value);
    ElMessage.success('封禁成功');
    user.value.status = 'banned';
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e?.response?.data?.message || '封禁失败');
    }
  } finally {
    statusSaving.value = false;
  }
}

async function handleUnban() {
  try {
    await ElMessageBox.confirm(
      `确定解封用户「${user.value.nickname || user.value.phone}」吗？`,
      '解封确认',
      { confirmButtonText: '确认解封', cancelButtonText: '取消', type: 'info' }
    );
    statusSaving.value = true;
    await unbanUser(userId.value);
    ElMessage.success('解封成功');
    user.value.status = 'active';
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e?.response?.data?.message || '解封失败');
    }
  } finally {
    statusSaving.value = false;
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
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

/* ===== 生命周期 ===== */
onMounted(() => {
  fetchUser();
});
</script>

<style scoped>
.user-detail-page {
  padding: 24px;
  min-height: 100vh;
  background: #0f1923;
}

/* 面包屑 */
.breadcrumb-area {
  margin-bottom: 16px;
}

.breadcrumb-link {
  color: #409eff;
  cursor: pointer;
  transition: color 0.15s;
}

.breadcrumb-link:hover {
  color: #66b1ff;
}

.breadcrumb-area :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
  color: #6b7c8e;
}

.breadcrumb-area :deep(.el-breadcrumb__separator) {
  color: #3a4a5a;
}

/* 页面标题 */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.header-left {
  flex: 1;
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

/* 详情卡片 */
.detail-card {
  background: #152233;
  border: 1px solid #1e3044;
  border-radius: 10px;
  padding: 24px;
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding-bottom: 14px;
  border-bottom: 1px solid #1e3044;
}

.card-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #e8edf2;
}

.card-badge {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 信息网格 */
.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.info-label {
  font-size: 12px;
  font-weight: 500;
  color: #6b7c8e;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-value {
  font-size: 15px;
  color: #c8d6e5;
  word-break: break-all;
}

.no-avatar {
  color: #4a5a6a;
  font-size: 13px;
}

/* 状态圆点 */
.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot--active {
  background: #22c55e;
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.5);
}

.status-dot--banned {
  background: #ef4444;
  box-shadow: 0 0 6px rgba(239, 68, 68, 0.5);
}

/* 操作区 */
.action-row {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.action-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: #0d1a28;
  border: 1px solid #1e3044;
  border-radius: 8px;
  transition: border-color 0.15s;
}

.action-item:hover {
  border-color: #2d4a6a;
}

.action-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.action-label {
  font-size: 14px;
  font-weight: 500;
  color: #c8d6e5;
}

.action-desc {
  font-size: 12px;
  color: #6b7c8e;
}

.action-select {
  width: 200px;
}

/* 加载与空态 */
.loading-area {
  background: #152233;
  border: 1px solid #1e3044;
  border-radius: 10px;
  padding: 32px 24px;
}

.empty-area {
  background: #152233;
  border: 1px solid #1e3044;
  border-radius: 10px;
  padding: 48px 24px;
  text-align: center;
}

.empty-area :deep(.el-empty__description p) {
  color: #6b7c8e;
}

/* 覆盖 Element Plus 暗色主题 - 选择器 */
.action-select :deep(.el-input__wrapper) {
  background-color: #152233;
  border-color: #1e3044;
  box-shadow: none;
}

.action-select :deep(.el-input__wrapper:hover) {
  border-color: #2d4a6a;
}

.action-select :deep(.el-input__wrapper.is-focus) {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.15);
}

.action-select :deep(.el-input__inner) {
  color: #c8d6e5;
}
</style>
