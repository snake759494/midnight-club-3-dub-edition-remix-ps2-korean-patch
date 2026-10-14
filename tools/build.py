"""미드나이트 클럽 3 DUB 에디션 리믹스(USA) 한글 패치 빌드
원본 ISO -> 'Midnight Club 3 - DUB Edition Remix (Korean).iso'
"""
import os, re, sys, glob, struct, shutil, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dave, davew, strtbl, kfont, elfpatch, subs, flashfont, flashtext, imgspecs
from udf import UDF

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'Midnight Club 3 - DUB Edition Remix (USA).iso')
DST = os.path.join(ROOT, 'Midnight Club 3 - DUB Edition Remix (Korean).iso')
SEC = 2048
TABLES = ['mcloadstrings', 'mcstrings01', 'mcstrings01_pal', 'mcstrings02', 'mcstrings02_pal',
          'mcstrings04', 'mcstrings04_pal', 'mcstrings08', 'mcstrings08_pal']
# 한글 글리프를 추가할 폰트: (폰트명, ttf, 크기, 셀높이, 상단, 그림자팽창, 기준선위높이)
TTF = 'NanumSquareNeo-cBd.ttf'
FLASH_TTF = 'NanumSquareNeo-eHv.ttf'   # 플래시 UI 의 굵은 둥근 글꼴에 맞춤
FONTS = [f for f in os.environ.get('KFONTS', 'smallspace,arial12,chat,minidub,bigstencil').split(',')]
PAGE = {k: int(v) for k, v in (x.split(':') for x in os.environ.get('KPAGE', '').split(',') if x)}
DEBUG_TINT = '--tint' in sys.argv
TINT = [(240, 240, 240), (255, 60, 60), (60, 255, 60), (80, 140, 255), (255, 255, 0), (255, 0, 255),
        (0, 255, 255), (255, 140, 0), (150, 80, 255), (255, 150, 200), (120, 60, 0), (0, 128, 128),
        (128, 128, 0), (200, 200, 255), (0, 90, 0), (255, 220, 160), (90, 90, 90), (160, 0, 60), (0, 60, 160)]

def iso_records(f):
    f.seek(16 * SEC); pvd = f.read(SEC)
    rl, rs = struct.unpack_from('<I', pvd, 158)[0], struct.unpack_from('<I', pvd, 166)[0]
    f.seek(rl * SEC); d = f.read(rs); out = {}; p = 0
    while p < len(d):
        n = d[p]
        if n == 0: p = (p // SEC + 1) * SEC; continue
        lba, sz = struct.unpack_from('<I', d, p + 2)[0], struct.unpack_from('<I', d, p + 10)[0]
        nm = d[p + 33:p + 33 + d[p + 32]].decode('latin1').split(';')[0]
        out[nm] = (lba, sz, rl * SEC + p); p += n
    return out

from tsvesc import unesc

def src_strings():
    """원본 ISO 문자열 표의 고유 영문(translation/src.tsv). 없으면 원본 ISO 에서 추출"""
    p = os.path.join(ROOT, 'translation', 'src.tsv')
    if not os.path.exists(p):
        import subprocess, sys
        subprocess.check_call([sys.executable, 'dumpsrc.py'], cwd=os.path.dirname(os.path.abspath(__file__)))
    return [unesc(l.rstrip(chr(10)).split(chr(9), 1)[1]) for l in open(p, encoding='utf-8', newline=chr(10))]

def sid(s):
    """번역 표 ID: 영문 원문 UTF-8 의 SHA-1 앞 16자리(공개 번역 표에는 원문 대신 이 값만 둔다)"""
    import hashlib
    return hashlib.sha1(s.encode('utf-8')).hexdigest()[:16]

def load_tr():
    byid = {sid(s): s for s in src_strings()}
    tr = {}
    for fn in sorted(glob.glob(os.path.join(ROOT, 'translation', 'ko_*.tsv'))):
        for ln, line in enumerate(open(fn, encoding='utf-8', newline='\n'), 1):
            line = line.rstrip('\n')
            if not line or line.startswith('#'): continue
            p = line.split('\t')
            assert len(p) == 2, (fn, ln, line)
            key, ko = p[0], unesc(p[1])
            assert key in byid, (fn, ln, key)
            if ko.strip(): tr[byid[key]] = ko
    return apply_cars(tr)

def apply_cars(tr):
    """translation/cars.tsv: 차량·바이크 이름을 한글로(단독 문자열 + 번역문 안의 이름)"""
    import re
    exact, phr = {}, []
    for line in open(os.path.join(ROOT, 'translation', 'cars.tsv'), encoding='utf-8'):
        line = line.rstrip(chr(10))
        if not line or line.startswith('#'): continue
        en, ko = line.split(chr(9))
        if en.startswith('='): exact[en[1:]] = ko
        else: phr.append((en, ko))
    phr.sort(key=lambda p: -len(p[0]))
    rx = re.compile('|'.join(r'(?<![A-Za-z])' + re.escape(e.strip()) + r'(?![A-Za-z])' for e, _ in phr))
    m = {e.strip(): k.strip() for e, k in phr}
    sub = lambda s: rx.sub(lambda g: m[g.group(0)], s)
    srcs = set(src_strings())
    n = 0
    for en in srcs:
        cur = tr.get(en, en)
        new = exact.get(en) or sub(cur)
        if new != cur: tr[en] = new; n += 1
    print('차 이름 한글화 %d개' % n)
    return tr

def font_metrics(A, ents, names, fname, G, t):
    """원본 'H'(없으면 'A'/'0') 글리프로 한글 크기·위치·그림자 팽창·색 산출"""
    import numpy as np, collections, tex
    gi = {g[0]: i for i, g in enumerate(G)}
    c = next(c for c in (72, 65, 48) if c in gi)
    i = gi[c]; g = G[i]; pg = next(k for k in range(len(t)) if i < t[k])
    _, _, _, pal, px = tex.read(get_from(A, ents, 'fonts/texture/%s_%02d.tex' % (fname, pg)))
    a = pal[px[g[2]:g[2] + g[4], g[1]:g[1] + g[3]]]
    ys = np.nonzero(a[..., 3].max(1) > 60)[0]; xs = np.nonzero(a[..., 3].max(0) > 60)[0]
    it, ib = int(ys[0]), int(ys[-1]); caph = ib - it + 1; inkw = int(xs[-1] - xs[0] + 1)
    dil = 0
    sname = 'fonts/texture/%s_%02ds.tex' % (fname, pg)
    if sname in names:
        _, _, _, p2, px2 = tex.read(get_from(A, ents, sname))
        a2 = p2[px2[g[2]:g[2] + g[4], g[1]:g[1] + g[3]]]
        y2 = np.nonzero(a2[..., 3].max(1) > 60)[0]
        dil = max(1, it - int(y2[0])) if len(y2) else 0
    col = collections.Counter(tuple(int(v) for v in x[:3]) for x in a.reshape(-1, 4) if x[3] > 200).most_common(1)
    fill = col[0][0] if col else (240, 240, 240)
    if max(fill) < 200: fill = (240, 240, 240)   # 녹색 등 특수색 폰트는 흰색 계열로(정점색으로 칠해짐)
    target = max(9, round(caph * 1.05))
    size = round(target / 0.95)
    top = max(it, dil)
    cellh = top + target + dil + 1
    # 엔진 진행폭 = 셀폭 + 보정값 + 헤더 전역 자간(S). 한글 잉크 사이 간격을 2px(큰 글꼴은 높이의 12%)로 맞춘다
    S = struct.unpack_from('<I', get_from(A, ents, 'fonts/%s.fonttex' % fname), 8)[0]
    gap = max(2, round(caph * 0.12)) - S
    return dict(size=size, top=top, cellh=cellh, dil=dil, yoff=g[5] - (top - it), gap=gap, fill=fill)

def get_from(f, ents, name):
    import zlib
    e = next(e for e in ents if e[0] == name)
    f.seek(e[1]); c = f.read(e[3])
    return zlib.decompress(c, -15) if e[3] != e[2] else c

def main():
    t0 = time.time()
    tr = load_tr(); print('번역 %d개' % len(tr))
    src = open(SRC, 'rb')
    rec = iso_records(src)
    a_lba, a_size, a_rec = rec['ASSETS.DAT']
    # ASSETS.DAT 를 ISO 안에서 직접 읽는 파일 객체
    class Sub:
        def __init__(s, f, base): s.f, s.b = f, base
        def seek(s, o): s.f.seek(s.b + o)
        def read(s, n): return s.f.read(n)
    A = Sub(src, a_lba * SEC)
    ents = dave.read_fobj(A)
    replace, add = {}, {}
    # 1) 문자열 표
    used = set()
    # 플래시 UI 글꼴에도 한글을 넣으므로(flashfont) 모든 표를 번역하고 영문 우회는 쓰지 않는다
    for t in TABLES:
        d = get_from(A, ents, 'fonts/%s.strtbl' % t)
        replace['fonts/%s.strtbl' % t] = strtbl.build(d, tr)
    for ko in tr.values(): used.update(c for c in ko if ord(c) >= 0x100)
    # 1-2) 자막 CSV (영상 자막은 minidub, 영상 제목은 bigstencil 폰트로 그려진다)
    font_chars = {'minidub': set(), 'bigstencil': set()}
    pairs = subs.load_pairs(os.path.join(ROOT, 'translation'))
    nsub = 0
    for nm in sorted({e[0] for e in ents if e[0].startswith('tune/subtitle/') and e[0].endswith('.csv')}):
        out = subs.rewrite(get_from(A, ents, nm), pairs)
        if out is not None:
            replace[nm] = out; nsub += 1
            txt = {c for c in out.decode('utf-8', 'ignore') if ord(c) >= 0xac00}
            # *_h.csv = 영상 제목(bigstencil), 나머지 = 자막 본문(minidub)
            (font_chars['bigstencil'] if '_h' in nm.rsplit('/', 1)[-1] else font_chars['minidub']).update(txt)
    print('자막 %d개 파일' % nsub)
    # 2) 폰트
    names = {e[0] for e in ents}
    for fi, fname in enumerate(FONTS):
        hdr, G, t = kfont.parse_fonttex(get_from(A, ents, 'fonts/%s.fonttex' % fname))
        have = {g[0] for g in G}
        chars = sorted(c for c in (font_chars.get(fname) or used) if ord(c) > max(have))
        m = font_metrics(A, ents, names, fname, G, t)
        fill = TINT[fi % len(TINT)] if DEBUG_TINT else m['fill']
        st = kfont.Style(os.path.join(ROOT, TTF), m['size'], m['cellh'], m['top'], m['dil'], fill=fill)
        n7 = int(os.environ.get('KP7', '0')) if fname == 'smallspace' else 0
        if n7:
            # 실험: 처음 n7 글자를 마지막 원본 페이지(7) 빈 곳(y>=64)에 넣는다
            import numpy as np
            p7 = bytearray(get_from(A, ents, 'fonts/texture/%s_%02d.tex' % (fname, len(t) - 1)))
            s7 = bytearray(get_from(A, ents, 'fonts/texture/%s_%02ds.tex' % (fname, len(t) - 1)))
            w7 = struct.unpack_from('<H', p7, 0)[0]
            px = np.frombuffer(bytes(p7[14 + 1024:]), np.uint8).reshape(-1, w7).copy()
            usedidx = set(np.unique(px).tolist())
            free = [i for i in range(256) if i not in usedidx and (i & 0x18) in (0, 0x18) and i][:16]
            assert len(free) == 16, free
            for k, i in enumerate(free): p7[14 + 4 * i:18 + 4 * i] = bytes((222, 226, 222, round(k * 255 / 15)))
            spx = np.frombuffer(bytes(s7[14 + 64:]), np.uint8)
            sp = np.stack([spx & 15, spx >> 4], 1).reshape(-1, w7).copy()
            x = 0; y = 64
            for ch in chars[:n7]:
                fill, sh, inkw, pad = kfont.render(ch, st)
                h, w = fill.shape
                if x + w > w7: x = 0; y += h
                q = np.round(fill * 15).astype(int)
                region = px[y:y + h, x:x + w]
                lut = np.array([0] + free[1:], np.uint8)
                region[q > 0] = lut[q[q > 0]]
                sq_ = np.round(sh * 15).astype(np.uint8)
                sp[y:y + h, x:x + w] = np.maximum(sp[y:y + h, x:x + w], sq_)
                G.append([ord(ch), x, y, w, h, m['yoff'], max(-128, inkw + m['gap'] - w)])
                x += w
            t[-1] += n7
            p7[14 + 1024:] = px.tobytes()
            fl = sp.reshape(-1); s7[14 + 64:] = bytes((fl[0::2] & 15) | ((fl[1::2] & 15) << 4))
            replace['fonts/texture/%s_%02d.tex' % (fname, len(t) - 1)] = bytes(p7)
            replace['fonts/texture/%s_%02ds.tex' % (fname, len(t) - 1)] = bytes(s7)
            chars = chars[n7:]
        fmt0 = struct.unpack_from('<H', get_from(A, ents, 'fonts/texture/%s_00.tex' % fname), 4)[0]
        glyphs, pm, ps = kfont.make_pages(chars, st, page=PAGE.get(fname, 256 if fname == 'smallspace' else 128), fmt8=False)
        np0 = len(t)
        for code, pi, x, y, w, h, inkw, pad in glyphs:
            G.append([code, x, y, w, h, m['yoff'], max(-128, inkw + m['gap'] - w)])
        # 페이지 경계표(누적 글리프 수)
        cnt = len(t) and t[-1]
        for k in range(len(pm)):
            cnt += sum(1 for g in glyphs if g[1] == k); t.append(cnt)
        assert all(G[i][0] <= G[i + 1][0] for i in range(len(G) - 1)) and len(t) <= 127
        replace['fonts/%s.fonttex' % fname] = kfont.build_fonttex(hdr, G, t)
        for k in range(len(pm)):
            for nm, data in (('fonts/texture/%s_%02d.tex' % (fname, np0 + k), pm[k]),
                             ('fonts/texture/%s_%02ds.tex' % (fname, np0 + k), ps[k])):
                (replace if nm in names else add)[nm] = data
        print('폰트 %s: 한글 등 %d자, 크기 %d, 페이지 %d->%d' % (fname, len(chars), m['size'], np0, len(t)))
    # 2-2) 플래시 UI(.pck) 내장 텍스처 글꼴에 한글 추가
    #   한글 픽셀 페이지는 ELF 의 RAM 최상단(elfpatch.ATLAS_VA)에 한 벌, pck 에는 표만 넣는다
    fchars = sorted({c for v in tr.values() for c in v if 0xac00 <= ord(c) <= 0xd7a3} | flashtext.all_korean())
    atlas = flashfont.Atlas(fchars, os.path.join(ROOT, FLASH_TTF),
                            flashfont.find_template(lambda n: get_from(A, ents, n)), elfpatch.ATLAS_VA)
    nf = nfont = npool = nst = 0
    fsel = os.environ.get('KFLASH')
    for nm in sorted({e[0] for e in ents if e[0].startswith('flash/') and e[0].endswith('.pck')}):
        if fsel and not any(x in nm for x in fsel.split(',')): continue
        src0 = get_from(A, ents, nm)
        out, k = flashfont.patch_pck_global(src0, atlas)
        out2, np_, ns = flashtext.apply(out if out is not None else src0, atlas)
        if out2 is not None: out = out2; npool += np_; nst += ns
        if out is not None: replace[nm] = out; nf += 1; nfont += k
    print('플래시 %d개 파일, 글꼴 %d개에 한글 %d자 (아틀라스 %d페이지), 상수 풀 %d, 정적 텍스트 %d'
          % (nf, nfont, len(fchars), len(atlas.h_addr), npool, nst))
    # 2-3) 게임 텍스처(이미지) 속 영문 문구
    imgs = imgspecs.build(lambda n: get_from(A, ents, n))
    replace.update(imgs); print('이미지 %d장' % len(imgs))
    # 3) 아카이브 목차/데이터
    head, pieces, new_size = davew.plan_full(A, replace, add)
    u = UDF(src)
    part_end = u.part_start + u.part_len
    assert a_lba + new_size // SEC <= part_end, 'UDF 파티션 초과'
    src.close()
    # 4) ISO 기록
    if not os.path.exists(DST) or os.path.getsize(DST) != os.path.getsize(SRC):
        print('ISO 복사...'); shutil.copyfile(SRC, DST)
    with open(SRC, 'rb') as s, open(DST, 'r+b') as o:
        # ASSETS.DAT 전체를 새 배치로 기록(원본 ISO 에서 읽어 조각별로)
        A0 = a_lba * SEC
        o.seek(A0); o.write(head)
        cur = A0 + len(head)
        for npos, p in pieces:
            o.seek(A0 + cur - A0) if False else None
            if A0 + npos > cur: o.seek(cur); o.write(bytes(A0 + npos - cur))
            o.seek(A0 + npos)
            if p[0] == 'mem': o.write(p[1]); cur = A0 + npos + len(p[1])
            else:
                s.seek(A0 + p[1]); rem = p[2]
                while rem:
                    k = min(rem, 1 << 22); o.write(s.read(k)); rem -= k
                cur = A0 + npos + p[2]
        o.seek(cur)
        pad_end = (part_end) * SEC
        if cur < pad_end:   # 남은 파티션 영역 0 으로 (이전 빌드 잔여 제거)
            o.write(b'\0' * (pad_end - cur))
        # ISO9660 크기
        o.seek(a_rec + 10); o.write(struct.pack('<I', new_size) + struct.pack('>I', new_size))
        u2 = UDF(o)
        lbn = u2.files['/ASSETS.DAT']
        b, tag, ad0, l_ad, adt = u2._fe(lbn)
        struct.pack_into('<Q', b, 56, new_size)
        struct.pack_into('<I', b, ad0, new_size)
        struct.pack_into('<Q', b, 64, (new_size + SEC - 1) // SEC)
        from udf import fix_tag
        fix_tag(b)
        o.seek((u2.part_start + lbn) * SEC); o.write(b)
        # 5) ELF 패치(UTF-8 복원 코드). 커진 ELF 는 ASSETS.DAT 뒤 빈 영역(UDF 파티션 안)으로 옮긴다
        e_lba, e_size, e_rec = rec['SLUS_213.55']
        s.seek(e_lba * SEC); elf0 = s.read(e_size)
        elf1, ncode, heap = elfpatch.patch(elf0, atlas.blob)
        o.seek(e_lba * SEC); o.write(elf0)          # 원래 자리는 원본 유지
        n_lba = a_lba + (new_size + SEC - 1) // SEC + 16
        assert n_lba + (len(elf1) + SEC - 1) // SEC <= part_end, 'ELF 공간 부족'
        o.seek(n_lba * SEC); o.write(elf1)
        o.write(b'\0' * ((-len(elf1)) % SEC))
        o.seek(e_rec + 2); o.write(struct.pack('<I', n_lba) + struct.pack('>I', n_lba))
        o.seek(e_rec + 10); o.write(struct.pack('<I', len(elf1)) + struct.pack('>I', len(elf1)))
        lbn = u2.files['/SLUS_213.55']
        b, tag, ad0, l_ad, adt = u2._fe(lbn)
        struct.pack_into('<Q', b, 56, len(elf1))
        struct.pack_into('<II', b, ad0, len(elf1), n_lba - u2.part_start)
        struct.pack_into('<Q', b, 64, (len(elf1) + SEC - 1) // SEC)
        fix_tag(b)
        o.seek((u2.part_start + lbn) * SEC); o.write(b)
        print('ELF 패치: 코드 %d바이트, 힙 %#x' % (ncode, heap))
    print('완료 %.0f초: %s' % (time.time() - t0, DST))

if __name__ == '__main__':
    main()
