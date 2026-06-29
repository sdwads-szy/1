<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <el-button link class="back-btn" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <h1 class="page-title">{{ isEdit ? '编辑商品' : '发布商品' }}</h1>
      </div>
      <div class="header-actions">
        <el-button @click="handleSaveDraft" :loading="saving">保存草稿</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="saving">
          {{ isEdit ? '保存修改' : '提交审核' }}
        </el-button>
      </div>
    </div>

    <div class="form-layout">
      <!-- 商品基本信息 -->
      <div class="form-card">
        <div class="card-header">
          <h2 class="card-title">基本信息</h2>
          <span class="card-subtitle">商品的基础信息，标题为必填项</span>
        </div>
        <el-form
          ref="productFormRef"
          :model="productForm"
          :rules="productRules"
          label-width="110px"
          label-position="right"
          class="product-form"
        >
          <el-form-item label="商品标题" prop="title">
            <el-input
              v-model="productForm.title"
              placeholder="请输入商品标题，最多200字"
              maxlength="200"
              show-word-limit
              size="large"
            />
          </el-form-item>

          <el-form-item label="所属类目" prop="category_id">
            <el-select
              v-model="productForm.category_id"
              placeholder="请选择商品类目"
              size="large"
              class="full-width"
            >
              <el-option label="加载中..." value="" disabled v-if="categories.length === 0" />
              <el-option
                v-for="cat in categories"
                :key="cat.id"
                :label="cat.name"
                :value="cat.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="商品描述" prop="description">
            <el-input
              v-model="productForm.description"
              type="textarea"
              placeholder="请输入商品描述，支持富文本"
              :rows="5"
              maxlength="5000"
              show-word-limit
            />
          </el-form-item>

          <el-form-item label="商品主图" prop="main_image">
            <div class="image-upload-area">
              <el-input
                v-model="productForm.main_image"
                placeholder="请输入商品主图URL"
                size="large"
                class="image-url-input"
              />
              <div class="image-preview" v-if="productForm.main_image">
                <el-image
                  :src="productForm.main_image"
                  fit="cover"
                  class="preview-img"
                  :preview-teleported="true"
                />
              </div>
            </div>
          </el-form-item>
        </el-form>
      </div>

      <!-- SKU 规格管理 -->
      <div class="form-card">
        <div class="card-header">
          <div>
            <h2 class="card-title">SKU 规格</h2>
            <span class="card-subtitle">定义商品的价格、库存及规格组合</span>
          </div>
          <el-button type="primary" plain size="default" @click="addSku">
            <el-icon><Plus /></el-icon>
            添加 SKU
          </el-button>
        </div>

        <div v-if="skuList.length === 0" class="sku-empty">
          <el-icon class="empty-icon"><Box /></el-icon>
          <span>暂未添加 SKU，请点击上方按钮添加</span>
        </div>

        <div v-else class="sku-list">
          <div
            v-for="(sku, index) in skuList"
            :key="index"
            class="sku-card"
          >
            <div class="sku-card-header">
              <span class="sku-index">SKU #{{ index + 1 }}</span>
              <el-button type="danger" link size="small" @click="removeSku(index)">
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </div>

            <div class="sku-card-body">
              <!-- 规格键值对 -->
              <div class="spec-editor">
                <div class="spec-label">规格组合</div>
                <div class="spec-kv-list">
                  <div
                    v-for="(spec, si) in sku.specs"
                    :key="si"
                    class="spec-kv-row"
                  >
                    <el-input
                      v-model="spec.key"
                      placeholder="规格名（如颜色）"
                      size="default"
                      class="spec-key-input"
                    />
                    <span class="spec-sep">:</span>
                    <el-input
                      v-model="spec.value"
                      placeholder="规格值（如红色）"
                      size="default"
                      class="spec-val-input"
                    />
                    <el-button
                      v-if="sku.specs.length > 1"
                      type="danger"
                      link
                      size="small"
                      @click="removeSpec(index, si)"
                    >
                      <el-icon><Close /></el-icon>
                    </el-button>
                  </div>
                </div>
                <el-button type="primary" link size="small" @click="addSpec(index)">
                  <el-icon><Plus /></el-icon>
                  添加规格
                </el-button>
              </div>

              <!-- 价格 / 库存 / 图片 -->
              <div class="sku-fields">
                <div class="sku-field">
                  <label class="field-label">
                    价格 <span class="required-star">*</span>
                  </label>
                  <el-input
                    v-model="sku.price"
                    placeholder="0.00"
                    size="default"
                    class="field-input"
                  >
                    <template #prefix>¥</template>
                  </el-input>
                </div>

                <div class="sku-field">
                  <label class="field-label">
                    库存 <span class="required-star">*</span>
                  </label>
                  <el-input-number
                    v-model="sku.stock"
                    :min="0"
                    :max="99999"
                    placeholder="0"
                    size="default"
                    class="field-input"
                    controls-position="right"
                  />
                </div>

                <div class="sku-field sku-field-image">
                  <label class="field-label">SKU 图片</label>
                  <el-input
                    v-model="sku.image"
                    placeholder="图片URL（选填）"
                    size="default"
                    class="field-input"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { ArrowLeft, Plus, Delete, Close, Box, Picture } from '@element-plus/icons-vue';
import { createProduct, updateProduct, getProduct } from '@/api/merchant.js';

const router = useRouter();
const route = useRoute();

/* ===== 编辑模式判断 ===== */
const productId = computed(() => route.query.productId);
const isEdit = computed(() => !!productId.value);

/* ===== 表单 ===== */
const productFormRef = ref(null);
const saving = ref(false);

const productForm = reactive({
  title: '',
  category_id: '',
  description: '',
  main_image: '',
});

const productRules = {
  title: [
    { required: true, message: '请输入商品标题', trigger: 'blur' },
    { max: 200, message: '标题不超过200字', trigger: 'blur' },
  ],
  category_id: [
    { required: true, message: '请选择商品类目', trigger: 'change' },
  ],
};

/* ===== 类目（预留，实际需从 API 获取） ===== */
const categories = ref([]);

/* ===== SKU 列表 ===== */
const skuList = ref([]);

function createEmptySku() {
  return {
    specs: [{ key: '', value: '' }],
    price: '',
    stock: 0,
    image: '',
  };
}

function addSku() {
  skuList.value.push(createEmptySku());
}

function removeSku(index) {
  skuList.value.splice(index, 1);
}

function addSpec(skuIndex) {
  skuList.value[skuIndex].specs.push({ key: '', value: '' });
}

function removeSpec(skuIndex, specIndex) {
  skuList.value[skuIndex].specs.splice(specIndex, 1);
}

/* ===== 构建 SKU 提交数据 ===== */
function buildSkusPayload() {
  return skuList.value
    .filter((sku) => {
      const hasSpec = sku.specs.some((s) => s.key.trim() && s.value.trim());
      return hasSpec && sku.price !== '' && sku.price !== null;
    })
    .map((sku) => {
      const specObj = {};
      sku.specs.forEach((s) => {
        if (s.key.trim() && s.value.trim()) {
          specObj[s.key.trim()] = s.value.trim();
        }
      });
      return {
        spec_combo: JSON.stringify(specObj),
        price: Number(sku.price),
        stock: Number(sku.stock) || 0,
        image: sku.image || '',
      };
    });
}

/* ===== 提交 ===== */
async function handleSubmit() {
  if (!productFormRef.value) return;
  try {
    await productFormRef.value.validate();
  } catch {
    ElMessage.warning('请填写必填项');
    return;
  }

  const skus = buildSkusPayload();
  if (skus.length === 0) {
    ElMessage.warning('请至少添加一个完整的 SKU（含规格名/值、价格）');
    return;
  }

  saving.value = true;
  try {
    const payload = {
      categoryId: productForm.category_id,
      title: productForm.title,
      description: productForm.description,
      mainImage: productForm.main_image,
      skus,
    };

    if (isEdit.value) {
      await updateProduct(productId.value, payload);
      ElMessage.success('商品已更新，请重新提交审核');
    } else {
      await createProduct(payload);
      ElMessage.success('商品已发布，等待平台审核');
    }
    router.push({ name: 'MerchantProductList' });
  } catch (err) {
    ElMessage.error(isEdit.value ? '更新失败，请重试' : '发布失败，请重试');
  } finally {
    saving.value = false;
  }
}

async function handleSaveDraft() {
  saving.value = true;
  try {
    const payload = {
      categoryId: productForm.category_id,
      title: productForm.title || '未命名商品',
      description: productForm.description,
      mainImage: productForm.main_image,
      skus: buildSkusPayload(),
      status: 'draft',
    };

    if (isEdit.value) {
      await updateProduct(productId.value, payload);
    } else {
      await createProduct(payload);
    }
    ElMessage.success('草稿已保存');
    router.push({ name: 'MerchantProductList' });
  } catch (err) {
    ElMessage.error('保存草稿失败');
  } finally {
    saving.value = false;
  }
}

/* ===== 加载编辑数据 ===== */
async function loadProduct() {
  if (!productId.value) return;
  try {
    const res = await getProduct(productId.value);
    const data = res.data || res;
    const p = data.product || data;

    productForm.title = p.title || '';
    productForm.category_id = p.category_id || '';
    productForm.description = p.description || '';
    productForm.main_image = p.main_image || '';

    if (data.skus && data.skus.length > 0) {
      skuList.value = data.skus.map((s) => {
        let specs = [{ key: '', value: '' }];
        try {
          const obj = typeof s.spec_combo === 'string' ? JSON.parse(s.spec_combo) : s.spec_combo;
          const entries = Object.entries(obj || {});
          if (entries.length > 0) {
            specs = entries.map(([k, v]) => ({ key: k, value: v }));
          }
        } catch {
          specs = [{ key: '', value: '' }];
        }
        return {
          specs,
          price: s.price !== undefined ? String(s.price) : '',
          stock: s.stock || 0,
          image: s.image || '',
        };
      });
    }
  } catch (err) {
    ElMessage.error('加载商品信息失败');
  }
}

/* ===== 导航 ===== */
function goBack() {
  router.push({ name: 'MerchantProductList' });
}

/* ===== 生命周期 ===== */
onMounted(() => {
  loadProduct();
});
</script>

<style scoped>
.page-container {
  padding: var(--app-space-xl, 24px);
  min-height: 100%;
  background: var(--app-bg-page, #f0f2f5);
}

/* ——— 页面头部 ——— */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--app-space-lg, 20px) var(--app-space-xl, 24px);
  background: linear-gradient(135deg, #1a2332 0%, #1e2d3d 100%);
  border-radius: var(--app-radius-md, 12px);
  margin-bottom: var(--app-space-lg, 20px);
  color: #fff;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--app-space-sm, 8px);
}

.back-btn {
  color: rgba(255, 255, 255, 0.8);
  font-size: 1.25rem;
  padding: 4px;
}

.back-btn:hover {
  color: #fff;
}

.page-title {
  font-size: var(--app-font-2xl, 1.25rem);
  font-weight: 700;
  color: #fff;
  margin: 0;
  letter-spacing: 0.5px;
}

.header-actions {
  display: flex;
  gap: var(--app-space-sm, 8px);
}

.header-actions :deep(.el-button--primary) {
  background: #3b82f6;
  border-color: #3b82f6;
  font-weight: 600;
}

/* ——— 表单布局 ——— */
.form-layout {
  display: flex;
  flex-direction: column;
  gap: var(--app-space-lg, 20px);
  max-width: 900px;
}

.form-card {
  background: var(--app-bg-container, #fff);
  border-radius: var(--app-radius-base, 8px);
  padding: var(--app-space-xl, 24px);
  box-shadow: var(--app-shadow-level-1, 0 1px 3px rgba(0,0,0,0.06));
}

.card-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: var(--app-space-xl, 24px);
  padding-bottom: var(--app-space-base, 16px);
  border-bottom: 1px solid var(--app-border-light, #e5e7eb);
}

.card-title {
  font-size: var(--app-font-lg, 1rem);
  font-weight: 600;
  color: var(--app-text-primary, #1a1a2e);
  margin: 0;
}

.card-subtitle {
  font-size: var(--app-font-xs, 0.75rem);
  color: var(--app-text-secondary, #6b7280);
  margin-left: var(--app-space-sm, 8px);
}

.product-form {
  max-width: 640px;
}

.full-width {
  width: 100%;
}

/* 图片上传 */
.image-upload-area {
  display: flex;
  gap: var(--app-space-md, 12px);
  align-items: flex-start;
  width: 100%;
}

.image-url-input {
  flex: 1;
}

.image-preview {
  flex-shrink: 0;
}

.preview-img {
  width: 120px;
  height: 120px;
  border-radius: var(--app-radius-sm, 4px);
  border: 1px solid var(--app-border-light, #e5e7eb);
}

/* ——— SKU 区域 ——— */
.sku-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 0;
  color: var(--app-text-secondary, #6b7280);
  font-size: var(--app-font-base, 0.875rem);
  gap: var(--app-space-sm, 8px);
}

.empty-icon {
  font-size: 2.5rem;
  color: #d1d5db;
}

.sku-list {
  display: flex;
  flex-direction: column;
  gap: var(--app-space-base, 16px);
}

.sku-card {
  border: 1px solid var(--app-border-light, #e5e7eb);
  border-radius: var(--app-radius-base, 8px);
  overflow: hidden;
  transition: box-shadow 0.2s var(--app-ease-standard, ease);
}

.sku-card:hover {
  box-shadow: var(--app-shadow-level-1, 0 1px 3px rgba(0,0,0,0.06));
}

.sku-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px var(--app-space-base, 16px);
  background: #f8f9fb;
  border-bottom: 1px solid var(--app-border-light, #e5e7eb);
}

.sku-index {
  font-size: var(--app-font-sm, 0.8125rem);
  font-weight: 600;
  color: #374151;
}

.sku-card-body {
  padding: var(--app-space-base, 16px);
}

/* 规格编辑器 */
.spec-editor {
  margin-bottom: var(--app-space-md, 12px);
}

.spec-label {
  font-size: var(--app-font-sm, 0.8125rem);
  font-weight: 500;
  color: #374151;
  margin-bottom: var(--app-space-sm, 8px);
}

.spec-kv-list {
  display: flex;
  flex-direction: column;
  gap: var(--app-space-sm, 8px);
  margin-bottom: var(--app-space-sm, 8px);
}

.spec-kv-row {
  display: flex;
  align-items: center;
  gap: var(--app-space-sm, 8px);
}

.spec-key-input {
  width: 140px;
}

.spec-val-input {
  width: 160px;
}

.spec-sep {
  color: var(--app-text-secondary, #6b7280);
  font-weight: 600;
}

/* SKU 字段 */
.sku-fields {
  display: flex;
  gap: var(--app-space-base, 16px);
  flex-wrap: wrap;
}

.sku-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 180px;
}

.sku-field-image {
  flex: 1;
  min-width: 200px;
}

.field-label {
  font-size: var(--app-font-sm, 0.8125rem);
  font-weight: 500;
  color: #374151;
}

.required-star {
  color: #ef4444;
}

.field-input {
  width: 100%;
}
</style>
