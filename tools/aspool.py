"""pck 안 SWF ActionConstantPool(0x88) 찾기/고쳐쓰기 (전체 길이 유지)"""
import struct

def pools(d):
    out = []
    i = 0
    while True:
        i = d.find(b'\x88', i)
        if i < 0: break
        if i + 5 <= len(d):
            L, c = struct.unpack_from('<HH', d, i + 1)
            if 3 <= L < 0x8000 and 1 <= c <= L and i + 3 + L <= len(d):
                body = d[i + 5:i + 3 + L]
                parts = body.split(b'\0')
                if len(parts) == c + 1 and parts[-1] == b'' and d[i + 3 + L] in (0x96, 0x1c, 0x4c, 0x3d, 0x52, 0x8e, 0x9b, 0x99, 0x9d, 0x07, 0x17, 0x1d, 0x00, 0x47, 0x48, 0x8b, 0x94, 0x9e, 0x40, 0x0d, 0x9f):
                    out.append((i, L, [p for p in parts[:-1]]))
                    i += 3 + L; continue
        i += 1
    return out

def rewrite(d, at, L, strs):
    body = b''.join(s + b'\0' for s in strs)
    assert len(body) == L - 2, (len(body), L - 2)
    d[at + 5:at + 3 + L] = body
