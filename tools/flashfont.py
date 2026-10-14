"""플래시 UI(.pck) 내장 텍스처 글꼴에 한글 글리프 추가

pck = 0x80 바이트 머리 + 힙 이미지. 이미지 안 포인터는 0x06800000 기준(파일 오프셋 = 값 - 0x06800000 + 0x80).
머리 +0xc = 이미지 크기. 로더는 객체 타입별로 포인터를 재배치한다.

글꼴 객체(태그 5, 머리 'cdcdcd05'):
  +0x08 u16 글리프 수(lh)      +0x0c 벡터 글리프 배열(런타임 미사용)
  +0x10 u16[] 글리프별 유니코드  +0x14 u16[] 진행폭(글꼴 단위)
  +0x18 u8[128] ASCII 코드 -> 글리프 번호
  +0xa0 텍스처 글꼴(TG) 포인터
TG: +0 텍스처 목록(H 포인터 배열) +4 글리프 레코드(12바이트) +8 u16 em, +0xa u16 글리프 수
    +0xc u8[] 글리프별 페이지 +0x10 텍스처 수
글리프 레코드: u8 x,y,w,h(128x128 아틀라스) + s16 left,top,right,bottom(기준선 기준 글꼴 단위)
조회(ELF 0x210b60): 코드<0x80 은 ASCII 표, 그 외는 코드 표 선형 탐색. 문자열은 UTF-8 로 디코드(0x210bc0).

텍스처 페이지 단위(U, 0x2180 바이트): U+0 1, U+4 (미사용 연결), U+8 픽셀 포인터(U+0x60),
  U+0x60 픽셀 0x2000(PSMT4 128x128, PSMCT32 64x32 업로드 배치), H=U+0x2090 GS 전송 헤더,
  H+0x90 CLUT 포인터(U+0x2130), H+0x94 U 포인터, U+0x2140 CLUT 16색(흰색, 알파 0..0x80)
"""
import struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import gsmem

BASE = 0x06800000
UNIT = 0x2180




class Pck:
    def __init__(self, data):
        self.d = bytearray(data)
        self.base = struct.unpack_from('<I', self.d, 0)[0]

    def P(self, v): return v - self.base + 0x80
    def V(self, o): return o - 0x80 + self.base

    def W(self, o): return struct.unpack_from('<I', self.d, o)[0]
    def setW(self, o, v): struct.pack_into('<I', self.d, o, v)

    def fonts(self):
        """텍스처 글꼴을 가진 글꼴 객체 오프셋 목록"""
        out = []
        d = self.d
        for o in range(0x80, len(d) - 0xb0, 4):
            if self.W(o) != 0xcdcdcd05: continue
            n = struct.unpack_from('<h', d, o + 8)[0]
            cp, ap, tg = self.W(o + 0x10), self.W(o + 0x14), self.W(o + 0xa0)
            if n <= 0 or not all(self.base <= p < self.base + len(d) for p in (cp, tg)): continue
            t = self.P(tg)
            if struct.unpack_from('<H', d, t + 0xa)[0] != n: continue
            out.append(o)
        return out

    def font_info(self, fo):
        d = self.d
        n = struct.unpack_from('<h', d, fo + 8)[0]
        codes = list(struct.unpack_from('<%dH' % n, d, self.P(self.W(fo + 0x10))))
        ap = self.W(fo + 0x14)
        advs = list(struct.unpack_from('<%dH' % n, d, self.P(ap))) if ap else [0x320] * n
        t = self.P(self.W(fo + 0xa0))
        texl, recp, em, cnt, pagep, ntex = struct.unpack_from('<IIHHII', d, t)
        texs = [self.W(self.P(texl) + 4 * k) for k in range(ntex)]
        recs = [list(struct.unpack_from('<4B4h', d, self.P(recp) + 12 * i)) for i in range(n)]
        # 페이지 표가 없으면(pagep=0) 모든 글리프가 0번 페이지
        pages = list(d[self.P(pagep):self.P(pagep) + n]) if pagep else [0] * n
        return dict(n=n, codes=codes, advs=advs, tg=t, em=em, texs=texs, recs=recs, pages=pages)

    def append(self, blob, align=0x80):
        """이미지 끝에 덧붙이고 파일 오프셋 반환"""
        while len(self.d) % align: self.d.append(0xcd)
        o = len(self.d); self.d += blob
        return o

    def finish(self):
        while len(self.d) % 0x80: self.d.append(0xcd)
        self.setW(0xc, len(self.d) - 0x80)
        return bytes(self.d)


def metrics(info):
    """대표 대문자(H/A/O)로 단위/px, 기준선 위 높이(px), 진행폭 비율"""
    for ch in 'HAOMN0E':
        if ord(ch) in info['codes']:
            i = info['codes'].index(ord(ch)); x, y, w, h, l, t, r, b = info['recs'][i]
            if w and h:
                k = (r - l) / w
                kv = (b - t) / h
                return dict(k=k, kv=kv, h=h, top=t, bottom=b, adv=info['advs'][i], w=w, l=l, r=r)
    return None


def render(ch, font, h_px, inkh):
    """흰색 알파 글리프(여백 없음) -> 0..15 배열, 실제 높이는 h_px"""
    S = 4
    im = Image.new('L', (h_px * S * 3, h_px * S * 2), 0)
    dr = ImageDraw.Draw(im)
    bb = font.getbbox('한')
    dr.text((h_px * S - font.getbbox(ch)[0], -bb[1] + (h_px - inkh) // 2 * S), ch, font=font, fill=255)
    a = np.asarray(im, np.float32) / 255
    cols = np.nonzero(a.max(0) > 0.02)[0]
    if not len(cols): return np.zeros((h_px, 1), np.uint8)
    x0 = cols[0] // S * S; x1 = (cols[-1] // S + 1) * S
    crop = im.crop((x0, 0, x1, h_px * S))
    g = np.asarray(crop.resize(((x1 - x0) // S, h_px), Image.BOX), np.float32) / 255
    return np.clip(np.round(g * 15 * 1.08), 0, 15).astype(np.uint8)


_GCACHE = {}
_PCACHE = {}


def glyph(ch, ttf, hpx):
    key = (ch, ttf, hpx)
    if key not in _GCACHE:
        font = ImageFont.truetype(ttf, round(hpx * 4 / 0.95))
        _GCACHE[key] = render(ch, font, hpx, hpx)
    return _GCACHE[key]


def layout(chars, ttf, hpx):
    """chars 를 128x128 페이지들에 배치 -> (페이지 픽셀(인코딩됨) 목록, 배치 목록). 결과 캐시"""
    key = (tuple(chars), ttf, hpx)
    if key in _PCACHE: return _PCACHE[key]
    pages_px = []; place = []
    cur = np.zeros((128, 128), np.uint8); x = y = 0
    for c in chars:
        g = glyph(c, ttf, hpx); h, w = g.shape
        if x + w > 128: x = 0; y += h + 1
        if y + h > 128:
            pages_px.append(cur); cur = np.zeros((128, 128), np.uint8); x = y = 0
        cur[y:y + h, x:x + w] = g
        place.append((c, len(pages_px), x, y, w, h)); x += w + 1
    pages_px.append(cur)
    res = ([gsmem.encode_t4_to_ct32(p) for p in pages_px], place)
    _PCACHE[key] = res
    return res


def add_glyphs(pck, fo, chars, ttf, template_unit, scale=1.15):
    """글꼴 fo 에 chars 추가(이미 있는 코드는 건너뜀). 반환: 추가 글자 수"""
    info = pck.font_info(fo)
    m = metrics(info)
    if m is None: return 0
    have = set(info['codes'])
    chars = [c for c in chars if ord(c) not in have]
    if not chars: return 0
    hpx = max(m['h'], round(m['h'] * scale))
    enc, place = layout(chars, ttf, hpx)
    ntex0 = len(info['texs'])
    new_h = []
    for px in enc:
        u = bytearray(template_unit)
        u[0x60:0x2060] = px
        o = pck.append(bytes(u))
        struct.pack_into('<I', pck.d, o + 8, pck.V(o + 0x60))
        struct.pack_into('<I', pck.d, o + 0x2120, pck.V(o + 0x2130))
        struct.pack_into('<I', pck.d, o + 0x2124, pck.V(o))
        new_h.append(pck.V(o + 0x2090))
    n0 = info['n']; n1 = n0 + len(place)
    kx, kv = m['k'], m['kv']
    bot = m['bottom']; top = bot - round(hpx * kv)
    sp = max(1, round(kx * 1.5))
    codes = info['codes'] + [ord(c) for c, *_ in place]
    advs = info['advs'] + [round(w * kx) + sp for c, pg, x, y, w, h in place]
    recs = info['recs'] + [[x, y, w, h, 0, top, round(w * kx), bot] for c, pg, x, y, w, h in place]
    pages = info['pages'] + [ntex0 + pg for c, pg, *_ in place]
    texs = info['texs'] + new_h
    assert len(texs) <= 255 and n1 < 32768
    o_code = pck.append(struct.pack('<%dH' % n1, *codes), 16)
    o_adv = pck.append(struct.pack('<%dH' % n1, *advs), 16)
    o_rec = pck.append(b''.join(struct.pack('<4B4h', *r) for r in recs), 16)
    o_pg = pck.append(bytes(pages), 16)
    o_tex = pck.append(struct.pack('<%dI' % len(texs), *texs), 16)
    t = info['tg']
    struct.pack_into('<h', pck.d, fo + 8, n1)
    pck.setW(fo + 0x10, pck.V(o_code)); pck.setW(fo + 0x14, pck.V(o_adv))
    pck.setW(t + 0, pck.V(o_tex)); pck.setW(t + 4, pck.V(o_rec))
    struct.pack_into('<H', pck.d, t + 0xa, n1)
    pck.setW(t + 0xc, pck.V(o_pg)); pck.setW(t + 0x10, len(texs))
    return len(place)


def text_fonts(pck):
    """본문용 글꼴: 글리프 40개 이상이고 A~Z 를 가진 것"""
    out = []
    for f in pck.fonts():
        i = pck.font_info(f)
        if i['n'] >= 40 and all(ord(c) in i['codes'] for c in 'AEMRST'): out.append(f)
    return out


def patch_pck(data, chars, ttf):
    """pck 의 본문용 글꼴 전부에 chars 추가. 바뀌지 않으면 None"""
    pck = Pck(data)
    fonts = text_fonts(pck)
    if not fonts: return None, 0
    tu = None
    for f in pck.fonts():
        tu = template_unit(pck, pck.font_info(f))
        if tu: break
    if tu is None: return None, 0
    added = 0
    for f in fonts: added += add_glyphs(pck, f, chars, ttf, tu)
    return (pck.finish() if added else None), len(fonts)


def template_unit(pck, info):
    """글꼴의 두 번째 텍스처 페이지 단위(U..U+0x2180)를 복제 원본으로"""
    for h in info['texs']:
        H = pck.P(h); U = pck.P(pck.W(H + 0x94))
        if H - U == 0x2090: return bytes(pck.d[U:U + UNIT])
    return None


# ---------------------------------------------------------------------------
# 전역 아틀라스 방식: 한글 픽셀 페이지는 ELF 메모리(절대 주소)에 한 벌만 두고,
# 각 pck 글꼴에는 표(코드/진행폭/레코드/페이지)와 확장 텍스처 목록만 넣는다.
# 텍스처 목록의 원래 개수(TG+0x10)는 그대로 두어 로더가 앞부분만 재배치하게 한다.
ATLAS_PX = 20


class Atlas:
    def __init__(self, chars, ttf, template, base, px=ATLAS_PX):
        """template: pck 에서 뽑은 페이지 단위(0x2180 바이트, 적재 전 값). base: 적재 절대 주소"""
        enc, place = layout(chars, ttf, px)
        self.px = px; self.base = base
        self.place = {c: (pg, x, y, w, h) for c, pg, x, y, w, h in place}
        self.h_addr = []
        blob = bytearray()
        for k, pix in enumerate(enc):
            U = base + len(blob)
            u = bytearray(template)
            u[0x60:0x2060] = pix
            struct.pack_into('<I', u, 4, 0)
            struct.pack_into('<I', u, 8, U + 0x60)
            struct.pack_into('<I', u, 0x2120, U + 0x2130)
            struct.pack_into('<I', u, 0x2124, U)
            blob += u
            self.h_addr.append(U + 0x2090)
        self.blob = bytes(blob)


def add_global(pck, fo, atlas, scale=1.15):
    info = pck.font_info(fo)
    m = metrics(info)
    if m is None: return 0
    have = set(info['codes'])
    if not any(ord(c) not in have for c in atlas.place): return 0
    # 같은 이름의 글꼴이 pck마다 원래 글리프 수가 달라도(152/153 등) 한글 번호가 같도록
    # 아틀라스 전체를 16 배수 위치부터 같은 순서로 붙인다(빈 칸은 크기 0 글리프)
    chars = list(atlas.place)
    ntex0 = len(info['texs'])
    assert ntex0 + len(atlas.h_addr) <= 255
    kx, kv = m['k'], m['kv']
    hpx = m['h'] * scale                   # 이 글꼴에서 한글이 차지할 높이(원 글꼴 px)
    s = hpx / atlas.px                     # 아틀라스 px -> 글꼴 px
    bot = m['bottom']; top = bot - round(hpx * kv)
    sp = max(1, round(kx * 1.5))
    codes = list(info['codes']); advs = list(info['advs']); recs = [list(r) for r in info['recs']]; pages = list(info['pages'])
    while len(codes) % 16:
        codes.append(0xe000 + len(codes)); advs.append(0); recs.append([0] * 8); pages.append(0)
    for c in chars:
        pg, x, y, w, h = atlas.place[c]
        ww = round(w * s * kx)
        codes.append(ord(c)); advs.append(ww + sp)
        recs.append([x, y, w, h, 0, top, ww, bot]); pages.append(ntex0 + pg)
    n1 = len(codes)
    assert n1 < 32768
    texs = info['texs'] + atlas.h_addr
    o_code = pck.append(struct.pack('<%dH' % n1, *codes), 16)
    o_adv = pck.append(struct.pack('<%dH' % n1, *advs), 16)
    o_rec = pck.append(b''.join(struct.pack('<4B4h', *r) for r in recs), 16)
    o_pg = pck.append(bytes(pages), 16)
    o_tex = pck.append(struct.pack('<%dI' % len(texs), *texs), 16)
    t = info['tg']
    struct.pack_into('<h', pck.d, fo + 8, n1)
    pck.setW(fo + 0x10, pck.V(o_code)); pck.setW(fo + 0x14, pck.V(o_adv))
    pck.setW(t + 0, pck.V(o_tex)); pck.setW(t + 4, pck.V(o_rec))
    struct.pack_into('<H', pck.d, t + 0xa, n1)
    pck.setW(t + 0xc, pck.V(o_pg))
    # t+0x10(텍스처 수)는 원래 값 유지: 로더가 앞쪽(pck 내부)만 재배치
    return len(chars)


def patch_pck_global(data, atlas):
    pck = Pck(data)
    fonts = text_fonts(pck)
    added = sum(add_global(pck, f, atlas) for f in fonts)
    return (pck.finish() if added else None), len(fonts)


def find_template(get_data):
    """garage.pck 의 두 번째 페이지 단위를 템플릿으로"""
    pck = Pck(get_data('flash/garage.pck'))
    for f in pck.fonts():
        tu = template_unit(pck, pck.font_info(f))
        if tu: return tu
    raise RuntimeError('템플릿 없음')
