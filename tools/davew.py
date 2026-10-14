"""Dave 아카이브 목차 재작성: 기존 이름 블록 보존 + 새 항목 삽입 + 바뀐 파일은 끝에 추가"""
import struct, zlib
import dave
CSI = {c: i for i, c in enumerate(dave.CS)}

def encname(s):
    v = 0; k = 0
    for c in s + '\0':
        v |= CSI[c] << (6 * k); k += 1
    return v.to_bytes((6 * k + 7) // 8, 'little')

def pack(data):
    c = zlib.compressobj(9, zlib.DEFLATED, -15); z = c.compress(data) + c.flush()
    return (z, len(data), len(z)) if len(z) < len(data) else (data, len(data), len(data))

def rebuild(src, orig_size, replace, add):
    """src: 원본 assets.dat 파일 객체. replace: {name: bytes}, add: {name: bytes}
    반환: (헤더+목차+이름 블록, 추가 데이터 blob, blob 시작 오프셋)"""
    src.seek(0); h = src.read(16)
    n, dsz, nsz = struct.unpack_from('<3I', h, 4)
    src.seek(0x800); toc = src.read(dsz); names = src.read(nsz)
    ents = []
    prev = ''
    nb = names + b'\0' * 64
    for i in range(n):
        no, off, usz, csz = struct.unpack_from('<4I', toc, i * 16)
        nm = dave.decname(nb, no, prev); prev = nm
        ents.append([nm, no, off, usz, csz, False])   # False = 원본 이름 바이트 사용
    # 새 항목 삽입(정렬 위치)
    for nm in sorted(add):
        pos = next(i for i, e in enumerate(ents) if e[0] > nm)
        assert ents[pos - 1][0] < nm, (nm, ents[pos - 1][0], ents[pos][0])
        ents.insert(pos, [nm, None, None, 0, 0, True])
        if not ents[pos + 1][5]:
            ents[pos + 1][5] = True       # 다음 항목은 접두어 참조가 깨지므로 완전 이름으로 재인코딩
    newnames = bytearray(names)
    for e in ents:
        if e[5]:
            e[1] = len(newnames); newnames += encname(e[0])
    N = len(ents)
    dsz2 = (N * 16 + 0x7ff) & ~0x7ff
    nsz2 = (len(newnames) + 0x7ff) & ~0x7ff
    data_start = 0x800 + dsz2 + nsz2
    blob = bytearray(); base = (orig_size + 0x7ff) & ~0x7ff
    def put(b):
        while len(blob) % 0x800: blob.append(0)
        o = base + len(blob); blob.extend(b); return o
    cache = {}
    moved = 0
    for e in ents:
        nm = e[0]
        if nm in replace or nm in add:
            if nm not in cache:
                z, u, c = pack(replace.get(nm, add.get(nm)))
                cache[nm] = (put(z), u, c)
            e[2], e[3], e[4] = cache[nm]
        elif e[2] < data_start and e[4] > 0:
            key = ('mv', e[2])
            if key not in cache:
                src.seek(e[2]); cache[key] = put(src.read(e[4])); moved += 1
            e[2] = cache[key]
    hdr = bytearray(0x800); hdr[:4] = b'Dave'
    struct.pack_into('<3I', hdr, 4, N, dsz2, nsz2)
    t = bytearray(dsz2)
    for i, e in enumerate(ents): struct.pack_into('<4I', t, i * 16, e[1], e[2], e[3], e[4])
    nmb = bytes(newnames) + b'\0' * (nsz2 - len(newnames))
    while len(blob) % 0x800: blob.append(0)
    print('dave: entries %d (+%d), header %#x, moved %d files, blob %.1f MB' % (N, len(add), data_start, moved, len(blob) / 1e6))
    return bytes(hdr + t + nmb), bytes(blob), base


def plan_full(src, replace, add):
    """ASSETS.DAT 전체 재작성 계획.
    원래 데이터 순서·정렬(0x800/0x100/0x20/0x10)을 유지하고, 바뀐 파일은 제자리에 새 크기로 넣는다.
    반환: (머리+목차+이름 바이트, 조각 목록[(새 오프셋, ('src', 옛 오프셋, 길이) | ('mem', bytes))], 전체 크기)"""
    src.seek(0); h = src.read(16)
    n, dsz, nsz = struct.unpack_from('<3I', h, 4)
    src.seek(0x800); toc = src.read(dsz); names = src.read(nsz)
    nb = names + b'\0' * 64
    ents = []; prev = ''
    for i in range(n):
        no, off, usz, csz = struct.unpack_from('<4I', toc, i * 16)
        nm = dave.decname(nb, no, prev); prev = nm
        ents.append([nm, no, off, usz, csz, False])
    for nm in sorted(add):
        pos = next(i for i, e in enumerate(ents) if e[0] > nm)
        ents.insert(pos, [nm, None, None, 0, 0, True])
        if not ents[pos + 1][5]: ents[pos + 1][5] = True
    newnames = bytearray(names)
    for e in ents:
        if e[5]:
            e[1] = len(newnames); newnames += encname(e[0])
    N = len(ents)
    dsz2 = (N * 16 + 0x7ff) & ~0x7ff
    nsz2 = (len(newnames) + 0x7ff) & ~0x7ff
    data_start = 0x800 + dsz2 + nsz2
    raw = {e[0] for e in ents if e[2] is not None and e[4] and e[3] == e[4]}   # 원래 비압축 저장
    packed = {}
    for nm, data in list(replace.items()) + list(add.items()):
        packed[nm] = (data, len(data), len(data)) if nm in raw else pack(data)
    # 옛 오프셋별 데이터(같은 오프셋을 여러 이름이 공유할 수 있음)
    by_off = {}
    for e in ents:
        if e[2] is None or e[4] == 0: continue
        by_off.setdefault(e[2], []).append(e)
    pieces = []; pos = (data_start + 0x7ff) & ~0x7ff
    placed = {}
    newoff = {}
    def align_of(o):
        for a in (0x800, 0x100, 0x20, 0x10):
            if o % a == 0: return a
        return 0x10
    for o in sorted(by_off):
        es = by_off[o]
        a = align_of(o)
        pos = (pos + a - 1) & ~(a - 1)
        rep = next((e[0] for e in es if e[0] in packed), None)
        if rep and rep in placed:          # 바뀐 파일의 중복 사본은 첫 사본 하나로 합친다
            for e in es:
                e[2] = placed[rep]; e[3], e[4] = packed[e[0]][1], packed[e[0]][2]
            continue
        if rep:
            z, u, c = packed[rep]; pieces.append((pos, ('mem', z))); size = c
            placed[rep] = pos
        else:
            size = max(e[4] for e in es); pieces.append((pos, ('src', o, size)))
        for e in es:
            if e[0] in packed: e[3], e[4] = packed[e[0]][1], packed[e[0]][2]
            e[2] = pos
        newoff[o] = pos
        pos += size
    for e in ents:   # 새 항목
        if e[2] is None and e[0] in packed:
            pos = (pos + 0x7ff) & ~0x7ff
            z, u, c = packed[e[0]]; pieces.append((pos, ('mem', z)))
            e[2], e[3], e[4] = pos, u, c; pos += c
    for e in ents:   # 크기 0 항목(디렉터리 등): 원래 값 유지하되 데이터 영역 밖이면 그대로
        if e[2] is None: e[2] = 0
    total = (pos + 0x7ff) & ~0x7ff
    hdr = bytearray(0x800); hdr[:4] = b'Dave'
    struct.pack_into('<3I', hdr, 4, N, dsz2, nsz2)
    t = bytearray(dsz2)
    for i, e in enumerate(ents): struct.pack_into('<4I', t, i * 16, e[1], e[2], e[3], e[4])
    nmb = bytes(newnames) + b'\0' * (nsz2 - len(newnames))
    print('dave(full): entries %d (+%d), data start %#x, size %.1f MB' % (N, len(add), data_start, total / 1e6))
    return bytes(hdr + t + nmb), pieces, total
