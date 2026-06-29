<template>
  <div class="onboarding-container">
    <div class="onboarding-card">
      <div class="onboarding-header">
        <h2 class="onboarding-title">资质上传</h2>
        <p class="onboarding-subtitle">请提交真实有效的资质信息，审核通过后即可开店</p>
      </div>

      <el-steps :active="2" align-center class="onboarding-steps">
        <el-step title="注册账号" description="已完成" />
        <el-step title="资质上传" description="当前步骤" />
        <el-step title="店铺信息" description="待完成" />
        <el-step title="等待审核" description="待审核" />
      </el-steps>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120px"
        label-position="right"
        class="onboarding-form"
      >
        <el-form-item label="营业执照" prop="businessLicense">
          <div class="upload-area">
            <el-upload
              ref="licenseUploadRef"
              :auto-upload="false"
              :limit="1"
              :on-change="(file) => handleFileChange(file, 'businessLicense')"
              :on-remove="() => handleFileRemove('businessLicense')"
              :file-list="licenseFileList"
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
                    <span class="el-upload-list__item-delete" @click="handleFileRemove('businessLicense')">
                      <el-icon><Delete /></el-icon>
                    </span>
                  </span>
                </div>
              </template>
            </el-upload>
            <p class="upload-tip">支持 jpg / png 格式，大小不超过 5MB</p>
          </div>
        </el-form-item>

        <el-form-item label="法人身份证" prop="legalPersonId">
          <div class="upload-area">
            <el-upload
              ref="idUploadRef"
              :auto-upload="false"
              :limit="1"
              :on-change="(file) => handleFileChange(file, 'legalPersonId')"
              :on-remove="() => handleFileRemove('legalPersonId')"
              :file-list="idFileList"
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
                    <span class="el-upload-list__item-delete" @click="handleFileRemove('legalPersonId')">
                      <el-icon><Delete /></el-icon>
                    </span>
                  </span>
                </div>
              </template>
            </el-upload>
            <p class="upload-tip">请上传身份证人像面，支持 jpg / png 格式</p>
          </div>
        </el-form-item>

        <el-form-item label="银行账户" prop="bankAccount">
          <el-input
            v-model="form.bankAccount"
            placeholder="请输入银行账号"
            maxlength="30"
            clearable
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="submitting"
            @click="handleSubmit"
            class="submit-btn"
          >
            提交审核
          </el-button>
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
 * 商家入驻 - 第二步：资质上传
 * 上传营业执照、法人身份证、银行账户信息
 */
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, ZoomIn, Delete } from '@element-plus/icons-vue'
import { submitQualification } from '@/api/merchant'

const router = useRouter()

const formRef = ref(null)
const submitting = ref(false)
const previewVisible = ref(false)
const previewUrl = ref('')

// 文件数据持有
const licenseFile = ref(null)
const legalPersonFile = ref(null)
const licenseFileList = ref([])
const idFileList = ref([])

const form = reactive({
  businessLicense: '',
  legalPersonId: '',
  bankAccount: ''
})

const rules = {
  businessLicense: [
    {
      required: true,
      message: '请上传营业执照',
      trigger: 'change',
      validator: (_rule, _value, callback) => {
        if (!licenseFile.value) {
          callback(new Error('请上传营业执照'))
        } else {
          callback()
        }
      }
    }
  ],
  legalPersonId: [
    {
      required: true,
      message: '请上传法人身份证',
      trigger: 'change',
      validator: (_rule, _value, callback) => {
        if (!legalPersonFile.value) {
          callback(new Error('请上传法人身份证'))
        } else {
          callback()
        }
      }
    }
  ],
  bankAccount: [
    { required: true, message: '请输入银行账户', trigger: 'blur' },
    { pattern: /^\d{10,30}$/, message: '银行账号格式不正确', trigger: 'blur' }
  ]
}

function handleFileChange(file, field) {
  const raw = file.raw
  if (!raw) return

  const isImage = raw.type.startsWith('image/')
  const isLt5M = raw.size / 1024 / 1024 < 5

  if (!isImage) {
    ElMessage.error('只能上传图片文件')
    return
  }
  if (!isLt5M) {
    ElMessage.error('图片大小不能超过 5MB')
    return
  }

  if (field === 'businessLicense') {
    licenseFile.value = raw
    licenseFileList.value = [file]
  } else if (field === 'legalPersonId') {
    legalPersonFile.value = raw
    idFileList.value = [file]
  }

  formRef.value?.validateField(field)
}

function handleFileRemove(field) {
  if (field === 'businessLicense') {
    licenseFile.value = null
    licenseFileList.value = []
  } else if (field === 'legalPersonId') {
    legalPersonFile.value = null
    idFileList.value = []
  }
}

function handlePreview(file) {
  previewUrl.value = file.url
  previewVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const fd = new FormData()
    fd.append('businessLicense', licenseFile.value)
    fd.append('legalPersonId', legalPersonFile.value)
    fd.append('bankAccount', form.bankAccount)

    const res = await submitQualification(fd)
    ElMessage.success('资质提交成功，请完善店铺信息')
    router.push({ name: 'MerchantShopEdit', state: { qualificationId: res.qualificationId } })
  } catch (err) {
    const msg = err?.response?.data?.message || err?.message || '提交失败，请稍后重试'
    ElMessage.error(msg)
  } finally {
    submitting.value = false
  }
}
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

.submit-btn {
  width: 100%;
  height: 44px;
  font-size: var(--app-font-lg, 1rem);
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
}
</style>
