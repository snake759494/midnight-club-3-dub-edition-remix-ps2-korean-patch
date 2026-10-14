import os
"""SLUS_213.55 패치: UTF-8 이 바이트 단위로 넓혀진 2바이트 문자열을 원래 문자로 복원

게임은 문자열 표(UTF-16)를 여러 곳에서 UTF-8 1바이트 문자열로 바꾼 뒤(0x435fd8),
화면에 그릴 때 바이트를 그대로 2바이트로 넓힌다(인라인 루프 150여 곳). 그러면 한글 1자가
0xEx 0x8x 0x8x 세 글자가 되어 사라진다. 그리는 쪽 진입부 두 곳에서 문자열을 제자리 복원한다.
  - 0x2bc8f0 : 폰트 레이아웃/그리기(a1 = 2바이트 문자열)
  - 0x37c8b8 : 텍스트 위젯 문자열 설정(a2 = 2바이트 문자열, 버튼 안내 등)
복원 코드는 BSS 끝(0x715d40)에 두고 첫 LOAD 세그먼트를 거기까지 늘린 뒤 힙 시작을 뒤로 민다.
"""
import struct

R = {n: i for i, n in enumerate('zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra'.split())}
CODE_VA = 0x1ffc000
CODE_SIZE = 0x4000
ATLAS_VA = 0x1fd0000          # 플래시 UI 용 전역 한글 텍스처 페이지(flashfont.build_atlas)
ATLAS_MAX = CODE_VA - ATLAS_VA
HEAP_OLD = 0x715d3c
HEAP_NEW = 0x719000


class Asm:
    def __init__(self, base):
        self.base = base; self.ins = []; self.labels = {}; self.fix = []

    def pc(self): return self.base + 4 * len(self.ins)
    def L(self, name): self.labels[name] = self.pc()
    def w(self, x): self.ins.append(x & 0xffffffff)

    def i(self, op, rs, rt, imm): self.w((op << 26) | (R[rs] << 21) | (R[rt] << 16) | (imm & 0xffff))
    def r(self, rs, rt, rd, sh, fn): self.w((R[rs] << 21) | (R[rt] << 16) | (R[rd] << 11) | (sh << 6) | fn)

    def addiu(self, rt, rs, imm): self.i(9, rs, rt, imm)
    def andi(self, rt, rs, imm): self.i(12, rs, rt, imm)
    def ori(self, rt, rs, imm): self.i(13, rs, rt, imm)
    def xori(self, rt, rs, imm): self.i(14, rs, rt, imm)
    def lhu(self, rt, o, rs): self.i(0x25, rs, rt, o)
    def sh(self, rt, o, rs): self.i(0x29, rs, rt, o)
    def ld(self, rt, o, rs): self.i(0x37, rs, rt, o)
    def sd(self, rt, o, rs): self.i(0x3f, rs, rt, o)
    def sll(self, rd, rt, s): self.r('zero', rt, rd, s, 0)
    def or_(self, rd, rs, rt): self.r(rs, rt, rd, 0, 0x25)
    def move(self, rd, rs): self.r(rs, 'zero', rd, 0, 0x2d)   # daddu
    def jr(self, rs): self.r(rs, 'zero', 'zero', 0, 8)
    def nop(self): self.w(0)
    def lbu(self, rt, o, rs): self.i(0x24, rs, rt, o)
    def slti(self, rt, rs, imm): self.i(10, rs, rt, imm)
    def sq(self, rt, o, rs): self.i(0x1f, rs, rt, o)
    def lq(self, rt, o, rs): self.i(0x1e, rs, rt, o)
    def subu(self, rd, rs, rt): self.r(rs, rt, rd, 0, 0x23)
    def addu(self, rd, rs, rt): self.r(rs, rt, rd, 0, 0x21)
    def blez(self, rs, l): self._br(6, rs, 'zero', l)
    def lb(self, rt, o, rs): self.i(0x20, rs, rt, o)
    def sb(self, rt, o, rs): self.i(0x28, rs, rt, o)
    def lw(self, rt, o, rs): self.i(0x23, rs, rt, o)
    def lui_ori(self, rt, v): self.i(0xf, 'zero', rt, v >> 16); self.ori(rt, rt, v & 0xffff)

    def _br(self, op, rs, rt, label):
        self.fix.append((len(self.ins), label)); self.i(op, rs, rt, 0)
    def beq(self, rs, rt, l): self._br(4, rs, rt, l)
    def bne(self, rs, rt, l): self._br(5, rs, rt, l)
    def beqz(self, rs, l): self._br(4, rs, 'zero', l)
    def bnez(self, rs, l): self._br(5, rs, 'zero', l)
    def b(self, l): self._br(4, 'zero', 'zero', l)

    def j(self, target): self.w((2 << 26) | ((target >> 2) & 0x3ffffff))
    def jal(self, target): self.w((3 << 26) | ((target >> 2) & 0x3ffffff))

    def bytes(self):
        for k, l in self.fix:
            t = self.labels[l]; off = (t - (self.base + 4 * k + 4)) >> 2
            self.ins[k] = (self.ins[k] & 0xffff0000) | (off & 0xffff)
        return b''.join(struct.pack('<I', x) for x in self.ins)


def find_widen_loops(D, va2off, lo=0x1a0000, hi=0x5e9610):
    """바이트->2바이트 넓히기 루프(7명령) 목록: (주소, T, S, I, N, C, Dst)"""
    W = lambda a: struct.unpack_from('<I', D, va2off(a))[0]
    rs = lambda w: (w >> 21) & 31; rt = lambda w: (w >> 16) & 31; rd = lambda w: (w >> 11) & 31
    out = []
    for a in range(lo, hi - 28, 4):
        w = [W(a + 4 * k) for k in range(7)]
        # addu T,S,I
        if (w[0] >> 26) != 0 or (w[0] & 0x7ff) != 0x21: continue
        T = rd(w[0]); S, I = rs(w[0]), rt(w[0])
        # lbu C,(T)
        if (w[1] >> 26) != 0x24 or rs(w[1]) != T or (w[1] & 0xffff): continue
        C = rt(w[1])
        # addiu I,I,1  (S/I 순서는 여기서 확정)
        if (w[2] >> 26) != 9 or (w[2] & 0xffff) != 1 or rs(w[2]) != rt(w[2]): continue
        if rt(w[2]) == S: S, I = I, S
        if rt(w[2]) != I: continue
        # slt T,I,N
        if (w[3] >> 26) != 0 or (w[3] & 0x7ff) != 0x2a or rd(w[3]) != T or rs(w[3]) != I: continue
        N = rt(w[3])
        # sh C,(Dst)
        if (w[4] >> 26) != 0x29 or rt(w[4]) != C or (w[4] & 0xffff): continue
        Dst = rs(w[4])
        # bnez T, a
        if (w[5] >> 26) != 5 or rs(w[5]) != T or rt(w[5]) != 0: continue
        if ((w[5] & 0xffff) - 0x10000) * 4 + a + 24 != a: continue
        # addiu Dst,Dst,2
        if w[6] != ((9 << 26) | (Dst << 21) | (Dst << 16) | 2): continue
        if len({T, S, I, N, C, Dst}) != 6: continue
        # 진짜 문자열 넓히기만: 앞쪽에 jal strlen(0x432808) 과 addiu N, v0, 1 이 있어야 함
        back = [W(a - 4 * k) for k in range(1, 40)]
        if (3 << 26) | (0x432808 >> 2) not in back: continue
        if ((9 << 26) | (2 << 21) | (N << 16) | 1) not in back: continue
        out.append((a, T, S, I, N, C, Dst))
    return out


def build_code(D, va2off):
    a = Asm(CODE_VA)
    # ---- u8w(a0 = 인자 블록 {src, dst, N, I} 각 8바이트) : 바이트 문자열을 UTF-8 복원하며 2바이트로 넓힘.
    #      a1, a2, t4~t7 은 128비트로 보존 ----
    a.L('u8w')
    a.addiu('sp', 'sp', -96)
    a.sq('a1', 0, 'sp'); a.sq('a2', 16, 'sp'); a.sq('t4', 32, 'sp'); a.sq('t5', 48, 'sp'); a.sq('t6', 64, 'sp'); a.sq('t7', 80, 'sp')
    a.ld('a1', 8, 'a0'); a.ld('a2', 16, 'a0'); a.ld('t4', 24, 'a0')
    a.subu('a2', 'a2', 't4')
    a.ld('a0', 0, 'a0')
    a.L('w_loop')
    a.blez('a2', 'w_end'); a.nop()
    a.lbu('t4', 0, 'a0')
    a.andi('t5', 't4', 0xf0); a.xori('t5', 't5', 0xe0)
    a.bnez('t5', 'w_two'); a.slti('t5', 'a2', 3)
    a.bnez('t5', 'w_one'); a.lbu('t5', 1, 'a0')
    a.andi('t6', 't5', 0xc0); a.xori('t6', 't6', 0x80)
    a.bnez('t6', 'w_one'); a.lbu('t6', 2, 'a0')
    a.andi('t7', 't6', 0xc0); a.xori('t7', 't7', 0x80)
    a.bnez('t7', 'w_one'); a.andi('t4', 't4', 0xf)
    a.sll('t4', 't4', 12)
    a.andi('t5', 't5', 0x3f); a.sll('t5', 't5', 6); a.or_('t4', 't4', 't5')
    a.andi('t6', 't6', 0x3f); a.or_('t4', 't4', 't6')
    a.addiu('a0', 'a0', 3)
    a.b('w_store'); a.addiu('a2', 'a2', -3)
    a.L('w_two')
    a.andi('t5', 't4', 0xe0); a.xori('t5', 't5', 0xc0)
    a.bnez('t5', 'w_one'); a.slti('t5', 'a2', 2)
    a.bnez('t5', 'w_one'); a.lbu('t5', 1, 'a0')
    a.andi('t6', 't5', 0xc0); a.xori('t6', 't6', 0x80)
    a.bnez('t6', 'w_one'); a.andi('t4', 't4', 0x1f)
    a.sll('t4', 't4', 6)
    a.andi('t5', 't5', 0x3f); a.or_('t4', 't4', 't5')
    a.addiu('a0', 'a0', 2)
    a.b('w_store'); a.addiu('a2', 'a2', -2)
    a.L('w_one')
    a.addiu('a0', 'a0', 1); a.addiu('a2', 'a2', -1)
    a.L('w_store')
    a.sh('t4', 0, 'a1')
    a.b('w_loop'); a.addiu('a1', 'a1', 2)
    a.L('w_end')
    a.lq('a1', 0, 'sp'); a.lq('a2', 16, 'sp'); a.lq('t4', 32, 'sp'); a.lq('t5', 48, 'sp'); a.lq('t6', 64, 'sp'); a.lq('t7', 80, 'sp')
    a.jr('ra'); a.addiu('sp', 'sp', 96)

    # ---- 2바이트 sprintf(0x435db8) 의 %s 넓히기(널 종료, s1 -> s0) 전용 썽크 ----
    a.L('spw')
    a.addiu('sp', 'sp', -64)
    a.sq('t4', 0, 'sp'); a.sq('t5', 16, 'sp'); a.sq('t6', 32, 'sp'); a.sq('t7', 48, 'sp')
    a.L('s_loop')
    a.lbu('t4', 0, 's1')
    a.beqz('t4', 's_end'); a.andi('t5', 't4', 0xf0)
    a.xori('t5', 't5', 0xe0)
    a.bnez('t5', 's_two'); a.lbu('t5', 1, 's1')
    a.andi('t6', 't5', 0xc0); a.xori('t6', 't6', 0x80)
    a.bnez('t6', 's_one'); a.lbu('t6', 2, 's1')
    a.andi('t7', 't6', 0xc0); a.xori('t7', 't7', 0x80)
    a.bnez('t7', 's_one'); a.andi('t4', 't4', 0xf)
    a.sll('t4', 't4', 12)
    a.andi('t5', 't5', 0x3f); a.sll('t5', 't5', 6); a.or_('t4', 't4', 't5')
    a.andi('t6', 't6', 0x3f); a.or_('t4', 't4', 't6')
    a.b('s_store'); a.addiu('s1', 's1', 3)
    a.L('s_two')
    a.andi('t6', 't4', 0xe0); a.xori('t6', 't6', 0xc0)
    a.bnez('t6', 's_one'); a.andi('t6', 't5', 0xc0)
    a.xori('t6', 't6', 0x80)
    a.bnez('t6', 's_one'); a.andi('t4', 't4', 0x1f)
    a.sll('t4', 't4', 6)
    a.andi('t5', 't5', 0x3f); a.or_('t4', 't4', 't5')
    a.b('s_store'); a.addiu('s1', 's1', 2)
    a.L('s_one')
    a.lbu('t4', 0, 's1'); a.addiu('s1', 's1', 1)
    a.L('s_store')
    a.sh('t4', 0, 's0')
    a.b('s_loop'); a.addiu('s0', 's0', 2)
    a.L('s_end')
    a.move('v1', 'zero')
    a.lq('t4', 0, 'sp'); a.lq('t5', 16, 'sp'); a.lq('t6', 32, 'sp'); a.lq('t7', 48, 'sp')
    a.jr('ra'); a.addiu('sp', 'sp', 64)

    # ---- 루프별 썽크(22명령) ----
    nm = lambda r: list(R)[r]
    sites = []
    for (site, T, S, I, N, C, Dst) in find_widen_loops(D, va2off):
        T, S, I, N, C, Dst = map(nm, (T, S, I, N, C, Dst))
        t = a.pc(); sites.append((site, t, T, S, I))
        a.addiu('sp', 'sp', -112)
        a.sq('a0', 0, 'sp'); a.sq('ra', 16, 'sp')
        a.sd(T, 64, 'sp'); a.sd(Dst, 72, 'sp'); a.sd(N, 80, 'sp'); a.sd(I, 88, 'sp')
        a.jal(a.labels['u8w']); a.addiu('a0', 'sp', 64)
        a.lq('a0', 0, 'sp'); a.lq('ra', 16, 'sp')
        # 루프 종료 상태 재현: Dst += 2*(N-I), I = N, T = 0, C = 0
        a.ld(Dst, 72, 'sp'); a.ld(C, 80, 'sp'); a.ld(T, 88, 'sp')
        a.subu(C, C, T); a.sll(C, C, 1); a.addu(Dst, Dst, C)
        a.ld(I, 80, 'sp')
        a.move(T, 'zero'); a.move(C, 'zero')
        a.jr('ra'); a.addiu('sp', 'sp', 112)
    # ---- alt_lookup(a0 = 문자열표, a1 = 키): '~키' 가 있으면 그것(영문, 플래시 UI 용), 없으면 원래 키로 0x2be510 ----
    KBUF = CODE_VA + CODE_SIZE - 0x100
    a.L('alt')
    a.addiu('sp', 'sp', -48)
    a.sq('ra', 0, 'sp'); a.sq('a0', 16, 'sp'); a.sq('a1', 32, 'sp')
    a.lui_ori('t4', KBUF); a.addiu('t5', 'zero', 0x7e); a.sb('t5', 0, 't4'); a.addiu('t4', 't4', 1)
    a.move('t6', 'a1'); a.addiu('t7', 'zero', 0xf0)
    a.L('alt_cp')
    a.lb('t5', 0, 't6'); a.sb('t5', 0, 't4'); a.addiu('t6', 't6', 1); a.addiu('t7', 't7', -1)
    a.beqz('t7', 'alt_orig'); a.nop()
    a.bnez('t5', 'alt_cp'); a.addiu('t4', 't4', 1)
    a.lui_ori('a0', KBUF)
    a.jal(0x2be7d8); a.nop()
    a.lq('a0', 16, 'sp')
    a.lw('t4', 0x28, 'a0'); a.sll('t4', 't4', 2); a.addu('t4', 't4', 'a0'); a.lw('a0', 0, 't4')
    a.beqz('a0', 'alt_orig'); a.nop()
    a.jal(0x2befb8); a.move('a1', 'v0')
    a.beqz('v0', 'alt_orig'); a.nop()
    a.lq('a0', 16, 'sp'); a.lui_ori('a1', KBUF)
    a.jal(0x2be510); a.nop()
    a.b('alt_out'); a.nop()
    a.L('alt_orig')
    a.lq('a0', 16, 'sp'); a.lq('a1', 32, 'sp')
    a.jal(0x2be510); a.nop()
    a.L('alt_out')
    a.lq('ra', 0, 'sp')
    a.jr('ra'); a.addiu('sp', 'sp', 48)

    global SPW_VA, ALT_VA
    ALT_VA = a.labels['alt']
    SPW_VA = a.labels['spw']
    return a.bytes(), sites


def patch(D, atlas=b''):
    """D: 원본 ELF bytes -> 패치된 ELF bytes"""
    D = bytearray(D)
    ph = struct.unpack_from('<8I', D, 0x34)
    assert ph[0] == 1 and ph[2] == 0x1a0000 and struct.unpack_from('<H', D, 0x2c)[0] == 1
    base_off = ph[1] - ph[2]
    va2off = lambda va: va + base_off
    code, sites = build_code(bytes(D), va2off)
    # 루프 교체: jal thunk ; addu T,S,I(지연 슬롯) ; nop x5
    rng = os.environ.get('KSITES')
    if rng:
        lo, hi = map(int, rng.split(':')); sites = sites[lo:hi]
    for site, t, T, S, I in sites:
        w0 = struct.unpack_from('<I', D, va2off(site))[0]
        struct.pack_into('<7I', D, va2off(site), (3 << 26) | ((t >> 2) & 0x3ffffff), w0, 0, 0, 0, 0, 0)
    print('넓히기 루프 %d곳 교체' % len(sites))

    # 2바이트 sprintf 의 %s 넓히기 루프(0x435f04~0x435f24, 9명령) -> jal spw
    exp = [0, 0x92220000, 0x26310001, 0x00021600, 0x82230000, 0x00021603, 0xa6020000, 0x1460fff9, 0x26100002]
    assert list(struct.unpack_from('<9I', D, va2off(0x435f04))) == exp, [hex(x) for x in struct.unpack_from('<9I', D, va2off(0x435f04))]
    struct.pack_into('<9I', D, va2off(0x435f04), (3 << 26) | ((SPW_VA >> 2) & 0x3ffffff), *([0] * 8))
    # 게임 메모리 관리자 상한 0x2000000 -> ATLAS_VA (lui a0,0x200 / addiu a0,a0,0)
    #   힙 시작(BSS 끝)을 옮기면 부팅이 깨지므로 RAM 최상단을 아틀라스+코드 자리로 쓴다
    assert struct.unpack_from('<I', D, va2off(0x5a89c0))[0] == 0x3c040200
    assert struct.unpack_from('<I', D, va2off(0x5a89dc))[0] == 0x24840000
    assert len(code) <= CODE_SIZE and CODE_VA + CODE_SIZE == 0x2000000
    assert len(atlas) <= ATLAS_MAX, hex(len(atlas))
    lo = ATLAS_VA if atlas else CODE_VA
    hi = (lo + 0x8000) >> 16
    struct.pack_into('<I', D, va2off(0x5a89c0), 0x3c040000 | hi)
    struct.pack_into('<I', D, va2off(0x5a89dc), 0x24840000 | ((lo - (hi << 16)) & 0xffff))
    # 두 번째 LOAD 세그먼트(파일 끝에 덧붙임): [아틀라스][0 채움][코드]
    body = (atlas + bytes(CODE_VA - ATLAS_VA - len(atlas)) + code) if atlas else code
    while len(D) % 16: D.append(0)
    seg_off = len(D); D += body
    struct.pack_into('<8I', D, 0x54, 1, seg_off, lo, lo, len(body), 0x2000000 - lo, 7, 16)
    struct.pack_into('<H', D, 0x2c, 2)
    return bytes(D), len(code), CODE_VA


if __name__ == '__main__':
    import sys
    d = open(sys.argv[1], 'rb').read()
    out, n, heap = patch(d)
    print('code %d bytes, heap %#x, elf %d -> %d' % (n, heap, len(d), len(out)))
