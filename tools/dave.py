import struct
CS="\0 #$()-./?0123456789_abcdefghijklmnopqrstuvwxyz~"
def decname(nb,o,prev):
    v=int.from_bytes(nb[o:o+64],'little'); c=v&63; s=''; k=0
    if c>=0x38:
        L=(c-0x38)|(((v>>6)&31)<<3); s=prev[:L]; k=2
    while True:
        c=(v>>(6*k))&63; k+=1
        if c==0: return s
        s+=CS[c]
def read(path):
    f=open(path,'rb');h=f.read(16)
    assert h[:4]==b'Dave'
    n,dsz,nsz=struct.unpack_from('<3I',h,4)
    f.seek(0x800);d=f.read(dsz);nb=f.read(nsz)+b'\0'*64
    out=[];prev=''
    for i in range(n):
        no,off,usz,csz=struct.unpack_from('<4I',d,i*16)
        name=decname(nb,no,prev);prev=name
        out.append((name,off,usz,csz))
    return out
if __name__=='__main__':
    import sys
    for e in read(sys.argv[1]): print('%-60s %10x %9d %9d'%e)

def read_fobj(f):
    f.seek(0); h = f.read(16)
    assert h[:4] == b'Dave'
    n, dsz, nsz = struct.unpack_from('<3I', h, 4)
    f.seek(0x800); d = f.read(dsz); nb = f.read(nsz) + b'\0' * 64
    out = []; prev = ''
    for i in range(n):
        no, off, usz, csz = struct.unpack_from('<4I', d, i * 16)
        name = decname(nb, no, prev); prev = name
        out.append((name, off, usz, csz))
    return out
