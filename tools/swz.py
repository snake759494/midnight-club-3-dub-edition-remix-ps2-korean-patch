"""PS2 PSMT4 텍스처 스위즐(PSMCT32/PSMT8 경유 업로드) 변환"""
import numpy as np

def _maps(w, h):
    """4bpp 이미지 (x,y) -> (바이트 위치, 상위니블 여부) 테이블 (알려진 unswizzle4 공식)"""
    pos = np.zeros((h, w), np.int64); hi = np.zeros((h, w), bool)
    for y in range(h):
        for x in range(w):
            blockLocation = (y & ~0xf) * w + (x & ~0x1f) * 2
            swapSelector = (((y + 2) >> 2) & 1) * 4
            posY = (((y & ~3) >> 1) + (y & 1)) & 7
            columnLocation = posY * w * 2 + ((x + swapSelector) & 7) * 4
            byteNum = (x >> 3) & 3
            bitSet = (y >> 1) & 1
            p = blockLocation + columnLocation + byteNum
            pos[y, x] = p; hi[y, x] = bool(bitSet)
    return pos, hi

_cache = {}
def maps(w, h):
    if (w, h) not in _cache: _cache[(w, h)] = _maps(w, h)
    return _cache[(w, h)]

def unswizzle4(data, w, h):
    """data: w*h/2 바이트(4bpp 스위즐) -> (h,w) 인덱스"""
    b = np.frombuffer(data, np.uint8)
    # 먼저 8bpp 바이트 배열로 '펼친' 공간에서 nibble 단위 선택
    lin = np.stack([b & 15, b >> 4], 1).reshape(-1)          # 니블 선형
    pos, hi = maps(w, h)
    # 공식은 8bpp 버퍼(w*h 바이트) 기준: 바이트값의 하위/상위 니블
    buf8 = lin  # w*h 개 니블 = w*h '바이트' 처럼 사용
    v = buf8[pos]
    return np.where(hi, v >> 4, v & 15) if False else v

def swizzle4(idx):
    raise NotImplementedError
