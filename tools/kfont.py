"""한글 글리프 페이지 생성 + fonttex 확장 (원본: 회백색 채움 + 검은 외곽 그림자 레이어)"""
import struct, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
ROOT = r'D:/ps2/미드나이트클럽3_DUB에디션리믹스/'
SS = 4

def parse_fonttex(d):
    ver = struct.unpack_from('<f', d, 0)[0]
    n = struct.unpack_from('<I', d, 0x2c)[0]
    hdr = d[:0x30]
    G = [list(struct.unpack_from('<IBBBBbb', d, 0x30 + i * 10)) for i in range(n)]
    p = 0x30 + n * 10
    np_ = struct.unpack_from('<I', d, p)[0]
    t = list(struct.unpack_from('<%dI' % np_, d, p + 4))
    tail = d[p + 4 + 4 * np_:]
    assert not tail, tail
    return hdr, G, t

def build_fonttex(hdr, G, t):
    out = bytearray(hdr); struct.pack_into('<I', out, 0x2c, len(G))
    for g in G: out += struct.pack('<IBBBBbb', *g)
    out += struct.pack('<I', len(t)) + struct.pack('<%dI' % len(t), *t)
    return bytes(out)

def tex8(px, pal):
    """8bpp(형식 0x0E) 텍스처: 팔레트 256색. 인덱스 0~7 만 쓰면 CSM1 스위즐과 무관하므로
    16단계 농도를 0~7, 32~39 (스위즐 불변 위치)에 배치한다"""
    h, w = px.shape
    out = bytearray(struct.pack('<7H', w, h, 0x0e, 1, 0, 1, 1))
    full = [(0, 0, 0, 0)] * 256
    idx = list(range(8)) + list(range(32, 40))
    for k, c in enumerate(pal): full[idx[k]] = c
    for c in full: out += bytes(c)
    lut = np.array(idx, np.uint8)
    out += bytes(lut[px.astype(np.uint8)].reshape(-1))
    return bytes(out)

def tex4(px, pal):
    h, w = px.shape
    out = bytearray(struct.pack('<7H', w, h, 0x10, 1, 0, 1, 1))
    out += bytes(np.asarray(pal, np.uint8).reshape(-1))
    f = px.reshape(-1).astype(np.uint8)
    out += bytes((f[0::2] & 15) | ((f[1::2] & 15) << 4))
    return bytes(out)

class Style:
    def __init__(self, ttf, size, cellh, top, dil, fill=(222, 226, 222), shift=0):
        self.font = ImageFont.truetype(ttf, size * SS)
        self.cellh, self.top, self.dil, self.fill, self.shift = cellh, top, dil, fill, shift

def render(ch, st):
    """반환: 채움 커버리지, 그림자 커버리지 (cellh x w), 잉크 폭"""
    f = st.font
    W = st.cellh * SS * 2
    im = Image.new('L', (W, st.cellh * SS * 2), 0)
    d = ImageDraw.Draw(im)
    # 한글 기준 상단 정렬: '가'의 bbox 상단을 top 에 맞춤
    ref = f.getbbox('한')
    d.text((SS * 4 - f.getbbox(ch)[0], st.top * SS - ref[1] + st.shift * SS), ch, font=f, fill=255)
    a = np.asarray(im, np.float32) / 255
    cols = np.nonzero(a.max(0) > 0.02)[0]
    if len(cols) == 0: x0, x1 = SS * 4, SS * 4 + SS * 6
    else: x0, x1 = cols[0], cols[-1] + 1
    pad = st.dil + 1
    inkw = int(np.ceil((x1 - x0) / SS))
    w = inkw + 2 * pad
    # 잘라내기 (SS 배율 기준)
    sx = x0 - pad * SS
    crop = im.crop((sx, 0, sx + w * SS, st.cellh * SS))
    fill = np.asarray(crop.resize((w, st.cellh), Image.BOX), np.float32) / 255
    big = crop.filter(ImageFilter.MaxFilter(2 * st.dil * SS + 1)) if st.dil else crop
    big = big.filter(ImageFilter.GaussianBlur(SS * 0.6))
    sh = np.asarray(big.resize((w, st.cellh), Image.BOX), np.float32) / 255
    return fill, np.clip(sh * 1.15, 0, 1), inkw, pad

def make_pages(chars, st, page=256, fmt8=True):
    """chars 의 글리프를 page x page 4bpp 텍스처들에 배치. 반환: glyph 목록(code,page_rel,x,y,w,h,adv), main pages, shadow pages"""
    cells = []
    for ch in chars:
        fill, sh, inkw, pad = render(ch, st)
        cells.append((ord(ch), fill, sh, inkw, pad))
    pages_m, pages_s, glyphs = [], [], []
    x = y = 0; pm = ps = None
    def newpage():
        return np.zeros((page, page), np.uint8), np.zeros((page, page), np.uint8)
    pm, ps = newpage(); pi = 0
    for code, fill, sh, inkw, pad in cells:
        h, w = fill.shape
        if x + w > page: x = 0; y += h
        if y + h > page:
            pages_m.append(pm); pages_s.append(ps); pm, ps = newpage(); pi += 1; x = y = 0
        pm[y:y + h, x:x + w] = np.round(fill * 15).astype(np.uint8)
        ps[y:y + h, x:x + w] = np.round(sh * 15).astype(np.uint8)
        glyphs.append((code, pi, x, y, w, h, inkw, pad))
        x += w
    pages_m.append(pm); pages_s.append(ps)
    palm = [(st.fill[0], st.fill[1], st.fill[2], round(i * 255 / 15)) for i in range(16)]
    pals = [(0, 0, 0, round(i * 255 / 15)) for i in range(16)]
    return glyphs, [(tex8 if fmt8 else tex4)(p, palm) for p in pages_m], [tex4(p, pals) for p in pages_s]
