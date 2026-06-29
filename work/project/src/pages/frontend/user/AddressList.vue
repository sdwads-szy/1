<template>
  <div class="page-container address-list-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <el-button
          class="back-btn"
          :icon="ArrowLeft"
          text
          @click="goBack"
        />
        <h1 class="page-title">收货地址</h1>
      </div>
      <el-button type="primary" :icon="Plus" @click="goToCreate">
        新增地址
      </el-button>
    </div>

    <div class="page-content">
      <!-- 加载态 -->
      <div v-if="loading" class="state-wrapper flex-center">
        <el-icon class="loading-icon"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <!-- 错误态 -->
      <div v-else-if="loadError" class="state-wrapper flex-center">
        <el-icon class="error-icon"><WarningFilled /></el-icon>
        <span>{{ loadError }}</span>
        <el-button type="primary" size="small" @click="fetchAddresses">重试</el-button>
      </div>

      <!-- 空态 -->
      <div v-else-if="addresses.length === 0" class="state-wrapper flex-center empty-state">
        <el-icon class="empty-icon"><MapLocation /></el-icon>
        <span class="empty-text">暂无收货地址</span>
        <el-button type="primary" :icon="Plus" @click="goToCreate">添加新地址</el-button>
      </div>

      <!-- 地址列表 -->
      <div v-else class="address-list">
        <div
          v-for="addr in addresses"
          :key="addr.id"
          class="address-item card"
        >
          <div class="addr-main">
            <div class="addr-header">
              <div class="addr-user">
                <span class="addr-name">{{ addr.name }}</span>
                <span class="addr-phone">{{ addr.phone }}</span>
              </div>
              <el-tag
                v-if="addr.is_default === 1 || addr.is_default === true"
                type="warning"
                size="small"
                effect="light"
                class="default-tag"
              >
                默认
              </el-tag>
            </div>
            <div class="addr-detail">
              {{ addr.province }}{{ addr.city }}{{ addr.district }} {{ addr.detail }}
            </div>
          </div>
          <div class="addr-actions">
            <el-button
              type="primary"
              link
              :icon="Edit"
              @click="goToEdit(addr)"
            >
              编辑
            </el-button>
            <el-button
              type="danger"
              link
              :icon="Delete"
              @click="handleDelete(addr)"
            >
              删除
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  Loading,
  WarningFilled,
  MapLocation,
  Plus,
  ArrowLeft,
  Edit,
  Delete
} from '@element-plus/icons-vue';
import { getAddresses, deleteAddress } from '@/api/user';

const router = useRouter();

// --- 状态 ---
const loading = ref(true);
const loadError = ref('');
const addresses = ref([]);

// --- 方法 ---
async function fetchAddresses() {
  loading.value = true;
  loadError.value = '';
  try {
    const res = await getAddresses();
    const data = res.data || res;
    addresses.value = Array.isArray(data) ? data : (data.list || []);
  } catch (err) {
    loadError.value = err?.response?.data?.message || err?.message || '加载失败，请重试';
  } finally {
    loading.value = false;
  }
}

function goBack() {
  router.push({ name: 'Profile' });
}

function goToCreate() {
  router.push({ name: 'AddressEdit', params: { id: 'new' } });
}

function goToEdit(addr) {
  router.push({ name: 'AddressEdit', params: { id: addr.id } });
}

async function handleDelete(addr) {
  try {
    await ElMessageBox.confirm(
      `确定要删除地址「${addr.province}${addr.city}${addr.district}」吗？`,
      '删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    );
  } catch {
    return;
  }

  try {
    await deleteAddress(addr.id);
    ElMessage.success('地址已删除');
    await fetchAddresses();
  } catch (err) {
    const msg = err?.response?.data?.message || '删除失败，请重试';
    ElMessage.error(msg);
  }
}

// --- 生命周期 ---
onMounted(() => {
  fetchAddresses();
});
</script>

<style scoped>
.address-list-page {
  max-width: 720px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--app-space-xl) 0 var(--app-space-lg);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--app-space-xs);
}

.back-btn {
  font-size: 20px;
  color: var(--app-text-secondary);
}

.page-title {
  font-size: var(--app-font-3xl);
  font-weight: 700;
  color: var(--app-text-primary);
  margin: 0;
}

.state-wrapper {
  flex-direction: column;
  gap: var(--app-space-sm);
  padding: var(--app-space-4xl) 0;
  color: var(--app-text-secondary);
}

.loading-icon {
  font-size: 32px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.error-icon {
  font-size: 32px;
  color: var(--app-color-danger);
}

.empty-state {
  padding: var(--app-space-5xl) 0;
}

.empty-icon {
  font-size: 56px;
  color: #fdba74;
}

.empty-text {
  font-size: var(--app-font-lg);
  color: var(--app-text-secondary);
  margin-bottom: var(--app-space-sm);
}

/* 地址列表 */
.address-list {
  display: flex;
  flex-direction: column;
  gap: var(--app-space-md);
}

.address-item {
  padding: var(--app-space-base) var(--app-space-xl);
  display: flex;
  align-items: center;
  justify-content: space-between;
  transition: all 0.2s var(--app-ease-standard);
  border-left: 4px solid transparent;
}

.address-item:hover {
  box-shadow: var(--app-shadow-level-2);
  border-left-color: #f97316;
}

.addr-main {
  flex: 1;
  min-width: 0;
}

.addr-header {
  display: flex;
  align-items: center;
  gap: var(--app-space-sm);
  margin-bottom: var(--app-space-xs);
}

.addr-user {
  display: flex;
  align-items: center;
  gap: var(--app-space-md);
}

.addr-name {
  font-size: var(--app-font-lg);
  font-weight: 600;
  color: var(--app-text-primary);
}

.addr-phone {
  font-size: var(--app-font-sm);
  color: var(--app-text-secondary);
}

.default-tag {
  flex-shrink: 0;
}

.addr-detail {
  font-size: var(--app-font-sm);
  color: var(--app-text-regular);
  line-height: 1.5;
  word-break: break-all;
}

.addr-actions {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex-shrink: 0;
  margin-left: var(--app-space-base);
}
</style>
