"""패치 코드 검증용 최소 MIPS(R5900 일부) 해석기"""
import struct

class CPU:
    def __init__(self, mem):
        self.m = mem; self.r = [0] * 32; self.hi = [0] * 32   # hi: 128비트 상위 64비트(sq/lq)
        self.pc = 0

    def rd(self, a, n): return int.from_bytes(self.m.read(a, n), 'little')
    def wr(self, a, n, v): self.m.write(a, (v & ((1 << (8 * n)) - 1)).to_bytes(n, 'little'))

    def set(self, i, v):
        if i: self.r[i] = v & 0xffffffffffffffff

    def run(self, pc, stop, maxn=200000):
        self.pc = pc; npc = pc + 4; n = 0
        while self.pc != stop:
            n += 1
            if n > maxn: raise RuntimeError('too many steps')
            w = self.rd(self.pc, 4); op = w >> 26; rs = (w >> 21) & 31; rt = (w >> 16) & 31
            rd = (w >> 11) & 31; sa = (w >> 6) & 31; fn = w & 63; imm = w & 0xffff
            simm = imm - 0x10000 if imm & 0x8000 else imm
            R = self.r; s32 = lambda v: ((v & 0xffffffff) ^ 0x80000000) - 0x80000000
            nxt = npc + 4; tgt = None
            if op == 0:
                if fn == 0x21: self.set(rd, s32(R[rs] + R[rt]))
                elif fn == 0x23: self.set(rd, s32(R[rs] - R[rt]))
                elif fn == 0x25: self.set(rd, R[rs] | R[rt])
                elif fn == 0x2d: self.set(rd, R[rs] + R[rt])
                elif fn == 0x00: self.set(rd, s32(R[rt] << sa))
                elif fn == 0x2a: self.set(rd, int(s32(R[rs]) < s32(R[rt])))
                elif fn == 0x08: tgt = R[rs] & 0xffffffff
                else: raise NotImplementedError(hex(w))
            elif op == 9: self.set(rt, s32(R[rs] + simm))
            elif op == 10: self.set(rt, int(s32(R[rs]) < simm))
            elif op == 12: self.set(rt, R[rs] & imm)
            elif op == 13: self.set(rt, R[rs] | imm)
            elif op == 14: self.set(rt, R[rs] ^ imm)
            elif op == 15: self.set(rt, s32(imm << 16))
            elif op == 0x24: self.set(rt, self.rd((R[rs] + simm) & 0xffffffff, 1))
            elif op == 0x20: v = self.rd((R[rs] + simm) & 0xffffffff, 1); self.set(rt, v - 256 if v & 0x80 else v)
            elif op == 0x25: self.set(rt, self.rd((R[rs] + simm) & 0xffffffff, 2))
            elif op == 0x23: self.set(rt, s32(self.rd((R[rs] + simm) & 0xffffffff, 4)))
            elif op == 0x37: self.set(rt, self.rd((R[rs] + simm) & 0xffffffff, 8))
            elif op == 0x28: self.wr((R[rs] + simm) & 0xffffffff, 1, R[rt])
            elif op == 0x29: self.wr((R[rs] + simm) & 0xffffffff, 2, R[rt])
            elif op == 0x2b: self.wr((R[rs] + simm) & 0xffffffff, 4, R[rt])
            elif op == 0x3f: self.wr((R[rs] + simm) & 0xffffffff, 8, R[rt])
            elif op == 0x1f:
                a = (R[rs] + simm) & 0xfffffff0; self.wr(a, 8, R[rt]); self.wr(a + 8, 8, self.hi[rt])
            elif op == 0x1e:
                a = (R[rs] + simm) & 0xfffffff0; self.set(rt, self.rd(a, 8)); self.hi[rt] = self.rd(a + 8, 8)
            elif op == 4:
                if R[rs] == R[rt]: tgt = npc + 4 * simm
            elif op == 5:
                if R[rs] != R[rt]: tgt = npc + 4 * simm
            elif op == 6:
                if s32(R[rs]) <= 0: tgt = npc + 4 * simm
            elif op == 2: tgt = (npc & 0xf0000000) | ((w & 0x3ffffff) << 2)
            elif op == 3: self.set(31, npc + 4); tgt = (npc & 0xf0000000) | ((w & 0x3ffffff) << 2)
            else: raise NotImplementedError(hex(w))
            self.pc = npc
            npc = tgt if tgt is not None else self.pc + 4
        return n


class Mem:
    def __init__(self): self.pages = {}
    def map(self, base, data):
        for i in range(0, len(data)): self.pages[base + i] = data[i]
    def read(self, a, n): return bytes(self.pages.get(a + i, 0) for i in range(n))
    def write(self, a, b):
        for i, x in enumerate(b): self.pages[a + i] = x
