<template>
  <div class="onboarding-container">
    <div class="onboarding-card">
      <div class="onboarding-header">
        <h2 class="onboarding-title">店铺信息</h2>
        <p class="onboarding-subtitle">完善您的店铺资料，让买家更好地了解您</p>
      </div>

      <el-steps :active="3" align-center class="onboarding-steps">
        <el-step title="注册账号" description="已完成" />
        <el-step title="资质上传" description="已提交" />
        <el-step title="店铺信息" description="当前步骤" />
        <el-step title="等待审核" description="待审核" />
      </el-steps>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
        label-position="right"
        class="onboarding-form"
      >
        <el-form-item label="店铺名称" prop="name">
          <el-input
            v-model="form.name"
            placeholder="请输入店铺名称"
            maxlength="50"
            show-word-limit
            clearable
          />
        </el-form-item>

        <el-form-item label="店铺Logo" prop="logo">
          <div class="upload-area">
            <el-upload
              ref="logoUploadRef"
              :auto-upload="false"
              :limit="1"
              :on-change="handleLogoChange"
              :on-remove="handleLogoRemove"
              :file-list="logoFileList"
              list-type="picture-card"
              accept="image/*"
            >
              <template #default>
                <el-icon><Plus /></el-icon>
              </template>
              <template #file="{ file }">
                <div>
                  <img :src="file.url" alt="" class="upload-preview" />
                  <span class="el-upload-list__item-actions">
                    <span class="el-upload-list__item-preview" @click="handlePreview(file)">
                      <el-icon><ZoomIn /></el-icon>
                    </span>
                    <span class="el-upload-list__item-delete" @click="handleLogoRemove">
                      <el-icon><Delete /></el-icon>
                    </span>
                  </span>
                </div>
              </template>
            </el-upload>
            <p class="upload-tip">建议尺寸 200×200px，支持 jpg / png，不超过 2MB</p>
          </div>
        </el-form-item>

        <el-form-item label="店铺简介" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            placeholder="请输入店铺简介，介绍您的经营范围和特色"
            :rows="4"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>

        <el-form-item>
          <div class="btn-group">
            <el-button @click="handleSkip" class="skip-btn">暂不填写，查看进度</el-button>
            <el-button
              type="primary"
              :loading="submitting"
              @click="handleSubmit"
              class="submit-btn"
            >
              保存并查看进度
            </el-button>
          </div>
        </el-form-item>
      </el-form>

      <!-- 图片预览弹窗 -->
      <el-dialog v-model="previewVisible" title="图片预览" width="520px" :close-on-click-modal="true">
        <img :src="previewUrl" alt="" style="width: 100%;" />
      </el-dialog>
    </div>
  </div>
</template>

<script setup>
/**
 * 商家入驻 - 第三步：店铺信息编辑
 * 加载已有店铺信息，支持编辑名称、Logo、简介
 */
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, ZoomIn, Delete } from '@element-plus/icons-vue'
import { getShopInfo, updateShop } from '@/api/merchant'

const router = useRouter()

const formRef = ref(null)
const submitting = ref(false)
const loading = ref(false)
const previewVisible = ref(false)
const previewUrl = ref('')

const logoFile = ref(null)
const logoFileList = ref([])
const existingLogoUrl = ref('')

const form = reactive({
  name: '',
  logo: '',
  description: ''
})

const rules = {
  name: [
    { required: true, message: '请输入店铺名称', trigger: 'blur' },
    { min: 2, max: 50, message: '店铺名称长度2-50个字符', trigger: 'blur' }
  ],
  description: [
    { max: 500, message: '店铺简介不超过500字', trigger: 'blur' }
  ]
}

function handleLogoChange(file) {
  const raw = file.raw
  if (!raw) return

  const isImage = raw.type.startsWith('image/')
  const isLt2M = raw.size / 1024 / 1024 < 2

  if (!isImage) {
    ElMessage.error('只能上传图片文件')
    return
  }
  if (!isLt2M) {
    ElMessage.error('图片大小不能超过 2MB')
    return
  }

  logoFile.value = raw
  logoFileList.value = [file]
}

function handleLogoRemove() {
  logoFile.value = null
  logoFileList.value = []
  existingLogoUrl.value = ''
}

function handlePreview(file) {
  previewUrl.value = file.url
  previewVisible.value = true
}

function handleSkip() {
  router.push({ name: 'MerchantProgress' })
}

async function fetchShopInfo() {
  loading.value = true
  try {
    const data = await getShopInfo()
    if (data) {
      form.name = data.name || ''
      form.description = data.description || ''
      existingLogoUrl.value = data.logo || ''
      if (existingLogoUrl.value) {
        logoFileList.value = [{
          name: '当前Logo',
          url: existingLogoUrl.value
        }]
      }
    }
  } catch (err) {
    const msg = err?.response?.data?.message || err?.message || '获取店铺信息失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const fd = new FormData()
    fd.append('name', form.name)
    fd.append('description', form.description || '')
    if (logoFile.value) {
      fd.append('logo', logoFile.value)
    }

    await updateShop(fd)
    ElMessage.success('店铺信息保存成功')
    router.push({ name: 'MerchantProgress' })
  } catch (err) {
    const msg = err?.response?.data?.message || err?.message || '保存失败，请稍后重试'
    ElMessage.error(msg)
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  fetchShopInfo()
})
</script>

<style scoped>
.onboarding-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a2332 0%, #1e3a5f 50%, #1a2332 100%);
  padding: var(--app-space-xl, 24px);
}

.onboarding-card {
  width: 100%;
  max-width: 560px;
  background: var(--app-bg-container, #ffffff);
  border-radius: var(--app-radius-lg, 16px);
  box-shadow: var(--app-shadow-level-3, 0 12px 32px rgba(0,0,0,0.12));
  padding: 40px 36px;
}

.onboarding-header {
  text-align: center;
  margin-bottom: 28px;
}

.onboarding-title {
  font-size: var(--app-font-3xl, 1.5rem);
  font-weight: 700;
  color: #1e3a5f;
  margin: 0 0 8px 0;
}

.onboarding-subtitle {
  font-size: var(--app-font-base, 0.875rem);
  color: var(--app-text-secondary, #6b7280);
  margin: 0;
}

.onboarding-steps {
  margin-bottom: 32px;
}

.onboarding-steps :deep(.el-step__title) {
  font-size: var(--app-font-xs, 0.75rem);
}

.onboarding-steps :deep(.el-step__description) {
  font-size: var(--app-font-xs, 0.75rem);
}

.onboarding-form {
  margin-top: 8px;
}

.upload-area {
  width: 100%;
}

.upload-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.upload-tip {
  font-size: var(--app-font-xs, 0.75rem);
  color: var(--app-text-secondary, #6b7280);
  margin: 6px 0 0 0;
}

.btn-group {
  display: flex;
  gap: var(--app-space-md, 12px);
  width: 100%;
}

.skip-btn {
  flex: 1;
  height: 44px;
  border-radius: var(--app-radius-base, 8px);
}

.submit-btn {
  flex: 1;
  height: 44px;
  font-size: var(--app-font-base, 0.875rem);
  font-weight: 600;
  background: #1e3a5f;
  border-color: #1e3a5f;
  border-radius: var(--app-radius-base, 8px);
  transition: all 0.15s var(--app-ease-standard, cubic-bezier(0.4,0,0.2,1));
}

.submit-btn:hover {
  background: #2c5282;
  border-color: #2c5282;
}

.submit-btn:active {
  background: #162d4a;
  border-color: #162d4a;
}

@media (max-width: 576px) {
  .onboarding-card {
    padding: 28px 20px;
  }
  .btn-group {
    flex-direction: column;
  }
}
</style>
