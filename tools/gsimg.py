"""GS 메모리 배치 범용 계산: PSMCT32 로 업로드된 데이터를 PSMT8/PSMT4 로 읽기·쓰기 (임의 크기)"""
import numpy as np
from gsmem import BT32, CT32, BT4, CT4

BT8 = [[0, 1, 4, 5, 16, 17, 20, 21],
       [2, 3, 6, 7, 18, 19, 22, 23],
       [8, 9, 12, 13, 24, 25, 28, 29],
       [10, 11, 14, 15, 26, 27, 30, 31]]
CT8 = [
 [0, 4, 16, 20, 32, 36, 48, 52, 2, 6, 18, 22, 34, 38, 50, 54],
 [8, 12, 24, 28, 40, 44, 56, 60, 10, 14, 26, 30, 42, 46, 58, 62],
 [33, 37, 49, 53, 1, 5, 17, 21, 35, 39, 51, 55, 3, 7, 19, 23],
 [41, 45, 57, 61, 9, 13, 25, 29, 43, 47, 59, 63, 11, 15, 27, 31],
 [96, 100, 112, 116, 64, 68, 80, 84, 98, 102, 114, 118, 66, 70, 82, 86],
 [104, 108, 120, 124, 72, 76, 88, 92, 106, 110, 122, 126, 74, 78, 90, 94],
 [65, 69, 81, 85, 97, 101, 113, 117, 67, 71, 83, 87, 99, 103, 115, 119],
 [73, 77, 89, 93, 105, 109, 121, 125, 75, 79, 91, 95, 107, 111, 123, 127],
 [128, 132, 144, 148, 160, 164, 176, 180, 130, 134, 146, 150, 162, 166, 178, 182],
 [136, 140, 152, 156, 168, 172, 184, 188, 138, 142, 154, 158, 170, 174, 186, 190],
 [161, 165, 177, 181, 129, 133, 145, 149, 163, 167, 179, 183, 131, 135, 147, 151],
 [169, 173, 185, 189, 137, 141, 153, 157, 171, 175, 187, 191, 139, 143, 155, 159],
 [224, 228, 240, 244, 192, 196, 208, 212, 226, 230, 242, 246, 194, 198, 210, 214],
 [232, 236, 248, 252, 200, 204, 216, 220, 234, 238, 250, 254, 202, 206, 218, 222],
 [193, 197, 209, 213, 225, 229, 241, 245, 195, 199, 211, 215, 227, 231, 243, 247],
 [201, 205, 217, 221, 233, 237, 249, 253, 203, 207, 219, 223, 235, 239, 251, 255]]


def addr32(w, h, bw):
    """CT32 (y,x) -> 바이트 주소, bw=버퍼 폭(64px 단위)"""
    y, x = np.mgrid[0:h, 0:w]
    page = (y // 32) * bw + x // 64
    blk = np.array(BT32)[(y % 32) // 8, (x % 64) // 8]
    col = np.array(CT32)[y % 8, x % 8]
    return page * 8192 + blk * 256 + col * 4

def addr8(w, h, bw):
    y, x = np.mgrid[0:h, 0:w]
    page = (y // 64) * max(1, bw // 2) + x // 128
    blk = np.array(BT8)[(y % 64) // 16, (x % 128) // 16]
    return page * 8192 + blk * 256 + np.array(CT8)[y % 16, x % 16]

def addr4(w, h, bw):
    """니블 주소"""
    y, x = np.mgrid[0:h, 0:w]
    page = (y // 128) * max(1, bw // 2) + x // 128
    blk = np.array(BT4)[(y % 128) // 16, (x % 128) // 32]
    return page * 16384 + blk * 512 + np.array(CT4)[y % 16, x % 32]


def _upload_geom(psm, w, h):
    """PSMT8 (w,h) -> CT32 (w/2,h/2), PSMT4 (w,h) -> CT32 (w/2,h/4) 로 업로드된 것으로 본다"""
    return (w // 2, h // 2) if psm == 0x13 else (w // 2, h // 4)

def decode(data, psm, w, h, upload_h):
    """data: 업로드 바이트(CT32 로 w32 x upload_h). psm 0x13=T8, 0x14=T4 -> 인덱스 (h,w)"""
    w32, h32 = _upload_geom(psm, w, h)
    bw = max(1, (w32 + 63) // 64)
    mem = np.zeros(max(8192, ((len(data) + 8191) // 8192 + 4) * 8192), np.uint8)
    a = addr32(w32, h32, bw)
    words = np.frombuffer(data, np.uint8).reshape(h32, w32, 4)
    for k in range(4): mem[a + k] = words[..., k]
    tbw = max(2, (w + 63) // 64)
    if psm == 0x13:
        return mem[addr8(w, h, tbw)]
    nib = np.stack([mem & 15, mem >> 4], 1).reshape(-1)
    return nib[addr4(w, h, tbw)]

def encode(idx, psm, upload_h, nbytes):
    """decode 의 역: 인덱스 (h,w) -> 업로드 바이트"""
    h, w = idx.shape
    w32, h32 = _upload_geom(psm, w, h)
    bw = max(1, (w32 + 63) // 64)
    mem = np.zeros(max(8192, ((nbytes + 8191) // 8192 + 4) * 8192), np.uint8)
    tbw = max(2, (w + 63) // 64)
    if psm == 0x13:
        mem[addr8(w, h, tbw)] = idx
    else:
        nib = np.zeros(mem.size * 2, np.uint8); nib[addr4(w, h, tbw)] = idx & 15
        mem = (nib[0::2] | (nib[1::2] << 4)).astype(np.uint8)
    a = addr32(w32, h32, bw)
    out = np.stack([mem[a + k] for k in range(4)], -1)
    return out.astype(np.uint8).tobytes()


def clut_swizzle8(c):
    """256색 CLUT(CSM1) 저장 순서 <-> 논리 순서"""
    i = np.arange(256); s = (i & 0xe7) | ((i & 8) << 1) | ((i & 0x10) >> 1)
    return c[s]
