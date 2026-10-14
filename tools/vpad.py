"""테스트 전용: PINE(IPC)으로 게임을 백그라운드 조작 (창 포커스 불필요)
- pnach 테스트 섹션: scePadRead(0x543ed8) 가 1P 데이터를 복사한 직후 VPAD(0x1fff3f0, u16, 눌림=1) 를 버튼 비트(눌림=0)에 반영
- PINE: PCSX2.ini 의 EnablePINE=true, TCP 127.0.0.1:28011
사용: python vpad.py press X|O|T|S|U|D|L|R|START|SELECT [ms] / save N / load N / section(pnach 섹션 출력)"""
import socket, struct, sys, time
from elfpatch import Asm

VPAD = 0x1fff3f0
VPRES = 0x1fff3d0   # 감압 12바이트: 오른 왼 위 아래 △ ○ × □ L1 R1 L2 R2
PRES = dict(R=0, L=1, U=2, D=3, T=4, O=5, X=6, S=7, L1=8, R1=9, L2=10, R2=11)
CAVE = 0x1fff800   # hudfix 코드(0x1fff000~) 와 겹치지 않게
BTN = dict(SELECT=0x0001, START=0x0008, U=0x0010, R=0x0020, D=0x0040, L=0x0080, L2=0x0100, R2=0x0200,
           L1=0x0400, R1=0x0800, T=0x1000, O=0x2000, X=0x4000, S=0x8000)

def section():
    a = Asm(CAVE)
    a.lui_ori('at', VPAD - 4); a.lw('t9', 0, 'at'); a.addiu('t9', 't9', 1); a.i(0x2b, 'at', 't9', 0)   # 호출 횟수(디버그)
    a.i(0x2b, 'at', 's4', -4); a.i(0x2b, 'at', 's1', -8)   # 마지막 rdata·포트(디버그)
    a.lhu('t9', 2, 's4')
    a.bnez('s1', 'skip'); a.nop()                       # 1P(포트 0)만
    a.lui_ori('at', VPAD); a.lhu('at', 0, 'at')
    a.r('at', 'zero', 'at', 0, 0x27)                    # nor at,at,zero
    a.r('t9', 'at', 't9', 0, 0x24)                      # and t9,t9,at
    a.sh('t9', 2, 's4')
    a.lui_ori('at', VPRES)                               # 감압 바이트 12~23 (0=안 눌림)을 VPRES 값으로
    for k in range(3):
        a.lw('t9', 4 * k, 'at'); a.i(0x2b, 's4', 't9', 12 + 4 * k)
    a.L('skip')
    a.addiu('v1', 'zero', 1)                            # 원래 0x544004
    a.beq('s3', 'v1', 'one'); a.nop()                   # 원래 0x544008 bnel s3,v1,0x54401c / lw v0,0x60(s0)
    a.lw('v0', 0x60, 's0'); a.j(0x54401c); a.nop()
    a.L('one'); a.j(0x544010); a.nop()
    code = a.bytes()
    out = ['[DEV virtual pad]', 'description=테스트용 가상 패드(배포 안 함)']
    out += ['patch=1,EE,%08x,word,%08x' % (CAVE + 4 * i, struct.unpack_from('<I', code, 4 * i)[0]) for i in range(len(code) // 4)]
    out += ['patch=1,EE,00544004,word,%08x' % ((2 << 26) | (CAVE >> 2)), 'patch=1,EE,00544008,word,00000000']
    return '\n'.join(out) + '\n'

def pine(payload):
    s = socket.create_connection(('127.0.0.1', 28011), timeout=10)
    s.sendall(struct.pack('<I', len(payload) + 4) + payload)
    hdr = s.recv(4); n = struct.unpack('<I', hdr)[0]; body = b''
    while len(body) < n - 4: body += s.recv(n - 4 - len(body))
    s.close(); return body

def w16(addr, v): return pine(struct.pack('<BIH', 5, addr, v))
def r32(addr): return struct.unpack_from('<I', pine(struct.pack('<BI', 2, addr)), 1)[0]

def setp(names):
    m = 0; pr = bytearray(12)
    for n in names:
        m |= BTN[n]
        if n in PRES: pr[PRES[n]] = 0xff
    for k in range(0, 12, 2): w16(VPRES + k, pr[k] | pr[k + 1] << 8)
    w16(VPAD, m)

def press(names, ms=250):
    setp(names.split('+')); time.sleep(ms / 1000); setp([]); time.sleep(0.25)

if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'section': print(section(), end='')
    elif c == 'press': press(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 150)
    elif c == 'save': print(pine(struct.pack('<BB', 9, int(sys.argv[2]))))
    elif c == 'load': print(pine(struct.pack('<BB', 0xa, int(sys.argv[2]))))
    elif c == 'status': print(pine(struct.pack('<B', 0xf)))
