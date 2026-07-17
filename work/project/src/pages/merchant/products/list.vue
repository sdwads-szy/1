<template>
  <div class="merchant-products-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="page-header-left">
        <el-button text @click="$router.push({name:'MerchantDashboard'})">← 返回看板</el-button>
        <h2 class="page-title">商品管理</h2>
      </div>
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        发布商品
      </el-button>
    </div>

    <!-- 筛选区卡片 -->
    <div class="filter-card">
      <div class="filter-left">
        <el-radio-group v-model="statusFilter" size="small" @change="handleStatusChange">
          <el-radio-button value="">全部</el-radio-button>
          <el-radio-button value="draft">草稿</el-radio-button>
          <el-radio-button value="listed">已上架</el-radio-button>
          <el-radio-button value="delisted">已下架</el-radio-button>
        </el-radio-group>
      </div>
      <div class="filter-right">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索商品名称..."
          clearable
          class="search-input"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
    </div>

    <!-- 商品表格 -->
    <el-table
      v-loading="loading"
      :data="productList"
      stripe
      class="product-table"
      row-key="id"
      @sort-change="handleSortChange"
    >
      <el-table-column label="商品图片" width="90" align="center">
        <template #default="{ row }">
          <el-image
            :src="row.defaultImage || '/img/public/placeholder/product.svg'"
            fit="cover"
            class="product-thumb"
            lazy
          >
            <template #error>
              <div class="image-error">
                <el-icon><PictureFilled /></el-icon>
              </div>
            </template>
          </el-image>
        </template>
      </el-table-column>

      <el-table-column label="商品名称" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="product-name">{{ row.name }}</span>
        </template>
      </el-table-column>

      <el-table-column label="最低价格" width="120" align="right">
        <template #default="{ row }">
          <span class="price-cell">&yen;{{ formatPrice(row.minPrice) }}</span>
        </template>
      </el-table-column>

      <el-table-column label="销量" width="100" align="right" sortable="custom" prop="sales">
        <template #default="{ row }">
          <span class="sales-cell">{{ row.sales ?? 0 }}</span>
        </template>
      </el-table-column>

      <el-table-column label="状态" width="110" align="center">
        <template #default="{ row }">
          <el-tag
            :type="statusTagType(row.status)"
            size="small"
            effect="plain"
          >
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="创建时间" width="170" align="center">
        <template #default="{ row }">
          <span class="time-cell">{{ row.createdAt || '-' }}</span>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="200" align="center" fixed="right">
        <template #default="{ row }">
          <div class="action-buttons">
            <el-button
              type="primary"
              link
              size="small"
              @click="handleEdit(row)"
            >
              编辑
            </el-button>
            <el-button
              v-if="row.status === 'draft' || row.status === 'delisted'"
              type="success"
              link
              size="small"
              @click="handleList(row)"
            >
              上架
            </el-button>
            <el-button
              v-if="row.status === 'listed'"
              type="warning"
              link
              size="small"
              @click="handleDelist(row)"
            >
              下架
            </el-button>
          </div>
        </template>
      </el-table-column>

      <!-- 空状态 -->
      <template #empty>
        <div class="empty-state">
          <el-empty
            :description="emptyDescription"
            :image-size="80"
          >
            <el-button v-if="statusFilter === '' && !searchKeyword" type="primary" @click="handleCreate">
              发布商品
            </el-button>
            <el-button v-else @click="clearFilters">
              清除筛选
            </el-button>
          </el-empty>
        </div>
      </template>
    </el-table>

    <!-- 分页 -->
    <div v-if="total > 0" class="pagination-wrapper">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handlePageSizeChange"
        @current-change="handlePageChange"
      />
    </div>

    <!-- 创建/编辑商品对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? '编辑商品' : '发布商品'"
      width="900px"
      :close-on-click-modal="false"
      destroy-on-close
      @closed="resetForm"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="90px"
        label-position="right"
      >
        <!-- 基础信息 -->
        <el-divider content-position="left">基础信息</el-divider>

        <el-form-item label="商品类目" prop="categoryId">
          <el-cascader
            v-model="form.categoryId"
            :options="categoryOptions"
            :props="{ value: 'id', label: 'name', emitPath: false, checkStrictly: true }"
            placeholder="请选择商品类目"
            clearable
            class="category-cascader"
          />
        </el-form-item>

        <el-form-item label="商品名称" prop="name">
          <el-input
            v-model="form.name"
            placeholder="请输入商品名称，最多128字"
            :maxlength="128"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="商品描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            placeholder="请输入商品描述（选填）"
            :rows="4"
            :maxlength="2000"
            show-word-limit
          />
        </el-form-item>

        <!-- 商品图片 -->
        <el-divider content-position="left">商品图片</el-divider>

        <el-form-item label="轮播图片">
          <el-upload
            v-model:file-list="imageFileList"
            :http-request="handleImageUpload"
            list-type="picture-card"
            :limit="8"
            multiple
            :on-exceed="handleImageExceed"
            :before-upload="beforeImageUpload"
            :on-remove="handleImageRemove"
            :on-preview="handleImagePreview"
          >
            <el-icon><Plus /></el-icon>
          </el-upload>
          <div class="upload-tip">支持 jpg/png/webp 格式，单张不超过5MB，最多8张</div>
        </el-form-item>

        <!-- SKU 规格 -->
        <el-divider content-position="left">
          <span>SKU 规格</span>
          <el-button type="primary" link size="small" @click="addSkuRow" style="margin-left: 12px;">
            <el-icon><Plus /></el-icon>
            添加规格
          </el-button>
        </el-divider>

        <el-form-item label="规格列表" prop="skus">
          <div class="sku-table-wrapper">
            <table class="sku-table">
              <thead>
                <tr>
                  <th class="col-spec">规格名称</th>
                  <th class="col-price">价格 (元)</th>
                  <th class="col-stock">库存</th>
                  <th class="col-image">规格图片</th>
                  <th class="col-action">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(sku, index) in form.skus" :key="index">
                  <td>
                    <el-input
                      v-model="sku.specName"
                      placeholder="如：暗夜黑 / L码"
                      size="small"
                      :maxlength="64"
                    />
                  </td>
                  <td>
                    <el-input-number
                      v-model="sku.price"
                      :min="0.01"
                      :precision="2"
                      :step="10"
                      size="small"
                      controls-position="right"
                      placeholder="0.00"
                    />
                  </td>
                  <td>
                    <el-input-number
                      v-model="sku.stock"
                      :min="0"
                      :step="10"
                      size="small"
                      controls-position="right"
                      placeholder="0"
                    />
                  </td>
                  <td>
                    <el-upload
                      :http-request="(opts) => handleSkuImageUpload(opts, index)"
                      :show-file-list="false"
                      accept="image/jpeg,image/png,image/webp"
                    >
                      <div class="sku-image-trigger" :class="{ 'has-image': sku.image }">
                        <template v-if="sku.image">
                          <img :src="sku.image" class="sku-thumb" />
                          <div class="sku-image-mask">
                            <el-icon><Edit /></el-icon>
                          </div>
                        </template>
                        <el-icon v-else><Plus /></el-icon>
                      </div>
                    </el-upload>
                  </td>
                  <td>
                    <el-button
                      type="danger"
                      link
                      size="small"
                      :disabled="form.skus.length <= 1"
                      @click="removeSkuRow(index)"
                    >
                      删除
                    </el-button>
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-if="form.skus.length === 0" class="sku-empty">
              暂无规格，请点击「添加规格」
            </div>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitLoading" @click="handleSubmit">
            {{ isEditing ? '保存修改' : '提交发布' }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 图片预览对话框 -->
    <el-dialog v-model="previewVisible" title="图片预览" width="600px" :close-on-click-modal="true">
      <img :src="previewUrl" class="preview-image" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, Search, PictureFilled, Edit } from '@element-plus/icons-vue';
import { getMerchantProducts, createMerchantProduct, updateMerchantProduct } from '@/api/merchant-products';
import { uploadFile } from '@/api/merchant-register';
import request from '@/utils/request';

// ── 状态 ──
const loading = ref(false);
const submitLoading = ref(false);
const productList = ref([]);
const total = ref(0);
const currentPage = ref(1);
const pageSize = ref(20);
const statusFilter = ref('');
const searchKeyword = ref('');
const sortProp = ref('');
const sortOrder = ref('');

// ── 对话框 ──
const dialogVisible = ref(false);
const isEditing = ref(false);
const editingId = ref(null);
const formRef = ref(null);
const previewVisible = ref(false);
const previewUrl = ref('');

// ── 表单 ──
const form = reactive({
  categoryId: null,
  name: '',
  description: '',
  skus: [],
});

const imageFileList = ref([]);

const formRules = {
  categoryId: [{ required: true, message: '请选择商品类目', trigger: 'change' }],
  name: [
    { required: true, message: '请输入商品名称', trigger: 'blur' },
    { min: 1, max: 128, message: '商品名称长度在1到128个字符', trigger: 'blur' },
  ],
  skus: [
    {
      validator: (_rule, value, callback) => {
        if (!value || value.length === 0) {
          callback(new Error('请至少添加一个规格'));
          return;
        }
        for (let i = 0; i < value.length; i++) {
          const sku = value[i];
          if (!sku.specName || !sku.specName.trim()) {
            callback(new Error(`第${i + 1}个规格名称不能为空`));
            return;
          }
          if (!sku.price || sku.price <= 0) {
            callback(new Error(`第${i + 1}个规格价格必须大于0`));
            return;
          }
          if (sku.stock === undefined || sku.stock === null || sku.stock < 0) {
            callback(new Error(`第${i + 1}个规格库存不能为空`));
            return;
          }
        }
        callback();
      },
      trigger: 'change',
    },
  ],
};

// ── 类目选项 ──
const categoryOptions = ref([]);

// ── 计算属性 ──
const emptyDescription = computed(() => {
  if (searchKeyword.value) return '未找到匹配商品，试试调整搜索条件';
  if (statusFilter.value) return `暂无${statusLabel(statusFilter.value)}商品`;
  return '还没有商品，发布您的第一个商品，开始销售吧';
});

// ── 方法 ──

/** 状态标签文本 */
function statusLabel(status) {
  const map = { draft: '草稿', listed: '已上架', delisted: '已下架' };
  return map[status] || status;
}

/** 状态标签类型 */
function statusTagType(status) {
  const map = { draft: 'info', listed: 'success', delisted: 'warning' };
  return map[status] || 'info';
}

/** 格式化价格 */
function formatPrice(price) {
  if (price === null || price === undefined) return '0.00';
  return Number(price).toFixed(2);
}

/** 加载商品列表 */
async function loadProducts() {
  loading.value = true;
  try {
    const params = { page: currentPage.value, pageSize: pageSize.value };
    if (statusFilter.value) params.status = statusFilter.value;
    if (searchKeyword.value) params.q = searchKeyword.value;
    const res = await getMerchantProducts(params);
    const data = res.data || res;
    productList.value = data.list || [];
    total.value = data.total || 0;
  } catch (e) {
    ElMessage.error('加载失败，网络连接异常，请检查网络后重试');
    productList.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

/** 加载类目树 */
async function loadCategories() {
  try {
    const res = await request({ url: '/categories', method: 'get' });
    const data = res.data || res;
    categoryOptions.value = Array.isArray(data) ? data : [];
  } catch {
    categoryOptions.value = [];
  }
}

/** 状态筛选变更 */
function handleStatusChange() {
  currentPage.value = 1;
  loadProducts();
}

/** 搜索 */
function handleSearch() {
  currentPage.value = 1;
  loadProducts();
}

/** 排序变更 */
function handleSortChange({ prop, order }) {
  sortProp.value = prop || '';
  sortOrder.value = order || '';
  currentPage.value = 1;
  loadProducts();
}

/** 分页变更 */
function handlePageChange(page) {
  currentPage.value = page;
  loadProducts();
}

function handlePageSizeChange(size) {
  pageSize.value = size;
  currentPage.value = 1;
  loadProducts();
}

/** 清除筛选 */
function clearFilters() {
  statusFilter.value = '';
  searchKeyword.value = '';
  currentPage.value = 1;
  loadProducts();
}

// ── 创建/编辑 ──

function handleCreate() {
  isEditing.value = false;
  editingId.value = null;
  resetForm();
  dialogVisible.value = true;
}

async function handleEdit(row) {
  isEditing.value = true;
  editingId.value = row.id;
  // 填充表单
  form.categoryId = row.categoryId || null;
  form.name = row.name || '';
  form.description = row.description || '';
  form.skus = (row.skus || []).map((s) => ({
    id: s.id || null,
    specName: s.specName || '',
    price: Number(s.price) || 0,
    stock: s.stock ?? 0,
    image: s.image || '',
  }));

  // 填充图片列表
  imageFileList.value = (row.images || []).map((url) => ({ name: url, url }));

  dialogVisible.value = true;
}

/** 重置表单 */
function resetForm() {
  form.categoryId = null;
  form.name = '';
  form.description = '';
  form.skus = [{ specName: '', price: 0, stock: 0, image: '' }];
  imageFileList.value = [];
  formRef.value?.resetFields();
}

/** 添加 SKU 行 */
function addSkuRow() {
  form.skus.push({ specName: '', price: 0, stock: 0, image: '' });
}

/** 删除 SKU 行 */
function removeSkuRow(index) {
  if (form.skus.length <= 1) return;
  form.skus.splice(index, 1);
}

// ── 图片上传 ──

async function handleImageUpload(options) {
  const fd = new FormData();
  fd.append('file', options.file);
  fd.append('type', 'img/product');
  try {
    const res = await uploadFile(fd);
    const data = res.data || res;
    const url = data.url || '';
    options.onSuccess({ url });
  } catch (e) {
    ElMessage.error('图片上传失败，请重试');
    options.onError(e);
  }
}

async function handleSkuImageUpload(options, skuIndex) {
  const fd = new FormData();
  fd.append('file', options.file);
  fd.append('type', 'img/sku');
  try {
    const res = await uploadFile(fd);
    const data = res.data || res;
    form.skus[skuIndex].image = data.url || '';
    options.onSuccess({ url: data.url });
  } catch (e) {
    ElMessage.error('图片上传失败，请重试');
    options.onError(e);
  }
}

function beforeImageUpload(file) {
  const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
  if (!validTypes.includes(file.type)) {
    ElMessage.error('仅支持 jpg/png/webp 格式');
    return false;
  }
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过 5MB');
    return false;
  }
  return true;
}

function handleImageExceed() {
  ElMessage.warning('最多上传8张图片');
}

function handleImageRemove(_file, fileList) {
  imageFileList.value = fileList;
}

function handleImagePreview(file) {
  previewUrl.value = file.url || (file.response && file.response.url);
  previewVisible.value = true;
}

// ── 提交 ──

async function handleSubmit() {
  if (!formRef.value) return;
  try {
    await formRef.value.validate();
  } catch {
    return;
  }

  // 构建图片 URL 数组
  const imageUrls = imageFileList.value
    .map((f) => f.url || (f.response && f.response.url) || f.name)
    .filter(Boolean);

  const payload = {
    categoryId: form.categoryId,
    name: form.name.trim(),
    description: form.description || '',
    skus: form.skus.map((s) => ({
      id: s.id || undefined,
      specName: s.specName.trim(),
      price: String(s.price),
      stock: s.stock,
      image: s.image || '',
    })),
    images: imageUrls,
  };

  submitLoading.value = true;
  try {
    if (isEditing.value) {
      payload.id = editingId.value;
      await updateMerchantProduct(payload);
      ElMessage.success('商品信息已保存');
    } else {
      const res = await createMerchantProduct(payload);
      const resData = res.data || res;
      if (resData.mockCode) {
        ElMessage.success({ message: '[模拟] 商品已创建，商品ID: ' + resData.productId, duration: 5000 });
      } else {
        ElMessage.success('商品已创建，状态为草稿');
      }
    }
    dialogVisible.value = false;
    loadProducts();
  } catch (e) {
    const msg = e?.response?.data?.message || e?.message || '提交失败，请修改后重试';
    ElMessage.error(msg);
  } finally {
    submitLoading.value = false;
  }
}

// ── 上架 / 下架 ──

async function handleList(row) {
  const newStatus = 'listed';
  const actionText = '上架';
  try {
    await ElMessageBox.confirm(
      `确定将「${row.name}」${actionText}？${actionText}后消费者可立即购买`,
      `${actionText}确认`,
      { type: 'info' }
    );
  } catch {
    return;
  }

  try {
    await updateMerchantProduct({ id: row.id, status: newStatus });
    ElMessage.success(`商品已${actionText}`);
    loadProducts();
  } catch (e) {
    const msg = e?.response?.data?.message || e?.message || `${actionText}失败，请重试`;
    ElMessage.error(msg);
  }
}

async function handleDelist(row) {
  const newStatus = 'delisted';
  const actionText = '下架';
  try {
    await ElMessageBox.confirm(
      `确定将「${row.name}」${actionText}？${actionText}后消费者将无法购买`,
      `${actionText}确认`,
      { type: 'warning' }
    );
  } catch {
    return;
  }

  try {
    await updateMerchantProduct({ id: row.id, status: newStatus });
    ElMessage.success(`商品已${actionText}`);
    loadProducts();
  } catch (e) {
    const msg = e?.response?.data?.message || e?.message || `${actionText}失败，请重试`;
    ElMessage.error(msg);
  }
}

// ── 生命周期 ──
onMounted(() => {
  loadProducts();
  loadCategories();
});
</script>

<style scoped>
.merchant-products-page {
  padding: 0;
}

/* ── 页面头部 ── */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-lg);
}

.page-title {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
}

/* ── 筛选卡片 ── */
.filter-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--color-bg-base);
  border: none;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: var(--space-md) var(--space-lg);
  margin-bottom: var(--space-lg);
}

.filter-left {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.filter-right {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.search-input {
  width: 260px;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: var(--radius-full);
}

/* ── 表格 ── */
.product-table {
  background: var(--color-bg-base);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.product-table :deep(.el-table__header th) {
  background: var(--color-bg-page);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: 600;
  padding: var(--space-xs) var(--space-sm);
}

.product-table :deep(.el-table__body td) {
  padding: var(--space-xs) var(--space-sm);
}

.product-table :deep(.el-table__body tr:hover > td) {
  background: var(--color-primary-50);
}

.product-table :deep(.el-table__body .el-table__row--striped) {
  background: rgba(0, 0, 0, 0.015);
}

.product-table :deep(.el-table__body .el-table__row--striped:hover > td) {
  background: var(--color-primary-50);
}

.product-thumb {
  width: 60px;
  height: 60px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  overflow: hidden;
}

.image-error {
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-page);
  color: var(--color-text-tertiary);
  font-size: 22px;
}

.product-name {
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  line-height: var(--line-height-normal);
}

.price-cell {
  font-family: var(--font-family);
  font-weight: 600;
  color: var(--color-error);
}

.sales-cell {
  color: var(--color-text-secondary);
}

.time-cell {
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

.action-buttons {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
}

/* ── 分页 ── */
.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-lg);
  padding: var(--space-sm) 0;
}

/* ── 空状态 ── */
.empty-state {
  padding: var(--space-3xl) 0;
}

/* ── 对话框 ── */
.category-cascader {
  width: 100%;
}

.upload-tip {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-top: var(--space-xs);
}

/* ── SKU 表格 ── */
.sku-table-wrapper {
  width: 100%;
  overflow-x: auto;
}

.sku-table {
  width: 100%;
  border-collapse: collapse;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.sku-table th,
.sku-table td {
  padding: var(--space-sm);
  text-align: left;
  border-bottom: 1px solid var(--color-border);
  vertical-align: middle;
}

.sku-table th {
  background: var(--color-bg-page);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: 600;
  white-space: nowrap;
}

.sku-table tbody tr:last-child td {
  border-bottom: none;
}

.sku-table tbody tr:hover td {
  background: var(--color-primary-50);
}

.col-spec { width: 28%; }
.col-price { width: 20%; }
.col-stock { width: 16%; }
.col-image { width: 20%; }
.col-action { width: 16%; }

.sku-empty {
  text-align: center;
  padding: var(--space-xl);
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

.sku-image-trigger {
  width: 48px;
  height: 48px;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-smooth);
  position: relative;
  overflow: hidden;
  background: var(--color-bg-page);
  color: var(--color-text-tertiary);
}

.sku-image-trigger:hover {
  border-color: var(--color-primary-500);
}

.sku-image-trigger.has-image {
  border-style: solid;
}

.sku-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.sku-image-mask {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-bg-base);
  opacity: 0;
  transition: opacity var(--duration-fast) var(--ease-smooth);
}

.sku-image-trigger:hover .sku-image-mask {
  opacity: 1;
}

/* ── 对话框底部 ── */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-sm);
}

/* ── 图片预览 ── */
.preview-image {
  width: 100%;
  height: auto;
  border-radius: var(--radius-sm);
}
</style>
