# 文件上传与静态资源规范（所有 Agent 共享）

🛑 本文档是文件上传、存储、渲染的**唯一权威来源**。图片/视频/文档等所有静态文件遵循同一套逻辑。

---

## 核心规则

1. **禁止硬编码完整 URL** — 所有文件路径必须是相对路径（`/img/...`, `/video/...`, `/audio/...`, `/file/...`），完整 URL 由 `FILE_BASE_URL` + 相对路径拼接
2. **按类型分一级目录** — `img/`（图片）、`video/`（视频）、`audio/`（音频）、`file/`（文档等），Agent 在一级目录下自行细化二级子目录
3. **统一上传逻辑** — 前端传 `type` 参数（如 `img/avatar`、`video/course`），后端自动写入对应目录
4. **占位文件兜底** — 开发/演示阶段使用占位文件，`FILE_MODE=mock`；生产用真实文件，`FILE_MODE=real`

---

## 目录结构

```
public/
├── img/                         # 图片
│   ├── public/                  # 静态（Logo/图标/Banner — 开发者管理）
│   │   └── placeholder/        # 占位图（Python 自动生成）
│   └── user/                    # 动态（用户上传 — 内容编辑管理）
│       └── {agent自定义子目录}/  # 如 products/、avatars/、covers/
├── video/                       # 视频
│   ├── public/                  # 静态（演示视频/片头）
│   │   └── placeholder/
│   └── user/                    # 动态（用户上传）
│       └── {agent自定义子目录}/  # 如 courses/、shorts/、live/
├── audio/                       # 音频
│   ├── public/                  # 静态（系统提示音/背景音乐）
│   │   └── placeholder/
│   └── user/                    # 动态（用户上传）
│       └── {agent自定义子目录}/  # 如 podcasts/、songs/、voice/
├── file/                        # 其他文件（文档/压缩包）
│   ├── public/                  # 静态（协议模板/示例文件）
│   │   └── placeholder/
│   └── user/                    # 动态（用户上传）
│       └── {agent自定义子目录}/  # 如 contracts/、invoices/、exports/
```

🛑 Agent 根据项目类型自行命名二级子目录，不硬编码分类。
🛑 没有对应文件类型的项目（如无视频）→ 不创建对应目录。

---

## 路径格式

### 代码中引用

```html
<!-- ✅ 正确：相对路径 -->
<img :src="`${FILE_BASE_URL}/img/user/products/phone.jpg`" />
<video :src="`${FILE_BASE_URL}/video/user/courses/lesson1.mp4`" />
<audio :src="`${FILE_BASE_URL}/audio/user/podcasts/ep1.mp3`" />
<a :href="`${FILE_BASE_URL}/file/user/contracts/agreement.pdf`">下载</a>

<!-- ❌ 错误：硬编码完整 URL -->
<img src="https://example.com/images/logo.png" />
<video src="https://videos.example.com/course.mp4" />
```

### .env 配置

```bash
# ══ 文件服务 ══
# 文件服务基础 URL（末尾无斜杠），所有 /img/ /video/ /file/ 路径拼接此前缀
# 空 = 同源加载（开发/演示），非空 = 独立文件服务器/CDN（生产）
FILE_BASE_URL=
# 演示模式用占位文件，生产模式用真实文件
FILE_MODE=mock
```

---

## 三部分统一逻辑

### 1. 上传（backend Agent）

永远写入本地 `public/`，返回相对路径。上传接口按 `type` 参数自动分类：

```
前端: FormData { file, type: "img/avatar" }     → 后端: public/img/user/avatar/xxx.jpg
前端: FormData { file, type: "video/course" }     → 后端: public/video/user/course/xxx.mp4
前端: FormData { file, type: "audio/podcast" }    → 后端: public/audio/user/podcast/xxx.mp3
前端: FormData { file, type: "file/contract" }    → 后端: public/file/user/contract/xxx.pdf
```

```js
const UPLOAD_DIRS = {
  img:   'public/img/user',
  video: 'public/video/user',
  audio: 'public/audio/user',
  file:  'public/file/user',
};

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const type = req.body.type || 'file/general';     // 如 "img/avatar"
    const [category, sub] = type.split('/');
    const dir = path.join(UPLOAD_DIRS[category] || UPLOAD_DIRS.file, sub);
    fs.mkdirSync(dir, { recursive: true });
    cb(null, dir);
  },
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname);
    cb(null, Date.now() + '_' + crypto.randomBytes(4).toString('hex') + ext);
  }
});
// 返回: { url: "/img/user/avatar/20260714_a1b2c3.jpg" }
```

### 2. 存储

- **开发/演示**：`Express.static('public')` — 同源直接访问
- **生产**：`rsync public/ → 文件服务器`，或 Nginx `proxy_pass /img/ → 文件服务器`
- **切换**：只需 1) 同步文件 2) 改 `FILE_BASE_URL`。上传逻辑零改动。

### 3. 渲染（frontend Agent）

```js
// src/utils/asset.js
const FILE_BASE_URL = import.meta.env.VITE_FILE_BASE_URL || '';

export function assetUrl(path) {
  if (!path) return '';
  if (path.startsWith('http')) return path;  // 已是完整 URL（兼容旧数据）
  return FILE_BASE_URL + path;
}
```

```html
<img :src="assetUrl(item.image)" />
<video :src="assetUrl(item.videoUrl)" />
```

---

## Agent 生成规则

### infra Agent
- `.env.example` 中添加 `FILE_BASE_URL` 和 `FILE_MODE`
- 占位文件由 Python 自动生成到 `public/*/placeholder/`

### db Agent（seed 数据）
- 文件字段统一使用占位路径（Python 自动生成到 `public/{category}/public/placeholder/`）：
  - 图片：`/img/public/placeholder/avatar.svg` `/img/public/placeholder/product.svg` `/img/public/placeholder/banner.svg` `/img/public/placeholder/logo.svg`
  - 视频：`/video/public/placeholder/video.svg`
  - 音频：`/audio/public/placeholder/audio.svg`
  - 文件：`/file/public/placeholder/document.svg`
- 禁止编造 `https://...` 完整 URL

### frontend Agent
- `<img>/<video>/<a>` 使用 `assetUrl()` 拼接 `FILE_BASE_URL`
- 子目录根据项目类型自行命名

### backend Agent
- 上传接口按 `type` 参数写入对应 `public/{category}/user/{sub}/`
- 数据库只存相对路径

### integrator Agent
- 完成后 Python 扫描所有 `/img/`、`/video/`、`/file/` 引用，生成 `Memory/file_manifest.json`
