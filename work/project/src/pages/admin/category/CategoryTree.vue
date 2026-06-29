<template>
  <div class="page-container category-admin">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">类目管理</h2>
        <p class="page-desc">管理平台商品类目，最多支持三级层级</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openAddDialog(null)">
        新增根类目
      </el-button>
    </div>

    <el-card class="tree-card" shadow="never">
      <!-- 加载态 -->
      <div v-if="loading" class="state-box">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <p>加载类目数据中...</p>
      </div>

      <!-- 空态 -->
      <div v-else-if="treeData.length === 0" class="state-box empty-state">
        <el-icon :size="48"><FolderOpened /></el-icon>
        <p class="empty-title">暂无类目</p>
        <p class="empty-desc">点击上方按钮创建第一个类目</p>
      </div>

      <!-- 树形数据 -->
      <el-tree
        v-else
        ref="treeRef"
        :data="treeData"
        node-key="id"
        :props="treeProps"
        :expand-on-click-node="false"
        highlight-current
        :default-expand-all="true"
      >
        <template #default="{ node, data }">
          <div class="tree-node">
            <div class="node-info">
              <span class="node-name">{{ data.name }}</span>
              <el-tag
                :type="data.status === 'active' ? 'success' : 'info'"
                size="small"
                class="node-status"
              >
                {{ data.status === 'active' ? '启用' : '禁用' }}
              </el-tag>
              <span class="node-sort">排序 {{ data.sort }}</span>
            </div>
            <div class="node-actions">
              <el-button
                v-if="node.level < 3"
                link
                type="primary"
                size="small"
                @click.stop="openAddDialog(data)"
              >
                添加子类目
              </el-button>
              <el-button
                link
                type="primary"
                size="small"
                @click.stop="openEditDialog(data)"
              >
                编辑
              </el-button>
              <el-button
                link
                type="danger"
                size="small"
                @click.stop="confirmDelete(data)"
              >
                删除
              </el-button>
            </div>
          </div>
        </template>
      </el-tree>
    </el-card>

    <!-- 新增 / 编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑类目' : '新增类目'"
      width="480px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="90px"
        label-position="right"
      >
        <el-form-item label="父类目">
          <el-input :model-value="parentCategoryName" disabled />
        </el-form-item>

        <el-form-item label="类目名称" prop="name">
          <el-input
            v-model="form.name"
            placeholder="请输入类目名称"
            :maxlength="50"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="排序权重" prop="sort">
          <el-input-number
            v-model="form.sort"
            :min="0"
            :max="9999"
            controls-position="right"
            class="w-full"
          />
        </el-form-item>

        <el-form-item v-if="isEdit" label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio value="active">启用</el-radio>
            <el-radio value="disabled">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 删除确认弹窗 -->
    <el-dialog
      v-model="deleteDialogVisible"
      title="删除类目"
      width="420px"
      :close-on-click-modal="false"
    >
      <div class="delete-confirm">
        <el-icon :size="24" color="var(--app-color-danger)"><WarningFilled /></el-icon>
        <div>
          <p class="delete-title">确定删除类目「{{ deleteTarget?.name }}」？</p>
          <p class="delete-desc">
            若该类目下有子类目，将同时被删除，此操作不可撤销。
          </p>
        </div>
      </div>
      <template #footer>
        <el-button @click="deleteDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="deleting" @click="handleDelete">
          确认删除
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { Plus, Loading, FolderOpened, WarningFilled } from '@element-plus/icons-vue';
import {
  getCategoryTree,
  createCategory,
  updateCategory,
  deleteCategory
} from '@/api/admin/category.js';

// ── 树配置 ──
const treeProps = {
  children: 'children',
  label: 'name'
};

// ── 状态 ──
const treeRef = ref(null);
const treeData = ref([]);
const loading = ref(true);

// ── 弹窗状态 ──
const dialogVisible = ref(false);
const isEdit = ref(false);
const editingNode = ref(null);
const parentNode = ref(null);
const submitting = ref(false);
const formRef = ref(null);

const form = reactive({
  name: '',
  sort: 0,
  status: 'active'
});

const rules = {
  name: [
    { required: true, message: '请输入类目名称', trigger: 'blur' },
    { max: 50, message: '不超过50个字符', trigger: 'blur' }
  ],
  sort: [
    { required: true, message: '请输入排序权重', trigger: 'blur' }
  ],
  status: [
    { required: true, message: '请选择状态', trigger: 'change' }
  ]
};

// ── 删除弹窗 ──
const deleteDialogVisible = ref(false);
const deleteTarget = ref(null);
const deleting = ref(false);

// ── 计算属性 ──
const parentCategoryName = computed(() => {
  if (isEdit.value && editingNode.value) {
    const parent = findParent(treeData.value, editingNode.value.id);
    return parent ? parent.name : '根类目';
  }
  if (parentNode.value) {
    return parentNode.value.name;
  }
  return '根类目';
});

// ── 工具函数 ──
function findParent(nodes, childId) {
  for (const node of nodes) {
    if (node.children && node.children.some(c => c.id === childId)) {
      return node;
    }
    if (node.children) {
      const found = findParent(node.children, childId);
      if (found) return found;
    }
  }
  return null;
}

// ── 数据加载 ──
async function fetchTree() {
  loading.value = true;
  try {
    const res = await getCategoryTree();
    treeData.value = res.data ?? [];
  } catch {
    ElMessage.error('加载类目数据失败');
  } finally {
    loading.value = false;
  }
}

// ── 新增 ──
function openAddDialog(parent) {
  isEdit.value = false;
  editingNode.value = null;
  parentNode.value = parent;
  form.name = '';
  form.sort = 0;
  form.status = 'active';
  dialogVisible.value = true;
}

// ── 编辑 ──
function openEditDialog(node) {
  isEdit.value = true;
  editingNode.value = node;
  parentNode.value = null;
  form.name = node.name;
  form.sort = node.sort;
  form.status = node.status;
  dialogVisible.value = true;
}

// ── 提交 ──
async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;

  submitting.value = true;
  try {
    if (isEdit.value) {
      await updateCategory(editingNode.value.id, {
        name: form.name,
        sort: form.sort,
        status: form.status
      });
      ElMessage.success('类目更新成功');
    } else {
      await createCategory({
        name: form.name,
        parentId: parentNode.value ? parentNode.value.id : 0,
        sort: form.sort
      });
      ElMessage.success('类目创建成功');
    }
    dialogVisible.value = false;
    await fetchTree();
  } catch {
    ElMessage.error(isEdit.value ? '更新失败' : '创建失败');
  } finally {
    submitting.value = false;
  }
}

// ── 删除 ──
function confirmDelete(node) {
  deleteTarget.value = node;
  deleteDialogVisible.value = true;
}

async function handleDelete() {
  if (!deleteTarget.value) return;
  deleting.value = true;
  try {
    await deleteCategory(deleteTarget.value.id);
    ElMessage.success('类目已删除');
    deleteDialogVisible.value = false;
    deleteTarget.value = null;
    await fetchTree();
  } catch {
    ElMessage.error('删除失败');
  } finally {
    deleting.value = false;
  }
}

// ── 生命周期 ──
onMounted(() => {
  fetchTree();
});
</script>

<style scoped>
.category-admin {
  max-width: 900px;
}

/* ── 页面头部 ── */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--app-space-xl);
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  margin: 0;
  font-size: var(--app-font-3xl);
  font-weight: 600;
  color: var(--app-text-primary);
}

.page-desc {
  margin: 0;
  font-size: var(--app-font-sm);
  color: var(--app-text-secondary);
}

/* ── 卡片 ── */
.tree-card {
  background: var(--app-bg-container);
  border: 1px solid var(--app-border-light);
  border-radius: var(--app-radius-md);
  min-height: 400px;
}

.tree-card :deep(.el-card__body) {
  padding: var(--app-space-xl);
}

/* ── 状态占位 ── */
.state-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  color: var(--app-text-secondary);
  gap: var(--app-space-sm);
}

.empty-state .empty-title {
  margin: var(--app-space-md) 0 0;
  font-size: var(--app-font-lg);
  font-weight: 500;
  color: var(--app-text-primary);
}

.empty-state .empty-desc {
  margin: 4px 0 0;
  font-size: var(--app-font-sm);
  color: var(--app-text-secondary);
}

/* ── 树节点 ── */
.tree-node {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: 1;
  padding: 4px 8px;
  border-radius: var(--app-radius-sm);
  transition: background var(--app-ease-standard) 0.15s;
}

.tree-node:hover {
  background: var(--app-bg-hover);
}

.node-info {
  display: flex;
  align-items: center;
  gap: var(--app-space-sm);
}

.node-name {
  font-size: var(--app-font-base);
  font-weight: 500;
  color: var(--app-text-primary);
}

.node-status {
  flex-shrink: 0;
}

.node-sort {
  font-size: var(--app-font-xs);
  color: var(--app-text-secondary);
  background: var(--app-bg-hover);
  padding: 1px 8px;
  border-radius: var(--app-radius-full);
}

.node-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  opacity: 0;
  transition: opacity var(--app-ease-standard) 0.15s;
}

.tree-node:hover .node-actions {
  opacity: 1;
}

/* ── el-tree 覆盖 ── */
:deep(.el-tree-node__content) {
  height: 44px;
  padding-right: 8px;
  border-radius: var(--app-radius-sm);
}

:deep(.el-tree-node__content:hover) {
  background: transparent;
}

:deep(.el-tree-node__expand-icon) {
  color: var(--app-text-secondary);
}

:deep(.el-tree-node.is-current > .el-tree-node__content) {
  background: var(--app-color-primary-lightest);
}

/* ── 删除确认弹窗 ── */
.delete-confirm {
  display: flex;
  gap: var(--app-space-base);
  align-items: flex-start;
}

.delete-title {
  margin: 0;
  font-size: var(--app-font-base);
  font-weight: 500;
  color: var(--app-text-primary);
}

.delete-desc {
  margin: 6px 0 0;
  font-size: var(--app-font-sm);
  color: var(--app-text-secondary);
  line-height: 1.5;
}

/* ── 通用 ── */
.w-full {
  width: 100%;
}
</style>
