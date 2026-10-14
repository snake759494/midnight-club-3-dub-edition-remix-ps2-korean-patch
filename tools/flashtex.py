"""pck 안 텍스처(이미지) 목록·복원·교체"""
import struct, numpy as np
from PIL import Image
import gsimg
from flashfont import Pck

def textures(pck):
    """[(H, U, psm, w, h, upload_h, pix_off, nbytes, clut_off, ncol)]"""
    d = pck.d; W = pck.W; out = []
    inr = lambda v: pck.base <= v < pck.base + len(d)
    for q in range(0, len(d) - 4, 4):
        if W(q) != 0xcafebabe: continue
        H = q - 0x6c
        if H < 0 or not inr(W(H + 0x94)): continue
        U = pck.P(W(H + 0x94))
        code, _, w, h, _, uh = struct.unpack_from('<6H', d, U + 0x28)
        psm = {6: 0x14, 5: 0x13}.get(code)
        if psm is None or not inr(W(U + 8)): continue
        pix = pck.P(W(U + 8)); nb = w * h // 2 if psm == 0x14 else w * h
        clut = pck.P(W(H + 0x90)) if inr(W(H + 0x90)) else None
        out.append((H, U, psm, w, h, uh, pix, nb, clut, 16 if psm == 0x14 else 256))
    return out

def palette(d, clut, n):
    c = np.frombuffer(bytes(d[clut + 0x10:clut + 0x10 + 4 * n]), np.uint8).reshape(n, 4).copy()
    if n == 256: c = gsimg.clut_swizzle8(c)
    return c

def _tv(a):
    a = a.astype(np.int16)
    return np.abs(np.diff(a, axis=0)).mean() + np.abs(np.diff(a, axis=1)).mean()

def decode_auto(raw, psm, w, h, uh):
    """스위즐/선형 중 더 매끈한 쪽 -> (인덱스, swizzled 여부)"""
    a = gsimg.decode(raw, psm, w, h, uh)
    if psm == 0x13: b = np.frombuffer(raw, np.uint8).reshape(h, w)
    else:
        bb = np.frombuffer(raw, np.uint8); b = np.stack([bb & 15, bb >> 4], 1).reshape(h, w)
    return (a, True) if _tv(a) <= _tv(b) else (b, False)

def image(pck, t):
    H, U, psm, w, h, uh, pix, nb, clut, n = t
    idx, _ = decode_auto(bytes(pck.d[pix:pix + nb]), psm, w, h, uh)
    pal = palette(pck.d, clut, n)
    rgba = pal[idx].astype(np.int32); rgba[..., 3] = np.minimum(255, rgba[..., 3] * 2)
    return Image.fromarray(rgba.astype(np.uint8), 'RGBA'), idx, pal
