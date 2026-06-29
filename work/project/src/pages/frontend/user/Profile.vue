<template>
  <div class="page-container profile-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">个人中心</h1>
      <p class="page-subtitle">管理您的个人信息与收货地址</p>
    </div>

    <div class="page-content">
      <!-- 加载态 -->
      <div v-if="loading" class="loading-wrapper flex-center">
        <el-icon class="loading-icon"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <!-- 错误态 -->
      <div v-else-if="loadError" class="error-wrapper flex-center">
        <el-icon class="error-icon"><WarningFilled /></el-icon>
        <span>{{ loadError }}</span>
        <el-button type="primary" size="small" @click="fetchProfile">重试</el-button>
      </div>

      <!-- 用户信息卡片 -->
      <template v-else>
        <div class="profile-card card">
          <!-- 头像区 -->
          <div class="avatar-section">
            <div class="avatar-wrapper">
              <el-avatar
                :size="100"
                :src="profile.avatar"
                class="profile-avatar"
              >
                {{ profile.nickname ? profile.nickname.charAt(0) : 'U' }}
              </el-avatar>
              <div v-if="isEditing" class="avatar-overlay" @click="showAvatarInput = true">
                <el-icon><Camera /></el-icon>
              </div>
            </div>
          </div>

          <!-- 查看模式 -->
          <div v-if="!isEditing" class="info-section">
            <div class="info-row">
              <span class="info-label">昵称</span>
              <span class="info-value">{{ profile.nickname || '未设置' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">手机号</span>
              <span class="info-value phone-masked">{{ profile.phone || '***' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">角色</span>
              <el-tag :type="roleTagType" size="small" class="role-tag">
                {{ roleLabel }}
              </el-tag>
            </div>
            <div class="info-actions">
              <el-button type="primary" @click="enterEdit">编辑资料</el-button>
            </div>
          </div>

          <!-- 编辑模式 -->
          <div v-else class="info-section edit-section">
            <el-form
              ref="formRef"
              :model="editForm"
              :rules="formRules"
              label-width="80px"
              class="profile-form"
            >
              <el-form-item label="头像地址" prop="avatar">
                <el-input
                  v-model="editForm.avatar"
                  placeholder="请输入头像图片URL"
                  clearable
                />
              </el-form-item>
              <el-form-item label="昵称" prop="nickname">
                <el-input
                  v-model="editForm.nickname"
                  placeholder="请输入昵称"
                  maxlength="50"
                  show-word-limit
                />
              </el-form-item>
              <div class="info-actions">
                <el-button @click="cancelEdit">取消</el-button>
                <el-button type="primary" :loading="saving" @click="saveProfile">保存</el-button>
              </div>
            </el-form>
          </div>
        </div>

        <!-- 地址管理入口 -->
        <div class="address-entry card" @click="goToAddresses">
          <div class="entry-left">
            <el-icon class="entry-icon"><LocationFilled /></el-icon>
            <div class="entry-text">
              <span class="entry-title">收货地址管理</span>
              <span class="entry-desc">管理您的常用收货地址</span>
            </div>
          </div>
          <el-icon class="entry-arrow"><ArrowRight /></el-icon>
        </div>
      </template>
    </div>

    <!-- 头像URL编辑弹窗 -->
    <el-dialog
      v-model="showAvatarInput"
      title="修改头像"
      width="400px"
      :close-on-click-modal="false"
    >
      <el-form :model="avatarForm" label-width="80px">
        <el-form-item label="头像地址">
          <el-input v-model="avatarForm.url" placeholder="请输入头像图片URL" clearable />
        </el-form-item>
        <div class="avatar-preview" v-if="avatarForm.url">
          <el-avatar :size="80" :src="avatarForm.url" />
        </div>
      </el-form>
      <template #footer>
        <el-button @click="showAvatarInput = false">取消</el-button>
        <el-button type="primary" @click="confirmAvatar">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Loading, WarningFilled, Camera, LocationFilled, ArrowRight } from '@element-plus/icons-vue';
import { getProfile, updateProfile } from '@/api/user';

const router = useRouter();

// --- 状态 ---
const loading = ref(true);
const loadError = ref('');
const isEditing = ref(false);
const saving = ref(false);
const showAvatarInput = ref(false);
const formRef = ref(null);

const profile = reactive({
  nickname: '',
  avatar: '',
  phone: '',
  role: 'user'
});

const editForm = reactive({
  nickname: '',
  avatar: ''
});

const avatarForm = reactive({
  url: ''
});

// --- 表单校验 ---
const formRules = {
  nickname: [
    { required: true, message: '请输入昵称', trigger: 'blur' },
    { min: 1, max: 50, message: '昵称长度1-50个字符', trigger: 'blur' }
  ]
};

// --- 计算属性 ---
const roleMap = {
  user: { label: '普通用户', type: '' },
  merchant: { label: '商家', type: 'warning' },
  admin: { label: '管理员', type: 'danger' }
};

const roleLabel = computed(() => {
  return roleMap[profile.role]?.label || profile.role;
});

const roleTagType = computed(() => {
  return roleMap[profile.role]?.type || 'info';
});

// --- 方法 ---
async function fetchProfile() {
  loading.value = true;
  loadError.value = '';
  try {
    const res = await getProfile();
    const data = res.data || res;
    Object.assign(profile, {
      nickname: data.nickname || '',
      avatar: data.avatar || '',
      phone: data.phone || '',
      role: data.role || 'user'
    });
  } catch (err) {
    loadError.value = err?.response?.data?.message || err?.message || '加载失败，请重试';
  } finally {
    loading.value = false;
  }
}

function enterEdit() {
  editForm.nickname = profile.nickname;
  editForm.avatar = profile.avatar;
  isEditing.value = true;
}

function cancelEdit() {
  isEditing.value = false;
  formRef.value?.resetFields();
}

async function saveProfile() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;

  saving.value = true;
  try {
    await updateProfile({
      nickname: editForm.nickname,
      avatar: editForm.avatar
    });
    profile.nickname = editForm.nickname;
    profile.avatar = editForm.avatar;
    isEditing.value = false;
    ElMessage.success('资料更新成功');
  } catch (err) {
    const msg = err?.response?.data?.message || '保存失败，请重试';
    ElMessage.error(msg);
  } finally {
    saving.value = false;
  }
}

function confirmAvatar() {
  editForm.avatar = avatarForm.url;
  showAvatarInput.value = false;
}

function goToAddresses() {
  router.push({ name: 'AddressList' });
}

// --- 生命周期 ---
onMounted(() => {
  fetchProfile();
});
</script>

<style scoped>
.profile-page {
  max-width: 640px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  padding: var(--app-space-xl) 0 var(--app-space-lg);
}

.page-title {
  font-size: var(--app-font-3xl);
  font-weight: 700;
  color: var(--app-text-primary);
  margin: 0 0 var(--app-space-xs);
}

.page-subtitle {
  font-size: var(--app-font-sm);
  color: var(--app-text-secondary);
  margin: 0;
}

.loading-wrapper,
.error-wrapper {
  flex-direction: column;
  gap: var(--app-space-sm);
  padding: var(--app-space-4xl) 0;
  color: var(--app-text-secondary);
}

.loading-icon,
.error-icon {
  font-size: 32px;
}

.error-icon {
  color: var(--app-color-danger);
}

/* 个人信息卡片 */
.profile-card {
  padding: var(--app-space-2xl);
  text-align: center;
}

.avatar-section {
  margin-bottom: var(--app-space-xl);
}

.avatar-wrapper {
  position: relative;
  display: inline-block;
}

.profile-avatar {
  border: 3px solid #fed7aa;
  box-shadow: 0 0 0 4px rgba(249, 115, 22, 0.1);
}

.avatar-overlay {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 24px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s var(--app-ease-standard);
}

.avatar-wrapper:hover .avatar-overlay {
  opacity: 1;
}

/* 信息行 */
.info-section {
  max-width: 360px;
  margin: 0 auto;
}

.info-row {
  display: flex;
  align-items: center;
  padding: var(--app-space-md) 0;
  border-bottom: 1px solid var(--app-border-light);
}

.info-row:last-of-type {
  border-bottom: none;
}

.info-label {
  width: 80px;
  font-size: var(--app-font-sm);
  color: var(--app-text-secondary);
  flex-shrink: 0;
}

.info-value {
  font-size: var(--app-font-base);
  color: var(--app-text-primary);
  flex: 1;
  text-align: left;
}

.phone-masked {
  letter-spacing: 2px;
}

.role-tag {
  text-transform: capitalize;
}

.info-actions {
  margin-top: var(--app-space-xl);
  display: flex;
  gap: var(--app-space-sm);
  justify-content: center;
}

/* 编辑表单 */
.edit-section {
  text-align: left;
}

.profile-form {
  max-width: 400px;
  margin: 0 auto;
}

/* 地址入口 */
.address-entry {
  margin-top: var(--app-space-lg);
  padding: var(--app-space-base) var(--app-space-xl);
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  transition: all 0.2s var(--app-ease-standard);
  border-left: 3px solid #f97316;
}

.address-entry:hover {
  box-shadow: var(--app-shadow-level-2);
  transform: translateY(-2px);
}

.entry-left {
  display: flex;
  align-items: center;
  gap: var(--app-space-md);
}

.entry-icon {
  font-size: 28px;
  color: #f97316;
  background: #fff7ed;
  padding: var(--app-space-sm);
  border-radius: var(--app-radius-base);
}

.entry-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  text-align: left;
}

.entry-title {
  font-size: var(--app-font-lg);
  font-weight: 600;
  color: var(--app-text-primary);
}

.entry-desc {
  font-size: var(--app-font-xs);
  color: var(--app-text-secondary);
}

.entry-arrow {
  font-size: 18px;
  color: var(--app-text-secondary);
}

/* 头像预览 */
.avatar-preview {
  margin-top: var(--app-space-sm);
  text-align: center;
}
</style>
