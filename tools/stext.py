"""pck 정적 텍스트(태그 6, 0x211ab0) 해석/교체
+0x30 부터 u16 명령 스트림:
  0002 a b | 0001 slot height | 0004 x | 0003 y | 0005 n (glyph adv)*n | ... | 0000
글리프 번호는 해당 slot 글꼴의 글리프 순번."""
import struct

def parse(d, p):
    """-> (명령 목록[(op, args, 위치)], 끝 위치)"""
    hw = lambda q: struct.unpack_from('<H', d, q)[0]
    q = p; cmds = []
    if hw(q) != 2: return None
    cmds.append((2, [hw(q + 2), hw(q + 4)], q)); q += 6
    for _ in range(4000):
        op = hw(q)
        if op == 0: return cmds, q
        if op == 1: cmds.append((1, [hw(q + 2), hw(q + 4)], q)); q += 6
        elif op in (3, 4): cmds.append((op, [hw(q + 2)], q)); q += 4
        elif op == 5:
            n = hw(q + 2)
            if n > 300: return None
            cmds.append((5, [(hw(q + 4 + 4 * i), hw(q + 6 + 4 * i)) for i in range(n)], q)); q += 4 + 4 * n
        elif op == 6: cmds.append((6, [hw(q + 2), hw(q + 4)], q)); q += 6
        else: return None
    return None

def records(pck):
    d = pck.d; W = pck.W; out = []
    for o in range(0x80, len(d) - 0x40, 4):
        if W(o) != 0xcdcdcd06 or W(o + 4) != 0x211ab0: continue
        r = parse(d, o + 0x30)
        if r: out.append(dict(obj=o, cmds=r[0], end=r[1]))
    return out

def text(rec, codes):
    """줄 단위 문자열 목록 (각 0005 가 한 줄)"""
    lines = []
    for op, args, q in rec['cmds']:
        if op == 5: lines.append(''.join(chr(codes[g]) if g < len(codes) else '�' for g, a in args))
    return lines

def slot_of(rec):
    return next((a[0] for op, a, q in rec['cmds'] if op == 1), None)
