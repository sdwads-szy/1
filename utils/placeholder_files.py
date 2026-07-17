# utils/placeholder_files.py
"""自动生成占位文件（img/video/audio/file），供 seed 数据和演示使用。

占位文件需要能真实使用: 图片显示、视频播放、音频播放、文件下载。
添加新类型/新文件: 在 _PLACEHOLDERS 字典中新增条目即可。
"""

import struct
from pathlib import Path

# ═══════════════════════════════════════════════
# SVG 生成器（用于 img 类型 + video/audio/file 的预览海报）
# ═══════════════════════════════════════════════

_SVG_WRAPPER = '<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n{body}\n</svg>'


def _box_svg(w: int, h: int, label: str, color: str = "#555B66") -> str:
    body = (
        f'  <rect width="{w}" height="{h}" fill="#0E1017"/>\n'
        f'  <rect x="{w//10}" y="{h//10}" width="{w*4//5}" height="{h*4//5}" rx="8" fill="#151720" stroke="#1C1F2B" stroke-width="1"/>\n'
        f'  <text x="{w//2}" y="{h//2 + 5}" text-anchor="middle" fill="{color}" font-size="{min(w,h)//15}" font-family="sans-serif">{label}</text>'
    )
    return _SVG_WRAPPER.format(w=w, h=h, body=body)


# ═══════════════════════════════════════════════
# 二进制生成器（可播放/可下载的真实文件）
# ═══════════════════════════════════════════════

def _make_wav(duration_sec: float = 1.0, sample_rate: int = 8000) -> bytes:
    """生成静音 WAV 文件，可真实播放。16-bit mono PCM。"""
    num_samples = int(duration_sec * sample_rate)
    data_size = num_samples * 2
    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF', 36 + data_size, b'WAVE',
        b'fmt ', 16, 1, 1, sample_rate, sample_rate * 2, 2, 16,
        b'data', data_size
    )
    return header + b'\x00' * data_size


def _make_minimal_mp4() -> bytes:
    """生成最小可播放 MP4（160x120 黑屏，~2秒，h.264 baseline）。"""
    # ── h.264 NAL units ──
    sps = bytes([0x67, 0x42, 0xC0, 0x0A, 0xA6, 0x11, 0x11, 0xE8, 0x40, 0x00, 0x00, 0xFA, 0x00, 0x00, 0x3A, 0x98, 0x23, 0xC4, 0x89, 0x83, 0x60])
    pps = bytes([0x68, 0xCB, 0x83, 0xCB, 0x20])
    # IDR slice — single black macroblock for 160x120
    idr = bytes([
        0x65, 0xB8, 0x00, 0x05, 0x3F, 0xFF, 0xFC, 0x16, 0xA7, 0x22, 0x73, 0x55, 0x8D, 0x96, 0x22, 0x53,
        0x1C, 0x7F, 0x3B, 0x6E, 0x92, 0x2A, 0xEE, 0x6B, 0x26, 0x93, 0x88, 0x81, 0xC4, 0x83, 0xF1, 0x40,
        0xB1, 0xD6, 0x3B, 0xC7, 0x79, 0xDD, 0x91, 0x3A, 0x92, 0xBC, 0xA1, 0xE9, 0x6E, 0xDF, 0x53, 0x7C,
        0xB2, 0x57, 0x31, 0x3D, 0x75, 0xED, 0x2D, 0x19, 0x83, 0x7E, 0xCE, 0x05, 0x00, 0x00, 0x03, 0x00,
        0x00, 0x03, 0x00, 0x00, 0x03, 0x00, 0x00, 0x03, 0x00, 0x5E, 0x2C, 0x05, 0x00
    ])

    avcc = struct.pack('>B', 1) + struct.pack('>BH', 1, len(sps)) + sps + struct.pack('>BH', 1, len(pps)) + pps

    def _atom(atype: bytes, data: bytes) -> bytes:
        return struct.pack('>I', 8 + len(data)) + atype + data

    tkhd = bytes([0] * 12 + [0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01]) + bytes([0] * 40) + struct.pack('>HH', 160, 120) + bytes(8)
    mdhd = bytes([0] * 12) + struct.pack('>I', 30) + struct.pack('>I', 30) + struct.pack('>I', 2) + bytes(8)
    hdlr = bytes([0] * 4) + b'vide' + bytes(12)
    vmhd = bytes([0] * 4) + bytes(8)
    dref = bytes([0] * 4) + struct.pack('>I', 1) + bytes(12)
    stsd = bytes([0] * 4) + struct.pack('>I', 1) + bytes(4) + b'avc1' + bytes(6) + struct.pack('>H', 1) + bytes(32) + struct.pack('>HH', 160, 120) + struct.pack('>I', 0x00480000) + struct.pack('>I', 0x00480000) + bytes(8) + struct.pack('>H', 1) + bytes(2) + avcc
    stts = bytes([0] * 4) + struct.pack('>I', 1) + struct.pack('>II', 2, 30)
    stsc = bytes([0] * 4) + struct.pack('>I', 1) + struct.pack('>III', 1, 1, 1)
    stsz = bytes([0] * 4) + struct.pack('>I', 0) + struct.pack('>I', 1) + struct.pack('>I', len(idr))
    stco = bytes([0] * 4) + struct.pack('>I', 1)

    dinf = _atom(b'dinf', _atom(b'dref', dref))
    stbl = _atom(b'stbl', stsd + _atom(b'stts', stts) + _atom(b'stsc', stsc) + _atom(b'stsz', stsz) + _atom(b'stco', stco))
    minf = _atom(b'minf', vmhd + dinf + stbl)
    mdia = _atom(b'mdia', mdhd + hdlr + minf)
    trak = _atom(b'trak', tkhd + mdia)

    # mdat atom — needs to be at absolute offset. Compute moov size first.
    mvhd = bytes([0] * 12) + struct.pack('>I', 2) + struct.pack('>I', 2) + struct.pack('>I', 30) + struct.pack('>I', 30) + bytes(48)
    moov_no_size = mvhd + trak
    moov = _atom(b'moov', moov_no_size)
    mdat = _atom(b'mdat', idr)

    ftyp = bytes([0x00, 0x00, 0x00, 0x14, 0x66, 0x74, 0x79, 0x70, 0x69, 0x73, 0x6F, 0x6D,
                  0x00, 0x00, 0x00, 0x01, 0x69, 0x73, 0x6F, 0x6D])

    return ftyp + moov + mdat


def _make_minimal_pdf() -> bytes:
    """生成最小合法 PDF（1 页空白），可真实打开。"""
    return (
        b'%PDF-1.4\n'
        b'1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n'
        b'2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n'
        b'3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\n'
        b'xref\n0 4\n'
        b'0000000000 65535 f \n'
        b'0000000009 00000 n \n'
        b'0000000058 00000 n \n'
        b'0000000115 00000 n \n'
        b'trailer<</Size 4/Root 1 0 R>>\n'
        b'startxref\n190\n'
        b'%%EOF'
    )


def _make_sample_txt() -> str:
    return "这是一个占位文本文件。\n实际内容由人工替换。\n\nThis is a placeholder text file.\nReplace with real content.\n"


# ═══════════════════════════════════════════════
# 占位文件注册表
# ═══════════════════════════════════════════════

# 格式: { "filename": (content, is_binary) }
# content: str（文本）或 bytes（二进制）
# is_binary: True = 二进制写入, False = 文本写入

_PLACEHOLDERS = {
    "img": {
        "avatar.svg":  (_SVG_WRAPPER.format(w=80, h=80, body=(
            '  <circle cx="40" cy="40" r="40" fill="#0D9488" opacity="0.2"/>\n'
            '  <circle cx="40" cy="30" r="14" fill="#0D9488" opacity="0.6"/>\n'
            '  <ellipse cx="40" cy="62" rx="22" ry="14" fill="#0D9488" opacity="0.5"/>'
        )), False),
        "product.svg": (_box_svg(400, 300, "商品图片"), False),
        "banner.svg":  (_SVG_WRAPPER.format(w=800, h=300, body=(
            '  <defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
            '<stop offset="0%" stop-color="#0D9488"/><stop offset="100%" stop-color="#10B981"/>'
            '</linearGradient></defs>\n'
            '  <rect width="800" height="300" fill="url(#bg)" opacity="0.15"/>\n'
            '  <text x="400" y="155" text-anchor="middle" fill="#9CA3AF" font-size="18" font-family="sans-serif">横幅图片</text>'
        )), False),
        "logo.svg":    (_SVG_WRAPPER.format(w=120, h=120, body=(
            '  <rect width="120" height="120" rx="12" fill="#151720" stroke="#1C1F2B" stroke-width="1"/>\n'
            '  <text x="60" y="65" text-anchor="middle" fill="#555B66" font-size="12" font-family="sans-serif">LOGO</text>'
        )), False),
    },
    "video": {
        "video.svg":    (_box_svg(640, 360, "▶ 视频占位", color="#8B5CF6"), False),
        "sample.mp4":   (_make_minimal_mp4(), True),   # 可播放黑屏视频
    },
    "audio": {
        "audio.svg":    (_box_svg(400, 80, "♪ 音频占位", color="#F59E0B"), False),
        "sample.wav":   (_make_wav(), True),            # 1秒静音，可播放
    },
    "file": {
        "document.svg": (_box_svg(300, 400, "📄 文档占位", color="#6B7280"), False),
        "sample.txt":   (_make_sample_txt(), False),    # 可下载文本
        "sample.pdf":   (_make_minimal_pdf(), True),    # 可打开 PDF
    },
}


# ═══════════════════════════════════════════════
# 生成入口
# ═══════════════════════════════════════════════

def ensure(workspace: str | Path) -> dict:
    """生成所有占位文件到 public/{category}/public/placeholder/。
    跳过已存在的文件。返回 {category: count}。
    """
    root = Path(workspace).resolve()
    result = {}
    for category, files in _PLACEHOLDERS.items():
        d = root / "public" / category / "public" / "placeholder"
        d.mkdir(parents=True, exist_ok=True)
        count = 0
        for name, (content, is_binary) in files.items():
            fp = d / name
            if not fp.exists():
                mode = "wb" if is_binary else "w"
                enc = None if is_binary else "utf-8"
                with open(fp, mode, encoding=enc) as f:
                    f.write(content.strip() + ("\n" if not is_binary else b""))
                count += 1
        if count:
            result[category] = count
    total = sum(result.values())
    if total:
        cats = ", ".join(f"{k}×{v}" for k, v in sorted(result.items()))
        print(f"  [placeholder] {total} 个占位文件已生成 ({cats}) → {root / 'public'}")
    return result
