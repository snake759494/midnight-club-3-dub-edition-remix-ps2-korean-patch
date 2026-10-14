"""플래시 UI(내장 글꼴, 한글 없음)로 넘어가는 문자열 표 키 수집

0x2be510(키 -> 문자열 조회) 직후 UTF-8 변환(0x435fd8)이나 프롬프트 설정(0x290ee8/0x291108)으로
이어지는 곳의 키를 모은다. 키가 함수 인자로 들어온 경우(래퍼 함수)는 그 함수의 호출부에서 다시 추적한다.
"""
import struct, json
from elf import D, off
W = lambda a: struct.unpack_from('<I', D, off(a))[0]
J = lambda t: (3 << 26) | ((t >> 2) & 0x3ffffff)
LOOK = J(0x2be510)
PROMPT = {J(0x290ee8), J(0x291108), J(0x290eb8)}       # 버튼 안내(플래시) 설정
FLASH = {J(0x320968), J(0x290fe8), J(0x290eb8), J(0x28f5d0)}   # 플래시 변수/텍스트 설정
CONV = J(0x435fd8)                                       # UTF-16 -> UTF-8


def flash_bound(a):
    """0x2be510 호출 a 뒤에서 결과가 플래시로 가는지(정적 근사)"""
    for k in range(1, 40):
        w = W(a + 4 * k)
        if w in PROMPT: return True
        if w == CONV:
            return any(W(a + 4 * (k + j)) in FLASH for j in range(1, 30))
    return False
TEXT_LO, TEXT_HI = 0x1a0000, 0x5e9610

def sx(v): return v - 0x10000 if v & 0x8000 else v

def fstart(a):
    b = a
    while b > TEXT_LO:
        if W(b - 8) == 0x03e00008: return b
        b -= 4
    return None

def resolve(a, reg, depth=0):
    """a 직전까지 reg 에 들어간 값: 상수 주소(int), ('arg', r)(함수 인자), None(알 수 없음)"""
    if depth > 6: return None
    fs = fstart(a)
    b = a - 4
    while fs is not None and b >= fs:
        w = W(b); op = w >> 26; rt = (w >> 16) & 31; rs = (w >> 21) & 31
        if op == 9 and rt == reg and rs == reg and depth > 0:      # 상위값(lui) 탐색 중 다른 경로의 addiu reg,reg 는 건너뜀
            b -= 4; continue
        if op == 9 and rt == reg:                                   # addiu
            if rs == 0: return sx(w & 0xffff)
            base = resolve(b, rs, depth + 1)
            return base + sx(w & 0xffff) if isinstance(base, int) else None
        if op == 0xf and rt == reg: return (w & 0xffff) << 16       # lui
        if op == 0 and (w & 0x3f) in (0x25, 0x2d, 0x21) and ((w >> 11) & 31) == reg:   # move
            r2 = (w >> 16) & 31
            src = rs if r2 == 0 else (r2 if rs == 0 else None)
            return None if src is None else resolve(b, src, depth + 1)
        if op in (0x23, 0x20, 0x24, 0x21, 0x25, 0x37, 0x27, 0x1a, 0x1b, 0x22, 0x26) and rt == reg: return None
        if op == 0 and ((w >> 11) & 31) == reg and (w & 0x3f) not in (0x08, 0x09): return None
        if op == 3 and depth == 0 and reg in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 24, 25) and b < a - 8:
            return None                                             # 호출이 임시 레지스터를 덮음
        b -= 4
    if reg in (4, 5, 6, 7): return ('arg', reg)
    return None

def string_at(v):
    if not (0x600000 <= v < 0x6a0000): return None
    s = D[off(v):off(v) + 100].split(b'\0')[0]
    try: return s.decode('latin1')
    except UnicodeDecodeError: return None

def collect():
    calls = {}
    for a in range(TEXT_LO, TEXT_HI, 4):
        w = W(a)
        if (w >> 26) == 3: calls.setdefault((w & 0x3ffffff) << 2, []).append(a)
    keys = set(); miss = []
    todo = []
    for a in calls.get(0x2be510, []):
        if flash_bound(a):
            todo.append((a + 8, 5))
    seen = set()
    while todo:
        site, reg = todo.pop()
        if (site, reg) in seen: continue
        seen.add((site, reg))
        v = resolve(site, reg)
        if isinstance(v, int):
            s = string_at(v)
            if s is not None: keys.add(s)
            else: miss.append(site)
        elif isinstance(v, tuple):
            f = fstart(site - 4)
            for c in calls.get(f, []): todo.append((c + 8, v[1]))
        else:
            miss.append(site)
    return keys, miss

if __name__ == '__main__':
    k, m = collect()
    print(len(k), 'miss', len(m))
    print(sorted(k))
