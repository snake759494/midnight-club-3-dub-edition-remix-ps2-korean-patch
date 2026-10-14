"""게임 텍스처(.tex) 속 영문 문구를 한글로 다시 그린다.

.tex: u16 w,h,fmt,mips,... 14바이트 머리 + 팔레트 + 픽셀(+밉맵)
  fmt 14/1 : 8bpp, 팔레트 256색(CSM1 순서)   fmt 15/16 : 4bpp, 팔레트 16색
픽셀은 위아래가 뒤집혀 저장되어 있다(화면 기준으로 편집 후 다시 뒤집는다).
좌표는 모두 화면 기준 원본 텍스처 픽셀.
"""
import struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SW = np.arange(256); SW = (SW & 0xe7) | ((SW & 8) << 1) | ((SW & 0x10) >> 1)


class Tex:
    def __init__(self, data):
        self.d = bytearray(data)
        self.w, self.h, self.fmt, self.mips = struct.unpack_from('<4H', data, 0)
        self.bpp = 8 if self.fmt in (14, 1) else 4
        n = 256 if self.bpp == 8 else 16
        self.poff = 14; self.xoff = 14 + 4 * n
        pal = np.frombuffer(bytes(data[14:14 + 4 * n]), np.uint8).reshape(n, 4).copy()
        self.pal = pal[SW] if n == 256 else pal          # 논리 순서
        self.idx = self._read(0)

    def _sizes(self):
        out = []; w, h = self.w, self.h
        for k in range(max(1, self.mips)):
            out.append((w, h)); w = max(1, w // 2); h = max(1, h // 2)
        return out

    def _off(self, level):
        o = self.xoff
        for w, h in self._sizes()[:level]: o += w * h * self.bpp // 8
        return o

    def _read(self, level):
        w, h = self._sizes()[level]; o = self._off(level)
        if self.bpp == 8: px = np.frombuffer(bytes(self.d[o:o + w * h]), np.uint8).reshape(h, w)
        else:
            b = np.frombuffer(bytes(self.d[o:o + w * h // 2]), np.uint8)
            px = np.stack([b & 15, b >> 4], 1).reshape(h, w)
        return px[::-1].copy()                            # 화면 기준

    def rgba(self):
        return self.pal[self.idx].astype(np.float32)

    def quantize(self, img):
        """RGBA float (h,w,4) -> 팔레트 인덱스 (알파 0 은 가장 투명한 색)"""
        pal = self.pal.astype(np.float32)
        flat = img.reshape(-1, 4)
        # 알파는 0..128 범위 그대로 비교. 투명에 가까우면 색 무시
        wa = np.clip(flat[:, 3:4] / 128.0, 0, 1)
        dc = ((flat[:, None, :3] - pal[None, :, :3]) ** 2).sum(-1) * (wa ** 2)
        da = (flat[:, None, 3] - pal[None, :, 3]) ** 2 * 4
        out = np.empty(len(flat), np.uint8)
        for s in range(0, len(flat), 4096):
            out[s:s + 4096] = np.argmin(dc[s:s + 4096] + da[s:s + 4096], 1)
        return out.reshape(img.shape[:2])

    def write(self, img):
        """화면 기준 RGBA float(0..255, 알파 0..128) -> 모든 밉 레벨 기록"""
        for lv, (w, h) in enumerate(self._sizes()):
            if lv == 0: src = img
            else:
                im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGBA').resize((w, h), Image.BOX)
                src = np.asarray(im, np.float32)
            q = self.quantize(src)[::-1]
            o = self._off(lv)
            if self.bpp == 8: self.d[o:o + w * h] = q.astype(np.uint8).tobytes()
            else:
                f = q.reshape(-1)
                self.d[o:o + w * h // 2] = ((f[0::2] & 15) | ((f[1::2] & 15) << 4)).astype(np.uint8).tobytes()
        return bytes(self.d)


def inpaint(img, rect):
    """rect 안을 좌우 바깥 열 색으로 선형 보간해 지운다"""
    x0, y0, x1, y1 = rect
    x0 = max(0, x0); y0 = max(0, y0); x1 = min(img.shape[1], x1); y1 = min(img.shape[0], y1)
    L = img[y0:y1, max(0, x0 - 1)]; R = img[y0:y1, min(img.shape[1] - 1, x1)]
    t = np.linspace(0, 1, x1 - x0)[None, :, None]
    img[y0:y1, x0:x1] = L[:, None] * (1 - t) + R[:, None] * t


def clear(img, rect, color=(0, 0, 0, 0)):
    x0, y0, x1, y1 = rect
    img[max(0, y0):y1, max(0, x0):x1] = color


def text_layer(txt, ttf, box, h_px, angle=0.0, sx=1.0, italic=0.0):
    """box 중심에 높이 h_px 로 그린 알파 마스크(이미지 크기). 폭이 넘치면 가로로 줄인다"""
    S = 4
    f = ImageFont.truetype(ttf, int(h_px * S / 0.78))
    bb = f.getbbox(txt)
    W, H = bb[2] - bb[0] + 8 * S, bb[3] - bb[1] + 8 * S
    m = Image.new('L', (W, H), 0)
    ImageDraw.Draw(m).text((4 * S - bb[0], 4 * S - bb[1]), txt, font=f, fill=255)
    if italic:
        m = m.transform((W + int(H * italic), H), Image.AFFINE, (1, italic, -H * italic, 0, 1, 0), Image.BICUBIC)
    x0, y0, x1, y1 = box
    bw = (x1 - x0) * S
    tw = m.width * sx
    if tw > bw: sx = sx * bw / tw
    m = m.resize((max(1, int(m.width * sx)), m.height), Image.LANCZOS)
    if angle: m = m.rotate(-angle, resample=Image.BICUBIC, expand=True)
    return m, S


def stamp(img, mask, S, center, color, outline=0, ocolor=(0, 0, 0, 128)):
    """mask(S배) 를 center 에 color 로 합성. outline>0 이면 테두리"""
    h, w = img.shape[:2]
    big = Image.new('L', (w * S, h * S), 0)
    cx, cy = center
    big.paste(mask, (int(cx * S - mask.width / 2), int(cy * S - mask.height / 2)))
    layers = []
    if outline:
        ob = big.filter(ImageFilter.MaxFilter(2 * outline * S + 1))
        layers.append((ob, ocolor))
    layers.append((big, color))
    for m, col in layers:
        a = np.asarray(m.resize((w, h), Image.BOX), np.float32) / 255.0
        col = np.array(col, np.float32)
        img[..., :3] = img[..., :3] * (1 - a[..., None]) + col[:3] * a[..., None]
        img[..., 3] = img[..., 3] * (1 - a) + col[3] * a


def dominant(img, rect, bright=True):
    """rect 안 불투명 픽셀 중 밝은(또는 어두운) 쪽 대표색"""
    x0, y0, x1, y1 = rect
    p = img[y0:y1, x0:x1].reshape(-1, 4)
    p = p[p[:, 3] > 60]
    if not len(p): return (220, 220, 220, 128)
    lum = p[:, :3].mean(1) * p[:, 3] / 128.0
    sel = p[lum >= np.percentile(lum, 85)] if bright else p[lum <= np.percentile(lum, 15)]
    return tuple(np.median(sel, 0))
