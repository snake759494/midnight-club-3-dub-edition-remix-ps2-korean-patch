import struct,capstone
import os
def _load():
    """원본 ISO 안의 SLUS_213.55 를 읽는다"""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    iso = os.path.join(root, 'Midnight Club 3 - DUB Edition Remix (USA).iso')
    f = open(iso, 'rb'); f.seek(16 * 2048); pvd = f.read(2048)
    rl = struct.unpack_from('<I', pvd, 158)[0]; f.seek(rl * 2048); d = f.read(2048); p = 0
    while d[p]:
        nm = d[p + 33:p + 33 + d[p + 32]]
        if nm.startswith(b'SLUS_213.55'):
            lba, sz = struct.unpack_from('<I', d, p + 2)[0], struct.unpack_from('<I', d, p + 10)[0]
            f.seek(lba * 2048); return f.read(sz)
        p += d[p]
    raise FileNotFoundError('SLUS_213.55')
D=_load()
BASE=0x1a0000-0x80
def off(va): return va-BASE
def va(o): return o+BASE
md=capstone.Cs(capstone.CS_ARCH_MIPS,capstone.CS_MODE_MIPS64+capstone.CS_MODE_LITTLE_ENDIAN)
def dis(a,n=40):
    for i in md.disasm(D[off(a):off(a)+n*4],a): print('%08x  %s %s'%(i.address,i.mnemonic,i.op_str))
def refs(target):
    hi=(target+0x8000)>>16; lo=(target-(hi<<16))&0xffff; out=[]
    for o in range(0x80,len(D)-4,4):
        w=struct.unpack_from('<I',D,o)[0]
        if (w&0xffff)==lo and (w>>26) in (9,0x23,0x2b,0x20,0x24,0x21,0x25,0x28,0x29,0x31,0x39,0x37,0x3f,0x1e,0x1f):
            for b in range(1,16):
                w2=struct.unpack_from('<I',D,o-4*b)[0]
                if (w2>>26)==0xf and (w2&0xffff)==hi: out.append(va(o));break
    return out
def dis1(a,n=40):
    for k in range(n):
        x=a+4*k; l=list(md.disasm(D[off(x):off(x)+4],x))
        print('%08x  %s'%(x,(l[0].mnemonic+' '+l[0].op_str) if l else '.word 0x%08x'%struct.unpack_from('<I',D,off(x))[0]))
def dis2(a,n=40):
    """MMI 등 capstone 이 모르는 명령은 원시 값으로 출력"""
    for k in range(n):
        x=a+4*k; w=D[off(x):off(x)+4]
        ins=list(md.disasm(w,x))
        print('%08x  %s'%(x,(ins[0].mnemonic+' '+ins[0].op_str) if ins else '.word 0x%08x'%struct.unpack('<I',w)[0]))
