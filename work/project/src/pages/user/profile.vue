<template>
  <div class="profile-page">
    <!-- 左侧导航 (桌面端) -->
    <aside class="profile-sidebar">
      <div class="sidebar-user-brief">
        <el-avatar :size="48" :src="assetUrl(profile.avatar)" />
        <span class="sidebar-nickname">{{ profile.nickname || '用户' }}</span>
      </div>
      <nav class="sidebar-nav">
        <div
          v-for="item in navItems"
          :key="item.key"
          class="nav-item"
          :class="{ active: activeSection === item.key }"
          @click="activeSection = item.key"
        >
          <el-icon v-if="item.icon" class="nav-icon"><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </div>
        <div class="nav-item logout-item" @click="handleLogout">
          <span>退出登录</span>
        </div>
      </nav>
    </aside>

    <!-- 右侧内容区 -->
    <main class="profile-content">
      <!-- ========== 个人资料 ========== -->
      <section v-if="activeSection === 'profile'" class="content-section">
        <h2 class="section-title">个人资料</h2>
        <div class="profile-card">
          <div class="profile-avatar-row">
            <el-avatar :size="72" :src="assetUrl(profile.avatar)" />
            <div class="profile-avatar-info">
              <span class="profile-role-tag">
                <el-tag :type="roleTagType" size="small">{{ roleLabel }}</el-tag>
              </span>
            </div>
          </div>
          <el-divider />
          <div class="profile-info-grid">
            <div class="info-item">
              <label>昵称</label>
              <span>{{ profile.nickname || '-' }}</span>
            </div>
            <div class="info-item">
              <label>手机号</label>
              <span>{{ profile.mobile || '-' }}</span>
            </div>
            <div class="info-item">
              <label>用户ID</label>
              <span>{{ profile.userId || '-' }}</span>
            </div>
            <div class="info-item">
              <label>角色</label>
              <span>{{ roleLabel }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- ========== 收货地址 ========== -->
      <section v-if="activeSection === 'addresses'" class="content-section">
        <div class="section-header">
          <h2 class="section-title">收货地址</h2>
          <el-button type="primary" @click="openAddressDialog(null)">
            <el-icon><Plus /></el-icon>
            添加新地址
          </el-button>
        </div>

        <!-- 地址列表 -->
        <div v-if="addresses.length > 0" class="address-list">
          <div
            v-for="addr in addresses"
            :key="addr.id"
            class="address-card"
            :class="{ 'is-default': addr.isDefault }"
          >
            <div class="address-card-header">
              <span class="address-contact">
                <strong>{{ addr.contactName }}</strong>
                <span class="address-phone">{{ addr.phone }}</span>
              </span>
              <el-tag v-if="addr.isDefault" type="primary" size="small" effect="plain">默认</el-tag>
            </div>
            <div class="address-card-body">
              {{ addr.province }}{{ addr.city }}{{ addr.district }} {{ addr.detail }}
            </div>
            <div class="address-card-actions">
              <el-button text type="primary" size="small" @click="openAddressDialog(addr)">编辑</el-button>
              <el-button
                v-if="!addr.isDefault"
                text
                type="danger"
                size="small"
                @click="handleDeleteAddress(addr.id)"
              >
                删除
              </el-button>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-else class="empty-state">
          <div class="empty-icon">
            <svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M32 12C22.059 12 14 20.059 14 30C14 34.714 15.897 38.988 18.95 42.15L20 43.2V50C20 51.105 20.895 52 22 52H42C43.105 52 44 51.105 44 50V43.2L45.05 42.15C48.103 38.988 50 34.714 50 30C50 20.059 41.941 12 32 12Z" stroke="currentColor" stroke-width="2" fill="none"/>
              <circle cx="32" cy="32" r="3" fill="currentColor"/>
              <path d="M32 38V42" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </div>
          <p class="empty-title">还没有收货地址</p>
          <p class="empty-desc">添加一个常用地址，下单更方便</p>
          <el-button type="primary" @click="openAddressDialog(null)">添加新地址</el-button>
        </div>
      </section>

      <!-- ========== 安全设置 ========== -->
      <section v-if="activeSection === 'security'" class="content-section">
        <h2 class="section-title">安全设置</h2>
        <div class="security-card">
          <div class="security-empty">
            <div class="empty-icon">
              <svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M32 8L8 18V30C8 44.568 18.212 54.784 32 58C45.788 54.784 56 44.568 56 30V18L32 8Z" stroke="currentColor" stroke-width="2" fill="none"/>
                <path d="M24 32L30 38L40 26" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <p class="empty-title">安全设置</p>
            <p class="empty-desc">设置密保问题，让账户更安全</p>
          </div>
        </div>
      </section>
    </main>

    <!-- ========== 地址编辑对话框 ========== -->
    <el-dialog
      v-model="addressDialogVisible"
      :title="editingAddress ? '编辑地址' : '新增地址'"
      width="520px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form
        ref="addressFormRef"
        :model="addressForm"
        :rules="addressRules"
        label-width="80px"
        label-position="left"
      >
        <el-form-item label="收货人" prop="contactName">
          <el-input v-model="addressForm.contactName" placeholder="请输入收货人姓名" maxlength="32" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="addressForm.phone" placeholder="请输入收货人手机号" maxlength="11" />
        </el-form-item>
        <el-form-item label="所在地区" prop="region">
          <el-cascader
            v-model="addressForm.region"
            :options="regionOptions"
            placeholder="请选择省/市/区"
            style="width: 100%"
            clearable
          />
        </el-form-item>
        <el-form-item label="详细地址" prop="detail">
          <el-input
            v-model="addressForm.detail"
            type="textarea"
            placeholder="街道、门牌号等"
            maxlength="255"
            :rows="2"
          />
        </el-form-item>
        <el-form-item label="默认地址">
          <el-switch v-model="addressForm.isDefault" active-text="设为默认收货地址" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addressDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="addressSubmitting" @click="handleAddressSubmit">
          {{ editingAddress ? '保存修改' : '添加地址' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus } from '@element-plus/icons-vue';
import { useUserStore } from '@/stores/user';
import { getUserProfile, getAddresses, createAddress, updateAddress, deleteAddress } from '@/api/user';

const router = useRouter();
const userStore = useUserStore();

// ── 侧边导航 ──
const navItems = [
  { key: 'profile', label: '个人资料' },
  { key: 'addresses', label: '收货地址' },
  { key: 'orders', label: '我的订单' },
  { key: 'security', label: '安全设置' }
];

const activeSection = ref('profile');

// ── 用户信息 ──
const profile = reactive({
  userId: null,
  mobile: '',
  nickname: '',
  avatar: '',
  role: ''
});

const roleLabel = computed(() => {
  const map = { user: '买家', merchant: '商家', admin: '管理员' };
  return map[profile.role] || profile.role || '-';
});

const roleTagType = computed(() => {
  const map = { user: '', merchant: 'warning', admin: 'danger' };
  return map[profile.role] || '';
});

async function fetchProfile() {
  try {
    const res = await getUserProfile();
    if (res.data) {
      Object.assign(profile, res.data);
    }
  } catch {
    ElMessage.error('获取用户信息失败');
  }
}

// ── 地址管理 ──
const addresses = ref([]);
const addressDialogVisible = ref(false);
const addressSubmitting = ref(false);
const editingAddress = ref(null);
const addressFormRef = ref(null);

const addressForm = reactive({
  region: [],
  detail: '',
  phone: '',
  contactName: '',
  isDefault: false
});

const addressRules = {
  contactName: [
    { required: true, message: '请输入收货人姓名', trigger: 'blur' },
    { min: 1, max: 32, message: '姓名长度1-32个字符', trigger: 'blur' }
  ],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确', trigger: 'blur' }
  ],
  region: [
    { required: true, message: '请选择所在地区', trigger: 'change' }
  ],
  detail: [
    { required: true, message: '请输入详细地址', trigger: 'blur' },
    { min: 1, max: 255, message: '详细地址长度1-255个字符', trigger: 'blur' }
  ]
};

async function fetchAddresses() {
  try {
    const res = await getAddresses();
    if (res.data && res.data.list) {
      addresses.value = res.data.list;
    }
  } catch {
    ElMessage.error('获取地址列表失败');
  }
}

function openAddressDialog(addr) {
  if (addr) {
    editingAddress.value = addr;
    addressForm.region = [addr.province, addr.city, addr.district];
    addressForm.detail = addr.detail;
    addressForm.phone = addr.phone;
    addressForm.contactName = addr.contactName;
    addressForm.isDefault = !!addr.isDefault;
  } else {
    editingAddress.value = null;
    addressForm.region = [];
    addressForm.detail = '';
    addressForm.phone = '';
    addressForm.contactName = '';
    addressForm.isDefault = false;
  }
  addressDialogVisible.value = true;
}

async function handleAddressSubmit() {
  const valid = await addressFormRef.value.validate().catch(() => false);
  if (!valid) return;

  addressSubmitting.value = true;
  try {
    const [province, city, district] = addressForm.region;
    const payload = {
      province,
      city,
      district,
      detail: addressForm.detail,
      phone: addressForm.phone,
      contactName: addressForm.contactName,
      isDefault: addressForm.isDefault
    };

    if (editingAddress.value) {
      await updateAddress(editingAddress.value.id, payload);
      ElMessage.success('地址已更新');
    } else {
      await createAddress(payload);
      ElMessage.success('地址已添加');
    }
    addressDialogVisible.value = false;
    await fetchAddresses();
  } catch (err) {
    const msg = err?.response?.data?.message || '操作失败，请重试';
    ElMessage.error(msg);
  } finally {
    addressSubmitting.value = false;
  }
}

async function handleDeleteAddress(id) {
  try {
    await ElMessageBox.confirm('确定要删除该地址吗？', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    });
    await deleteAddress(id);
    ElMessage.success('地址已删除');
    await fetchAddresses();
  } catch (err) {
    if (err !== 'cancel' && err !== 'close') {
      const msg = err?.response?.data?.message || '删除失败';
      ElMessage.error(msg);
    }
  }
}

// ── 退出登录 ──
async function handleLogout() {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '退出确认', {
      confirmButtonText: '退出',
      cancelButtonText: '取消',
      type: 'warning'
    });
    userStore.logout();
    router.push({ name: 'AuthLogin' });
    ElMessage.success('已退出登录');
  } catch {
    // 取消操作
  }
}

// ── 图片路径拼接 ──
const FILE_BASE_URL = import.meta.env.VITE_FILE_BASE_URL || '';
function assetUrl(path) {
  if (!path) return '';
  if (path.startsWith('http')) return path;
  return FILE_BASE_URL + path;
}

// ── 省市区数据 (Cascader) ──
const regionOptions = [
  { value: '北京市', label: '北京市', children: [
    { value: '北京市', label: '北京市', children: [
      { value: '东城区', label: '东城区' }, { value: '西城区', label: '西城区' },
      { value: '朝阳区', label: '朝阳区' }, { value: '丰台区', label: '丰台区' },
      { value: '石景山区', label: '石景山区' }, { value: '海淀区', label: '海淀区' },
      { value: '门头沟区', label: '门头沟区' }, { value: '房山区', label: '房山区' },
      { value: '通州区', label: '通州区' }, { value: '顺义区', label: '顺义区' },
      { value: '昌平区', label: '昌平区' }, { value: '大兴区', label: '大兴区' },
      { value: '怀柔区', label: '怀柔区' }, { value: '平谷区', label: '平谷区' },
      { value: '密云区', label: '密云区' }, { value: '延庆区', label: '延庆区' }
    ]}
  ]},
  { value: '天津市', label: '天津市', children: [
    { value: '天津市', label: '天津市', children: [
      { value: '和平区', label: '和平区' }, { value: '河东区', label: '河东区' },
      { value: '河西区', label: '河西区' }, { value: '南开区', label: '南开区' },
      { value: '河北区', label: '河北区' }, { value: '红桥区', label: '红桥区' },
      { value: '东丽区', label: '东丽区' }, { value: '西青区', label: '西青区' },
      { value: '津南区', label: '津南区' }, { value: '北辰区', label: '北辰区' },
      { value: '武清区', label: '武清区' }, { value: '宝坻区', label: '宝坻区' },
      { value: '滨海新区', label: '滨海新区' }, { value: '宁河区', label: '宁河区' },
      { value: '静海区', label: '静海区' }, { value: '蓟州区', label: '蓟州区' }
    ]}
  ]},
  { value: '上海市', label: '上海市', children: [
    { value: '上海市', label: '上海市', children: [
      { value: '黄浦区', label: '黄浦区' }, { value: '徐汇区', label: '徐汇区' },
      { value: '长宁区', label: '长宁区' }, { value: '静安区', label: '静安区' },
      { value: '普陀区', label: '普陀区' }, { value: '虹口区', label: '虹口区' },
      { value: '杨浦区', label: '杨浦区' }, { value: '闵行区', label: '闵行区' },
      { value: '宝山区', label: '宝山区' }, { value: '嘉定区', label: '嘉定区' },
      { value: '浦东新区', label: '浦东新区' }, { value: '金山区', label: '金山区' },
      { value: '松江区', label: '松江区' }, { value: '青浦区', label: '青浦区' },
      { value: '奉贤区', label: '奉贤区' }, { value: '崇明区', label: '崇明区' }
    ]}
  ]},
  { value: '重庆市', label: '重庆市', children: [
    { value: '重庆市', label: '重庆市', children: [
      { value: '万州区', label: '万州区' }, { value: '涪陵区', label: '涪陵区' },
      { value: '渝中区', label: '渝中区' }, { value: '大渡口区', label: '大渡口区' },
      { value: '江北区', label: '江北区' }, { value: '沙坪坝区', label: '沙坪坝区' },
      { value: '九龙坡区', label: '九龙坡区' }, { value: '南岸区', label: '南岸区' },
      { value: '北碚区', label: '北碚区' }, { value: '渝北区', label: '渝北区' },
      { value: '巴南区', label: '巴南区' }
    ]}
  ]},
  { value: '河北省', label: '河北省', children: [
    { value: '石家庄市', label: '石家庄市', children: [
      { value: '长安区', label: '长安区' }, { value: '桥西区', label: '桥西区' },
      { value: '新华区', label: '新华区' }, { value: '裕华区', label: '裕华区' }
    ]},
    { value: '唐山市', label: '唐山市', children: [
      { value: '路北区', label: '路北区' }, { value: '路南区', label: '路南区' }
    ]},
    { value: '保定市', label: '保定市', children: [
      { value: '竞秀区', label: '竞秀区' }, { value: '莲池区', label: '莲池区' }
    ]},
    { value: '廊坊市', label: '廊坊市', children: [
      { value: '广阳区', label: '广阳区' }, { value: '安次区', label: '安次区' }
    ]}
  ]},
  { value: '山西省', label: '山西省', children: [
    { value: '太原市', label: '太原市', children: [
      { value: '小店区', label: '小店区' }, { value: '迎泽区', label: '迎泽区' },
      { value: '杏花岭区', label: '杏花岭区' }, { value: '尖草坪区', label: '尖草坪区' },
      { value: '万柏林区', label: '万柏林区' }, { value: '晋源区', label: '晋源区' }
    ]},
    { value: '大同市', label: '大同市', children: [
      { value: '平城区', label: '平城区' }, { value: '云冈区', label: '云冈区' }
    ]}
  ]},
  { value: '内蒙古自治区', label: '内蒙古自治区', children: [
    { value: '呼和浩特市', label: '呼和浩特市', children: [
      { value: '新城区', label: '新城区' }, { value: '回民区', label: '回民区' },
      { value: '玉泉区', label: '玉泉区' }, { value: '赛罕区', label: '赛罕区' }
    ]},
    { value: '包头市', label: '包头市', children: [
      { value: '昆都仑区', label: '昆都仑区' }, { value: '青山区', label: '青山区' }
    ]}
  ]},
  { value: '辽宁省', label: '辽宁省', children: [
    { value: '沈阳市', label: '沈阳市', children: [
      { value: '和平区', label: '和平区' }, { value: '沈河区', label: '沈河区' },
      { value: '大东区', label: '大东区' }, { value: '皇姑区', label: '皇姑区' },
      { value: '铁西区', label: '铁西区' }, { value: '浑南区', label: '浑南区' }
    ]},
    { value: '大连市', label: '大连市', children: [
      { value: '中山区', label: '中山区' }, { value: '西岗区', label: '西岗区' },
      { value: '沙河口区', label: '沙河口区' }, { value: '甘井子区', label: '甘井子区' }
    ]}
  ]},
  { value: '吉林省', label: '吉林省', children: [
    { value: '长春市', label: '长春市', children: [
      { value: '南关区', label: '南关区' }, { value: '宽城区', label: '宽城区' },
      { value: '朝阳区', label: '朝阳区' }, { value: '二道区', label: '二道区' },
      { value: '绿园区', label: '绿园区' }
    ]},
    { value: '吉林市', label: '吉林市', children: [
      { value: '船营区', label: '船营区' }, { value: '昌邑区', label: '昌邑区' }
    ]}
  ]},
  { value: '黑龙江省', label: '黑龙江省', children: [
    { value: '哈尔滨市', label: '哈尔滨市', children: [
      { value: '道里区', label: '道里区' }, { value: '南岗区', label: '南岗区' },
      { value: '道外区', label: '道外区' }, { value: '松北区', label: '松北区' },
      { value: '香坊区', label: '香坊区' }
    ]},
    { value: '大庆市', label: '大庆市', children: [
      { value: '萨尔图区', label: '萨尔图区' }, { value: '龙凤区', label: '龙凤区' }
    ]}
  ]},
  { value: '江苏省', label: '江苏省', children: [
    { value: '南京市', label: '南京市', children: [
      { value: '玄武区', label: '玄武区' }, { value: '秦淮区', label: '秦淮区' },
      { value: '建邺区', label: '建邺区' }, { value: '鼓楼区', label: '鼓楼区' },
      { value: '栖霞区', label: '栖霞区' }, { value: '雨花台区', label: '雨花台区' },
      { value: '江宁区', label: '江宁区' }, { value: '浦口区', label: '浦口区' }
    ]},
    { value: '苏州市', label: '苏州市', children: [
      { value: '姑苏区', label: '姑苏区' }, { value: '虎丘区', label: '虎丘区' },
      { value: '吴中区', label: '吴中区' }, { value: '相城区', label: '相城区' },
      { value: '吴江区', label: '吴江区' }
    ]},
    { value: '无锡市', label: '无锡市', children: [
      { value: '梁溪区', label: '梁溪区' }, { value: '锡山区', label: '锡山区' },
      { value: '惠山区', label: '惠山区' }, { value: '滨湖区', label: '滨湖区' },
      { value: '新吴区', label: '新吴区' }
    ]},
    { value: '常州市', label: '常州市', children: [
      { value: '天宁区', label: '天宁区' }, { value: '钟楼区', label: '钟楼区' },
      { value: '新北区', label: '新北区' }, { value: '武进区', label: '武进区' }
    ]},
    { value: '南通市', label: '南通市', children: [
      { value: '崇川区', label: '崇川区' }, { value: '通州区', label: '通州区' }
    ]},
    { value: '徐州市', label: '徐州市', children: [
      { value: '鼓楼区', label: '鼓楼区' }, { value: '云龙区', label: '云龙区' },
      { value: '泉山区', label: '泉山区' }
    ]}
  ]},
  { value: '浙江省', label: '浙江省', children: [
    { value: '杭州市', label: '杭州市', children: [
      { value: '上城区', label: '上城区' }, { value: '拱墅区', label: '拱墅区' },
      { value: '西湖区', label: '西湖区' }, { value: '滨江区', label: '滨江区' },
      { value: '萧山区', label: '萧山区' }, { value: '余杭区', label: '余杭区' },
      { value: '临平区', label: '临平区' }, { value: '钱塘区', label: '钱塘区' }
    ]},
    { value: '宁波市', label: '宁波市', children: [
      { value: '海曙区', label: '海曙区' }, { value: '江北区', label: '江北区' },
      { value: '鄞州区', label: '鄞州区' }, { value: '北仑区', label: '北仑区' }
    ]},
    { value: '温州市', label: '温州市', children: [
      { value: '鹿城区', label: '鹿城区' }, { value: '龙湾区', label: '龙湾区' },
      { value: '瓯海区', label: '瓯海区' }
    ]},
    { value: '嘉兴市', label: '嘉兴市', children: [
      { value: '南湖区', label: '南湖区' }, { value: '秀洲区', label: '秀洲区' }
    ]},
    { value: '金华市', label: '金华市', children: [
      { value: '婺城区', label: '婺城区' }, { value: '金东区', label: '金东区' }
    ]}
  ]},
  { value: '安徽省', label: '安徽省', children: [
    { value: '合肥市', label: '合肥市', children: [
      { value: '瑶海区', label: '瑶海区' }, { value: '庐阳区', label: '庐阳区' },
      { value: '蜀山区', label: '蜀山区' }, { value: '包河区', label: '包河区' }
    ]},
    { value: '芜湖市', label: '芜湖市', children: [
      { value: '镜湖区', label: '镜湖区' }, { value: '鸠江区', label: '鸠江区' }
    ]}
  ]},
  { value: '福建省', label: '福建省', children: [
    { value: '福州市', label: '福州市', children: [
      { value: '鼓楼区', label: '鼓楼区' }, { value: '台江区', label: '台江区' },
      { value: '仓山区', label: '仓山区' }, { value: '晋安区', label: '晋安区' },
      { value: '马尾区', label: '马尾区' }
    ]},
    { value: '厦门市', label: '厦门市', children: [
      { value: '思明区', label: '思明区' }, { value: '湖里区', label: '湖里区' },
      { value: '集美区', label: '集美区' }, { value: '海沧区', label: '海沧区' },
      { value: '同安区', label: '同安区' }, { value: '翔安区', label: '翔安区' }
    ]},
    { value: '泉州市', label: '泉州市', children: [
      { value: '鲤城区', label: '鲤城区' }, { value: '丰泽区', label: '丰泽区' },
      { value: '洛江区', label: '洛江区' }, { value: '泉港区', label: '泉港区' }
    ]}
  ]},
  { value: '江西省', label: '江西省', children: [
    { value: '南昌市', label: '南昌市', children: [
      { value: '东湖区', label: '东湖区' }, { value: '西湖区', label: '西湖区' },
      { value: '青云谱区', label: '青云谱区' }, { value: '青山湖区', label: '青山湖区' },
      { value: '红谷滩区', label: '红谷滩区' }
    ]},
    { value: '九江市', label: '九江市', children: [
      { value: '浔阳区', label: '浔阳区' }, { value: '濂溪区', label: '濂溪区' }
    ]}
  ]},
  { value: '山东省', label: '山东省', children: [
    { value: '济南市', label: '济南市', children: [
      { value: '历下区', label: '历下区' }, { value: '市中区', label: '市中区' },
      { value: '槐荫区', label: '槐荫区' }, { value: '天桥区', label: '天桥区' },
      { value: '历城区', label: '历城区' }
    ]},
    { value: '青岛市', label: '青岛市', children: [
      { value: '市南区', label: '市南区' }, { value: '市北区', label: '市北区' },
      { value: '李沧区', label: '李沧区' }, { value: '崂山区', label: '崂山区' },
      { value: '城阳区', label: '城阳区' }
    ]},
    { value: '烟台市', label: '烟台市', children: [
      { value: '芝罘区', label: '芝罘区' }, { value: '莱山区', label: '莱山区' }
    ]},
    { value: '潍坊市', label: '潍坊市', children: [
      { value: '潍城区', label: '潍城区' }, { value: '奎文区', label: '奎文区' }
    ]}
  ]},
  { value: '河南省', label: '河南省', children: [
    { value: '郑州市', label: '郑州市', children: [
      { value: '中原区', label: '中原区' }, { value: '二七区', label: '二七区' },
      { value: '管城回族区', label: '管城回族区' }, { value: '金水区', label: '金水区' },
      { value: '惠济区', label: '惠济区' }
    ]},
    { value: '洛阳市', label: '洛阳市', children: [
      { value: '西工区', label: '西工区' }, { value: '洛龙区', label: '洛龙区' }
    ]}
  ]},
  { value: '湖北省', label: '湖北省', children: [
    { value: '武汉市', label: '武汉市', children: [
      { value: '江岸区', label: '江岸区' }, { value: '江汉区', label: '江汉区' },
      { value: '硚口区', label: '硚口区' }, { value: '汉阳区', label: '汉阳区' },
      { value: '武昌区', label: '武昌区' }, { value: '青山区', label: '青山区' },
      { value: '洪山区', label: '洪山区' }, { value: '东西湖区', label: '东西湖区' }
    ]},
    { value: '宜昌市', label: '宜昌市', children: [
      { value: '西陵区', label: '西陵区' }, { value: '伍家岗区', label: '伍家岗区' }
    ]}
  ]},
  { value: '湖南省', label: '湖南省', children: [
    { value: '长沙市', label: '长沙市', children: [
      { value: '芙蓉区', label: '芙蓉区' }, { value: '天心区', label: '天心区' },
      { value: '岳麓区', label: '岳麓区' }, { value: '开福区', label: '开福区' },
      { value: '雨花区', label: '雨花区' }, { value: '望城区', label: '望城区' }
    ]},
    { value: '株洲市', label: '株洲市', children: [
      { value: '天元区', label: '天元区' }, { value: '芦淞区', label: '芦淞区' }
    ]}
  ]},
  { value: '广东省', label: '广东省', children: [
    { value: '广州市', label: '广州市', children: [
      { value: '越秀区', label: '越秀区' }, { value: '天河区', label: '天河区' },
      { value: '海珠区', label: '海珠区' }, { value: '荔湾区', label: '荔湾区' },
      { value: '白云区', label: '白云区' }, { value: '番禺区', label: '番禺区' },
      { value: '黄埔区', label: '黄埔区' }, { value: '南沙区', label: '南沙区' },
      { value: '花都区', label: '花都区' }
    ]},
    { value: '深圳市', label: '深圳市', children: [
      { value: '福田区', label: '福田区' }, { value: '罗湖区', label: '罗湖区' },
      { value: '南山区', label: '南山区' }, { value: '宝安区', label: '宝安区' },
      { value: '龙岗区', label: '龙岗区' }, { value: '龙华区', label: '龙华区' },
      { value: '光明区', label: '光明区' }, { value: '坪山区', label: '坪山区' },
      { value: '盐田区', label: '盐田区' }
    ]},
    { value: '东莞市', label: '东莞市', children: [
      { value: '莞城街道', label: '莞城街道' }, { value: '南城街道', label: '南城街道' },
      { value: '东城街道', label: '东城街道' }, { value: '万江街道', label: '万江街道' }
    ]},
    { value: '佛山市', label: '佛山市', children: [
      { value: '禅城区', label: '禅城区' }, { value: '南海区', label: '南海区' },
      { value: '顺德区', label: '顺德区' }, { value: '高明区', label: '高明区' },
      { value: '三水区', label: '三水区' }
    ]},
    { value: '珠海市', label: '珠海市', children: [
      { value: '香洲区', label: '香洲区' }, { value: '斗门区', label: '斗门区' },
      { value: '金湾区', label: '金湾区' }
    ]},
    { value: '惠州市', label: '惠州市', children: [
      { value: '惠城区', label: '惠城区' }, { value: '惠阳区', label: '惠阳区' }
    ]}
  ]},
  { value: '广西壮族自治区', label: '广西壮族自治区', children: [
    { value: '南宁市', label: '南宁市', children: [
      { value: '青秀区', label: '青秀区' }, { value: '兴宁区', label: '兴宁区' },
      { value: '西乡塘区', label: '西乡塘区' }, { value: '江南区', label: '江南区' },
      { value: '良庆区', label: '良庆区' }
    ]},
    { value: '桂林市', label: '桂林市', children: [
      { value: '秀峰区', label: '秀峰区' }, { value: '象山区', label: '象山区' },
      { value: '七星区', label: '七星区' }
    ]}
  ]},
  { value: '海南省', label: '海南省', children: [
    { value: '海口市', label: '海口市', children: [
      { value: '龙华区', label: '龙华区' }, { value: '美兰区', label: '美兰区' },
      { value: '琼山区', label: '琼山区' }, { value: '秀英区', label: '秀英区' }
    ]},
    { value: '三亚市', label: '三亚市', children: [
      { value: '吉阳区', label: '吉阳区' }, { value: '天涯区', label: '天涯区' },
      { value: '海棠区', label: '海棠区' }, { value: '崖州区', label: '崖州区' }
    ]}
  ]},
  { value: '四川省', label: '四川省', children: [
    { value: '成都市', label: '成都市', children: [
      { value: '锦江区', label: '锦江区' }, { value: '青羊区', label: '青羊区' },
      { value: '金牛区', label: '金牛区' }, { value: '武侯区', label: '武侯区' },
      { value: '成华区', label: '成华区' }, { value: '高新区', label: '高新区' }
    ]},
    { value: '绵阳市', label: '绵阳市', children: [
      { value: '涪城区', label: '涪城区' }, { value: '游仙区', label: '游仙区' }
    ]}
  ]},
  { value: '贵州省', label: '贵州省', children: [
    { value: '贵阳市', label: '贵阳市', children: [
      { value: '南明区', label: '南明区' }, { value: '云岩区', label: '云岩区' },
      { value: '花溪区', label: '花溪区' }, { value: '乌当区', label: '乌当区' },
      { value: '观山湖区', label: '观山湖区' }
    ]},
    { value: '遵义市', label: '遵义市', children: [
      { value: '红花岗区', label: '红花岗区' }, { value: '汇川区', label: '汇川区' }
    ]}
  ]},
  { value: '云南省', label: '云南省', children: [
    { value: '昆明市', label: '昆明市', children: [
      { value: '五华区', label: '五华区' }, { value: '盘龙区', label: '盘龙区' },
      { value: '官渡区', label: '官渡区' }, { value: '西山区', label: '西山区' },
      { value: '呈贡区', label: '呈贡区' }
    ]},
    { value: '大理白族自治州', label: '大理白族自治州', children: [
      { value: '大理市', label: '大理市' }
    ]}
  ]},
  { value: '西藏自治区', label: '西藏自治区', children: [
    { value: '拉萨市', label: '拉萨市', children: [
      { value: '城关区', label: '城关区' }, { value: '堆龙德庆区', label: '堆龙德庆区' }
    ]}
  ]},
  { value: '陕西省', label: '陕西省', children: [
    { value: '西安市', label: '西安市', children: [
      { value: '新城区', label: '新城区' }, { value: '碑林区', label: '碑林区' },
      { value: '莲湖区', label: '莲湖区' }, { value: '雁塔区', label: '雁塔区' },
      { value: '未央区', label: '未央区' }, { value: '灞桥区', label: '灞桥区' },
      { value: '长安区', label: '长安区' }
    ]},
    { value: '咸阳市', label: '咸阳市', children: [
      { value: '秦都区', label: '秦都区' }, { value: '渭城区', label: '渭城区' }
    ]}
  ]},
  { value: '甘肃省', label: '甘肃省', children: [
    { value: '兰州市', label: '兰州市', children: [
      { value: '城关区', label: '城关区' }, { value: '七里河区', label: '七里河区' },
      { value: '西固区', label: '西固区' }, { value: '安宁区', label: '安宁区' }
    ]}
  ]},
  { value: '青海省', label: '青海省', children: [
    { value: '西宁市', label: '西宁市', children: [
      { value: '城东区', label: '城东区' }, { value: '城中区', label: '城中区' },
      { value: '城西区', label: '城西区' }, { value: '城北区', label: '城北区' }
    ]}
  ]},
  { value: '宁夏回族自治区', label: '宁夏回族自治区', children: [
    { value: '银川市', label: '银川市', children: [
      { value: '兴庆区', label: '兴庆区' }, { value: '金凤区', label: '金凤区' },
      { value: '西夏区', label: '西夏区' }
    ]}
  ]},
  { value: '新疆维吾尔自治区', label: '新疆维吾尔自治区', children: [
    { value: '乌鲁木齐市', label: '乌鲁木齐市', children: [
      { value: '天山区', label: '天山区' }, { value: '沙依巴克区', label: '沙依巴克区' },
      { value: '新市区', label: '新市区' }, { value: '水磨沟区', label: '水磨沟区' }
    ]}
  ]}
];

// ── 导航：我的订单 ──
function goToOrders() {
  router.push({ name: 'OrderList' });
}

// ── watch activeSection 处理我的订单跳转 ──
import { watch } from 'vue';
watch(activeSection, (val) => {
  if (val === 'orders') {
    goToOrders();
    activeSection.value = 'profile';
  }
});

// ── 生命周期 ──
onMounted(async () => {
  await fetchProfile();
  await fetchAddresses();
});
</script>

<style scoped>
/* ── 页面布局 ── */
.profile-page {
  display: flex;
  min-height: calc(100vh - 56px);
  background: var(--color-bg-page, hsl(25, 5%, 97%));
}

/* ── 左侧导航 ── */
.profile-sidebar {
  width: 180px;
  flex-shrink: 0;
  background: var(--color-bg-base, #FFFFFF);
  border-right: 1px solid var(--color-border, hsl(25, 7%, 90%));
  padding: var(--space-lg, 24px) 0;
  display: flex;
  flex-direction: column;
}

.sidebar-user-brief {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 var(--space-md, 16px) var(--space-lg, 24px);
  border-bottom: 1px solid var(--color-border, hsl(25, 7%, 90%));
  margin-bottom: var(--space-sm, 8px);
}

.sidebar-nickname {
  margin-top: var(--space-sm, 8px);
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-secondary, hsl(25, 7%, 42%));
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-xs, 4px);
  padding: var(--space-sm, 8px) var(--space-lg, 24px);
  font-size: var(--font-size-base, 14px);
  color: var(--color-text-secondary, hsl(25, 7%, 42%));
  cursor: pointer;
  transition: background var(--duration-fast, 150ms) var(--ease-smooth, cubic-bezier(0.16, 1, 0.3, 1)),
              color var(--duration-fast, 150ms) var(--ease-smooth, cubic-bezier(0.16, 1, 0.3, 1));
  border-left: 3px solid transparent;
  user-select: none;
}

.nav-item:hover {
  background: var(--color-primary-50, hsl(25, 26%, 95%));
  color: var(--color-primary-600, hsl(25, 85%, 45%));
}

.nav-item.active {
  background: var(--color-primary-100, hsl(25, 43%, 90%));
  color: var(--color-primary-700, hsl(25, 81%, 35%));
  border-left-color: var(--color-primary-500, hsl(25, 85%, 55%));
  font-weight: 600;
}

.nav-icon {
  font-size: 16px;
}

.logout-item {
  margin-top: auto;
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
}

.logout-item:hover {
  color: var(--color-error, hsl(0, 80%, 52%));
  background: hsl(0, 40%, 96%);
}

/* ── 右侧内容 ── */
.profile-content {
  flex: 1;
  padding: var(--space-xl, 32px);
  max-width: 560px;
}

.content-section {
  animation: sectionFadeIn var(--duration-normal, 225ms) var(--ease-smooth, cubic-bezier(0.16, 1, 0.3, 1));
}

@keyframes sectionFadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

.section-title {
  font-size: var(--font-size-xl, 21px);
  font-weight: 700;
  color: var(--color-text-primary, hsl(25, 9%, 12%));
  margin: 0 0 var(--space-lg, 24px);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-lg, 24px);
}

.section-header .section-title {
  margin-bottom: 0;
}

/* ── 个人资料卡片 ── */
.profile-card {
  background: var(--page-account-card-bg, hsl(215, 3%, 99%));
  border: 1px solid var(--color-border, hsl(25, 7%, 90%));
  border-radius: var(--radius-lg, 30px);
  padding: var(--space-xl, 32px);
  box-shadow: var(--shadow-sm, 0 1px 2px rgba(30,28,27,0.05));
}

.profile-avatar-row {
  display: flex;
  align-items: center;
  gap: var(--space-lg, 24px);
}

.profile-avatar-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs, 4px);
}

.profile-role-tag {
  display: flex;
  gap: var(--space-sm, 8px);
}

.profile-info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-md, 16px);
  margin-top: var(--space-md, 16px);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item label {
  font-size: var(--font-size-xs, 10.5px);
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-item span {
  font-size: var(--font-size-base, 14px);
  color: var(--color-text-primary, hsl(25, 9%, 12%));
  line-height: var(--line-height-normal, 1.5);
}

/* ── 地址列表 ── */
.address-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-md, 16px);
}

.address-card {
  background: var(--color-bg-base, #FFFFFF);
  border: 1px solid var(--color-border, hsl(25, 7%, 90%));
  border-radius: var(--radius-md, 20px);
  padding: var(--space-md, 16px) var(--space-lg, 24px);
  box-shadow: var(--shadow-sm, 0 1px 2px rgba(30,28,27,0.05));
  transition: box-shadow var(--duration-fast, 150ms) var(--ease-smooth, cubic-bezier(0.16, 1, 0.3, 1)),
              border-color var(--duration-fast, 150ms) var(--ease-smooth, cubic-bezier(0.16, 1, 0.3, 1));
}

.address-card.is-default {
  border-color: var(--color-primary-300, hsl(25, 72%, 70%));
  background: var(--color-primary-50, hsl(25, 26%, 95%));
}

.address-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-xs, 4px);
}

.address-contact strong {
  font-size: var(--font-size-base, 14px);
  color: var(--color-text-primary, hsl(25, 9%, 12%));
}

.address-phone {
  margin-left: var(--space-md, 16px);
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-secondary, hsl(25, 7%, 42%));
}

.address-card-body {
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-secondary, hsl(25, 7%, 42%));
  line-height: var(--line-height-normal, 1.5);
  margin-bottom: var(--space-sm, 8px);
}

.address-card-actions {
  display: flex;
  gap: var(--space-sm, 8px);
}

/* ── 空状态 ── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-3xl, 64px) var(--space-lg, 24px);
  background: var(--color-bg-base, #FFFFFF);
  border: 1px solid var(--color-border, hsl(25, 7%, 90%));
  border-radius: var(--radius-md, 20px);
}

.empty-icon {
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
  margin-bottom: var(--space-md, 16px);
}

.empty-title {
  font-size: var(--font-size-md, 15.75px);
  color: var(--color-text-secondary, hsl(25, 7%, 42%));
  margin: 0 0 var(--space-xs, 4px);
}

.empty-desc {
  font-size: var(--font-size-sm, 12.25px);
  color: var(--color-text-tertiary, hsl(25, 4%, 62%));
  margin: 0 0 var(--space-lg, 24px);
}

/* ── 安全设置卡片 ── */
.security-card {
  background: var(--color-bg-base, #FFFFFF);
  border: 1px solid var(--color-border, hsl(25, 7%, 90%));
  border-radius: var(--radius-md, 20px);
  padding: var(--space-xl, 32px);
}

.security-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-xl, 32px) 0;
}

/* ── 响应式 ── */
@media (max-width: 768px) {
  .profile-page {
    flex-direction: column;
  }

  .profile-sidebar {
    width: 100%;
    flex-direction: row;
    padding: var(--space-sm, 8px);
    border-right: none;
    border-bottom: 1px solid var(--color-border, hsl(25, 7%, 90%));
    overflow-x: auto;
  }

  .sidebar-user-brief {
    display: none;
  }

  .sidebar-nav {
    flex-direction: row;
    gap: 0;
  }

  .nav-item {
    border-left: none;
    border-bottom: 2px solid transparent;
    padding: var(--space-sm, 8px) var(--space-md, 16px);
    white-space: nowrap;
    font-size: var(--font-size-sm, 12.25px);
  }

  .nav-item.active {
    border-left-color: transparent;
    border-bottom-color: var(--color-primary-500, hsl(25, 85%, 55%));
  }

  .logout-item {
    margin-top: 0;
    margin-left: auto;
  }

  .profile-content {
    max-width: 100%;
    padding: var(--space-md, 16px);
  }

  .profile-info-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .profile-content {
    padding: var(--space-sm, 8px);
  }

  .profile-card,
  .address-card,
  .security-card {
    border-radius: var(--radius-sm, 10px);
    padding: var(--space-md, 16px);
    box-shadow: none;
  }
}
</style>
