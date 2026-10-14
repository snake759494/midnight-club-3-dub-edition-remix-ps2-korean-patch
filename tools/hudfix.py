"""16:9 와이드에서 주행 HUD 가로 늘어남 보정 pnach 섹션 생성 (python hudfix.py -> ../widescreen/SLUS-21355_3021E351.pnach 갱신)
HUD 코드(0x270000~0x2a0000)가 부른 2D 사각형·글자만, 그리고 HUD 의 3D 뷰포트(미니맵·백미러·화살표)와
게이지 직교 투영만 가운데 4:3 영역으로 압축한다. 메뉴·차고 등 플래시 UI 와 3D 장면은 그대로 둔다.
게임 2D 루틴은 GS X = (화면 x + 원점X[0x70e5b8]) << 4 로 좌표를 만든다(화면 x 0..W).
와이드에서 x' = W/8 + x*0.75 (W=화면 폭, 이 게임은 512) 로 가운데 4:3 영역에 압축해 원래 비율로 보이게 한다.
  R: 정수 사각형 루틴 0x52afb8 (스프라이트·미니맵·속도계). 화면 높이 전체 띠(y0<=0, y1>=400: 3D 장면 합성)는 제외
  F/G/H: 글자 루틴 0x52b1f0 (기준점 실수 x, 글자별 상대 x·너비 1/16 단위)
코드는 한글 패치 ELF 의 RAM 최상단 코드 영역 빈 곳(0x1fff000~)에 둔다."""
import struct, elf
from elfpatch import Asm, R

CAVE = 0x1fff000
GATE = 0x1fff3f8
OFFX = 0x1fff3c0          # 플래시 x 오프셋(float)          # F 판정 결과(G/H 용)
HUD_LO, HUD_HI = 0x270000, 0x2a0000   # HUD 요소 코드 범위
import os
# 기본값: 실험으로 확정한 HUD 호출 위치(환경 변수로 바꿔 실험 가능)
#   VIEWS: 미니맵(0x286374, 0x288098), 백미러(0x293d08), 3D 화살표(0x29c4ac) 뷰포트
#   ORTHO: 데미지 링(0x27540c), 속도계(0x29480c), 타코미터(0x298e24) 의 직교 투영
VIEWS = [int(x, 16) for x in os.environ.get('VIEWS', '286374,288098,293d08,29c4ac').split(',') if x]
ORTHO = [int(x, 16) for x in os.environ.get('ORTHO', '27540c,29480c,298e24').split(',') if x]

def sra(a, rd, rt, s): a.r('zero', rt, rd, s, 3)
def lh(a, rt, o, rs): a.i(0x21, rs, rt, o)
def mtc1(a, rt, fs): a.w(0x44800000 | (R[rt] << 16) | (fs << 11))
def fop(a, fn, fd, fs, ft): a.w(0x46000000 | (ft << 16) | (fs << 11) | (fd << 6) | fn)
def x34(a, r):   # r = r*3/4
    a.sll('at', r, 1); a.addu(r, r, 'at'); sra(a, r, r, 2)

def build():
    a = Asm(CAVE); ent = {}
    # R: 0x52b100 'lw v0,ox' 자리에서 호출. v0=원점X, s0=x0, s2=x1 변환
    ent['R'] = a.pc()
    a.i(0xf, 'zero', 'v0', 0x71); a.lw('v0', -0x1a48, 'v0')
    # HUD 코드(0x270000~0x2a0000)가 부른 경우만 변환: 호출자 ra 는 0x52afb8 프레임의 0xa0(sp)
    a.lw('t9', 0xa0, 'sp'); a.lui_ori('at', HUD_LO); a.subu('t9', 't9', 'at')
    a.lui_ori('at', HUD_HI - HUD_LO); a.r('t9', 'at', 'at', 0, 0x2b)   # sltu at,t9,at
    a.beqz('at', 'skip'); a.nop()
    # 제외: 원점(0,0)에서 시작(오프스크린 렌더 타깃), 높이 440 이상(후처리 띠), 폭 400 이상(3D 장면 합성)
    a.or_('at', 's0', 's1'); a.beqz('at', 'skip'); a.nop()
    a.subu('at', 's3', 's1'); a.slti('at', 'at', 440); a.beqz('at', 'skip'); a.nop()
    a.subu('at', 's2', 's0'); a.slti('at', 'at', 400); a.beqz('at', 'skip'); a.nop()
    a.i(0xf, 'zero', 't9', 0x71); a.lw('t9', -0x1af0, 't9'); sra(a, 't9', 't9', 3)   # 화면 폭/8
    x34(a, 's0'); a.addu('s0', 's0', 't9')
    x34(a, 's2'); a.addu('s2', 's2', 't9')
    a.L('skip'); a.jr('ra'); a.nop()
    # F: 0x52b264 'add.s f1,f1,f3' 자리(글자 기준점). HUD 가 그린 글자면 f1 = f1*0.75 + W/8, 판정 결과는 GATE 에 저장(G/H 가 사용)
    #    판정: 0x52b1f0 의 호출 복귀점(0x68(sp))이 래퍼 0x2bc8f0 안(0x2bd95c)이고, 래퍼의 호출자 ra(0x9a8(fp)) 가 HUD 코드
    ent['F'] = a.pc()
    a.lui_ori('t9', GATE); a.i(0x2b, 't9', 'zero', 0)
    a.lw('at', 0x68, 'sp'); a.lui_ori('t8', 0x2bd95c); a.bne('at', 't8', 'fend'); a.nop()
    a.lw('at', 0x9a8, 'fp'); a.lui_ori('t8', HUD_LO); a.subu('at', 'at', 't8')
    a.lui_ori('t8', HUD_HI - HUD_LO); a.r('at', 't8', 't8', 0, 0x2b)   # sltu t8,at,t8
    a.beqz('t8', 'fend'); a.nop()
    a.i(0x2b, 't9', 't8', 0)                                            # GATE = 1
    a.i(0xf, 'zero', 'at', 0x3f40); mtc1(a, 'at', 5); fop(a, 2, 1, 1, 5)
    a.i(0xf, 'zero', 'at', 0x71); a.lw('at', -0x1af0, 'at'); sra(a, 'at', 'at', 3)
    mtc1(a, 'at', 5); a.w(0x46802960)                                   # cvt.s.w f5,f5
    fop(a, 0, 1, 1, 5)
    a.L('fend'); a.jr('ra'); fop(a, 0, 1, 1, 3)
    # G: 0x52b3e0 'lh a0,0(s3)' 자리. 글자 상대 x *0.75
    ent['G'] = a.pc()
    lh(a, 'a0', 0, 's3'); a.lui_ori('at', GATE); a.lw('at', 0, 'at'); a.beqz('at', 'gend'); a.nop()
    x34(a, 'a0'); a.L('gend'); a.jr('ra'); a.nop()
    # H: 0x52b438 'lh a2,4(s3)' 자리. 글자 너비 *0.75
    ent['H'] = a.pc()
    lh(a, 'a2', 4, 's3'); a.lui_ori('at', GATE); a.lw('at', 0, 'at'); a.beqz('at', 'hend'); a.nop()
    x34(a, 'a2'); a.L('hend'); a.jr('ra'); a.nop()
    # (참고) 0x52ad20 다각형 루틴은 플래시 도형 전용(호출자 0x521b64)이라 건드리지 않는다. 플래시 UI 는 원래대로 둔다
    # 플래시 UI(메뉴·차고): x 배율(0x70f1b0 = 화면 폭/무비 폭)을 0.75배, 정점 x 에 화면 폭/8 을 더한다.
    # 들어올 때 j, 나갈 때 j(리프 함수라 ra 보존). 화면 폭/8 은 배율 계산 시점의 f1(화면 폭)에서 구해 OFFX 에 저장
    ent['S'] = a.pc()                                                   # 0x20b65c 'swc1 f0,(t2)' 자리
    a.i(0xf, 'zero', 'at', 0x3f40); mtc1(a, 'at', 2); fop(a, 2, 0, 0, 2)     # f0 *= 0.75
    a.w(0xe5400000)                                                     # swc1 f0,0(t2)
    a.i(0xf, 'zero', 'at', 0x3e00); mtc1(a, 'at', 2); fop(a, 2, 2, 1, 2)     # f2 = 화면 폭 * 0.125
    a.lui_ori('at', OFFX); a.w(0xe4220000)                              # swc1 f2,0(at)  OFFX = 폭/8
    a.i(0xf, 'zero', 't9', 0x3f40); mtc1(a, 't9', 2); fop(a, 2, 2, 1, 2)
    a.w(0xe4220004)                                                     # swc1 f2,4(at)  OFFX+4 = 폭*3/4
    a.j(0x20b660); a.nop()
    for tag, ret, rd, rs, rt in (('X1', 0x20ef10, 3, 3, 4), ('X2', 0x20f040, 3, 3, 4), ('X3', 0x210240, 1, 1, 8)):
        ent[tag] = a.pc()
        fop(a, 2, rd, rs, rt)                                           # 원래 mul.s
        # 무대(4:3) 밖 도형이 화면 안으로 들어오지 않게 x 를 [0, 폭*3/4] 로 제한한 뒤 폭/8 을 더함
        a.lui_ori('at', OFFX); a.w(0xc4200004 | (rt << 16))             # lwc1 frt,4(at)
        fop(a, 0x29, rd, rd, rt)                                        # min.s
        mtc1(a, 'zero', rt); fop(a, 0x28, rd, rd, rt)                   # max.s rd,rd,0
        a.w(0xc4200000 | (rt << 16))                                    # lwc1 frt,0(at)
        fop(a, 0, rd, rd, rt)
        a.j(ret); a.nop()
    # V: HUD 3D 뷰포트(0x530f38: a1=x, a2=y, a3=폭, t0=높이) 호출 대신 들어와 x·폭을 4:3 영역으로 압축
    ent['V'] = a.pc()
    a.i(0xf, 'zero', 'at', 0x71); a.lw('at', -0x1af0, 'at'); sra(a, 'at', 'at', 3)
    a.move('t9', 'at')
    x34(a, 'a1'); a.addu('a1', 'a1', 't9'); x34(a, 'a3')
    a.j(0x530f38); a.nop()
    # O: 2D 직교 투영(0x531420) 호출 대신 들어와 가로 범위를 4/3배로 넓힌 뒤 원래 함수로 점프
    ent['O'] = a.pc()
    fop(a, 0, 0, 12, 13); fop(a, 1, 1, 13, 12)                  # f0=l+r, f1=r-l
    a.i(0xf, 'zero', 'at', 0x3f00); mtc1(a, 'at', 2); fop(a, 2, 0, 0, 2)   # f0 = 중심
    a.lui_ori('at', 0x3f2aaaab); mtc1(a, 'at', 2); fop(a, 2, 1, 1, 2)      # f1 = 폭*2/3
    fop(a, 1, 12, 0, 1); a.j(0x531420); fop(a, 0, 13, 0, 1)
    code = a.bytes()
    assert CAVE + len(code) <= OFFX, 'HUD 코드가 데이터 영역(0x1fff3c0~)과 겹침'
    hooks = {0x52b100: ent['R'], 0x52b264: ent['F'], 0x52b3e0: ent['G'], 0x52b438: ent['H']}
    # 원래 명령 확인(한글 ELF 와 원본이 이 영역은 같다)
    orig = {0x52b100: 0x8ca2e5b8, 0x52b264: 0x46030840, 0x52b3e0: 0x86640000, 0x52b438: 0x86660004}
    for k, v in orig.items():
        assert struct.unpack_from('<I', elf.D, elf.off(k))[0] == v, hex(k)
    lines = ['patch=1,EE,%08x,word,%08x' % (CAVE + 4 * i, struct.unpack_from('<I', code, 4 * i)[0])
             for i in range(len(code) // 4)]
    jhooks = {0x20b65c: ent['S'], 0x20ef08: ent['X1'], 0x20f038: ent['X2'], 0x210238: ent['X3']}
    for k in os.environ.get('JSKIP', '').split(','):
        if k: jhooks.pop(int(k, 16))
    jorig = {0x20b65c: 0xe5400000, 0x20ef08: 0x460418c2, 0x20f038: 0x460418c2, 0x210238: 0x46080842}
    for k, v in jorig.items():
        assert struct.unpack_from('<I', elf.D, elf.off(k))[0] == v, hex(k)
    for c in ORTHO: hooks[c] = ent['O']
    for c in VIEWS: hooks[c] = ent['V']
    lines += ['patch=1,EE,%08x,word,%08x' % (k, (3 << 26) | (t >> 2)) for k, t in hooks.items()]
    lines += ['patch=1,EE,%08x,word,%08x' % (k, (2 << 26) | (t >> 2)) for k, t in jhooks.items()]
    return lines

def section():
    return ('[Widescreen 16:9 HUD fix]\n'
            'description=16:9 에서 주행 HUD와 메뉴·차고·로딩 화면이 가로로 늘어나지 않게 가운데 4:3 비율로 그림. Widescreen 16:9 와 함께 켤 것\n'
            + '\n'.join(build()) + '\n')

if __name__ == '__main__':
    p = '../widescreen/SLUS-21355_3021E351.pnach'
    base = open(p, encoding='utf-8').read().split('\n[Widescreen 16:9 HUD fix]')[0].rstrip('\n') + '\n\n'
    open(p, 'w', encoding='utf-8').write(base + section())
    print('ok')
