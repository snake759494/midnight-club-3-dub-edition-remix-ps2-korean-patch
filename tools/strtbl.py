import struct
def parse(d):
    n=struct.unpack_from('<I',d,0)[0];offs=list(struct.unpack_from('<%dI'%n,d,4))
    p=4+4*n; a,cnt=struct.unpack_from('<2I',d,p);p+=8
    keys=[]
    for i in range(cnt):
        L=struct.unpack_from('<I',d,p)[0];keys.append(d[p+4:p+4+L].decode('latin1'));p+=4+L+1
    hdr=(a,)
    langs=[]
    for li,o in enumerate(offs):
        if o>=len(d): langs.append((o,o,[]));continue
        p=o;c=struct.unpack_from('<I',d,p)[0];p+=4;ents=[]
        for i in range(c):
            h,x=struct.unpack_from('<IH',d,p);p+=6
            L=struct.unpack_from('<I',d,p)[0];font=d[p+4:p+4+L].decode();p+=4+L
            m=struct.unpack_from('<I',d,p)[0];p+=4
            s=d[p:p+2*m].decode('utf-16le');p+=2*m
            sx,sy,y=struct.unpack_from('<ffH',d,p);p+=10
            ents.append([h,x,font,s,sx,sy,y])
        langs.append((o,p,ents))
    return offs,hdr,keys,langs
if __name__=='__main__':
    import sys
    d=open(sys.argv[1],'rb').read()
    offs,hdr,keys,langs=parse(d)
    print(hdr,len(keys),keys[:5])
    for o,e,ents in langs: print(hex(o),hex(e),len(ents),ents[1])
    print(len(d))

def oaat(b):
    """문자열 키 해시(Jenkins one-at-a-time, 대소문자 구분)"""
    h = 0
    for c in b:
        h = (h + c) & 0xffffffff; h = (h + (h << 10)) & 0xffffffff; h ^= h >> 6
    h = (h + (h << 3)) & 0xffffffff; h ^= h >> 11; h = (h + (h << 15)) & 0xffffffff
    return h


def build(d, tr, langs_to=range(7), alt_keys=None, keep_keys=()):
    """tr: {영문(NUL 제외): 한글}. 영어(0번) 섹션 기준으로 같은 인덱스의 문자열을 지정 언어 섹션 전부에 기록.
    alt_keys(키 이름 판정 함수): 해당 키는 '~키' 항목을 추가해 영문 원문을 넣는다(플래시 UI 용)."""
    offs, hdr, keys, langs = parse(d)
    n = len(offs)
    p0 = 4 + 4 * n
    eng = langs[0][2]
    hk = {oaat(k.encode('latin1')): k for k in keys}
    alt = [i for i, e in enumerate(eng) if alt_keys and e[0] in hk and alt_keys(hk[e[0]])]
    keep = {oaat(k.encode('latin1')) for k in keep_keys}
    alt_names = ['~' + hk[eng[i][0]] for i in alt]
    # 키 이름 목록(헤더) 재작성: 기존 + '~' 키
    a, cnt = struct.unpack_from('<2I', d, p0)
    q = p0 + 8
    for _ in range(cnt):
        L = struct.unpack_from('<I', d, q)[0]; q += 4 + L + 1
    head = bytearray(d[p0:q])
    struct.pack_into('<I', head, 4, cnt + len(alt_names))
    for nm in alt_names:
        b = nm.encode('latin1'); head += struct.pack('<I', len(b)) + b + b'\0'
    head += d[q:offs[0]] if offs[0] < len(d) else d[q:]
    out_secs = []
    seen = {}
    def ent(h, x, font, s, sx, sy, y):
        fb = font.encode(); u = s.encode('utf-16le')
        return struct.pack('<IH', h, x) + struct.pack('<I', len(fb)) + fb + struct.pack('<I', len(u) // 2) + u + struct.pack('<ffH', sx, sy, y)
    for li, (o, e, ents) in enumerate(langs):
        if not ents: out_secs.append(None); continue
        if o in seen: out_secs.append(('dup', seen[o])); continue
        seen[o] = li
        sec = bytearray(struct.pack('<I', len(ents) + len(alt)))
        for i, (h, x, font, s, sx, sy, y) in enumerate(ents):
            if li in langs_to:
                es = eng[i][3].rstrip('\0')
                if h in keep: s = eng[i][3]
                elif es in tr: s = tr[es] + '\0'
                elif li != 0: s = eng[i][3]
            sec += ent(h, x, font, s, sx, sy, y)
        for i, nm in zip(alt, alt_names):
            h, x, font, s, sx, sy, y = eng[i]
            sec += ent(oaat(nm.encode('latin1')), x, font, s, sx, sy, y)
        out_secs.append(bytes(sec))
    body = bytearray(head); newoffs = []
    base = p0
    for sec in out_secs:
        if sec is None: newoffs.append(None); continue
        if isinstance(sec, tuple): newoffs.append(newoffs[sec[1]]); continue
        newoffs.append(base + len(body)); body += sec
    end = base + len(body)
    newoffs = [x if x is not None else end for x in newoffs]
    return struct.pack('<I', n) + struct.pack('<%dI' % n, *newoffs) + bytes(body)
