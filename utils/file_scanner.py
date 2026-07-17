# utils/file_scanner.py
"""生成部署清单 —— 扫描项目中需要人工配置的三类内容：
  1. 静态文件（/img/ /video/ /audio/ /file/）
  2. 第三方服务（*_MODE=real 时需要的 API 密钥）
  3. 占位文件（需要替换为真实文件的 placeholder）
"""

import json
import re
from pathlib import Path
from datetime import datetime


def scan(workspace: str | Path) -> dict:
    ws = Path(workspace).resolve()
    return {
        "generated_at": datetime.now().isoformat(),
        "static_files": _scan_static_files(ws),
        "third_party_services": _scan_services(ws),
        "placeholders": _scan_placeholders(ws),
    }


def save_manifest(workspace: str | Path, manifest_dir: str | Path = None) -> Path:
    result = scan(workspace)
    ws = Path(workspace).resolve()
    dest = (Path(manifest_dir) if manifest_dir else ws.parent / "Memory") / "deployment_manifest.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2, ensure_ascii=False), "utf-8", newline="\n")

    sf = result["static_files"]
    sv = result["third_party_services"]
    ph = result["placeholders"]
    print(f"[manifest] 部署清单: {dest}")
    print(f"  静态文件: {sf['total']} ({sf['img']}图片 {sf['video']}视频 {sf['audio']}音频 {sf['file']}其他)")
    print(f"  第三方服务: {len(sv)} 个")
    print(f"  占位文件: {len(ph)} 个")
    return dest


# ═══════════════════════════════════
# 1. 静态文件扫描
# ═══════════════════════════════════

def _scan_static_files(ws: Path) -> dict:
    files = {}
    _path_re = re.compile(r"""["'\(]\s*(/(?:img|video|audio|file)/[^"'\s()>]+)""")

    for ext in ["*.vue", "*.js", "*.json", "*.html"]:
        for fp in ws.rglob(ext):
            if any(s in fp.parts for s in ("node_modules", ".git", "test", "Memory", ".meta")):
                continue
            try:
                content = fp.read_text("utf-8", errors="replace")
            except Exception:
                continue
            rel_file = str(fp.relative_to(ws)).replace("\\", "/")
            for m in _path_re.finditer(content):
                fpath = m.group(1).split("?")[0].split("#")[0]
                if fpath not in files:
                    files[fpath] = {"path": fpath, "category": _cat(fpath),
                                    "type": _type(fpath), "referenced_by": []}
                ref = f"{rel_file}:{content[:m.start()].count(chr(10)) + 1}"
                if ref not in files[fpath]["referenced_by"]:
                    files[fpath]["referenced_by"].append(ref)

    sorted_files = sorted(files.values(), key=lambda x: (x["category"], x["path"]))
    return {
        "total": len(files),
        "img": sum(1 for v in files.values() if v["category"] == "img"),
        "video": sum(1 for v in files.values() if v["category"] == "video"),
        "audio": sum(1 for v in files.values() if v["category"] == "audio"),
        "file": sum(1 for v in files.values() if v["category"] == "file"),
        "files": sorted_files,
    }


# ═══════════════════════════════════
# 2. 第三方服务扫描
# ═══════════════════════════════════

def _scan_services(ws: Path) -> list:
    services = []
    env_file = ws / ".env"
    if not env_file.exists():
        return services

    env_content = env_file.read_text("utf-8", errors="replace")

    # 扫描代码中引用的服务（通过 npm 包名推断）
    pkg_file = ws / "package.json"
    npm_pkgs = set()
    if pkg_file.exists():
        try:
            pkg = json.loads(pkg_file.read_text("utf-8"))
            npm_pkgs = set(pkg.get("dependencies", {}).keys()) | set(pkg.get("devDependencies", {}).keys())
        except Exception:
            pass

    # 服务 → 需要的 env 变量映射
    _SERVICE_MAP = {
        "mysql2": {"vars": ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME"],
                   "note": "MySQL 数据库连接"},
        "redis": {"vars": ["REDIS_URL"], "note": "Redis 缓存/队列"},
        "ioredis": {"vars": ["REDIS_URL"], "note": "Redis 缓存/队列"},
        "mongoose": {"vars": ["MONGO_URL"], "note": "MongoDB 数据库连接"},
        "nodemailer": {"vars": ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS"],
                       "note": "邮件发送服务"},
        "bullmq": {"vars": ["REDIS_URL"], "note": "BullMQ 任务队列（依赖 Redis）"},
        "jsonwebtoken": {"vars": ["JWT_SECRET", "JWT_EXPIRES_IN", "JWT_REFRESH_SECRET"],
                         "note": "JWT 鉴权 Token 签名"},
        "bcrypt": {"vars": ["BCRYPT_SALT_ROUNDS"], "note": "密码哈希"},
        "bcryptjs": {"vars": ["BCRYPT_SALT_ROUNDS"], "note": "密码哈希"},
        "multer": {"vars": [], "note": "文件上传（本地存储，FILE_BASE_URL 控制访问前缀）"},
        "multer-s3": {"vars": ["AWS_ACCESS_KEY", "AWS_SECRET_KEY", "AWS_S3_BUCKET", "AWS_REGION"],
                      "note": "S3 文件上传存储"},
        "express-rate-limit": {"vars": [], "note": "API 限流"},
        "express-session": {"vars": ["SESSION_SECRET"], "note": "Session 管理"},
        "cors": {"vars": ["CORS_ORIGIN"], "note": "跨域白名单"},
        "helmet": {"vars": [], "note": "HTTP 安全头"},
        "compression": {"vars": [], "note": "Gzip 压缩"},
    }

    for pkg_name, info in _SERVICE_MAP.items():
        if pkg_name in npm_pkgs:
            # 检查哪些变量需要配置
            missing_vars = []
            configured_vars = []
            for var in info["vars"]:
                if re.search(rf'^{var}=', env_content, re.MULTILINE):
                    val = re.search(rf'^{var}=(.+)', env_content, re.MULTILINE)
                    configured_vars.append({var: val.group(1).strip() if val else "?"})
                else:
                    missing_vars.append(var)

            services.append({
                "service": pkg_name,
                "note": info["note"],
                "configured": configured_vars,
                "needs_config": missing_vars,
                "ready": len(missing_vars) == 0,
            })

    return services


# ═══════════════════════════════════
# 3. 占位文件扫描
# ═══════════════════════════════════

def _scan_placeholders(ws: Path) -> list:
    placeholders = []
    for fp in ws.rglob("*"):
        if any(s in fp.parts for s in ("node_modules", ".git", "Memory", ".meta")):
            continue
        rel = str(fp.relative_to(ws)).replace("\\", "/")
        if "/placeholder/" in rel and fp.is_file():
            placeholders.append({
                "file": rel,
                "size": fp.stat().st_size,
                "note": "占位文件，需要替换为真实内容",
            })
    return placeholders


def _cat(path: str) -> str:
    for c in ("img", "video", "audio", "file"):
        if f"/{c}/" in path or path.startswith(f"/{c}/"):
            return c
    return "file"


def _type(path: str) -> str:
    if "/placeholder/" in path:
        return "placeholder"
    if "/public/" in path:
        return "public"
    if "/user/" in path:
        return "user"
    return "public"
